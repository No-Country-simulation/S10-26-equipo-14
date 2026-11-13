"""Low-rate parser for public Frávega product detail pages."""

from __future__ import annotations

import json
import re
import time
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.extractors.base import ExtractionError, ProductSnapshot
from app.extractors.http_content import decode_http_body
from app.models import Store, StoreProduct

_ALLOWED_HOSTS = {"fravega.com", "www.fravega.com"}
_USER_AGENT = "PriceScopePriceMonitor/0.1 (+https://github.com/No-Country-simulation/S10-26-equipo-14)"
_MAX_RESPONSE_BYTES = 5 * 1024 * 1024
_MAX_TEXT_LENGTH = 4000


class _ProductPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_json_ld = False
        self._parts: list[str] = []
        self.documents: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attributes = {name.lower(): value for name, value in attrs}
        content_type = (attributes.get("type") or "").split(";", 1)[0].strip().lower()
        if content_type == "application/ld+json":
            self._in_json_ld = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_json_ld:
            self.documents.append("".join(self._parts))
            self._in_json_ld = False
            self._parts = []


class _SameStoreRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(urljoin(req.full_url, newurl))
        if target.scheme != "https" or target.hostname not in _ALLOWED_HOSTS:
            raise HTTPError(newurl, code, "Redirect outside the public Frávega site refused", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _walk_json(value):
    if isinstance(value, dict):
        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(str(item).lower() == "product" for item in types):
            yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _optional_text(value) -> str | None:
    if isinstance(value, dict):
        value = value.get("name")
    if not isinstance(value, (str, int)):
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:_MAX_TEXT_LENGTH] or None


def _first_value(data: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _optional_text(data.get(key))
        if value:
            return value
    return None


def _barcode(data: dict) -> str | None:
    # GTINs must arrive as strings so leading zeroes are preserved. A numeric
    # JSON value has already lost any leading zeroes and is not safe to store.
    for key in ("gtin13", "gtin14", "gtin12", "gtin8", "gtin"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def parse_product_page(html: str, source_url: str, configured_currency: str | None = None) -> ProductSnapshot:
    """Read one unambiguous Product + Offer JSON-LD record from HTML."""
    parser = _ProductPageParser()
    parser.feed(html)
    products = []
    for document in parser.documents:
        try:
            parsed = json.loads(document, parse_float=Decimal)
        except (json.JSONDecodeError, TypeError):
            continue
        products.extend(_walk_json(parsed))

    if len(products) != 1:
        from app.extractors.strategies import parse_html_product
        return parse_html_product(html, source_url, configured_currency=configured_currency)

    product = products[0]
    name = _optional_text(product.get("name"))
    if not name:
        raise ExtractionError("El producto JSON-LD no tiene un nombre utilizable.")
    if len(name) > 250:
        raise ExtractionError("El nombre publicado supera el límite del modelo de producto.")

    offers = product.get("offers")
    if isinstance(offers, list):
        if len(offers) != 1:
            raise ExtractionError("La página contiene varias ofertas; no se elegirá un precio arbitrariamente.")
        offers = offers[0]
    if not isinstance(offers, dict) or offers.get("price") is None:
        raise ExtractionError("La página no publica un precio único en su oferta JSON-LD.")

    try:
        amount = Decimal(str(offers["price"]))
    except (InvalidOperation, ValueError) as exc:
        raise ExtractionError("El precio publicado no es un decimal válido.") from exc
    if not amount.is_finite() or amount <= 0:
        raise ExtractionError("El precio publicado debe ser positivo y finito.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ExtractionError("El precio publicado tiene más de dos decimales significativos.")

    currency = _optional_text(offers.get("priceCurrency"))
    if currency is None or not re.fullmatch(r"[A-Za-z]{3}", currency):
        raise ExtractionError("La oferta no publica una moneda ISO de tres letras.")

    availability_text = str(offers.get("availability") or "").rstrip("/").rsplit("/", 1)[-1]
    availability = {
        "InStock": True,
        "LimitedAvailability": True,
        "OnlineOnly": True,
        "InStoreOnly": True,
        "OutOfStock": False,
        "SoldOut": False,
        "Discontinued": False,
    }.get(availability_text)

    brand = _optional_text(product.get("brand"))
    category = _optional_text(product.get("category"))
    return ProductSnapshot(
        name=name,
        amount=amount,
        currency=currency.upper(),
        source_url=source_url,
        external_id=_first_value(product, ("sku", "productID")),
        barcode=_barcode(product),
        brand=brand,
        model=_optional_text(product.get("model")),
        description=_optional_text(product.get("description")),
        category_name=category,
        is_available=availability,
    )


class FravegaExtractor:
    """Reads only known Frávega ``/p/`` URLs allowed by robots.txt.

    It does not crawl search/category pages, call storefront APIs, use accounts,
    retry denials, or bypass rate limits. Inject ``get_text`` for offline tests.
    """

    name = "Frávega"

    def __init__(
        self,
        *,
        timeout_seconds: float = 15,
        minimum_interval_seconds: float = 1.5,
        get_text: Callable[[str], str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.minimum_interval_seconds = max(0, minimum_interval_seconds)
        self._get_text_override = get_text
        self._sleep = sleep
        self._last_request_at: float | None = None
        self._robots: RobotFileParser | None = None

    def supports(self, store: Store) -> bool:
        parsed = urlsplit(store.base_url)
        return parsed.scheme == "https" and parsed.hostname in _ALLOWED_HOSTS

    @staticmethod
    def validate_product_url(url: str) -> None:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in _ALLOWED_HOSTS
            or not parsed.path.startswith("/p/")
            or parsed.query
            or parsed.fragment
        ):
            raise ExtractionError("Solo se permiten URLs HTTPS públicas de producto Frávega bajo /p/." )

    def _rate_limit(self) -> None:
        now = time.monotonic()
        if self._last_request_at is not None:
            remaining = self.minimum_interval_seconds - (now - self._last_request_at)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at = time.monotonic()

    def _request_text(
        self,
        url: str,
        *,
        allowed_content_types: frozenset[str] = frozenset({"text/html", "application/xhtml+xml"}),
    ) -> str:
        self._rate_limit()
        if self._get_text_override is not None:
            return self._get_text_override(url)

        request = Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "gzip, deflate",
            },
        )
        opener = build_opener(_SameStoreRedirect())
        try:
            with opener.open(request, timeout=self.timeout_seconds) as response:
                content_type = response.headers.get_content_type()
                if content_type not in allowed_content_types:
                    raise ExtractionError("La respuesta pública tiene un tipo de contenido inesperado.")
                body = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            if exc.code == 403:
                raise ExtractionError("BLOCKED: Frávega denegó la solicitud (HTTP 403); no se reintentará.") from exc
            if exc.code == 429:
                raise ExtractionError("RATE_LIMITED: Frávega respondió HTTP 429; no se reintentará.") from exc
            raise ExtractionError(f"La página de producto respondió HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ExtractionError("NETWORK_ERROR: no se pudo leer la página pública de producto.") from exc
        if len(body) > _MAX_RESPONSE_BYTES:
            raise ExtractionError("La respuesta superó el límite local de tamaño.")
        return decode_http_body(
            body,
            content_encoding=response.headers.get("Content-Encoding"),
            charset=response.headers.get_content_charset(),
            max_bytes=_MAX_RESPONSE_BYTES,
        )

    def prepare(self) -> None:
        if self._robots is not None:
            return
        robots_url = "https://www.fravega.com/robots.txt"
        try:
            text = self._request_text(
                robots_url,
                allowed_content_types=frozenset({"text/plain", "text/html"}),
            )
        except Exception as exc:
            raise ExtractionError("No se pudo comprobar robots.txt; se cancela la extracción.") from exc
        parser = RobotFileParser(robots_url)
        parser.parse(text.splitlines())
        crawl_delay = parser.crawl_delay(_USER_AGENT)
        request_rate = parser.request_rate(_USER_AGENT)
        if crawl_delay:
            self.minimum_interval_seconds = max(self.minimum_interval_seconds, crawl_delay)
        if request_rate and request_rate.requests > 0:
            self.minimum_interval_seconds = max(
                self.minimum_interval_seconds,
                request_rate.seconds / request_rate.requests,
            )
        self._robots = parser

    def fetch_allowed_page(self, url: str) -> str:
        """Fetch one known public page only after robots and host validation."""
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS or parsed.query or parsed.fragment:
            raise ExtractionError("Solo se permiten páginas HTTPS públicas del sitio Frávega.")
        self.prepare()
        if not self._robots or not self._robots.can_fetch(_USER_AGENT, url):
            raise ExtractionError("robots.txt no autoriza consultar esta página pública.")
        return self._request_text(url)

    def extract(self, listing: StoreProduct) -> ProductSnapshot:
        self.validate_product_url(listing.product_url)
        self.prepare()
        if not self._robots or not self._robots.can_fetch(_USER_AGENT, listing.product_url):
            raise ExtractionError("robots.txt no autoriza consultar esta URL de producto.")
        html = self._request_text(listing.product_url)
        return parse_product_page(html, listing.product_url, configured_currency=listing.currency)
