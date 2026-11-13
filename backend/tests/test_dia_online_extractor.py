from app.extractors import DiaOnlineExtractor, extractor_for_store
from app.models import Store, StoreProduct


PRODUCT_URL = "https://diaonline.supermercadosdia.com.ar/snack-tasty-bite-carne-pedigree-40-gr-314778/p"
PRODUCT_JSON_LD = """<script type="application/ld+json">
{
  "@type":"Product",
  "name":"Snack Tasty Bite Carne Pedigree 40 Gr.",
  "brand":{"@type":"Brand","name":"PEDIGREE"},
  "sku":"00314778",
  "offers":{"@type":"AggregateOffer","lowPrice":925,"highPrice":925,
    "priceCurrency":"ARS","offers":[{"@type":"Offer","price":925,
      "priceCurrency":"ARS","availability":"http://schema.org/InStock"}]}
}
</script>"""


def test_dia_online_is_selected_only_for_its_https_host():
    adapter = extractor_for_store(Store(name="Dia Online", base_url="https://diaonline.supermercadosdia.com.ar"))
    assert isinstance(adapter, DiaOnlineExtractor)
    assert adapter.connector_verified is True
    assert not adapter.supports(Store(name="Dia Online", base_url="http://diaonline.supermercadosdia.com.ar"))
    assert not adapter.supports(Store(name="Dia Online", base_url="https://example.com"))


def test_dia_online_extracts_one_aggregate_jsonld_offer_after_robots_allows_it():
    requests = []

    def get_text(url: str) -> str:
        requests.append(url)
        if url.endswith("/robots.txt"):
            return "User-agent: *\nDisallow: /busca/\n"
        return PRODUCT_JSON_LD

    store = Store(name="Dia Online", base_url="https://diaonline.supermercadosdia.com.ar")
    listing = StoreProduct(store=store, product_url=PRODUCT_URL,
                           product_name="Snack Tasty Bite Carne Pedigree 40 Gr.", currency="ARS")
    extractor = DiaOnlineExtractor(minimum_interval_seconds=0, get_text=get_text,
                                   sleep=lambda _seconds: None)

    snapshot = extractor.extract(listing)

    assert snapshot.name == "Snack Tasty Bite Carne Pedigree 40 Gr."
    assert str(snapshot.amount) == "925"
    assert snapshot.currency == "ARS"
    assert snapshot.external_id == "00314778"
    assert snapshot.source_url == PRODUCT_URL
    assert requests == ["https://diaonline.supermercadosdia.com.ar/robots.txt", PRODUCT_URL]
