# PriceScope

**Monitor de Inflación Real Multimoneda — FinTech / B2B Analytics**

PriceScope es una plataforma de analítica económica orientada al seguimiento de precios de productos y cotizaciones cambiarias en distintos mercados y tiendas de comercio electrónico.

Su objetivo es facilitar el análisis de la evolución de los precios en moneda local y extranjera, almacenar observaciones históricas y ofrecer información útil para comparar productos, tiendas y categorías.

El proyecto se desarrolla como parte de **NoCountry — Simulación laboral S10-26, Equipo 14**.

---

## 1. Problema

La recopilación manual de precios y su conversión a distintas monedas puede generar retrasos, errores y dificultades para:

- Identificar variaciones reales del mercado.
- Comparar productos equivalentes entre tiendas.
- Diferenciar cambios de precio de fluctuaciones cambiarias.
- Detectar promociones y cambios de disponibilidad.
- Consultar y analizar la evolución histórica de los precios.

PriceScope busca centralizar estos datos y facilitar su consulta mediante una API y una interfaz web.

## 2. Objetivo

Desarrollar una plataforma de inteligencia de mercado que permita registrar, consultar y analizar precios de productos y tipos de cambio, con una arquitectura preparada para incorporar procesos automatizados de extracción, normalización y análisis económico.

## 3. Funcionalidades del proyecto

### Implementadas en el backend

- API REST desarrollada con FastAPI.
- Consulta de tiendas y categorías.
- Consulta de productos y catálogo paginado.
- Consulta y registro de relaciones entre productos y tiendas.
- Consulta y registro de observaciones de precios.
- Consulta de cotizaciones cambiarias.
- Persistencia de datos mediante PostgreSQL.
- Modelado y acceso a datos con SQLAlchemy.
- Gestión de cambios del esquema mediante Alembic.
- Validación de datos con Pydantic.
- Documentación interactiva de endpoints mediante OpenAPI y Swagger.
- Endpoints de salud y disponibilidad del servicio.

### En desarrollo o pendientes de integración

- Conexión completa de las pantallas del frontend con la API.
- Automatización de la recolección de precios de tiendas de comercio electrónico.
- Normalización y asociación avanzada de productos equivalentes.
- Seguimiento automatizado de promociones y disponibilidad.
- Cálculo de inflación acumulada y variaciones por períodos.
- Comparativas analíticas entre tiendas, productos y categorías.
- Sistema de alertas.
- Autenticación de usuarios mediante registro e inicio de sesión.
- Gestión de perfiles y permisos de acceso.

**Importante:** las pantallas o indicadores que todavía utilicen datos de demostración o mocks no deben interpretarse como resultados de una recolección real o como indicadores económicos calculados a partir de datos productivos.

## 4. Arquitectura y tecnologías

PriceScope utiliza una arquitectura separada en frontend, backend y base de datos.

| Componente | Tecnología |
|---|---|
| Frontend | React, TypeScript, Vite y Tailwind CSS |
| Backend | Python y FastAPI |
| ORM | SQLAlchemy |
| Validación de datos | Pydantic |
| Base de datos | PostgreSQL |
| Hosting de base de datos | Neon |
| Migraciones | Alembic |
| Pruebas backend | Pytest |
| Documentación API | OpenAPI / Swagger |
| Hosting frontend | Vercel |
| Hosting backend | Render |

### Flujo general de información

1. Los datos de productos, tiendas y cotizaciones se registran o incorporan al sistema.
2. El backend valida y procesa las solicitudes.
3. SQLAlchemy permite consultar y persistir la información en PostgreSQL.
4. FastAPI expone los datos mediante endpoints REST.
5. El frontend consume la API y presenta la información en sus distintas pantallas.

La automatización de extracción y el procesamiento analítico avanzado forman parte de la evolución prevista del proyecto.

## 5. Estructura del repositorio

```text
S10-26-equipo-14/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── alembic/
│   ├── alembic.ini
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── data/
│   │   ├── lib/
│   │   └── pages/
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── docs/
│   ├── arquitectura.md
│   ├── modelo-datos.md
│   ├── diccionario-datos.md
│   ├── decisiones-tecnicas.md
│   ├── plan-trabajo.md
│   └── ...
│
├── .gitignore
└── README.md
```

La estructura representa la organización general del proyecto. Algunos módulos y archivos pueden evolucionar conforme se integren nuevas funcionalidades.

## 6. Requisitos previos

Para ejecutar el proyecto localmente se necesita:

- Git.
- Python compatible con las dependencias del backend.
- Node.js y npm.
- Acceso a una instancia PostgreSQL.
- Variables de entorno configuradas para el backend y el frontend.

## 7. Configuración del entorno local

### 7.1. Clonar el repositorio

```bash
git clone https://github.com/No-Country-simulation/S10-26-equipo-14.git

cd S10-26-equipo-14
```

### 7.2. Preparar el backend

Desde la raíz del repositorio:

```bash
python -m venv env
```

Activar el entorno virtual en Git Bash:

```bash
source env/Scripts/activate
```

En Windows PowerShell:

```powershell
.\env\Scripts\Activate.ps1
```

Instalar las dependencias:

```bash
cd backend
pip install -e .
```

### 7.3. Configuración local del backend

Para el MVP local no es necesario crear ni editar `.env`. Usa la SQLite local
`backend/.local/pricescope.sqlite3` y define `DATABASE_URL` solo en la terminal
que inicia FastAPI. Desde `backend/`, en PowerShell:

```powershell
python -m app.commands.pricescope_local db init
$env:DATABASE_URL = "sqlite:///./.local/pricescope.sqlite3"
```

`db init` está limitado a la SQLite local predeterminada y valida el esquema
existente antes de aplicar migraciones locales. No lo apuntes a una base remota.

La configuración de producción se proporciona mediante el entorno del servicio
correspondiente; no copies esas credenciales a archivos del repositorio ni a
variables `VITE_`, porque estas últimas se exponen al navegador.

### 7.4. Ejecutar el backend

Desde la carpeta `backend/`:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

El backend local estará disponible en:

```text
http://127.0.0.1:8001
```

Documentación interactiva:

```text
http://127.0.0.1:8001/docs
```

Esquema OpenAPI:

```text
http://127.0.0.1:8001/openapi.json
```

### 7.5. Preparar el frontend

Abrir otra terminal y entrar en la carpeta del frontend:

```bash
cd frontend
npm install
```

En desarrollo, Vite envía las solicitudes `/api` al backend local
`http://127.0.0.1:8001`. No configures `VITE_API_URL` para este flujo local.

Ejecutar Vite:

```bash
npm run dev
```

El frontend estará disponible normalmente en:

```text
http://localhost:5173
```

`VITE_API_URL` se reserva para configurar compilaciones de producción. No
incluyas credenciales en esa variable.

Para cargar datos de demostración sintéticos en la SQLite local, ejecuta desde
`backend/`:

```powershell
python -m app.commands.seed_demo
python -m app.commands.seed_demo --apply
```

El primer comando solo valida el destino; el segundo es idempotente, usa URLs
`.invalid` y no ejecuta extracciones. No lo ejecutes contra bases remotas.

## 8. API y documentación de endpoints

El backend utiliza el prefijo `/api/v1` para sus rutas de negocio.

Entre los endpoints disponibles se encuentran:

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/v1/stores` | Consultar tiendas |
| GET | `/api/v1/categories` | Consultar categorías |
| GET | `/api/v1/products` | Consultar productos |
| GET | `/api/v1/products/paginated` | Consultar productos con paginación |
| GET | `/api/v1/products/{product_id}` | Consultar un producto |
| GET | `/api/v1/store-products` | Consultar productos asociados a tiendas |
| POST | `/api/v1/store-products` | Registrar una asociación producto-tienda |
| GET | `/api/v1/price-observations` | Consultar observaciones de precios |
| POST | `/api/v1/price-observations` | Registrar una observación de precio |
| GET | `/api/v1/exchange-rates` | Consultar cotizaciones cambiarias |

Los parámetros, filtros y esquemas de solicitud y respuesta deben consultarse en la documentación OpenAPI del backend, que representa el contrato técnico vigente.

### Parámetros de consulta

El catálogo paginado permite trabajar con parámetros como:

- `limit`: cantidad máxima de resultados.
- `offset`: desplazamiento de resultados.
- `category_id`: filtro por categoría.

Para consultar los endpoints y probar las solicitudes:

https://pricescope-api.onrender.com/docs

## 9. Despliegue

### Frontend

El frontend está publicado mediante Vercel:

https://pricescope-14.vercel.app/

### Backend

La API está desplegada en Render:

https://pricescope-api.onrender.com

Documentación Swagger:

https://pricescope-api.onrender.com/docs

Comprobación de salud:

https://pricescope-api.onrender.com/health

Comprobación de disponibilidad:

https://pricescope-api.onrender.com/ready

El servicio puede tardar en responder a la primera solicitud después de un período de inactividad, debido a las características del plan de hosting.

### Variables de entorno de producción

El frontend necesita conocer la URL pública del backend mediante:

```env
VITE_API_URL=https://pricescope-api.onrender.com
```

El backend debe tener configurado `DATABASE_URL` y los orígenes autorizados en `CORS_ORIGINS`.

Las variables de producción se administran desde los paneles de Vercel y Render, no desde archivos versionados en Git.

## 10. Pruebas y validación

El backend utiliza Pytest para las pruebas automatizadas.

Desde la carpeta `backend/`, con el entorno virtual activo:

```bash
pytest
```

Para obtener un resumen detallado:

```bash
pytest -v
```

Las pruebas de integración que necesitan una base de datos deben ejecutarse únicamente en un entorno de pruebas controlado y con la configuración adecuada.

Para validar la integración completa se debe comprobar:

1. Que el backend inicia correctamente.
2. Que la conexión con PostgreSQL funciona.
3. Que los endpoints responden según sus contratos.
4. Que el frontend puede consumir la API.
5. Que los datos mostrados corresponden a las respuestas recibidas.
6. Que la compilación y las verificaciones del frontend finalizan correctamente.

Desde `frontend/`:

```bash
npm run lint
npm run build
```

## 11. Estado actual y próximos objetivos

El proyecto cuenta con una base técnica funcional: frontend React, API FastAPI, persistencia PostgreSQL, documentación OpenAPI y despliegues separados.

Los siguientes objetivos son:

- Completar la integración frontend-backend.
- Sustituir progresivamente los datos mock por información de la API.
- Validar el catálogo, los precios y las cotizaciones.
- Incorporar indicadores calculados a partir de datos persistidos.
- Implementar autenticación y gestión de usuarios.
- Desarrollar el proceso automatizado de ingesta.
- Incorporar comparativas y alertas.
- Mejorar la cobertura de pruebas y la documentación técnica.

## 12. Equipo

**NoCountry — Simulación laboral S10-26, Equipo 14.**

Proyecto colaborativo de desarrollo de una solución FinTech orientada a la inteligencia de mercado y al análisis multimoneda.

---

**PriceScope — De los precios observados a la inteligencia de mercado.**
