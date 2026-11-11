from app.analyzers.fravega import FravegaAnalyzer
from app.extractors.fravega import FravegaExtractor
from app.models import Category, Store


def test_analyzer_proposes_observed_navigation_labels_and_exact_catalog_matches():
    html = '''<html><nav>
      <a href="/computacion"> Computación </a>
      <a href="/audio">Audio</a>
      <a href="/p/fixture-product">Producto</a>
      <a href="https://outside.example/category">Fuera del sitio</a>
    </nav><a href="/not-in-navigation">No analizar</a></html>'''

    def get_text(url: str) -> str:
        if url.endswith("/robots.txt"):
            return "User-agent: *\nAllow: /\n"
        return html

    analyzer = FravegaAnalyzer(FravegaExtractor(get_text=get_text, minimum_interval_seconds=0))
    store = Store(id=1, name="Tienda de prueba", base_url="https://www.fravega.com", is_active=True)
    categories = [Category(id=3, name="Computación", slug="computacion")]

    result = analyzer.analyze(store, categories)

    assert result.analyzer_key == "fravega-public-navigation-v1"
    assert [(item.name, item.category_id) for item in result.categories] == [
        ("Computación", 3), ("Audio", None),
    ]
    assert all(item.source_url.startswith("https://www.fravega.com/") for item in result.categories)


def test_analyzer_cancels_when_robots_disallow_homepage():
    def get_text(url: str) -> str:
        if url.endswith("/robots.txt"):
            return "User-agent: *\nDisallow: /\n"
        raise AssertionError("No se debe solicitar el homepage denegado")

    analyzer = FravegaAnalyzer(FravegaExtractor(get_text=get_text, minimum_interval_seconds=0))
    store = Store(id=1, name="Tienda de prueba", base_url="https://www.fravega.com", is_active=True)

    try:
        analyzer.analyze(store, [])
    except Exception as error:
        assert "robots.txt" in str(error)
    else:
        raise AssertionError("El análisis debía detenerse ante una regla Disallow")
