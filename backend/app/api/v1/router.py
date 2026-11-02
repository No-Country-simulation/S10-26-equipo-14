from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Category, ExchangeRate, PriceObservation, Product, Store, StoreProduct
from app.schemas.catalog import CategoryOut, ProductOut, StoreOut, StoreProductCreate, StoreProductOut
from app.schemas.market import ExchangeRateOut, PriceObservationCreate, PriceObservationOut

router = APIRouter(prefix="/api/v1")


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
    store_product_id: int = Query(gt=0),
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    if start is not None and (start.tzinfo is None or start.utcoffset() is None):
        raise HTTPException(status_code=422, detail="start debe incluir zona horaria")
    if end is not None and (end.tzinfo is None or end.utcoffset() is None):
        raise HTTPException(status_code=422, detail="end debe incluir zona horaria")
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail="start no puede ser posterior a end")
    query = select(PriceObservation).where(PriceObservation.store_product_id == store_product_id)
    if start is not None:
        query = query.where(PriceObservation.observed_at >= start)
    if end is not None:
        query = query.where(PriceObservation.observed_at <= end)
    return db.scalars(query.order_by(PriceObservation.observed_at.desc()).limit(limit)).all()


@router.get("/exchange-rates", response_model=list[ExchangeRateOut], tags=["exchange-rates"])
def list_exchange_rates(
    rate_type: str = Query(min_length=1, max_length=30),
    on_date: datetime | None = None,
    db: Session = Depends(get_db),
):
    if on_date is not None and (on_date.tzinfo is None or on_date.utcoffset() is None):
        raise HTTPException(status_code=422, detail="on_date debe incluir zona horaria")
    query = select(ExchangeRate).where(ExchangeRate.rate_type == rate_type)
    if on_date is not None:
        query = query.where(ExchangeRate.observed_at <= on_date)
    return db.scalars(query.order_by(ExchangeRate.observed_at.desc()).limit(100)).all()
