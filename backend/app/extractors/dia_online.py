"""Public JSON-LD product-page adapter for Supermercados DIA Online."""

from urllib.parse import urlsplit

from app.extractors.public_store import PublicStoreExtractor
from app.models import Store


class DiaOnlineExtractor(PublicStoreExtractor):
    name = "Dia Online JSON-LD"
    connector_verified = True
    host = "diaonline.supermercadosdia.com.ar"

    def supports(self, store: Store) -> bool:
        parsed = urlsplit(store.base_url)
        return parsed.scheme == "https" and parsed.hostname == self.host
