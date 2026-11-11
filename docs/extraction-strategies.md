# Motor de extraccion publica

## Arquitectura y Credicoop

`PublicStoreExtractor` implementa el contrato `StoreExtractor` para hosts HTTPS registrados distintos de Fravega. Consulta `robots.txt` antes de la ficha, aplica timeout y limite de respuesta, limita la tasa y rechaza redirecciones a otros hosts. Su parser comun es `parse_html_product` en `backend/app/extractors/strategies.py`.

La extraccion real de Credicoop se obtuvo con `PublicStoreExtractor` -> `parse_html_product`, y guardo una observacion de `1086665.88 ARS`. La ejecucion original solo persistio `source=Public HTML strategies`; no guardo el subtipo de marcado. No se conservo el HTML original, por lo que no afirmamos que Open Graph fuera el formato real de aquella respuesta. En adelante, `ProductSnapshot.extraction_format` y el diagnostico por URL registran si se uso JSON-LD, Open Graph/product metadata, Microdata/RDFa, JSON embebido, Shopify o selectores HTML configurados.

La fixture `backend/tests/fixtures/extraction/credicoop_product_metadata.html` es una muestra sintetica de regresion basada en los campos observados (nombre, precio y moneda); no es una copia de la pagina de Credicoop. La prueba offline confirma que la estrategia Open Graph/product metadata reproduce el importe y recorre el servicio, las asociaciones y el endpoint de observaciones sin Internet.

Se aceptan Product/Offer/AggregateOffer/PriceSpecification JSON-LD, Microdata/RDFa, Open Graph/product metadata, JSON embebido como `__NEXT_DATA__`, objetos de producto Shopify y selectores simples configurables (etiqueta, clase, id o atributo). AggregateOffer solo se acepta si low/high coinciden. `compare_at_price` se ignora. Se exige nombre, precio positivo, moneda ISO admitida y URL de origen. No se usa Playwright ni APIs privadas.

Los estados de extraccion son `SUCCESS`, `BLOCKED`, `RATE_LIMITED`, `LOCATION_REQUIRED`, `PRICE_NOT_FOUND`, `PRODUCT_NOT_FOUND`, `UNSUPPORTED` y `NETWORK_ERROR`. `ExtractionRun.error_summary` conserva diagnosticos JSON por URL (HTTP, MIME, formato, producto y moneda) sin guardar cabeceras ni cuerpos.

## Verificacion real registrada

En la SQLite aislada `backend/.local/verification/creditcoop_test_2.sqlite3` quedaron 1 tienda, 1 producto canonico, 1 `StoreProduct`, 1 `ExtractionRun` (`SUCCESS`) y 1 `PriceObservation` por `1086665.88 ARS`. URL:

https://tiendacredicoop.coop/televisores-y-accesorios/43925-smart-tv-samsung-qled-4-k-uhd-55-qn-55-q-6-faag-7798180339319.html

La observacion quedo a `2026-11-11 01:55:18 UTC` (10 de noviembre, 21:55:18 America/La_Paz). La base de verificacion sigue separada; no se copia automaticamente a la base principal.

No se hicieron nuevas peticiones a tiendas en esta consolidacion. Las pruebas siguientes usan solo fixtures locales.

## Consumo por API y frontend

El backend ya expone:

- `GET /api/v1/products/paginated-with-prices` devuelve la pagina de productos canonicos, incluyendo `latest_price` (importe, moneda, tienda, fecha, disponibilidad y URL) o `null` si no hay observaciones.
- `GET /api/v1/price-observations` con filtros `store_id`, `store_product_id`, `category_id`, `start`, `end` y `limit`.
- `POST /api/v1/management/stores/{store_id}/extract` ejecuta una extraccion local y devuelve estado y conteos. La peticion requiere cliente loopback y evita duplicados concurrentes por tienda en el proceso.
- `GET /api/v1/management/stores/{store_id}/extractions?limit=10` devuelve el historial y conteo de observaciones por ejecucion.
- `GET /api/v1/store-products`, `GET /api/v1/products` y `GET /api/v1/stores` para resolver las asociaciones del precio.

`CatalogoPage` consume la ruta paginada con ultimo precio; conserva filtros y paginacion e indica cuando no hay observacion. `TiendasPage` permite ejecutar extracciones, muestra progreso/resultado, conteos e historial y permite consultar las observaciones de cada ejecucion. `DivisasPage` sigue usando `fetchPriceObservations` para su serie temporal ARS. Para visualizar la base verificada, iniciar deliberadamente un backend local con esa SQLite; no se copia a la base principal.

Desde `backend`, el CLI local se ejecuta asi:

```powershell
python -m app.commands.pricescope_local --db .local/pricescope.sqlite3 extract --store-id 1
python -m app.commands.pricescope_local --db .local/pricescope.sqlite3 observations --store-id 1
```
