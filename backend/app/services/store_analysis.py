"""Run bounded public analysis and persist an audit record."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analyzers import analyzer_for_store
from app.models import Category, ExtractionRun, Store, StoreIntegration


def analyze_store(session: Session, store_id: int) -> tuple[StoreIntegration, ExtractionRun]:
    store = session.get(Store, store_id)
    if store is None:
        raise ValueError(f"No existe la tienda con id {store_id}.")
    integration = session.scalar(select(StoreIntegration).where(StoreIntegration.store_id == store_id))
    if integration is None:
        integration = StoreIntegration(store_id=store_id)
        session.add(integration)
        session.flush()

    analyzer = analyzer_for_store(store)
    source = f"analysis:{analyzer.key if analyzer else 'unsupported'}"[:100]
    started_at = datetime.now(timezone.utc)
    integration.status = "analyzing"
    integration.analysis_message = "Revisando recursos públicos permitidos."
    run = ExtractionRun(source=source, store_id=store.id, status="running", started_at=started_at)
    session.add(run)
    session.commit()
    session.refresh(integration)

    try:
        if analyzer is None:
            integration.analyzer_key = None
            integration.status = "configuration_required"
            integration.analysis_candidates = []
            integration.analysis_message = "Todavía no hay un analizador compatible con este sitio. Se requiere configurar una integración específica."
            run.status = "failed"
            run.error_summary = integration.analysis_message
            run.records_seen = 0
        else:
            categories = session.scalars(select(Category).order_by(Category.name)).all()
            result = analyzer.analyze(store, categories)
            integration.analyzer_key = result.analyzer_key
            integration.analysis_candidates = [
                {"name": item.name, "source_url": item.source_url, "category_id": item.category_id}
                for item in result.categories
            ]
            integration.status = "configuration_required"
            integration.analysis_message = result.message
            run.status = "succeeded"
            run.records_seen = len(result.categories)
    except Exception as exc:
        session.rollback()
        integration = session.scalar(select(StoreIntegration).where(StoreIntegration.store_id == store_id))
        run = session.get(ExtractionRun, run.id)
        if integration is None or run is None:
            raise RuntimeError("No se pudo recuperar el registro del análisis.") from exc
        integration.status = "error"
        integration.analysis_message = f"El análisis no pudo completarse: {str(exc)[:3500]}"
        integration.analysis_candidates = []
        run.status = "failed"
        run.error_summary = integration.analysis_message
        run.records_seen = 0
    finally:
        integration.last_analysis_at = datetime.now(timezone.utc)
        integration.updated_at = datetime.now(timezone.utc)
        run.finished_at = datetime.now(timezone.utc)
        session.commit()

    session.refresh(integration)
    session.refresh(run)
    return integration, run
