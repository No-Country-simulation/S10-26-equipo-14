import assert from "node:assert/strict"
import test from "node:test"

import { canExtractStore, coverageLabel } from "../src/lib/storeCoverage.js"

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
