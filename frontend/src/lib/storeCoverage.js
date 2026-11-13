const COVERAGE_LABELS = {
  inactive: "Registrada · inactiva",
  no_connector: "Pendiente de integración",
  connector_unverified: "Conector genérico sin verificar",
  no_listings: "Faltan publicaciones válidas",
  pending: "Pendiente de primera extracción",
  running: "Extracción en curso",
  partial: "Cobertura parcial",
  failed: "Última extracción fallida",
  no_data: "Extracción exitosa sin observaciones",
  operational: "Operativa",
}

export function coverageLabel(status) {
  return COVERAGE_LABELS[status] ?? "Estado de cobertura desconocido"
}

export function canExtractStore(store, canManage, busy = false) {
  return Boolean(canManage && !busy && store.is_active && store.connector_configured)
}

export function hasRecentVerifiedCoverage(store, now = Date.now()) {
  if (!store?.is_active || !store.connector_available || !store.is_operational ||
      store.coverage_status !== "operational" || store.last_extraction_status !== "SUCCESS" || !store.operational_at) return false
  const observedAt = Date.parse(store.operational_at)
  const age = now - observedAt
  return Number.isFinite(age) && age >= 0 && age <= 48 * 60 * 60 * 1000
}
