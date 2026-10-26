
# PriceScope — Modelo de datos

## 1. Objetivo

Definir las entidades necesarias para almacenar los comercios,
sus productos, los precios históricos, las monedas y las alertas.

Este documento representa el diseño inicial. Las tablas definitivas
deben contrastarse con los requerimientos del MVP antes de crear
las migraciones de base de datos.

## 2. Entidades

### stores

Representa un comercio o fuente de precios.

Un comercio puede publicar muchos productos.

### categories

Clasifica los productos, por ejemplo, alimentos, tecnología o moda.

Una categoría puede contener muchos productos publicados.

### canonical_products

Representa un producto común del catálogo de PriceScope.

Se utiliza para agrupar publicaciones que corresponden al mismo
producto o a una equivalencia aprobada.

No debe asumirse que dos productos con nombres parecidos son
necesariamente iguales.

### store_products

Representa una publicación concreta de un producto en una tienda.

Conserva datos específicos de la publicación, como la URL, el
identificador externo y el nombre original.

Puede estar vinculada a un producto común, pero esa relación
puede quedar pendiente cuando no se ha confirmado la equivalencia.

### price_observations

Registra una observación de precio en un momento determinado.

Las observaciones históricas deben conservarse para poder estudiar
cambios de precios a lo largo del tiempo.

Cada registro debe identificar el producto publicado, el importe,
la moneda y la fecha de observación.

### exchange_rates

Almacena tipos de cambio entre dos monedas y la fecha a la que
corresponde la cotización.

Debe definirse la fuente del tipo de cambio y la regla para
seleccionar la cotización aplicable a una observación de precio.

### alerts

Representa una regla de alerta asociada a un producto común.

Los criterios concretos —porcentaje de variación, precio objetivo
o ventana temporal— deben definirse antes de implementar el módulo.

## 3. Relaciones principales

- stores 1:N store_products.
- categories 1:N store_products.
- canonical_products 1:N store_products, cuando se ha confirmado
  la relación con el producto común.
- store_products 1:N price_observations.
- canonical_products 1:N alerts.

N significa "muchos". Por ejemplo, una tienda puede publicar
muchos productos, pero cada publicación pertenece a una tienda.

## 4. Reglas de integridad

- Las claves primarias identifican cada registro.
- Las claves foráneas mantienen la coherencia entre entidades.
- Los precios deben utilizar un tipo decimal adecuado, no números
  de punto flotante para cálculos monetarios.
- Las fechas deben permitir identificar cuándo se observó un precio.
- El historial no debe sobrescribirse cuando aparece un precio nuevo.
- La asociación de productos equivalentes debe poder quedar pendiente.

## 5. Decisiones pendientes

- Definir el vínculo entre observaciones de precios y tipos de cambio.
- Decidir si se conserva el precio original y el precio convertido.
- Definir restricciones para evitar observaciones duplicadas.
- Definir qué campos son obligatorios para cada fuente.
- Revisar si las alertas necesitan usuario, canal y estado de entrega.
