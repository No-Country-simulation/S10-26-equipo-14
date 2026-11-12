"""Single-page public HTML extractor for registered HTTPS store hosts."""
from __future__ import annotations

import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from app.extractors.base import ExtractionError, ProductSnapshot
from app.extractors.strategies import parse_html_product
from app.models import Store, StoreProduct

_UA = "PriceScopePriceMonitor/0.1 (public product page parser)"
_MAX = 5 * 1024 * 1024


class PublicStoreExtractor:
    name = "Public HTML strategies"

    def __init__(self, *, timeout_seconds: float = 15, minimum_interval_seconds: float = 1.5,
                 get_text=None, sleep=time.sleep, selectors: dict[str, str] | None = None):
        self.timeout_seconds = timeout_seconds
        self.minimum_interval_seconds = max(0, minimum_interval_seconds)
        self._get_text = get_text
        self.selectors = dict(selectors or {})
        self._sleep = sleep
        self._last = 0.0
        self._robots: dict[str, RobotFileParser] = {}
        self.last_http_status: int | None = None
        self.last_content_type: str | None = None

    def supports(self, store: Store) -> bool:
        parsed = urlsplit(store.base_url)
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and parsed.hostname not in {"fravega.com", "www.fravega.com"})

    def prepare(self) -> None:
        return

    def _fetch(self, url: str, host: str, *, robots: bool = False) -> str:
        wait = self.minimum_interval_seconds - (time.monotonic() - self._last)
        if self._last and wait > 0: self._sleep(wait)
        self._last = time.monotonic()
        if self._get_text:
            self.last_http_status = 200
            self.last_content_type = "text/plain" if robots else "text/html"
            return self._get_text(url)
        class SameHost(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                target = urlsplit(urljoin(req.full_url, newurl))
                if target.scheme != "https" or target.hostname != host:
                    raise HTTPError(newurl, code, "Redirect outside registered host refused", headers, fp)
                return super().redirect_request(req, fp, code, msg, headers, newurl)
        try:
            request = Request(url, headers={"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml"})
            with build_opener(SameHost()).open(request, timeout=self.timeout_seconds) as response:
                self.last_http_status = response.status
                self.last_content_type = response.headers.get_content_type()
                allowed = {"text/plain", "text/html"} if robots else {"text/html", "application/xhtml+xml"}
                if self.last_content_type not in allowed:
                    raise ExtractionError("UNSUPPORTED: tipo de contenido no HTML.")
                body = response.read(_MAX + 1)
                if len(body) > _MAX: raise ExtractionError("UNSUPPORTED: respuesta demasiado grande.")
                return body.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        except HTTPError as exc:
            self.last_http_status = exc.code
            self.last_content_type = exc.headers.get_content_type() if exc.headers else None
            if exc.code == 403: raise ExtractionError("BLOCKED: HTTP 403; no se reintentará.") from exc
            if exc.code == 429: raise ExtractionError("RATE_LIMITED: HTTP 429; no se reintentará.") from exc
            raise ExtractionError(f"UNSUPPORTED: HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ExtractionError("NETWORK_ERROR: no se pudo leer la página pública.") from exc

    def _allowed(self, url: str, host: str) -> bool:
        robots = self._robots.get(host)
        if robots is None:
            robots_url = f"https://{host}/robots.txt"
            try:
                content = self._fetch(robots_url, host, robots=True)
            except Exception as exc:
                # Cannot safely determine permissions; fail closed.
                raise ExtractionError("BLOCKED: no se pudo comprobar robots.txt.") from exc
            robots = RobotFileParser(robots_url); robots.parse(content.splitlines()); self._robots[host] = robots
        return robots.can_fetch(_UA, url)

    def extract(self, listing: StoreProduct) -> ProductSnapshot:
        parsed = urlsplit(listing.product_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ExtractionError("UNSUPPORTED: se requiere URL HTTPS pública.")
        host = parsed.hostname
        if not self._allowed(listing.product_url, host):
            raise ExtractionError("BLOCKED: robots.txt no autoriza esta página.")
        html = self._fetch(listing.product_url, host)
        return parse_html_product(html, listing.product_url, configured_currency=listing.currency,
                                  selectors=self.selectors)
