export type CoverageStatus =
  | "inactive" | "no_connector" | "connector_unverified" | "no_listings"
  | "pending" | "running" | "partial" | "failed" | "no_data" | "operational"

export function coverageLabel(status: CoverageStatus): string
export function canExtractStore(
  store: { is_active: boolean; connector_configured: boolean },
  canManage: boolean,
  busy?: boolean,
): boolean
export function hasRecentVerifiedCoverage(
  store: {
    is_active: boolean
    connector_available: boolean
    is_operational: boolean
    coverage_status: CoverageStatus
    last_extraction_status: string | null
    operational_at: string | null
  },
  now?: number,
): boolean
