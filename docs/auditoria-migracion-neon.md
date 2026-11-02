# Auditoría previa a la migración de Neon

**Fecha:** 2026-11-02
**Rama:** `feature/ps-mvp-backend`
**Revisión pendiente:** `4db267e3b121`
**Decisión tras corrección local:** **LISTA PARA APLICAR**

## Alcance y método

La inspección original de Neon fue de solo lectura. En esta corrección se modificaron únicamente modelos, la revisión pendiente, pruebas e informes; Neon no fue contactado ni modificado. Se regeneró el DDL offline para `cb0deba93496:4db267e3b121`. No se ejecutaron migraciones ni sentencias de escritura en Neon. No se consultaron ni imprimieron credenciales o URL de conexión.

La revisión `cb0deba93496` no se modificó porque ya está aplicada. Se editó `4db267e3b121` en lugar de crear una revisión adicional: Neon sigue en su revisión padre y la revisión dependiente todavía no se ha aplicado.

## Último estado de Neon observado

Este estado proviene de la auditoría previa; en la corrección actual no se estableció conexión con Neon.

El esquema activo consultado fue `public`.

| Objeto/estado | Resultado |
| --- | --- |
| `alembic_version` | Existe; contiene `cb0deba93496` |
| Revisión `cb0deba93496` | Aplicada |
| Revisión `4db267e3b121` | Pendiente; DDL corregido localmente y aún no aplicado |
| Tablas actuales | `alembic_version`, `stores` |
| Tabla `stores` | Existe y coincide con la revisión/modelo: `id BIGINT` autoincremental, `name VARCHAR`, `base_url TEXT`, `country VARCHAR NULL`, `is_active BOOLEAN NOT NULL DEFAULT true`, `created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()` |
| Colisiones de nombres con las tablas nuevas | Ninguna |
| Conectividad | SQLAlchemy ejecutó `SELECT 1` correctamente |

## Comparación de modelos y migraciones

`cb0deba93496_create_stores.py` y `Store` coinciden en nombres, tipos PostgreSQL, nullability y defaults. La variante `INTEGER` declarada en los modelos para SQLite no afecta PostgreSQL; allí se compila como `BIGINT`/`BIGSERIAL`, igual que la migración.

La revisión `4db267e3b121_create_market_data_schema.py` coincide con los modelos para las tablas nuevas:

- **Claves:** todas las tablas tienen `BIGINT` autoincremental como PK. Las FK usan `BIGINT` y apuntan a las PK correspondientes.
- **Tipos:** nombres y textos usan `VARCHAR`/`TEXT`; importes son `NUMERIC(14,2)`; tasas `NUMERIC(18,6)`; fechas son `TIMESTAMP WITH TIME ZONE`.
- **Nullability:** `Category.name/slug`, `Product.name`, datos requeridos de `StoreProduct`, importe/moneda/fecha de `PriceObservation`, fuente/tipo/tasa/fecha de `ExchangeRate` y fuente/estado/fecha inicio/contador de `ExtractionRun` son `NOT NULL`. Las columnas opcionales permanecen `NULL`.
- **Unicidad:** `categories.name`, `categories.slug`, `(store_id, external_id)`, `(store_product_id, observed_at)` y `(source, rate_type, base_currency, quote_currency, observed_at)` coinciden.
- **Checks:** importe de precio y tasa deben ser mayores que cero; ambos checks coinciden entre modelo y migración.
- **Índices:** coinciden los índices explícitos y los generados por `index=True` para producto/nombre, categoría, tienda/publicación, historial de precios, tipo/fecha de cotización y fuente de ejecución.
- **Defaults:** `ARS`, `USD`, `true`, `now()` y contador cero coinciden. Los defaults Python donde están definidos complementan los defaults de servidor.
- **Relaciones tras el cambio:** categoría→producto conserva `ON DELETE SET NULL`; producto canónico→publicación, tienda→publicación y publicación→observaciones usan `RESTRICT`. Coinciden entre modelos y revisión pendiente.

## SQL generado

El SQL PostgreSQL pendiente se guardó en [4db267e3b121_create_market_data_schema.sql](sql/4db267e3b121_create_market_data_schema.sql). Crea `categories`, `products`, `store_products`, `price_observations`, `exchange_rates` y `extraction_runs`, sus restricciones e índices, y actualiza `alembic_version` de `cb0deba93496` a `4db267e3b121` al final de la transacción.

El archivo fue producido con `alembic upgrade cb0deba93496:4db267e3b121 --sql`; no fue ejecutado contra Neon.

## Problemas y riesgos

### Política de retención aplicada en el código pendiente

Se sustituyeron las cascadas peligrosas por `ON DELETE RESTRICT`. Se eligió `RESTRICT` en vez de `NO ACTION` para expresar que el borrado debe rechazarse inmediatamente cuando quedan referencias; no se necesita una FK diferible para este dominio. Una tienda con publicaciones, una publicación con observaciones y un producto canónico con publicaciones no pueden eliminarse físicamente mientras existan referencias. La baja de tienda se representa mediante `stores.is_active = false`.

Las relaciones ORM usan `passive_deletes="all"` sin cascada ORM, para delegar el rechazo al motor y evitar que SQLAlchemy ponga FK requeridas en `NULL`. `Store.deactivate()` aplica la baja lógica. Un listener `before_flush` bloquea borrar observaciones mediante SQLAlchemy; una retención autorizada necesitará un procedimiento explícito revisado. Las pruebas SQLite con FK activas cubren las rutas ORM con las colecciones cargadas. La suite de integración posterior también probó la política en PostgreSQL local 16.

### Duplicados con identificador externo nulo

`external_id` es nullable. PostgreSQL permite varias filas con `NULL` en `(store_id, external_id)`. Cuando falte, la estrategia propuesta es comparar una URL canonicalizada de la fuente (host/ruta y parámetros de seguimiento retirados), sin fabricar un `external_id`. Si la URL tampoco es estable, no deduplicar automáticamente y marcar para revisión manual. No se impuso unicidad por URL porque su estabilidad no está garantizada.

### Validaciones de dominio limitadas al tipo

`currency VARCHAR(3)` no valida códigos ISO; `ExtractionRun.status VARCHAR(20)` no limita estados permitidos. No impide esta migración, pero las reglas se sostienen hoy en aplicación/proveedor y no en la base. Acordar si requieren checks antes de estabilizar el contrato.

## Pérdida de datos y compatibilidad

- El DDL pendiente crea tablas, restricciones e índices y avanza `alembic_version`; no altera ni elimina filas de las tablas actuales. No se detecta pérdida inmediata de datos al aplicar esta revisión sobre el estado observado.
- Los nombres de tablas pendientes no chocan con objetos existentes.
- `BIGSERIAL`, `NUMERIC`, `TIMESTAMP WITH TIME ZONE`, FK `ON DELETE`, checks e índices son compatibles con PostgreSQL/Neon.
- Neon ya registra `cb0deba93496`; por tanto, la nueva revisión se ejecutaría después de la tabla `stores` existente.
- No se detectaron diferencias de definición entre los modelos y el DDL para la revisión pendiente.

## Recomendaciones

1. Mantener las bajas de tienda como `is_active = false`; no añadir borrado físico de tiendas, publicaciones ni productos enlazados sin revisar retención.
2. Usar la estrategia de URL natural para publicaciones sin `external_id`; si no hay URL estable, no deduplicar automáticamente.
3. Definir si `rate_type`, `ExtractionRun.status` y los códigos de moneda requieren checks antes de estabilizar el contrato.
4. Revisar el SQL regenerado y obtener aprobación explícita antes de aplicarlo. Esta corrección no aplicó la revisión.

## Decisión final

**LISTA PARA APLICAR.** La revisión pendiente usa `RESTRICT` en las relaciones que protegen publicaciones e historial, y el ORM delega el rechazo al motor. La baja lógica de tienda preserva sus referencias; el ORM también bloquea el borrado de una observación individual. Las pruebas confirman que los intentos de borrar tienda, publicación, producto canónico relacionado u observación no eliminan historial. El último estado observado de Neon fue `cb0deba93496`; la revisión corregida no se ha aplicado desde el entorno de desarrollo. La unicidad de publicaciones sin `external_id` se gestiona según la estrategia natural descrita arriba.

La protección de borrado de observaciones cubre operaciones ORM. Un acceso SQL privilegiado puede omitir reglas de aplicación; si se requiere protección también frente a SQL manual, deberá definirse un mecanismo de permisos/retención específico en PostgreSQL antes de conceder ese acceso.

## Validación PostgreSQL local posterior

Con autorización explícita se creó la base local aislada `pricescope_test`; no se reutilizó ni eliminó ninguna base preexistente. La suite de integración aplica Alembic solo después de validar host loopback, nombre de base y estado inicial permitido. Alembic dejó la base local en `4db267e3b121` con las ocho tablas esperadas; `alembic check` no detectó diferencias entre modelos y esquema. Las pruebas usan transacciones revertidas y la verificación posterior encontró cero filas en `stores` y `price_observations`. Resultado combinado: **18 pruebas aprobadas**. Neon no fue usado durante esta validación.
