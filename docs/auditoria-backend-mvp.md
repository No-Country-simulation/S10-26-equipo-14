# Auditoría y alcance del backend MVP

## Auditoría inicial

La revisión inicial encontró un `develop` local obsoleto (`51840a1`). Se comprobó que `origin/develop` apuntaba a `4991e08`, que ya incluye la integración de Store (`cb0deba93496`) y los contratos TypeScript iniciales. La rama `feature/ps-mvp-backend` se creó desde `origin/develop`, y la nueva migración se encadena después de Store. Se conservaron cambios locales preexistentes (eliminación de `backend/alembic/.gitkeep` y archivos nuevos en `docs/issues/` y `scripts/`).

### Estado encontrado

- Backend: `/health` era el único endpoint. `Store` era el único modelo implementado en la rama previa y no estaba en `develop`.
- `backend/pyproject.toml` estaba vacío; las dependencias instaladas estaban en el entorno local, sin manifiesto reproducible. `.env.example` también estaba vacío.
- `category.py`, `price.py`, `product.py`, `exchange_rate.py` y `alert.py` estaban vacíos.
- No había extractores, servicios, esquemas Pydantic ni rutas de dominio.
- La migración previa solo creaba `stores` y no existía en la rama base `develop`.
- Las pruebas solo cubrían `/health` y metadatos básicos de `Store`; `conftest.py` estaba vacío.
- Alembic ya tenía configuración/env, pero el registro de metadatos conocía únicamente Store.
- El frontend tiene páginas Home/About/Demo, contratos TypeScript preliminares y mocks JSON, pero no cliente HTTP ni consumo de API. Sus tipos aún difieren del nuevo dominio: `Product` modela una publicación directa (`store_id`, `sku`, `url`, `is_active`), `PriceObservation` usa `product_id`/`store_id` y `ExchangeRate` usa `pair`/`recorded_at`; el backend separa producto canónico y publicación, registra observaciones por `store_product_id` y divide tipo/monedas/fecha de cotización. `Category` frontend tiene `description`, ausente en el modelo persistido; `Store` requiere `created_at`, que el schema de respuesta de tienda no expone. TypeScript espera `number` para montos/tasas mientras JSON transmite `Decimal` como string. No se modificó el frontend.
- La documentación de arquitectura y datos era conceptual y dejaba pendientes la granularidad de cotizaciones, deduplicación y fecha aplicable.
- No se encontraron implementaciones duplicadas funcionales. Los placeholders vacíos y la documentación divergente son la principal inconsistencia.

## Riesgos de integración

1. El frontend no consume aún el backend; sus interfaces y mocks no coinciden completamente con los contratos API implementados.
2. El modelo distingue productos canónicos de publicaciones de tienda. El MVP permite una publicación sin producto canónico para evitar emparejamientos dudosos.
3. Una observación se identifica por publicación y timestamp; dos cambios reales con la misma marca temporal se rechazan. El recolector debe normalizar timestamps y reintentar idempotentemente.
4. `on_date` de cotizaciones funciona como consulta “última cotización de ese tipo hasta el instante indicado”, no como coincidencia por día calendario.
5. Los IDs son `BIGINT` en PostgreSQL. Se usa una variante `INTEGER` solo para permitir pruebas SQLite locales.
6. No se conectó a Neon ni se aplicaron migraciones. La revisión Alembic inicial crea el esquema completo desde una base vacía; requiere revisión antes de cualquier despliegue.
7. BCRA y Ámbito, así como los catálogos de Carrefour/Frávega, no se consultaron. Los conectores son contratos/primitivas, no integraciones externas verificadas.

## Bloques implementados

### Bloque A — Persistencia y contratos

Modelos `Category`, `Product`, `StoreProduct`, `PriceObservation`, `ExchangeRate` y `ExtractionRun`, con relaciones, índices, claves foráneas, restricciones de unicidad, montos decimales y marcas temporales con zona horaria. `Store` se conserva como entidad raíz.

### Bloque B — API de consulta y registro

Rutas bajo `/api/v1`: listado de tiendas activas, categorías, productos (opcional por categoría), publicaciones (opcional por tienda), creación de publicaciones, creación/consulta histórica de observaciones y consulta de cotizaciones por tipo y fecha límite. FastAPI publica OpenAPI automáticamente en `/docs`.

### Bloque C — Ingestión modular

`app.services.ingestion` define protocolos de proveedor, normalización decimal/moneda/fecha, persistencia de cotizaciones y precios, y auditoría de ejecuciones. No realiza scraping ni llama fuentes externas.

## Orden recomendado pendiente

1. Revisar la migración inicial en CI con PostgreSQL local desechable y acordar explícitamente el esquema con el equipo.
2. Acordar tipos y semántica de `rate_type`, fuentes, frecuencia y política de cotización por fecha.
3. Implementar/adaptar proveedores oficiales solo tras verificar acceso, formato y estabilidad documental de cada fuente.
4. Probar captura inicial Carrefour mediante un mecanismo permitido y medir cambios del sitio; luego evaluar Frávega.
5. Añadir pruebas PostgreSQL para restricciones/migraciones y pruebas de servicio para idempotencia y fallos de extracción.
6. Acordar y consumir contratos desde el frontend existente.

La configuración ya no carga automáticamente `.env`: la aplicación toma `DATABASE_URL` del entorno del proceso y usa una URL local no secreta por defecto. El entorno de despliegue debe inyectar su propia URL; no se inspeccionó ni se imprimió el `.env` del repositorio.

## Verificación local

Suite backend ejecutada con SQLite en memoria: **8 pruebas aprobadas**. Alembic generó correctamente el SQL PostgreSQL offline desde `cb0deba93496` hasta `4db267e3b121`. No se ejecutaron pruebas frontend ni migraciones contra una base real.
