
# PriceScope — Diccionario de datos

## Precedencia y estado del contenido

La seccion **Esquema vigente** describe el contrato persistido actual y fue
contrastada con los modelos SQLAlchemy y las migraciones `4db267e3b121` y
`d8f31a9c0e42`. Las secciones iniciales conservan un borrador de diseño legado;
no representan el esquema desplegable ni el contrato de API. En caso de
diferencia, prevalecen modelos y migraciones vigentes.

## Convenciones

- PK: clave primaria.
- FK: clave foránea.
- NOT NULL: campo obligatorio.
- UNIQUE: valor único según la restricción definida.
- Los tipos y restricciones definitivos serán los de las migraciones.

## Borrador legado: stores (propuesta, no vigente)

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador interno |
| name | VARCHAR(150) | NOT NULL | Nombre del comercio |
| base_url | TEXT | NOT NULL | URL principal de la fuente |
| country | VARCHAR(100) | Opcional | País del comercio |
| is_active | BOOLEAN | NOT NULL | Indica si la fuente está habilitada |
| created_at | TIMESTAMPTZ | NOT NULL | Fecha de creación |

## Borrador legado: categories (propuesta, no vigente)

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador de categoría |
| name | VARCHAR(100) | NOT NULL | Nombre de la categoría |

Debe definirse si el nombre será único globalmente o dentro
de una jerarquía de categorías.

## Borrador legado: canonical_products (propuesta, no vigente; la tabla vigente es products)

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador del producto común |
| name | VARCHAR(250) | NOT NULL | Nombre normalizado |
| brand | VARCHAR(150) | Opcional | Marca |
| model | VARCHAR(150) | Opcional | Modelo o referencia |

La estrategia de identificación de productos equivalentes
debe documentarse por separado.

## Borrador legado: store_products (propuesta, no vigente)

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador de la publicación |
| store_id | BIGINT | FK, NOT NULL | Comercio que publica el producto |
| category_id | BIGINT | FK, Opcional | Categoría asignada |
| canonical_product_id | BIGINT | FK, Opcional | Producto común relacionado |
| external_id | VARCHAR(200) | Opcional | Identificador en la tienda |
| product_url | TEXT | NOT NULL | URL de la publicación |
| product_name | VARCHAR(300) | NOT NULL | Nombre publicado por la tienda |

La combinación de tienda y external_id puede utilizarse para
evitar duplicados cuando la fuente proporcione identificadores
estables. La restricción definitiva debe validarse por fuente.

## Borrador legado: price_observations (propuesta, no vigente)

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador de observación |
| store_product_id | BIGINT | FK, NOT NULL | Publicación observada |
| price | NUMERIC(14,4) | NOT NULL | Importe observado |
| currency | CHAR(3) | NOT NULL | Código de moneda, por ejemplo USD |
| observed_at | TIMESTAMPTZ | NOT NULL | Fecha y hora de observación |

El importe debe ser positivo salvo que un requerimiento justifique
otro comportamiento. La precisión debe confirmarse según los
precios y monedas que se analizarán.

## Borrador legado: exchange_rates (propuesta, no vigente)

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador del tipo de cambio |
| base_currency | CHAR(3) | NOT NULL | Moneda de origen |
| quote_currency | CHAR(3) | NOT NULL | Moneda de destino |
| rate | NUMERIC(18,8) | NOT NULL | Unidades de destino por unidad de origen |
| observed_at | TIMESTAMPTZ | NOT NULL | Fecha de la cotización |

Ejemplo: si base_currency es USD, quote_currency es DOP y rate
es 60, entonces 1 USD equivale a 60 DOP según esa cotización.

## Borrador legado: alerts (propuesta, no implementada)

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador de alerta |
| canonical_product_id | BIGINT | FK, NOT NULL | Producto vigilado |
| threshold | NUMERIC(14,4) | Pendiente | Umbral configurado |
| is_active | BOOLEAN | NOT NULL | Indica si la regla está activa |

Antes de implementar alerts deben definirse el tipo de umbral,
su unidad, la dirección de la variación y la ventana temporal.

## Esquema vigente del backend MVP

Las tablas reales se denominan `products` (producto canonico) y
`store_products` (publicacion de una tienda). Esta seccion corresponde a las
migraciones `4db267e3b121` y `d8f31a9c0e42` y supersede las filas marcadas como
propuestas en las secciones iniciales. Las tablas siguientes detallan todos los
campos de `categories` y `products`; las secciones iniciales con esos nombres
son solo borradores legados.

### `categories`

| Campo | Tipo PostgreSQL | Regla | Significado |
|---|---|---|---|
| `id` | BIGINT | PK, autoincremental | Identificador interno |
| `name` | VARCHAR(120) | NOT NULL, UNIQUE (`uq_categories_name`) | Nombre de la categoría |
| `slug` | VARCHAR(140) | NOT NULL, UNIQUE (`uq_categories_slug`) | Identificador legible para URL |

### `products`

| Campo | Tipo PostgreSQL | Regla | Significado |
|---|---|---|---|
| `id` | BIGINT | PK, autoincremental | Identificador del producto canónico |
| `name` | VARCHAR(250) | NOT NULL, índice `ix_products_name` | Nombre normalizado |
| `brand` | VARCHAR(120) | NULL | Marca |
| `model` | VARCHAR(120) | NULL | Modelo o referencia |
| `description` | TEXT | NULL | Descripción del producto |
| `barcode` | VARCHAR(64) | NULL, UNIQUE cuando informado (`uq_products_barcode`) | Código de barras textual; conserva ceros iniciales |
| `category_id` | BIGINT | FK a `categories.id`, NULL, índice `ix_products_category_id`, ON DELETE SET NULL | Categoría canónica |

La relación ORM `Category.products` vincula categorías con productos y
`Product.category` permite consultar la categoría canónica. Al borrar una
categoría referenciada por un producto, la FK establece `category_id` en NULL.

| Tabla.campo | Tipo | Regla | Significado |
|---|---|---|---|
| products.barcode | VARCHAR(64) | Opcional, UNIQUE cuando informado | Código de barras textual, conserva ceros iniciales |
| store_products.store_id | BIGINT | FK NOT NULL, RESTRICT | Tienda que publica |
| store_products.product_id | BIGINT | FK opcional, RESTRICT | Producto canonico asociado |
| store_products.category_id | BIGINT | FK opcional, SET NULL | Categoria asignada por la tienda |
| store_products.external_id | VARCHAR(180) | Opcional; UNIQUE junto a store_id | Identificador de origen cuando existe |
| price_observations.store_product_id | BIGINT | FK NOT NULL, RESTRICT | Publicacion observada |
| price_observations.amount | NUMERIC(14,2) | NOT NULL, positivo | Precio observado como Decimal |
| price_observations.promotional_price | NUMERIC(14,2) | Opcional, positivo | Precio promocional cuando la fuente lo informa |
| price_observations.source_url | TEXT | Opcional | URL usada para esa observacion |
| price_observations.is_available | BOOLEAN | Opcional | Disponibilidad; NULL significa no informada |
| price_observations.observed_at | TIMESTAMPTZ | NOT NULL | Momento de captura con zona horaria |
| exchange_rates.rate_type | VARCHAR(30) | NOT NULL | Tipo de cotizacion, por ejemplo official o blue |
| exchange_rates.rate_side | VARCHAR(10) | NOT NULL; reference/buy/sell | Lado publicado por la fuente; reference es el valor unico |
| exchange_rates.source | VARCHAR(100) | NOT NULL | Fuente identificable de la cotizacion |
| exchange_rates.base_currency | VARCHAR(3) | NOT NULL | Moneda base (por defecto USD) |
| exchange_rates.quote_currency | VARCHAR(3) | NOT NULL | Moneda cotizada (por defecto ARS) |
| exchange_rates.rate | NUMERIC(18,6) | NOT NULL, positivo | Tasa como Decimal |
| exchange_rates.observed_at | TIMESTAMPTZ | NOT NULL | Momento de vigencia/publicacion con zona horaria |

La unicidad `(store_id, external_id)` permite varios `NULL` en PostgreSQL; por
ello no se fabrica un identificador para publicaciones que carecen de uno. La
unicidad nullable de `products.barcode` permite multiples productos sin codigo.

El endpoint y sus filtros implementados se describen en “Comportamiento
implementado y pendiente” más abajo. Esta tabla por sí sola no implica que la
API permita filtrar por cada campo persistido.

### Criterio de selección de cotizaciones

#### Política definida

Para una comparación se debe fijar el tipo (`official` o `blue`, donde blue
representa el mercado paralelo), el lado (`reference`, `buy` o `sell`), la
moneda base, la moneda cotizada y un instante de corte con zona horaria. Una
tasa `reference` es la cotización única publicada por una fuente; `buy` y
`sell` son valores diferentes y nunca se sustituyen uno por otro. Solo son
comparables registros con coincidencia exacta de tipo, lado y par de monedas.

Por fuente, se elige la observación más reciente cuyo `observed_at` sea menor o
igual al instante de corte. Si hay varias fuentes elegibles, la fuente
preferida debe configurarse explícitamente usando criterios documentados de
cobertura y confiabilidad; no se selecciona silenciosamente por orden ni se
mezclan lados o proveedores. Si no hay preferencia configurada, se mantienen
las tasas diferenciadas por fuente para que el consumidor decida. Una consulta
por día debe convertir el final del día de negocio a un instante con zona
horaria explícita.

#### Comportamiento implementado y pendiente

`GET /api/v1/exchange-rates` implementa actualmente filtros por `rate_type` y
`on_date` opcional; cuando se proporciona, `on_date` debe tener zona horaria y
se devuelven hasta 100 registros con `observed_at <= on_date`, ordenados de más
reciente a más antiguo. El endpoint todavía no filtra por fuente, lado ni par
de monedas, y no resuelve la fuente preferida. La política de selección
detallada de esta sección está definida para el consumidor, pero su aplicación
completa requiere ampliar el contrato/API en un cambio futuro; no se afirma que
esté implementada.

## Nota de mantenimiento

Este diccionario debe actualizarse cuando cambie una migración
o se apruebe una modificación del modelo de datos.
