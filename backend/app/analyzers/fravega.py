"""Conservative navigation analysis for known public Frávega homepages."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from app.analyzers.base import CategoryCandidate, StoreAnalysisResult
from app.extractors.fravega import FravegaExtractor
from app.models import Category, Store


class _NavigationLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.nav_depth = 0
        self.current_href: str | None = None
        self.current_text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs}
        if tag.lower() == "nav":
            self.nav_depth += 1
        elif tag.lower() == "a" and self.nav_depth and values.get("href"):
            self.current_href = values["href"]
            self.current_text = []

    def handle_data(self, data: str) -> None:
        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.current_href is not None:
            label = re.sub(r"\s+", " ", " ".join(self.current_text)).strip()
            if label:
                self.links.append((label[:120], self.current_href))
            self.current_href = None
            self.current_text = []
        elif tag.lower() == "nav" and self.nav_depth:
            self.nav_depth -= 1


class FravegaAnalyzer:
    key = "fravega-public-navigation-v1"

    def __init__(self, fetcher: FravegaExtractor | None = None) -> None:
        self.fetcher = fetcher or FravegaExtractor()

    def supports(self, store: Store) -> bool:
        return self.fetcher.supports(store)

    def analyze(self, store: Store, known_categories: list[Category]) -> StoreAnalysisResult:
        homepage = store.base_url.rstrip("/") + "/"
        html = self.fetcher.fetch_allowed_page(homepage)
        parser = _NavigationLinks()
        parser.feed(html)
        known = {category.name.strip().casefold(): category.id for category in known_categories}
        candidates: list[CategoryCandidate] = []
        seen: set[tuple[str, str]] = set()
        for label, raw_url in parser.links:
            url = urljoin(homepage, raw_url)
            parsed = urlsplit(url)
            if (
                parsed.scheme != "https"
                or parsed.hostname not in {"fravega.com", "www.fravega.com"}
                or parsed.path == "/"
                or parsed.path.startswith("/p/")
                or parsed.query
                or parsed.fragment
            ):
                continue
            identity = (label.casefold(), url)
            if identity in seen:
                continue
            seen.add(identity)
            candidates.append(CategoryCandidate(
                name=label,
                source_url=url,
                category_id=known.get(label.casefold()),
            ))
            if len(candidates) == 50:
                break
        message = (
            "Se encontraron enlaces en la navegación pública. Revisa cada propuesta; solo las categorías que coincidan con el catálogo se pueden monitorear."
            if candidates
            else "La página no expuso categorías identificables en su navegación pública. Se requiere configuración manual."
        )
        return StoreAnalysisResult(self.key, message, tuple(candidates))
