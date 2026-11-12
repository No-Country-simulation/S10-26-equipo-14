export interface ExtractionRun {
  run_id: number
  store_id: number
  store_name: string
  source: string
  status: string
  started_at: string
  finished_at: string | null
  records_seen: number
  observations_created: number
  error_summary: string | null
}
