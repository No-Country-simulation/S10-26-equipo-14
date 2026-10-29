# PriceScope — Guía de Épicas e Historias de Usuario Frontend

**Proyecto:** PriceScope - Monitor de Inflación Real Multimoneda  
**Contexto:** Simulación Laboral Abierta (No Country) — Equipo 14  
**Enfoque:** Orientado al Valor de Negocio y Cliente Corporativo (FinTech / Retail Analytics)

---

## Tabla de Contenidos

1. [Contexto y Objetivos del MVP](#1-contexto-y-objetivos-del-mvp)
2. [Organización del Equipo](#2-organización-del-equipo)
3. [Desglose de Épicas e Historias de Usuario](#3-desglose-de-épicas-e-historias-de-usuario)
4. [Matriz de Trabajo Semanal](#4-matriz-de-trabajo-semanal)

---

## 1. Contexto y Objetivos del MVP

PriceScope es una solución de inteligencia de mercado B2B orientada a cadenas minoristas, fondos de inversión y medios económicos en entornos de alta volatilidad cambiaria. El objetivo del MVP en 4 semanas es automatizar la medición de la inflación real y la comparación de precios de una canasta de bienes representativa frente a la evolución del tipo de cambio oficial y paralelo, ofreciendo un tablero analítico claro, confiable y accionable.

### Perfiles de Cliente (User Personas)

| Perfil | Necesidad Clave |
|--------|----------------|
| **Analista de Pricing / Retail** | Monitorear precios de competidores directos, detectar ofertas temporales y ajustar listas de precios protegiendo los márgenes de rentabilidad. |
| **Gestor de Fondos de Inversión** | Seguir la evolución de la canasta en moneda local y en divisa extranjera para tomar decisiones de cobertura frente a la devaluación. |
| **Analista Económico / Inteligencia de Mercado** | Datos transparentes con sellado de tiempo para medir la inflación subyacente real sin distorsiones por promociones pasajeras. |

---

## 2. Organización del Equipo

Dado que el equipo está compuesto por **3 desarrolladores frontend y 3 backend** con experiencia mixta:

### Estrategia Zero-Figma (Suplencia UX/UI)
Uso directo de bibliotecas de componentes financieros y analíticos prediseñados (**Tremor** y **shadcn/ui** con **Tailwind CSS**) para evitar demoras en diseño y mantener estética B2B consistente.

### Gestión Ágil Ligera (Suplencia PM)
Implementación de un tablero Kanban en GitHub Projects vinculado al repositorio oficial, sincronizaciones diarias asíncronas y un Tech Lead encargado de code reviews y resolución de bloqueos.

### Desarrollo Desacoplado con Mocks
El frontend inicia inmediatamente en la Semana 1 utilizando tipados TypeScript e interfaces JSON simuladas acordadas con el backend, evitando cuellos de botella por demoras en la base de datos o API.

---

## 3. Desglose de Épicas e Historias de Usuario (Enfoque Cliente)

---

### ÉPICA FE-1: Tablero Ejecutivo y Diagnóstico Macroeconómico

**Objetivo de negocio:** Permitir a los tomadores de decisiones evaluar de un vistazo la inflación real del mercado y el impacto de la volatilidad cambiaria sobre la canasta observada.

#### HU-01: Visualización de Indicadores Clave de Inflación y Tipo de Cambio

**Como** gestor de fondos de inversión,  
**quiero** visualizar un resumen ejecutivo con los principales indicadores de inflación acumulada y brecha cambiaria en la pantalla principal,  
**para** evaluar rápidamente si los precios de la economía se están ajustando por encima o por debajo del ritmo de devaluación de la divisa.

**Criterios de Aceptación:**

- [ ] El panel principal renderiza tarjetas métricas de alto nivel: Inflación Acumulada de la Canasta, Variación de Divisa (Brecha Oficial vs. Blue), Categoría con Mayor Aceleración y Spread Promedio entre Tiendas.
- [ ] Cada indicador muestra su tendencia visual mediante código de color: verde (estabilidad o apreciación) y rojo (aceleración inflacionaria o devaluación brusca).
- [ ] Durante la consulta de datos, la interfaz despliega componentes de carga animados (skeletons) que preservan el diseño sin saltos visuales.

---

#### HU-02: Análisis Gráfico de Inflación Real vs. Evolución Cambiaria

**Como** analista económico,  
**quiero** interactuar con un gráfico de series temporales que confronte la evolución de precios en moneda local frente a la cotización de la divisa extranjera,  
**para** comprobar de forma visual si la devaluación se traslada inmediatamente a los precios o si existe rezago en el mercado.

**Criterios de Aceptación:**

- [ ] El gráfico principal dibuja dos series diferenciadas: Curva A con el índice de precios promedio en moneda local y Curva B con la cotización del tipo de cambio (Oficial o Blue).
- [ ] Las escalas cuentan con doble eje Y claramente rotulado (moneda local a la izquierda, divisa a la derecha).
- [ ] Al pasar el cursor sobre cualquier punto temporal (hover), un tooltip unificado detalla la fecha exacta, precio en moneda local, valor convertido a dólares y la tasa cambiaria aplicada.
- [ ] La leyenda permite activar u ocultar series individuales para aislar variables de análisis.

---

#### HU-03: Segmentación y Filtros Dinámicos del Tablero

**Como** director comercial de una cadena minorista,  
**quiero** filtrar la información del tablero por categoría de productos, ventana temporal, comercio y tipo de moneda,  
**para** concentrar mi análisis en los segmentos comerciales específicos donde compite mi empresa.

**Criterios de Aceptación:**

- [ ] La barra superior ofrece selectores interactivos para: rango temporal (7d, 30d, 90d, personalizado), categoría de productos, moneda de visualización (Local, USD Oficial, USD Blue) y comercio específico.
- [ ] Al modificar un filtro, todos los gráficos y métricas se recalculan reactivamente sin recargar la página completa.
- [ ] Los parámetros seleccionados quedan reflejados en la URL para permitir compartir enlaces directos entre colegas del equipo.

---

### ÉPICA FE-2: Inteligencia de Precios Competitiva y Catálogo Canónico

**Objetivo de negocio:** Brindar visibilidad detallada sobre cómo se comportan los precios de productos idénticos en distintas cadenas comerciales, aislando promociones y variaciones de presentación.

#### HU-04: Exploración y Auditoría del Catálogo Monitoreado

**Como** analista de pricing,  
**quiero** buscar y consultar el listado completo de productos observados con sus características estandarizadas,  
**para** validar qué artículos forman parte de la medición y verificar su equivalencia entre tiendas.

**Criterios de Aceptación:**

- [ ] Se presenta una tabla con paginación que lista productos canónicos con: Nombre Comercial, Marca, Contenido Neto/Unidad (ej. 1 kg, 500 ml), Categoría y Tiendas Monitoreadas.
- [ ] Dispone de un buscador en tiempo real con debounce que filtra por coincidencia de nombre o marca.
- [ ] Cada fila cuenta con un enlace directo a la vista comparativa entre comercios.
- [ ] Si un producto presenta cambios de contenido neto detectados (reduflación), se muestra una etiqueta de advertencia visible.

---

#### HU-05: Comparador de Precios entre Cadenas de E-commerce

**Como** comprador corporativo o analista de retail,  
**quiero** comparar en una sola vista el precio actual de un mismo producto en todos los e-commerces relevados,  
**para** identificar qué competidor ofrece el mejor valor, calcular la dispersión del mercado y negociar con proveedores.

**Criterios de Aceptación:**

- [ ] La ficha del producto muestra una tabla comparativa con cada tienda participante: nombre, precio vigente y estado de stock.
- [ ] La tienda con el precio más bajo del mercado se resalta automáticamente con un distintivo visual ("Mejor Precio").
- [ ] La tabla calcula y exhibe el spread porcentual entre la opción más costosa y la más económica.
- [ ] Se incluye un enlace externo para auditar la publicación original en la tienda minorista.

---

#### HU-06: Aislamiento de Promociones Temporales vs. Precio Regular

**Como** analista económico,  
**quiero** visualizar de manera separada el precio de lista regular y el precio con descuento o promoción de cada producto,  
**para** evitar que ofertas pasajeras (como 2x1 o CyberWeek) distorsionen el cálculo real de la inflación estructural de fondo.

**Criterios de Aceptación:**

- [ ] La ficha del producto muestra claramente: Precio Regular (base), Precio con Descuento (promocional) y Porcentaje de Descuento aplicado.
- [ ] Si el producto no tiene oferta vigente, se indica explícitamente "Precio Regular (Sin oferta)".
- [ ] Un selector permite alternar los gráficos históricos entre la serie de precios regulares y la serie con promociones efectivas.

---

### ÉPICA FE-3: Monitoreo Cambiario y Volatilidad en Tiempo Real

**Objetivo de negocio:** Aportar transparencia total sobre las cotizaciones de divisas utilizadas en las conversiones y su sincronización horaria precisa.

#### HU-07: Panel de Cotizaciones Cambiarias Oficial y Paralela

**Como** gestor financiero,  
**quiero** consultar un módulo con la cotización actualizada del dólar oficial y el dólar blue junto con su brecha cambiaria,  
**para** sustentar mis proyecciones y análisis de cobertura de inventarios frente a la volatilidad cambiaria.

**Criterios de Aceptación:**

- [ ] Se presentan tarjetas con las cotizaciones vigentes del día: valor oficial y valor blue/paralelo, calculando la brecha porcentual entre ambas.
- [ ] La pantalla incluye un gráfico histórico que muestra la tendencia de ambas cotizaciones en los últimos 30 días.

---

#### HU-08: Trazabilidad y Sellado de Tiempo en Conversión de Precios

**Como** auditor o analista financiero corporativo,  
**quiero** conocer la fecha y hora exacta en que se registró el precio de un bien y la cotización cambiaria con la que fue convertido a dólares,  
**para** tener plena certeza metodológica de que las fluctuaciones intradía de la divisa no alteraron erróneamente el valor histórico reportado.

**Criterios de Aceptación:**

- [ ] Cada observación histórica de precio muestra de forma visible el timestamp exacto de recolección.
- [ ] Al inspeccionar el valor en dólares de un producto, la interfaz informa qué cotización específica de mercado se empleó para esa conversión.
- [ ] Se muestra un indicador del estado de sincronización indicando el tiempo transcurrido desde la última ingesta de divisas.

---

### ÉPICA FE-4: Sistema de Alertas Tempranas de Cobertura e Inflación

**Objetivo de negocio:** Notificar proactivamente a las empresas sobre desfasajes de precios y picos anómalos para que reaccionen a tiempo antes de perder rentabilidad.

#### HU-09: Alertas de Aumentos que Superan la Devaluación

**Como** tomador de decisiones en retail o finanzas,  
**quiero** recibir alertas sobre aquellos productos cuyo incremento porcentual de precio supere la tasa de devaluación del tipo de cambio en un período determinado,  
**para** identificar bienes que se encarecen en moneda dura (inflación en dólares) y renegociar con proveedores o ajustar mis listas de precios.

**Criterios de Aceptación:**

- [ ] Si el incremento de un producto en un período dado excede el avance de la divisa, la plataforma genera una alerta prioritaria en la bandeja de notificaciones.
- [ ] La alerta especifica: nombre del producto, porcentaje de incremento del precio local, porcentaje de devaluación en igual período y la brecha de descalce.
- [ ] Cada alerta cuenta con un botón directo a la ficha del producto y permite filtrado por severidad (Crítica, Moderada, Informativa).

---

#### HU-10: Detección Visual de Picos Anómalos y Eventos Comerciales

**Como** analista de mercado,  
**quiero** que la plataforma resalte visualmente los productos con aumentos bruscos de precio o cambios durante eventos comerciales (como CyberWeek),  
**para** aislar conductas especulativas de mercado frente a movimientos genuinos de costos.

**Criterios de Aceptación:**

- [ ] Los gráficos de evolución incorporan marcadores visuales sobre las fechas que coinciden con eventos masivos de comercio electrónico.
- [ ] El panel agrupa productos que registraron variaciones de precio superiores al umbral promedio de su categoría en lapsos de 48 horas.
- [ ] Se provee una función para copiar o exportar el listado de productos alertados.

---

### ÉPICA FE-5: Experiencia de Usuario Corporativa y Confiabilidad

**Objetivo de negocio:** Garantizar que los ejecutivos naveguen de forma ágil, segura y sin interrupciones durante sus sesiones de análisis o reuniones de directorio.

#### HU-11: Continuidad Operativa y Gestión de Errores de Conexión

**Como** usuario corporativo que consulta el dashboard en una reunión operativa,  
**quiero** recibir avisos claros y alternativas de recuperación cuando un servicio de datos o cotización tarde en responder,  
**para** no encontrar pantallas en blanco ni perder el contexto de mi sesión de trabajo.

**Criterios de Aceptación:**

- [ ] Las peticiones asíncronas despliegan skeletons contextualmente sin bloquear la navegación.
- [ ] Si el servidor experimenta una interrupción temporal, se despliega un mensaje informativo discreto con un botón de "Reintentar consulta" sin cerrar la sesión.
- [ ] Si una búsqueda no arroja resultados, se presenta una pantalla clara que sugiere ajustar los filtros seleccionados.
- [ ] Los campos numéricos sin información disponible se formatean con indicadores neutrales ("—" o "N/D") evitando errores visuales de tipo null o NaN.

---

#### HU-12: Visualización Ejecutiva Adaptativa (Desktop y Tablets)

**Como** directivo de empresa que viaja o asiste a reuniones con tablet o laptop ejecutiva,  
**quiero** que la interfaz de analítica ajuste automáticamente sus paneles y tablas a diferentes resoluciones de pantalla,  
**para** consumir los gráficos e indicadores con total legibilidad desde cualquier entorno de trabajo.

**Criterios de Aceptación:**

- [ ] El tablero se visualiza sin desbordamientos horizontales en pantallas desde 1024px en adelante.
- [ ] Los menús de navegación colapsan en barras laterales accesibles en pantallas medianas para maximizar el área de lectura de los gráficos.
- [ ] Las tablas de precios y comparativas permiten desplazamiento horizontal fluido y sticky headers en sus columnas principales.

---

## 4. Matriz de Trabajo Semanal para el Equipo Frontend

| Semana | Enfoque | Épicas | Historias de Usuario | Responsable |
|--------|---------|--------|---------------------|-------------|
| **Semana 1** | Cimientos y Mocks (Preparación técnica para Épicas FE-1 a FE-5) | — | — | Setup de React.js, Tailwind y Tremor/shadcn (FE-1 y FE-3)<br>Modelado de interfaces TypeScript basadas en el ERD y archivo mock de datos JSON (FE-1)<br>Estructura de navegación y layout corporativo (FE-2) |
| **Semana 2** | Tablero y Visualización (ÉPICA FE-1 y ÉPICA FE-2 parcial) | FE-1, FE-2 | HU-01, HU-03, HU-02, HU-04 | Tarjetas de métricas ejecutivas y barra de filtros (FE-2 y FE-3)<br>Gráfico de series temporales de doble eje (FE-1)<br>Tabla de exploración del catálogo canónico (FE-2) |
| **Semana 3** | Comparativa, Alertas e Integración (ÉPICA FE-2, FE-3 y FE-4) | FE-2, FE-3, FE-4 | HU-05, HU-06, HU-07, HU-08, HU-09, HU-10 | Ficha comparativa entre tiendas y módulo de divisas (FE-2 y FE-3)<br>Bandeja de alertas de devaluación y picos (FE-3)<br>Conexión con endpoints reales de FastAPI y reemplazo progresivo de mocks (FE-1 + Backend) |
| **Semana 4** | Calidad, Estabilización y Demo (ÉPICA FE-5) | FE-5 | HU-11, HU-12 | Estados de carga, manejo de errores y adaptabilidad responsiva (FE-2 y FE-3)<br>Auditoría de rendimiento y ensayo del recorrido de demostración en vivo (Todo el equipo frontend) |

---

*Documento elaborado por el Equipo 14 — Simulación Laboral Abierta (No Country)*
