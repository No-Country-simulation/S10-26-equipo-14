"""Common contracts for public, robots-aware store analysis."""

from dataclasses import dataclass
from typing import Protocol

from app.models import Category, Store


@dataclass(frozen=True, slots=True)
class CategoryCandidate:
    name: str
    source_url: str
    category_id: int | None


@dataclass(frozen=True, slots=True)
class StoreAnalysisResult:
    analyzer_key: str
    message: str
    categories: tuple[CategoryCandidate, ...]


class StoreAnalyzer(Protocol):
    key: str

    def supports(self, store: Store) -> bool: ...

    def analyze(self, store: Store, known_categories: list[Category]) -> StoreAnalysisResult: ...
