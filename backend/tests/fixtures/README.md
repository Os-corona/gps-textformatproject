# Fixtures de Prueba DOCX (S2T14)

Este directorio contiene documentos de prueba diseñados para validar el pipeline de procesamiento, extracción y normalización de documentos DOCX en PrettyDocs, cubriendo casos de uso comunes, documentos del mundo real y escenarios de fallo.

## Estructura del Directorio

```text
backend/tests/fixtures/
├── 01_planos.docx
├── 02_headings_mixto.docx
├── 03_tema.docx
├── 04_tabla_imagen.docx
├── 05_listas.docx
├── 06_secciones.docx
├── README.md
└── invalid/
    ├── falso.docx
    ├── vacio.docx
    └── corrupto.docx
```

---

## Matriz de Archivos de Prueba

| Archivo | Qué contiene | Qué prueba |
| :--- | :--- | :--- |
| **`01_planos.docx`** | Párrafos de texto plano sin estilos aplicados ni jerarquías complejas. | Extracción básica de texto plano, verificación de que el motor no asuma jerarquías inexistentes y aplique correctamente los estilos base por defecto. |
| **`02_headings_mixto.docx`** | Headings reales combinados con párrafos con fuente, tamaño y negritas aplicadas a mano (formato directo). Documento real, desordenado y anonimizado. | Diferenciación entre estilos semánticos de Word vs. estilos "hardcodeados" a mano (run-level formatting). Capacidad de normalización en documentos sucios o inconsistentes. |
| **`03_tema.docx`** | Documento nuevo de Word sin tocar fuentes manualmente, utilizando títulos y estilos nativos del tema de Word. | Herencia e interpretación correcta de los estilos de tema nativos de Microsoft Word (Normal, Título, Subtítulo, Heading 1-3) sin overrides directos. |
| **`04_tabla_imagen.docx`** | Tabla con celdas combinadas (spans horizontales y/o verticales) y al menos una imagen embebida. | Preservación de tablas con estructuras complejas (`gridSpan`, `vMerge`) y manejo de elementos multimedia inline/floating sin distorsión ni pérdida de datos. |
| **`05_listas.docx`** | Listas con viñetas y numeradas con 3 niveles de profundidad, generado en Google Docs o LibreOffice y exportado a `.docx`. | Compatibilidad cross-platform de numeraciones multinivel y esquemas de listas (`w:numId`, `w:ilvl`) producidos por herramientas ofimáticas alternativas a Word. |
| **`06_secciones.docx`** | 3 secciones separadas con saltos de sección, incluyendo una sección intermedia con orientación horizontal (landscape). | Detección y preservación de múltiples secciones, saltos de página/sección y retención de orientación de página diferenciada (vertical vs. horizontal). |
| **`invalid/falso.docx`** | Archivo PDF real renombrado con extensión `.docx` (cabecera `%PDF-`). | Validación de magic bytes y rechazo temprano de archivos con extensión engañosa que no son paquetes OOXML válidos. |
| **`invalid/vacio.docx`** | Archivo ZIP válido pero vacío (sin archivos internos, 22 bytes estándar). | Manejo de excepción ante paquetes ZIP vacíos que carecen de la estructura OOXML requerida (`[Content_Types].xml`, `word/document.xml`, etc.). |
| **`invalid/corrupto.docx`** | Archivo DOCX real truncado a la mitad de su tamaño binario. | Resiliencia ante archivos incompletos, descargas interrumpidas o paquetes corruptos (`BadZipFile` / fin de archivo inesperado). |

---

## Verificación de Integridad

- **Documentos válidos (`01` al `06`):** Deben abrirse en Microsoft Word sin advertencias de reparación ni diálogos de contenido no legible.
- **Documentos inválidos (`invalid/`):** El backend debe capturar excepciones específicas (validación de formato, integridad de paquete OOXML) y retornar errores controlados al usuario o pipeline.
