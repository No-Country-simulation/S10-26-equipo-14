# Frontend de PriceScope

Interfaz web de PriceScope construida con **React + TypeScript + Vite + Tailwind CSS**.

## Requisitos

- Node.js 20.19+ (recomendado 22.x)
- npm

## Puesta en marcha

```bash
cd frontend
npm install
npm run dev
```

La aplicación queda disponible en `http://localhost:5173`.

## Scripts disponibles

| Comando           | Descripción                                        |
| ----------------- | -------------------------------------------------- |
| `npm run dev`     | Servidor de desarrollo con HMR                     |
| `npm run build`   | Type-check (`tsc -b`) + build de producción        |
| `npm run preview` | Vista previa del build de producción               |
| `npm run lint`    | Linting con oxlint                                 |

## Estructura

```
src/
├── main.tsx                  # Entry point
├── App.tsx                   # Shell: provee el RouterProvider
├── index.css                 # Estilos base (@import "tailwindcss")
├── app/
│   └── router.tsx            # Definición de rutas (react-router-dom)
├── components/
│   └── layout/
│       └── Layout.tsx        # Header, navegación, footer y <Outlet />
└── pages/
    ├── HomePage.tsx          # Landing con funcionalidades previstas
    └── AboutPage.tsx         # Descripción del proyecto y stack
```

## Convenciones

- TypeScript estricto y JSX en archivos `.tsx`.
- Estilos utilitarios con Tailwind CSS v4 (plugin `@tailwindcss/vite`, sin `tailwind.config.js`).
- Una página por ruta en `src/pages/`; componentes reutilizables en `src/components/`.
