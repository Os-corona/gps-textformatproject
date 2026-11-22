# Documentación de Prompts de IA — PrettyDocs (`docs/prompts.md`)

Este documento registra el diseño, las reglas, las defensas de seguridad, los ejemplos *few-shot* y el historial de versiones del prompt utilizado por `ai_engine` (`backend/ai_engine/prompts.py`) junto con el divisor de fragmentos (`backend/ai_engine/chunker.py`).

---

## 1. Principios de Diseño

1. **Separación estricta entre estructura y redacción:** El modelo de lenguaje actúa únicamente como **maquetador estructural** sobre el Documento Intermedio (`di.v1`). Tiene prohibido alterar, agregar, omitir o reordenar palabras, cifras o signos de puntuación significativos.
2. **Defensa contra *Prompt Injection*:** El JSON del fragmento (`AIChunkInput`) se envuelve siempre entre etiquetas `<documento>...</documento>`. El prompt del sistema y el mensaje de usuario instruyen explícitamente al modelo a tratar todo el contenido interior como datos pasivos e ignorar cualquier orden, instrucción o intento de cambio de rol dentro del texto del usuario.
3. **Coherencia jerárquica entre fragmentos (`heading_path`):** Los documentos largos se dividen en fragmentos de hasta `AI_MAX_CHUNK_CHARS` (8,000 caracteres) sin partir bloques a la mitad y cortando preferentemente antes de un posible título. Cada fragmento incluye la lista `heading_path` con la ruta de títulos activa (conservando tanto el título principal de nivel 0 como la jerarquía H1–H6 y respetando cualquier `heading_path` inicial presente en un `AIChunkInput`) para evitar saltos inválidos de nivel.
4. **Trazabilidad y marcaje de elementos generados (`"generated": true`):**
   - Cada bloque de salida referencia en `src` los IDs de los bloques de origen (`["b1", ...]`).
   - Si la IA crea un subtítulo (`heading`) o un encabezado de tabla (celdas de `header_row`, nunca el bloque completo `table`) que no existía en el texto original, **debe marcarlo con `"generated": true`**.
   - Los párrafos normales (`"type": "paragraph"`) **nunca** llevan el campo `"generated"` y jamás pueden contener texto inventado.

---

## 2. Reglas de Estructuración (`PROMPT_VERSION = "1.0"`)

| Elemento | Tipo en `AIChunkOutput` | Regla aplicada en Prompt v1.0 |
| :--- | :--- | :--- |
| **Títulos y Subtítulos** | `heading` (`level` 0–3) | Detecta títulos falsos (≤ 20 palabras, `ends_with_period: false`, `size_ratio >= 1.2`, `all_bold: true` o `is_all_caps: true`). Respeta `heading_path` sin saltar niveles jerárquicos. Si se crea un subtítulo no existente en el texto, se marca con `"generated": true`. |
| **Listas** | `list_item` (`level` 0–8, `is_numbered`) | Convierte párrafos con glifos iniciales (`•`, `·`, `◦`, `▪`, `-`, `*`) en `is_numbered: false` eliminando el glifo. Convierte numeración manual (`1.`, `a)`, `I.`) en `is_numbered: true` eliminando el prefijo manual. |
| **Tablas** | `table` (`header_row`, `rows`) | Agrupa secuencias de ≥ 2 registros consecutivos con estructura clave-valor (`Clave: valor`) o separadores consistentes (`\|`, `\t`, `:`). Exige filas rectangulares (misma suma de `h_span`). Si el encabezado es generado por la IA, sus celdas llevan `"generated": true`. |
| **Énfasis (Negritas)** | `Run.bold = true` | Gobernado por `emphasis`:<br>- `none` / `ninguno`: no agrega negritas nuevas (0 %).<br>- `light` / `ligero`: solo etiquetas o prefijos clave (`"Clave:"`), ≤ 15 % de palabras.<br>- `medium` / `medio`: etiquetas clave y conceptos principales, ≤ 30 % de palabras. |
| **Bloques Opacos** | `keep` (`id`, `src`) | Imágenes, tablas nativas existentes, saltos de sección y campos (`type: "keep"`) se conservan intactos en su misma posición relativa. |
| **Párrafos Normales** | `paragraph` (`runs`, `src`) | Conservan el texto íntegro palabra por palabra. **Nunca** incluyen el campo `"generated"`. |

---

## 3. Ejemplos *Few-Shot* Incluidos en el Prompt v1.0

### Ejemplo 1: Título falso detectado por tamaño y negrita
- **Entrada (`<documento>`):** Bloque `b1` con `"text": "1. RESUMEN EJECUTIVO"`, `all_bold: true`, `size_ratio: 1.45`, `ends_with_period: false`, seguido de un párrafo normal `b2`.
- **Salida (`AIChunkOutput`):** `b1` clasificado como `{"type": "heading", "id": "b1", "src": ["b1"], "level": 1, "runs": [{"text": "1. RESUMEN EJECUTIVO"}]}` y `b2` como `paragraph`.

### Ejemplo 2: Lista con glifos convertida a `list_item` (adaptada según `emphasis`)
- **Entrada (`<documento>`):**
  - Bloque `b10` (9 palabras): `"• Norte: crecimiento sostenido de ventas durante todo el trimestre."` (`indent_level: 0`).
  - Bloque `b11` (9 palabras): `"◦ Sur: operación estable sin incidencias operativas durante el periodo."` (`indent_level: 1`).
- **Salida (`AIChunkOutput`):** Bloques `list_item` con `is_numbered: false`, niveles `0` y `1` respectivamente, sin los glifos `•` ni `◦`, y con negritas ajustadas dinámicamente al nivel de `emphasis`:
  - `none` / `ninguno`: 0 palabras en negrita (0 %).
  - `light` / `ligero`: 1 de 9 palabras en negrita (`"Norte:"` / `"Sur:"`, 11.1 % ≤ 15 %).
  - `medium` / `medio`: 2 de 9 palabras en negrita (`"Norte:"` + `"crecimiento"` / `"Sur:"` + `"operación"`, 22.2 % ≤ 30 %).

---

## 4. Límites y Fragmentación (`ai_engine/chunker.py`)

- **`AI_MAX_DOC_CHARS = 60000`**: Límite máximo de caracteres por documento para estructuración con IA. Validado por `ensure_within_limit()`, que lanza `DocumentTooLargeForAI` (`error_code = "DOCUMENT_TOO_LARGE_FOR_AI"`) si se supera.
- **`AI_MAX_CHUNK_CHARS = 8000`**: Tamaño máximo estricto en caracteres por fragmento (`AIChunkInput`).
- **Bloques individuales mayores a `AI_MAX_CHUNK_CHARS`**: Como ningún `SourceBlock` puede partirse a la mitad y ningún fragmento puede superar `AI_MAX_CHUNK_CHARS`, cualquier bloque individual que exceda 8,000 caracteres se rechaza explícitamente lanzando `BlockTooLargeForAI` (subclase de `DocumentTooLargeForAI` con `error_code = "DOCUMENT_TOO_LARGE_FOR_AI"`).
- **Política de corte y conservación de `heading_path`:**
  - Cuando un fragmento alcanza el límite, el `chunker` busca hacia atrás el último posible título o corta justo antes de un título entrante para que cada sección viaje junto con sus párrafos hijos.
  - Se propaga `heading_path` de un fragmento al siguiente respetando el nivel `0` (`Title`) como raíz de los encabezados `H1..H6` (`level` 1..6) y conservando cualquier `heading_path` inicial recibido en un `AIChunkInput`.
  - Cada fragmento guarda en `metadata.heading_levels` los niveles de su `heading_path`, en el mismo orden, para conservar la jerarquía al serializarlo y volver a dividirlo, incluso con títulos sin numeración.

---

## 5. Historial de Versiones del Prompt

| Versión | Fecha | Tarea | Cambios realizados |
| :--- | :--- | :--- | :--- |
| **`1.0`** | Sprint 3 | **S3T17 / S3T9** | Versión inicial del prompt de maquetación estructural sobre `di.v1`. Incluye rol estricto de no alteración textual, reglas para `heading`, `list_item`, `table`, `emphasis`, preservación de `keep`, regla de `"generated": true` para subtítulos o encabezados de tabla creados por la IA (prohibido en párrafos normales), protección `<documento>` contra *prompt injection* y 2 ejemplos *few-shot* adaptados al nivel de `emphasis`. |

## Integridad de la salida (S3T18)

El campo `generated` solo se admite en subtítulos y celdas de encabezado; no en el bloque completo de una tabla. El servicio y sus umbrales se documentan en [ai-integrity.md](ai-integrity.md).
