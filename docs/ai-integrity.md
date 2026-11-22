# S3T18: integridad y servicio de estructuración

`ai_engine.validator.validate_chunk(input_blocks, output_blocks)` acepta bloques
Pydantic o diccionarios. Devuelve un `IntegrityReport` con `ok`, `violations`
(`type`, `src`, `message`) y `warnings`. Conserva `is_valid` y `errors` para los
consumidores anteriores del reporte. Una salida que no cumple el esquema produce
una violación `INVALID_SCHEMA`.

## Comprobaciones

- Todos los bloques originales necesitan referencias `src` válidas y en orden.
  Solo un origen dividido en varios `list_item` puede repetir su referencia.
  Un subtítulo generado puede referenciar un origen sin reemplazar su contenido.
- Los `keep` se devuelven exactamente una vez, en su posición relativa entre los
  bloques originales. La salida referencia el original; nunca sustituye su XML.
  Los `keep` con `keep_kind="empty"` pueden omitirse en la salida para delegar
  el espaciado a la plantilla.
- Números con signos, decimales, porcentajes y símbolos Unicode de moneda se
  comparan como una secuencia exacta (normalizando el espacio antes de `%`).
  También se comprueba el texto generado: marcarlo no autoriza inventar cifras.
  En tablas pivoteadas, los datos críticos se comparan tras deduplicar las claves
  promovidas a encabezado.
- `SequenceMatcher(autojunk=False)` compara tokens por grupos de procedencia,
  conservando el orden. Solo se ignora el cambio de caja al inicio de un bloque
  o de las cláusulas que se convierten en viñetas. Se verifica la retención por
  bloque o registro para evitar que uno largo oculte la omisión de otro corto.
- Se permite quitar glifos en listas y prefijos de numeración manual (de 1 a 3
  dígitos, evitando años de 4 dígitos) en listas ordenadas. El signo de un
  importe negativo nunca se trata como un glifo.
- Al dividir un párrafo en listas se permite quitar `,`, `;`, `y`, `e`, `o` (sin
  sensibilidad a mayúsculas). En tablas se permiten separadores `:`, `|`,
  tabuladores. Las claves repetidas pueden pasar al encabezado cuando todos los
  registros tienen las mismas claves en el mismo orden; sus valores permanecen
  en orden de lectura.
- Solo los subtítulos H1–H3 y las celdas de la primera fila con `header_row=true`
  pueden llevar `generated=true`. El valor por defecto es `false`. No se admite
  el campo en párrafos, listas, `callout`, `keep` ni en el bloque completo de
  una tabla. Los encabezados generados no entran en el presupuesto de palabras
  nuevas, pero tienen límite propio de longitud y de cantidad por fragmento. Los
  párrafos y bloques `callout` no pueden ganar texto inventado, aunque quepa en
  el presupuesto general.
- Los títulos no terminan en punto y se restringen a Title y H1–H3. Las tablas
  deben tener al menos dos filas y dos columnas, considerando `h_span`, con ancho
  uniforme. El porcentaje de negrita se verifica por bloque y por celda sobre las
  negritas añadidas respecto al bloque de origen, preservando las negritas
  originales del documento.

Los cambios estructurales permitidos se registran como advertencias, no errores.

## Configuración

Los umbrales se leen de Django settings en cada validación y se configuran mediante
variables de entorno; las opciones del documento no pueden relajarlos.

| Variable | Valor por defecto |
| --- | --- |
| `AI_MAX_BOLD_RATIO` | `0.30` |
| `AI_MAX_HEADING_WORDS` | `20` |
| `AI_MIN_TOKEN_RETENTION` | `0.95` |
| `AI_MAX_ADDED_TOKEN_RATIO` | `0.05` |
| `AI_MAX_GENERATED_HEADING_WORDS` | `6` |

La retención mínima permite diferencias parciales dentro de ese margen; no permite
omitir bloques completos, reordenar contenido ni alterar datos críticos.

## Servicio

```python
from ai_engine.service import structure_document

result = structure_document(di, {"emphasis": "ligero"}, provider)
blocks = result.blocks
summary = result.summary
```

`provider` implementa `LLMProvider.structure(chunk, feedback=None)` y devuelve un
`ProviderResult`. Si se omite, se utiliza el registro de proveedores configurado.
Las opciones se transmiten en `metadata.ai_options` para construir el prompt.
El servicio entrega una copia del fragmento al proveedor para proteger el original.

Por fragmento se realiza una llamada y se valida la respuesta. Si falla la
integridad, el esquema, la correspondencia del `chunk_id` o el proveedor devuelve
un `ProviderError`, se hace **un solo reintento** con las violaciones serializadas
en `feedback`. Un segundo fallo activa `heuristic.structure` y continúa con los
fragmentos restantes. Los reintentos de transporte internos del proveedor son
independientes del único reintento de integridad.

`StructureResult` contiene `blocks`, las salidas finales en `chunks`, los reportes
de cada intento de IA en `reports`, `usage` y `summary`. Desde S3T19, el callback
opcional `on_progress(stage, done, total)` permite persistir el avance sin acoplar
el servicio a la base de datos. `usage` agrega el consumo de todas las respuestas,
incluidos los reintentos; el [orquestador](job-orchestrator.md) lo guarda en el job.

Campos de `summary`:

| Campo del resumen | Significado |
| --- | --- |
| `chunks_total` | Fragmentos del documento |
| `chunks_ai` | Fragmentos aceptados por el validador tras usar IA |
| `chunks_retried` | Fragmentos que necesitaron el segundo intento |
| `chunks_heuristic` | Fragmentos resueltos mediante el respaldo heurístico |
| `blocks_by_type` | Conteo final por tipo de bloque |
| `generated_elements` | Subtítulos y celdas de encabezado marcados como generados |

Los límites de documento y de bloque se comprueban antes de llamar al proveedor.
Un documento demasiado grande sigue lanzando `DocumentTooLargeForAI`, según S3T17.
Este servicio queda disponible para el orquestador; esta tarea no cambia los
endpoints existentes ni ejecuta llamadas reales al proveedor en las pruebas.

## Pruebas

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_ai_validator.py tests/test_ai_service.py -q
```

La tabla parametrizada cubre datos críticos alterados, omisiones, cambios de orden,
`keep` perdido/duplicado/movido, negritas excesivas, texto inventado, forma de tablas
y títulos, ubicaciones inválidas de `generated` y las transformaciones permitidas.
Las pruebas del servicio usan proveedores simulados sin red y comprueban el
feedback, el único reintento, el respaldo y la continuidad entre fragmentos.
