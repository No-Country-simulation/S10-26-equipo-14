# Backend público de solo lectura

## Política

El backend acepta `APP_ENV=development`, `APP_ENV=test` o `APP_ENV=production`.
Si no se configura el entorno, el valor predeterminado es `production`. `PUBLIC_READ_ONLY`
por defecto es `true`.

Un método HTTP `POST`, `PUT`, `PATCH` o `DELETE` dirigido a `/api/` se rechaza con
HTTP 403 antes de entrar al router, salvo cuando se cumplen ambas condiciones:

- `APP_ENV=development`
- `PUBLIC_READ_ONLY=false`

La producción y el entorno `test` permanecen bloqueados aunque
`PUBLIC_READ_ONLY=false`. Los tests que necesitan escrituras deben crear una app
aislada con configuración de desarrollo y una base de pruebas.

## Desarrollo local

Para habilitar temporalmente las operaciones locales, configura en el entorno
del backend (o en el `.env` local, que no debe versionarse):

```dotenv
APP_ENV=development
PUBLIC_READ_ONLY=false
```

Para volver al modo seguro, usa `PUBLIC_READ_ONLY=true` o elimina ambas
variables; sin configuración, la API inicia en producción y solo lectura.

## Producción / Render

Configura explícitamente:

```dotenv
APP_ENV=production
PUBLIC_READ_ONLY=true
```

`PUBLIC_READ_ONLY=false` no habilita escrituras si `APP_ENV=production`. En
Render también se mantienen las variables ya necesarias para la aplicación,
como `DATABASE_URL` y `CORS_ORIGINS`; no incluyas sus valores en el repositorio.

## Rutas y exposición

Las consultas GET del catálogo, tiendas, productos, observaciones, cotizaciones
y gestión continúan disponibles. El frontend usa `/api/v1/management/stores` en
Inicio y Tiendas, y `/api/v1/management/stores/{store_id}/extractions` en el
historial. En entornos no locales, la clave interna del analizador y mensajes de
error se omiten; el historial conserva su esquema, pero devuelve `source` como
`"Extracción"` y `error_summary` como `null`. Los metadatos de estado y los
candidatos de navegación pública se mantienen para no romper esa interfaz.

`GET /api/v1/store-products` se considera privado en producción: incluye IDs
externos y URLs de cada publicación y el frontend no lo consume. En desarrollo
sigue disponible para compatibilidad local.

Las rutas mutadoras cubiertas por el bloqueo central son:

- `POST /api/v1/store-products`
- `POST /api/v1/price-observations`
- `POST /api/v1/management/stores`
- `POST /api/v1/management/stores/{store_id}/analyze`
- `POST /api/v1/management/stores/{store_id}/extract`
- `PUT /api/v1/management/stores/{store_id}/monitoring`

No hay rutas HTTP `PATCH` ni `DELETE` registradas actualmente. Los comandos
locales de extracción no son rutas HTTP y deben ejecutarse solo como tarea
operativa local revisada; no forman parte del servicio web público.

## CORS no es autorización

CORS regula qué páginas web pueden leer respuestas desde un navegador. No
autentica usuarios ni impide llamadas directas con clientes HTTP. El middleware
de solo lectura del servidor es el control que rechaza las mutaciones.
