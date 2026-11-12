import type { PricedProduct } from "@/types"

interface CatalogProductSummaryProps {
  product: PricedProduct
}

function priceText(amount: string, currency: string) {
  try {
    return new Intl.NumberFormat("es-AR", { style: "currency", currency }).format(Number(amount))
  } catch {
    return `${amount} ${currency}`
  }
}

function quantityText(value: string) {
  const quantity = Number(value)
  return Number.isFinite(quantity)
    ? new Intl.NumberFormat("es-AR", { maximumFractionDigits: 6 }).format(quantity)
    : value
}

function unavailableReasonText(reason: string | null | undefined) {
  switch (reason) {
    case "missing_package_quantity":
    case "missing_package_unit":
    case "missing_package_count":
    case "missing_product":
      return "Faltan datos de presentación"
    case "unsupported_package_unit":
    case "incompatible_dimensions":
      return "La unidad no es comparable"
    case "invalid_package_quantity":
    case "invalid_package_count":
    case "invalid_price":
      return "Datos insuficientes o inválidos"
    case "unsupported_currency":
      return "Moneda no admitida para normalización"
    default:
      return "Precio por unidad no disponible"
  }
}

function presentation(product: PricedProduct) {
  const { package_quantity: quantity, package_unit: unit, package_count: count } = product
  if (quantity == null && unit == null && count == null) return "Presentación no informada"
  if (quantity == null || unit == null) return "Presentación incompleta"

  const original = `${quantityText(quantity)} ${unit}`
  const packageText = count == null
    ? `${original} · multiplicidad no informada`
    : count > 1 ? `${count} × ${original}` : original
  if (product.normalized_quantity && product.normalized_unit) {
    return `${packageText} (${quantityText(product.normalized_quantity)} ${product.normalized_unit} en total)`
  }
  return packageText
}

function observedDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? "Fecha no disponible" : date.toLocaleString()
}

export default function CatalogProductSummary({ product }: CatalogProductSummaryProps) {
  const price = product.latest_price
  if (!price) return <span className="text-sm text-slate-500">Sin observaciones de precio</span>
  const isSyntheticDemo = price.store_name.trim().toLocaleUpperCase("es-AR").startsWith("DEMO ")

  return (
    <div className="space-y-1">
      {isSyntheticDemo && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-900">
          Datos sintéticos de demostración; no son precios actuales
        </p>
      )}
      <p className="font-semibold tabular-nums text-slate-900">
        {priceText(price.amount, price.currency)}
      </p>
      {price.promotional_price && (
        <p className="text-xs text-emerald-800">
          Promoción publicada: {priceText(price.promotional_price, price.currency)}
        </p>
      )}
      {price.normalized_price && price.normalized_unit ? (
        <p className="text-sm font-medium text-indigo-800">
          {priceText(price.normalized_price, price.currency)} / {price.normalized_unit}
        </p>
      ) : (
        <p className="text-xs text-slate-500">
          {unavailableReasonText(price.normalization_unavailable_reason)}
        </p>
      )}
      {price.normalized_promotional_price && price.normalized_unit && (
        <p className="text-xs text-emerald-800">
          Promoción normalizada: {priceText(price.normalized_promotional_price, price.currency)} / {price.normalized_unit}
        </p>
      )}
      {price.promotional_normalization_unavailable_reason && (
        <p className="text-xs text-amber-700">Precio promocional no comparable</p>
      )}
      <p className="text-xs text-slate-600">
        {price.is_available === true ? "Disponible" :
          price.is_available === false ? "Agotado" : "Disponibilidad no informada"}
        {" · "}{price.store_name}
      </p>
      <p className="text-xs text-slate-500">Actualizado {observedDate(price.observed_at)}</p>
      {price.source_url && (
        <a href={price.source_url} target="_blank" rel="noreferrer" className="text-xs text-indigo-700 hover:underline">
          Ver publicación
        </a>
      )}
    </div>
  )
}

export function CatalogPresentation({ product }: CatalogProductSummaryProps) {
  return <span className="text-slate-700">{presentation(product)}</span>
}
