from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.product_normalization import calculate_unit_prices, normalize_quantity
from app.models import Category, ExchangeRate, PriceObservation, Product, Store, StoreProduct
from app.schemas.catalog import (CategoryOut, PricedProductOut, PricedProductPageOut,
                                 ProductOut, ProductPageOut, StoreOut, StoreProductCreate,
                                 StoreProductOut)
from app.schemas.market import ExchangeRateOut, PriceObservationCreate, PriceObservationOut
from app.services.indicators import accumulated_inflation, compare_latest_prices, price_alerts, shrinkflation_signals
from app.services.exchange_rate_providers import MonedApiProvider
from app.services.ingestion import persist_quotes

router = APIRouter(prefix="/api/v1")

from app.api.v1.stores import router as store_management_router

router.include_router(store_management_router)


def _validate_range(start: datetime | None, end: datetime | None) -> None:
    for field_name, value in (("start", start), ("end", end)):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise HTTPException(status_code=422, detail=f"{field_name} debe incluir zona horaria")
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail="start no puede ser posterior a end")


def _search_pattern(search: str | None) -> str | None:
    value = search.strip() if search else ""
    if not value:
        return None
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _product_payload(product: Product) -> dict[str, object]:
    quantity = normalize_quantity(
        product.package_quantity, product.package_unit, product.package_count
    )
    return {
        "id": product.id,
        "name": product.name,
        "brand": product.brand,
        "model": product.model,
        "description": product.description,
        "barcode": product.barcode,
        "category_id": product.category_id,
        "package_quantity": product.package_quantity,
        "package_unit": product.package_unit,
        "package_count": product.package_count,
        "normalized_quantity": quantity.total_quantity if quantity.available else None,
        "normalized_unit": quantity.unit if quantity.available else None,
        "normalization_unavailable_reason": quantity.reason,
    }


def _store_product_payload(listing: StoreProduct, product: Product | None) -> dict[str, object]:
    quantity = normalize_quantity(
        product.package_quantity if product else None,
        product.package_unit if product else None,
        product.package_count if product else None,
    )
    return {
        "id": listing.id,
        "store_id": listing.store_id,
        "product_id": listing.product_id,
        "category_id": listing.category_id,
        "external_id": listing.external_id,
        "product_url": listing.product_url,
        "product_name": listing.product_name,
        "currency": listing.currency,
        "package_quantity": product.package_quantity if product else None,
        "package_unit": product.package_unit if product else None,
        "package_count": product.package_count if product else None,
        "normalized_quantity": quantity.total_quantity if quantity.available else None,
        "normalized_unit": quantity.unit if quantity.available else None,
        "normalization_unavailable_reason": (
            "missing_product" if product is None else quantity.reason
        ),
    }


def _latest_price_payload(
    product: Product,
    observation: PriceObservation,
    listing: StoreProduct,
    store: Store,
) -> dict[str, object]:
    normalized = calculate_unit_prices(
        package_quantity=product.package_quantity,
        package_unit=product.package_unit,
        package_count=product.package_count,
        price=observation.amount,
        promotional_price=observation.promotional_price,
        currency=observation.currency,
    )
    return {
        "amount": str(observation.amount),
        "promotional_price": (
            str(observation.promotional_price) if observation.promotional_price is not None else None
        ),
        "currency": observation.currency,
        "observed_at": observation.observed_at,
        "store_id": store.id,
        "store_name": store.name,
        "store_product_id": listing.id,
        "source_url": observation.source_url,
        "is_available": observation.is_available,
        "normalized_quantity": normalized.total_quantity,
        "normalized_unit": normalized.unit,
        "normalized_price": normalized.regular_price_per_unit,
        "normalized_promotional_price": normalized.promotional_price_per_unit,
        "normalization_unavailable_reason": normalized.reason,
        "promotional_normalization_unavailable_reason": normalized.promotional_reason,
    }


@router.get("/stores", response_model=list[StoreOut], tags=["catalog"])
def list_stores(db: Session = Depends(get_db)):
    return db.scalars(select(Store).where(Store.is_active.is_(True), ~Store.name.like("DEMO PriceScope %")).order_by(Store.name)).all()


@router.get("/categories", response_model=list[CategoryOut], tags=["catalog"])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).where(~Category.name.like("DEMO PriceScope %")).order_by(Category.name)).all()


@router.get("/products", response_model=list[ProductOut], tags=["catalog"])
def list_products(category_id: int | None = None, db: Session = Depends(get_db)):
    query = select(Product).where(~Product.name.like("DEMO PriceScope %")).order_by(Product.name)
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    return [_product_payload(item) for item in db.scalars(query).all()]


@router.get("/products/paginated", response_model=ProductPageOut, tags=["catalog"])
def list_products_paginated(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=250),
    db: Session = Depends(get_db),
):
    filters = [~Product.name.like("DEMO PriceScope %")]
    if category_id is not None:
        filters.append(Product.category_id == category_id)
    pattern = _search_pattern(search)
    if pattern is not None:
        filters.append(Product.name.ilike(pattern, escape="\\"))

    total = db.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
    items = db.scalars(
        select(Product)
        .where(*filters)
        .order_by(Product.name, Product.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": [_product_payload(item) for item in items], "total": total, "limit": limit, "offset": offset}


@router.get("/products/paginated-with-prices", response_model=PricedProductPageOut, tags=["catalog"])
def list_products_with_latest_prices(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=250),
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
):
    """List canonical products with their latest observation across stores."""
    _validate_range(start, end)
    filters = [~Product.name.like("DEMO PriceScope %")]
    if category_id is not None:
        filters.append(Product.category_id == category_id)
    pattern = _search_pattern(search)
    if pattern is not None:
        filters.append(Product.name.ilike(pattern, escape="\\"))

    observation_window = []
    if start is not None:
        observation_window.append(PriceObservation.observed_at >= start)
    if end is not None:
        observation_window.append(PriceObservation.observed_at <= end)
    if observation_window:
        in_window = (
            select(PriceObservation.id)
            .join(StoreProduct, PriceObservation.store_product_id == StoreProduct.id)
            .where(StoreProduct.product_id == Product.id, *observation_window)
            .exists()
        )
        filters.append(in_window)

    total = db.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
    latest_observation_id = (
        select(PriceObservation.id)
        .join(StoreProduct, PriceObservation.store_product_id == StoreProduct.id)
        .where(StoreProduct.product_id == Product.id, *observation_window)
        .order_by(PriceObservation.observed_at.desc(), PriceObservation.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Product, PriceObservation, StoreProduct, Store)
        .select_from(Product)
        .outerjoin(PriceObservation, PriceObservation.id == latest_observation_id)
        .outerjoin(StoreProduct, StoreProduct.id == PriceObservation.store_product_id)
        .outerjoin(Store, Store.id == StoreProduct.store_id)
        .where(*filters)
        .order_by(Product.name, Product.id)
        .limit(limit)
        .offset(offset)
    ).all()
    items = []
    for product, observation, listing, store in rows:
        latest_price = None
        if observation is not None and listing is not None and store is not None:
            latest_price = _latest_price_payload(product, observation, listing, store)
        items.append({**_product_payload(product), "latest_price": latest_price})
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/products/{product_id}", response_model=ProductOut, tags=["catalog"])
def get_product(product_id: int = Path(gt=0), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None or product.name.startswith("DEMO PriceScope "):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return _product_payload(product)


@router.get("/store-products", response_model=list[StoreProductOut], tags=["catalog"])
def list_store_products(store_id: int | None = None, db: Session = Depends(get_db)):
    query = select(StoreProduct, Product).outerjoin(Product, Product.id == StoreProduct.product_id)
    query = query.order_by(StoreProduct.id)
    if store_id is not None:
        query = query.where(StoreProduct.store_id == store_id)
    return [_store_product_payload(listing, product) for listing, product in db.execute(query).all()]


@router.post("/store-products", response_model=StoreProductOut, status_code=status.HTTP_201_CREATED, tags=["catalog"])
def create_store_product(payload: StoreProductCreate, db: Session = Depends(get_db)):
    row = StoreProduct(**payload.model_dump(mode="json"))
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tienda inexistente o publicación duplicada") from exc
    product = db.get(Product, row.product_id) if row.product_id is not None else None
    return _store_product_payload(row, product)


@router.post("/price-observations", response_model=PriceObservationOut, status_code=status.HTTP_201_CREATED, tags=["prices"])
def create_price_observation(payload: PriceObservationCreate, db: Session = Depends(get_db)):
    if payload.observed_at.tzinfo is None or payload.observed_at.utcoffset() is None:
        raise HTTPException(status_code=422, detail="observed_at debe incluir zona horaria")
    row = PriceObservation(**payload.model_dump())
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Publicación inexistente o observación duplicada") from exc
    return row


@router.get("/price-observations", response_model=list[PriceObservationOut], tags=["prices"])
def list_price_observations(
    store_product_id: int | None = Query(default=None, gt=0),
    store_id: int | None = Query(default=None, gt=0),
    category_id: int | None = Query(default=None, gt=0),
    start: datetime | None = None,
    end: datetime | None = None,
    search: str | None = Query(default=None, max_length=250),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    _validate_range(start, end)
    query = select(PriceObservation)
    if store_product_id is not None:
        query = query.where(PriceObservation.store_product_id == store_product_id)
    pattern = _search_pattern(search)
    joined_listing = store_id is not None or category_id is not None or pattern is not None
    joined_product = category_id is not None or pattern is not None
    if joined_listing:
        query = query.join(StoreProduct, PriceObservation.store_product_id == StoreProduct.id)
    if store_id is not None:
        query = query.where(StoreProduct.store_id == store_id)
    if joined_product:
        query = query.outerjoin(Product, StoreProduct.product_id == Product.id)
    if category_id is not None:
        query = query.where(
            or_(Product.category_id == category_id, StoreProduct.category_id == category_id)
        )
    if pattern is not None:
        query = query.where(or_(Product.name.ilike(pattern, escape="\\"), StoreProduct.product_name.ilike(pattern, escape="\\")))
    if not joined_listing:
        query = query.join(StoreProduct, PriceObservation.store_product_id == StoreProduct.id)
    if not joined_product:
        query = query.outerjoin(Product, StoreProduct.product_id == Product.id)
    query = query.join(Store, Store.id == StoreProduct.store_id).where(
        ~Store.name.like("DEMO PriceScope %"), or_(Product.id.is_(None), ~Product.name.like("DEMO PriceScope %"))
    )
    if start is not None:
        query = query.where(PriceObservation.observed_at >= start)
    if end is not None:
        query = query.where(PriceObservation.observed_at <= end)
    return db.scalars(query.order_by(PriceObservation.observed_at.desc()).limit(limit)).all()


@router.get("/exchange-rates", response_model=list[ExchangeRateOut], tags=["exchange-rates"])
def list_exchange_rates(
    rate_type: str = Query(..., min_length=1, max_length=30),
    on_date: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    for field_name, value in (("on_date", on_date),):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise HTTPException(status_code=422, detail=f"{field_name} debe incluir zona horaria")
    _validate_range(start, end)
    # Refresh requested USD/ARS series from a real public source.
    # If the provider is temporarily unavailable, keep the stored real history.
    if rate_type in {"official", "parallel"}:
        try:
            persist_quotes(db, MonedApiProvider(rate_type).fetch())
            db.commit()
        except Exception:
            db.rollback()

    query = select(ExchangeRate).where(
        ExchangeRate.rate_type == rate_type,
        ~ExchangeRate.source.ilike("%demo%"),
        ~ExchangeRate.source.ilike("%synthetic%"),
    )
    if on_date is not None:
        query = query.where(ExchangeRate.observed_at <= on_date)
    if start is not None:
        query = query.where(ExchangeRate.observed_at >= start)
    if end is not None:
        query = query.where(ExchangeRate.observed_at <= end)
    return db.scalars(query.order_by(ExchangeRate.observed_at.desc()).limit(limit)).all()


@router.get("/comparisons", tags=["indicators"])
def list_price_comparisons(
    category_id: int | None = Query(default=None, gt=0),
    store_id: int | None = Query(default=None, gt=0),
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _validate_range(start, end)
    return compare_latest_prices(
        db, category_id=category_id, store_id=store_id, start=start, end=end, limit=limit
    )


@router.get("/alerts", tags=["indicators"])
def list_price_alerts(
    category_id: int | None = Query(default=None, gt=0),
    store_id: int | None = Query(default=None, gt=0),
    start: datetime | None = None,
    end: datetime | None = None,
    rate_type: Literal["official", "parallel"] = "official",
    spike_percent: Decimal = Query(default=Decimal("20"), gt=0, le=500),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _validate_range(start, end)
    return price_alerts(
        db,
        category_id=category_id,
        store_id=store_id,
        start=start,
        end=end,
        rate_type=rate_type,
        spike_percent=spike_percent,
        limit=limit,
    )


@router.get("/indicators/inflation", tags=["indicators"])
def get_accumulated_inflation(
    start: datetime,
    end: datetime,
    category_id: int | None = Query(default=None, gt=0),
    store_id: int | None = Query(default=None, gt=0),
    product_id: int | None = Query(default=None, gt=0),
    rate_type: Literal["official", "parallel"] = "official",
    db: Session = Depends(get_db),
):
    _validate_range(start, end)
    return accumulated_inflation(
        db, start=start, end=end, category_id=category_id,
        store_id=store_id, product_id=product_id, rate_type=rate_type,
    )


@router.get("/indicators/shrinkflation", tags=["indicators"])
def get_shrinkflation_signals(
    start: datetime | None = None,
    end: datetime | None = None,
    category_id: int | None = Query(default=None, gt=0),
    store_id: int | None = Query(default=None, gt=0),
    product_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _validate_range(start, end)
    return shrinkflation_signals(
        db, start=start, end=end, category_id=category_id,
        store_id=store_id, product_id=product_id, limit=limit,
    )
