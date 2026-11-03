# Proveedores de ingesta: tareas pendientes

El módulo `backend/app/services/ingestion.py` contiene tipos de proveedor,
normalización y primitivas de persistencia. No contiene clientes HTTP ni
extractores reales. Ningún proveedor está integrado o validado actualmente.

## Carrefour Argentina

- Confirmar una fuente pública y estable y sus términos de uso/robots antes de
  implementar captura. No automatizar acceso que evada controles.
- Confirmar identificador externo estable, URL canónica, moneda, precio regular,
  promoción y señal de disponibilidad.
- Definir límites de frecuencia, reintentos y evidencia de fecha/hora de captura.
- Probar el parser solo con fixtures sintéticos claramente identificados, sin
  presentar sus valores como precios vigentes.

## Frávega

- Repetir la verificación de acceso autorizado y estabilidad de la fuente.
- Determinar cómo representan SKU, variantes, cuotas/promociones y disponibilidad;
  no tratar financiación como precio contado sin una regla aprobada.
- Añadir adaptador, normalización y pruebas únicamente tras confirmar la fuente.

## BCRA (cotización oficial)

- Identificar el endpoint oficial vigente, campos, unidades y frecuencia.
- Confirmar si la respuesta ofrece una tasa de referencia o compra/venta; persistir
  `rate_side=reference` para una única tasa o `buy`/`sell` cuando estén presentes.
- Documentar cómo seleccionar la última observación no posterior a la fecha de
  comparación y cómo representar días sin publicación.

## Ámbito Financiero (cotización blue candidata)

- Verificar accesibilidad automatizada, estabilidad, atribución y condiciones de
  reutilización antes de construir un adaptador.
- Confirmar si se publican compra y venta y registrar cada lado como observación
  separada. Si el proveedor no es accesible/estable, dejarlo deshabilitado y
  proponer otra fuente documentada.

## Requisitos comunes antes de activar un proveedor

- Guardar fuente, hora con zona, ejecución (`ExtractionRun`) y resultado por lote.
- Validar moneda y decimales antes de persistir; nunca convertir a `float`.
- Hacer idempotentes los reintentos mediante claves de unicidad acordes a la
  fuente y conservar cada observación histórica.
- Añadir pruebas de parser y de fallos con fixtures sintéticos; separar esos
  fixtures de cualquier dato operativo.
- Ejecutar integración PostgreSQL aislada antes de desplegar cambios de esquema.
