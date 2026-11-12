# PriceScope — Frontend

Aplicación web de **PriceScope**, una plataforma FinTech de inteligencia de mercado que busca facilitar el seguimiento y análisis de precios de productos y tipos de cambio en distintos mercados.

Este directorio contiene la interfaz web del proyecto.

## 1. Tecnologías

- **React 19:** construcción de interfaces.
- **TypeScript:** tipado estático.
- **Vite 8:** servidor de desarrollo y herramienta de construcción.
- **Tailwind CSS 4:** estilos y diseño adaptable.
- **React Router 7:** navegación entre páginas.
- **Recharts:** visualización de datos y gráficos.
- **Oxlint:** análisis estático del código.

## 2. Requisitos

- Node.js 20.19+ o 22.12+.
- npm.
- Acceso al backend de PriceScope para consultar los datos de la API.

Se recomienda utilizar una versión LTS compatible de Node.js.

## 3. Instalación

Desde la raíz del repositorio:

```bash
cd frontend
npm install
```

## 4. Configuración de variables de entorno

En desarrollo local no hace falta crear `.env.local`: las solicitudes usan la
ruta relativa `/api` y Vite las reenvía a `http://127.0.0.1:8001`.

`VITE_API_URL` se utiliza en compilaciones de producción para indicar la URL
raíz del backend. Ejemplo de configuración de producción:

```env
VITE_API_URL=https://pricescope-api.onrender.com
```

**Importante:**
- No configures `VITE_API_URL` para el desarrollo local; Vite usa su proxy local.
- En producción, `VITE_API_URL` indica la URL raíz del backend.
- No agregar `/api` al final.
- Las variables con prefijo `VITE_` son visibles desde el navegador. No colocar contraseñas, tokens privados ni credenciales.
- Reiniciar Vite después de cambiar su configuración de proxy.

## 5. Ejecución

Iniciar el servidor de desarrollo:

```bash
npm run dev
```

Vite mostrará la dirección local, normalmente:

```text
http://localhost:5173
```

## 6. Comandos disponibles

| Comando | Descripción |
|---|---|
| `npm run dev` | Inicia el entorno de desarrollo. |
| `npm run lint` | Analiza el código mediante Oxlint. |
| `npm run build` | Ejecuta la comprobación TypeScript y genera la versión de producción. |
| `npm run preview` | Permite visualizar localmente la compilación de producción. |

Para generar la compilación:

```bash
npm run build
```

Los archivos resultantes se generan en `dist/`.

## 7. Estructura del proyecto

```text
frontend/
├── public/                 # Recursos públicos
├── src/
│   ├── app/                # Configuración de la aplicación y rutas
│   ├── components/         # Componentes reutilizables
│   │   ├── filters/        # Filtros
│   │   └── ui/             # Componentes de interfaz
│   ├── data/               # Datos de demostración
│   │   └── mock/           # Datos simulados
│   ├── lib/                # Cliente y utilidades de API
│   ├── pages/              # Páginas de la aplicación
│   ├── types/              # Tipos e interfaces TypeScript
│   └── ...
├── .env.example            # Ejemplo de configuración
├── index.html
├── package.json
├── vite.config.ts
└── README.md
```

## 8. Comunicación con el backend

El frontend consume la API REST desarrollada con FastAPI.

URL del backend desplegado:

https://pricescope-api.onrender.com

Documentación interactiva:

https://pricescope-api.onrender.com/docs

OpenAPI:

https://pricescope-api.onrender.com/openapi.json

El cliente de comunicación se encuentra en:

```text
src/lib/api.ts
```

Entre los recursos contemplados para la integración están:

- Productos.
- Categorías.
- Establecimientos comerciales.
- Observaciones de precios.
- Tipos de cambio.

Los endpoints disponibles y sus contratos deben consultarse en la documentación OpenAPI del backend.

**Nota:** el catálogo utiliza paginación del backend y la búsqueda por nombre, mientras no exista búsqueda server-side, debe entenderse como una búsqueda local sobre los productos cargados en la página actual.

## 9. Páginas principales

La aplicación contiene las siguientes áreas:

- **Inicio:** presentación y acceso a las funcionalidades.
- **Catálogo:** consulta y exploración de productos.
- **Divisas:** información relacionada con tipos de cambio.
- **Demo:** presentación de funcionalidades e indicadores ilustrativos.
- **Acerca de:** información general del proyecto.
- **Comparativas y alertas:** funcionalidades previstas para próximas etapas.

Los datos de demostración no deben confundirse con observaciones reales obtenidas de comercios o fuentes financieras.

## 10. Validación antes de integrar cambios

Ejecutar:

```bash
npm run lint
npm run build
```

Revisar también los cambios de Git:

```bash
git status
git diff --check
```

Antes de crear un Pull Request, comprobar que las modificaciones no introduzcan errores de TypeScript, problemas de integración con la API ni datos simulados presentados como reales.

## 11. Despliegue

El frontend está publicado en Vercel:

https://pricescope-14.vercel.app/

La variable de entorno `VITE_API_URL` debe configurarse en el proyecto de Vercel con la URL del backend correspondiente.

El backend debe permitir el origen del frontend mediante su configuración CORS.

---

**PriceScope — Inteligencia de mercado y monitoreo de precios.**

Proyecto desarrollado por No Country — Simulación S10-26, Equipo 14.
