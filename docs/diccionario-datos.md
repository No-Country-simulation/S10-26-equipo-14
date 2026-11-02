
# PriceScope — Diccionario de datos

## Convenciones

- PK: clave primaria.
- FK: clave foránea.
- NOT NULL: campo obligatorio.
- UNIQUE: valor único según la restricción definida.
- Los tipos y restricciones definitivos serán los de las migraciones.

## 1. stores

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador interno |
| name | VARCHAR(150) | NOT NULL | Nombre del comercio |
| base_url | TEXT | NOT NULL | URL principal de la fuente |
| country | VARCHAR(100) | Opcional | País del comercio |
| is_active | BOOLEAN | NOT NULL | Indica si la fuente está habilitada |
| created_at | TIMESTAMPTZ | NOT NULL | Fecha de creación |

## 2. categories

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador de categoría |
| name | VARCHAR(100) | NOT NULL | Nombre de la categoría |

Debe definirse si el nombre será único globalmente o dentro
de una jerarquía de categorías.

## 3. canonical_products

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador del producto común |
| name | VARCHAR(250) | NOT NULL | Nombre normalizado |
| brand | VARCHAR(150) | Opcional | Marca |
| model | VARCHAR(150) | Opcional | Modelo o referencia |

La estrategia de identificación de productos equivalentes
debe documentarse por separado.

## 4. store_products

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

## 5. price_observations

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

## 6. exchange_rates

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador del tipo de cambio |
| base_currency | CHAR(3) | NOT NULL | Moneda de origen |
| quote_currency | CHAR(3) | NOT NULL | Moneda de destino |
| rate | NUMERIC(18,8) | NOT NULL | Unidades de destino por unidad de origen |
| observed_at | TIMESTAMPTZ | NOT NULL | Fecha de la cotización |

Ejemplo: si base_currency es USD, quote_currency es DOP y rate
es 60, entonces 1 USD equivale a 60 DOP según esa cotización.

## 7. alerts

| Campo | Tipo propuesto | Regla | Significado |
|---|---|---|---|
| id | BIGINT | PK | Identificador de alerta |
| canonical_product_id | BIGINT | FK, NOT NULL | Producto vigilado |
| threshold | NUMERIC(14,4) | Pendiente | Umbral configurado |
| is_active | BOOLEAN | NOT NULL | Indica si la regla está activa |

Antes de implementar alerts deben definirse el tipo de umbral,
su unidad, la dirección de la variación y la ventana temporal.

## Esquema actual del backend MVP

Las tablas reales se denominan `products` (producto canonico) y
`store_products` (publicacion de una tienda). Esta seccion corresponde a las
migraciones `4db267e3b121` y `d8f31a9c0e42` y supersede las filas marcadas como
propuestas en las secciones iniciales.

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

Para una observacion fechada, consultar `GET /api/v1/exchange-rates` con
`rate_type` y `on_date` (timestamp con zona). La API devuelve tasas de ese tipo
con `observed_at <= on_date`, ordenadas de mas reciente a mas antigua; el primer
resultado es la ultima cotizacion conocida no posterior a la fecha solicitada.
Si se necesita un lado de compra/venta especifico, seleccionar por `rate_side`.

## Nota de mantenimiento

Este diccionario debe actualizarse cuando cambie una migración
o se apruebe una modificación del modelo de datos.
