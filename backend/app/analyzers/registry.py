from app.analyzers.base import StoreAnalyzer
from app.analyzers.fravega import FravegaAnalyzer
from app.models import Store


def analyzer_for_store(store: Store) -> StoreAnalyzer | None:
    analyzers: tuple[StoreAnalyzer, ...] = (FravegaAnalyzer(),)
    matches = [analyzer for analyzer in analyzers if analyzer.supports(store)]
    return matches[0] if len(matches) == 1 else None
