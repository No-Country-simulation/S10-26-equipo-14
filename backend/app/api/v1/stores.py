from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.management_security import is_development
from app.models import (
    Category,
    ExtractionRun,
    PriceObservation,
    Store,
    StoreIntegration,
    StoreMonitoringCategory,
    StoreMonitoringPreference,
    StoreProduct,
)
from app.schemas.extraction import ExtractionRunOut
from app.schemas.store_management import MonitoringUpdate, StoreCreate, StoreManagementOut
from app.services.store_analysis import analyze_store
from app.extractors import ExtractionError, extractor_for_store
from app.services.extraction import run_store_extraction

router = APIRouter(prefix="/management/stores", tags=["store-management"])
_extraction_guard = Lock()
_running_extractions: set[int] = set()


def _run_output(db: Session, run: ExtractionRun, store: Store,
                observations_created: int | None = None,
                include_diagnostics: bool = True) -> ExtractionRunOut:
    if observations_created is None:
        observations_created = db.scalar(
            select(func.count(PriceObservation.id))
            .join(StoreProduct, StoreProduct.id == PriceObservation.store_product_id)
            .where(StoreProduct.store_id == store.id,
                   PriceObservation.observed_at == run.started_at)
        ) or 0
    return ExtractionRunOut(
        run_id=run.id,
        store_id=store.id,
        store_name=store.name,
        source=run.source if include_diagnostics else "Extracción",
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        records_seen=run.records_seen,
        observations_created=observations_created,
        error_summary=run.error_summary if include_diagnostics else None,
    )


def _management_record(store: Store, integration: StoreIntegration | None,
                       preference: StoreMonitoringPreference | None,
                       category_ids: list[int], latest_run: ExtractionRun | None) -> StoreManagementOut:
    return StoreManagementOut(
        id=store.id,
        name=store.name,
        base_url=store.base_url,
        country=store.country,
        is_active=store.is_active,
        created_at=store.created_at,
        integration_status=integration.status if integration else "pending",
        analyzer_key=integration.analyzer_key if integration else None,
        analysis_message=integration.analysis_message if integration else None,
        analysis_candidates=integration.analysis_candidates or [] if integration else [],
        last_analysis_at=integration.last_analysis_at if integration else None,
        currency=preference.currency if preference else "ARS",
        interval_hours=preference.interval_hours if preference else 24,
        monitoring_enabled=preference.is_enabled if preference else False,
        category_ids=category_ids,
        last_extraction_at=latest_run.finished_at if latest_run else None,
        last_extraction_status=latest_run.status if latest_run else None,
    )


def _records(db: Session) -> list[StoreManagementOut]:
    stores = db.scalars(select(Store).order_by(Store.name, Store.id)).all()
    if not stores:
        return []
    store_ids = [store.id for store in stores]
    integrations = {
        row.store_id: row for row in db.scalars(
            select(StoreIntegration).where(StoreIntegration.store_id.in_(store_ids))
        ).all()
    }
    preferences = {
        row.store_id: row for row in db.scalars(
            select(StoreMonitoringPreference).where(StoreMonitoringPreference.store_id.in_(store_ids))
        ).all()
    }
    selected: dict[int, list[int]] = {store_id: [] for store_id in store_ids}
    for store_id, category_id in db.execute(
        select(StoreMonitoringCategory.store_id, StoreMonitoringCategory.category_id)
        .where(StoreMonitoringCategory.store_id.in_(store_ids))
    ).all():
        selected[store_id].append(category_id)
    latest: dict[int, ExtractionRun] = {}
    for run in db.scalars(
        select(ExtractionRun)
        .where(ExtractionRun.store_id.in_(store_ids), ~ExtractionRun.source.like("analysis:%"))
        .order_by(ExtractionRun.started_at.desc(), ExtractionRun.id.desc())
    ).all():
        if run.store_id not in latest:
            latest[run.store_id] = run
    return [
        _management_record(store, integrations.get(store.id), preferences.get(store.id),
                           selected[store.id], latest.get(store.id))
        for store in stores
    ]


@router.get("", response_model=list[StoreManagementOut])
def list_managed_stores(request: Request, db: Session = Depends(get_db)):
    records = _records(db)
    if is_development(request.app.state.settings):
        return records

    safe_records = []
    for record in records:
        safe_message = record.analysis_message
        if record.integration_status == "error":
            safe_message = "El análisis no pudo completarse; los detalles internos se omiten en el modo público."
        safe_records.append(record.model_copy(update={"analyzer_key": None, "analysis_message": safe_message}))
    return safe_records


@router.post("", response_model=StoreManagementOut, status_code=status.HTTP_201_CREATED)
def create_managed_store(payload: StoreCreate, db: Session = Depends(get_db)):
    base_url = str(payload.base_url).rstrip("/")
    existing = db.scalar(select(Store).where(
        func.lower(Store.name) == payload.name.lower()
    ))
    if existing:
        if existing.base_url.rstrip("/").lower() == base_url.lower():
            return _find_record(db, existing.id)
        raise HTTPException(status_code=409, detail="Ya existe una tienda con ese nombre y otra URL.")
    existing_url = db.scalar(select(Store).where(func.lower(Store.base_url) == base_url.lower()))
    if existing_url:
        raise HTTPException(status_code=409, detail="Ese sitio ya está registrado con otro nombre.")

    store = Store(name=payload.name, base_url=base_url, country=payload.country, is_active=True)
    db.add(store)
    try:
        db.flush()
        integration = StoreIntegration(store_id=store.id, status="pending")
        preference = StoreMonitoringPreference(
            store_id=store.id,
            currency=payload.currency,
            interval_hours=24,
            is_enabled=False,
        )
        db.add_all([integration, preference])
        db.commit()
        db.refresh(store)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo registrar la tienda por un conflicto de datos.") from exc
    return _management_record(store, integration, preference, [], None)


@router.post("/{store_id}/analyze", response_model=StoreManagementOut)
def analyze_managed_store(store_id: int = Path(gt=0), db: Session = Depends(get_db)):
    try:
        analyze_store(db, store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _find_record(db, store_id)


@router.post("/{store_id}/extract", response_model=ExtractionRunOut)
def extract_managed_store(store_id: int = Path(gt=0), db: Session = Depends(get_db)):
    """Run one synchronous extraction; serialize duplicate requests per store."""
    with _extraction_guard:
        if store_id in _running_extractions:
            raise HTTPException(status_code=409, detail="Ya hay una extracción en curso para esta tienda.")
        _running_extractions.add(store_id)
    try:
        store = db.get(Store, store_id)
        if store is None:
            raise HTTPException(status_code=404, detail="Tienda no encontrada.")
        running = db.scalar(select(ExtractionRun.id).where(
            ExtractionRun.store_id == store_id,
            ExtractionRun.status == "running",
        ).limit(1))
        if running is not None:
            raise HTTPException(status_code=409, detail="Ya hay una extracción en curso para esta tienda.")
        try:
            extractor = extractor_for_store(store)
            result = run_store_extraction(db, store_id, extractor)
        except (ExtractionError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        run = db.get(ExtractionRun, result.run_id)
        if run is None:
            raise HTTPException(status_code=500, detail="No se encontró el registro de la extracción.")
        db.refresh(run)
        return _run_output(db, run, store, result.observations_created)
    finally:
        with _extraction_guard:
            _running_extractions.discard(store_id)


@router.get("/{store_id}/extractions", response_model=list[ExtractionRunOut])
def list_store_extractions(
    request: Request,
    store_id: int = Path(gt=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada.")
    runs = db.scalars(
        select(ExtractionRun)
        .where(ExtractionRun.store_id == store_id,
               ~ExtractionRun.source.like("analysis:%"))
        .order_by(ExtractionRun.started_at.desc(), ExtractionRun.id.desc())
        .limit(limit)
    ).all()
    include_diagnostics = is_development(request.app.state.settings)
    return [
        _run_output(db, run, store, include_diagnostics=include_diagnostics)
        for run in runs
    ]


@router.put("/{store_id}/monitoring", response_model=StoreManagementOut)
def update_monitoring(store_id: int, payload: MonitoringUpdate, db: Session = Depends(get_db)):
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada.")
    integration = db.scalar(select(StoreIntegration).where(StoreIntegration.store_id == store_id))
    if integration is None or integration.status not in {"configuration_required", "active"}:
        raise HTTPException(status_code=409, detail="Analiza primero la compatibilidad de esta tienda.")
    matched_categories = {
        candidate.get("category_id")
        for candidate in (integration.analysis_candidates or [])
        if isinstance(candidate, dict) and isinstance(candidate.get("category_id"), int)
    }
    if payload.enabled and not payload.category_ids:
        raise HTTPException(status_code=422, detail="Selecciona al menos una categoría para activar la configuración.")
    if payload.enabled and (integration.analyzer_key is None or not set(payload.category_ids).issubset(matched_categories)):
        raise HTTPException(status_code=422, detail="Solo puedes activar categorías propuestas y reconocidas por el catálogo.")
    categories = db.scalars(select(Category).where(Category.id.in_(payload.category_ids))).all() if payload.category_ids else []
    if len(categories) != len(payload.category_ids):
        raise HTTPException(status_code=422, detail="Una o más categorías ya no existen en el catálogo.")

    preference = db.get(StoreMonitoringPreference, store_id)
    if preference is None:
        preference = StoreMonitoringPreference(store_id=store_id)
        db.add(preference)
        db.flush()
    preference.currency = payload.currency
    preference.interval_hours = payload.interval_hours
    preference.is_enabled = payload.enabled
    preference.updated_at = datetime.now(timezone.utc)
    db.query(StoreMonitoringCategory).filter(StoreMonitoringCategory.store_id == store_id).delete(synchronize_session=False)
    db.add_all(StoreMonitoringCategory(store_id=store_id, category_id=category.id) for category in categories)
    integration.status = "active" if payload.enabled else "configuration_required"
    integration.analysis_message = (
        "Configuración activa. La ejecución programada todavía no está disponible; las extracciones actuales son manuales."
        if payload.enabled
        else "Preferencias guardadas. El monitoreo está desactivado hasta que lo actives."
    )
    integration.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _find_record(db, store_id)


def _find_record(db: Session, store_id: int) -> StoreManagementOut:
    record = next((item for item in _records(db) if item.id == store_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada.")
    return record
