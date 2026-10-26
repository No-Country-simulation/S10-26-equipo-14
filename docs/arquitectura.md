
# PriceScope — Estructura del repositorio

## Objetivo

Explicar la responsabilidad de cada carpeta y evitar que el equipo
duplique componentes o coloque archivos en lugares incorrectos.

## Raíz del proyecto

- `README.md`: presentación del proyecto e instrucciones iniciales.
- `.gitignore`: archivos que Git no debe versionar.
- `.env.example`: ejemplo de variables necesarias, sin secretos reales.
- `backend/`: API, lógica de negocio, persistencia y pruebas del backend.
- `docs/`: arquitectura, datos, decisiones y planificación.
- `frontend/`: interfaz web existente, mantenida por su responsable.

## Backend

- `pyproject.toml`: configuración del proyecto Python y sus dependencias.
- `alembic.ini`: configuración de Alembic.
- `alembic/versions/`: historial de migraciones de base de datos.
- `app/main.py`: creación de la aplicación FastAPI.
- `app/core/`: configuración y componentes transversales.
- `app/db/`: conexión, sesiones y registro de modelos.
- `app/models/`: modelos de persistencia.
- `app/schemas/`: esquemas de entrada y salida de la API.
- `app/api/v1/`: rutas de la primera versión de la API.
- `app/services/`: lógica de negocio.
- `app/scrapers/`: extracción y adaptación de fuentes de datos.
- `app/tests/`: pruebas cercanas a los módulos de aplicación.
- `tests/`: pruebas generales o de integración.

## Convenciones

- Los modelos representan la estructura de persistencia.
- Los esquemas validan los datos de entrada y salida.
- Los servicios implementan las reglas de negocio.
- Las rutas HTTP coordinan las solicitudes y respuestas.
- Los scrapers obtienen datos de fuentes externas.
- Las migraciones registran los cambios del esquema.

## Mantenimiento

La estructura documentada debe reflejar el repositorio real.
No se crearán carpetas nuevas solo por anticipación: cada módulo
debe tener una responsabilidad definida y un uso previsto.
