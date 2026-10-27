
# PriceScope — Plan de trabajo del MVP

## 1. Objetivo

Construir una versión mínima funcional de PriceScope que permita
registrar fuentes y productos, conservar observaciones históricas
de precios y consultar la información mediante una API.

Las funcionalidades finales deben ajustarse al alcance acordado
por el equipo y a los criterios de evaluación del proyecto.

## 2. Principios de planificación

- Cada tarea debe tener un responsable.
- Cada tarea debe estar registrada en GitHub Issues.
- Cada Issue debe incluir criterios de aceptación.
- Los cambios de código deben relacionarse con su Issue.
- El trabajo debe integrarse mediante pull requests revisables.
- Las funcionalidades no implementadas deben permanecer como pendientes.

## 3. Semana 1 — Fundamentos

Objetivo: preparar el proyecto y acordar sus contratos técnicos.

Resultados previstos:
- Alcance del MVP aprobado.
- Flujo Git acordado.
- Entorno de desarrollo documentado.
- Configuración segura de Neon.
- Estructura inicial del backend.
- Modelo de datos revisado.
- Primera migración de base de datos.
- Endpoint de salud y pruebas iniciales.

Criterio de salida:
Un integrante del equipo debe poder preparar el entorno siguiendo
la documentación y ejecutar las comprobaciones iniciales.

## 4. Semana 2 — Datos y API

Objetivo: implementar el flujo básico de consulta y almacenamiento.

Resultados previstos:
- Modelos y migraciones acordados.
- Endpoints para las entidades prioritarias.
- Validación de entradas y respuestas.
- Pruebas de servicios y persistencia.
- Contrato de API documentado para frontend.

Criterio de salida:
Los flujos prioritarios pueden probarse y sus resultados
se verifican en la base de datos o mediante la API.

## 5. Semana 3 — Flujo funcional del MVP

Objetivo: conectar las piezas esenciales del producto.

Resultados previstos:
- Primera fuente de precios, si está incluida en el alcance.
- Normalización y registro de observaciones.
- Consulta de historial.
- Indicadores prioritarios acordados.
- Integración con el frontend disponible.

Criterio de salida:
Se puede demostrar el recorrido principal de datos con un conjunto
de prueba conocido y resultados verificables.

## 6. Semana 4 — Estabilización y demostración

Objetivo: reducir riesgos antes de la entrega.

Resultados previstos:
- Pruebas de regresión.
- Corrección de errores prioritarios.
- Validación de configuración y secretos.
- Instrucciones de instalación actualizadas.
- Datos de demostración identificados.
- Preparación de la exposición.
- Revisión de limitaciones conocidas.

Criterio de salida:
El equipo puede reproducir la demostración y explicar las
limitaciones reales del producto.

## 7. Gestión del trabajo

GitHub Issues será la fuente oficial de tareas.

Estados propuestos:
- Backlog
- Ready
- In progress
- In review
- Done
- Blocked

Cada tarea debe tener:
- Identificador.
- Objetivo y contexto.
- Alcance.
- Dependencias.
- Criterios de aceptación.
- Pasos de prueba.
- Responsable.
- Pull request relacionado, cuando corresponda.

## 8. Riesgos y dependencias

- Cambios de contrato entre frontend y backend.
- Disponibilidad y restricciones de las fuentes de precios.
- Errores al relacionar productos equivalentes.
- Datos incompletos o monedas no reconocidas.
- Límites de conexión o configuración de Neon.
- Cambios sin revisión que rompan funcionalidades existentes.

## 9. Seguimiento

El plan se actualiza cuando cambia el alcance o el orden de trabajo.
Los cambios importantes deben reflejarse también en los Issues
afectados y, cuando corresponda, en las decisiones técnicas.
