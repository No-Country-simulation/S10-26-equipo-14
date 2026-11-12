const stack = [
  { name: 'Frontend', value: 'React + TypeScript + Vite + Tailwind CSS' },
  { name: 'Backend', value: 'Python + FastAPI + SQLAlchemy + Pydantic' },
  { name: 'Base de datos', value: 'PostgreSQL (Neon) + Alembic' },
  { name: 'Infraestructura', value: 'Frontend en Vercel + API en Render' },
  {
    name: 'Ingesta de datos',
    value: 'Adaptadores y extracción manual local en desarrollo; sin ejecución periódica',
  },
]

export default function AboutPage() {
  return (
    <section className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">
        Acerca de PriceScope
      </h1>
      <p className="mt-4 leading-relaxed text-slate-600">
        PriceScope es una aplicación en desarrollo para consultar productos,
        tiendas, observaciones históricas de precios y cotizaciones cambiarias
        mediante su API. El MVP permite explorar el catálogo y visualizar series
        construidas con los registros disponibles.
      </p>
      <p className="mt-4 leading-relaxed text-slate-600">
        Los datos sintéticos del entorno local de demostración no representan
        precios actuales. El cálculo de inflación, las comparativas, las alertas
        y la extracción periódica aún no están implementados. Los adaptadores de
        ingesta y la extracción manual local siguen en desarrollo; no hay
        ejecuciones programadas.
      </p>

      <h2 className="mt-10 text-xl font-semibold text-slate-900">
        Stack tecnológico
      </h2>
      <dl className="mt-4 divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
        {stack.map((item) => (
          <div key={item.name} className="flex flex-col gap-1 px-5 py-4 sm:flex-row sm:items-center sm:gap-6">
            <dt className="w-48 shrink-0 text-sm font-medium text-slate-500">
              {item.name}
            </dt>
            <dd className="text-sm text-slate-900">{item.value}</dd>
          </div>
        ))}
      </dl>

      <p className="mt-10 text-sm text-slate-500">
        No Country — Simulación laboral S10-26, Equipo 14.
      </p>
    </section>
  )
}
