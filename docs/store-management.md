# Gestión de Tiendas: flujo local

## Flujo para la persona administradora

1. Abre **Tiendas** y registra nombre, sitio principal HTTPS, país y moneda.
2. Pulsa **Analizar sitio**. El analizador consulta `robots.txt` y solo lee la
   portada pública de Frávega cuando la regla de rastreo la permite. No recorre
   rutas descubiertas ni consulta APIs internas.
3. Revisa los enlaces observados. PriceScope solo permite seleccionar para
   monitoreo un enlace cuyo texto coincida exactamente con una categoría ya
   existente en el catálogo. Las etiquetas no reconocidas se muestran como
   propuestas pendientes; no crean categorías automáticamente.
4. Selecciona categorías reconocidas, moneda y frecuencia deseada y pulsa
   **Activar monitoreo**. La pantalla indica que la configuración está activa,
   pero las ejecuciones siguen siendo manuales porque aún no hay scheduler.
5. La última extracción se muestra cuando existe un `ExtractionRun` asociado a
   esa tienda. Los registros históricos anteriores a la columna `store_id` no
   se pueden atribuir con certeza a una tienda.

## Estados

- `pending`: tienda guardada, aún sin análisis.
- `analyzing`: análisis en curso.
- `configuration_required`: se necesita revisar propuestas, categorías o
  compatibilidad.
- `active`: las preferencias se guardaron como activas; esto aún no programa
  una tarea periódica.
- `error`: el análisis no pudo completarse; se puede volver a intentar.

La identidad global vive en `stores`. El estado técnico del adaptador y los
resultados observados viven en `store_integrations`. La moneda, frecuencia,
categorías elegidas y activación viven en `store_monitoring_preferences` y
`store_monitoring_categories`. Esta primera versión tiene preferencias a nivel
de tienda; no contiene `user_id`, `organization_id` ni roles. Cuando se incorpore
autenticación, habrá que definir su ámbito organizacional antes de migrar esas
preferencias.

## Ejecución local

Las escrituras de gestión y el análisis están protegidos para aceptar únicamente
conexiones loopback. Esto no es autenticación; es una barrera temporal para que
las rutas administrativas nuevas no queden disponibles desde el backend
desplegado. No abras esa barrera: antes de habilitar operaciones remotas se debe
implementar autenticación y autorización de roles.

Usa una terminal en `backend/`. Inicializa la base local con el CLI; la ruta
predeterminada es `backend/.local/pricescope.sqlite3` y no depende de `.env`.
Después define esa misma URL solo en la terminal que inicia FastAPI. En PowerShell:

```powershell
python -m app.commands.pricescope_local db init
$env:DATABASE_URL = "sqlite:///./.local/pricescope.sqlite3"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

En otra terminal, ejecuta `npm run dev` en `frontend/`. Vite reenvía `/api` a
`http://127.0.0.1:8001`; en desarrollo no se usa la API desplegada.
El backend exige que `DATABASE_URL` apunte a SQLite y que Alembic esté en head
`f41d0c2a9b73`. Para retirar la variable de esa terminal usa:

```powershell
Remove-Item Env:DATABASE_URL
```

No ejecutes el comando Alembic con una URL de Neon/Render para esta prueba. La
migración `a6f20488d7b1_store_management.py` solo se incorpora al repositorio;
no se ha ejecutado contra servicios remotos.

## Alcance y limitaciones

- El único analizador registrado es específico para Frávega. Otros dominios
  quedan en `configuration_required` sin solicitudes de red.
- Se leen enlaces dentro de `<nav>` estático en la portada. Si el sitio los
  renderiza con JavaScript, usa otra estructura o `robots.txt` no permite la
  portada, el analizador no detectará categorías y fallará cerrado.
- Las propuestas provienen de etiquetas y enlaces realmente observados. Una
  coincidencia exacta con `Category` solo habilita la selección; el operador
  confirma antes de guardar preferencias.
- No hay descubrimiento/importación de productos, scheduler, ejecución periódica,
  autenticación ni ámbito por usuario/organización. La selección de categorías
  guarda configuración, pero no inicia una tarea automática.
- No se han agregado productos, categorías, URLs ni precios de demostración a
  las bases de datos. Las pruebas usan HTML sintético y no acceden al portal.
