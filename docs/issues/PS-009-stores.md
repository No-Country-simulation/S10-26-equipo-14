
# [DB] Crear el modelo y la migración de stores

## Contexto

PriceScope necesita registrar los comercios de los que se obtendrán
precios. La tabla stores será una de las entidades iniciales del modelo.

## Objetivo

Crear el modelo SQLAlchemy de Store y la migración correspondiente
para PostgreSQL, siguiendo el modelo de datos aprobado.

## Alcance

- Crear el modelo Store.
- Definir los campos acordados en el diccionario de datos.
- Registrar el modelo para que Alembic pueda detectarlo.
- Crear la migración.
- Aplicar la migración en el entorno de desarrollo autorizado.
- Añadir pruebas para las reglas principales.

## Fuera de alcance

- Implementar scraping de tiendas.
- Crear la interfaz de administración.
- Modificar las tablas del frontend.
- Añadir campos que no estén acordados en el modelo.

## Dependencias

- Modelo de datos revisado.
- Entorno Python instalado.
- Variables de conexión configuradas de forma segura.
- Base de datos de desarrollo disponible.

## Criterios de aceptación

- [ ] El modelo Store coincide con el diccionario de datos aprobado.
- [ ] Alembic detecta y genera la migración esperada.
- [ ] La migración se aplica correctamente en la base de datos de desarrollo.
- [ ] Las restricciones y campos obligatorios son correctos.
- [ ] Las pruebas correspondientes pasan.
- [ ] No se incluyen credenciales en los archivos versionados.
- [ ] La documentación se actualiza si cambió el modelo.

## Pruebas

1. Ejecutar la migración en la base de datos de desarrollo.
2. Comprobar que la tabla y sus columnas existen.
3. Comprobar que los campos obligatorios rechazan valores inválidos.
4. Ejecutar la suite de pruebas del backend.
5. Revisar el resultado de la migración antes de integrarla.

## Entregable

Modelo Store, migración y pruebas relacionadas.

## Evidencias requeridas

- Nombre de la migración creada.
- Resultado de las pruebas.
- Resumen de los cambios en el pull request.
- Explicación de las decisiones tomadas.

## Preguntas de revisión

- ¿Para qué sirve una migración?
- ¿Qué problema resuelve la clave primaria?
- ¿Por qué no debemos guardar la contraseña de Neon en el código?
- ¿Qué ocurre si posteriormente necesitamos añadir una columna?

## Definición de terminado

El Issue se considera terminado cuando se cumplen los criterios,
las pruebas pasan y el cambio se revisa e integra según el flujo
Git acordado por el equipo.
