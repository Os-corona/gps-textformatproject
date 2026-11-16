# Extractor v2 — S3T10

Desde `backend/`:

```python
from docx_engine.extractor import extract_document

di = extract_document("tests/fixtures/05_listas.docx")
print(di.stats.model_dump())
print(di.blocks[2].hints.model_dump())
payload = di.model_dump(mode="json")
```

`extract_document()` acepta una ruta (`str` o `Path`) o un stream binario y
devuelve `DocumentIntermediate` (alias `DI`), definido en
`common/document_schema.py`. No escribe imágenes en disco ni altera el archivo.
El esquema exportado está en `docs/schemas/document_intermediate.schema.json`.

## Bloques y estadísticas

Cada hijo directo de `w:body` tiene exactamente un `SourceBlock`, con ID
`b0`, `b1`, etc., usando su posición original. Se incluyen párrafos vacíos,
elementos desconocidos y el `sectPr` final, por lo que los IDs no se desplazan
al encontrar contenido que no sea texto editable.

- `paragraph`: texto y runs con `bold`, `italic`, `underline`, `font` y `size`.
- `keep`: XML original en `xml` y motivos en `opaque_reasons`. Incluye tablas,
  imágenes, dibujos, campos, referencias a notas, hipervínculos, cambios
  registrados, saltos de sección, elementos desconocidos y párrafos vacíos.
  Los campos que abarcan varios párrafos protegen todo el intervalo.

Los motivos son `table`, `image`, `drawing`, `field`, `footnote`, `hyperlink`,
`tracked_change`, `section_break`, `section_properties`, `unknown_element` y
`empty_paragraph`. Un bloque puede tener varios motivos.

`stats` contiene `total_blocks`, `text_blocks`, `opaque_blocks` y un mapa
`opaque_reasons` de ID a lista de motivos. Los dos conteos parciales suman el total.
El XML opaco puede contener referencias a relaciones del paquete original:
debe reutilizarse junto con ese DOCX al implementar la reconstrucción v2.

## Hints

- `all_bold`: todos los runs con contenido distinto de espacios son negrita;
  considera estilos heredados y overrides explícitos.
- `size_ratio`: tamaño máximo de los runs / `base_font_size`. El tamaño base
  es la moda ponderada por cantidad de caracteres de los párrafos editables,
  contando espacios. Los tamaños se resuelven desde formato directo, estilo
  de carácter, estilo de párrafo y sus ancestros, hasta `docDefaults`; si falta
  todo, se usan 11 pt. En empate gana el primer tamaño encontrado.
- `words`, `ends_with_period`, `starts_with_glyph` y `manual_numbering`:
  señales del texto original, que no se modifica ni se recorta.
- `indent_level`: rango de las sangrías positivas distintas del documento,
  comenzando en 1; sin sangría positiva corresponde 0. Usa `w:start`/`w:left`
  de `w:ind`, incluida la herencia de estilos. `indent_cm` conserva el valor
  físico. No se impone un paso fijo a archivos exportados por otros editores.
- `style_name`, `is_native_list`, `is_list`, `is_numbered` y `list_level`:
  identifican listas nativas, también con numeración heredada o anulada con
  `numId=0`. Los glifos y números manuales se señalan por separado.

`underline` usa el booleano nullable del esquema `Run`: conserva presencia,
ausencia y desactivación explícita; no distingue variantes como doble subrayado.

## Compatibilidad y pruebas

`extract_structure()` adapta el v2 al contrato anterior de `/api/documents/extract/`:
párrafos, tablas con `rows`/`data` e imágenes extraídas a rutas temporales.
La vista heredada sigue omitiendo párrafos vacíos y no ofrece la conservación
completa de bloques opacos; para ese fin se utiliza el DI. El rebuilder v1
también aplica ahora `underline`.

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_extractor_v2.py tests/test_docx_engine.py tests/test_document_schema.py tests/test_templates_engine.py tests/test_template_formatting.py tests/test_templates_engine_v2.py -q
```

Las pruebas cubren los seis fixtures, las señales de listas de `05_listas`,
los títulos con formato manual de `02_headings_mixto`, los bloques opacos de
`04_tabla_imagen` y `06_secciones`, herencia tipográfica, tipos de contenido
opaco, estabilidad de IDs, serialización, subrayado y el endpoint de extracción.
Las dos pruebas `xfail` existentes del rebuilder v1 siguen documentando la
pérdida de secciones de `06_secciones`; su corrección pertenece al rebuilder v2.
