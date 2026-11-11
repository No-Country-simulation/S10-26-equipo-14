from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Category, ExchangeRate, PriceObservation, Product, Store, StoreProduct
from app.schemas.catalog import (CategoryOut, PricedProductOut, PricedProductPageOut,
                                 ProductOut, ProductPageOut, StoreOut, StoreProductCreate,
                                 StoreProductOut)
from app.schemas.market import ExchangeRateOut, PriceObservationCreate, PriceObservationOut

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


@router.get("/stores", response_model=list[StoreOut], tags=["catalog"])
def list_stores(db: Session = Depends(get_db)):
    return db.scalars(select(Store).where(Store.is_active.is_(True)).order_by(Store.name)).all()


@router.get("/categories", response_model=list[CategoryOut], tags=["catalog"])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name)).all()


@router.get("/products", response_model=list[ProductOut], tags=["catalog"])
def list_products(category_id: int | None = None, db: Session = Depends(get_db)):
    query = select(Product).order_by(Product.name)
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    return db.scalars(query).all()


@router.get("/products/paginated", response_model=ProductPageOut, tags=["catalog"])
def list_products_paginated(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=250),
    db: Session = Depends(get_db),
):
    filters = []
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
    return {"items": items, "total": total, "limit": limit, "offset": offset}


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
    filters = [Product.category_id == category_id] if category_id is not None else []
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
            latest_price = {
                "amount": str(observation.amount),
                "currency": observation.currency,
                "observed_at": observation.observed_at,
                "store_id": store.id,
                "store_name": store.name,
                "store_product_id": listing.id,
                "source_url": observation.source_url,
                "is_available": observation.is_available,
            }
        items.append({
            "id": product.id,
            "name": product.name,
            "brand": product.brand,
            "model": product.model,
            "description": product.description,
            "barcode": product.barcode,
            "category_id": product.category_id,
            "latest_price": latest_price,
        })
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/products/{product_id}", response_model=ProductOut, tags=["catalog"])
def get_product(product_id: int = Path(gt=0), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return product


@router.get("/store-products", response_model=list[StoreProductOut], tags=["catalog"])
def list_store_products(store_id: int | None = None, db: Session = Depends(get_db)):
    query = select(StoreProduct).order_by(StoreProduct.id)
    if store_id is not None:
        query = query.where(StoreProduct.store_id == store_id)
    return db.scalars(query).all()


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
    return row


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
    if store_id is not None or category_id is not None or pattern is not None:
        query = query.join(StoreProduct, PriceObservation.store_product_id == StoreProduct.id)
    if store_id is not None:
        query = query.where(StoreProduct.store_id == store_id)
    if category_id is not None or pattern is not None:
        query = query.outerjoin(Product, StoreProduct.product_id == Product.id)
    if category_id is not None:
        query = query.where(
            or_(Product.category_id == category_id, StoreProduct.category_id == category_id)
        )
    if pattern is not None:
        query = query.where(or_(Product.name.ilike(pattern, escape="\\"), StoreProduct.product_name.ilike(pattern, escape="\\")))
    if start is not None:
        query = query.where(PriceObservation.observed_at >= start)
    if end is not None:
        query = query.where(PriceObservation.observed_at <= end)
    return db.scalars(query.order_by(PriceObservation.observed_at.desc()).limit(limit)).all()


@router.get("/exchange-rates", response_model=list[ExchangeRateOut], tags=["exchange-rates"])
def list_exchange_rates(
    rate_type: str | None = Query(default=None, min_length=1, max_length=30),
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
    query = select(ExchangeRate)
    if rate_type is not None:
        query = query.where(ExchangeRate.rate_type == rate_type)
    if on_date is not None:
        query = query.where(ExchangeRate.observed_at <= on_date)
    if start is not None:
        query = query.where(ExchangeRate.observed_at >= start)
    if end is not None:
        query = query.where(ExchangeRate.observed_at <= end)
    return db.scalars(query.order_by(ExchangeRate.observed_at.desc()).limit(limit)).all()
