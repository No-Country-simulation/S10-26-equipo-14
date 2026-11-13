from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.management_security import admin_token_matches, is_development, require_admin_api_token
from app.models import (
    Category,
    ExtractionRun,
    PriceObservation,
    Product,
    Store,
    StoreIntegration,
    StoreMonitoringCategory,
    StoreMonitoringPreference,
    StoreProduct,
)
from app.schemas.extraction import ExtractionRunOut
from app.schemas.catalog import ManagedStoreProductCreate, StoreProductOut
from app.schemas.market import PriceObservationOut
from app.schemas.store_management import MonitoringUpdate, StoreCreate, StoreManagementOut
from app.services.store_analysis import analyze_store
from app.extractors import ExtractionError, extractor_for_store
from app.extractors.fravega import FravegaExtractor
from app.extractors.public_store import PublicStoreExtractor
from app.services.extraction import run_store_extraction

router = APIRouter(prefix="/management/stores", tags=["store-management"])
_extraction_guard = Lock()
_running_extractions: set[int] = set()


@contextmanager
def _database_extraction_lock(db: Session, store_id: int):
    """Hold a DB-level lock across extraction, independently of session commits."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        yield True
        return
    with bind.connect() as connection:
        transaction = connection.begin()
        try:
            lock_id = 0x5052494353434F50 ^ store_id
            acquired = bool(connection.execute(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": lock_id},
            ).scalar_one())
            yield acquired
        finally:
            transaction.rollback()


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


def _coverage_fields(db: Session, store: Store, latest_run: ExtractionRun | None,
                     has_listings: bool) -> dict[str, object]:
    connector_name = None
    connector_verified = False
    try:
        extractor = extractor_for_store(store)
        connector_name = extractor.name
        # The generic HTTPS parser is a fallback strategy, not proof of a
        # store-specific connector. Only named adapters can be enabled here.
        connector_verified = not isinstance(extractor, PublicStoreExtractor)
    except ExtractionError:
        pass

    connector_available = connector_verified
    connector_configured = connector_available and has_listings and store.is_active
    observations_created = 0
    if latest_run is not None and latest_run.status == "SUCCESS":
        observations_created = db.scalar(
            select(func.count(PriceObservation.id))
            .join(StoreProduct, StoreProduct.id == PriceObservation.store_product_id)
            .join(Store, Store.id == StoreProduct.store_id)
            .outerjoin(Product, Product.id == StoreProduct.product_id)
            .where(StoreProduct.store_id == store.id,
                   PriceObservation.observed_at == latest_run.started_at,
                   PriceObservation.is_available.is_not(False),
                   ~Store.name.like("DEMO PriceScope %"),
                   ~StoreProduct.product_name.like("DEMO PriceScope %"),
                   (Product.id.is_(None) | ~Product.name.like("DEMO PriceScope %")))
        ) or 0
    is_operational = connector_configured and observations_created > 0

    if not store.is_active:
        coverage_status = "inactive"
    elif connector_name is None:
        coverage_status = "no_connector"
    elif not connector_verified:
        coverage_status = "connector_unverified"
    elif not has_listings:
        coverage_status = "no_listings"
    elif latest_run is None:
        coverage_status = "pending"
    elif latest_run.status == "running":
        coverage_status = "running"
    elif latest_run.status == "PARTIAL_SUCCESS":
        coverage_status = "partial"
    elif latest_run.status != "SUCCESS":
        coverage_status = "failed"
    elif observations_created == 0:
        coverage_status = "no_data"
    else:
        coverage_status = "operational"

    if not store.is_active:
        disabled_reason = "La tienda está inactiva."
    elif connector_name is None:
        disabled_reason = "Pendiente de integración: no hay un conector compatible implementado."
    elif not connector_verified:
        disabled_reason = "El parser HTML genérico no verifica una integración funcional para este comercio."
    elif not has_listings:
        disabled_reason = "Agrega una publicación de producto para configurar la extracción."
    else:
        disabled_reason = None

    return {
        "connector_available": connector_available,
        "connector_name": connector_name,
        "connector_configured": connector_configured,
        "is_operational": is_operational,
        "coverage_status": coverage_status,
        "operational_at": latest_run.finished_at if is_operational else None,
        "extraction_disabled_reason": disabled_reason,
    }


def _management_record(store: Store, integration: StoreIntegration | None,
                       preference: StoreMonitoringPreference | None,
                       category_ids: list[int], latest_run: ExtractionRun | None,
                       coverage: dict[str, object]) -> StoreManagementOut:
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
        **coverage,
    )


def _records(db: Session) -> list[StoreManagementOut]:
    stores = db.scalars(select(Store).order_by(Store.name, Store.id)).all()
    if not stores:
        return []
    store_ids = [store.id for store in stores]
    stores_with_listings: set[int] = set()
    stores_by_id = {store.id: store for store in stores}
    for listing in db.scalars(
        select(StoreProduct).where(StoreProduct.store_id.in_(store_ids))
    ).all():
        store = stores_by_id[listing.store_id]
        try:
            _validate_listing_url(store, listing.product_url)
        except HTTPException:
            continue
        stores_with_listings.add(store.id)
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
        _management_record(
            store, integrations.get(store.id), preferences.get(store.id),
            selected[store.id], latest.get(store.id),
            _coverage_fields(db, store, latest.get(store.id), store.id in stores_with_listings),
        )
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


@router.post("", response_model=StoreManagementOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin_api_token)])
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
    return _find_record(db, store.id)


def _canonical_host(host: str | None) -> str:
    value = (host or "").lower().rstrip(".")
    return value[4:] if value.startswith("www.") else value


def _validate_listing_url(store: Store, product_url: str) -> None:
    base = urlsplit(store.base_url)
    page = urlsplit(product_url)
    supported_domains = ("carrefour.com.ar", "fravega.com")
    retailer_host = _canonical_host(base.hostname)
    product_host = _canonical_host(page.hostname)
    blocked_path = any(
        page.path.casefold().startswith(prefix)
        for prefix in ("/busca", "/buscapagina", "/account", "/login", "/checkout", "/quick-view", "/espiar")
    )
    if (
        page.scheme != "https"
        or page.username is not None
        or page.password is not None
        or page.port not in (None, 443)
        or page.query
        or page.fragment
        or page.path in {"", "/"}
        or blocked_path
        or (product_host == "fravega.com" and not page.path.startswith("/p/"))
        or product_host != retailer_host
        or not any(retailer_host == domain or retailer_host.endswith(f".{domain}") for domain in supported_domains)
    ):
        raise HTTPException(
            status_code=422,
            detail="La publicación debe ser una URL de producto HTTPS del mismo dominio de Carrefour Argentina o Frávega.",
        )


@router.get("/{store_id}/store-products", response_model=list[StoreProductOut])
def list_managed_store_products(store_id: int = Path(gt=0), db: Session = Depends(get_db)):
    if db.get(Store, store_id) is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada.")
    rows = db.execute(
        select(StoreProduct, Product)
        .outerjoin(Product, Product.id == StoreProduct.product_id)
        .where(StoreProduct.store_id == store_id)
        .order_by(StoreProduct.id)
    ).all()
    from app.api.v1.router import _store_product_payload
    return [_store_product_payload(listing, product) for listing, product in rows]


@router.post("/{store_id}/store-products", response_model=StoreProductOut,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin_api_token)])
def create_managed_store_product(
    payload: ManagedStoreProductCreate,
    store_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada.")
    if not store.is_active:
        raise HTTPException(status_code=409, detail="La tienda está inactiva.")
    product_url = str(payload.product_url)
    _validate_listing_url(store, product_url)
    try:
        extractor_for_store(store)
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if payload.product_id is not None and db.get(Product, payload.product_id) is None:
        raise HTTPException(status_code=422, detail="El producto canónico indicado no existe.")
    if payload.category_id is not None and db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=422, detail="La categoría indicada no existe.")
    existing = db.scalar(select(StoreProduct.id).where(
        StoreProduct.store_id == store_id,
        StoreProduct.product_url == product_url,
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail="La URL ya está registrada para esta tienda.")
    listing = StoreProduct(
        store_id=store_id,
        product_id=payload.product_id,
        category_id=payload.category_id,
        external_id=payload.external_id,
        product_url=product_url,
        product_name=payload.product_name,
        currency=payload.currency,
    )
    db.add(listing)
    try:
        db.commit()
        db.refresh(listing)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo registrar la publicación por un conflicto de datos.") from exc
    from app.api.v1.router import _store_product_payload
    return _store_product_payload(listing, db.get(Product, listing.product_id) if listing.product_id else None)


@router.post("/{store_id}/analyze", response_model=StoreManagementOut,
             dependencies=[Depends(require_admin_api_token)])
def analyze_managed_store(store_id: int = Path(gt=0), db: Session = Depends(get_db)):
    try:
        analyze_store(db, store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _find_record(db, store_id)


@router.post("/{store_id}/extract", response_model=ExtractionRunOut,
             dependencies=[Depends(require_admin_api_token)])
def extract_managed_store(store_id: int = Path(gt=0), db: Session = Depends(get_db)):
    """Run one synchronous extraction; serialize duplicate requests per store."""
    with _extraction_guard:
        if store_id in _running_extractions:
            raise HTTPException(status_code=409, detail="Ya hay una extracción en curso para esta tienda.")
        _running_extractions.add(store_id)
    try:
        with _database_extraction_lock(db, store_id) as acquired:
            if not acquired:
                raise HTTPException(status_code=409, detail="Ya hay una extracción en curso para esta tienda.")
            store = db.get(Store, store_id)
            if store is None:
                raise HTTPException(status_code=404, detail="Tienda no encontrada.")
            if not store.is_active:
                raise HTTPException(status_code=409, detail="La tienda está inactiva.")
            listings = db.scalars(
                select(StoreProduct).where(StoreProduct.store_id == store_id)
            ).all()
            if not listings:
                raise HTTPException(status_code=409, detail="La tienda no tiene publicaciones configuradas.")
            try:
                extractor = extractor_for_store(store)
            except ExtractionError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            if isinstance(extractor, PublicStoreExtractor):
                raise HTTPException(
                    status_code=422,
                    detail="El parser HTML genérico no está verificado como conector funcional para este comercio.",
                )
            if isinstance(extractor, FravegaExtractor):
                for listing in listings:
                    try:
                        _validate_listing_url(store, listing.product_url)
                    except HTTPException as exc:
                        raise HTTPException(
                            status_code=422,
                            detail="La tienda tiene una publicación inválida o fuera del dominio permitido.",
                        ) from exc
            stale_runs = db.scalars(select(ExtractionRun).where(
                ExtractionRun.store_id == store_id,
                ExtractionRun.status == "running",
            )).all()
            for stale_run in stale_runs:
                stale_run.status = "ABANDONED"
                stale_run.finished_at = datetime.now(timezone.utc)
                stale_run.error_summary = "Ejecución anterior interrumpida; no hay un bloqueo activo."
            if stale_runs:
                db.commit()
            try:
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
    x_admin_api_token: str | None = Header(default=None, alias="X-Admin-API-Token"),
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
    include_diagnostics = is_development(request.app.state.settings) or admin_token_matches(
        request.app.state.settings, x_admin_api_token
    )
    return [
        _run_output(db, run, store, include_diagnostics=include_diagnostics)
        for run in runs
    ]


@router.get("/{store_id}/extractions/{run_id}/observations", response_model=list[PriceObservationOut])
def list_run_observations(
    store_id: int = Path(gt=0),
    run_id: int = Path(gt=0),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    run = db.get(ExtractionRun, run_id)
    if run is None or run.store_id != store_id:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada para esta tienda.")
    return db.scalars(
        select(PriceObservation)
        .join(StoreProduct, StoreProduct.id == PriceObservation.store_product_id)
        .where(
            StoreProduct.store_id == store_id,
            PriceObservation.observed_at == run.started_at,
        )
        .order_by(PriceObservation.observed_at, PriceObservation.id)
        .limit(limit)
    ).all()


@router.put("/{store_id}/monitoring", response_model=StoreManagementOut,
            dependencies=[Depends(require_admin_api_token)])
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
    successful_run = db.scalar(
        select(ExtractionRun.id)
        .join(PriceObservation, PriceObservation.observed_at == ExtractionRun.started_at)
        .join(StoreProduct, StoreProduct.id == PriceObservation.store_product_id)
        .where(
            ExtractionRun.store_id == store_id,
            StoreProduct.store_id == store_id,
            ExtractionRun.status.in_(("SUCCESS", "PARTIAL_SUCCESS")),
        ).limit(1)
    )
    integration.status = (
        "active" if payload.enabled and successful_run is not None
        else "configuration_required" if payload.enabled
        else "configuration_required"
    )
    integration.analysis_message = (
        "Monitoreo configurado tras una extracción satisfactoria."
        if payload.enabled and successful_run is not None
        else "Preferencias guardadas; la integración se activará después de una extracción satisfactoria."
        if payload.enabled
        else "Preferencias guardadas. El monitoreo está desactivado."
    )
    integration.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _find_record(db, store_id)


def _find_record(db: Session, store_id: int) -> StoreManagementOut:
    record = next((item for item in _records(db) if item.id == store_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada.")
    return record
