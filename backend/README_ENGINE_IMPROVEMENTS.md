# PrettyDocs Backend — Mejoras del Motor Documental, Plantillas y Proveedores de IA

Este documento resume los cambios técnicos implementados en el backend para dejar el motor documental (`docx_engine`), el esquema del Documento Intermedio (`common`), las plantillas (`templates_engine`), la capa de proveedores de IA (`ai_engine/providers`) y la API (`api`) listos para la integración completa con IA.

---

## 1. Esquema del Documento Intermedio (`common/document_schema.py` y `docs/schemas/`)

Todos los cambios son **100 % retrocompatibles** con `di.v1` (todos los campos nuevos tienen valores por defecto):

- **`Hints` enriquecido para la IA:**
  - `is_all_caps: bool = False`: detecta texto en MAYÚSCULAS sostenidas (≥ 2 letras), útil para títulos falsos sin cambio de tamaño.
  - `alignment: Optional["left" | "center" | "right" | "justify"] = None`: alineación efectiva (directa o heredada del estilo).
  - `blank_lines_before: int = 0` y `blank_lines_after: int = 0`: cantidad de párrafos vacíos consecutivos inmediatamente antes/después del bloque.
  - `tab_count: int = 0`: cantidad de tabuladores dentro del párrafo (útil para detectar candidatos a tabla).
  - `has_key_value_pattern: bool = False`: detecta patrones `"Clave: valor"` (excluyendo URLs `http://` / `https://`).
- **`SourceBlock.keep_kind`:**
  - Clasificación ligera para bloques opacos `keep`: `"table" | "image" | "section_break" | "empty" | "drawing" | "field" | "footnote" | "hyperlink" | "track_changes" | "other"`.
  - Permite que la IA sepa qué hay en un bloque `keep` (p. ej. una imagen o tabla antes de un pie de figura) sin enviar XML.
- **`TableOutBlock.header_row: bool = True`:**
  - Permite indicar si la primera fila de una tabla generada por IA actúa como encabezado repetible (`w:tblHeader`).
- **JSON Schemas re-exportados:** ejecutando `python common/document_schema.py` se regeneran los 5 esquemas en `docs/schemas/`.

---

## 2. Extractor v2 (`docx_engine/extractor.py`)

- Calcula y rellena todos los nuevos campos de `Hints` y `keep_kind` en `extract_document(path)`.
- Rebobina automáticamente streams binarios (`seek(0)`) cuando recibe `BytesIO` o `FieldFile` de Django antes de abrirlos con `python-docx`.

---

## 3. Rebuilder v2 (`docx_engine/rebuilder.py`)

- **Manejo inteligente de párrafos vacíos (`empty_paragraph`):**
  - `_check_keep_references` ahora permite omitir bloques `keep` cuya única razón sea `empty_paragraph` (sin tokens de contenido), mientras mantiene la exigencia estricta de orden y presencia para todos los demás bloques opacos (imágenes, tablas, saltos de sección, campos, etc.).
  - `rebuild_document(original_path, structured_di, *, collapse_empty_paragraphs: bool = False)`: el flag opcional `collapse_empty_paragraphs=True` elimina automáticamente los `empty_paragraph` redundantes para que `templates_engine v2` controle el espaciado limpiamente. Por defecto es `False` para preservar el roundtrip exacto.
- **Acabado editorial en tablas generadas por IA (`_add_structured_table`):**
  - Respeta `block.header_row` antes de insertar `<w:tblHeader/>`.
  - Aplica ancho al 100 % (`<w:tblW w:w="5000" w:type="pct"/>`), márgenes internos de celda (`<w:tblCellMar>`) y `<w:cantSplit/>` en cada fila para evitar que una fila se parta entre dos páginas.
- Rebobina automáticamente streams binarios (`seek(0)`) antes de abrir el documento original.

---

## 4. Templates Engine v2 y API (`templates_engine/`, `api/views.py`)

- **`templates_engine/config.py`:**
  - Corregido el bug donde `TemplateConfig(**preset.model_dump())` activaba `use_ai=True` por tener `"ai": None` en el diccionario.
  - `AIConfig` sincroniza el alias `detect_headings` ↔ `detect_titles` y soporta valores de `api-contract.md` v1.1 (`reporte`, `none|light|medium`) manteniendo compatibilidad con el frontend actual (`detect_titles`, `ninguno|ligero|medio`).
- **`templates_engine/typography.py`:** incluye el estilo `Title` en `target_styles` con limpieza de atributos de tema OOXML.
- **`templates_engine/applier.py` y `margins.py`:** soportan `margins_cm` parciales sin lanzar `KeyError`.
- **`templates_engine/paragraphs.py` y `tables.py`:** validan colores hex (`^[0-9A-Fa-f]{6}$`) antes de construir `w:shd`.
- **`templates_engine/page_numbers.py`:** conserva encabezados existentes con texto en lugar de sobrescribir su alineación.
- **`api/views.py`:**
  - `POST /api/documents/` devuelve también `size_bytes` y `uploaded_at`.
  - `POST /api/documents/{id}/format/` persiste `job.use_ai = config.use_ai`, limpia `job.error_message` en reintentos, lee `original_file` con cierre seguro de handle (`with ... open('rb')`) y devuelve `document_id`, `job_id`, `status`, `config` y `finished_at`.

---

## 5. Capa de Proveedores de IA (`ai_engine/providers/`)

- Interfaz `LLMProvider` (`base.py`), `OpenRouterProvider` (`openrouter.py`, SDK `openai`, JSON Schema de S3T3, `temperature` en `[0.0, 0.2]`, validación estricta Pydantic, reintentos exponenciales hasta 3 intentos en 429/5xx, cero filtración de secrets/texto en logs) y fábrica `get_provider()` (`registry.py`).
- Configuración en `backend/.env` / `backend/.env.example`: `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `AI_TIMEOUT_S`, `AI_BASE_URL`, `AI_TEMPERATURE`.
- Pruebas offline en `tests/test_ai_providers.py` + prueba real marcada `@pytest.mark.live` (excluida por defecto en `pytest.ini`; ejecutar con `pytest tests/test_ai_providers.py -m live -s`).

---

## 6. Comandos de verificación

```powershell
# Re-exportar JSON Schemas a docs/schemas/
cd backend
.\venv\Scripts\python.exe common/document_schema.py

# Suite completa de backend (excluye live y e2e playwright)
.\venv\Scripts\pytest.exe --ignore=tests/test_e2e_web.py -q

# Prueba real contra OpenRouter (requiere AI_API_KEY en backend/.env)
.\venv\Scripts\pytest.exe tests/test_ai_providers.py -m live -s
```
