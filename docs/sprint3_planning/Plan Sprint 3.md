# Plan Sprint 3: Estructuración inteligente de documentos con IA

> **Objetivo del sprint:** que el programa funcione de punta a punta con este flujo: **extractor → JSON → agente de IA → rebuilder → templates_engine**. Con un `.docx` de texto plano o mal formateado se obtiene un Word con estructura real (títulos, listas, tablas, negritas y bloques destacados) y con la plantilla aplicada, **sin modificar la información**.
>
> Este plan es una guía flexible. Las prioridades (**M** = Must, **S** = Should, **C** = Could) indican qué se puede recortar si falta tiempo sin perder el objetivo.

---

## 1. Punto de partida (fin del Sprint 2)

| Ya funciona | Falta para el objetivo |
|---|---|
| Carga validada de `.docx` (extensión, 10 MB, magic bytes, corrupción). | Conectar el extractor y el rebuilder al flujo de la API (hoy solo existe `/extract/` y los scripts manuales). |
| Formateo visual síncrono sobre el original: márgenes, fuente, tamaños de H1–H3 e interlineado, con 3 presets. | Que la plantilla dé formato a la **estructura**: títulos (negrita, espaciado), listas, tablas, citas y alineación. |
| `extract_structure`: párrafos, runs, listas nativas, imágenes y tablas con celdas combinadas. | IDs estables por bloque, señales para la IA (tamaño relativo, glifos, sangría) y bloques "intocables". |
| `rebuild_from_structure`: roundtrip sin pérdidas en 5 de 6 fixtures. | Que no se pierdan secciones ni la orientación (06_secciones) y que se respeten los niveles de lista. |
| 61 pruebas en verde (templates_engine y API). | Pruebas de docx_engine, `ai_engine` completo, procesamiento asíncrono y pantallas de IA. |
| `PIPELINE` extensible, `ProcessingJob.use_ai`, `ai_suggestions` y el estado `review` reservados. | Activar todo eso. |

**Hallazgo que guía el sprint:** los fixtures `02_headings_mixto` y `05_listas` tienen títulos falsos (párrafos `Normal` con negrita y 16–22 pt) y listas escritas con glifos (`·`, `◦`, `▪`, `1.`). El extractor no las reconoce y la plantilla solo cambia la fuente. Son el caso de prueba perfecto para la IA.

---

## 2. Decisiones de diseño

1. **La IA propone estructura, no redacta.** Su único trabajo es clasificar, dividir, agrupar y marcar énfasis. No corrige ortografía ni reescribe. La corrección de texto pasa al Sprint 4.
2. **La integridad se verifica con código, no con el prompt.** Un validador comprueba que la secuencia de palabras y cifras del resultado es **idéntica** a la original. Si un fragmento no pasa, se reintenta una vez; si vuelve a fallar, se usa el estructurador heurístico. Nunca se entrega texto alterado.
3. **Bloques opacos.** Imágenes, tablas existentes, saltos de sección, ecuaciones y campos se envían a la IA solo como `{"type": "keep", "id": "b12"}` y el rebuilder los copia tal cual del XML original. La IA solo ve los párrafos de texto.
4. **Reconstruir sobre el original, no sobre un documento en blanco.** El rebuilder v2 clona el `.docx` original, vacía el body (conserva la última `sectPr`) e inserta los bloques nuevos. Así se conservan estilos, numeración, encabezados, pies, relaciones de imágenes y la configuración de página.
5. **Dos modos de formateo.** `use_ai: false` sigue igual que en el Sprint 2 (síncrono e in-place, sin regresiones). `use_ai: true` usa el modo "reestructurar", que es asíncrono y pasa por revisión.
6. **Un proveedor real, desacoplado.** Interfaz `LLMProvider` con `FakeProvider` (determinista, gratis) y un proveedor real configurable. La API key vive en el `.env` del servidor durante este sprint. Que cada usuario traiga su propia key (con cifrado) queda para el Sprint 4.
7. **Lo asíncrono, simple.** Un `JobRunner` con un backend `thread` (ThreadPoolExecutor) para desarrollo y demo, y `sync` para las pruebas. Celery y Redis son opcionales (C), con la misma interfaz, para no frenar al equipo en Windows.
8. **El estructurador heurístico es parte del producto.** Detecta títulos falsos, glifos de lista y numeración manual sin IA. Sirve como `FakeProvider`, como respaldo cuando la IA falla y como base de comparación en la evaluación.

---

## 3. Arquitectura del flujo con IA

```mermaid
flowchart TD
    A["POST /format/ use_ai=true"] --> B["202 Accepted + JobRunner.enqueue(job)"]
    B --> C["extractor v2: Documento Intermedio (DI) con ids, hints y bloques opacos"]
    C --> D["chunker: fragmentos de ~8k caracteres con la ruta de títulos como contexto"]
    D --> E["LLMProvider.structure(chunk): JSON con esquema"]
    E --> F{"validador de integridad"}
    F -- "OK" --> G["DI estructurado"]
    F -- "falla" --> R["1 reintento con feedback"]
    R --> F2{"validador"}
    F2 -- "OK" --> G
    F2 -- "falla" --> H["estructurador heurístico para ese fragmento"]
    H --> G
    G --> I["estado review: el usuario ve la vista previa"]
    I -- "aceptar (con bloques revertidos opcionales)" --> J["rebuilder v2 sobre el original"]
    I -- "rechazar" --> K["flujo Sprint 2 (solo plantilla)"]
    J --> L["templates_engine v2"]
    K --> M["result.docx (done)"]
    L --> M
```

Regla de dependencias: `ai_engine` **no importa** `python-docx` ni `docx_engine`. Solo trabaja con el esquema del DI (`common/document_schema.py`).

---

## 4. Documento Intermedio (DI): el JSON que viaja a la IA

**Entrada a la IA** (compacta; solo lo necesario para decidir):
```json
{
  "doc_context": {"document_type": "reporte", "body_font_size": 11},
  "heading_path": ["1. RESUMEN"],
  "blocks": [
    {"id": "b3", "text": "1. RESUMEN", "hints": {"all_bold": true, "size_ratio": 1.45, "words": 2, "ends_with_period": false}},
    {"id": "b4", "text": "Región Norte: crecimiento moderado, sin incidencias.", "hints": {"starts_with_glyph": null, "indent_level": 0}},
    {"id": "b5", "type": "keep"}
  ]
}
```

**Salida de la IA** (validada con Pydantic y JSON Schema):
```json
{
  "blocks": [
    {"type": "heading", "level": 1, "src": ["b3"], "runs": [{"text": "1. RESUMEN"}]},
    {"type": "list_item", "ordered": false, "level": 0, "src": ["b4"],
     "runs": [{"text": "Región Norte:", "bold": true}, {"text": " crecimiento moderado, sin incidencias."}]},
    {"type": "keep", "id": "b5"}
  ]
}
```

Tipos de bloque en la salida: `heading` (niveles 0–3, donde 0 = Título), `paragraph`, `list_item` (`ordered` y `level` 0–2), `table` (`header_row` y `rows[][]` con `runs`), `callout` (`note` | `quote` | `warning`) y `keep`. Cada bloque generado lleva `src` con los ids de origen, para trazabilidad, para la vista previa y para revertir.

---

## 5. Regla de integridad del contenido (el corazón del sprint)

`validate_chunk(input_blocks, output_blocks) -> IntegrityReport`

1. **Secuencia de tokens idéntica:** se tokenizan palabras y números (`\w+`, con acentos y sin cambiar mayúsculas) de la entrada y de la salida (todos los runs y celdas en orden de lectura). Las dos listas deben ser **exactamente iguales**: nada agregado, quitado, cambiado ni reordenado.
2. **Puntuación significativa:** `. , ; ? ! ¿ ¡ ( ) " %` y los símbolos de moneda deben conservarse en orden.
3. **Únicos cambios permitidos (estructurales):** quitar glifos de viñeta al inicio (`• · ◦ ▪ - – *`), quitar la numeración manual al inicio de un bloque convertido en `list_item ordered` (`1.`, `a)`, `iv.`), quitar separadores convertidos en celdas (`:`, `|`, tabulador), y cambios de espacios o saltos de línea.
4. **Bloques `keep`:** cada id opaco aparece exactamente una vez y en el mismo orden.
5. **Guardrails de forma:** un título tiene ≤ 20 palabras y no termina en punto; la negrita ocupa ≤ 30 % de las palabras de un párrafo (configurable); una tabla tiene ≥ 2 filas y ≥ 2 columnas, todas sus filas con el mismo número de columnas efectivas; no se permiten más de 3 niveles de título.
6. Si algo falla, el reporte indica qué bloques `src` están afectados para el reintento y para las métricas.

---

## 6. Backlog del Sprint 3

### Fase 0: Base

**S3T1 – Contrato API v1.1 (modo reestructurar con IA)** · M · Backend + Frontend
1. Actualizar `api-contract.md` a v1.1 y registrar el cambio en "Control de cambios".
2. Agregar a la configuración `use_ai: true` y el bloque `ai`: `{"document_type": "reporte|academico|acta|propuesta|otro", "detect_headings": true, "detect_lists": true, "detect_tables": true, "emphasis": "none|light|medium"}`.
3. `POST /documents/{id}/format/` con `use_ai: true` responde **202** `{status: "processing"}`. Con `false` se mantiene el 200 del Sprint 2.
4. `GET /documents/{id}/` agrega `progress {stage, done, total}` (etapas `extracting | structuring | validating | building`), `ai_summary` y `error_code`, y activa el estado `review`.
5. Nuevo `GET /documents/{id}/structure/` (solo en `review`): DI original y DI propuesto, para la vista previa.
6. Nuevo `POST /documents/{id}/review/`: `{"action": "accept", "revert": ["b4", ...]}` o `{"action": "reject"}`. Responde 200 con el estado `done` y los conteos.
7. Errores nuevos: `AI_NOT_CONFIGURED` (503), `AI_UNAVAILABLE`, `AI_RATE_LIMIT`, `DOCUMENT_TOO_LARGE_FOR_AI` (400) e `INVALID_STATE` (409).
8. Incluir mocks de cada respuesta para el frontend. Aprobación por PR de backend y frontend **antes del día 2**.

**S3T2 – Red de pruebas de docx_engine y deuda del Sprint 2** · M · Backend docx
1. Crear `tests/test_docx_engine.py`: roundtrip extract → rebuild con los 6 fixtures, usando `comparator` para verificar textos, número de tablas, imágenes y celdas combinadas.
2. Marcar como `xfail` documentado el caso conocido (06_secciones pierde secciones) hasta S3T5.
3. Corregir el `UserWarning` de `spacing.py` (buscar el estilo por tipo o por id de forma segura).
4. Mover `manual_test.py` y `probar_deteccion.py` a `scripts/` y apuntarlos a `tests/fixtures/`, o eliminarlos.
5. Eliminar `extract_paragraphs` si nadie lo usa.

**S3T3 – Esquema del Documento Intermedio (Pydantic)** · M · Backend IA
1. Crear `backend/common/document_schema.py` con `Run`, `Hints`, `SourceBlock`, `OutBlock` (unión discriminada por `type`), `AIChunkInput`, `AIChunkOutput` e `IntegrityReport`.
2. Agregar `schema_version = "di.v1"`.
3. Validaciones: `level` en rango, filas de tabla rectangulares (considerando `h_span`) y `runs` no vacíos.
4. Exportar el JSON Schema a `docs/schemas/` (lo usan el proveedor para la salida estructurada y el frontend).
5. Tests de serialización ida y vuelta.

### Fase 1: Motor documental

**S3T4 – Extractor v2** · M · Backend docx
1. `extract_document(path) -> DI`: un id estable `b{índice en el body}` para cada hijo del body.
2. Los párrafos de texto pasan a `SourceBlock` con `hints`: `all_bold`, `size_ratio` (tamaño máximo del run / tamaño base del documento, calculado como la moda ponderada por caracteres), `words`, `ends_with_period`, `starts_with_glyph`, `manual_numbering` (regex), `indent_level` (a partir de `w:ind`), `style_name` y si es lista nativa.
3. Se marcan como opacos (`keep`): tablas existentes, párrafos con imagen, dibujo, campo, nota al pie, hipervínculo o control de cambios, párrafos con `sectPr` (salto de sección) y elementos desconocidos.
4. Conservar `underline` en los runs.
5. Devolver estadísticas: total, de texto, opacos y el motivo de cada opaco.
6. Mantener `extract_structure` (lo usa `/extract/`) como adaptador sobre el v2.
7. Tests: en `05_listas` los glifos y la sangría se detectan; en `02_headings_mixto` los títulos falsos tienen `size_ratio > 1.2`; en `04` y `06` los opacos son los esperados.

**S3T5 – Rebuilder v2 (sobre el documento original)** · M · Backend docx
1. `rebuild_document(original_path, structured_di) -> Document`: clonar el original, vaciar el body conservando la `sectPr` final e insertar en orden.
2. `keep`: `deepcopy` del elemento XML original por id. Así las imágenes y las tablas conservan sus relaciones y se eliminan los archivos temporales.
3. `heading` → `Title` / `Heading 1–3`; `paragraph` → `Normal`; `callout` → `Quote` / `Intense Quote` (crear el estilo si no existe).
4. `list_item`: numeración **nativa** de Word (`numPr` con `ilvl` = `level`). Crear un `abstractNum` de viñetas y otro numerado en `numbering.xml` si no existen. Cada lista ordenada nueva reinicia la numeración.
5. `table`: crear la tabla, marcar la fila de encabezado (`tblHeader`) y respetar `h_span`.
6. Runs: `bold`, `italic` y `underline`, sin fuente ni tamaño (eso lo pone la plantilla).
7. Verificar: guardar en memoria, reabrir y comparar los tokens del resultado con el DI (reutilizar el validador).
8. Tests: 06_secciones conserva 3 secciones y la página horizontal (cerrar el `xfail` de S3T2), las listas quedan con `numPr` e `ilvl` correctos y los textos no cambian.

**S3T6 – templates_engine v2: formato de la estructura** · M · Backend plantillas
1. Extender el preset (compatible hacia atrás, todos los campos nuevos opcionales):
   `paragraph: {alignment: left|justify, first_line_indent_cm, space_after_pt}`,
   `headings: {h1: {size_pt, bold, align, space_before_pt, space_after_pt, color}, h2, h3, title}`,
   `lists: {indent_cm_per_level}`,
   `tables: {style, header_bold, header_fill, cell_line_spacing}`,
   `callout: {italic, left_indent_cm, fill}` y `page_numbers: bool`.
2. Nuevos módulos `headings.py`, `paragraphs.py`, `lists.py`, `tables.py` y `page_numbers.py`, encadenados en `apply_template` (el orden importa: estilos → párrafos → tablas).
3. Aplicar `keep_with_next` a los títulos y usar el interlineado de celda (1.0) dentro de las tablas.
4. Actualizar `apa7` (sangría de 1.27 cm, títulos centrados y en negrita, número de página) y `reporte` (justificado, encabezado de tabla sombreado). Agregar `tesis` si da tiempo (C).
5. `TemplateConfig`: dejar de rechazar `use_ai=True` y agregar el submodelo `ai` validado.
6. Tests: los 61 actuales siguen en verde y hay pruebas nuevas por cada módulo, sobre un documento generado por el rebuilder v2.

### Fase 2: IA

**S3T7 – Estructurador heurístico (sin IA)** · M · Backend IA
1. `ai_engine/heuristic.py` con `structure(chunk) -> AIChunkOutput` usando los `hints`:
   título si `size_ratio ≥ 1.2` o (`all_bold` y ≤ 12 palabras y sin punto final); nivel por rango de tamaño.
   Viñeta si `starts_with_glyph`, con el nivel según el glifo o `indent_level`.
   Lista ordenada si hay `manual_numbering`.
   Negrita para el prefijo "Clave:" en líneas consecutivas del tipo clave-valor.
2. Quitar los glifos y la numeración manual (cambios permitidos por la regla de integridad).
3. Registrar como `FakeProvider` (`AI_PROVIDER=fake`). Debe poder simular errores de autenticación, límite, timeout y salida inválida para las pruebas.
4. Tests: con `02_headings_mixto` y `05_listas` produce la estructura esperada y pasa el validador.

**S3T8 – Capa de proveedores y proveedor real** · M · Backend IA
1. `ai_engine/providers/base.py`: `LLMProvider.structure(chunk_input) -> ProviderResult(output, usage)` con las excepciones `ProviderAuthError`, `ProviderRateLimitError`, `ProviderUnavailableError` e `InvalidModelOutputError`.
2. `registry.get_provider()` lee `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL` y `AI_TIMEOUT_S` del `.env`. Si falta la key → `AI_NOT_CONFIGURED`.
3. Implementar **un** proveedor real con salida estructurada usando el JSON Schema de S3T3: Gemini (`response_schema`, tiene capa gratuita) o Anthropic (tool use forzado). Lo decide el equipo. Temperatura de 0 a 0.2.
4. Validar la respuesta con Pydantic. Si es inválida → `InvalidModelOutputError`. Backoff exponencial para 429 y 5xx (máximo 3 intentos).
5. Registrar los tokens de entrada y salida. **Nunca** escribir en logs la key ni el texto del documento.
6. Tests con el SDK simulado y prueba `@pytest.mark.live` excluida por defecto. Agregar el SDK a `requirements.txt` y las variables a `.env.example`.

**S3T9 – Prompt v1 y chunker** · M · Backend IA
1. `ai_engine/prompts.py` con `PROMPT_VERSION = "1.0"`. Rol: "eres un maquetador; NO cambias, agregas, quitas ni reordenas palabras". Reglas: cuándo es título y de qué nivel, cuándo agrupar en lista, cuándo convertir en tabla (≥ 2 registros con la misma estructura clave-valor o separadores consistentes), negrita solo para términos o etiquetas clave según el nivel `emphasis`, y `keep` intacto.
2. Defensa contra inyección: el texto va como datos dentro de `<documento>` y el prompt indica que cualquier instrucción dentro del texto se ignora.
3. Incluir 2 ejemplos *few-shot* cortos (título falso y lista con glifos → salida JSON).
4. `ai_engine/chunker.py`: fragmentos de hasta `AI_MAX_CHUNK_CHARS` (8000) sin partir bloques, cortando preferentemente antes de un posible título. Cada fragmento lleva su `heading_path` para que los niveles sean coherentes. `ensure_within_limit` (`AI_MAX_DOC_CHARS` = 60000) lanza `DocumentTooLargeForAI`.
5. Tests: snapshot del prompt; el chunker no pierde, duplica ni reordena bloques.
6. Documentar en `docs/prompts.md` qué cambia en cada versión.

**S3T10 – Validador de integridad y guardrails** · M · Backend IA
1. `ai_engine/validator.py`: implementar la regla de la §5 y devolver un `IntegrityReport` (`ok`, `violations[]` con `src` y tipo).
2. `ai_engine/service.py`: `structure_document(di, options, provider)` → por cada fragmento: proveedor → validador → **1 reintento** incluyendo las violaciones en el mensaje → si sigue fallando, `heuristic.structure` para ese fragmento. Resumen: fragmentos con IA, reintentados, en respaldo, y bloques por tipo creados.
3. Umbrales en `settings` (`AI_MAX_BOLD_RATIO`, `AI_MAX_HEADING_WORDS`).
4. Tests tipo tabla: palabra cambiada, cifra cambiada, palabra agregada, orden alterado, `keep` perdido, glifo quitado (válido), numeración quitada en una lista ordenada (válido), tabla desde "Clave: valor" (válido) y exceso de negrita.

**S3T11 – Orquestador y ejecución asíncrona** · M · Backend API
1. Migración de `ProcessingJob`: `progress_stage`, `progress_done`, `progress_total`, `ai_summary` (JSON), `ai_usage` (JSON), `error_code`, y `structure_original` / `structure_proposed` (JSON; se puede reutilizar `ai_suggestions`).
2. `orchestrator/runner.py`: `enqueue(job_id)` con backends `sync` (tests) y `thread` (desarrollo y demo), elegido con `JOB_RUNNER` en `settings`. (C: backend `celery` con la misma interfaz.)
3. `orchestrator/ai_pipeline.py`: `run_ai_structuring(job_id)` → extraer → `ensure_within_limit` → `structure_document` (actualizando el progreso por fragmento) → guardar el DI propuesto → `review`.
4. `finalize_job(job, revert_ids)`: aplicar las reversiones (los bloques `src` revertidos vuelven a su forma original) → rebuilder v2 → `apply_template` → reabrir para verificar → `done`.
5. Errores: autenticación → `AI_NOT_CONFIGURED` / `AI_UNAVAILABLE`; si todos los fragmentos caen en el respaldo, el proceso sigue (no es error), pero `ai_summary.fallback_only = true`. Cualquier excepción inesperada → `error` + `PROCESSING_ERROR` sin stack trace.
6. Tests con `JOB_RUNNER=sync` y `FakeProvider`.

**S3T12 – Endpoints de IA y revisión** · M · Backend API
1. Extender `format_document_view`: si `use_ai` está activo, validar y responder 202 con `enqueue`; si el job ya está en `processing` → 409 `INVALID_STATE`.
2. Agregar `progress`, `ai_summary` y `error_code` a `document_status_view`.
3. `GET /structure/` (solo en `review`, si no, 409) y `POST /review/` (`accept` con `revert` validado contra los ids existentes, o `reject` → flujo Sprint 2).
4. La descarga solo funciona en `done`, como en el Sprint 2.
5. Probar el flujo completo en Postman con `FakeProvider` usando los fixtures 01, 02 y 05.

### Fase 3: Frontend

**S3T13 – Opciones de IA en ConfigView** · M · Frontend
1. Sección "Estructurar con IA" con un interruptor apagado por defecto. Apagado = flujo idéntico al del Sprint 2.
2. Al activarlo: tipo de documento, casillas para detectar títulos, listas y tablas, y selector de énfasis (ninguno, ligero, medio).
3. Aviso: "El texto de tu documento se enviará a un proveedor de IA. El contenido no se modifica, solo su estructura", con una casilla obligatoria.
4. Armar el payload v1.1. Si la respuesta es 202, navegar a `/processing/:id`.

**S3T14 – ProcessingView (progreso)** · M · Frontend
1. Ruta `/processing/:id` (sobrevive a recargas). Polling de `GET /documents/{id}/` cada 2 s, que se detiene al salir o cuando el estado deja de ser `processing`.
2. Barra con la etapa y "Estructurando fragmento X de Y".
3. Navegación: `review` → `/review/:id`, `done` → `/result`, `error` → mensaje según el `error_code` con los botones "Volver a configuración" y "Reintentar sin IA".

**S3T15 – ReviewView (vista previa de la estructura)** · M · Frontend
1. Ruta `/review/:id`. Carga `GET /structure/` y renderiza el DI propuesto como HTML semántico (`h1–h3`, `ul/ol`, `table`, `blockquote` y `strong`), con interpolación `{{ }}` y **nunca** `v-html`.
2. Vista de dos columnas en escritorio: el texto original plano y la propuesta. Resaltar el tipo de cada bloque con una etiqueta discreta.
3. Resumen arriba: títulos, listas, tablas y negritas detectados, y fragmentos en respaldo heurístico.
4. Botones "Aplicar y generar documento" (`accept`) y "Descartar IA, solo plantilla" (`reject`).
5. (S) "Revertir este bloque" por bloque: lo agrega a `revert[]` y la vista previa lo muestra como el original.
6. Probar con mocks: documento grande (100 bloques) y vista móvil.

**S3T16 – ResultView con resumen de IA** · S · Frontend
1. Mostrar el resumen (`ai_summary`): bloques reestructurados, revertidos y la plantilla aplicada.
2. Mantener la descarga como en el Sprint 2.

### Fase 4: Calidad y evaluación

**S3T17 – Corpus de evaluación (texto plano → estructura esperada)** · M · QA
1. `backend/tests/ai_fixtures/` con 8 documentos inventados o anonimizados: (a) reporte totalmente plano, (b) títulos falsos por tamaño y negrita, (c) listas con glifos y numeración manual en 3 niveles, (d) datos clave-valor que deberían ser tabla, (e) acta con asistentes, acuerdos y fechas, (f) documento con imágenes, tabla existente y 2 secciones (los `keep`), (g) texto con instrucciones incrustadas ("ignora lo anterior y resume") para probar la inyección, (h) documento que ya está bien estructurado (no debe empeorar).
2. `golden.json` por documento: tipo esperado de cada bloque (heading y nivel, list_item y nivel, table, paragraph) y tablas esperadas.
3. Revisión cruzada del golden por un segundo integrante. Entregar en los días 1 a 3.

**S3T18 – Pruebas automatizadas del pipeline** · M · QA + Backend
1. Todo con pytest, `FakeProvider` y `JOB_RUNNER=sync` (sin red y sin costo).
2. Cubrir: esquema, extractor v2, rebuilder v2, templates v2, heurístico, chunker, validador (tabla de casos), proveedores (mapeo de errores y reintentos con mocks), servicio (reintento y respaldo) y endpoints (202, 409, `structure`, `review` accept/revert/reject, download).
3. **Prueba de propiedad de integridad:** para cada fixture y cada `ai_fixture`, los tokens de `extract(original)` == los tokens de `extract(resultado final)` (sin contar los glifos permitidos).
4. Seguridad: con `caplog`, ni la key ni el texto aparecen en los logs.
5. Meta: todo en verde, sin regresiones en las 61 actuales, y reportar la cobertura de `ai_engine` y `docx_engine`.

**S3T19 – Evaluación con modelo real y ajuste del prompt** · S · Backend IA
1. `scripts/evaluate_ai.py`: corre el corpus S3T17 con el proveedor real y lo compara con `golden.json`.
2. Métricas: **integridad = 100 %** (obligatorio), exactitud por tipo de bloque (meta ≥ 85 % en títulos y listas, ≥ 70 % en tablas), % de fragmentos que caen en respaldo (meta ≤ 10 %), inyección ignorada, y tokens y costo estimado por página. Comparar contra el heurístico como línea base.
3. Máximo 3 iteraciones de ajuste (subiendo `PROMPT_VERSION`). Registrar los resultados en `docs/evaluacion-ia.md` (fecha, modelo y versión del prompt).

**S3T20 – Integración E2E, demo y documentación** · M · Todo el equipo
1. Levantar backend y frontend en una máquina distinta siguiendo el README (variables `AI_*` y `JOB_RUNNER`).
2. Flujo completo con el corpus: subir → configurar IA → ver el progreso → revisar → aceptar o revertir → descargar → abrir en Word.
3. Checklist en Word: títulos con estilo real (aparecen en el panel de navegación), listas nativas con sus niveles, tablas con encabezado, imágenes, secciones y tablas originales intactas, plantilla aplicada y **el texto idéntico** al original.
4. Errores: sin key, proveedor caído (simulado), documento demasiado grande y recarga durante el progreso. Verificar que el flujo sin IA del Sprint 2 sigue igual.
5. Actualizar el README y el contrato. Bugs en Jira. Demo de 5 minutos con el "antes y después" de `02_headings_mixto`.

---

## 7. Orden de ejecución y trabajo en paralelo

```mermaid
flowchart LR
    T1["S3T1 Contrato"] --> T12["S3T12 Endpoints"]
    T1 --> T13["S3T13-16 Frontend (con mocks)"]
    T2["S3T2 Pruebas docx"] --> T4["S3T4 Extractor v2"]
    T3["S3T3 Esquema DI"] --> T4
    T3 --> T7["S3T7 Heurístico"]
    T3 --> T8["S3T8 Proveedores"]
    T4 --> T5["S3T5 Rebuilder v2"]
    T5 --> T6["S3T6 Templates v2"]
    T7 --> T10["S3T10 Validador + servicio"]
    T8 --> T10
    T9["S3T9 Prompt + chunker"] --> T10
    T10 --> T11["S3T11 Orquestador"]
    T6 --> T11
    T11 --> T12
    T12 --> T20["S3T20 E2E y demo"]
    T13 --> T20
    T17["S3T17 Corpus"] --> T18["S3T18 Pruebas"]
    T17 --> T19["S3T19 Evaluación"]
    T10 --> T19
    T18 --> T20
```

| Semana | Backend docx / plantillas | Backend IA | Backend API | Frontend | QA |
|---|---|---|---|---|---|
| 1 | S3T2, S3T4, inicio de S3T5 | S3T3, S3T7, S3T9 | S3T1 | Revisión de S3T1, S3T13 con mocks | S3T17 |
| 2 | S3T5, S3T6 | S3T8, S3T10 | S3T11, S3T12 | S3T14, S3T15 | S3T18 (en paralelo) |
| 3 | Bugs y apoyo | S3T19 | Integración | S3T16, pulido | S3T18, S3T20 |

**Hito intermedio (fin de la semana 1):** `extract → heurístico → rebuild v2 → apply_template` funcionando desde un script, sin IA real ni API. Con eso el objetivo del sprint ya se puede demostrar y el resto suma calidad.

---

## 8. Definition of Done del sprint

- [ ] Con `use_ai: true`, un `.docx` plano sale con títulos, listas nativas, tablas y negritas reales, con la plantilla aplicada.
- [ ] **Integridad del 100 %** comprobada por las pruebas en todos los fixtures y `ai_fixtures` (los tokens del original y del resultado son iguales).
- [ ] Imágenes, tablas existentes, secciones y orientación intactas en el modo IA.
- [ ] Revisión antes de generar (aceptar o rechazar; revertir por bloque si se hizo S3T15.5).
- [ ] El flujo sin IA del Sprint 2 no tiene regresiones y las 61 pruebas originales siguen en verde.
- [ ] El sistema funciona sin key real (`FakeProvider` / heurístico) para desarrollo y pruebas.
- [ ] Contrato v1.1, README y `docs/evaluacion-ia.md` actualizados.

## 9. Fuera de alcance (candidatos para el Sprint 4)

- Corrección ortográfica y gramatical con IA (el plan anterior: sugerencias, reconciliador de runs y diff por palabra).
- Que el usuario traiga su propia API key, con cifrado Fernet y limpieza de credenciales.
- Celery + Redis en producción y varios proveedores al mismo tiempo.
- Edición manual de la estructura en la vista previa (cambiar el nivel de un título o el tipo de un bloque).
- Autenticación real, historial por usuario, índice (TOC) automático y portada.

## 10. Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| La IA altera el texto (alucina, "mejora" redacción). | Validador de tokens obligatorio + reintento + respaldo heurístico. El usuario nunca recibe texto alterado. |
| Niveles de título incoherentes entre fragmentos. | `heading_path` en cada fragmento y normalización final de niveles (no saltar de H1 a H3). |
| Numeración nativa de listas compleja en OOXML. | Encapsularla en `lists.py` del rebuilder, con pruebas de XML. Si se complica, usar el respaldo `List Bullet` / `List Number` / `List Bullet 2` / `List Bullet 3`. |
| Costo o límites del proveedor. | `FakeProvider` en desarrollo, límite de gasto en la cuenta y métrica de costo por página en S3T19. |
| Hilos en el servidor de desarrollo (un reinicio deja jobs colgados). | Al arrancar, marcar como `error` los jobs en `processing` con más de 10 min. Celery queda opcional. |
| El equipo se bloquea esperando el contrato. | S3T1 el día 1 y el frontend trabaja con mocks desde el día 2. |
