
#!/usr/bin/env bash
set -euo pipefail

REPO="No-Country-simulation/S10-26-equipo-14"
LABEL="backend"

gh auth status
gh repo view "$REPO" >/dev/null


create_issue() {
  local id="$1"
  local title="$2"
  local body
  local existing

  body="$(cat)"

  existing="$(
    gh issue list --repo "$REPO" --state all --limit 1000 \
      --json number,title \
      --jq "map(select(.title | startswith(\"[$id]\"))) | .[0].number // empty"
  )"

  if [[ -n "$existing" ]]; then
    echo "ACTUALIZANDO $id -> issue #$existing"
    gh issue edit "$existing" --repo "$REPO" \
      --title "[$id] $title" \
      --body "$body" \
      --add-label "$LABEL"
  else
    echo "CREANDO $id"
    gh issue create --repo "$REPO" \
      --title "[$id] $title" \
      --body "$body" \
      --label "$LABEL"
  fi
}


# =========================================================
# SEMANA 1 — FUNDAMENTOS
# =========================================================

create_issue PS-001 "Fijar alcance técnico del MVP" <<'BODY'
## Objetivo
Construir un MVP de PriceScope para Argentina que registre precios históricos y permita compararlos con cotizaciones cambiarias.

## Decisiones ya tomadas
- Mercado inicial: Argentina.
- Monedas: ARS como moneda local y USD como moneda de comparación.
- Fuentes de precios iniciales: Carrefour Argentina y Frávega.
- Cotización oficial: API del BCRA.
- Cotización blue: Ámbito Financiero como fuente inicial candidata.
- Backend: Python + FastAPI.
- Base de datos: PostgreSQL en Neon.
- Arquitectura: aplicación modular, no microservicios.

## Alcance del MVP
- Registro e inicio de sesión.
- Catálogo de tiendas y productos.
- Historial de precios.
- Historial de cotizaciones.
- Comparación de precios y variaciones.
- Dashboard y alertas básicas.
- Extracción limitada a una selección de productos.

## Criterios de aceptación
- [ ] El alcance está documentado.
- [ ] Se distingue lo imprescindible de lo posterior.
- [ ] El equipo puede desarrollar sin esperar nuevas decisiones de alcance.
BODY

create_issue PS-002 "Preparar entorno Python y dependencias" <<'BODY'
## Objetivo
Conseguir que el backend pueda ejecutarse localmente desde VS Code.

## Alcance
- Definir una versión compatible de Python.
- Preparar y activar `.venv`.
- Preparar las dependencias del backend.
- Documentar instalación y ejecución.
- Ignorar `.venv/`, `__pycache__/` y `.env` en Git.

## Criterios de aceptación
- [ ] El entorno virtual se crea siguiendo instrucciones documentadas.
- [ ] Las dependencias se pueden instalar de forma reproducible.
- [ ] `.env` y credenciales no se versionan.
- [ ] El archivo de dependencias está actualizado.
BODY

create_issue PS-003 "Conectar de forma segura con Neon PostgreSQL" <<'BODY'
## Objetivo
Permitir que Python se conecte a la base de datos de desarrollo alojada en Neon.

## Alcance
- Leer la URL desde una variable de entorno.
- Crear `.env.example` con valores ficticios.
- Utilizar SSL según la configuración recomendada por Neon.
- Implementar una comprobación de conexión sin imprimir secretos.

## Criterios de aceptación
- [ ] La conexión funciona desde el entorno local.
- [ ] La configuración no tiene credenciales codificadas en el código.
- [ ] `.env` está ignorado por Git.
- [ ] Los logs no muestran la URL completa ni la contraseña.
- [ ] Se documenta cómo configurar la conexión.
BODY

create_issue PS-004 "Crear aplicación FastAPI y endpoint de salud" <<'BODY'
## Objetivo
Tener una API mínima que pueda arrancar y comprobarse antes de desarrollar los módulos de negocio.

## Alcance
- Crear el punto de entrada FastAPI.
- Implementar `GET /health`.
- Habilitar documentación OpenAPI durante el desarrollo.
- Separar configuración y aplicación de forma sencilla.

## Criterios de aceptación
- [ ] La aplicación arranca siguiendo las instrucciones del repositorio.
- [ ] `GET /health` devuelve HTTP 200 y JSON.
- [ ] `/docs` permite inspeccionar la API.
- [ ] El endpoint de salud no depende de la base de datos.
BODY

create_issue PS-005 "Configurar SQLAlchemy, Alembic y modelo Store" <<'BODY'
## Objetivo
Preparar el ORM y las migraciones, e implementar la primera tabla de tiendas.

## Alcance
- Configurar SQLAlchemy y Alembic.
- Crear el modelo `Store`.
- Campos iniciales: id, name, base_url, country, is_active y created_at.
- Crear una migración inicial revisable.

## Criterios de aceptación
- [ ] Alembic detecta los metadatos del modelo.
- [ ] La migración crea la tabla en Neon.
- [ ] Los campos obligatorios tienen restricciones.
- [ ] La URL de conexión procede del entorno.
- [ ] Se documenta cómo aplicar y revisar migraciones.
BODY

create_issue PS-006 "Crear modelos Category y Product" <<'BODY'
## Objetivo
Representar categorías y productos normalizados para el catálogo de PriceScope.

## Alcance
- Crear `Category`.
- Crear `Product` como producto canónico.
- Incluir nombre, marca, modelo y código de barras cuando estén disponibles.
- Usar restricciones y tipos de datos adecuados.

## Criterios de aceptación
- [ ] Los modelos están integrados con SQLAlchemy.
- [ ] Las migraciones crean las tablas.
- [ ] Los campos obligatorios están validados.
- [ ] La documentación del modelo y del diccionario de datos está actualizada.

## Nota
No asumir que dos productos son idénticos solamente porque sus nombres se parecen.
BODY

create_issue PS-007 "Crear modelo StoreProduct y relaciones del catálogo" <<'BODY'
## Objetivo
Relacionar una publicación específica de una tienda con el producto normalizado.

## Alcance
- Crear `StoreProduct`.
- Relacionarlo con Store y Category.
- Relación opcional con Product canónico.
- Guardar external_id, product_url y product_name.
- Definir unicidad por tienda e identificador externo cuando esté disponible.

## Criterios de aceptación
- [ ] Las claves foráneas están definidas.
- [ ] La migración se aplica correctamente.
- [ ] Se evita duplicar una publicación identificada por la misma tienda y external_id.
- [ ] Las relaciones están documentadas y probadas.
BODY

# =========================================================
# SEMANA 2 — DATOS, API Y AUTENTICACIÓN
# =========================================================

create_issue PS-008 "Crear historial de precios PriceObservation" <<'BODY'
## Objetivo
Guardar observaciones históricas sin sobrescribir precios anteriores.

## Alcance
- Relación con StoreProduct.
- Precio decimal, moneda ISO y fecha/hora de observación.
- Registrar URL de origen cuando corresponda.
- Definir campos para disponibilidad y precio promocional si la fuente los permite.

## Criterios de aceptación
- [ ] Se pueden guardar múltiples observaciones del mismo producto.
- [ ] Los precios utilizan NUMERIC/Decimal, no float.
- [ ] Las fechas incluyen zona horaria o se almacenan en UTC.
- [ ] La migración se aplica correctamente.
- [ ] Se prueba que un nuevo precio no elimina el histórico.
BODY

create_issue PS-009 "Crear modelo ExchangeRate y guardar cotizaciones" <<'BODY'
## Objetivo
Guardar cotizaciones oficiales y blue con trazabilidad temporal.

## Alcance
- Crear modelo ExchangeRate.
- Campos: moneda base, moneda cotizada, tipo de tasa, valor, fuente y fecha/hora.
- Monedas iniciales: ARS y USD.
- Tipos iniciales: official y blue.
- Conservar compra y venta si la fuente proporciona ambas.

## Criterios de aceptación
- [ ] Las cotizaciones tienen fuente y fecha.
- [ ] Las tasas no se mezclan entre tipos official y blue.
- [ ] Los valores usan Decimal/NUMERIC.
- [ ] Se pueden consultar cotizaciones históricas.
- [ ] Se documenta cómo se elige una tasa para una fecha de observación.
BODY

create_issue PS-010 "Crear esquemas Pydantic para la API" <<'BODY'
## Objetivo
Validar datos de entrada y definir respuestas consistentes.

## Alcance
- Esquemas para tiendas, categorías, productos, publicaciones y precios.
- Esquemas para cotizaciones.
- Separar entradas de creación y respuestas cuando corresponda.
- Validar campos requeridos, fechas, monedas y números.

## Criterios de aceptación
- [ ] Los datos inválidos producen errores claros.
- [ ] Los precios no se convierten a float para almacenarse.
- [ ] Los esquemas no exponen campos internos innecesarios.
- [ ] Existen pruebas de entradas válidas e inválidas.
BODY

create_issue PS-011 "Implementar endpoints de consulta del catálogo" <<'BODY'
## Objetivo
Permitir consultar tiendas, categorías y productos desde la API.

## Alcance
- GET /stores
- GET /categories
- GET /products
- GET /products/{id}
- Añadir paginación básica donde corresponda.
- Usar SQLAlchemy y los esquemas Pydantic.

## Criterios de aceptación
- [ ] Las rutas aparecen en OpenAPI.
- [ ] Los resultados proceden de PostgreSQL.
- [ ] Los IDs inexistentes producen respuestas adecuadas.
- [ ] Se validan los parámetros de consulta.
- [ ] Se documenta un ejemplo de petición y respuesta.
BODY

create_issue PS-012 "Implementar endpoints de precios y cotizaciones" <<'BODY'
## Objetivo
Registrar y consultar el historial de precios y tipos de cambio.

## Alcance
- Endpoint para registrar una observación de precio.
- Endpoint para consultar observaciones por producto.
- Endpoint para consultar cotizaciones por tipo y rango de fechas.
- Validar moneda, fecha y valor.
- No inventar valores cuando falten datos.

## Criterios de aceptación
- [ ] Las observaciones se guardan en PostgreSQL.
- [ ] Se preserva el histórico.
- [ ] Se pueden filtrar cotizaciones por tipo y fechas.
- [ ] Los errores de validación tienen respuestas claras.
- [ ] Los endpoints están documentados en OpenAPI.
BODY

create_issue PS-013 "Implementar usuarios y migración de autenticación" <<'BODY'
## Objetivo
Preparar el almacenamiento seguro de cuentas para incluir login y register en el MVP.

## Alcance
- Crear tabla User.
- Email normalizado y único.
- Contraseña almacenada únicamente como hash seguro.
- Fecha de creación y estado de cuenta.
- Usar una biblioteca mantenida para hashing; nunca implementar criptografía propia.

## Criterios de aceptación
- [ ] La tabla tiene restricción de unicidad para email.
- [ ] No se almacena contraseña en texto plano.
- [ ] La migración se puede aplicar y revisar.
- [ ] Los modelos no devuelven el hash de contraseña en respuestas públicas.
BODY

create_issue PS-014 "Implementar register, login y usuario actual con JWT" <<'BODY'
## Objetivo
Permitir crear una cuenta e iniciar sesión de forma segura.

## Alcance
- POST /auth/register
- POST /auth/login
- GET /auth/me
- Hash seguro de contraseñas.
- JWT de acceso con expiración.
- Secretos de JWT en variables de entorno.
- Mensajes de error que no revelen si una contraseña es correcta.

## Criterios de aceptación
- [ ] Un usuario puede registrarse.
- [ ] No se permiten emails duplicados.
- [ ] El login devuelve un token válido.
- [ ] Un token expirado o inválido se rechaza.
- [ ] `/auth/me` devuelve el usuario autenticado sin datos sensibles.
- [ ] Se prueban credenciales correctas e incorrectas.

## Fuera de alcance
OAuth, recuperación de contraseña y verificación de email.
BODY

create_issue PS-015 "Proteger endpoints privados y documentar CORS" <<'BODY'
## Objetivo
Aplicar autenticación a las operaciones privadas y preparar la comunicación con el frontend existente.

## Alcance
- Definir qué endpoints son públicos y cuáles requieren JWT.
- Proteger endpoints de usuario y futuras alertas personales.
- Configurar CORS con los orígenes de desarrollo necesarios.
- Leer los orígenes permitidos desde configuración.

## Criterios de aceptación
- [ ] Los endpoints privados rechazan solicitudes sin token válido.
- [ ] Los endpoints públicos siguen accesibles.
- [ ] CORS no utiliza comodines inseguros con credenciales.
- [ ] Los orígenes del frontend se documentan.
- [ ] Existen pruebas de acceso autorizado y no autorizado.
BODY

# =========================================================
# SEMANA 3 — FUENTES, INDICADORES E INTEGRACIÓN
# =========================================================

create_issue PS-016 "Implementar cliente de cotización oficial del BCRA" <<'BODY'
## Objetivo
Importar cotizaciones oficiales desde la API pública del BCRA.

## Fuente
https://www.bcra.gob.ar/apis-banco-central/

## Alcance
- Crear un módulo de integración separado.
- Consultar la API documentada.
- Normalizar la respuesta y validar los campos.
- Guardar cotizaciones con fecha y fuente.
- Gestionar timeouts, errores HTTP y respuestas inesperadas.

## Criterios de aceptación
- [ ] Se obtiene y valida una respuesta de la API.
- [ ] Los datos se guardan como ExchangeRate.
- [ ] Una falla externa no derriba toda la API.
- [ ] Los logs registran errores sin secretos.
- [ ] Se puede probar el procesamiento con una respuesta de ejemplo.
BODY

create_issue PS-017 "Implementar captura de cotización blue" <<'BODY'
## Objetivo
Registrar la cotización blue con procedencia y fecha verificables.

## Fuente inicial candidata
https://www.ambito.com/contenidos/dolar.html

## Alcance
- Revisar la estructura y las condiciones de uso de la fuente.
- Implementar extracción solo si es técnicamente estable y permitida.
- Guardar fuente, tipo de tasa y timestamp de captura.
- Si no existe acceso estable, usar un proveedor alternativo documentado.
- No confundir tasa oficial, blue, MEP y CCL.

## Criterios de aceptación
- [ ] Se distingue la tasa blue de la oficial.
- [ ] Se guarda el timestamp real de captura.
- [ ] Se valida que la tasa extraída sea numérica y positiva.
- [ ] Se documentan limitaciones y fallback.
- [ ] No se publican valores inventados como si fueran datos actuales.
BODY

create_issue PS-018 "Crear interfaz común para extractores de precios" <<'BODY'
## Objetivo
Evitar que el código de cada tienda quede mezclado con la lógica de persistencia.

## Alcance
- Definir una interfaz común para extractores.
- Normalizar los campos mínimos: tienda, URL, nombre, precio, moneda, disponibilidad y fecha.
- Separar extracción, normalización y almacenamiento.
- Registrar errores por producto sin perder el resto de la ejecución.

## Criterios de aceptación
- [ ] Los dos extractores pueden utilizar la misma estructura de salida.
- [ ] La lógica de base de datos no está duplicada por tienda.
- [ ] Los datos incompletos se rechazan o marcan explícitamente.
- [ ] Hay pruebas con HTML o respuestas guardadas como fixtures.
BODY

create_issue PS-019 "Crear extractor inicial de Carrefour Argentina" <<'BODY'
## Objetivo
Capturar una selección controlada de precios de productos de supermercado.

## Fuente
https://www.carrefour.com.ar/

## Alcance
- Trabajar con una lista pequeña de URLs de productos.
- Capturar nombre, precio, disponibilidad y URL.
- Identificar si el precio es promocional cuando sea posible.
- Respetar límites razonables de solicitudes y las condiciones del sitio.
- No intentar recorrer todo el catálogo.

## Criterios de aceptación
- [ ] El extractor procesa productos de prueba reproducibles.
- [ ] Los precios se normalizan a Decimal y ARS cuando la página lo confirme.
- [ ] Los errores de una URL no detienen todos los productos.
- [ ] Se registra la fecha de captura.
- [ ] Se documentan los productos y las limitaciones de la fuente.
BODY

create_issue PS-020 "Crear extractor inicial de Frávega" <<'BODY'
## Objetivo
Capturar una selección controlada de bienes durables o tecnología.

## Fuente
https://www.fravega.com/

## Alcance
- Trabajar con una lista pequeña de URLs seleccionadas.
- Capturar nombre, precio, disponibilidad y URL.
- Normalizar la moneda.
- Evitar técnicas para evadir controles de acceso.
- Mantener el extractor separado del de Carrefour.

## Criterios de aceptación
- [ ] El extractor procesa productos de prueba reproducibles.
- [ ] Los precios y monedas se validan.
- [ ] Se registra la fecha de captura.
- [ ] Los errores se documentan sin detener el resto del proceso.
- [ ] La documentación explica cómo añadir o desactivar URLs.
BODY

create_issue PS-021 "Implementar ejecución y registro de capturas" <<'BODY'
## Objetivo
Ejecutar los extractores de manera controlada y guardar el resultado de cada ejecución.

## Alcance
- Crear entidad ExtractionRun o equivalente.
- Guardar inicio, fin, fuente, estado y contadores.
- Ejecutar los extractores manualmente mediante un comando.
- Evitar duplicar observaciones idénticas por una misma captura.
- No depender todavía de un servicio de scheduling externo.

## Criterios de aceptación
- [ ] Existe un comando documentado para ejecutar una captura.
- [ ] Cada ejecución deja un registro.
- [ ] Los errores se reflejan en el estado y los logs.
- [ ] Las observaciones históricas no se sobrescriben.
- [ ] Se puede repetir una ejecución de prueba.
BODY

create_issue PS-022 "Calcular variaciones de precios y brecha cambiaria" <<'BODY'
## Objetivo
Producir indicadores básicos a partir de datos históricos verificables.

## Alcance
- Variación porcentual de precio entre dos observaciones.
- Variación de precio en un intervalo definido.
- Brecha porcentual entre cotización blue y oficial.
- Equivalencia aproximada de precios ARS a USD indicando la tasa utilizada.
- Excluir o marcar periodos sin datos suficientes.

## Criterios de aceptación
- [ ] Las fórmulas están documentadas.
- [ ] Los cálculos usan Decimal cuando corresponda.
- [ ] Cada resultado identifica el periodo y la tasa usada.
- [ ] No se etiqueta una variación corta como inflación oficial.
- [ ] Existen pruebas con valores conocidos.
BODY

create_issue PS-023 "Implementar alertas básicas de variación de precio" <<'BODY'
## Objetivo
Permitir configurar umbrales y detectar cambios de precio relevantes.

## Alcance
- Crear modelo Alert.
- Relacionar alerta con usuario y producto cuando aplique.
- Permitir un umbral porcentual.
- Detectar cuándo una nueva observación supera el umbral.
- Guardar historial de activaciones o eventos.

## Criterios de aceptación
- [ ] Se puede crear y consultar una alerta.
- [ ] Las alertas de usuarios no son visibles para otros usuarios.
- [ ] El cálculo utiliza observaciones históricas válidas.
- [ ] Se prueba un caso que dispara una alerta y otro que no.
- [ ] Las notificaciones por email quedan fuera del MVP.
BODY

create_issue PS-024 "Integrar contratos de API con el frontend existente" <<'BODY'
## Objetivo
Asegurar que el frontend existente pueda consumir los endpoints del backend.

## Alcance
- Documentar URLs, métodos, parámetros y respuestas.
- Documentar login, register y uso del token.
- Verificar CORS con el origen real del frontend.
- Proporcionar ejemplos de errores de validación.
- No reemplazar ni duplicar la carpeta frontend.

## Criterios de aceptación
- [ ] El frontend puede registrarse e iniciar sesión contra el backend.
- [ ] Puede consultar productos e historial de precios.
- [ ] Los errores se muestran con respuestas coherentes.
- [ ] Se documenta la configuración local de ambos proyectos.
- [ ] Los cambios de contrato quedan reflejados en OpenAPI.
BODY

create_issue PS-025 "Pruebas integrales y guía de ejecución del MVP" <<'BODY'
## Objetivo
Dejar un circuito demostrable y reproducible antes de la semana de estabilización.

## Alcance
- Pruebas de salud, persistencia, catálogo, precios y autenticación.
- Probar la importación de cotizaciones.
- Probar el procesamiento de al menos una captura de precios.
- Preparar datos de demostración sin secretos.
- Documentar cómo iniciar backend, configurar Neon, aplicar migraciones y ejecutar pruebas.

## Criterios de aceptación
- [ ] Las pruebas críticas pasan o sus fallos están documentados.
- [ ] Una persona puede seguir la guía desde un entorno limpio.
- [ ] Se documentan los endpoints disponibles.
- [ ] Se documentan las limitaciones de los extractores.
- [ ] No hay credenciales reales en el repositorio.
- [ ] Existe una lista priorizada de errores pendientes para la semana 4.
BODY

echo
echo "Proceso terminado."
echo "Issues: https://github.com/$REPO/issues"
