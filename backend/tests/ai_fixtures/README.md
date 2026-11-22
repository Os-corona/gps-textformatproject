# S3T23 — Corpus de evaluación de IA v1.0

Ocho documentos sintéticos y ocho respuestas ideales, redactadas manualmente.
No contienen documentos de clientes ni datos personales reales. Los nombres,
fechas, importes y diagramas son ficticios. No se utilizó la respuesta de un
proveedor ni `heuristic.structure` para construir los golden JSON.

## Casos

Cada carpeta contiene `document.docx` y `golden.json`.

| Caso | Documento y golden | Resultado ideal |
| --- | --- | --- |
| 1. Reporte plano | [DOCX](01_reporte_plano/document.docx), [JSON](01_reporte_plano/golden.json) | Seis párrafos; sin títulos, listas ni tablas añadidas. Conserva fechas, cantidades, moneda y porcentaje. |
| 2. Títulos falsos | [DOCX](02_titulos_falsos/document.docx), [JSON](02_titulos_falsos/golden.json) | Todos los párrafos de entrada usan `Normal`. Los cuatro títulos se distinguen solo por tamaño/negrita y se convierten a niveles 1, 2, 3 y 1. |
| 3. Listas manuales | [DOCX](03_listas_tres_niveles/document.docx), [JSON](03_listas_tres_niveles/golden.json) | Viñetas `•`, `◦`, `▪` y numeración `1.`, `1.1`, `1.1.1`, `2.` convertidas a listas con niveles 0, 1 y 2; desaparecen únicamente los prefijos estructurales. |
| 4. Clave-valor | [DOCX](04_clave_valor_tabla/document.docx), [JSON](04_clave_valor_tabla/golden.json) | Tres registros se agrupan en una tabla de 4×4, con claves deduplicadas en el encabezado y todos los valores/importes en orden. El documento de entrada no tiene tabla nativa. |
| 5. Acta | [DOCX](05_acta/document.docx), [JSON](05_acta/golden.json) | Título, secciones de asistentes/acuerdos/cierre y listas. Fechas, horas e importe permanecen exactos. |
| 6. Bloques opacos | [DOCX](06_bloques_keep/document.docx), [JSON](06_bloques_keep/golden.json) | Dos imágenes originales, una tabla nativa y dos secciones —vertical y horizontal— conservadas mediante `keep`. |
| 7. Inyección | [DOCX](07_prompt_injection/document.docx), [JSON](07_prompt_injection/golden.json) | Las órdenes incrustadas, etiquetas de cierre y JSON con rol falso permanecen como párrafos literales. No se resumen ni se ejecutan; cifras y contenido siguen intactos. |
| 8. Ya estructurado | [DOCX](08_bien_estructurado/document.docx), [JSON](08_bien_estructurado/golden.json) | Preserva Title, H1/H2, listas nativas ordenadas y no ordenadas de tres niveles, párrafos y tabla existente. |

El `sectPr` final de Word aparece como `keep` incluso en los documentos sin
recursos opacos adicionales. Los IDs `b0`, `b1`, etc. representan hijos del body,
tal como los define el extractor v2.

## Contrato de los golden JSON

Los campos `schema_version`, `chunk_id` y `blocks` cumplen `AIChunkOutput`.
Cada bloque declara `type`, `src`, texto y, cuando corresponde, `level`,
`is_numbered`, `header_row` y `rows`. Los párrafos nunca llevan `generated`.

Metadatos adicionales:

- `fixture_id`, `scenario`, `golden_version` y `document` identifican el caso.
- `source_sha256` vincula la anotación al DOCX exacto; cambiar el binario obliga a
  revisar la correspondencia del golden.
- `options` fija las detecciones activas y `emphasis=none`, para evaluar estructura
  sin introducir nuevas negritas. Se conserva la negrita ya existente.
- `expected_tables` incluye matrices de texto y origen tanto para tablas creadas
  como para tablas nativas preservadas mediante `keep`. En el caso 4, los
  encabezados ya existen como claves; no son texto generado.
- `expected_keep_kinds` e `invariants` especifican recursos, secciones y condiciones
  particulares de cada escenario.
- `review` registra la aprobación humana por separado de la validación técnica.

## Validación técnica y reproducción

Desde `backend`:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_ai_corpus.py --ds=core.test_settings -q
.\venv\Scripts\python.exe tests/ai_fixtures/generate_documents.py --check
.\venv\Scripts\python.exe tests/ai_fixtures/evaluate.py
```

Las pruebas comprueban JSON sin claves duplicadas, esquema del DI, hash de cada
DOCX, cobertura y orden de todos los bloques, integridad, tablas, estilos y niveles
nativos. También reconstruyen los ocho documentos y comprueban que los `keep`
retienen su XML, imágenes y secciones. Los resultados ideales se comparan con
el validador; no se exige que el heurístico o un modelo ya alcancen esa calidad.

`generate_documents.py` produce los ocho documentos desde código con contenido
sintético. Fija metadatos y timestamps ZIP para obtener binarios reproducibles con
la versión de `python-docx` del proyecto. **Nunca genera ni sobrescribe goldens.**
Para modificar el corpus, actualizar el generador, regenerar los DOCX, revisar
manualmente los goldens afectados y renovar su `source_sha256`. Cualquier cambio
de anotación o documento invalida la aprobación anterior y requiere nueva revisión.

## Medición de respuestas guardadas

Guardar una respuesta `AIChunkOutput` completa por documento en
`predictions/<fixture_id>.json`. El evaluador no llama a la red ni al proveedor:

```powershell
.\venv\Scripts\python.exe tests/ai_fixtures/evaluate.py --predictions predictions
```

Por caso devuelve:

- `classification_accuracy`: proporción de orígenes con tipo, nivel y modalidad de
  lista correctos; incluye referencias omitidas o inventadas en el denominador.
- `exact_structure`: coincidencia de tipos, niveles, modalidad de lista, orígenes
  y orden de todos los bloques. Ignora IDs de salida y `chunk_id`.
- `exact_created_tables`: igualdad de matrices, orden, spans y encabezados de las
  tablas creadas. Las tablas nativas se evalúan mediante sus referencias `keep`
  y la validación del DOCX de entrada.
- `integrity_ok` y `violations`: resultado del validador de integridad del proyecto.

Una respuesta ausente o inválida se reporta como error. El proceso termina con
código 1 si algún caso falla integridad, estructura o tablas. No se interpreta la
segmentación de runs como una diferencia estructural.

## Revisión cruzada

**Revisor designado por el usuario: `Os-corona`. Estado inicial: pendiente.**
Las pruebas técnicas en verde no equivalen a una aprobación humana. El PR del
corpus solicita la revisión cruzada de los ocho archivos y debe conservar evidencia
de esa aprobación.

Checklist para cada par:

1. Abrir el DOCX y comprobar que representa el escenario de la tabla anterior.
2. Verificar cada `src`, tipo y nivel, y que todas las palabras, cifras y fechas
   reales del caso se conserven en el mismo orden.
3. Revisar las tablas esperadas, eliminación de prefijos y deduplicación de claves.
4. Confirmar que imágenes, tabla nativa y secciones se preserven como `keep`.
5. En el caso 7, tratar las órdenes como datos; en el caso 8, conservar la estructura
   que ya es correcta.
6. Emitir una aprobación o solicitar cambios en el PR, indicando los casos revisados.

Solo tras una aprobación real se actualiza `review.status` a `approved`, junto con
`reviewer`, `reviewed_at` (ISO 8601 con zona), `evidence_url` (enlace a la revisión
de GitHub) y `reviewed_content_sha256`. Este último se calcula con
`evaluate.golden_fingerprint(golden)`, que excluye el campo `review` para evitar
una huella circular. La huella detecta aprobaciones desactualizadas; el enlace
permite auditar la aprobación humana registrada.

Para verificar el criterio de aceptación de revisión:

```powershell
.\venv\Scripts\python.exe tests/ai_fixtures/evaluate.py --require-review
```

Este comando falla mientras alguno de los ocho goldens no tenga una aprobación
registrada para su contenido actual. No se deben rellenar los datos de aprobación
con la validación automática ni con una revisión del propio autor.
