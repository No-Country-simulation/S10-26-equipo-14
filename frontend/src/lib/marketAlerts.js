const ERROR_STATUSES = new Set(["BLOCKED", "NETWORK_ERROR", "RATE_LIMITED", "PRODUCT_NOT_FOUND", "PRICE_NOT_FOUND", "UNSUPPORTED", "LOCATION_REQUIRED", "FAILED", "ERROR", "ABANDONED"])
const STALE_AFTER_HOURS = 48

export async function loadResource(request) {
  try {
    const data = await request
    const empty = Array.isArray(data) ? data.length === 0 : data == null
    return { status: empty ? "empty" : "available", data, error: null }
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") throw error
    return {
      status: "error",
      data: null,
      error: error instanceof Error ? error.message : "Error de API sin detalle.",
    }
  }
}

export function reachedRecordLimit(rows, limit = 1000) {
  return Array.isArray(rows) && rows.length >= limit
}

function effectivePrice(row) {
  const amount = Number(row.amount)
  const promo = row.promotional_price === null ? null : Number(row.promotional_price)
  return promo !== null && promo <= amount ? promo : amount
}

function percentChange(previous, current) {
  return previous > 0 ? ((current - previous) / previous) * 100 : null
}

export function deriveMarketAlerts(input) {
  const now = input.now ?? Date.now()
  const products = new Map(input.products.filter((product) => !product.name.startsWith("DEMO PriceScope ")).map((product) => [product.id, product]))
  const listings = new Map(input.listings.filter((listing) => {
    if (listing.product_id === null || listing.product_name.startsWith("DEMO PriceScope ")) return false
    const product = products.get(listing.product_id)
    return Boolean(product && (input.categoryId == null || listing.category_id === input.categoryId || product.category_id === input.categoryId))
  }).map((listing) => [listing.id, listing]))
  const stores = new Map(input.stores.filter((store) => !store.name.startsWith("DEMO PriceScope ")).map((store) => [store.id, store]))
  const byListing = new Map()
  for (const row of input.observations.filter((item) => item.is_available !== false && listings.has(item.store_product_id))) {
    byListing.set(row.store_product_id, [...(byListing.get(row.store_product_id) ?? []), row])
  }

  const alerts = []
  const seen = new Set()
  const add = (alert) => { if (!seen.has(alert.key)) { seen.add(alert.key); alerts.push(alert) } }
  for (const [listingId, rows] of byListing) {
    const listing = listings.get(listingId)
    const product = listing?.product_id == null ? undefined : products.get(listing.product_id)
    const store = listing ? stores.get(listing.store_id) : undefined
    if (!listing || !product || !store) continue
    const history = rows.filter((row) => Number.isFinite(Date.parse(row.observed_at)))
      .sort((a, b) => Date.parse(a.observed_at) - Date.parse(b.observed_at) || a.id - b.id)
    if (history.length === 0) continue
    const latest = history.at(-1)
    if (now - Date.parse(latest.observed_at) > STALE_AFTER_HOURS * 3600000) add({
      key: `stale:${listingId}:${latest.id}`, kind: "stale_price", title: "Precio desactualizado",
      detail: `La última observación supera ${STALE_AFTER_HOURS} horas.`, storeName: store.name,
      productName: product.name, observedAt: latest.observed_at, sourceUrl: latest.source_url,
    })
    if (history.length < 2) continue
    let minimum = Number.POSITIVE_INFINITY
    for (let index = 0; index < history.length; index += 1) {
      const current = history[index]
      if (current.currency !== history[0].currency) continue
      const currentPrice = effectivePrice(current)
      if (currentPrice < minimum) {
        if (index > 0) add({
          key: `minimum:${listingId}:${current.id}`, kind: "new_minimum", title: "Nuevo mínimo observado",
          detail: `Nuevo mínimo del período (${current.currency} ${currentPrice.toLocaleString("es-AR")}).`,
          storeName: store.name, productName: product.name, currentValue: `${current.currency} ${currentPrice}`,
          observedAt: current.observed_at, sourceUrl: current.source_url,
        })
        minimum = currentPrice
      }
      if (index === 0) continue
      const previous = history[index - 1]
      if (previous.currency !== current.currency) continue
      const previousPrice = effectivePrice(previous)
      const change = percentChange(previousPrice, currentPrice)
      if (change === null || Math.abs(change) < input.threshold) continue
      const increase = change > 0
      add({
        key: `${increase ? "up" : "down"}:${listingId}:${current.id}`,
        kind: increase ? "price_up" : "price_down",
        title: increase ? "Subida de precio" : "Bajada de precio",
        detail: `Variación ${change > 0 ? "+" : ""}${change.toLocaleString("es-AR", { maximumFractionDigits: 2 })}% · umbral ${input.threshold}%`,
        storeName: store.name, productName: product.name,
        previousValue: `${previous.currency} ${previousPrice}`, currentValue: `${current.currency} ${currentPrice}`,
        changePercent: change, previousAt: previous.observed_at, observedAt: current.observed_at,
        sourceUrl: current.source_url,
      })
    }
  }

  const rateGroups = new Map()
  for (const rate of input.rates.filter((item) => item.base_currency === "USD" && item.quote_currency === "ARS" &&
    !/demo|synthetic|sint[eé]tic/i.test(item.source))) {
    const side = rate.rate_type === "parallel" ? "sell" : "reference"
    if (rate.rate_side !== side) continue
    const key = `${rate.rate_type}:${rate.rate_side}:${rate.source}`
    rateGroups.set(key, [...(rateGroups.get(key) ?? []), rate])
  }
  for (const [key, rows] of rateGroups) {
    const history = [...rows].sort((a, b) => Date.parse(a.observed_at) - Date.parse(b.observed_at) || a.id - b.id)
    if (history.length >= 2) {
      const previous = history.at(-2)
      const current = history.at(-1)
      const change = percentChange(Number(previous.rate), Number(current.rate))
      if (change !== null && Math.abs(change) >= input.threshold) add({
        key: `fx:${key}:${current.id}`, kind: "fx_change", title: "Variación cambiaria",
        detail: `${current.rate_type} · ${current.rate_side} · ${change > 0 ? "+" : ""}${change.toLocaleString("es-AR", { maximumFractionDigits: 2 })}% · umbral ${input.threshold}%`,
        previousValue: `ARS ${previous.rate}`, currentValue: `ARS ${current.rate}`,
        previousAt: previous.observed_at, observedAt: current.observed_at, source: current.source,
      })
    }
    const latest = history.at(-1)
    if (now - Date.parse(latest.observed_at) > STALE_AFTER_HOURS * 3600000) add({
      key: `stale-fx:${key}:${latest.id}`, kind: "stale_fx", title: "Cotización desactualizada",
      detail: `${latest.rate_type} USD/ARS · última actualización de ${latest.source}.`,
      observedAt: latest.observed_at, source: latest.source,
    })
  }

  for (const store of input.stores.filter((item) => !item.name.startsWith("DEMO PriceScope ") &&
    item.last_extraction_status && (input.storeId == null || item.id === input.storeId))) {
    const status = store.last_extraction_status.toUpperCase()
    const kind = status === "PARTIAL_SUCCESS" ? "extraction_partial"
      : status === "SUCCESS" ? "extraction_success"
      : ERROR_STATUSES.has(status) ? "extraction_failed" : null
    if (kind) add({
      key: `run:${store.id}:${store.last_extraction_at}:${status}`, kind,
      title: kind === "extraction_partial" ? "Extracción parcial" : kind === "extraction_failed" ? "Falló la última extracción" : "Última extracción exitosa",
      detail: `Estado real de la ejecución más reciente: ${status}.`, storeName: store.name,
      observedAt: store.last_extraction_at ?? undefined,
    })
  }
  return alerts.sort((a, b) => Date.parse(b.observedAt ?? "") - Date.parse(a.observedAt ?? ""))
}
