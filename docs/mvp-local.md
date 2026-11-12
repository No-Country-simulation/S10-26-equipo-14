# PriceScope MVP: operación local

PriceScope conserva las cotizaciones y observaciones como registros inmutables
con fuente y fecha de observación. Las pantallas consultan la API; si la API no
está disponible, muestran el error en vez de sustituirlo por datos simulados.

## Base SQLite

Desde `backend/`, inicializa una base SQLite local:

```powershell
python -m app.commands.pricescope_local db init
```

La ruta predeterminada es `backend/.local/pricescope.sqlite3`. El comando
comprueba la forma y revisión del esquema antes de migrar; no usa `DATABASE_URL`
ni contacta Neon. Para cargar las quince tiendas objetivo sin inventar URL ni
estado de integración:

```powershell
python -m app.commands.seed_target_stores
```

Las tiendas creadas quedan en `configuration_required` hasta verificar una URL
y su compatibilidad. Una tienda existente no se sobrescribe. La extracción se
solicita desde gestión de tiendas o con `pricescope_local extract STORE_ID`;
cada intento conserva su resultado y errores. Frávega tiene un adaptador propio;
los demás sitios HTTPS públicos configurados usan el adaptador compartido, que
obedece `robots.txt`, límites de respuesta y tiempo de espera. Un estado activo
requiere análisis y configuración real; registrar una tienda no afirma que se
haya extraído exitosamente.

## Cotizaciones e indicadores

Desde `backend/`, ejecuta `python -m app.commands.ingest_exchange_rates` para
consultar BCRA (oficial) y DolarApi (paralelo). Cada fuente produce un registro
de ejecución y sus cotizaciones deduplicadas conservan proveedor, lado, par y
timestamp. Un fallo de proveedor queda registrado sin ocultar un fallo del otro.
El proceso apunta únicamente a la SQLite local ya inicializada.

La API ofrece catálogo canónico con última observación, publicaciones y su
historial, cotizaciones, series visualizadas en **Divisas**, comparativas de
productos presentes en al menos dos tiendas y alertas derivadas de dos
observaciones. La conversión solo debe compararse cuando existe una cotización
vigente para el instante correspondiente. Sin historial o una tasa alineable,
el indicador/alerta correspondiente no se fabrica. Precio promocional,
disponibilidad y precio unitario se incluyen cuando la página aporta evidencia
suficiente; no se infiere reduflación a partir de una única observación.

## Indicadores acumulados

`GET /api/v1/indicators/inflation` exige `start` y `end` con zona horaria, e
acepta `product_id`, `category_id`, `store_id` y `rate_type`. Para cada
publicación requiere dos fechas distintas dentro del período y moneda estable;
usa la primera y última observación, precio promocional cuando existe, y
promedia variaciones porcentuales equiponderadas por publicación. Presenta
grupos separados por moneda, con desglose por producto y categoría. Para ARS,
la cotización elegida (oficial o venta paralela) se calcula por separado usando
la primera y última cotización dentro del mismo período. La diferencia entre
variaciones se expresa en puntos porcentuales. Sin muestras elegibles responde
`insufficient_data`; nunca convierte monedas de precios.

`GET /api/v1/indicators/shrinkflation` compara pares consecutivos del mismo
producto canónico y publicación, dentro de los filtros temporales, de tienda,
producto y categoría. La cantidad de cada fecha se guarda en la observación
(`observed_package_quantity`, `observed_package_unit`,
`observed_package_count`); se normaliza a g, ml o unidad. Solo genera señal si
la cantidad nueva disminuye, la moneda coincide y el precio regular por unidad
normalizada aumenta. Marca `confirmed` cuando el precio total no disminuye y
`possible` cuando disminuye pero menos proporcionalmente que el contenido.
Las medidas ausentes permanecen desconocidas: no se rellenan desde la
presentación canónica actual. Se requieren medidas explícitas en ambas fechas.
La columna aditiva está en la revisión local `9c7e2a1f4b60`; actualiza la
SQLite local mediante `pricescope_local db init`.

### Activación local verificada (2026-11-12)

Se ejecutó `pricescope_local --db backend/.local/pricescope.sqlite3 db init`
desde la revisión `f41d0c2a9b73`. El cambio añadió únicamente tres columnas
nullable a `price_observations` mediante `ALTER TABLE ADD COLUMN`; no reconstruyó
la tabla ni actualizó valores existentes. Antes y después se conservaron 18
tiendas, 26 productos y 127 observaciones; la comparación de todas las filas
existentes de las tablas de mercado coincidió y `PRAGMA integrity_check` devolvió
`ok`. La base quedó en `9c7e2a1f4b60`.

La comprobación funcional contra esta SQLite devolvió HTTP 200 en inflación,
reduflación y alertas. Tras excluir la fixture sintética, el catálogo ofrece 5
productos canónicos no demo y 16 tiendas registradas no demo. Inflación acumulada: `insufficient_data`, porque
no hay dos observaciones comparables de una publicación real en el período.
Reduflación: cero señales y cero observaciones con medida histórica explícita.
Alertas: cero. El historial local registra 1 ejecución `SUCCESS`, 6 `BLOCKED`,
4 `PRICE_NOT_FOUND` y 1 `RATE_LIMITED`; no repetí intentos bloqueados. La
interfaz comunica la falta de datos y no infiere medidas. El build de producción
del frontend pasó; la inspección visual del navegador local no pudo ejecutarse
porque el host de browser/computer-use no estaba disponible. No se cargaron
datos sintéticos.

Los registros de la fixture local se reconocen por el prefijo inequívoco
`DEMO PriceScope` y se excluyen de tiendas, categorías, catálogo de productos,
observaciones predeterminadas y todos los indicadores reales. La página **Demo**
mantiene sus muestras presentadas aparte con etiqueta sintética. El historial
fixture sigue almacenado sin modificaciones.

Ambos indicadores están integrados en **Comparativas**, comparten período,
tienda y categoría, muestran moneda y fecha, y separan inflación de precios de
variación cambiaria. La pantalla indica explícitamente cuando faltan datos.

## Verificación local

```powershell
# backend
$env:DATABASE_URL = 'sqlite:///./pricescope-local.db'
$env:APP_ENV = 'test'
python -m pytest -q

# frontend
npm run test:catalog
npm run build
```

Los tests omitidos que requieren infraestructura externa no se ejecutan contra
Neon. Los comandos operativos de ingestión fijan de forma independiente la
SQLite bajo `backend/.local/`.

## Verificación de despliegue público (2026-11-12)

Las lecturas HTTP observadas devolvieron: Render `/health` `200` con `{"status":"ok"}`; Vercel `/` `200` con la shell HTML de PriceScope; Render `/ready` `200` con `{"status":"ready"}`. `/ready` confirma únicamente la comprobación de conectividad que implementa la app, no el éxito de cada consulta.

En OpenAPI de Render, el contrato publicado incluye GET de tiendas, categorías, productos (incluida paginación), publicaciones, observaciones de precio e historial por `store_product_id`, cotizaciones por `rate_type`, más `/health` y `/ready`. No publica comparativas, alertas, indicadores de inflación/reduflación ni gestión/extracciones. Respuestas observadas: tiendas `200 []`; categorías, productos paginados y publicaciones `500 Internal Server Error`; observaciones para `store_product_id=1` y cotizaciones para `rate_type=official`, `500 Internal Server Error`. Estos errores no entregan detalle de causa en la respuesta. El GET CORS desde el origen de Vercel no se pudo ejecutar porque la solicitud de permiso de red fue rechazada.

Por tanto, el frontend está servido, pero la integración funcional no queda validada: varias lecturas del API fallan y las rutas analíticas implementadas localmente no están en el contrato desplegado. No se modificó configuración, base de datos remota ni despliegue. Se necesita revisar logs de Render y el esquema/configuración de Neon para encontrar el origen de los `500`; no se infiere ni se aplica una corrección remota sin esa evidencia.

Corrección CORS local: `DEFAULT_CORS_ORIGINS` incluye exactamente `https://pricescope-14.vercel.app`; el validador conserva esa lista al leer `CORS_ORIGINS`, rechaza comodines con credenciales y CORS envuelve también respuestas del middleware de solo lectura. Se añadió una prueba GET del catálogo con ese origen; el test de preflight ya cubre POST/PUT y `content-type` para los orígenes desplegados. Suite backend: 167 passed, 5 skipped. Esta corrección aún no está desplegada, y las respuestas HTTP previas de Render no incluyeron `Access-Control-Allow-Origin`.

No hay `DATABASE_URL` en el entorno local, CLI/conector de Neon ni herramientas conectadas para leer el estado de producción o verificar un respaldo. `/ready` solo probó `SELECT 1`; otras consultas públicas dieron `500`. Por ello no se verificaron conteos ni revisiones de tablas remotas y no se ejecutó ninguna migración ni carga de datos.
