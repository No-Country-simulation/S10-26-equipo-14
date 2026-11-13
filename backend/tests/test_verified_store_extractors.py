import gzip
from decimal import Decimal

import pytest

from app.extractors import (
    CetrogarExtractor,
    CredicoopExtractor,
    ExtractionError,
    OnCityExtractor,
    PublicStoreExtractor,
    extractor_for_store,
)
from app.extractors.http_content import decode_http_body
from app.models import Store, StoreProduct


# Synthetic parser fixture only; it is never inserted into any database.
PRODUCT_PAGE = """
<script type="application/ld+json">
{
  "@type":"Product",
  "name":"Smart TV Samsung 55 QLED 4K",
  "sku":"fixture-tv-55",
  "brand":{"@type":"Brand","name":"Samsung"},
  "category":"Televisores",
  "offers":{"@type":"Offer","price":"899999.00","priceCurrency":"ARS",
             "availability":"https://schema.org/InStock"}
}
</script>
"""


@pytest.mark.parametrize(
    ("extractor_type", "store_name", "host", "product_url"),
    [
        (
            CetrogarExtractor,
            "Cetrogar",
            "www.cetrogar.com.ar",
            "https://www.cetrogar.com.ar/producto/prueba/p",
        ),
        (
            CredicoopExtractor,
            "Tienda Credicoop",
            "tiendacredicoop.coop",
            "https://tiendacredicoop.coop/producto/prueba.html",
        ),
        (
            OnCityExtractor,
            "On City",
            "www.oncity.com",
            "https://www.oncity.com/producto/prueba/p",
        ),
    ],
)
def test_verified_store_adapter_parses_real_page_shape_and_checks_domain(
    extractor_type, store_name, host, product_url
):
    store = Store(name=store_name, base_url=f"https://{host}", country="AR")
    extractor = extractor_type(minimum_interval_seconds=0, get_text=lambda _url: PRODUCT_PAGE)
    listing = StoreProduct(
        store=store,
        store_id=1,
        product_url=product_url,
        product_name="Smart TV Samsung 55 QLED 4K",
        currency="ARS",
    )

    assert extractor.supports(store)
    assert extractor_for_store(store).__class__ is extractor_type
    snapshot = extractor.extract(listing)
    assert snapshot.name == "Smart TV Samsung 55 QLED 4K"
    assert snapshot.amount == Decimal("899999.00")
    assert snapshot.currency == "ARS"
    assert snapshot.source_url == product_url
    assert snapshot.category_name == "Televisores"
    assert snapshot.is_available is True
    assert extractor.connector_verified is True


def test_verified_adapters_do_not_accept_another_stores_domain():
    extractor = CetrogarExtractor(minimum_interval_seconds=0)
    assert not extractor.supports(Store(name="Cetrogar", base_url="https://shop.example"))


def test_generic_parser_remains_unverified_fallback():
    store = Store(name="Tienda desconocida", base_url="https://shop.example")
    extractor = extractor_for_store(store)
    assert isinstance(extractor, PublicStoreExtractor)
    assert not extractor.connector_verified


def test_public_http_gzip_body_is_decoded_with_a_decompressed_size_limit():
    body = gzip.compress(PRODUCT_PAGE.encode("utf-8"))
    decoded = decode_http_body(
        body,
        content_encoding="gzip",
        charset="utf-8",
        max_bytes=10_000,
    )
    assert decoded == PRODUCT_PAGE

    compressed_expansion = gzip.compress(b"x" * 1000)
    with pytest.raises(ExtractionError, match="descomprimida demasiado grande"):
        decode_http_body(
            compressed_expansion,
            content_encoding="gzip",
            charset="utf-8",
            max_bytes=100,
        )


def test_public_http_rejects_unknown_or_invalid_content_encoding():
    with pytest.raises(ExtractionError, match="no admitida"):
        decode_http_body(b"page", content_encoding="br", charset="utf-8", max_bytes=100)
    with pytest.raises(ExtractionError, match="comprimida inv\u00e1lida"):
        decode_http_body(b"not gzip", content_encoding="gzip", charset="utf-8", max_bytes=100)
