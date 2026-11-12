"""Read-only indicators derived from persisted prices and exchange quotes."""

from __future__ import annotations

from bisect import bisect_right
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExchangeRate, PriceObservation, Product, Store, StoreProduct
from app.services.product_normalization import normalize_quantity


def _effective_price(observation: PriceObservation) -> Decimal:
    promotion = observation.promotional_price
    return promotion if promotion is not None and promotion <= observation.amount else observation.amount


def compare_latest_prices(
    session: Session,
    *,
    category_id: int | None = None,
    store_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
) -> list[dict[str, object]]:
    """Compare latest available listing prices, requiring two distinct stores."""
    observation_filters = []
    if start is not None:
        observation_filters.append(PriceObservation.observed_at >= start)
    if end is not None:
        observation_filters.append(PriceObservation.observed_at <= end)
    latest_id = (
        select(PriceObservation.id)
        .where(PriceObservation.store_product_id == StoreProduct.id, *observation_filters)
        .order_by(PriceObservation.observed_at.desc(), PriceObservation.id.desc())
        .limit(1)
        .correlate(StoreProduct)
        .scalar_subquery()
    )
    query = (
        select(Product, StoreProduct, PriceObservation, Store)
        .join(StoreProduct, StoreProduct.product_id == Product.id)
        .join(PriceObservation, PriceObservation.id == latest_id)
        .join(Store, Store.id == StoreProduct.store_id)
        .order_by(Product.name, Store.name, StoreProduct.id)
        .where(~Product.name.like("DEMO PriceScope %"), ~Store.name.like("DEMO PriceScope %"))
    )
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    rows = session.execute(query.limit(limit * 20)).all()
    grouped: dict[int, dict[str, object]] = {}
    for product, listing, observation, store in rows:
        item = grouped.setdefault(product.id, {
            "product_id": product.id,
            "product_name": product.name,
            "category_id": product.category_id,
            "prices": [],
        })
        item["prices"].append({
            "store_id": store.id,
            "store_name": store.name,
            "store_product_id": listing.id,
            "amount": str(observation.amount),
            "promotional_price": str(observation.promotional_price) if observation.promotional_price is not None else None,
            "effective_price": str(_effective_price(observation)),
            "currency": observation.currency,
            "observed_at": observation.observed_at,
            "source_url": observation.source_url,
            "is_available": observation.is_available,
        })

    results = []
    for item in grouped.values():
        latest_by_store = {}
        for price in item["prices"]:
            existing = latest_by_store.get(price["store_id"])
            if existing is None or price["observed_at"] > existing["observed_at"]:
                latest_by_store[price["store_id"]] = price
        prices = list(latest_by_store.values())
        if store_id is not None and all(price["store_id"] != store_id for price in prices):
            continue
        currencies = {price["currency"] for price in prices}
        if len(prices) < 2 or len(currencies) != 1:
            continue
        ordered = sorted(prices, key=lambda price: Decimal(price["effective_price"]))
        low, high = Decimal(ordered[0]["effective_price"]), Decimal(ordered[-1]["effective_price"])
        item["prices"] = prices
        item["spread_amount"] = str(high - low)
        item["spread_percent"] = str((high - low) / low * Decimal("100")) if low > 0 else None
        item["currency"] = next(iter(currencies))
        results.append(item)
    results.sort(key=lambda item: item["product_name"])
    return results[:limit]


def price_alerts(
    session: Session,
    *,
    category_id: int | None = None,
    store_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    rate_type: str = "official",
    spike_percent: Decimal = Decimal("20"),
    limit: int = 100,
) -> list[dict[str, object]]:
    """Find price jumps and increases exceeding aligned FX depreciation.

    Alerts are derived from the two latest in-window observations per listing.
    If a matching FX quote is unavailable, no currency-relative alert is
    fabricated; a configured absolute spike can still be reported.
    """
    filters = []
    if start is not None:
        filters.append(PriceObservation.observed_at >= start)
    if end is not None:
        filters.append(PriceObservation.observed_at <= end)
    if store_id is not None:
        filters.append(StoreProduct.store_id == store_id)
    if category_id is not None:
        filters.append((Product.category_id == category_id) | (StoreProduct.category_id == category_id))
    filters.extend((~Product.name.like("DEMO PriceScope %"), ~Store.name.like("DEMO PriceScope %")))
    rows = session.execute(
        select(PriceObservation, StoreProduct, Product, Store)
        .join(StoreProduct, StoreProduct.id == PriceObservation.store_product_id)
        .join(Product, Product.id == StoreProduct.product_id)
        .join(Store, Store.id == StoreProduct.store_id)
        .where(*filters)
        .order_by(PriceObservation.observed_at.desc(), PriceObservation.id.desc())
        .limit(20_000)
    ).all()
    by_listing: dict[int, list[tuple[PriceObservation, StoreProduct, Product, Store]]] = {}
    for row in rows:
        by_listing.setdefault(row[1].id, []).append(row)

    expected_side = "sell" if rate_type == "parallel" else "reference"
    rates = session.scalars(
        select(ExchangeRate)
        .where(
            ExchangeRate.rate_type == rate_type,
            ExchangeRate.base_currency == "USD",
            ExchangeRate.quote_currency == "ARS",
            ExchangeRate.rate_side == expected_side,
        )
        .order_by(ExchangeRate.observed_at)
    ).all()

    rate_dates = [rate.observed_at for rate in rates]

    def aligned_rate(at: datetime) -> ExchangeRate | None:
        index = bisect_right(rate_dates, at) - 1
        return rates[index] if index >= 0 else None

    results: list[dict[str, object]] = []
    for listing_rows in by_listing.values():
        if len(listing_rows) < 2:
            continue
        latest, previous = listing_rows[0], listing_rows[1]
        newer, listing, product, store = latest
        older = previous[0]
        if newer.currency != older.currency:
            continue
        before, after = _effective_price(older), _effective_price(newer)
        if before <= 0:
            continue
        price_change = (after - before) / before * Decimal("100")
        if price_change <= 0:
            continue

        old_rate = aligned_rate(older.observed_at) if newer.currency == "ARS" else None
        new_rate = aligned_rate(newer.observed_at) if newer.currency == "ARS" else None
        fx_change = None
        if old_rate is not None and new_rate is not None and old_rate.rate > 0:
            fx_change = (new_rate.rate - old_rate.rate) / old_rate.rate * Decimal("100")

        alert_types = []
        if price_change >= spike_percent:
            alert_types.append("price_spike")
        if fx_change is not None and price_change > fx_change:
            alert_types.append("price_increase_over_currency")
        for alert_type in alert_types:
            results.append({
                "alert_type": alert_type,
                "product_id": product.id,
                "product_name": product.name,
                "store_id": store.id,
                "store_name": store.name,
                "store_product_id": listing.id,
                "currency": newer.currency,
                "previous_price": str(before),
                "latest_price": str(after),
                "price_change_percent": str(price_change),
                "exchange_rate_type": rate_type if fx_change is not None else None,
                "exchange_rate_change_percent": str(fx_change) if fx_change is not None else None,
                "previous_observed_at": older.observed_at,
                "observed_at": newer.observed_at,
                "source_url": newer.source_url,
            })
    results.sort(key=lambda item: (item["observed_at"], item["alert_type"]), reverse=True)
    return results[:limit]


def shrinkflation_signals(
    session: Session,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    category_id: int | None = None,
    store_id: int | None = None,
    product_id: int | None = None,
    limit: int = 100,
) -> list[dict[str, object]]:
    """Compare explicit, timestamped package measurements on the same listing.

    Canonical package metadata is intentionally not copied backward into old
    observations. A signal requires two observations carrying their own
    measured quantity/unit/count, the same canonical product, and currency.
    """
    filters = [Product.id.is_not(None)]
    if start is not None:
        filters.append(PriceObservation.observed_at >= start)
    if end is not None:
        filters.append(PriceObservation.observed_at <= end)
    if category_id is not None:
        filters.append((Product.category_id == category_id) | (StoreProduct.category_id == category_id))
    if store_id is not None:
        filters.append(StoreProduct.store_id == store_id)
    if product_id is not None:
        filters.append(Product.id == product_id)
    filters.extend((~Product.name.like("DEMO PriceScope %"), ~Store.name.like("DEMO PriceScope %")))
    rows = session.execute(
        select(PriceObservation, StoreProduct, Product, Store)
        .join(StoreProduct, StoreProduct.id == PriceObservation.store_product_id)
        .join(Product, Product.id == StoreProduct.product_id)
        .join(Store, Store.id == StoreProduct.store_id)
        .where(*filters)
        .order_by(StoreProduct.id, PriceObservation.observed_at, PriceObservation.id)
    ).all()
    by_listing: dict[int, list[tuple[PriceObservation, StoreProduct, Product, Store]]] = {}
    for row in rows:
        obs = row[0]
        if obs.observed_package_quantity is None or obs.observed_package_unit is None or obs.observed_package_count is None:
            continue
        quantity = normalize_quantity(obs.observed_package_quantity, obs.observed_package_unit, obs.observed_package_count)
        if quantity.available:
            by_listing.setdefault(row[1].id, []).append(row)

    signals = []
    for history in by_listing.values():
        if len(history) < 2:
            continue
        for older_row, newer_row in zip(history, history[1:]):
            older, listing, product, store = older_row
            newer = newer_row[0]
            if older.currency != newer.currency:
                continue
            old_quantity = normalize_quantity(older.observed_package_quantity, older.observed_package_unit, older.observed_package_count)
            new_quantity = normalize_quantity(newer.observed_package_quantity, newer.observed_package_unit, newer.observed_package_count)
            if not old_quantity.available or not new_quantity.available or old_quantity.dimension != new_quantity.dimension:
                continue
            assert old_quantity.total_quantity and new_quantity.total_quantity
            if new_quantity.total_quantity >= old_quantity.total_quantity or older.amount <= 0:
                continue
            old_unit_price = older.amount / old_quantity.total_quantity
            new_unit_price = newer.amount / new_quantity.total_quantity
            unit_change = (new_unit_price - old_unit_price) / old_unit_price * Decimal("100")
            if unit_change <= 0:
                continue
            signals.append({
                "status": "confirmed" if newer.amount >= older.amount else "possible",
                "product_id": product.id,
                "product_name": product.name,
                "store_id": store.id,
                "store_name": store.name,
                "store_product_id": listing.id,
                "currency": newer.currency,
                "unit": new_quantity.unit,
                "previous_quantity": str(old_quantity.total_quantity),
                "latest_quantity": str(new_quantity.total_quantity),
                "previous_price": str(older.amount),
                "latest_price": str(newer.amount),
                "previous_unit_price": str(old_unit_price),
                "latest_unit_price": str(new_unit_price),
                "unit_price_change_percent": str(unit_change),
                "previous_observed_at": older.observed_at,
                "observed_at": newer.observed_at,
                "source_url": newer.source_url,
            })
    signals.sort(key=lambda item: (item["observed_at"], item["product_id"]), reverse=True)
    return signals[:limit]


def accumulated_inflation(
    session: Session,
    *,
    start: datetime,
    end: datetime,
    category_id: int | None = None,
    store_id: int | None = None,
    product_id: int | None = None,
    rate_type: str = "official",
) -> dict[str, object]:
    """Equal-weight price change using first/last same-listing observations.

    Currency groups are kept separate. Store listings need at least two
    distinct observations within the inclusive period; product/category results
    average eligible listing changes equally and disclose sample counts.
    FX movement is reported separately from price inflation.
    """
    filters = [PriceObservation.observed_at >= start, PriceObservation.observed_at <= end]
    if category_id is not None:
        filters.append((Product.category_id == category_id) | (StoreProduct.category_id == category_id))
    if store_id is not None:
        filters.append(StoreProduct.store_id == store_id)
    if product_id is not None:
        filters.append(Product.id == product_id)
    filters.extend((~Product.name.like("DEMO PriceScope %"), ~Store.name.like("DEMO PriceScope %")))
    rows = session.execute(
        select(PriceObservation, StoreProduct, Product)
        .join(StoreProduct, StoreProduct.id == PriceObservation.store_product_id)
        .join(Product, Product.id == StoreProduct.product_id)
        .join(Store, Store.id == StoreProduct.store_id)
        .where(*filters)
        .order_by(PriceObservation.observed_at, PriceObservation.id)
    ).all()
    by_listing: dict[int, list[tuple[PriceObservation, StoreProduct, Product]]] = {}
    for row in rows:
        by_listing.setdefault(row[1].id, []).append(row)

    product_rates: dict[tuple[int, str], list[Decimal]] = {}
    product_details: dict[tuple[int, str], dict[str, object]] = {}
    listing_counts_by_currency: dict[str, int] = {}
    for history in by_listing.values():
        currencies = {row[0].currency for row in history}
        if len(history) < 2 or len(currencies) != 1:
            continue
        first, last = history[0][0], history[-1][0]
        if first.observed_at == last.observed_at:
            continue
        initial = _effective_price(first)
        final = _effective_price(last)
        if initial <= 0:
            continue
        product = history[0][2]
        currency = first.currency
        key = (product.id, currency)
        product_rates.setdefault(key, []).append((final - initial) / initial * Decimal("100"))
        detail = product_details.setdefault(key, {
            "product_id": product.id,
            "product_name": product.name,
            "category_id": product.category_id or history[0][1].category_id,
            "currency": currency,
            "listings": [],
        })
        detail["listings"].append({
            "store_product_id": history[0][1].id,
            "initial_price": str(initial),
            "final_price": str(final),
            "initial_observed_at": first.observed_at,
            "final_observed_at": last.observed_at,
        })
        listing_counts_by_currency[currency] = listing_counts_by_currency.get(currency, 0) + 1

    products = []
    category_values: dict[tuple[int | None, str], list[Decimal]] = {}
    currency_values: dict[str, list[Decimal]] = {}
    for key, changes in product_rates.items():
        average = sum(changes, Decimal("0")) / Decimal(len(changes))
        detail = {**product_details[key], "status": "available", "inflation_percent": str(average), "listings_count": len(changes)}
        products.append(detail)
        category_values.setdefault((detail["category_id"], key[1]), []).append(average)
        currency_values.setdefault(key[1], []).append(average)

    currencies = []
    for currency, changes in sorted(currency_values.items()):
        fx_change = None
        fx_status = "not_applicable" if currency != "ARS" else "insufficient_data"
        if currency == "ARS":
            side = "sell" if rate_type == "parallel" else "reference"
            rates = session.scalars(select(ExchangeRate).where(
                ExchangeRate.rate_type == rate_type,
                ExchangeRate.rate_side == side,
                ExchangeRate.base_currency == "USD",
                ExchangeRate.quote_currency == "ARS",
                ExchangeRate.observed_at >= start,
                ExchangeRate.observed_at <= end,
            ).order_by(ExchangeRate.observed_at, ExchangeRate.id)).all()
            by_source: dict[str, list[ExchangeRate]] = {}
            for rate in rates:
                by_source.setdefault(rate.source, []).append(rate)
            comparable = [series for series in by_source.values()
                          if len(series) >= 2 and series[0].observed_at != series[-1].observed_at]
            if comparable:
                fx_series = max(comparable, key=lambda series: (len(series), series[-1].observed_at, series[0].source))
                if fx_series[0].rate > 0:
                    fx_change = (fx_series[-1].rate - fx_series[0].rate) / fx_series[0].rate * Decimal("100")
                fx_status = "available"
        average_inflation = sum(changes, Decimal("0")) / Decimal(len(changes))
        currencies.append({
            "currency": currency,
            "status": "available",
            "inflation_percent": str(average_inflation),
            "fx_rate_type": rate_type if currency == "ARS" else None,
            "fx_variation_percent": str(fx_change) if fx_change is not None else None,
            "price_minus_fx_percentage_points": str(average_inflation - fx_change) if fx_change is not None else None,
            "fx_status": fx_status,
            "products_count": len(changes),
            "listings_count": listing_counts_by_currency[currency],
        })

    categories = [{
        "category_id": category,
        "currency": currency,
        "status": "available",
        "inflation_percent": str(sum(changes, Decimal("0")) / Decimal(len(changes))),
        "products_count": len(changes),
    } for (category, currency), changes in sorted(category_values.items(), key=lambda pair: (pair[0][1], pair[0][0] or 0))]
    products.sort(key=lambda item: item["product_name"])
    return {
        "status": "available" if products else "insufficient_data",
        "message": None if products else "No hay dos observaciones comparables por publicación y moneda dentro del período.",
        "start": start,
        "end": end,
        "method": "promedio aritmético equiponderado de variaciones por publicación; precios efectivos promocionales cuando existen",
        "currencies": currencies,
        "categories": categories,
        "products": products,
    }
