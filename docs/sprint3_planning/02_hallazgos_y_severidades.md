# Registro Detallado de Hallazgos y Severidades Técnicas

Este documento cataloga y analiza minuciosamente todas las fallas, inconsistencias y vulnerabilidades identificadas en el proyecto al cierre del Sprint 2 y durante la preparación del Sprint 3.

---

## 1. Matriz General de Hallazgos

| ID | Hallazgo / Defecto | Severidad | Componente Afectado | Impacto en el Sistema | Estado |
| :--- | :--- | :---: | :--- | :--- | :---: |
| **HALL-01** | Regresión por Merge: `document_detail_view` inexistente y ruta colisionada | **Crítica (Bloqueante)** | [`backend/documents/urls.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/urls.py) | Impide el arranque del servidor Django y la ejecución de la suite de pruebas. | 🔴 Abierto |
| **HALL-02** | Ruptura de Contrato en `GET /api/documents/{id}/` | **Crítica (Bloqueante)** | [`backend/documents/views.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/views.py) | Rompe la suite de tests de API (`test_api.py`) y deja al frontend sin `download_url`. | 🔴 Abierto |
| **HALL-03** | Discrepancia de Ruta y Payload en Presets (`/api/templates/`) | **Crítica** | [`backend/core/urls.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/core/urls.py) / [`config.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/templates_engine/config.py) | El frontend recibe 404 o `TypeError` al consultar plantillas predeterminadas. | 🔴 Abierto |
| **HALL-04** | Normalización incompleta de tamaño en runs directos (`PRETTY-BUG-03`) | **Alta** | [`backend/documents/templates_engine/typography.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/templates_engine/typography.py) | Textos con formato hardcodeado en tablas y párrafos no adoptan el tamaño configurado. | 🔴 Abierto |
| **HALL-05** | Formato de Respuesta de Errores Incompatible con Frontend | **Media** | [`backend/documents/views.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/views.py) | El frontend muestra mensajes genéricos al recibir errores del backend. | 🔴 Abierto |
| **HALL-06** | Codificación binaria en `backend/requirements.txt` | **Media** | [`backend/requirements.txt`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/requirements.txt) | Dificulta la instalación limpia y el versionado Git en entornos CI/CD. | 🔴 Abierto |
| **HALL-07** | `UserWarning` en resolución de estilos (`PRETTY-BUG-06`) | **Baja** | [`backend/documents/templates_engine/spacing.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/templates_engine/spacing.py) | Contaminación de logs de prueba con advertencias de python-docx. | 🟡 Abierto |

---

## 2. Análisis Detallado por Hallazgo

### 🔴 HALL-01: Regresión por Merge: `document_detail_view` inexistente y ruta colisionada

- **Severidad:** **Crítica / Bloqueante**
- **Archivos Afectados:**
  - [`backend/documents/urls.py` (Líneas 6 y 16-18)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/urls.py#L6-L18)
  - [`backend/documents/views.py` (Línea 156)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/views.py#L156)
- **Causa Raíz:**
  Al resolver el merge del PR #28 (`cc42cdd`), se fusionaron dos ramas que abordaron la consulta del documento con nombres distintos. En `urls.py` se mantuvo la importación de `document_detail_view` y adicionalmente se importó `document_status_view`. Sin embargo, en `views.py` solo se conservó la función `document_status_view`.
  
  Código actual en [`backend/documents/urls.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/urls.py):
  ```python
  from .views import (
      extract_text_view,
      upload_document_view,
      format_document_view,
      document_detail_view,     # <-- NO EXISTE EN views.py
      download_document_view,
      document_status_view,
      list_templates_view
  )

  urlpatterns = [
      path('', upload_document_view, name='upload_document_root'),
      path('upload/', upload_document_view, name='upload_document'),
      path('extract/', extract_text_view, name='extract_text'),
      path('<int:id>/', document_detail_view, name='document_detail'),     # <-- Ruta 1
      path('<int:id>/format/', format_document_view, name='format_document'),
      path('<int:id>/', document_status_view, name='document_status'),     # <-- Ruta 2 (Duplicada)
      path('<int:id>/download/', download_document_view, name='download_document'),
      path('templates/', list_templates_view, name='list_templates'),
  ]
  ```
- **Consecuencia Técnica:**
  Al levantar el servidor Django o ejecutar `pytest`, se genera la siguiente excepción fatal:
  ```text
  ImportError: cannot import name 'document_detail_view' from 'documents.views'
  ```
- **Solución Requerida:**
  1. Eliminar la ruta duplicada en [`urls.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/urls.py).
  2. Implementar una única función en [`views.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/views.py) que satisfaga completamente el contrato de API bajo el nombre acordado (`document_detail_view`).

---

### 🔴 HALL-02: Ruptura de Contrato en `GET /api/documents/{id}/`

- **Severidad:** **Crítica / Bloqueante**
- **Archivos Afectados:**
  - [`backend/documents/views.py` (Líneas 156-176)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/views.py#L156-L176)
  - [`api-contract.md` (Sección 6.3)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/api-contract.md#L261-L288)
  - [`backend/tests/test_api.py` (Líneas 348-356)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/tests/test_api.py#L348-L356)
- **Causa Raíz:**
  La función `document_status_view` implementada en el PR #28 omite campos declarados obligatorios en el contrato de API:
  
  *Implementación defectuosa actual:*
  ```python
  return Response({
      "status": job.status,
      "config": job.config,
      "original_name": document.original_name,
      "error_message": job.error_message,
      "started_at": job.started_at,
      "finished_at": job.finished_at
  }, status=status.HTTP_200_OK)
  ```
  
  *Esquema acordado en el contrato:*
  ```json
  {
    "document_id": 12,
    "job_id": 12,
    "original_name": "tesis_capitulo1.docx",
    "size_bytes": 248913,
    "uploaded_at": "2026-10-08T15:30:00Z",
    "status": "done",
    "config": { ... },
    "use_ai": false,
    "error_message": null,
    "started_at": "2026-10-08T15:30:01Z",
    "finished_at": "2026-10-08T15:30:04Z",
    "download_url": "/api/documents/12/download/"
  }
  ```
- **Consecuencia Técnica:**
  - En la suite de pruebas [`test_api.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/tests/test_api.py), el test de integración `test_complete_flow_upload_format_status_download_and_verify` falla en la aserción de `download_url` y `document_id`.
  - En el frontend, el helper de descarga en [`ResultView.vue`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/frontend/src/views/ResultView.vue#L17-L24) depende de `document_id` para construir la URL de descarga directa.
- **Solución Requerida:**
  Restituir el retorno completo de atributos del documento y del job, calculando dinámicamente `download_url` únicamente cuando `job.status == 'done'`.

---

### 🔴 HALL-03: Discrepancia de Ruta y Payload en Presets (`/api/templates/`)

- **Severidad:** **Crítica**
- **Archivos Afectados:**
  - [`backend/core/urls.py` (Línea 22)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/core/urls.py#L22)
  - [`backend/documents/templates_engine/config.py` (Líneas 58-61)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/templates_engine/config.py#L58-L61)
  - [`frontend/src/services/api.js` (Línea 172)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/frontend/src/services/api.js#L172)
  - [`frontend/src/views/ConfigView.vue` (Líneas 164-167)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/frontend/src/views/ConfigView.vue#L164-L167)
- **Causa Raíz:**
  1. **Enrutamiento:** `core/urls.py` incluye a `documents.urls` bajo el prefijo `api/documents/`. Por lo tanto, la ruta definida `path('templates/', ...)` se expone en `http://localhost:8000/api/documents/templates/`. El contrato (§6.5) y el cliente frontend de Axios consultan `GET /api/templates/`, generando un error `404 Not Found`.
  2. **Estructura del Payload:** La función `list_presets()` en `config.py` simplemente lista los nombres de archivo `.json`:
     ```python
     def list_presets():
         return [f.replace('.json', '') for f in os.listdir(PRESETS_DIR) if f.endswith('.json')]
     ```
     Retornando `["apa7", "personalizado", "reporte"]`.
     Sin embargo, el frontend procesa:
     ```javascript
     const response = await apiClient.get('/templates/')
     return response.data.presets  // <-- UNDEFINED
     ```
     Y en [`ConfigView.vue`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/frontend/src/views/ConfigView.vue#L121-L125):
     ```typescript
     function applyPreset(preset: Preset) {
       const c = preset.config  // TypeError: Cannot read properties of undefined
     ```
- **Solución Requerida:**
  1. Enrutar `api/templates/` directamente en [`backend/core/urls.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/core/urls.py).
  2. Cargar los metadatos completos de cada preset JSON (`id`, `name`, `description`, `config` con `margins_cm`, `font_family`, `font_size_pt`, `line_spacing`) y retornar `{"presets": [...]}`.

---

### 🟠 HALL-04: Normalización incompleta de tamaño en runs directos (`PRETTY-BUG-03`)

- **Severidad:** **Alta**
- **Archivo Afectado:** [`backend/documents/templates_engine/typography.py` (Líneas 47-75)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/templates_engine/typography.py#L47-L75)
- **Causa Raíz:**
  En documentos con formato heterogéneo o "sucio", los usuarios aplican estilos directos a palabras o párrafos específicos (run-level formatting). La implementación actual de `apply_typography` recorre los runs y asigna el nombre de fuente (`run.font.name = font_name`) y modifica `w:rFonts`, pero **nunca normaliza el tamaño `run.font.size`**.
- **Consecuencia Técnica:**
  En la suite [`backend/tests/test_templates_engine.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/tests/test_templates_engine.py#L154-L198):
  ```python
  def test_typography_runs_no_divergent_font_or_size(loaded_doc, sample_config):
      # ...
      if run.font.size is not None:
          assert round(run.font.size.pt, 1) == expected_size
  ```
  Al evaluar los fixtures [`02_headings_mixto.docx`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/tests/fixtures/02_headings_mixto.docx) y [`04_tabla_imagen.docx`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/tests/fixtures/04_tabla_imagen.docx), los runs que tenían tamaños explícitos (ej. 14 pt en cuerpo o 9 pt en celdas de tabla) fallan la aserción porque no se ajustaron al estándar configurado (12 pt).
- **Solución Requerida:**
  En `typography.py`, asignar `run.font.size = Pt(font_size)` (o el tamaño correspondiente si pertenece a un Heading) o bien remover el override directo en `run._r.rPr` para que herede limpiamente del estilo de párrafo normalizado.

---

### 🟡 HALL-05: Formato de Respuesta de Errores Incompatible con Frontend

- **Severidad:** **Media**
- **Archivos Afectados:**
  - [`backend/documents/views.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/views.py#L61)
  - [`frontend/src/services/api.js` (Líneas 13-24)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/frontend/src/services/api.js#L13-L24)
- **Causa Raíz:**
  El interceptor de Axios espera un objeto de error estructurado:
  ```javascript
  const apiError = error.response?.data?.error
  const formattedError = {
    code: apiError?.code || error.code || 'ERR_UNKNOWN',
    message: apiError?.message || error.message || 'Ocurrió un error inesperado',
    details: apiError?.details || {}
  }
  ```
  En el backend, varias vistas retornan respuestas como:
  ```python
  return Response({"error": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
  ```
  Aquí `apiError` es el string `"NOT_FOUND"`, por lo que `apiError?.code` y `apiError?.message` resultan `undefined`.
- **Solución Requerida:**
  Crear una función auxiliar `api_error_response(code, message, status_code, details=None)` que asegure el cumplimiento del esquema `{ "error": { "code": code, "message": message, "details": details } }`.

---

### 🟡 HALL-06: Codificación binaria en `backend/requirements.txt`

- **Severidad:** **Media**
- **Archivo Afectado:** [`backend/requirements.txt`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/requirements.txt)
- **Causa Raíz:**
  El archivo fue generado en PowerShell con redirección estándar (`>`), la cual en ciertas versiones guarda por defecto en codificación UTF-16 LE con BOM.
- **Consecuencia Técnica:**
  - `git diff` no muestra las líneas modificadas sino `"Binary files differ"`.
  - En contenedores Linux (Docker) o runners de GitHub Actions, `pip install -r requirements.txt` puede arrojar errores de caracteres ilegibles (`UnicodeDecodeError`).
- **Solución Requerida:**
  Convertir y guardar el archivo en UTF-8 estándar sin BOM.

---

### 🟢 HALL-07: `UserWarning` en resolución de estilos (`PRETTY-BUG-06`)

- **Severidad:** **Baja**
- **Archivo Afectado:** [`backend/documents/templates_engine/spacing.py` (Líneas 23-26)](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/templates_engine/spacing.py#L23-L26)
- **Causa Raíz:**
  python-docx 1.2.0 introdujo advertencias cuando se accede al diccionario de estilos pasando nombres de estilo en inglés que pueden tener variantes localizadas en diferentes idiomas del paquete Office.
- **Solución Requerida:**
  Silenciar controladamente la advertencia o acceder mediante `doc.styles.get_style_id('Normal', ...)` para garantizar compatibilidad internacional.
