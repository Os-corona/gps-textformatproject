# Estado del Repositorio — PrettyDocs (Cierre Sprint 2 / Inicio Sprint 3)

| Metadato | Detalle |
| :--- | :--- |
| **Proyecto** | PrettyDocs — Formateo Inteligente de Documentos de Texto |
| **Fecha de corte** | 02 de Noviembre de 2026 |
| **Rama de análisis** | `testing/revisar-resultados-sprint-3` (derivada de `main`) |
| **Último Commit en `main`** | `cc42cdd` (*Merge pull request #28 from Os-corona/feature/S2T9-descarga-estado*) |
| **Estado global** | 🟡 Sprint 2 concluido funcionalmente en desarrollo; bloqueado técnicamente por colisión de merge reciente. |

---

## 1. Resumen Ejecutivo del Estado del Repositorio

PrettyDocs completó el desarrollo de las tareas nucleares del **Sprint 2** orientadas al formateo visual determinístico de documentos `.docx` (márgenes, tipografía e interlineado) sin intervención de Inteligencia Artificial.

Durante la integración de los últimos Pull Requests hacia la rama `main` (específicamente la fusión de la tarea `S2T16` — *Pruebas de API* y la tarea `S2T9` — *Endpoints de descarga, estado y presets*), se produjo una **regresión crítica en la resolución de conflictos** en el backend que impide el arranque normal de la aplicación y la ejecución de la suite de pruebas. Asimismo, se completó la interfaz web en Vue 3 con un flujo de 3 pasos (Carga, Configuración y Resultado), aunque existen discrepancias entre el contrato de API acordado y la implementación de ciertos endpoints.

---

## 2. Topología de Ramas y Commits Recientes

### 2.1 Historial Inmediato de Integración en `main`

1. **`cc42cdd` (01/11/2026):** *Merge pull request #28 from Os-corona/feature/S2T9-descarga-estado*.
   - Integró soporte de CORS (`django-cors-headers`), endpoints de descarga y consulta de estado.
   - Contiene la resolución de conflictos conflictiva en [`backend/documents/urls.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/urls.py) y [`backend/documents/views.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/views.py).
2. **`9a0bba7` (19/10/2026):** *Merge: resolucion de conflictos*.
   - Commit interno de merge donde se sobrescribió accidentalmente la función `document_detail_view` por `document_status_view`.
3. **`6425d13` (14/10/2026):** *docs(S2T16): documentar suite de pruebas de API y actualización de bugs*.
   - Registro de cobertura en [`README.md`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/README.md) y documentación de tickets Jira `PRETTY-BUG-01` a `PRETTY-BUG-06`.
4. **`f936cf9` (14/10/2026):** *feat(S2T16): implementar pruebas de API e integrar endpoints de consulta y descarga*.
   - Implementó [`backend/tests/test_api.py`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/tests/test_api.py) con 10 pruebas automatizadas y soporte de normalización en [`TemplateConfig`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/backend/documents/templates_engine/config.py).
5. **`d0b39b9` y `ee3ab18` (12-14/10/2026):** *Pantalla de resultados y carga conectada al backend*.
   - Conexión de vistas frontend ([`HomeView.vue`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/frontend/src/views/HomeView.vue), [`ResultView.vue`](file:///c:/Users/lartu/Documents/ITM/7%20TERM/GPS/projects/gps-textformatproject/frontend/src/views/ResultView.vue)) mediante Axios y Pinia.

---

## 3. Estructura de Directorios Actual

```text
gps-textformatproject/
├── .gitignore
├── api-contract.md                        # Contrato oficial Frontend <-> Backend (Sprint 2)
├── README.md                              # Documentación general y registro de bugs
├── backend/
│   ├── manage.py                          # Entrypoint Django
│   ├── pytest.ini                         # Configuración de pytest-django
│   ├── requirements.txt                   # Dependencias Python (UTF-16 LE - requiere fix)
│   ├── core/
│   │   ├── settings.py                    # Configuración Django + CORS + Apps
│   │   ├── urls.py                        # Enrutamiento raíz (/admin/, /api/documents/)
│   │   └── wsgi.py
│   ├── documents/
│   │   ├── models.py                      # Modelos Document y ProcessingJob
│   │   ├── serializers.py                 # Serializador con validaciones de cabecera ZIP/OOXML
│   │   ├── urls.py                        # Rutas de API (/api/documents/...) [CONTIENE ERROR]
│   │   ├── views.py                       # Vistas API REST
│   │   ├── pipeline.py                    # Definición de pasos secuenciales de formateo
│   │   ├── docx_engine/                   # Extractor de estructura y comparador
│   │   │   ├── extractor.py
│   │   │   ├── comparator.py
│   │   │   └── README_TEST_REPORT.md      # Reporte de pruebas estructurales
│   │   └── templates_engine/              # Motor de aplicación de formato
│   │       ├── applier.py                 # Orquestador del formato sobre el documento
│   │       ├── config.py                  # Modelo Pydantic TemplateConfig
│   │       ├── margins.py                 # Aplicación de márgenes en secciones
│   │       ├── spacing.py                 # Interlineado múltiple y w:lineRule
│   │       ├── typography.py              # Fuentes y normalización de estilos/runs
│   │       └── presets/                   # apa7.json, reporte.json, personalizado.json
│   ├── tests/
│   │   ├── test_api.py                    # Suite de pruebas de endpoints DRF (S2T16)
│   │   ├── test_templates_engine.py       # Suite de pruebas del motor de plantillas (S2T15)
│   │   └── fixtures/                      # 6 DOCX reales + 3 archivos inválidos
│   ├── uploads/                           # Almacén de archivos cargados
│   └── results/                           # Almacén de archivos procesados
└── frontend/
    ├── package.json                       # Dependencias Vue 3, Vite, Bootstrap, Pinia, Axios
    ├── vite.config.js
    └── src/
        ├── main.js
        ├── App.vue
        ├── router/index.js                # Rutas: /, /config, /result, /history, /settings
        ├── services/api.js                # Cliente Axios e interceptores de errores
        ├── stores/flowStore.js            # Estado global del documento, config y resultado
        ├── composables/useFileUpload.ts   # Lógica desacoplada de Drag&Drop y validación
        └── views/
            ├── HomeView.vue               # Paso 1: Subida de archivo
            ├── ConfigView.vue             # Paso 2: Selección de preset y personalización
            └── ResultView.vue             # Paso 3: Estado de proceso y descarga
```

---

## 4. Estado de la Pila Tecnológica y Dependencias

### 4.1 Backend
- **Framework:** Django 6.1.1 + Django REST Framework 3.18.1.
- **Manipulación de Documentos:** `python-docx` 1.2.0 + `lxml` 6.1.3.
- **Validación de Esquemas:** `pydantic` 2.14.1.
- **Testing:** `pytest` 9.1.1 + `pytest-django` 4.14.0.
- **Base de Datos:** PostgreSQL con `psycopg2-binary` 2.9.13 (en testing utiliza SQLite en memoria provisto por Django runner/pytest).
- **CORS:** `django-cors-headers` 4.9.0 configurado para `http://localhost:5173`.
- ⚠️ **Anomalía en archivo `requirements.txt`:** Se encuentra codificado en `UTF-16 LE` con Byte Order Mark (BOM). Esto provoca que `git diff` lo considere archivo binario y dificulta su parseo en entornos automáticos de integración continua (CI/CD).

### 4.2 Frontend
- **Framework:** Vue 3.5.21 (Composition API con `<script setup lang="ts">`).
- **Build Tool:** Vite 7.1.9.
- **Estilos:** Bootstrap 5.3.8 + Vanilla CSS complementario.
- **Gestión de Estado:** Pinia 3.0.3.
- **Cliente HTTP:** Axios 1.13.1 con sistema de mocks opcional (`VITE_USE_MOCKS=true`).

---

## 5. Tabla de Cumplimiento de Objetivos del Sprint 2

| Funcionalidad / Tarea | Estado en Código | Validación por Pruebas | Observación |
| :--- | :---: | :---: | :--- |
| **Subida y validación estricta de DOCX** | 🟢 Completado | 🟢 100% pasando | Rechaza magic bytes falsos (`%PDF-`), ZIPs vacíos, archivos corruptos y > 10 MB. |
| **Aplicación de Márgenes** | 🟢 Completado | 🟢 100% pasando | Aplica márgenes por sección sin romper páginas en horizontal (landscape). |
| **Aplicación de Interlineado** | 🟢 Completado | 🟢 100% pasando | Inyecta `w:line` y `w:lineRule="auto"` en párrafos del cuerpo. |
| **Normalización de Tipografía Base** | 🟢 Completado | 🟢 100% pasando | Elimina atributos de tema (`w:asciiTheme`) y asigna fuente en estilos `Normal` y `Heading 1-3`. |
| **Normalización de Formato Directo (Runs)** | 🔴 Incompleto | 🔴 Falla en fixtures sucios | `typography.py` no ajusta `run.font.size` en runs hardcodeados a mano (`PRETTY-BUG-03`). |
| **Endpoint de Descarga** | 🟢 Completado | 🟢 Validado | Devuelve stream binario con headers OOXML y nombre sugerido. |
| **Endpoint de Consulta de Estado** | 🔴 Roto | 🔴 Falla por regresión | Conflicto en `urls.py` y eliminación de campos del contrato (`download_url`). |
| **Catálogo de Presets** | 🔴 Incompleto | 🔴 Desalineado con frontend | Ruta incorrecta y retorno de nombres simples en vez del objeto estructurado. |
| **Interfaz de Usuario (SPA)** | 🟢 Completado | 🟢 Funcional con mocks | Flujo completo implementado y conectado a la API. |
