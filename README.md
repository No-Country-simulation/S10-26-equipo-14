# PriceScope

**Monitor de Inflación Real Multimoneda**

PriceScope es una plataforma de analítica económica que busca automatizar la recolección, el seguimiento y el análisis histórico de precios de productos en diferentes tiendas de comercio electrónico, relacionándolos con la evolución de las cotizaciones cambiarias.

## Problema

La recopilación manual de precios y su conversión a distintas monedas genera retrasos, errores y dificultades para identificar variaciones reales del mercado, promociones temporales y cambios en las presentaciones de los productos.

## Objetivo

Desarrollar una plataforma que permita monitorear precios, comparar productos equivalentes entre tiendas y analizar la inflación en moneda local y extranjera mediante indicadores y visualizaciones interactivas.

## Funcionalidades previstas

- Recolección automatizada de precios de tiendas de comercio electrónico.
- Normalización y asociación de productos equivalentes.
- Detección y seguimiento de promociones y disponibilidad.
- Integración de cotizaciones cambiarias con marcas de tiempo.
- Almacenamiento histórico de precios y tipos de cambio.
- Cálculo de inflación acumulada y variaciones porcentuales.
- Comparación de precios entre tiendas y categorías.
- Dashboard analítico y sistema de alertas.

## Arquitectura propuesta

- **Extracción de datos:** Python, Playwright o BeautifulSoup.
- **Backend:** por definir con el equipo.
- **Base de datos:** PostgreSQL.
- **Frontend:** React + TypeScript + Vite + Tailwind CSS (carpeta `frontend/`).
- **Procesamiento y programación:** tareas automatizadas.
- **Visualización:** gráficos e indicadores interactivos.

Las tecnologías definitivas y la distribución de responsabilidades se acordarán con el equipo.

## Alcance inicial

La primera versión buscará validar el flujo completo con 2 o 3 tiendas, un conjunto limitado de productos y una fuente de cotizaciones cambiarias. Posteriormente se podrá ampliar la cobertura y automatización.

## Equipo

NoCountry — Simulación laboral S10-26, Equipo 14.

## Estado del proyecto

Fase inicial: preparación del repositorio, definición de arquitectura y planificación del MVP.
