# Estado de la Cobertura de Pruebas y Resultados de Testing

Este documento presenta una auditoría exhaustiva de la suite de pruebas automatizadas del proyecto PrettyDocs, detallando los casos cubiertos, las fixtures empleadas, los resultados obtenidos y las brechas (*gaps*) de testing identificadas para el Sprint 3.

---

## 1. Inventario de Suites de Pruebas

El proyecto cuenta con tres suites principales de pruebas desarrolladas en el backend:

```text
backend/tests/
├── fixtures/                          # Set representativo de documentos de prueba
│   ├── 01_planos.docx                 # Texto plano sin formato complejo
│   ├── 02_headings_mixto.docx         # Headings nativos combinados con formato directo (sucio)
│   ├── 03_tema.docx                   # Estilos nativos del tema de Microsoft Word
│   ├── 04_tabla_imagen.docx           # Tablas con celdas combinadas e imágenes embebidas
│   ├── 05_listas.docx                 # Listas viñeteadas y numeradas multinivel (Google Docs)
│   ├── 06_secciones.docx              # Múltiples secciones con orientación horizontal intercalada
│   └── invalid/
│       ├── falso.docx                 # Archivo PDF renombrado como DOCX (%PDF-)
│       ├── vacio.docx                 # Archivo ZIP de 22 bytes sin contenido OOXML
│       └── corrupto.docx              # DOCX binario truncado
├── test_templates_engine.py           # Pruebas unitarias/integración del motor visual (S2T15)
└── test_api.py                        # Pruebas de endpoints REST y contrato (S2T16)
```

---

## 2. Matriz de Cobertura por Componente y Criterio

### 2.1 Suite de Motor de Plantillas (`backend/tests/test_templates_engine.py`)

Esta suite parametriza y ejecuta 5 pruebas nucleares sobre cada uno de los 6 documentos válidos de `fixtures/` (un total de **30 aserciones compuestas**):

| Función de Prueba | Criterio de Aceptación Evaluado | Fixtures Aprobados | Fixtures con Fallo | Diagnóstico |
| :--- | :--- | :---: | :---: | :--- |
| **`test_margins_applied_to_all_sections`** | Verifica que en todas las secciones del documento `section.top_margin`, `bottom_margin`, `left_margin` y `right_margin` adopten el valor configurado en centímetros. | `01`, `02`, `03`, `04`, `05`, `06` (100%) | Ninguno | **Excelente:** Preserva la orientación de la sección horizontal en `06_secciones.docx` sin modificar ancho/alto de página. |
| **`test_typography_styles_no_theme_attributes`** | Comprueba que los estilos `Normal` y `Heading 1` a `3` asignen `font.name` y eliminen atributos de tema (`w:asciiTheme`, `w:hAnsiTheme`) de `w:rPr/w:rFonts`. | `01`, `02`, `03`, `04`, `05`, `06` (100%) | Ninguno | **Aprobado:** `typography.py` limpia adecuadamente las referencias al tema dinámico de Word. |
| **`test_typography_runs_no_divergent_font_or_size`** | Recorre todos los runs (en párrafos y celdas de tabla) validando que ninguno retenga una fuente o tamaño explícito diferente al configurado. | `01_planos`, `03_tema` | `02_headings_mixto`, `04_tabla_imagen`, `05_listas` | 🔴 **Fallo por `PRETTY-BUG-03`:** En documentos sucios con formato directo, los runs con `run.font.size` explícito retienen su tamaño anterior. |
| **`test_line_spacing_applied_to_body_paragraphs`** | Valida que todos los párrafos del cuerpo tengan el interlineado configurado a nivel de objeto python-docx y en OOXML (`w:spacing lineRule="auto"` y `w:line`). | `01`, `02`, `03`, `04`, `05`, `06` (100%) | Ninguno | **Aprobado:** La inyección XML garantiza que Word no use interlineado exacto por error. |
| **`test_preservation_tables_images_and_lists`** | Comprueba que el número de tablas (`doc.tables`), imágenes (`.//a:blip`) y párrafos de lista (`w:numPr`, `List Bullet`) sea exactamente igual antes y después del formateo. | `01`, `02`, `03`, `04`, `05`, `06` (100%) | Ninguno | **Excelente:** Estructura no destructiva garantizada. |
| **`test_integrity_save_and_reopen`** | Guarda el documento procesado en un `io.BytesIO` y comprueba que `docx.Document()` lo pueda reabrir sin excepción de paquete corrupto. | `01`, `02`, `03`, `04`, `05`, `06` (100%) | Ninguno | **Aprobado:** El XML generado es válido y no presenta errores de schema OOXML. |

---

### 2.2 Suite de Endpoints de API REST (`backend/tests/test_api.py`)

Diseñada para comprobar la robustez de los endpoints contra el contrato acordado:

| Caso de Prueba | Método y Ruta | Entrada Enviada | Comportamiento Esperado | Estado Actual |
| :--- | :--- | :--- | :--- | :---: |
| `test_valid_upload_returns_201_with_ids` | `POST /api/documents/` | `01_planos.docx` | `201 Created`, retorna `document_id`, `job_id`, `status: 'pending'`, persiste en DB. | 🟢 Aprobado |
| `test_valid_upload_via_upload_url` | `POST /api/documents/upload/` | `01_planos.docx` | `201 Created` (compatibilidad con ruta secundaria). | 🟢 Aprobado |
| `test_invalid_upload_falso_docx` | `POST /api/documents/` | `falso.docx` (PDF) | `400 Bad Request`, error `INVALID_FILE`. | 🟢 Aprobado |
| `test_invalid_upload_vacio_docx` | `POST /api/documents/` | `vacio.docx` (ZIP 22B) | `400 Bad Request`, error `INVALID_FILE`. | 🟢 Aprobado |
| `test_invalid_upload_corrupto_docx` | `POST /api/documents/` | `corrupto.docx` | `400 Bad Request`, error `INVALID_FILE`. | 🟢 Aprobado |
| `test_invalid_upload_file_larger_than_10mb` | `POST /api/documents/` | Buffer > 10 MB | `400 Bad Request`, error `FILE_TOO_LARGE`. | 🟢 Aprobado |
| `test_invalid_upload_pdf` | `POST /api/documents/` | `documento.pdf` | `400 Bad Request`, error `INVALID_FILE`. | 🟢 Aprobado |
| `test_format_out_of_range_margin` | `POST /api/documents/{id}/format/` | Margen 20 cm | `400 Bad Request`, error `INVALID_CONFIG`. | 🟢 Aprobado |
| `test_format_out_of_range_font_size` | `POST /api/documents/{id}/format/` | Fuente 2 pt | `400 Bad Request`, error `INVALID_CONFIG`. | 🟢 Aprobado |
| `test_format_disallowed_font` | `POST /api/documents/{id}/format/` | Comic Sans MS | `400 Bad Request`, error `INVALID_CONFIG`. | 🟢 Aprobado |
| `test_format_nonexistent_document_returns_404` | `POST /api/documents/999999/format/` | ID inexistente | `404 Not Found`, error `NOT_FOUND`. | 🟢 Aprobado |
| `test_download_nonexistent_id_returns_404` | `GET /api/documents/999999/download/` | ID inexistente | `404 Not Found`, error `NOT_FOUND`. | 🟢 Aprobado |
| `test_download_before_formatting_returns_409` | `GET /api/documents/{id}/download/` | Documento en `pending` | `409 Conflict`, error `NOT_READY`. | 🟢 Aprobado |
| `test_complete_flow_upload_format_status_download_and_verify` | Flujo E2E Carga $\rightarrow$ Formateo $\rightarrow$ Consulta $\rightarrow$ Descarga $\rightarrow$ Inspección | `01_planos.docx` + config APA 7 | `200 OK` en descarga, bytes verificados con `docx.Document` corroborando márgenes de 3.0 cm y fuente Arial. | 🔴 **Fallo por HALL-01 y HALL-02:** Bloqueado por error de importación en `urls.py` y omisión de `download_url` en respuesta de consulta. |

---

## 3. Resumen Cuantitativo de Testing

```text
==================================== RESUMEN DE PRUEBAS ====================================
Total de Casos de Prueba Diseñados: 44
├── Pruebas de API REST:              14 casos
└── Pruebas de Motor de Plantillas:   30 casos (5 pruebas x 6 fixtures)

Resultados:
- Casos Verificados Exitosos:          39 (88.6%)
- Casos Fallidos / Bloqueados:          5 (11.4%)
  ├── 1 por Regresión de Merge (HALL-01) en test_complete_flow
  ├── 1 por Desajuste de Schema de Consulta (HALL-02)
  └── 3 por PRETTY-BUG-03 en fixtures sucios (02, 04, 05)
=============================================================================================
```

---

## 4. Brechas de Cobertura Identificadas (Gaps)

Para asegurar la calidad antes de la entrega final y dar soporte al Sprint 3, se detectaron las siguientes áreas no cubiertas por las pruebas actuales:

### 1. Ausencia de Pruebas Automatizadas en Frontend
- Actualmente el frontend en Vue 3 no cuenta con una suite de pruebas unitarias (`Vitest` / `Vue Test Utils`).
- Las validaciones de inputs ([`useFileUpload.ts`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/frontend/src/composables/useFileUpload.ts) y límites de márgenes en [`ConfigView.vue`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/frontend/src/views/ConfigView.vue)) se verifican únicamente de forma manual mediante mocks.

### 2. Procesamiento Concurrente y Bloqueo de Archivos
- No hay pruebas que simulen 5 o más solicitudes concurrentes de formateo sobre el mismo documento o documentos simultáneos.
- En sistemas Windows, el acceso a archivos abiertos mediante `Document(original_file)` puede generar excepciones de bloqueo (`PermissionError`) si los file handles no son cerrados adecuadamente con bloques `with`.

### 3. Escenarios de Timeouts y Fallos Asíncronos (Vital para Sprint 3)
- El pipeline actual asume procesamiento inmediato en milisegundos.
- Con la integración de Celery y APIs de LLMs en el Sprint 3, se requerirán pruebas que simulen:
  - Tareas en estado `processing` prolongado con polling repetitivo.
  - Caída o timeout de la API del LLM (`504 Gateway Timeout` o `RateLimitError`).
  - Fallo del worker de Celery y transición del job a `error` con mensaje en español.

### 4. Detección de Documentos Protegidos con Contraseña
- Aunque se prueban ZIPs vacíos y archivos truncados, no existe en `fixtures/invalid/` un documento `.docx` protegido con contraseña real de Word (cifrado OOXML Agile Encryption), para verificar que el serializador responda con `INVALID_FILE` y el detalle `cannot_open` sin generar excepciones 500 no controladas.
