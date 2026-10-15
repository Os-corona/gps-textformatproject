# PrettyDocs

Plataforma web para el **formateo y personalización de documentos de texto** mediante inteligencia artificial.

> **Estado del proyecto:** 🟡 En desarrollo — Sprint 1 (esqueleto del sistema)

## 📋 Descripción

PrettyDocs es un proyecto de software que tiene como objetivo desarrollar una plataforma web capaz de recibir documentos de texto y aplicarles un formato adecuado y personalizado, sin modificar ni agregar información al contenido original.

La plataforma estará orientada a usuarios que necesitan adaptar documentos a determinados formatos de presentación, permitiendo seleccionar diferentes opciones de configuración y utilizar agentes de inteligencia artificial proporcionados por el usuario.

## 🎯 Objetivo

Brindar una plataforma web capaz de entregar documentos con un formato adecuado y personalizado a partir de un documento de texto.

## ✨ Funcionalidades planeadas

* Dar formato preestablecido a documentos `.docx`.
* Permitir personalizar diferentes aspectos del formato.
* Configurar elementos como:

  * Márgenes.
  * Fuente.
  * Tamaño de fuente.
  * Número de página.
  * Logo institucional.
  * Otras opciones de formato.
* Permitir al usuario seleccionar diferentes opciones de formato.
* Corrección gramatical/ortográfica y reestructuración jerárquica del texto asistida por IA.
* Permitir el uso de distintos agentes de IA proporcionados por el usuario.

## 🚫 Fuera del alcance

* Aceptar documentos que no sean `.docx`.
* Modificar el significado del contenido existente.
* Agregar información nueva al documento.
* Interacción del usuario con la IA mediante prompts libres (el sistema usa prompts predefinidos).

## 👥 Equipo

| Integrante                      | Rol                            |
| -------------------------------- | ------------------------------- |
| Oscar Alejandro Arias Corona    | Líder de proyecto              |
| Alfonso Maron Fernandez Garibay | Frontend                       |
| Luis Dorian Ferreira Calderon   | Backend                        |
| Luis Arturo Roman Sanchez       | Administrador de Base de Datos |
| Roberto Cisneros Garcia         | Backend                        |

## 🛠️ Stack tecnológico

| Capa | Tecnología |
| --- | --- |
| Backend | Django + Django REST Framework |
| Base de datos | PostgreSQL |
| Manipulación de documentos | python-docx / lxml |
| Frontend | Vue 3 + Vite + Bootstrap |
| Procesamiento asíncrono | Celery + Redis *(se integra en sprints posteriores)* |
| IA | API de Anthropic / OpenAI / Gemini *(se integra en sprints posteriores)* |
| Testing | pytest + pytest-django |

## 📦 Estructura del repositorio

```
prettydocs/
├── backend/
│   ├── documents/          # Modelos y gestión de archivos (Document, ProcessingJob)
│   ├── docx_engine/        # Extracción y reconstrucción de .docx (sin IA)
│   ├── templates_engine/   # Plantillas y formato visual (sin IA)
│   ├── ai_engine/          # Integración con modelos de lenguaje
│   ├── orchestrator/       # Orquestación del pipeline (Celery)
│   ├── api/                # Endpoints REST para el frontend
│   ├── requirements.txt
│   └── manage.py
└── frontend/
    ├── src/
    │   ├── components/     # Componentes reutilizables (header, etc.)
    │   ├── views/          # Pantallas (carga, historial, etc.)
    │   ├── router/         # Rutas de la aplicación
    │   ├── services/       # Llamadas a la API del backend
    │   └── assets/
    ├── package.json
    └── vite.config.js
```

## 🚀 Instalación y ejecución

A continuación se describen los pasos para levantar el proyecto completo (backend + frontend) en una computadora nueva.

### Requisitos previos

* Python 3.11+
* Node.js 18+ y npm
* PostgreSQL instalado y corriendo localmente
* Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/Os-corona/gps-textformatproject.git
cd gps-textformatproject
```

### 2. Backend (Django)

```bash
cd backend

# Crear y activar entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

Crear la base de datos en PostgreSQL:

```sql
CREATE DATABASE prettydocs_db;
```

Crear un archivo `.env` dentro de `backend/` (usa `.env.example` como referencia) con tus credenciales locales:

```
DB_NAME=prettydocs_db
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
```

Aplicar migraciones y levantar el servidor:

```bash
python manage.py migrate
python manage.py runserver
```

El backend quedará disponible en `http://localhost:8000`.

### 3. Frontend (Vue)

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

El frontend quedará disponible en `http://localhost:5173` (o el puerto que indique Vite en consola).

### 4. Pruebas automatizadas (Testing)

Para ejecutar la suite de pruebas del motor de plantillas (`templates_engine` — Tarea S2T15):

```bash
cd backend

# Ejecutar la suite completa de pruebas del motor de plantillas
pytest tests/test_templates_engine.py -v

# O ejecutar por criterio específico:
pytest tests/test_templates_engine.py -k "test_margins" -v
pytest tests/test_templates_engine.py -k "test_line_spacing" -v
pytest tests/test_templates_engine.py -k "test_preservation" -v
pytest tests/test_templates_engine.py -k "test_integrity" -v
pytest tests/test_templates_engine.py -k "test_typography" -v
```

#### Cobertura de la Suite de Pruebas (S2T15):
1. **Fixture Parametrizada (`valid_docx_path`)**: Carga automática de los 6 documentos `.docx` válidos de `tests/fixtures/` (`01_planos` a `06_secciones`).
2. **Márgenes (`test_margins_applied_to_all_sections`)**: Verifica que tras `apply_template`, todas las secciones del documento adquieran los márgenes configurados sin alterar la orientación de página.
3. **Tipografía (`test_typography_*`)**:
   - Comprueba que los estilos `Normal` y `Heading 1` a `Heading 3` adopten la fuente configurada y eliminen atributos de tema (`w:asciiTheme`, `w:hAnsiTheme`, etc.).
   - Recorre todos los runs (cuerpo y celdas de tabla) validando que no existan overrides manuales discrepantes en fuente o tamaño.
4. **Interlineado (`test_line_spacing_applied_to_body_paragraphs`)**: Comprueba que los párrafos del cuerpo tengan el valor de interlineado múltiple configurado y la regla XML `w:lineRule="auto"`.
5. **Preservación Estructural (`test_preservation_tables_images_and_lists`)**: Verifica que el conteo de tablas, imágenes (`a:blip`) y párrafos de lista permanezca idéntico antes y después del formateo.
6. **Integridad de Archivo (`test_integrity_save_and_reopen`)**: Guarda el documento procesado en un stream binario y comprueba que `docx.Document()` lo reabra sin errores de corrupción ni excepciones de paquete.

---

### 🐛 Registro de Fallos y Bugs Detectados (Jira Tickets)

A partir de la ejecución de la suite de pruebas sobre el estado actual de `templates_engine`, se registraron los siguientes bugs para su seguimiento y resolución en Jira:

| Ticket Jira | Severidad | Componente | Resumen del Fallo | Estado Actual |
| :--- | :--- | :--- | :--- | :--- |
| **PRETTY-BUG-01** | Crítica / Bloqueante | `templates_engine/applier.py` | `ModuleNotFoundError: No module named 'documents.templates_engine.typography'`. `applier.py` importa `typography.py` el cual no fue creado/comiteado en S2T4. | Mitigado con stub temporal para pruebas; requiere implementación de S2T4. |
| **PRETTY-BUG-02** | Alta | `templates_engine/typography.py` | Los estilos `Normal` y `Heading 1` a `3` mantienen `font.name=None` y retienen atributos de tema (`asciiTheme`, `hAnsiTheme`, etc.) sin aplicar la fuente configurada. | Abierto (Fallo en `test_typography_styles_no_theme_attributes` en todos los fixtures). |
| **PRETTY-BUG-03** | Alta | `templates_engine/typography.py` | Los runs con formato directo (override manual) en cuerpo y tablas no normalizan su fuente ni tamaño a la configuración establecida. | Abierto (Fallo en `test_typography_runs_no_divergent_font_or_size` en fixtures `02`, `04`, `05`, `06`). |
| **PRETTY-BUG-04** | Media | `documents/pipeline.py` / `applier.py` | Incompatibilidad de tipos: `pipeline.py` pasa `job.config` como diccionario a `apply_template()`, pero este accede a los campos mediante atributos de objeto (`config.margin_top`), causando `AttributeError`. | Abierto (Requiere parseo a `TemplateConfig` en `pipeline.py`). |
| **PRETTY-BUG-05** | Media | `templates_engine/config.py` | `TemplateConfig` (Pydantic v2) no define `heading_sizes` y lanza `ValueError` al intentar asignar tamaños dinámicos; existe discrepancia con los nombres del contrato de API (`font_family` vs `font_name`, etc.). | Abierto. |
| **PRETTY-BUG-06** | Baja | `templates_engine/spacing.py` | `UserWarning` emitido por python-docx 1.2.0 por resolución de estilos mediante ID (`doc.styles["Normal"]`). | Abierto. |

## 📦 Alcance

### Incluye

* Formateo preestablecido y personalizable de documentos `.docx` (márgenes, tipografía, jerarquía de títulos, interlineado).
* Corrección gramatical/ortográfica y reestructuración jerárquica asistida por IA.
* Utilización de agentes de IA proporcionados por el usuario.

### No incluye

* Soporte para formatos de documentos distintos a `.docx`.
* Modificación del significado del contenido original.
* Interacción del usuario con la IA mediante prompts libres.

## 📅 Plan de trabajo (Ingeniería en Software)

| Fase | Entregable principal | Fecha |
| --- | --- | --- |
| U1 · Arranque | Acta, sistema de gestión, repositorio con esqueleto ejecutable y base de datos inicial | 11/09/2026 |
| U2 · Calidad y catálogo | Plan de calidad y módulo de catálogo | 02/10/2026 |
| U3 · Planificación | Plan del proyecto, matriz de riesgos y funcionalidades relacionadas | 30/10/2026 |
| U4 · Propuesta y alertas | Propuesta, contrato y funcionalidades de alertas/reportes | 13/11/2026 |
| U5 · Cierre | Prueba, informe de cierre y entrega | 04/12/2026 |

## 🧭 Progreso actual (Sprint 1)

El Sprint 1 se enfoca en construir el esqueleto del sistema y el núcleo de manipulación de documentos `.docx`, sin integración de IA todavía:

- [x] Proyecto Django inicializado con estructura de apps (`documents`, `docx_engine`, `templates_engine`, `ai_engine`, `orchestrator`, `api`)
- [x] Conexión a PostgreSQL configurada
- [x] Modelos base `Document` y `ProcessingJob`
- [X] Extractor de párrafos, runs, tablas, imágenes y listas
- [X] Rebuilder de párrafos, tablas, imágenes y listas
- [X] Función de comparación de documentos (`compare_documents`) y pruebas manuales del pipeline
- [X] Set completo de documentos de prueba y test de round-trip automatizado
- [x] Proyecto Vue inicializado (Vite + Bootstrap)
- [x] Layout base y navegación (header + rutas)
- [X] Pantalla de carga de archivo con validación `.docx`

## 📄 Documentación

La documentación del proyecto se irá incorporando conforme avance el desarrollo y las diferentes fases de gestión.