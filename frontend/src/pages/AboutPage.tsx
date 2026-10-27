const stack = [
  { name: 'Frontend', value: 'React + TypeScript + Vite + Tailwind CSS' },
  { name: 'Extracción de datos', value: 'Python (Playwright o BeautifulSoup)' },
  { name: 'Backend', value: 'Por definir con el equipo' },
  { name: 'Base de datos', value: 'PostgreSQL' },
]

export default function AboutPage() {
  return (
    <section className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">
        Acerca de PriceScope
      </h1>
      <p className="mt-4 leading-relaxed text-slate-600">
        PriceScope es una plataforma de analítica económica que automatiza la
        recolección, el seguimiento y el análisis histórico de precios de
        productos en diferentes tiendas de comercio electrónico, relacionándolos
        con la evolución de las cotizaciones cambiarias.
      </p>
      <p className="mt-4 leading-relaxed text-slate-600">
        La recopilación manual de precios y su conversión a distintas monedas
        genera retrasos, errores y dificultades para identificar variaciones
        reales del mercado. PriceScope busca resolverlo con un flujo completo de
        datos confiables y visualizaciones claras.
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
        NoCountry — Simulación laboral S10-26, Equipo 14.
      </p>
    </section>
  )
}
