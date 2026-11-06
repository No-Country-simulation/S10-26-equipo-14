# Contratos frontend/backend — PriceScope

> Estado: documentación de los contratos existentes en la rama base `develop`.
> Commit de `develop` revisado: `367d92da80080a850a8aa287e652745339b0d964`.
> Alcance: PS-026 / Issue #38. Este documento no implementa endpoints ni modifica modelos.

## 1. Resumen

FastAPI publica consultas de tiendas, categorías, productos canónicos, publicaciones, observaciones históricas y cotizaciones. También publica operaciones POST para crear publicaciones y observaciones. Las páginas `HomePage` y `CatalogoPage` aún leen JSON de `frontend/src/data/mock`; no se encontró integración HTTP en esas páginas. `DemoPage` presenta valores y series hardcodeados.

El mock `products.json` representa publicaciones por tienda, mientras el backend separa el producto canónico (`Product`) de la publicación comercial (`StoreProduct`). Esa distinción debe mantenerse al integrar el catálogo.

## 2. Fuentes revisadas

| Área | Archivos principales |
|---|---|
| Aplicación y rutas | `backend/app/main.py`, `backend/app/api/v1/router.py` |
| Modelos SQLAlchemy | `backend/app/models/store.py`, `category.py`, `product.py`, `store_product.py`, `price.py`, `exchange_rate.py` |
| Esquemas Pydantic | `backend/app/schemas/catalog.py`, `backend/app/schemas/market.py` |
| Tipos TypeScript | `frontend/src/types/store.ts`, `category.ts`, `product.ts`, `storeProduct.ts`, `price.ts`, `exchangeRate.ts` |
| Pantallas y filtros | `frontend/src/pages/HomePage.tsx`, `CatalogoPage.tsx`, `DemoPage.tsx`, `frontend/src/components/filters/FilterBar.tsx` |
| Datos simulados | `frontend/src/data/mock/stores.json`, `categories.json`, `products.json`, `prices.json`, `exchangeRates.json` |

Los esquemas de salida mencionados son los `response_model` de las rutas. La inspección generó el esquema con `app.openapi()` desde `backend/app/main.py`, sin conectar a una base de datos. El resultado es OpenAPI 3.1.0. Se recorrió el documento generado buscando las claves `example` y `examples`: no se encontró ninguna en parámetros, respuestas ni esquemas. OpenAPI publica esquemas y respuestas de validación, pero no ejemplos concretos de respuesta. Por ello este documento no presenta objetos JSON inventados ni ejemplos ilustrativos como respuestas reales.

## 3. Correspondencia de las seis entidades

En las respuestas, los campos listados son obligatorios como propiedades JSON. Cuando se indica nullable, la propiedad sigue presente y su valor puede ser `null`; eso no equivale a que pueda omitirse.

| Entidad | Contrato de salida backend | Campos anulables | TypeScript y mock |
|---|---|---|---|
| **Store** | `StoreOut`: `id:number`, `name:string`, `base_url:string`, `country:string|null`, `is_active:boolean`, `created_at:date-time`. | `country`. | `Store` declara esos campos y usa `string` para `created_at`. `stores.json` tiene la misma forma, con contenido simulado. |
| **Category** | `CategoryOut`: `id:number`, `name:string`, `slug:string`. | Ninguno. | `Category` coincide. `categories.json` añade `description`, que no existe en el modelo ni en la respuesta API. |
| **Product** | `ProductOut`: `id:number`, `name:string`, `brand:string|null`, `model:string|null`, `description:string|null`, `barcode:string|null`, `category_id:number|null`. | `brand`, `model`, `description`, `barcode`, `category_id`. | `Product` coincide con el esquema. `products.json` no tiene esta estructura: contiene campos de una publicación. |
| **StoreProduct** | `StoreProductOut`: `id:number`, `store_id:number`, `product_id:number|null`, `category_id:number|null`, `external_id:string|null`, `product_url:string`, `product_name:string`, `currency:string`. | `product_id`, `category_id`, `external_id`. | `StoreProduct` coincide. No hay mock separado de esta entidad; la página de catálogo consume `products.json`. |
| **PriceObservation** | `PriceObservationOut`: `id:number`, `store_product_id:number`, `amount:Decimal`, `promotional_price:Decimal|null`, `currency:string`, `source_url:string|null`, `is_available:boolean|null`, `observed_at:date-time`. | `promotional_price`, `source_url`, `is_available`. | `PriceObservation` representa los decimales como `DecimalString` (`string`) y el timestamp como `string`. `prices.json` usa `product_id`, `store_id` y montos numéricos, no el contrato API. |
| **ExchangeRate** | `ExchangeRateOut`: `id:number`, `source:string`, `rate_type:string`, `rate_side:string`, `base_currency:string`, `quote_currency:string`, `rate:Decimal`, `observed_at:date-time`. | Ninguno. | `ExchangeRate` usa `DecimalString` y restringe `rate_side` a una unión TypeScript. OpenAPI/Pydantic lo publica como `string`; el modelo SQLAlchemy aplica una restricción de base de datos a `reference`, `buy` o `sell`. `exchangeRates.json` usa otra estructura. |

### 3.1 Campos de entrada opcionales y anulables

Los campos opcionales que siguen corresponden a esquemas de creación; no deben confundirse con las propiedades requeridas de las respuestas:

| Request | Requeridos | Opcionales, defaults y nulabilidad |
|---|---|---|
| `StoreProductCreate` | `store_id`, `product_url`, `product_name`. | `product_id`, `category_id` y `external_id` aceptan `null` y por defecto son `null`; `currency` es opcional y por defecto `ARS`. `external_id` admite hasta 180 caracteres; URL y nombre tienen validaciones de formato/longitud en Pydantic. |
| `PriceObservationCreate` | `store_product_id`, `amount`, `observed_at`. | `promotional_price`, `source_url` e `is_available` aceptan `null` y por defecto son `null`; `currency` es opcional y por defecto `ARS`. `amount` y `promotional_price`, si se informan, deben ser mayores que cero; admiten hasta 14 dígitos y 2 decimales en el esquema. |

No hay requests de creación publicados para Store, Category, Product o ExchangeRate en el router inspeccionado.

### 3.2 Relaciones

- `Product` es el producto canónico que puede vincular publicaciones equivalentes entre comercios.
- `StoreProduct` representa la publicación de un producto en una tienda. `product_id` es anulable; la publicación también tiene `store_id` obligatorio y `category_id` opcional.
- `Product.category_id` es la categoría canónica. `StoreProduct.category_id` es la categoría de la publicación; ambas pueden diferir.
- `PriceObservation` referencia una publicación mediante `store_product_id`. No contiene `product_id` ni `store_id` propios.
- Las respuestas actuales son planas: entregan IDs, no objetos Store/Product/Category anidados.

La fila de `products.json` puede entenderse funcionalmente como una publicación, pero no se debe equiparar automáticamente: `name` se parece a `product_name`, `url` a `product_url`, y `sku` no está definido como equivalente de `external_id`.

## 4. Serialización

- En los esquemas OpenAPI generados, los campos `Decimal` de salida (`PriceObservationOut.amount`, `promotional_price` y `ExchangeRateOut.rate`) aparecen como `type: string`. Pydantic serializa esos valores decimales como cadenas JSON; las interfaces usan `DecimalString = string` para no perder precisión con `number`.
- Para los campos Decimal de entrada, OpenAPI acepta número o cadena según el esquema generado. La integración debe preservar precisión y no asumir que esa flexibilidad de entrada aplica a las respuestas.
- Los campos `datetime` aparecen en OpenAPI como cadenas `format: date-time`; su representación es ISO 8601. SQLAlchemy usa `DateTime(timezone=True)` para fechas de observaciones y cotizaciones. Las rutas validan que los parámetros temporales y `observed_at` enviados incluyan zona horaria. No hay una garantía documentada de normalización de toda respuesta a `Z`/UTC.
- Una propiedad nullable de salida sigue siendo obligatoria, y su valor puede ser `null`.

## 5. Endpoints publicados

Las rutas de negocio tienen el prefijo `/api/v1`; `/health` está fuera de ese prefijo.

| Método y ruta | Request y comportamiento observado | Respuesta observada |
|---|---|---|
| `GET /health` | Sin parámetros. | Objeto con estado `ok`; no comprueba disponibilidad de base de datos. |
| `GET /api/v1/stores` | Sin parámetros. Filtra `is_active = true` y ordena por nombre. | `list[StoreOut]`. |
| `GET /api/v1/categories` | Sin parámetros; orden por nombre. | `list[CategoryOut]`. |
| `GET /api/v1/products` | `category_id` opcional; no declara una validación positiva explícita. Orden por nombre. | `list[ProductOut]`. |
| `GET /api/v1/products/paginated` | `limit` default 20, 1–100; `offset` default 0, mínimo 0; `category_id` opcional y mayor que 0. Orden por nombre e ID; `total` cuenta el mismo filtro sin paginación. | `ProductPageOut`: `items`, `total`, `limit`, `offset`. |
| `GET /api/v1/products/{product_id}` | `product_id` mayor que 0. | `ProductOut`; 404 si no existe. |
| `GET /api/v1/store-products` | `store_id` opcional; sin validación positiva explícita. Orden por ID. | `list[StoreProductOut]`. |
| `POST /api/v1/store-products` | Body `StoreProductCreate`. | `StoreProductOut`, 201 al crear y 409 ante conflicto de integridad. |
| `GET /api/v1/price-observations` | Requiere `store_product_id > 0`; `start` y `end` opcionales, con zona horaria; `limit` default 100, 1–1000. Rechaza `start > end`; orden descendente por `observed_at`. | `list[PriceObservationOut]`. |
| `POST /api/v1/price-observations` | Body `PriceObservationCreate`; `observed_at` requiere zona horaria. | `PriceObservationOut`, 201 al crear y 409 ante conflicto de integridad. |
| `GET /api/v1/exchange-rates` | Requiere `rate_type` de 1–30 caracteres; `on_date` opcional y con zona horaria. Si se envía, incluye registros con `observed_at <= on_date`; orden descendente y máximo 100. | `list[ExchangeRateOut]`. |

El router inspeccionado no publica búsqueda textual de productos/publicaciones, endpoint de catálogo compuesto, CRUD de ejecuciones de extracción, alertas, autenticación/registro/login, ni creación de cotizaciones.

## 6. Mocks, pantallas y límites actuales

### Mocks

- `stores.json` comparte la forma general de `Store`; sus contenidos son de demostración.
- `categories.json` incluye `description`, ausente del modelo SQLAlchemy y de `CategoryOut`.
- `products.json` contiene `id`, `store_id`, `category_id`, `name`, `sku`, `url`, `is_active`. Es una representación plana de publicaciones y no de `ProductOut` ni de `StoreProductOut`.
- `prices.json` asocia importes por `product_id` y `store_id`; la API asocia observaciones a `store_product_id`. El JSON contiene importes numéricos, mientras la respuesta API serializa Decimal como string.
- `exchangeRates.json` usa `pair`, `recorded_at` y valores numéricos; la API separa `base_currency` y `quote_currency`, incluye `rate_type`, `rate_side` y `observed_at`, y serializa `rate` como string. Los valores `oficial` y `blue` pertenecen a los mocks; no prueban una integración con esas fuentes.

### HomePage

Calcula métricas leyendo los mocks. `GET /stores` y `GET /categories` podrían proporcionar listas para sus conteos. “Productos monitoreados” requiere decidir si cuenta productos canónicos o publicaciones. La pantalla busca `source === "oficial"` y usa `recorded_at`; debe adaptarse al esquema de cotizaciones antes de usar la API. No realiza requests HTTP.

### CatalogoPage y FilterBar

La pantalla filtra `products.json` en el cliente por tienda (`store_id`), categoría (`category_id`) y texto sobre `name`, y muestra tienda, categoría y `url`. El callback de FilterBar incluye fechas, pero `CatalogoPage` las descarta; las fechas no filtran resultados. Los chips activos tampoco muestran fechas.

La API actual puede proporcionar tiendas, categorías y publicaciones. `GET /store-products` solo filtra por `store_id`; no filtra por categoría ni texto. No devuelve nombres de tienda/categoría ni el último precio como objetos asociados. `GET /price-observations` requiere `store_product_id` y resuelve historial publicación por publicación. Para conservar el comportamiento de la tarjeta de catálogo se necesita una estrategia explícita de composición, paginación y precio más reciente.

### DemoPage

Presenta métricas y series temporales hardcodeadas en la página con Recharts. No consulta mocks ni endpoints y los valores no deben interpretarse como datos reales.

## 7. Propuesta de respuesta agregada para el catálogo — no implementada

Para una tarjeta que necesita producto canónico, publicación, tienda, categorías y último precio, se propone evaluar un recurso paginado con `items`, `total`, `limit` y `offset`. Cada elemento podría contener `product`, `listing` (`StoreProduct`), `store`, categoría canónica, categoría de publicación y `latest_price` nullable. La selección de la observación más reciente debería resolverse por publicación en el servidor.

Esto es una propuesta, no un endpoint o esquema existente. Alternativamente, una primera integración puede combinar rutas actuales, con el costo de implementar en cliente la asociación y evitar consultas de historial por tarjeta.

## 8. Incompatibilidades priorizadas

| Prioridad | Diferencia comprobada | Impacto |
|---|---|---|
| Alta | `products.json` modela publicaciones; `GET /products` devuelve productos canónicos. | La respuesta no puede sustituir al mock de catálogo sin cambiar el modelo de UI o usar `StoreProduct`. |
| Alta | Los mocks de precio relacionan por producto y tienda; la API requiere `store_product_id`. | No se puede asociar históricamente sin una identidad de publicación. |
| Alta | Catálogo API no agrega tienda, categoría y último precio; las rutas de observaciones requieren una publicación por consulta. | La pantalla no puede conectarse directamente manteniendo las mismas tarjetas y evitando N+1. |
| Media | Cotizaciones mock (`pair`, `recorded_at`, número) difieren de API (par de monedas separado, `observed_at`, Decimal string). | Requiere adapter y ajustar el selector de oficial/paralelo. |
| Media | `rate_side` es `string` en OpenAPI/Pydantic, aunque la base restringe valores y TypeScript usa unión literal. | El contrato estático y el esquema publicado no validan el mismo conjunto de valores. |
| Media | `FilterBar` captura fechas, pero `CatalogoPage` no las aplica ni conserva. | El filtro visual no cumple su intención actual. |
| Baja | `categories.json` incluye `description`. | No debe asumirse que la API devuelve ese campo. |

## 9. Decisiones pendientes antes de conectar pantallas

1. Definir si el filtro categoría se aplica a `Product.category_id`, `StoreProduct.category_id` o ambos; actualmente `/store-products` no tiene filtro de categoría.
2. Definir el alcance de búsqueda: nombre de producto canónico, nombre de publicación, marca, modelo u otros campos. No existe filtro textual en la API.
3. Definir el significado del rango de fechas: seleccionar publicaciones observadas en el período y/o elegir el último precio dentro del período. El endpoint de observaciones ofrece `start`/`end`, pero solo para un `store_product_id`.
4. Definir si “productos monitoreados” cuenta entidades Product únicas o publicaciones StoreProduct.
5. Elegir entre endpoint agregado de catálogo y composición cliente de las rutas actuales.
6. Definir adaptación visual de `rate_type` y `rate_side`. `rate_side` no está expresado como enum en OpenAPI.
7. Acordar estados de carga, error, lista vacía, URL de API por entorno y CORS antes de despliegue.

## 10. Issue #29 y autenticación

El alcance del Issue #29 mencionado en el proyecto incluye registro/login/token. No se encontraron rutas de autenticación ni esquemas de usuario/token en la aplicación inspeccionada. Debe confirmarse o separarse ese alcance y definirse autenticación y autorización antes de exponer operaciones de escritura. No es una capacidad disponible para integrar actualmente.

## 11. Criterios de aceptación documental y pendientes

Este documento cubre las seis entidades y sus relaciones; diferencia campos requeridos, opcionales y anulables; describe serialización, endpoints, mocks, filtros e incompatibilidades; identifica límites de pantallas y decisiones pendientes; y separa expresamente los contratos vigentes de la propuesta agregada.

La inspección comprobó los esquemas generados por OpenAPI y que no publican ejemplos concretos. No se probó una instancia desplegada ni se validaron respuestas con datos persistidos. La integración frontend/API, el endpoint agregado si se elige, la implementación de filtros faltantes, autenticación/autorización y extractores reales siguen fuera del alcance documental y pendientes.

## 12. Límites de esta revisión

- Se revisaron los archivos de código enumerados arriba en la versión de `develop` indicada en el encabezado y se generó su OpenAPI mediante `app.openapi()`.
- No se consultó ni modificó Neon y no se ejecutaron migraciones.
- No se modificaron backend funcional, frontend funcional, mocks, migraciones o servicios.
- Los datos de los JSON son contenido simulado y no evidencia de integraciones externas.
