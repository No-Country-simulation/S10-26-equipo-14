# Proveedores de ingesta: tareas pendientes

## MVP local del extractor de precios

El backend ahora incluye un contrato común en `backend/app/extractors/base.py`,
un registro de adaptadores y un adaptador inicial de Frávega. La selección se
apoya en los proveedores candidatos ya documentados y en sus reglas públicas:
el `robots.txt` de Frávega no bloquea las páginas de producto bajo `/p/`, pero
sí bloquea rutas de búsqueda y vistas internas. El adaptador consulta únicamente
URLs `/p/` que ya existan en `store_products`; no recorre catálogos, sitemaps,
búsquedas ni endpoints internos. Antes de solicitar un producto vuelve a leer
`robots.txt` y cancela la ejecución si no puede comprobarlo o si la ruta no está
permitida. Respeta `Crawl-delay`/`Request-rate` si se publican y aplica como
mínimo 1,5 segundos entre solicitudes. Ante HTTP 403/429 no reintenta ni intenta
eludir el bloqueo.

El adaptador toma un único `Product` y `Offer` JSON-LD inequívocos con nombre,
precio positivo y moneda. Si hay varias ofertas, falta el precio o el esquema no
es reconocible, registra el error y no inventa ni guarda un precio. Asocia por
código de barras cuando existe; si la publicación ya está asociada conserva el
producto canónico y solo completa metadatos vacíos. Si no hay asociación ni
código de barras, crea un producto canónico con el nombre leído de la página.
La categoría observada solo se asigna a `StoreProduct.category_id` cuando ya
existe una coincidencia exacta; no se infiere la categoría canónica. Cada ejecución crea
un `ExtractionRun`; las observaciones históricas son append-only. Las URLs se
muestrean una sola vez por ejecución y usan la marca UTC de inicio, junto con la
restricción única existente, para no duplicar una observación al reintentar con
el mismo instante.

No hay tiendas ni publicaciones reales preconfiguradas en el repositorio: los
registros de `stores.json` son demostrativos. El CLI registra solo la información
que proporcione el operador y usa por defecto `backend/.local/pricescope.sqlite3`
(ignorado por Git). No lee `.env` ni usa la configuración compartida de la API.
`db init` inspecciona una base existente, rechaza esquemas desconocidos y aplica
las revisiones locales hasta el head `a6f20488d7b1`; no se conecta a PostgreSQL,
Neon ni Render.

Desde `backend/`, sustituye los marcadores por datos que hayas verificado. La URL
debe ser una URL real de publicación proporcionada explícitamente; no uses URLs
de ejemplo o de pruebas para una extracción real:

```bash
python -m app.commands.pricescope_local db init
python -m app.commands.pricescope_local store add --name "Frávega" --base-url "https://www.fravega.com" --country AR
python -m app.commands.pricescope_local listing add --store-id ID_TIENDA --name "NOMBRE_PUBLICADO" --url "URL_REAL_DE_PRODUCTO" --currency ARS
python -m app.commands.pricescope_local extract --store-id ID_TIENDA
python -m app.commands.pricescope_local observations --store-id ID_TIENDA
python -m app.commands.pricescope_local runs
```

Omite `--gtin` si no conoces el GTIN. El alta de tienda y publicación es
idempotente para los mismos datos; un conflicto no sobrescribe datos existentes.
Si tienes un GTIN verificado, añade `--gtin` seguido del identificador numérico
de 8, 12, 13 o 14 dígitos.
Para otra ubicación local, antepone `--db RUTA.sqlite3` a cualquier subcomando.
Solo se aceptan archivos SQLite locales. El CLI devuelve código 0 si la
operación o extracción termina correctamente, 1 si la extracción fue parcial o
falló y 2 ante validaciones o errores de inicio. `observations` y `runs` consultan
el historial local.

La extracción solo consulta las URLs conocidas registradas, previa comprobación
de `robots.txt`; requiere que la página pública exponga un único producto y
oferta JSON-LD reconocibles. Los fixtures de las pruebas son sintéticos, no
productos ni cotizaciones de mercado. No se ha ejecutado una extracción real;
todavía se necesitan URLs reales que proporcione el usuario y confirmar los
términos de Frávega antes de automatizar consultas recurrentes.

### Incorporar una segunda tienda

1. Confirmar fuente pública, términos vigentes y `robots.txt`; definir rutas
   permitidas y límites de frecuencia. No reutilizar rutas internas de búsqueda
   ni endpoints privados.
2. Crear un adaptador bajo `backend/app/extractors/` que implemente `supports`,
   `prepare` (fallo cerrado al comprobar reglas) y `extract` para URLs de
   publicaciones existentes.
3. Normalizar exclusivamente los campos observados en `ProductSnapshot` y
   agregar el adaptador al registro de `backend/app/extractors/__init__.py`.
4. Probar parsing, bloqueos, respuestas malformadas e idempotencia con fixtures
   sintéticos. No guardar esos fixtures como datos operativos.
5. Ejecutar el CLI solo contra una base local y validar el origen antes de
   habilitar cualquier ejecución recurrente.

La disponibilidad de una página pública y su autorización en `robots.txt` no
equivalen a una garantía contractual de uso automatizado. Antes de programar
extracciones recurrentes en producción, revisar los términos vigentes de
Frávega y obtener autorización si corresponde.

`backend/app/services/ingestion.py` conserva las primitivas source-neutral de
normalización y persistencia. La lectura de páginas por tienda vive en
`backend/app/extractors/`; por ahora Frávega es el único adaptador. No se ha
validado una ejecución contra una base con tiendas y publicaciones reales.

## Carrefour Argentina

- Confirmar una fuente pública y estable y sus términos de uso/robots antes de
  implementar captura. No automatizar acceso que evada controles.
- Confirmar identificador externo estable, URL canónica, moneda, precio regular,
  promoción y señal de disponibilidad.
- Definir límites de frecuencia, reintentos y evidencia de fecha/hora de captura.
- Probar el parser solo con fixtures sintéticos claramente identificados, sin
  presentar sus valores como precios vigentes.

## Frávega: trabajo pendiente antes de activación recurrente

- El MVP solo lee páginas `/p/` ya registradas y un único `Offer` JSON-LD; no
  descubre productos ni interpreta cuotas como precio contado.
- Confirmar los términos vigentes y condiciones de uso automatizado antes de
  una ejecución recurrente en producción.
- Comparar el SKU, GTIN, disponibilidad y precio del JSON-LD con páginas
  autorizadas de la tienda antes de activar una ingestión operativa.
- Mantener las pruebas de parsing y bloqueo con fixtures sintéticos.

## BCRA (cotización oficial)

- Identificar el endpoint oficial vigente, campos, unidades y frecuencia.
- Confirmar si la respuesta ofrece una tasa de referencia o compra/venta; persistir
  `rate_side=reference` para una única tasa o `buy`/`sell` cuando estén presentes.
- Documentar cómo seleccionar la última observación no posterior a la fecha de
  comparación y cómo representar días sin publicación.

## Ámbito Financiero (cotización blue candidata)

- Verificar accesibilidad automatizada, estabilidad, atribución y condiciones de
  reutilización antes de construir un adaptador.
- Confirmar si se publican compra y venta y registrar cada lado como observación
  separada. Si el proveedor no es accesible/estable, dejarlo deshabilitado y
  proponer otra fuente documentada.

## Requisitos comunes antes de activar un proveedor

- Guardar fuente, hora con zona, ejecución (`ExtractionRun`) y resultado por lote.
- Validar moneda y decimales antes de persistir; nunca convertir a `float`.
- Hacer idempotentes los reintentos mediante claves de unicidad acordes a la
  fuente y conservar cada observación histórica.
- Añadir pruebas de parser y de fallos con fixtures sintéticos; separar esos
  fixtures de cualquier dato operativo.
- Ejecutar integración PostgreSQL aislada antes de desplegar cambios de esquema.
