
# PriceScope — Arquitectura del sistema

## 1. Objetivo

PriceScope es una plataforma de inteligencia de mercado que busca
recopilar, organizar y analizar precios publicados en comercios
electrónicos para estudiar su evolución y comparar precios entre
productos, tiendas y monedas.

La arquitectura debe permitir conservar el historial de precios,
incorporar nuevas fuentes de datos y ofrecer información útil
mediante una API y una interfaz web.

## 2. Componentes principales

### Frontend

Responsable de presentar la información al usuario.

Funciones previstas:
- Mostrar productos y tiendas.
- Consultar la evolución histórica de precios.
- Presentar indicadores y comparaciones.
- Mostrar alertas cuando se cumplan las condiciones configuradas.

El frontend existente en el repositorio debe revisarse antes de
definir nuevas carpetas o implementar componentes duplicados.

### Backend

El backend se desarrollará con Python y FastAPI, sujeto a la
confirmación del stack acordado por el equipo.

Responsabilidades:
- Exponer endpoints HTTP.
- Validar entradas y salidas.
- Aplicar reglas de negocio.
- Consultar y modificar la base de datos.
- Coordinar la extracción y normalización de precios.
- Facilitar los datos que consume el frontend.

### Base de datos

PostgreSQL alojado en Neon será la base de datos propuesta.

Debe almacenar:
- Tiendas y categorías.
- Productos publicados por cada tienda.
- Productos comunes usados para comparar artículos equivalentes.
- Observaciones históricas de precios.
- Tipos de cambio.
- Configuraciones de alertas.

### Extracción de datos

Los componentes de scraping recopilarán información de fuentes
públicas o autorizadas de comercio electrónico.

El proceso deberá:
1. Consultar la fuente.
2. Extraer la información disponible.
3. Normalizar nombres, precios y monedas.
4. Validar los datos.
5. Guardar nuevas observaciones sin borrar el historial.

Cada fuente puede requerir un adaptador específico.

## 3. Flujo general de información

1. Un scraper obtiene los datos publicados por una tienda.
2. El backend normaliza y valida el resultado.
3. Se identifica el producto de la tienda y, cuando sea posible,
   se relaciona con un producto común del catálogo.
4. Se registra una observación de precio con su fecha y moneda.
5. Los servicios de análisis consultan el historial.
6. La API entrega los resultados al frontend.

## 4. Tecnologías propuestas

- Python: lenguaje del backend y de los procesos de extracción.
- FastAPI: API HTTP.
- PostgreSQL / Neon: almacenamiento relacional.
- SQLAlchemy: acceso a datos desde Python.
- Alembic: migraciones del esquema.
- Pydantic: validación de datos.
- Pytest: pruebas automatizadas.
- Git y GitHub: control de versiones y gestión del trabajo.

Estas tecnologías deben confirmarse con el equipo antes de
considerarlas decisiones definitivas.

## 5. Principios de diseño

- Mantener el historial de precios.
- Separar la extracción, la lógica de negocio y la API.
- Evitar duplicados mediante identificadores y restricciones.
- No almacenar secretos en el repositorio.
- Validar y probar antes de integrar cambios.
- Documentar las decisiones que afecten a otros módulos.

## 6. Aspectos pendientes

- Confirmar el stack definitivo.
- Confirmar el contrato entre frontend y backend.
- Definir cómo se asocia cada precio con el tipo de cambio aplicable.
- Definir la frecuencia y las fuentes de extracción.
- Establecer las reglas para reconocer productos equivalentes.
- Confirmar las métricas que entran en el MVP.
