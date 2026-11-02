# Contrato de modelos del backend MVP

## Entidades

- `Product` es el producto canónico compartido entre comercios.
- `StoreProduct` es la publicación específica de una tienda. Mantiene por
  separado `store_id`, `product_id` (opcional), `category_id` (opcional), el
  identificador externo y la URL/nombre que publica el comercio.
- La categoría de una publicación puede diferir de la categoría del producto
  canónico. Se conserva como dato de fuente y queda con `NULL` si se elimina la
  categoría (`ON DELETE SET NULL`).
- `Product.barcode` es nullable y único cuando está informado; usa `VARCHAR(64)`
  para conservar ceros iniciales y representar varios estándares sin convertir
  el identificador a número.
- `PriceObservation` referencia `store_product_id`, no Product/Store directamente.
  Sus datos de origen, promoción y disponibilidad son opcionales; disponibilidad
  `NULL` significa desconocida/no informada.
- `ExchangeRate.rate_type` clasifica `official`, `blue` u otros tipos y
  `rate_side` discrimina `reference`, `buy` y `sell`. El lado `reference` se
  asigna por defecto cuando la fuente publica un único valor.

## Serialización

Los campos SQL `NUMERIC` se representan como `Decimal` en Python y como cadenas
JSON en las respuestas Pydantic de FastAPI. Las interfaces TypeScript usan el
alias `DecimalString` (`string`) para evitar la pérdida de precisión de `number`.
Los timestamps se serializan como cadenas ISO 8601 con zona horaria.

## Migración correctiva

La revisión `d8f31a9c0e42` depende de `4db267e3b121` y agrega el barcode,
clasificación de publicación, datos promocionales/de origen y lado de tasa. No
elimina filas ni tablas. Se eligió una revisión correctiva separada para
preservar el historial ya publicado de la revisión anterior. La revisión aún
debe validarse/aplicarse por los procedimientos del entorno; no se ha aplicado
en Neon.
