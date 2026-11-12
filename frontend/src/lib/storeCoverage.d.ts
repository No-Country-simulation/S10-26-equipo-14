export type CoverageStatus =
  | "inactive" | "no_connector" | "connector_unverified" | "no_listings"
  | "pending" | "running" | "partial" | "failed" | "no_data" | "operational"

export function coverageLabel(status: CoverageStatus): string
export function canExtractStore(
  store: { is_active: boolean; connector_configured: boolean },
  canManage: boolean,
  busy?: boolean,
): boolean
