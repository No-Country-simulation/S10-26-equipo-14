
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

## Nota de mantenimiento

Este diccionario debe actualizarse cuando cambie una migración
o se apruebe una modificación del modelo de datos.
