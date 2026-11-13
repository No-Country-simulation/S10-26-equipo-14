"""Reusable, conservative parsers for public product page markup."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser

from app.core.currency import is_supported_iso_currency
from app.extractors.base import ExtractionError, ProductSnapshot


@dataclass(frozen=True)
class PageSignals:
    json_documents: tuple[str, ...]
    meta: dict[str, str]
    itemprops: dict[str, str]
    tags: dict[str, str]


class _Signals(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.json_documents: list[str] = []
        self.meta: dict[str, str] = {}
        self.itemprops: dict[str, str] = {}
        self.tags: dict[str, str] = {}
        self.capture: str | None = None
        self.parts: list[str] = []
        self._json = False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): v for k, v in attrs if v is not None}
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            value = a.get("content", "")
            if key and value: self.meta[key] = value
        if "itemprop" in a and (a.get("content") or a.get("value")):
            self.itemprops[a["itemprop"].lower()] = a.get("content") or a.get("value") or ""
        if "property" in a:
            self.itemprops[a["property"].lower()] = a.get("content") or ""
        for attr, key in (("data-product-json", "product"), ("data-product", "product")):
            if attr in a: self.json_documents.append(a[attr])
        if tag == "script":
            typ = a.get("type", "").split(";", 1)[0].lower()
            self._json = typ in {"application/ld+json", "application/json"} or a.get("id") == "__NEXT_DATA__"
            self.capture = "script" if self._json else None
            self.parts = []
        elif tag in {"meta", "link"}: return
        elif "itemprop" in a and a.get("itemprop", "").lower() in {"name", "price", "pricecurrency", "sku", "availability", "brand"}:
            self.capture = "item:" + a["itemprop"].lower()
            self.parts = []
        if a.get("itemtype", "").lower().endswith("/product") or a.get("itemscope") is not None:
            self.tags["product_scope"] = "1"

    def handle_data(self, data):
        if self.capture: self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.capture == "script":
            self.json_documents.append("".join(self.parts)); self.capture = None; self.parts = []
        elif self.capture and self.capture.startswith("item:"):
            key = self.capture[5:]
            self.itemprops.setdefault(key, "".join(self.parts).strip())
            self.capture = None; self.parts = []


class _ConfiguredSelector(HTMLParser):
    """Small dependency-free selector support: tag, #id, .class, [attr=value]."""
    def __init__(self, selector: str):
        super().__init__(convert_charrefs=True)
        self.selector = selector.strip()
        self.matches: list[str] = []
        self.active: list[tuple[str, list[str]]] = []

    def _matches(self, tag: str, attrs: dict[str, str]) -> bool:
        s = self.selector
        if s.startswith("#"): return attrs.get("id") == s[1:]
        if s.startswith("."): return s[1:] in attrs.get("class", "").split()
        compound = re.fullmatch(r"([\w-]+)([.#])([\w-]+)", s)
        if compound:
            wanted_tag, marker, value = compound.groups()
            return tag == wanted_tag and (attrs.get("id") == value if marker == "#" else value in attrs.get("class", "").split())
        attr = re.fullmatch(r"([\w-]+)?\[([\w-]+)(?:=['\"]?([^'\"]+)['\"]?)?\]", s)
        if attr:
            tag_name, key, value = attr.groups()
            return (not tag_name or tag == tag_name) and key in attrs and (value is None or attrs[key] == value)
        return tag == s

    def handle_starttag(self, tag, attrs):
        values = {k.lower(): v or "" for k, v in attrs}
        if self._matches(tag, values):
            immediate = values.get("content") or values.get("value") or values.get("data-price") or ""
            if immediate: self.matches.append(immediate.strip())
            else: self.active.append((tag, []))

    def handle_data(self, data):
        for _tag, parts in self.active: parts.append(data)

    def handle_endtag(self, tag):
        for i in range(len(self.active) - 1, -1, -1):
            if self.active[i][0] == tag:
                _name, parts = self.active.pop(i)
                value = re.sub(r"\s+", " ", " ".join(parts)).strip()
                if value: self.matches.append(value)
                break


def page_signals(html: str) -> PageSignals:
    parser = _Signals(); parser.feed(html)
    return PageSignals(tuple(parser.json_documents), parser.meta, parser.itemprops, parser.tags)


def _walk(value):
    if isinstance(value, dict):
        yield value
        for v in value.values(): yield from _walk(v)
    elif isinstance(value, list):
        for v in value: yield from _walk(v)


def _text(value):
    if isinstance(value, dict): value = value.get("name")
    if isinstance(value, (str, int, float, Decimal)):
        val = re.sub(r"\s+", " ", str(value)).strip()
        return val or None
    return None


def parse_price(value) -> Decimal:
    if isinstance(value, Decimal): d = value
    elif isinstance(value, (int, float)): d = Decimal(str(value))
    elif isinstance(value, str):
        raw = value.strip().replace("\u00a0", " ")
        # Locale-aware Argentine formats: 1.234.567,89 and 1234,56.
        raw = re.sub(r"[^\d.,+-]", "", raw)
        if "," in raw and "." in raw: raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw: raw = raw.replace(",", ".")
        elif raw.count(".") > 1: raw = raw.replace(".", "")
        try: d = Decimal(raw)
        except InvalidOperation as exc: raise ExtractionError("Precio no válido.") from exc
    else: raise ExtractionError("Precio ausente o no numérico.")
    if not d.is_finite() or d <= 0: raise ExtractionError("El precio debe ser positivo y finito.")
    return d


def _snapshot(name, amount, currency, url, data=None, availability=None):
    name = _text(name)
    if not name: raise ExtractionError("No se identificó producto.")
    currency = _text(currency)
    if not is_supported_iso_currency(currency):
        raise ExtractionError("UNSUPPORTED: moneda desconocida o ISO 4217 no admitida.")
    data = data or {}
    avail = str(availability or "").rstrip("/").rsplit("/", 1)[-1]
    available = True if avail in {"InStock", "LimitedAvailability", "OnlineOnly"} else False if avail in {"OutOfStock", "SoldOut"} else None
    brand = _text(data.get("brand"))
    # Ignore unresolved template variables instead of persisting them as
    # observed catalog metadata (for example, "$shop.name").
    if brand and ("$" in brand or "{{" in brand or "}}" in brand):
        brand = None
    return ProductSnapshot(name, parse_price(amount), currency.upper(), url,
        external_id=_text(data.get("sku") or data.get("productID")),
        brand=brand, model=_text(data.get("model")),
        category_name=_text(data.get("category")), is_available=available)


def _offers(obj):
    offers = obj.get("offers")
    if isinstance(offers, dict): return [offers]
    if isinstance(offers, list): return offers
    return []


def _offer_price(offer):
    typ = offer.get("@type", "")
    types = {typ.lower()} if isinstance(typ, str) else {str(t).lower() for t in typ}
    if any(t.endswith("aggregateoffer") for t in types):
        low, high = offer.get("lowPrice"), offer.get("highPrice")
        return low if low is not None and high is not None and str(low) == str(high) else None
    if offer.get("price") is not None:
        return offer["price"]
    spec = offer.get("priceSpecification")
    if isinstance(spec, list):
        spec = spec[0] if len(spec) == 1 else None
    return spec.get("price") if isinstance(spec, dict) else None


def _offer_currency(offer, product):
    currency = offer.get("priceCurrency") or product.get("priceCurrency")
    spec = offer.get("priceSpecification")
    if isinstance(spec, dict): currency = currency or spec.get("priceCurrency")
    return currency


def parse_html_product(html: str, url: str, configured_currency: str | None = None,
                       selectors: dict[str, str] | None = None,
                       expected_name: str | None = None) -> ProductSnapshot:
    sig = page_signals(html)
    candidates: list[tuple[ProductSnapshot, str]] = []

    def add(snapshot_factory, format_name: str) -> None:
        # Retail sites often publish placeholder/empty offers alongside valid
        # product metadata. Ignore only the invalid candidate; keep validating
        # the remaining evidence and reject pages with no unambiguous price.
        try:
            candidates.append((snapshot_factory(), format_name))
        except ExtractionError:
            return
    for raw in sig.json_documents:
        try: root = json.loads(raw)
        except (ValueError, TypeError): continue
        # Next data and Shopify product JSON commonly wrap a product in arbitrary state.
        for obj in _walk(root):
            types = obj.get("@type", [])
            if isinstance(types, str): types = [types]
            if any(str(t).lower().endswith("product") for t in types):
                for offer in _offers(obj):
                    price = _offer_price(offer)
                    if price is not None:
                        add(lambda: _snapshot(obj.get("name"), price, _offer_currency(offer, obj), url, obj, offer.get("availability")), "jsonld_product_offer")
            # Shopify product JSON shape; ignore compare-at (previous) prices.
            if isinstance(obj.get("variants"), list) and obj.get("title"):
                variants = [v for v in obj["variants"] if isinstance(v, dict) and v.get("available", True) and v.get("price")]
                prices = {str(v["price"]) for v in variants}
                if len(prices) == 1:
                    add(lambda: _snapshot(obj["title"], variants[0]["price"], configured_currency, url,
                                  {"sku": variants[0].get("sku"), "brand": obj.get("vendor")},
                                  "InStock"), "shopify_product_json")
            # Plain embedded product state (e.g. Next/Apollo); requires unambiguous name+current price+currency.
            if obj.get("name") and (obj.get("price") or obj.get("currentPrice")) and (obj.get("priceCurrency") or configured_currency):
                add(lambda: _snapshot(obj["name"], obj.get("price") or obj.get("currentPrice"), obj.get("priceCurrency") or configured_currency, url, obj), "embedded_product_json")
    if not candidates:
        m = sig.meta
        name = m.get("og:title") or m.get("product: name") or m.get("product:name")
        price = m.get("product:price:amount") or m.get("og:price:amount")
        currency = m.get("product:price:currency") or m.get("og:price:currency") or configured_currency
        if name and price and currency: add(lambda: _snapshot(name, price, currency, url), "open_graph_product_metadata")
    ip = sig.itemprops
    if ip.get("name") and ip.get("price") and (ip.get("pricecurrency") or configured_currency):
        add(lambda: _snapshot(ip["name"], ip["price"], ip.get("pricecurrency") or configured_currency, url, ip, ip.get("availability")), "microdata_rdfa")
    if selectors:
        selected = {}
        for field, selector in selectors.items():
            if field not in {"name", "price", "currency"}: continue
            parser = _ConfiguredSelector(selector); parser.feed(html)
            values = list(dict.fromkeys(parser.matches))
            if len(values) == 1: selected[field] = values[0]
        if selected.get("name") and selected.get("price") and (selected.get("currency") or configured_currency):
            add(lambda: _snapshot(selected["name"], selected["price"], selected.get("currency") or configured_currency, url), "configured_html_selectors")
    # Exact duplicate strategies can see the same markup; deduplicate by evidence tuple.
    unique = {}
    for candidate, format_name in candidates:
        unique.setdefault((candidate.name, candidate.amount, candidate.currency), (candidate, format_name))
    if expected_name and len(unique) > 1:
        expected_tokens = set(re.findall(r"[a-z0-9]+", expected_name.casefold()))
        if expected_tokens:
            scored = []
            for key, value in unique.items():
                candidate_tokens = set(re.findall(r"[a-z0-9]+", value[0].name.casefold()))
                score = len(expected_tokens & candidate_tokens) / max(len(expected_tokens), len(candidate_tokens), 1)
                scored.append((score, key, value))
            best_score = max(score for score, _key, _value in scored)
            # Use the registered listing name only when it strongly and uniquely
            # identifies the page's primary product; never guess between ties.
            if best_score >= 0.70:
                unique = {key: value for score, key, value in scored if score == best_score}
    if not unique: raise ExtractionError("PRICE_NOT_FOUND: sin evidencia estructurada suficiente.")
    if len(unique) != 1: raise ExtractionError("Hay varios precios/productos candidatos; no se eligió uno arbitrariamente.")
    snapshot, format_name = next(iter(unique.values()))
    return replace(snapshot, extraction_format=format_name)
