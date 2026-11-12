import pytest

from app.extractors import ExtractionError, FravegaExtractor
from app.extractors.fravega import parse_product_page
from app.models import Store, StoreProduct


# This fixture price is synthetic test input, not a current Frávega price.
SYNTHETIC_PRODUCT_PAGE = """
<html><head><script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Producto ficticio de prueba",
  "sku": "fixture-sku-42",
  "gtin13": "7790000000042",
  "brand": {"@type": "Brand", "name": "Marca de prueba"},
  "model": "MODELO-FICTICIO",
  "category": "Categoría sintética",
  "offers": {
    "@type": "Offer",
    "price": 12345.67,
    "priceCurrency": "ARS",
    "availability": "https://schema.org/InStock"
  }
}
</script></head><body></body></html>
"""


def test_parses_product_json_ld_with_decimal_and_source_url():
    url = "https://www.fravega.com/p/producto-ficticio-42/"
    result = parse_product_page(SYNTHETIC_PRODUCT_PAGE, url)

    assert result.name == "Producto ficticio de prueba"
    assert str(result.amount) == "12345.67"
    assert result.currency == "ARS"
    assert result.external_id == "fixture-sku-42"
    assert result.barcode == "7790000000042"
    assert result.brand == "Marca de prueba"
    assert result.category_name == "Categoría sintética"
    assert result.is_available is True
    assert result.source_url == url


def test_rejects_ambiguous_or_invalid_offers():
    ambiguous = SYNTHETIC_PRODUCT_PAGE.replace(
        '"offers": {\n'
        '    "@type": "Offer",\n'
        '    "price": 12345.67,\n'
        '    "priceCurrency": "ARS",\n'
        '    "availability": "https://schema.org/InStock"\n'
        '  }',
        '"offers": [{"price": "10.00", "priceCurrency": "ARS"}, '
        '{"price": "11.00", "priceCurrency": "ARS"}]',
    )
    with pytest.raises(ExtractionError, match="varias ofertas"):
        parse_product_page(ambiguous, "https://www.fravega.com/p/ficticio/")

    no_price = SYNTHETIC_PRODUCT_PAGE.replace('"price": 12345.67,', '"price": null,')
    with pytest.raises(ExtractionError, match="no publica un precio único"):
        parse_product_page(no_price, "https://www.fravega.com/p/ficticio/")


def test_only_supports_https_fravega_stores_and_product_paths():
    extractor = FravegaExtractor(minimum_interval_seconds=0)
    assert extractor.supports(Store(name="Frávega", base_url="https://www.fravega.com"))
    assert not extractor.supports(Store(name="Otra", base_url="https://example.com"))
    with pytest.raises(ExtractionError, match="Solo se permiten"):
        extractor.validate_product_url("https://www.fravega.com/Busca/?query=test")


def test_checks_robots_before_fetching_listing_page():
    product_url = "https://www.fravega.com/p/producto-ficticio-42/"
    requests = []

    def fake_get(url: str) -> str:
        requests.append(url)
        if url.endswith("/robots.txt"):
            return "User-agent: *\nDisallow: /p/"
        return SYNTHETIC_PRODUCT_PAGE

    extractor = FravegaExtractor(
        minimum_interval_seconds=0,
        get_text=fake_get,
        sleep=lambda _seconds: None,
    )
    listing = StoreProduct(
        store_id=1,
        product_url=product_url,
        product_name="Producto ficticio de prueba",
    )

    with pytest.raises(ExtractionError, match="robots.txt no autoriza"):
        extractor.extract(listing)
    assert requests == ["https://www.fravega.com/robots.txt"]


def test_extracts_only_after_robots_allows_known_product_url():
    product_url = "https://www.fravega.com/p/producto-ficticio-42/"

    def fake_get(url: str) -> str:
        if url.endswith("/robots.txt"):
            return "User-agent: *\nDisallow: /Busca/\n"
        return SYNTHETIC_PRODUCT_PAGE

    extractor = FravegaExtractor(
        minimum_interval_seconds=0,
        get_text=fake_get,
        sleep=lambda _seconds: None,
    )
    listing = StoreProduct(
        store_id=1,
        product_url=product_url,
        product_name="Producto ficticio de prueba",
    )
    assert str(extractor.extract(listing).amount) == "12345.67"
