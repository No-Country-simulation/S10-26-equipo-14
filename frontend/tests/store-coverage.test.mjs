import assert from "node:assert/strict"
import test from "node:test"

import { canExtractStore, coverageLabel, hasRecentVerifiedCoverage } from "../src/lib/storeCoverage.js"

test("coverage labels distinguish partial, failed, empty, and operational states", () => {
  assert.equal(coverageLabel("partial"), "Cobertura parcial")
  assert.equal(coverageLabel("failed"), "Última extracción fallida")
  assert.equal(coverageLabel("no_data"), "Extracción exitosa sin observaciones")
  assert.equal(coverageLabel("operational"), "Operativa")
})

test("extraction is enabled only for an authenticated, active configured store", () => {
  const eligible = { is_active: true, connector_configured: true }
  assert.equal(canExtractStore(eligible, true), true)
  assert.equal(canExtractStore(eligible, false), false)
  assert.equal(canExtractStore({ ...eligible, is_active: false }, true), false)
  assert.equal(canExtractStore({ ...eligible, connector_configured: false }, true), false)
  assert.equal(canExtractStore(eligible, true, true), false)
})

test("public operational coverage requires recent successful extraction and an available connector", () => {
  const now = Date.parse("2026-11-12T12:00:00Z")
  const valid = {
    is_active: true, connector_available: true, is_operational: true,
    coverage_status: "operational", last_extraction_status: "SUCCESS",
    operational_at: "2026-11-11T12:00:00Z",
  }
  assert.equal(hasRecentVerifiedCoverage(valid, now), true)
  assert.equal(hasRecentVerifiedCoverage({ ...valid, last_extraction_status: "FAILED" }, now), false)
  assert.equal(hasRecentVerifiedCoverage({ ...valid, is_active: false }, now), false)
  assert.equal(hasRecentVerifiedCoverage({ ...valid, connector_available: false }, now), false)
  assert.equal(hasRecentVerifiedCoverage({ ...valid, operational_at: "2026-11-09T11:59:59Z" }, now), false)
})
