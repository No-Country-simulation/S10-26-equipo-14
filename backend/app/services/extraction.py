"""Run a store extractor and persist source-backed product price history."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.currency import is_supported_iso_currency
from app.core.gtin import is_valid_gtin
from app.extractors.base import ProductSnapshot, StoreExtractor
from app.models import Category, ExtractionRun, PriceObservation, Product, Store, StoreIntegration, StoreProduct
from app.services.ingestion import RawPrice, normalize_decimal, persist_price


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    run_id: int
    source: str
    status: str
    records_seen: int
    observations_created: int
    products_created: int
    prices_changed: int
    errors: tuple[str, ...]


def _normalized_status(errors: list[str]) -> str:
    if not errors:
        return "SUCCESS"
    text = " ".join(errors).upper()
    for status in ("RATE_LIMITED", "LOCATION_REQUIRED", "BLOCKED", "NETWORK_ERROR",
                   "PRODUCT_NOT_FOUND", "PRICE_NOT_FOUND", "UNSUPPORTED"):
        if status in text:
            return status
    if any(term in text for term in ("UBICACI", "CÓDIGO POSTAL", "LOCATION")):
        return "LOCATION_REQUIRED"
    if "PRECIO" in text or "OFERTA" in text:
        return "PRICE_NOT_FOUND"
    if "PRODUCTO" in text:
        return "PRODUCT_NOT_FOUND"
    return "UNSUPPORTED"


def _category_id(session: Session, category_name: str | None) -> int | None:
    if not category_name:
        return None
    matches = session.scalars(
        select(Category)
        .where(func.lower(Category.name) == category_name.strip().lower())
        .limit(2)
    ).all()
    return matches[0].id if len(matches) == 1 else None


def _associate_product(
    session: Session,
    listing: StoreProduct,
    snapshot: ProductSnapshot,
) -> bool:
    category_id = _category_id(session, snapshot.category_name)
    product = session.get(Product, listing.product_id) if listing.product_id else None

    if product is not None and snapshot.barcode and product.barcode and product.barcode != snapshot.barcode:
        raise ValueError(
            "Conflicto de GTIN con el producto canónico asociado; requiere revisión manual."
        )

    if product is None and snapshot.barcode:
        product = session.scalar(select(Product).where(Product.barcode == snapshot.barcode))

    product_created = product is None
    if product_created:
        product = Product(
            name=snapshot.name,
            brand=snapshot.brand,
            model=snapshot.model,
            description=snapshot.description,
            barcode=snapshot.barcode,
        )
        session.add(product)
        session.flush()
    else:
        # Fill missing catalog metadata from the listing, never overwrite values
        # already curated in the canonical product record.
        if not product.brand and snapshot.brand:
            product.brand = snapshot.brand
        if not product.model and snapshot.model:
            product.model = snapshot.model
        if not product.description and snapshot.description:
            product.description = snapshot.description
        if not product.barcode and snapshot.barcode:
            product.barcode = snapshot.barcode

    listing.product_id = product.id
    listing.product_name = snapshot.name
    if listing.category_id is None and category_id is not None:
        listing.category_id = category_id

    if listing.external_id is None and snapshot.external_id and len(snapshot.external_id) <= 180:
        duplicate_external_id = session.scalar(
            select(StoreProduct.id).where(
                StoreProduct.store_id == listing.store_id,
                StoreProduct.external_id == snapshot.external_id,
                StoreProduct.id != listing.id,
            )
        )
        if duplicate_external_id is None:
            listing.external_id = snapshot.external_id

    return product_created


def _same_observation_values(observation: PriceObservation, snapshot: ProductSnapshot) -> bool:
    return (
        observation.amount == snapshot.amount
        and observation.promotional_price == snapshot.promotional_price
        and observation.currency == snapshot.currency.upper()
        and observation.is_available == snapshot.is_available
        and observation.observed_package_quantity == snapshot.observed_package_quantity
        and observation.observed_package_unit == snapshot.observed_package_unit
        and observation.observed_package_count == snapshot.observed_package_count
    )


def run_store_extraction(
    session: Session,
    store_id: int,
    extractor: StoreExtractor,
    *,
    started_at: datetime | None = None,
) -> ExtractionResult:
    """Fetch known listing URLs for one active store and append observations.

    The caller supplies the session. Every observation in the batch uses the
    run's UTC start time, and the database uniqueness constraint makes a retry
    at the same instant idempotent for each store listing.
    """
    store = session.get(Store, store_id)
    if store is None:
        raise ValueError(f"No existe la tienda con id {store_id}.")
    if not store.is_active:
        raise ValueError(f"La tienda {store_id} está inactiva.")
    if not extractor.supports(store):
        raise ValueError(f"El extractor {extractor.name} no admite la tienda {store_id}.")

    started_at = started_at or datetime.now(timezone.utc)
    if started_at.tzinfo is None or started_at.utcoffset() is None:
        raise ValueError("La fecha de inicio debe incluir zona horaria.")
    started_at = started_at.astimezone(timezone.utc)
    run = ExtractionRun(
        source=extractor.name[:100],
        store_id=store_id,
        status="running",
        records_seen=0,
        started_at=started_at,
    )
    session.add(run)
    session.commit()
    run_id = run.id

    errors: list[str] = []
    diagnostics: list[dict[str, object]] = []
    records_seen = 0
    observations_created = 0
    products_created = 0
    prices_changed = 0

    try:
        extractor.prepare()
    except Exception as exc:  # provider errors are persisted without stopping the audit trail
        errors.append(f"No se pudo preparar el extractor: {exc}")

    listing_ids = session.scalars(
        select(StoreProduct.id)
        .where(StoreProduct.store_id == store_id)
        .order_by(StoreProduct.id)
    ).all()
    if not listing_ids:
        errors.append("PRODUCT_NOT_FOUND: la tienda no tiene publicaciones registradas para consultar.")

    if not errors:
        for listing_id in listing_ids:
            try:
                listing = session.get(StoreProduct, listing_id)
                if listing is None:
                    raise ValueError("La publicación dejó de estar disponible durante la ejecución.")
                snapshot = extractor.extract(listing)
                if snapshot.source_url != listing.product_url:
                    raise ValueError("UNSUPPORTED: la URL de origen no coincide con la publicación consultada.")
                amount = normalize_decimal(snapshot.amount)
                if amount >= Decimal("1000000000000"):
                    raise ValueError("El importe excede la precisión de PriceObservation.amount.")
                if amount != amount.quantize(Decimal("0.01")):
                    raise ValueError("El importe supera la precisión de dos decimales.")
                if len(snapshot.name) > 250 or not snapshot.name.strip():
                    raise ValueError("El nombre excede el tamaño o está vacío.")
                if (
                    not is_supported_iso_currency(snapshot.currency)
                ):
                    raise ValueError("UNSUPPORTED: moneda ISO 4217 desconocida o no admitida.")
                if snapshot.barcode is not None and not is_valid_gtin(snapshot.barcode):
                    raise ValueError("UNSUPPORTED: GTIN inválido; no se asociará ni publicará el producto.")
                for field, value, max_length in (
                    ("marca", snapshot.brand, 120),
                    ("modelo", snapshot.model, 120),
                    ("código de barras", snapshot.barcode, 64),
                ):
                    if value is not None and len(value) > max_length:
                        raise ValueError(f"El campo {field} excede su longitud permitida.")
                promotional_price = (
                    normalize_decimal(snapshot.promotional_price)
                    if snapshot.promotional_price is not None
                    else None
                )
                if promotional_price is not None and (
                    promotional_price >= Decimal("1000000000000")
                    or promotional_price != promotional_price.quantize(Decimal("0.01"))
                ):
                    raise ValueError("El precio promocional excede la precisión permitida.")
                records_seen += 1

                existing_observation = session.scalar(
                    select(PriceObservation.id).where(
                        PriceObservation.store_product_id == listing.id,
                        PriceObservation.observed_at == started_at,
                    )
                )
                if existing_observation is not None:
                    session.rollback()
                    continue

                previous_observation = session.scalar(
                    select(PriceObservation)
                    .where(PriceObservation.store_product_id == listing.id)
                    .order_by(PriceObservation.observed_at.desc(), PriceObservation.id.desc())
                    .limit(1)
                )
                product_created = _associate_product(session, listing, snapshot)
                price_changed = previous_observation is not None and (
                    previous_observation.amount != amount
                    or previous_observation.promotional_price != promotional_price
                    or previous_observation.currency != snapshot.currency.upper()
                )
                raw_price = RawPrice(
                    amount=amount,
                    promotional_price=promotional_price,
                    observed_package_quantity=snapshot.observed_package_quantity,
                    observed_package_unit=snapshot.observed_package_unit,
                    observed_package_count=snapshot.observed_package_count,
                    currency=snapshot.currency,
                    source_url=snapshot.source_url,
                    is_available=snapshot.is_available,
                    observed_at=started_at,
                )
                day_start = started_at.replace(hour=0, minute=0, second=0, microsecond=0)
                latest_today = session.scalar(
                    select(PriceObservation)
                    .where(
                        PriceObservation.store_product_id == listing.id,
                        PriceObservation.observed_at >= day_start,
                        PriceObservation.observed_at < started_at,
                    )
                    .order_by(PriceObservation.observed_at.desc(), PriceObservation.id.desc())
                    .limit(1)
                )
                observation_created = not (
                    latest_today is not None and _same_observation_values(latest_today, snapshot)
                )
                if observation_created:
                    session.add(persist_price(session, listing.id, raw_price))
                session.commit()
                products_created += int(product_created)
                prices_changed += int(price_changed)
                observations_created += int(observation_created)
                diagnostics.append({
                    "url": listing.product_url,
                    "http_status": getattr(extractor, "last_http_status", None),
                    "content_type": getattr(extractor, "last_content_type", None),
                    "format": snapshot.extraction_format,
                    "product": snapshot.name,
                    "currency": snapshot.currency,
                    "product_created": product_created,
                    "price_changed": price_changed,
                    "observation_created": observation_created,
                })
            except Exception as exc:  # keep valid listings even if one page is malformed
                session.rollback()
                errors.append(f"Publicación {listing_id}: {exc}")
                if any(marker in str(exc).upper() for marker in ("BLOCKED", "RATE_LIMITED", "HTTP 403", "HTTP 429")):
                    # A portal denial applies to the source, not just this URL;
                    # stop the batch instead of making additional requests.
                    break

    finished_at = datetime.now(timezone.utc)
    status = "PARTIAL_SUCCESS" if errors and observations_created > 0 else _normalized_status(errors)
    run = session.get(ExtractionRun, run_id)
    if run is None:
        raise RuntimeError("Se perdió el registro de la ejecución de extracción.")
    run.status = status
    run.records_seen = records_seen
    run.finished_at = finished_at
    # Keep actionable diagnostics while omitting request headers, response
    # bodies and other potentially sensitive transport details.
    diagnostic_lines = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in diagnostics]
    run.error_summary = "\n".join([*errors, *diagnostic_lines])[:4000] or None
    integration = session.scalar(select(StoreIntegration).where(StoreIntegration.store_id == store_id))
    if integration is not None:
        if status in {"SUCCESS", "PARTIAL_SUCCESS"} and observations_created > 0:
            integration.status = "active"
            integration.analysis_message = (
                "Extracción pública satisfactoria; la observación real quedó guardada."
                if status == "SUCCESS"
                else "Extracción parcial: se guardaron observaciones y se registraron errores por publicación."
            )
        elif errors:
            integration.status = "error"
            integration.analysis_message = "La última extracción no obtuvo datos utilizables; revisa su historial."
        integration.updated_at = finished_at
    session.commit()

    return ExtractionResult(
        run_id=run_id,
        source=extractor.name,
        status=status,
        records_seen=records_seen,
        observations_created=observations_created,
        products_created=products_created,
        prices_changed=prices_changed,
        errors=tuple(errors),
    )
