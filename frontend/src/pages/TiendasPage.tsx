import { useCallback, useEffect, useState } from 'react'
import { Activity, AlertCircle, Check, ChevronRight, CircleHelp, Globe2, History, LoaderCircle, Plus, Play, RefreshCw, Store as StoreIcon } from 'lucide-react'
import { apiClient, ApiError, type CreateStoreProductInput } from '@/lib/api'
import { canExtractStore, coverageLabel, hasRecentVerifiedCoverage } from '@/lib/storeCoverage.js'
import type { Category } from '@/types/category'
import type { CreateStoreInput, ManagedStore, StoreCategoryCandidate, StoreMonitoringInput } from '@/types/store'
import type { ExtractionRun, PriceObservation } from '@/types'
import type { StoreProduct } from '@/types/storeProduct'

const STATUS_LABELS: Record<ManagedStore['integration_status'], string> = {
  pending: 'Pendiente de análisis',
  analyzing: 'Analizando sitio',
  configuration_required: 'Requiere configuración',
  active: 'Configuración activa',
  error: 'Error de análisis',
}

const STATUS_STYLES: Record<ManagedStore['integration_status'], string> = {
  pending: 'bg-slate-100 text-slate-700',
  analyzing: 'bg-blue-100 text-blue-800',
  configuration_required: 'bg-amber-100 text-amber-900',
  active: 'bg-emerald-100 text-emerald-800',
  error: 'bg-rose-100 text-rose-800',
}

function formatDate(value: string | null) {
  if (!value) return 'Todavía no se registró una extracción.'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : date.toLocaleString()
}

function runState(run: ExtractionRun) {
  if (run.status === 'SUCCESS' || run.status === 'succeeded') return run.observations_created > 0 ? 'Completado' : 'Sin resultados nuevos'
  if (run.status === 'PARTIAL_SUCCESS' || run.status === 'partial') return 'Completado con errores'
  if (run.status === 'PRICE_NOT_FOUND' || run.status === 'PRODUCT_NOT_FOUND') return 'Sin resultados'
  return 'Error'
}

function errorText(error: unknown) {
  if (error instanceof ApiError && error.status === 403) {
    return 'Acceso administrativo no autorizado. Introduce la clave de administración válida para este entorno.'
  }
  if (error instanceof ApiError && error.status === 401) return 'El token administrativo fue rechazado. Verifica el acceso con el administrador del servicio.'
  if (error instanceof ApiError && error.status === 503) return 'La administración no está configurada en el backend. El responsable del servicio debe configurarla antes de habilitar escrituras.'
  return error instanceof Error ? error.message : 'Ocurrió un error inesperado.'
}

function StoreRegistrationForm({ onCreated, onCancel, adminToken }: {
  onCreated: (store: ManagedStore) => void
  onCancel: () => void
  adminToken?: string
}) {
  const [form, setForm] = useState<CreateStoreInput>({ name: '', base_url: '', country: '', currency: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const update = (field: keyof CreateStoreInput, value: string) => {
    setForm((current) => ({ ...current, [field]: field === 'currency' ? value.toUpperCase() : value }))
  }

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      onCreated(await apiClient.createStore(form, adminToken))
    } catch (cause) {
      setError(errorText(cause))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="mb-6 rounded-2xl border border-indigo-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Agregar una tienda</h2>
        <p className="mt-1 text-sm text-slate-600">Registra el sitio oficial. Después revisaremos qué información pública puede analizar PriceScope.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-medium text-slate-700">
          Nombre de la tienda
          <input required maxLength={150} value={form.name} onChange={(event) => update('name', event.target.value)} placeholder="Nombre comercial" className="mt-1.5 block h-10 w-full rounded-lg border border-slate-300 px-3 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Sitio web oficial
          <input required type="url" maxLength={300} value={form.base_url} onChange={(event) => update('base_url', event.target.value)} placeholder="https://tienda.example" className="mt-1.5 block h-10 w-full rounded-lg border border-slate-300 px-3 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
          <span className="mt-1 block text-xs font-normal text-slate-500">Usa la página principal HTTPS, sin una URL de producto.</span>
        </label>
        <label className="text-sm font-medium text-slate-700">
          País
          <input required maxLength={100} value={form.country} onChange={(event) => update('country', event.target.value)} placeholder="País donde opera" className="mt-1.5 block h-10 w-full rounded-lg border border-slate-300 px-3 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
        </label>
        <label className="text-sm font-medium text-slate-700">
          Moneda de referencia
          <input required minLength={3} maxLength={3} pattern="[A-Za-z]{3}" value={form.currency} onChange={(event) => update('currency', event.target.value)} placeholder="Código ISO, por ejemplo ARS" className="mt-1.5 block h-10 w-full rounded-lg border border-slate-300 px-3 font-normal uppercase outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
        </label>
      </div>
      {error && <p role="alert" className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <button type="button" onClick={onCancel} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">Cancelar</button>
        <button disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
          {saving && <LoaderCircle className="h-4 w-4 animate-spin" />}{saving ? 'Guardando…' : 'Registrar tienda'}
        </button>
      </div>
    </form>
  )
}

function StoreCard({ store, categories, onUpdated, onReload, canManage, adminToken }: {
  store: ManagedStore
  categories: Category[]
  onUpdated: (store: ManagedStore) => void
  onReload: () => void
  canManage: boolean
  adminToken?: string
}) {
  const [analyzing, setAnalyzing] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [extractResult, setExtractResult] = useState<ExtractionRun | null>(null)
  const [history, setHistory] = useState<ExtractionRun[]>([])
  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [observationsByRun, setObservationsByRun] = useState<Record<number, PriceObservation[]>>({})
  const [observationsLoading, setObservationsLoading] = useState<number | null>(null)
  const [storeProducts, setStoreProducts] = useState<StoreProduct[]>([])
  const [listingName, setListingName] = useState('')
  const [listingUrl, setListingUrl] = useState('')
  const [listingCurrency, setListingCurrency] = useState(store.currency)
  const [listingSaving, setListingSaving] = useState(false)
  const [selected, setSelected] = useState<number[]>(store.category_ids)
  const [currency, setCurrency] = useState(store.currency)
  const [interval, setInterval] = useState(store.interval_hours)
  const matchedCandidates: StoreCategoryCandidate[] = store.analysis_candidates.filter((candidate) => candidate.category_id !== null)

  const loadHistory = async () => {
    setHistoryLoading(true)
    try {
      setHistory(await apiClient.fetchStoreExtractions(store.id, 10, undefined, adminToken))
    } catch (cause) {
      setError(errorText(cause))
    } finally {
      setHistoryLoading(false)
    }
  }

  const extract = async () => {
    setExtracting(true)
    setError(null)
    setExtractResult(null)
    try {
      const result = await apiClient.extractStore(store.id, adminToken)
      setExtractResult(result)
      setHistoryOpen(true)
      await loadHistory()
      onReload()
    } catch (cause) {
      setError(errorText(cause))
    } finally {
      setExtracting(false)
    }
  }

  const loadRunObservations = async (run: ExtractionRun) => {
    setObservationsLoading(run.run_id)
    try {
      const rows = await apiClient.fetchRunObservations(store.id, run.run_id, 1000, undefined, adminToken)
      setObservationsByRun((current) => ({ ...current, [run.run_id]: rows }))
    } catch (cause) {
      setError(errorText(cause))
    } finally {
      setObservationsLoading(null)
    }
  }

  const analyze = async () => {
    setAnalyzing(true)
    setError(null)
    try {
      const updated = await apiClient.analyzeStore(store.id, adminToken)
      onUpdated(updated)
      setSelected(updated.category_ids)
    } catch (cause) {
      setError(errorText(cause))
    } finally {
      setAnalyzing(false)
    }
  }

  const savePreferences = async (enabled: boolean) => {
    setSaving(true)
    setError(null)
    const input: StoreMonitoringInput = {
      category_ids: selected,
      currency,
      interval_hours: interval,
      enabled,
    }
    try {
      onUpdated(await apiClient.saveStoreMonitoring(store.id, input, adminToken))
    } catch (cause) {
      setError(errorText(cause))
    } finally {
      setSaving(false)
    }
  }

  const toggleCategory = (id: number) => {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
  }

  const loadListings = async () => {
    try { setStoreProducts(await apiClient.fetchStoreProducts(store.id)) }
    catch (cause) { setError(errorText(cause)) }
  }

  const addListing = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setListingSaving(true)
    setError(null)
    const input: CreateStoreProductInput = { product_url: listingUrl.trim(), product_name: listingName.trim(), currency: listingCurrency.toUpperCase() }
    try {
      await apiClient.createStoreProduct(store.id, input, adminToken)
      setListingUrl(''); setListingName('')
      await loadListings()
    } catch (cause) { setError(errorText(cause)) }
    finally { setListingSaving(false) }
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div className="flex min-w-0 gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700"><StoreIcon className="h-5 w-5" /></span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-lg font-semibold text-slate-900">{store.name}</h2>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">Registrada</span>
              <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${store.coverage_status === 'operational' ? 'bg-emerald-100 text-emerald-800' : store.coverage_status === 'partial' ? 'bg-amber-100 text-amber-900' : store.coverage_status === 'failed' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-700'}`}>
                {coverageLabel(store.coverage_status)}
              </span>
              <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_STYLES[store.integration_status]}`}>
                {store.integration_status === 'analyzing' && <LoaderCircle className="mr-1 inline h-3.5 w-3.5 animate-spin" />}
                {STATUS_LABELS[store.integration_status]}
              </span>
            </div>
            <a className="mt-1 inline-flex items-center gap-1 break-all text-sm text-indigo-700 hover:underline" href={store.base_url} target="_blank" rel="noreferrer"><Globe2 className="h-3.5 w-3.5 shrink-0" />{store.base_url}</a>
            <p className="mt-1 text-sm text-slate-500">{store.country ?? 'País no especificado'} · moneda {store.currency}{store.connector_name ? ` · conector ${store.connector_name}` : ''}</p>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <button type="button" onClick={extract} disabled={!canExtractStore(store, canManage, extracting)} title={!canManage ? 'Introduce la clave de administración para habilitar esta acción.' : store.extraction_disabled_reason ?? undefined} className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60">
            {extracting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {extracting ? 'Extrayendo…' : 'Ejecutar extracción'}
          </button>
          <button type="button" onClick={analyze} disabled={!canManage || analyzing} title={!canManage ? 'Introduce la clave de administración para habilitar esta acción.' : undefined} className="inline-flex items-center justify-center gap-2 rounded-lg border border-indigo-200 px-3.5 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60">
            {analyzing ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            {analyzing ? 'Analizando…' : store.integration_status === 'pending' ? 'Analizar sitio' : 'Repetir análisis'}
          </button>
        </div>
      </div>

      {!store.connector_configured && (
        <p className="mt-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{store.extraction_disabled_reason ?? 'La extracción se habilitará cuando el conector esté configurado.'}</p>
      )}

      <div className="mt-5 grid gap-3 border-t border-slate-100 pt-4 text-sm sm:grid-cols-2">
        <p className="text-slate-600"><span className="font-medium text-slate-800">Última extracción:</span> {formatDate(store.last_extraction_at)}{store.last_extraction_status ? ` · ${store.last_extraction_status}` : ''}</p>
        <p className="text-slate-600"><span className="font-medium text-slate-800">Último análisis:</span> {formatDate(store.last_analysis_at)}</p>
      </div>

      {(extracting || extractResult) && (
        <div className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50 p-3 text-sm text-indigo-950" role="status">
          {extracting ? (
            <span className="inline-flex items-center gap-2"><LoaderCircle className="h-4 w-4 animate-spin" />Extracción ejecutándose…</span>
          ) : extractResult ? (
            <>
              <p className="font-semibold">{runState(extractResult)}</p>
              <p className="mt-1">Productos procesados: {extractResult.records_seen} · Observaciones generadas: {extractResult.observations_created}</p>
              {extractResult.status !== 'SUCCESS' && extractResult.status !== 'succeeded' && extractResult.error_summary && (
                <p className="mt-1 break-words text-rose-800">{extractResult.error_summary}</p>
              )}
            </>
          ) : null}
        </div>
      )}

      <div className="mt-4">
        <button type="button" onClick={() => {
          const open = !historyOpen
          setHistoryOpen(open)
          if (open) void loadHistory()
        }} className="inline-flex items-center gap-2 text-sm font-semibold text-indigo-700 hover:underline">
          <History className="h-4 w-4" />{historyOpen ? 'Ocultar historial' : 'Ver historial de extracciones'}
        </button>
        {historyOpen && (
          <div className="mt-3 rounded-xl border border-slate-200 p-4">
            <h3 className="font-semibold text-slate-900">Últimas extracciones</h3>
            {historyLoading ? <p className="mt-2 text-sm text-slate-500">Cargando historial…</p> : history.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">Todavía no hay ejecuciones para esta tienda.</p>
            ) : (
              <ul className="mt-3 divide-y divide-slate-100">
                {history.map((run) => (
                  <li key={run.run_id} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium text-slate-800">{formatDate(run.started_at)} · {runState(run)}</p>
                      <button type="button" disabled={observationsLoading === run.run_id} onClick={() => void loadRunObservations(run)} className="text-xs font-semibold text-indigo-700 hover:underline disabled:opacity-50">
                        {observationsLoading === run.run_id ? 'Cargando…' : 'Consultar observaciones'}
                      </button>
                    </div>
                    <p className="mt-1 text-xs text-slate-600">Productos procesados: {run.records_seen} · Observaciones generadas: {run.observations_created}</p>
                    {run.status !== 'SUCCESS' && run.status !== 'succeeded' && run.error_summary && <p className="mt-1 break-words text-xs text-rose-700">{run.error_summary}</p>}
                    {observationsByRun[run.run_id] && (
                      observationsByRun[run.run_id].length ? (
                        <ul className="mt-2 space-y-1 rounded-lg bg-slate-50 p-3 text-xs text-slate-700">
                          {observationsByRun[run.run_id].map((observation) => (
                            <li key={observation.id}>
                              <span className="font-semibold">{observation.amount} {observation.currency}</span>
                              {` · ${formatDate(observation.observed_at)}`}
                              {observation.source_url && <a className="ml-2 text-indigo-700 hover:underline" href={observation.source_url} target="_blank" rel="noreferrer">Ver origen</a>}
                            </li>
                          ))}
                        </ul>
                      ) : <p className="mt-2 text-xs text-slate-500">Esta ejecución no generó observaciones.</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="mt-5 rounded-xl border border-slate-200 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div><h3 className="font-semibold text-slate-900">Publicaciones de producto</h3><p className="mt-1 text-sm text-slate-600">Usa una URL HTTPS pública del mismo comercio. Los errores se registran por publicación.</p></div>
          <button type="button" onClick={() => void loadListings()} className="text-sm font-semibold text-indigo-700 hover:underline">Consultar publicaciones</button>
        </div>
        {storeProducts.length > 0 && <ul className="mt-3 space-y-2">{storeProducts.map((listing) => <li key={listing.id} className="rounded-lg bg-slate-50 p-3 text-sm"><p className="font-medium text-slate-800">{listing.product_name} · {listing.currency}</p><a href={listing.product_url} target="_blank" rel="noreferrer" className="break-all text-xs text-indigo-700 hover:underline">{listing.product_url}</a></li>)}</ul>}
        {storeProducts.length === 0 && <p className="mt-3 text-sm text-slate-500">No hay publicaciones cargadas o todavía no se consultaron.</p>}
        {canManage && <form onSubmit={addListing} className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">Nombre publicado<input required maxLength={250} value={listingName} onChange={(event) => setListingName(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-3 font-normal" /></label>
          <label className="text-sm font-medium text-slate-700">URL pública del producto<input required type="url" value={listingUrl} onChange={(event) => setListingUrl(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-3 font-normal" /></label>
          <label className="text-sm font-medium text-slate-700">Moneda ISO<input required pattern="[A-Za-z]{3}" maxLength={3} value={listingCurrency} onChange={(event) => setListingCurrency(event.target.value.toUpperCase())} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-3 uppercase font-normal" /></label>
          <button disabled={listingSaving} className="self-end rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{listingSaving ? 'Guardando…' : 'Agregar publicación'}</button>
        </form>}
      </div>

      {store.analysis_message && <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">{store.analysis_message}</p>}
      {error && <div role="alert" className="mt-3 flex items-start gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-800"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}

      {store.integration_status !== 'pending' && store.integration_status !== 'analyzing' && (
        <div className="mt-5 rounded-xl border border-slate-200 p-4">
          <div className="flex items-start gap-2">
            <Activity className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" />
            <div>
              <h3 className="font-semibold text-slate-900">Configurar monitoreo</h3>
              <p className="mt-1 text-sm text-slate-600">Elige categorías reconocidas por el catálogo y define la frecuencia deseada.</p>
            </div>
          </div>

          {store.analysis_candidates.length > 0 ? (
            <ul className="mt-4 space-y-2">
              {store.analysis_candidates.map((candidate, index) => {
                const category = candidate.category_id === null ? undefined : categories.find((item) => item.id === candidate.category_id)
                return (
                  <li key={`${candidate.source_url}-${index}`} className="flex items-start gap-3 rounded-lg bg-slate-50 p-3">
                    {candidate.category_id !== null && category ? (
                      <input aria-label={`Monitorear ${candidate.name}`} type="checkbox" checked={selected.includes(candidate.category_id)} disabled={!canManage} onChange={() => toggleCategory(candidate.category_id!)} className="mt-1 h-4 w-4 accent-indigo-600 disabled:cursor-not-allowed disabled:opacity-50" />
                    ) : <CircleHelp className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />}
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-slate-800">{candidate.name}</p>
                      <p className="text-xs text-slate-500">{category ? `Coincide con ${category.name}` : 'No coincide con una categoría existente; requiere revisión.'}</p>
                      <a className="mt-1 inline-flex items-center gap-1 break-all text-xs text-indigo-700 hover:underline" href={candidate.source_url} target="_blank" rel="noreferrer">Ver enlace observado<ChevronRight className="h-3 w-3" /></a>
                    </div>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">No hay categorías verificadas para seleccionar. Esta tienda necesita una integración específica antes de activarse.</p>
          )}

          <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <label className="text-sm font-medium text-slate-700">Moneda
              <input value={currency} maxLength={3} pattern="[A-Za-z]{3}" disabled={!canManage} onChange={(event) => setCurrency(event.target.value.toUpperCase())} className="mt-1 block h-9 w-full rounded-lg border border-slate-300 px-3 uppercase disabled:cursor-not-allowed disabled:bg-slate-100" />
            </label>
            <label className="text-sm font-medium text-slate-700">Revisar cada
              <select value={interval} disabled={!canManage} onChange={(event) => setInterval(Number(event.target.value))} className="mt-1 block h-9 w-full rounded-lg border border-slate-300 bg-white px-3 disabled:cursor-not-allowed disabled:bg-slate-100">
                <option value={24}>24 horas</option><option value={48}>48 horas</option><option value={168}>Cada semana</option>
              </select>
            </label>
            <button type="button" disabled={!canManage || saving || selected.length === 0 || matchedCandidates.length === 0} title={!canManage ? 'Disponible solo con el backend local.' : undefined} onClick={() => savePreferences(!store.monitoring_enabled)} className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">
              {saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              {store.monitoring_enabled ? 'Desactivar' : 'Activar monitoreo'}
            </button>
          </div>
          <p className="mt-3 text-xs text-slate-500">La activación guarda tus preferencias. La ejecución automática programada aún no está disponible; por ahora las extracciones siguen siendo manuales.</p>
        </div>
      )}
    </article>
  )
}

export default function TiendasPage() {
  const [adminAuthenticated, setAdminAuthenticated] = useState(false)
  const [adminTokenInput, setAdminTokenInput] = useState("")
  const [adminToken, setAdminToken] = useState("")
  const [adminAuthLoading, setAdminAuthLoading] = useState(false)
  const [adminAuthError, setAdminAuthError] = useState<string | null>(null)
  const canManage = import.meta.env.DEV || adminAuthenticated
  const [stores, setStores] = useState<ManagedStore[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [storesLoading, setStoresLoading] = useState(true)
  const [categoriesLoading, setCategoriesLoading] = useState(true)
  const [storesError, setStoresError] = useState<string | null>(null)
  const [categoriesError, setCategoriesError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [retry, setRetry] = useState(0)
  const visibleStores = canManage ? stores : stores.filter(hasRecentVerifiedCoverage)

  const load = useCallback(async (signal: AbortSignal) => {
    setStoresLoading(true)
    setCategoriesLoading(true)
    setStoresError(null)
    setCategoriesError(null)
    const storeRequest = apiClient.fetchManagedStores(signal)
      .then((managedStores) => { if (!signal.aborted) setStores(managedStores) })
      .catch((cause: unknown) => {
        if (!signal.aborted && !(cause instanceof Error && cause.name === 'AbortError')) setStoresError(errorText(cause))
      })
      .finally(() => { if (!signal.aborted) setStoresLoading(false) })
    const categoryRequest = apiClient.fetchCategories(signal)
      .then((knownCategories) => { if (!signal.aborted) setCategories(knownCategories) })
      .catch((cause: unknown) => {
        if (!signal.aborted && !(cause instanceof Error && cause.name === 'AbortError')) setCategoriesError(errorText(cause))
      })
      .finally(() => { if (!signal.aborted) setCategoriesLoading(false) })
    await Promise.all([storeRequest, categoryRequest])
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    queueMicrotask(() => {
      if (!controller.signal.aborted) void load(controller.signal)
    })
    return () => controller.abort()
  }, [load, retry])

  const updateStore = (updated: ManagedStore) => {
    setStores((current) => {
      const index = current.findIndex((store) => store.id === updated.id)
      if (index < 0) return [...current, updated].sort((left, right) => left.name.localeCompare(right.name))
      return current.map((store) => store.id === updated.id ? updated : store)
    })
  }

  const refreshStores = async () => {
    setStoresLoading(true)
    setStoresError(null)
    try {
      setStores(await apiClient.fetchManagedStores())
    } catch (cause) {
      setStoresError(errorText(cause))
    } finally {
      setStoresLoading(false)
    }
  }

  const connectAdmin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setAdminAuthLoading(true)
    setAdminAuthError(null)
    try {
      const valid = await apiClient.verifyAdminToken(adminTokenInput)
      if (!valid) {
        setAdminAuthError("La clave no es válida o la administración no está configurada en el servidor.")
        return
      }
      setAdminToken(adminTokenInput)
      setAdminAuthenticated(true)
      setAdminTokenInput("")
    } catch (cause) {
      setAdminAuthError(errorText(cause))
    } finally {
      setAdminAuthLoading(false)
    }
  }

  const disconnectAdmin = () => {
    setAdminToken("")
    setAdminAuthenticated(false)
  }

  const handleCreated = (created: ManagedStore) => {
    updateStore(created)
    setShowForm(false)
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-indigo-700">Administración</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">Tiendas</h1>
          <p className="mt-2 max-w-2xl text-slate-600">Registra un comercio, revisa lo que PriceScope puede detectar y decide qué categorías preparar para el monitoreo.</p>
        </div>
          <button type="button" disabled={!canManage} title={!canManage ? 'Introduce la clave de administración para habilitar esta acción.' : undefined} onClick={() => setShowForm((visible) => !visible)} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">
          <Plus className="h-4 w-4" />Agregar tienda
        </button>
      </header>

      {!import.meta.env.DEV && (
        <section className="rounded-xl border border-indigo-200 bg-white p-4 shadow-sm">
          {canManage ? (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-medium text-emerald-800">Acceso administrativo habilitado para esta sesión.</p>
              <button type="button" onClick={disconnectAdmin} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cerrar sesión administrativa</button>
            </div>
          ) : (
            <form onSubmit={connectAdmin} className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <label className="min-w-0 flex-1 text-sm font-medium text-slate-700">Clave de administración
                <input type="password" autoComplete="current-password" value={adminTokenInput} onChange={(event) => setAdminTokenInput(event.target.value)} required className="mt-1.5 block h-10 w-full rounded-lg border border-slate-300 px-3 font-normal" placeholder="Introduce la clave privada de administración" />
              </label>
              <button type="submit" disabled={adminAuthLoading || !adminTokenInput.trim()} className="h-10 rounded-lg bg-indigo-600 px-4 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{adminAuthLoading ? "Verificando…" : "Habilitar administración"}</button>
            </form>
          )}
          {adminAuthError && <p role="alert" className="mt-3 text-sm text-rose-700">{adminAuthError}</p>}
        </section>
      )}

      <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
        <CircleHelp className="mt-0.5 h-4 w-4 shrink-0" />
        <p id="store-management-availability">
          {canManage
            ? 'Administración autenticada en el servidor. Las acciones envían el token en la solicitud y solo se conserva en memoria mientras esta página está abierta.'
            : 'Modo de consulta: las tiendas y categorías siguen disponibles sin clave. Introduce la clave administrativa solo para habilitar altas, análisis y configuración.'}
        </p>
      </div>

      {showForm && <StoreRegistrationForm adminToken={adminToken} onCreated={handleCreated} onCancel={() => setShowForm(false)} />}

      {categoriesLoading && <p role="status" className="text-sm text-slate-500">Cargando categorías…</p>}
      {categoriesError && (
        <div role="alert" className="flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 sm:flex-row sm:items-center sm:justify-between">
          <span>No se pudieron cargar las categorías: {categoriesError}</span>
          <button type="button" onClick={() => { setCategoriesError(null); setCategoriesLoading(true); setRetry((value) => value + 1) }} className="rounded-lg border border-amber-300 px-3 py-1.5 font-semibold hover:bg-amber-100">Reintentar</button>
        </div>
      )}

      {storesError && (
        <div role="alert" className="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900 sm:flex-row sm:items-center sm:justify-between">
          <span className="flex items-start gap-2"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />No se pudieron cargar las tiendas: {storesError}</span>
          <button type="button" onClick={() => { setStoresError(null); setStoresLoading(true); setRetry((value) => value + 1) }} className="inline-flex shrink-0 items-center gap-2 self-start rounded-lg border border-rose-300 px-3 py-1.5 font-semibold hover:bg-rose-100"><RefreshCw className="h-3.5 w-3.5" />Reintentar</button>
        </div>
      )}

      {storesLoading ? (
        <div className="flex items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white py-16 text-slate-600"><LoaderCircle className="h-5 w-5 animate-spin text-indigo-600" />Cargando tiendas registradas…</div>
      ) : storesError && stores.length === 0 ? null : visibleStores.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
          <StoreIcon className="mx-auto h-10 w-10 text-slate-400" />
          <h2 className="mt-4 text-lg font-semibold text-slate-900">{canManage ? 'Todavía no hay tiendas registradas' : 'No hay tiendas operativas con precios recientes'}</h2>
          <p className="mx-auto mt-2 max-w-lg text-sm text-slate-600">{canManage ? 'Agrega el sitio oficial de un comercio. PriceScope comprobará primero si cuenta con un analizador compatible.' : 'Se muestran solo tiendas activas con conector específico, última extracción exitosa y precios persistidos en las últimas 48 horas.'}</p>
          <button type="button" disabled={!canManage} title={!canManage ? 'Introduce la clave de administración para habilitar esta acción.' : undefined} onClick={() => setShowForm(true)} className="mt-5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">Registrar la primera tienda</button>
        </div>
      ) : (
        <div className="space-y-4">{visibleStores.map((store) => <StoreCard key={store.id} store={store} categories={categories} canManage={canManage} adminToken={adminToken} onUpdated={updateStore} onReload={() => { void refreshStores() }} />)}</div>
      )}
    </section>
  )
}
