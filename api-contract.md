# PrettyDocs — Contrato de API (Sprint 2)

| | |
|---|---|
| **Versión** | 1.0 — borrador para aprobación |
| **Fecha** | 08/10/2026 |
| **Alcance** | Sprint 2: formateo visual de un `.docx` (márgenes, tipografía, interlineado) sin IA |
| **Autores** | Oscar Alejandro Arias Corona, Luis Dorian Ferreira Calderon |
| **Aprobación requerida de** | Alfonso Maron Fernandez Garibay (frontend) y Luis Dorian Ferreira Calderon (backend) |

Este documento es el acuerdo entre frontend y backend. Una vez aprobado, **solo se modifica con acuerdo de ambas partes** y dejando constancia en la sección [Control de cambios](#11-control-de-cambios).

---

## 1. Decisiones del sprint

| Tema | Decisión |
|---|---|
| Procesamiento | **Síncrono.** `POST .../format/` responde cuando el documento ya está listo. Celery se incorpora en el Sprint 3 junto con la IA. |
| Método de formateo | El formato se aplica **sobre el documento original (in-place)**. No se reconstruye el documento con el rebuilder. |
| Alcance del formato | Se formatean el **cuerpo, los títulos y el texto dentro de tablas**. Los encabezados y pies de página quedan intactos. |
| Se conserva | Negrita, cursiva, subrayado, color, imágenes, tablas, celdas combinadas y listas. |
| No se modifica | Orientación y tamaño de hoja. |
| Unidades | La API recibe y devuelve **centímetros** (márgenes) y **puntos** (tamaño de fuente). El backend hace las conversiones. |
| Tamaño máximo de archivo | **10 MB**. |
| Autenticación | **Ninguna en el Sprint 2.** El backend usa un usuario fijo de desarrollo. |
| Jobs | En el Sprint 2 hay **un job por documento**. Volver a formatear reemplaza la configuración y el resultado del mismo job. |
| IA | No disponible. El campo `use_ai` existe pero debe ser `false`. |

---

## 2. Convenciones generales

- **URL base (desarrollo):** `http://localhost:8000/api`
- **Origen del frontend permitido por CORS:** `http://localhost:5173`
- **Formato:** JSON en UTF-8, excepto la carga (multipart) y la descarga (binario).
- **Identificadores:** enteros. En las rutas, `{id}` es siempre el **`document_id`**.
- **Fechas:** ISO 8601 en UTC, por ejemplo `2026-10-08T15:30:00Z`.
- **Nombres de campos:** `snake_case`.
- **Campos sin valor:** se devuelven como `null`, nunca se omiten.

---

## 3. Estados del job

| Estado | Significado |
|---|---|
| `pending` | El documento se cargó y aún no se ha formateado. |
| `processing` | El formateo está en curso. |
| `done` | El documento formateado está listo para descargar. |
| `error` | El formateo falló. El motivo está en `error_message`. |

Transiciones permitidas: `pending → processing → done | error`. Si el usuario vuelve a formatear, el job regresa a `processing`.

> El estado `review` existe en el modelo de datos pero está **reservado para el Sprint 3** y la API no lo devuelve.

---

## 4. Esquema de configuración

### 4.1 Campos

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `preset_id` | string \| null | No | Uno de `apa7`, `reporte`, `personalizado`. Si se envía, sus valores se cargan primero. |
| `margins_cm` | objeto | Sí\* | Contiene `top`, `bottom`, `left`, `right`. Cada uno es un número entre **0.5 y 5.0**, con hasta 2 decimales. |
| `font_family` | string | Sí\* | Uno de la [lista cerrada de fuentes](#42-fuentes-permitidas). |
| `font_size_pt` | número | Sí\* | Entre **8 y 24**, en pasos de 0.5. |
| `line_spacing` | número | Sí\* | Entre **1.0 y 3.0**, con hasta 2 decimales. Se aplica como múltiplo. |
| `heading_sizes_pt` | objeto \| null | No | Contiene `h1`, `h2`, `h3`, cada uno entre 8 y 48. Si se omite, se toma del preset; si el preset no lo define, se calcula a partir del tamaño de fuente (ver 4.4). |
| `use_ai` | booleano | No | Debe ser `false`. Por defecto `false`. |

\* **Obligatorio solo si no se envía `preset_id`.** Con `preset_id`, cualquier campo enviado **sobrescribe** el valor del preset.

### 4.2 Fuentes permitidas

`Times New Roman`, `Arial`, `Calibri`, `Cambria`, `Georgia`, `Verdana`

Se usa una lista cerrada para evitar fuentes que no existan en el equipo de quien abra el documento. El valor debe coincidir **exactamente** (mayúsculas y espacios incluidos).

### 4.3 Presets

| `preset_id` | Nombre | Márgenes (cm) | Fuente | Tamaño | Interlineado | Títulos h1 / h2 / h3 |
|---|---|---|---|---|---|---|
| `apa7` | Formato académico (APA 7) | 2.54 en los 4 lados | Times New Roman | 12 | 2.0 | 12 / 12 / 12 |
| `reporte` | Reporte ejecutivo | 2.5 en los 4 lados | Calibri | 11 | 1.15 | 16 / 14 / 12 |
| `personalizado` | Personalizado | 2.54 en los 4 lados | Calibri | 11 | 1.15 | `null` (se calculan) |

### 4.4 Tamaño de títulos cuando no hay `heading_sizes_pt`

El tamaño de cada título se calcula multiplicando `font_size_pt` y redondeando al 0.5 más cercano:

| Título | Factor |
|---|---|
| `h1` (y estilo `Title`) | × 1.5 |
| `h2` | × 1.25 |
| `h3` | × 1.1 |

### 4.5 Ejemplo de solicitud (con preset y una modificación)

```json
{
  "preset_id": "apa7",
  "margins_cm": { "left": 3.0 },
  "use_ai": false
}
```

Resultado: se carga APA 7 y solo el margen izquierdo cambia a 3.0 cm.

### 4.6 Ejemplo de solicitud (sin preset, completa)

```json
{
  "preset_id": null,
  "margins_cm": { "top": 2.5, "bottom": 2.5, "left": 3.0, "right": 2.5 },
  "font_family": "Arial",
  "font_size_pt": 11,
  "line_spacing": 1.5,
  "use_ai": false
}
```

---

## 5. Formato de errores

Todo error usa la misma estructura:

```json
{
  "error": {
    "code": "INVALID_CONFIG",
    "message": "El tamaño de fuente debe estar entre 8 y 24 pt.",
    "details": { }
  }
}
```

- `code`: identificador estable, pensado para el código del frontend.
- `message`: texto en español, **listo para mostrarse al usuario tal cual**.
- `details`: opcional, con información adicional (por ejemplo, qué campos fallaron).

### 5.1 Catálogo de errores

| `code` | HTTP | Cuándo ocurre |
|---|---|---|
| `INVALID_FILE` | 400 | El archivo no es un `.docx` válido (extensión, firma, vacío, corrupto o protegido). |
| `FILE_TOO_LARGE` | 400 | El archivo supera los 10 MB. |
| `INVALID_CONFIG` | 400 | La configuración está incompleta, fuera de rango, tiene una fuente no permitida o `use_ai` es `true`. |
| `NOT_FOUND` | 404 | El documento o el preset no existe. |
| `NOT_READY` | 409 | Se intenta descargar un documento que aún no está en estado `done`. |
| `PROCESSING_ERROR` | 500 | Falló el formateo internamente. El job queda en estado `error`. |

### 5.2 Mensajes de `INVALID_FILE`

| `details.reason` | `message` |
|---|---|
| `no_file` | No se recibió ningún archivo. |
| `bad_extension` | Solo se permiten archivos .docx. |
| `bad_signature` | El archivo no es un documento de Word válido. |
| `cannot_open` | No se pudo abrir el documento. Puede estar dañado o protegido con contraseña. |

### 5.3 Ejemplo de `INVALID_CONFIG` con detalle

```json
{
  "error": {
    "code": "INVALID_CONFIG",
    "message": "La configuración no es válida.",
    "details": {
      "fields": {
        "font_size_pt": "Debe estar entre 8 y 24.",
        "margins_cm.top": "Debe estar entre 0.5 y 5.0."
      }
    }
  }
}
```

---

## 6. Endpoints

### 6.1 Subir documento

`POST /api/documents/`

**Solicitud:** `multipart/form-data`

| Campo | Tipo | Descripción |
|---|---|---|
| `file` | archivo | El `.docx` a procesar. |

**Validaciones, en este orden:**

1. Se recibió el archivo.
2. La extensión es `.docx`.
3. El tamaño no supera los 10 MB.
4. Los primeros bytes son la firma ZIP (`PK\x03\x04`).
5. `python-docx` puede abrirlo.

**Respuesta exitosa — `201 Created`:**

```json
{
  "document_id": 12,
  "job_id": 12,
  "status": "pending",
  "original_name": "tesis_capitulo1.docx",
  "size_bytes": 248913,
  "uploaded_at": "2026-10-08T15:30:00Z"
}
```

**Errores posibles:** `INVALID_FILE`, `FILE_TOO_LARGE`.

---

### 6.2 Formatear documento

`POST /api/documents/{id}/format/`

**Solicitud:** `application/json` con la [configuración](#4-esquema-de-configuración).

**Comportamiento:**

1. Valida la configuración y resuelve el preset si se envió.
2. Guarda la configuración en el job y pasa a `processing`.
3. Aplica márgenes, tipografía e interlineado sobre el documento original.
4. Reabre el resultado para comprobar que no está dañado.
5. Pasa a `done` (o a `error` si algo falla).

**Respuesta exitosa — `200 OK`:**

```json
{
  "document_id": 12,
  "job_id": 12,
  "status": "done",
  "config": {
    "preset_id": "apa7",
    "margins_cm": { "top": 2.54, "bottom": 2.54, "left": 3.0, "right": 2.54 },
    "font_family": "Times New Roman",
    "font_size_pt": 12,
    "line_spacing": 2.0,
    "heading_sizes_pt": { "h1": 12, "h2": 12, "h3": 12 },
    "use_ai": false
  },
  "finished_at": "2026-10-08T15:30:04Z"
}
```

> `config` devuelve siempre la configuración **ya resuelta** (preset más sobrescrituras), con todos los campos completos. Es lo que el frontend debe mostrar en el resumen de la pantalla de resultado.

**Errores posibles:** `NOT_FOUND`, `INVALID_CONFIG`, `PROCESSING_ERROR`.

---

### 6.3 Consultar estado

`GET /api/documents/{id}/`

**Respuesta exitosa — `200 OK`:**

```json
{
  "document_id": 12,
  "job_id": 12,
  "original_name": "tesis_capitulo1.docx",
  "size_bytes": 248913,
  "uploaded_at": "2026-10-08T15:30:00Z",
  "status": "done",
  "config": { },
  "use_ai": false,
  "error_message": null,
  "started_at": "2026-10-08T15:30:01Z",
  "finished_at": "2026-10-08T15:30:04Z",
  "download_url": "/api/documents/12/download/"
}
```

- `config` es `{}` mientras el documento no se haya formateado.
- `download_url` es `null` salvo que `status` sea `done`.
- `error_message` solo trae texto cuando `status` es `error`.

**Errores posibles:** `NOT_FOUND`.

---

### 6.4 Descargar documento formateado

`GET /api/documents/{id}/download/`

**Respuesta exitosa — `200 OK`:** el archivo binario.

| Encabezado | Valor |
|---|---|
| `Content-Type` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `Content-Disposition` | `attachment; filename="<nombre_original_sin_extension>_formateado.docx"` |

**Errores posibles:** `NOT_FOUND`, `NOT_READY`.

---

### 6.5 Listar presets

`GET /api/templates/`

**Respuesta exitosa — `200 OK`:**

```json
{
  "presets": [
    {
      "id": "apa7",
      "name": "Formato académico (APA 7)",
      "description": "Times New Roman 12, interlineado doble, márgenes de 2.54 cm.",
      "config": {
        "margins_cm": { "top": 2.54, "bottom": 2.54, "left": 2.54, "right": 2.54 },
        "font_family": "Times New Roman",
        "font_size_pt": 12,
        "line_spacing": 2.0,
        "heading_sizes_pt": { "h1": 12, "h2": 12, "h3": 12 }
      }
    },
    {
      "id": "reporte",
      "name": "Reporte ejecutivo",
      "description": "Calibri 11, interlineado 1.15, márgenes de 2.5 cm.",
      "config": {
        "margins_cm": { "top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5 },
        "font_family": "Calibri",
        "font_size_pt": 11,
        "line_spacing": 1.15,
        "heading_sizes_pt": { "h1": 16, "h2": 14, "h3": 12 }
      }
    },
    {
      "id": "personalizado",
      "name": "Personalizado",
      "description": "Valores base editables.",
      "config": {
        "margins_cm": { "top": 2.54, "bottom": 2.54, "left": 2.54, "right": 2.54 },
        "font_family": "Calibri",
        "font_size_pt": 11,
        "line_spacing": 1.15,
        "heading_sizes_pt": null
      }
    }
  ]
}
```

**Errores posibles:** ninguno esperado.

---

## 7. Flujo completo

```
Frontend                                   Backend
   │                                          │
   │  POST /api/documents/  (file)            │
   │ ───────────────────────────────────────► │  valida, guarda, crea job (pending)
   │ ◄─────────────────────────────────────── │  201 { document_id, ... }
   │                                          │
   │  GET /api/templates/                     │
   │ ───────────────────────────────────────► │
   │ ◄─────────────────────────────────────── │  200 { presets: [...] }
   │                                          │
   │  (usuario elige o ajusta configuración)  │
   │                                          │
   │  POST /api/documents/{id}/format/        │
   │ ───────────────────────────────────────► │  processing → aplica formato → done
   │ ◄─────────────────────────────────────── │  200 { status: "done", config }
   │                                          │
   │  GET /api/documents/{id}/download/       │
   │ ───────────────────────────────────────► │
   │ ◄─────────────────────────────────────── │  200 (archivo .docx)
```

Rutas del frontend asociadas: `/` (carga) → `/config` (configuración) → `/result` (resultado y descarga).

---

## 8. Reservado para el Sprint 3 (IA)

Estos puntos **ya están contemplados** para no romper el contrato después:

- El campo `use_ai` existe en la solicitud y la respuesta. En el Sprint 2, si llega `true`, la API responde `INVALID_CONFIG` con el mensaje *"La corrección con IA aún no está disponible."*
- El pipeline del backend se organiza como una lista de pasos. En el Sprint 3 se inserta un paso de IA **antes** del paso de plantilla.
- El modelo `ProcessingJob` ya incluye `ai_suggestions` (JSON, nulo). La API no lo expone todavía.
- El estado `review` se activará cuando existan sugerencias pendientes de aprobación.

---

## 9. Datos de ejemplo para el frontend (mocks)

El frontend puede usar las respuestas de la sección 6 tal cual como mocks mientras el backend no esté listo, activando `VITE_USE_MOCKS=true`. Respuestas de error recomendadas para probar los estados de falla:

**Carga con archivo inválido (`400`):**

```json
{
  "error": {
    "code": "INVALID_FILE",
    "message": "El archivo no es un documento de Word válido.",
    "details": { "reason": "bad_signature" }
  }
}
```

**Formateo fallido (`500`):**

```json
{
  "error": {
    "code": "PROCESSING_ERROR",
    "message": "No se pudo formatear el documento. Intenta de nuevo o prueba con otro archivo.",
    "details": { }
  }
}
```

**Descarga antes de tiempo (`409`):**

```json
{
  "error": {
    "code": "NOT_READY",
    "message": "El documento aún no está listo para descargar.",
    "details": { }
  }
}
```

---

## 10. Fuera del contrato (Sprint 2)

No se define ni se implementa todavía:

- Autenticación, registro de usuarios y permisos.
- Listado de historial de documentos (`GET /api/documents/`). Es parte del *stretch* del sprint.
- Vista previa del documento.
- Procesamiento asíncrono y consulta periódica (*polling*).
- Número de página, encabezados, pies y logo.
- Múltiples jobs por documento.

---

## 11. Control de cambios

| Versión | Fecha | Cambio | Acordado por |
|---|---|---|---|
| 1.0 | 08/10/2026 | Versión inicial | Pendiente de aprobación |
