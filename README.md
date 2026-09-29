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

### 4. Correr las pruebas del backend

```bash
cd backend
pytest
```

Esto ejecuta las pruebas de `docx_engine` (incluyendo las pruebas de round-trip de extracción/reconstrucción de documentos) y del resto de módulos con cobertura de tests.

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
- [ ] Extractor de párrafos, runs, tablas, imágenes y listas
- [ ] Rebuilder de párrafos, tablas, imágenes y listas
- [ ] Función de comparación de documentos (`compare_documents`) y pruebas manuales del pipeline
- [ ] Set completo de documentos de prueba y test de round-trip automatizado
- [x] Proyecto Vue inicializado (Vite + Bootstrap)
- [x] Layout base y navegación (header + rutas)
- [ ] Pantalla de carga de archivo con validación `.docx`

## 📄 Documentación

La documentación del proyecto se irá incorporando conforme avance el desarrollo y las diferentes fases de gestión.