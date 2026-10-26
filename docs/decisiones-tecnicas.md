
# PriceScope — Decisiones técnicas

## Estado del documento

Documento inicial. Las decisiones marcadas como propuestas o
pendientes no se consideran aprobadas hasta que el equipo las confirme.

## DT-001 — Lenguaje del backend

**Estado:** Propuesto.

**Decisión propuesta:** utilizar Python.

**Motivo:** facilita trabajar con extracción de datos, procesamiento,
normalización y análisis.

**Alternativas:** Java u otro lenguaje, si el equipo demuestra
una necesidad concreta de cambiar el stack.

**Consecuencia:** el equipo debe acordar una versión de Python
y un procedimiento común de instalación.

## DT-002 — API HTTP

**Estado:** Propuesto.

**Decisión propuesta:** utilizar FastAPI.

**Motivo:** permite construir endpoints HTTP y validar datos
mediante modelos tipados.

**Consecuencia:** deben acordarse las rutas y los contratos de datos
que consumirá el frontend.

## DT-003 — Base de datos

**Estado:** Propuesto.

**Decisión propuesta:** PostgreSQL en Neon.

**Motivo:** permite mantener relaciones entre entidades, restricciones
de integridad e historial de observaciones.

**Consecuencia:** las credenciales deben mantenerse fuera del
repositorio y las modificaciones del esquema deben versionarse.

## DT-004 — Acceso a datos y migraciones

**Estado:** Propuesto.

**Decisión propuesta:** SQLAlchemy para el acceso a datos y Alembic
para las migraciones.

**Motivo:** separar los modelos de aplicación del historial de
cambios de la estructura de la base de datos.

**Consecuencia:** los cambios de esquema deben revisarse y probarse
antes de integrarlos.

## DT-005 — Historial de precios

**Estado:** Principio propuesto.

**Decisión:** registrar observaciones nuevas en vez de reemplazar
el precio anterior.

**Motivo:** el objetivo del producto incluye analizar variaciones
a través del tiempo.

**Consecuencia:** deben definirse reglas para observaciones duplicadas,
reintentos y fechas de captura.

## DT-006 — Gestión de secretos

**Estado:** Requisito de seguridad.

**Decisión:** no guardar contraseñas, tokens ni la URL privada de
conexión de Neon en archivos versionados.

**Implementación propuesta:**
- Utilizar un archivo .env local ignorado por Git.
- Mantener .env.example con nombres de variables y valores ficticios.
- Configurar los secretos necesarios en los entornos de despliegue.

## DT-007 — Flujo Git

**Estado:** Pendiente de acuerdo del equipo.

**Propuesta:**
- main: versión estable.
- develop: integración del trabajo.
- feature/PS-XXX-descripcion: cambios asociados a un Issue.
- Pull request para revisar y probar antes de integrar.

No se deben subir credenciales ni integrar cambios sin revisión
cuando estos puedan afectar a otros módulos.

## DT-008 — Comparación entre monedas

**Estado:** Pendiente.

Antes de calcular precios comparables se debe definir:
- La moneda objetivo.
- La fuente del tipo de cambio.
- La fecha de cotización aplicable.
- El tratamiento de cotizaciones faltantes.
- Si se guarda el valor convertido o se calcula al consultar.

## DT-009 — Identificación de productos equivalentes

**Estado:** Pendiente.

Se debe decidir cómo identificar productos iguales entre tiendas,
qué atributos se consideran y cómo se revisan coincidencias dudosas.

No se deben comparar productos automáticamente solo porque
sus nombres se parezcan.

## Cómo registrar una nueva decisión

Cada decisión debe incluir:
- Identificador.
- Estado.
- Contexto o problema.
- Decisión elegida.
- Alternativas consideradas.
- Motivo.
- Consecuencias.
- Fecha y responsable, cuando se apruebe.
