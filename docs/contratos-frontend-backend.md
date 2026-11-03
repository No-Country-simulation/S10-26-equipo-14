# Contratos frontend/backend — PriceScope

> Estado: documentación de los contratos existentes en `develop`.  
> Base revisada: `develop` en el commit `367d92da80080a850a8aa287e652745339b0d964`.  
> Alcance: análisis documental para PS-026 / Issue #38. Este documento no implementa endpoints ni modifica modelos.

## 1. Resumen

El backend FastAPI publica rutas para tiendas, categorías, productos canónicos, publicaciones por tienda, observaciones de precios y cotizaciones. El frontend ya declara interfaces TypeScript para esas entidades, pero HomePage y CatalogoPage todavía consumen archivos JSON simulados. No se encontró un cliente HTTP en las páginas revisadas.

La integración no consiste en convertir directamente cada mock en un tipo de API: el mock `products.json` representa publicaciones por tienda, mientras que el backend separa el producto canónico (`Product`) de la publicación (`StoreProduct`).

## 2. Fuentes de código revisadas

| Área | Archivo |
|---|---|
| Rutas HTTP | [backend/app/api/v1/router.py](../backend/app/api/v1/router.py) |
| Esquemas de catálogo | [backend/app/schemas/catalog.py](../backend/app/schemas/catalog.py) |
| Esquemas de mercado | [backend/app/schemas/market.py](../backend/app/schemas/market.py) |
| Contrato conceptual de modelos | [docs/model-contracts.md](./model-contracts.md) |
| Tipos frontend | [frontend/src/types/store.ts](../frontend/src/types/store.ts), [category.ts](../frontend/src/types/category.ts), [product.ts](../frontend/src/types/product.ts), [storeProduct.ts](../frontend/src/types/storeProduct.ts), [price.ts](../frontend/src/types/price.ts), [exchangeRate.ts](../frontend/src/types/exchangeRate.ts) |
| Páginas frontend | [HomePage.tsx](../frontend/src/pages/HomePage.tsx), [CatalogoPage.tsx](../frontend/src/pages/CatalogoPage.tsx) |
| Mocks | [stores.json](../frontend/src/data/mock/stores.json), [categories.json](../frontend/src/data/mock/categories.json), [products.json](../frontend/src/data/mock/products.json), [prices.json](../frontend/src/data/mock/prices.json), [exchangeRates.json](../frontend/src/data/mock/exchangeRates.json) |

Los esquemas Pydantic indicados son los modelos usados como `response_model` por las rutas. Los ejemplos de la sección 4 son ejemplos representativos construidos a partir de esos esquemas; no son registros leídos de Neon ni respuestas capturadas de una API desplegada.

## 3. Correspondencia de entidades

| Entidad | Respuesta backend (Pydantic) | Tipo TypeScript | Mock y compatibilidad |
|---|---|---|---|
| Store | `StoreOut`: `id:number`, `name:string`, `base_url:string`, `country:string|null`, `is_active:boolean`, `created_at:datetime`. | `Store` coincide; fecha como `string` ISO. | `stores.json` tiene los mismos campos. Sus valores son demostrativos. |
| Category | `CategoryOut`: `id:number`, `name:string`, `slug:string`. | `Category` coincide. | `categories.json` agrega `description`, que no está en la respuesta. El tipo TS no declara ese campo. |
| Product | `ProductOut`: `id`, `name`, `brand:string|null`, `model:string|null`, `description:string|null`, `barcode:string|null`, `category_id:number|null`. | `Product` coincide con el esquema. | `products.json` no es un mock de Product: contiene `store_id`, `sku`, `url`, `is_active` y nombre de publicación. |
| StoreProduct | `StoreProductOut`: `id`, `store_id`, `product_id:number|null`, `category_id:number|null`, `external_id:string|null`, `product_url:string`, `product_name:string`, `currency:string`. | `StoreProduct` coincide en sus campos. | No hay un mock separado con este contrato. La página Catálogo consume el mock plano de publicaciones. |
| PriceObservation | `PriceObservationOut`: `id`, `store_product_id`, `amount:Decimal`, `promotional_price:Decimal|null`, `currency`, `source_url:string|null`, `is_available:boolean|null`, `observed_at:datetime`. | `PriceObservation` usa `DecimalString` (`string`) y fecha `string`; coincide con la serialización esperada. | `prices.json` usa `product_id`, `store_id` y montos JSON numéricos. No es compatible directamente. |
| ExchangeRate | `ExchangeRateOut`: `id`, `source`, `rate_type`, `rate_side`, `base_currency`, `quote_currency`, `rate:Decimal`, `observed_at:datetime`. | `ExchangeRate` usa `DecimalString`; `rate_side` es unión TS `reference | buy | sell`. | `exchangeRates.json` usa `pair`, `recorded_at`, montos numéricos y clasifica `source` como `oficial`/ `blue`. No coincide con el contrato de API. |

### 3.1 Relaciones que no deben mezclarse

- `Product` es el producto canónico compartido entre comercios.
- `StoreProduct` es una publicación concreta de un producto en una tienda. Su `product_id` puede ser nulo.
- `StoreProduct.category_id` describe la categoría asignada a la publicación; `Product.category_id` describe la categoría canónica. Pueden diferir.
- `PriceObservation` pertenece a una publicación mediante `store_product_id`. No se relaciona directamente con `product_id` ni con `store_id`.

Por lo tanto, la fila actual de `products.json` se parece semánticamente a `StoreProduct`, pero tampoco coincide campo por campo: `name` debería mapearse a `product_name`, `url` a `product_url`, y `sku` no debe asumirse equivalente a `external_id` sin una decisión funcional.

## 4. Serialización y ejemplos representativos

- Los campos `Decimal` de Pydantic se serializan como cadenas JSON para preservar precisión. El frontend usa `DecimalString = string`; no convertir estos valores a `number` para cálculos financieros sin definir una estrategia decimal.
- Los campos `datetime` se representan como cadenas ISO 8601. Las rutas de observaciones y cotizaciones exigen zona horaria en sus parámetros temporales.
- Los campos anulables del esquema deben reflejarse como `T | null` en TypeScript; no deben confundirse con campos opcionales ausentes.

Los siguientes fragmentos ilustran la forma de las respuestas a partir de los esquemas Pydantic actuales. Los valores son ficticios y no representan datos de mercado:

```json
{
  "id": 12,
  "name": "Producto de ejemplo",
  "brand": null,
  "model": null,
  "description": "Descripción ilustrativa",
  "barcode": null,
  "category_id": 3
}
```

Ejemplo representativo de una publicación:

```json
{
  "id": 31,
  "store_id": 2,
  "product_id": 12,
  "category_id": 3,
  "external_id": "SKU-EJEMPLO",
  "product_url": "https://example.com/producto",
  "product_name": "Producto de ejemplo",
  "currency": "ARS"
}
```

Ejemplo representativo de observación de precio:

```json
{
  "id": 85,
  "store_product_id": 31,
  "amount": "1250.50",
  "promotional_price": null,
  "currency": "ARS",
  "source_url": null,
  "is_available": true,
  "observed_at": "2026-01-20T10:00:00Z"
}
```

Ejemplo representativo de cotización:

```json
{
  "id": 9,
  "source": "fuente-ejemplo",
  "rate_type": "official",
  "rate_side": "reference",
  "base_currency": "USD",
  "quote_currency": "ARS",
  "rate": "1250.50",
  "observed_at": "2026-01-20T09:00:00Z"
}
```

## 5. Endpoints existentes

Todas las rutas de negocio usan el prefijo `/api/v1`.

| Método y ruta | Parámetros / comportamiento comprobado | Uso potencial |
|---|---|---|
| `GET /health` | Devuelve estado de aplicación; no confirma disponibilidad de DB. | Liveness básico. |
| `GET /stores` | Devuelve tiendas activas ordenadas por nombre. | Home y filtros de Catálogo. |
| `GET /categories` | Devuelve categorías ordenadas por nombre. | Home y filtros de Catálogo. |
| `GET /products` | Lista productos canónicos; acepta `category_id`. | Consultas de productos canónicos. |
| `GET /products/paginated` | `limit` 1–100, `offset` >= 0, `category_id` opcional; devuelve `items,total,limit,offset`. | Paginación de productos canónicos, no publicaciones. |
| `GET /products/{product_id}` | Devuelve producto canónico o 404. | Detalle del producto canónico. |
| `GET /store-products` | Lista publicaciones; filtro opcional `store_id`. | Catálogo básico, con adaptación de campos. |
| `POST /store-products` | Crea publicación; responde 201 o 409 por conflicto de integridad. | Escritura de publicaciones; requiere protección antes de exponer. |
| `GET /price-observations` | Requiere `store_product_id`; acepta `start`, `end`, `limit` (1–1000). Orden descendente por `observed_at`. Fechas con zona horaria y `start <= end`. | Historial de una publicación. |
| `POST /price-observations` | Crea observación; `observed_at` debe incluir zona horaria; responde 201 o 409. | Ingesta de observaciones; requiere protección. |
| `GET /exchange-rates` | Requiere `rate_type`; acepta `on_date` con zona horaria; devuelve hasta 100 registros descendentes con fecha <= `on_date`. | Cotización por tipo y fecha. |

No se encontraron en el router revisado endpoints para búsqueda textual de publicaciones, catálogo compuesto, alta/consulta de ejecuciones de extracción, alertas, ni autenticación/login/registro. Tampoco hay endpoint para crear cotizaciones en el router revisado.

## 6. Pantallas y compatibilidad actual

### HomePage

Actualmente calcula tiendas activas, productos, categorías y cotización oficial desde mocks. Para consumir API:
- `GET /stores` y `GET /categories` pueden alimentar sus conteos.
- “Productos monitoreados” debe definirse: contar productos canónicos (`Product`) o publicaciones (`StoreProduct`).
- La cotización debe adaptar `rate_type`, `rate_side`, `observed_at` y `rate`; no puede seguir buscando `source === "oficial"` ni leer `recorded_at` sin una transformación acordada.

### CatalogoPage

Actualmente filtra `products.json` en memoria usando `store_id`, `category_id` y texto sobre `name`. Renderiza tienda, categoría y `url`.
- Puede obtener tiendas, categorías y publicaciones de endpoints actuales, pero debe distinguir `product_name`/ `product_url` de los campos del producto canónico.
- El endpoint de publicaciones no incluye el último precio.
- Consultar el historial una vez por cada tarjeta sería un patrón ineficiente; conviene definir una respuesta agregada para el catálogo.
- `FilterBar` recoge fechas, pero la página revisada no las incorpora al estado aplicado ni a los chips activos.

### DemoPage

Sus métricas y series están hardcodeadas. Debe permanecer rotulada como demo mientras no consuma una fuente de datos real.

## 7. Propuesta de contrato agregado para catálogo (no implementado)

Para una tarjeta de catálogo que necesita producto, publicación, tienda, ambas categorías y último precio, se propone estudiar una respuesta paginada como:

```text
CatalogPage
  items: CatalogItem[]
  total: integer
  limit: integer
  offset: integer

CatalogItem
  product: ProductOut
  listing: StoreProductOut
  store: StoreOut
  listing_category: CategoryOut | null
  product_category: CategoryOut | null
  latest_price: PriceObservationOut | null
```

Esta es una propuesta de diseño, no un endpoint ni un esquema actualmente publicado. La consulta debería resolver la última observación por publicación en el servidor, evitando una petición de historial por tarjeta.

## 8. Decisiones pendientes antes de implementar

1. **Categoría:** decidir si el filtro visible representa la categoría de la publicación, la categoría canónica o ambas. Si ambas se ofrecen, usar parámetros distintos.
2. **Fechas:** definir si el rango selecciona publicaciones con observaciones dentro del período y si `latest_price` significa último precio global o último precio dentro del rango.
3. **Búsqueda:** acordar si busca en `Product.name`, `StoreProduct.product_name`, marca, modelo u otros campos.
4. **Conteo Home:** definir si “productos monitoreados” cuenta productos únicos o publicaciones.
5. **Catálogo agregado:** decidir si se crea un endpoint compuesto o si una primera versión acepta combinar rutas existentes en el cliente.
6. **Cotizaciones:** acordar cómo presentar `rate_type` y `rate_side`; el tipo TS restringe `rate_side` a tres literales, mientras el esquema Pydantic lo declara como `str`.
7. **Autenticación:** el Issue #29 incluye login/registro/token, pero no existen rutas de autenticación en el router revisado. Separar ese alcance o bloquearlo hasta diseñar e implementar autenticación y autorización.

## 9. Incompatibilidades priorizadas

| Prioridad | Incompatibilidad | Consecuencia |
|---|---|---|
| Alta | `products.json` mezcla producto y publicación. | No puede tiparse como `ProductOut`; necesita modelarse como `StoreProduct` o transformarse. |
| Alta | Precios mock usan `product_id` y `store_id`; API usa `store_product_id`. | No se puede asociar el historial correctamente sin identificar la publicación. |
| Alta | Catálogo API no entrega último precio ni paginación de publicaciones. | Se requiere endpoint agregado o una estrategia de consultas explícita. |
| Media | Cotizaciones mock usan `pair` y `recorded_at`; API usa monedas separadas y `observed_at`. | Requiere adaptación de contrato y UI. |
| Media | Filtros de fecha se capturan pero no se aplican. | La interfaz aparenta admitir una función que no opera. |
| Media | `rate_side` es `string` en Pydantic y unión literal en TypeScript. | El contrato de runtime no valida la misma restricción que expresa TS. |
| Baja | `categories.json` agrega `description`. | Campo mock excedente; no debe suponerse disponible desde API. |

## 10. Dependencias para el Issue #29

El Issue #29 incluye registro, login y token; esas capacidades no aparecen implementadas en las rutas inspeccionadas. Antes de conectar pantallas:
1. Revisar y aprobar las correspondencias de este documento.
2. Resolver las decisiones de categoría, fechas, búsqueda y conteo.
3. Definir si se requiere endpoint agregado de catálogo.
4. Separar el trabajo de autenticación o definir su implementación y criterios de seguridad.
5. Definir URL de API por entorno, CORS, manejo de errores, estados vacíos y carga.
6. Proteger endpoints de escritura antes de exponer el backend públicamente.

## 11. Límites de esta revisión

- La revisión estática se hizo sobre los archivos indicados en la rama `develop` y el commit de referencia al inicio del documento.
- No se ejecutó la aplicación ni se consultó una instancia desplegada de OpenAPI en vivo.
- No se consultó ni modificó Neon.
- No se modificaron modelos, rutas, servicios, migraciones, mocks ni cliente HTTP.
- Los valores de los ejemplos JSON son ilustrativos, no datos reales.
