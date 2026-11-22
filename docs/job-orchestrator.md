# S3T19: orquestador de trabajos

Esta implementación parte de S3T18 y reutiliza su chunker, validador y servicio
de estructuración. El modelo `ProcessingJob` pertenece a la aplicación `documents`.
La migración `documents/0003_processingjob_ai_progress.py` añade el progreso,
consumo, resumen, código de error y los DI original y propuesto.

## Configuración y ejecución

```dotenv
JOB_RUNNER=thread
JOB_RUNNER_MAX_WORKERS=2
```

`orchestrator.runner.enqueue(job_id)` devuelve un `Future`. Con `sync` ejecuta en
el mismo hilo; con `thread` usa un `ThreadPoolExecutor` compartido. En ambos casos
el arranque se registra con `transaction.on_commit`: un trabajo creado dentro de
una transacción no comienza antes de que sea visible y un rollback no lo ejecuta.
Los workers reciben solo el ID y gestionan sus propias conexiones de Django.

`thread` sirve para desarrollo/demo: su cola vive dentro del proceso y no sobrevive
a reinicios del servidor. `shutdown_runner()` permite cerrar el pool al terminar.
`sync` se utiliza en las pruebas para ejecutar el flujo de forma determinista.

## Propuesta de estructura

`run_ai_structuring(job_id)` reclama mediante una actualización condicional un job
`pending` o `processing` en etapa `queued`. Otras ejecuciones del mismo ID no lo
vuelven a procesar. No mantiene una transacción abierta durante las llamadas de IA.

1. Pasa a `processing` / `extracting` y extrae el DI desde el archivo almacenado.
2. Comprueba `ensure_within_limit` y guarda `structure_original`.
3. Llama a `structure_document` con las opciones `config.ai`. El callback
   `on_progress(stage, done, total)` persiste `structuring` y `validating` en cada
   fragmento. Los reintentos no incrementan el número de fragmentos completados.
4. Guarda `structure_proposed` y su copia de compatibilidad en `ai_suggestions`,
   junto con `ai_summary` y `ai_usage`. Cambia a `review`, sin generar todavía
   el archivo descargable ni establecer `finished_at`.

El resumen conserva los contadores de S3T18 y añade `fallback_only`,
`chunks_fallback`, `headings_detected`, `lists_detected`, `tables_detected` y
`bold_emphasis_applied`. Si todos los fragmentos usan el respaldo heurístico,
el job continúa a revisión con `fallback_only=true`.

`ai_usage` acumula los tokens de entrada, salida y totales de todas las respuestas,
incluidas las rechazadas por el validador. También guarda `calls`, los intentos de
transporte reportados en `attempts`, y las listas de modelos y proveedores usados.
Si una llamada falla sin devolver consumo, no se inventa una cifra de tokens.

## Aprobación y reversiones

```python
from orchestrator.ai_pipeline import finalize_job

finalize_job(job, revert_ids=["b3", "b8"])
```

`finalize_job` requiere `review`. Valida los IDs y reclama el job antes de pasar a
`processing` / `building`. Si la selección es inválida, permanece en revisión.

Las reversiones se expresan mediante bloques `keep` que referencian el XML del
archivo original. Así se recuperan texto, runs, propiedades y numeración originales
antes de aplicar la plantilla. Un origen dividido en varias viñetas se restaura
una sola vez. Si un origen pertenece a una tabla formada con varios bloques, se
restaura el grupo completo: no se intenta adivinar qué celdas corresponden a cada
origen. También se eliminan los subtítulos generados anclados a ese grupo. Revertir
todos los orígenes elimina además los subtítulos generados sin ancla.

La finalización reconstruye con `rebuilder v2`, aplica `apply_template`, guarda
en memoria y reabre el `.docx`. Compara los tokens del cuerpo y los datos críticos
antes y después del formateo. Solo publica el archivo y pasa a `done` si la
verificación termina correctamente. El resumen añade `reverted_blocks_count`
y `reverted_source_ids`; la propuesta original de revisión no se modifica.

## API y errores

- `POST /api/documents/{id}/format/` con `use_ai=true` encola el job y devuelve
  `202 Accepted`. En modo `sync` el worker ya puede haber terminado al consultar
  el estado; en modo `thread` la petición no espera al proveedor.
- Sin IA se conserva el formato síncrono con respuesta `200`.
- Un job que ya está en `processing` devuelve `409 INVALID_STATE` al intentar
  formatearlo nuevamente.
- `GET /api/documents/{id}/` expone `progress`, `ai_summary`, `ai_usage` y
  `error_code`, además de los campos existentes.
- La revisión/aprobación puede invocar `finalize_job`; esta tarea proporciona
  ese motor y no añade los endpoints `/structure/` y `/review/`.

Los fallos de autenticación/configuración se guardan como `AI_NOT_CONFIGURED`;
otros errores de proveedor que lleguen al orquestador usan `AI_UNAVAILABLE`.
Los límites de tamaño usan `DOCUMENT_TOO_LARGE_FOR_AI`. Los errores inesperados
usan `PROCESSING_ERROR` y un mensaje fijo, sin texto del proveedor ni stack traces.
La extracción y los límites de IA se comprueban en el worker: sus errores se
consultan en el estado del job después de recibir el `202`.

## Migraciones y pruebas

Aplicar la migración en el entorno de la aplicación:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py migrate
```

La configuración `core.test_settings` utiliza SQLite y almacenamiento temporal,
sin conectarse a la base PostgreSQL de desarrollo. Las pruebas de orquestación
usan `FakeProvider`, `JOB_RUNNER=sync` y una prueba del runner con hilos reales.

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_orchestrator.py --ds=core.test_settings -q
.\venv\Scripts\python.exe -m pytest --ds=core.test_settings --ignore=tests/test_e2e_web.py -m "not live and not e2e" -q
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=core.test_settings
```

Se comprueban las transiciones `processing → review → done`, progreso por fragmento,
consumo de reintentos, respaldo total, autenticación y errores seguros, reversiones
de XML y de tablas agrupadas, rollback, envíos duplicados y ejecución sin bloquear
la petición de la API.
