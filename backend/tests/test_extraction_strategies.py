import pytest
from decimal import Decimal

from app.extractors.base import ExtractionError
from app.extractors.strategies import parse_html_product, parse_price


def test_json_ld_and_aggregate_offer_with_explicit_single_value():
    page = '''<script type="application/ld+json">{"@type":"Product","name":"TV Samsung","offers":{"@type":"Offer","price":"1.234.567,89","priceCurrency":"ARS"}}</script>'''
    result = parse_html_product(page, "https://shop.test/tv")
    assert result.name == "TV Samsung"
    assert str(result.amount) == "1234567.89"
    assert result.currency == "ARS"
    aggregate = '<script type="application/ld+json">{"@type":"Product","name":"TV","offers":{"@type":"AggregateOffer","lowPrice":"80","highPrice":"80","priceCurrency":"ARS"}}</script>'
    assert str(parse_html_product(aggregate, "https://shop.test/tv").amount) == "80"
    ambiguous = aggregate.replace('"highPrice":"80"', '"highPrice":"90"')
    with pytest.raises(ExtractionError): parse_html_product(ambiguous, "https://shop.test/tv")


def test_price_specification_and_unknown_currency():
    page = '<script type="application/ld+json">{"@type":"Product","name":"TV","offers":{"@type":"Offer","priceSpecification":{"@type":"PriceSpecification","price":"75","priceCurrency":"ARS"}}}</script>'
    assert str(parse_html_product(page, "https://shop.test/tv").amount) == "75"
    unknown = page.replace("ARS", "ZZZ")
    with pytest.raises(ExtractionError): parse_html_product(unknown, "https://shop.test/tv")


def test_microdata_and_open_graph_strategies():
    micro = '<div itemscope itemtype="https://schema.org/Product"><span itemprop="name">TV X</span><meta itemprop="price" content="999,50"><meta itemprop="priceCurrency" content="ARS"></div>'
    assert str(parse_html_product(micro, "https://shop.test/tv").amount) == "999.50"
    og = '<meta property="og:title" content="TV Y"><meta property="product:price:amount" content="1234.50"><meta property="product:price:currency" content="USD">'
    assert parse_html_product(og, "https://shop.test/tv").currency == "USD"


def test_configurable_simple_html_selectors():
    html = '<h1 class="product-title">TV por selector</h1><span class="current-price">321.50</span>'
    result = parse_html_product(html, "https://shop.test/tv", "ARS", {
        "name": "h1.product-title", "price": ".current-price",
    })
    assert result.name == "TV por selector"
    assert result.currency == "ARS"


def test_page_blocked_state_is_preserved_without_price():
    from app.extractors.public_store import PublicStoreExtractor
    from app.models import StoreProduct

    def blocked(_url):
        raise ExtractionError("BLOCKED: HTTP 403")

    extractor = PublicStoreExtractor(get_text=blocked, minimum_interval_seconds=0)
    listing = StoreProduct(product_url="https://shop.test/item", product_name="TV", currency="ARS")
    with pytest.raises(ExtractionError, match="BLOCKED"):
        extractor.extract(listing)


def test_next_data_shopify_and_previous_compare_price_ignored():
    next_data = '<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"product":{"@type":"Product","name":"TV Z","offers":{"price":100,"priceCurrency":"ARS"}}}}}</script>'
    assert str(parse_html_product(next_data, "https://shop.test/tv").amount) == "100"
    shopify = '<script type="application/json">{"title":"TV Shopify","variants":[{"price":"250.00","compare_at_price":"300.00","available":true}]}</script>'
    result = parse_html_product(shopify, "https://shop.test/tv", "ARS")
    assert str(result.amount) == "250.00"


def test_rejects_absent_price_currency_and_ambiguous_or_invalid_price():
    with pytest.raises(ExtractionError): parse_html_product('<meta property="og:title" content="TV">', "https://shop.test/tv")
    with pytest.raises(ExtractionError): parse_html_product('<meta property="og:title" content="TV"><meta property="product:price:amount" content="3">', "https://shop.test/tv")
    with pytest.raises(ExtractionError): parse_html_product('<script type="application/ld+json">{"@type":"Product","name":"TV","offers":{"price":10}}</script>', "https://shop.test/tv")


def test_argentine_price_separators_and_nonpositive_values():
    assert parse_price("$ 1.234.567,89") == Decimal("1234567.89")
    assert parse_price("1.234,50") == Decimal("1234.50")
    with pytest.raises(ExtractionError): parse_price("0")


def test_unresolved_template_brand_is_not_persisted_as_product_metadata():
    html = '''<script type="application/ld+json">{"@type":"Product","name":"Samsung QN55Q6FAAG","brand":"$shop.name","offers":{"@type":"Offer","price":"1000.00","priceCurrency":"ARS"}}</script>'''

    snapshot = parse_html_product(html, "https://shop.test/tv")

    assert snapshot.name == "Samsung QN55Q6FAAG"
    assert snapshot.brand is None



def test_invalid_placeholder_offer_does_not_hide_valid_open_graph_price():
    html = """
    <script type="application/ld+json">
      {"@type":"Product","name":"TV placeholder","offers":{"@type":"Offer","price":"","priceCurrency":"ARS"}}
    </script>
    <meta property="og:title" content="TV real">
    <meta property="product:price:amount" content="1.899.999,00">
    <meta property="product:price:currency" content="ARS">
    """
    result = parse_html_product(html, "https://shop.test/tv")
    assert result.name == "TV real"
    assert result.amount == Decimal("1899999.00")
    assert result.currency == "ARS"



def test_expected_listing_name_disambiguates_related_products_on_retail_page():
    html = """
    <script type="application/ld+json">
      [
        {"@type":"Product","name":"Smart TV Samsung QN55Q6FAAGCZB 55 LED 4K","offers":{"@type":"Offer","price":"879999","priceCurrency":"ARS"}},
        {"@type":"Product","name":"Soundbar Samsung HW-Q600C","offers":{"@type":"Offer","price":"299999","priceCurrency":"ARS"}}
      ]
    </script>
    """
    result = parse_html_product(
        html,
        "https://shop.test/tv",
        configured_currency="ARS",
        expected_name="Smart TV Samsung QN55Q6FAAGCZB 55 pulgadas LED 4K",
    )
    assert result.name == "Smart TV Samsung QN55Q6FAAGCZB 55 LED 4K"
    assert result.amount == Decimal("879999")


def test_expected_listing_name_does_not_break_tied_product_prices():
    html = """
    <script type="application/ld+json">
      [
        {"@type":"Product","name":"Smart TV Samsung 55 QLED","offers":{"@type":"Offer","price":"879999","priceCurrency":"ARS"}},
        {"@type":"Product","name":"Smart TV Samsung 55 QLED","offers":{"@type":"Offer","price":"899999","priceCurrency":"ARS"}}
      ]
    </script>
    """
    with pytest.raises(ExtractionError, match="varios precios/productos"):
        parse_html_product(html, "https://shop.test/tv", configured_currency="ARS", expected_name="Smart TV Samsung 55 QLED")
