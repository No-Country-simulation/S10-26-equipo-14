const features = [
  {
    title: 'Recolección automatizada',
    description:
      'Extracción periódica de precios de tiendas de comercio electrónico mediante scripts programados.',
  },
  {
    title: 'Normalización de productos',
    description:
      'Asociación de productos equivalentes entre tiendas, con detección de presentaciones y variantes.',
  },
  {
    title: 'Seguimiento de promociones',
    description:
      'Detección y seguimiento de promociones temporales, cambios de precio y disponibilidad.',
  },
  {
    title: 'Cotizaciones cambiarias',
    description:
      'Integración de cotizaciones de divisas con marca de tiempo para conversiones confiables.',
  },
  {
    title: 'Histórico de precios',
    description:
      'Almacenamiento histórico de precios y tipos de cambio para análisis de tendencias.',
  },
  {
    title: 'Indicadores de inflación',
    description:
      'Cálculo de inflación acumulada y variaciones porcentuales en moneda local y extranjera.',
  },
]

export default function HomePage() {
  return (
    <section>
      <div className="mx-auto max-w-3xl text-center">
        <p className="mb-4 inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
          Fase inicial — MVP en desarrollo
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          PriceScope
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Monitoreá precios de productos en diferentes tiendas, comparalos entre
          monedas y analizá la inflación real con indicadores y visualizaciones
          interactivas.
        </p>
      </div>

      <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((feature) => (
          <div
            key={feature.title}
            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
          >
            <h2 className="text-base font-semibold text-slate-900">
              {feature.title}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              {feature.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
