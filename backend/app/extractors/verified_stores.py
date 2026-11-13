"""Named adapters for stores whose public product pages have been verified."""

from urllib.parse import urlsplit

from app.extractors.public_store import PublicStoreExtractor
from app.models import Store


class _VerifiedStructuredStoreExtractor(PublicStoreExtractor):
    connector_verified = True
    hosts: frozenset[str] = frozenset()

    def supports(self, store: Store) -> bool:
        parsed = urlsplit(store.base_url)
        return parsed.scheme == "https" and parsed.hostname in self.hosts


class CetrogarExtractor(_VerifiedStructuredStoreExtractor):
    name = "Cetrogar JSON-LD"
    hosts = frozenset({"cetrogar.com.ar", "www.cetrogar.com.ar"})


class CredicoopExtractor(_VerifiedStructuredStoreExtractor):
    name = "Tienda Credicoop JSON-LD"
    hosts = frozenset({"tiendacredicoop.coop"})


class OnCityExtractor(_VerifiedStructuredStoreExtractor):
    name = "On City JSON-LD"
    hosts = frozenset({"oncity.com", "www.oncity.com"})
