# Reporte de Pruebas: Pipeline de Extracción y Reconstrucción

En este documento se registran las diferencias encontradas al comparar los documentos originales del set de prueba con los documentos reconstruidos por el pipeline (`extractor` + `rebuilder`).

## 1. Párrafos simples
**Archivo:** `1_parrafos.docx`
**Diferencias encontradas:**
- Textos y estructura sin diferencias.
- Estilos: Los estilos llamados "normal" (minúscula) en el original fueron reconstruidos como "Normal" (mayúscula).

## 2. Documento con tabla
**Archivo:** `2_tabla.docx`
**Diferencias encontradas:**
- Tablas idénticas, textos idénticos.
- Estilos: Misma diferencia de mayúscula/minúscula en el estilo "Normal".

## 3. Documento con celda combinada
**Archivo:** `3_celda_combinada.docx`
**Diferencias encontradas:**
- Tablas idénticas, lo cual significa que el rebuilder procesó bien las celdas combinadas.
- Estilos: Diferencia de mayúscula/minúscula en el estilo "Normal".

## 4. Documento con imagen
**Archivo:** `4_imagen.docx`
**Diferencias encontradas:**
- Estructura y textos idénticos.
- Estilos: Diferencia de mayúscula/minúscula en el estilo "Normal".

## 5. Documento con lista
**Archivo:** `5_lista.docx`
**Diferencias encontradas:**
- Textos y estructura idénticos.
- Estilos: El rebuilder mejoró los estilos asignando explícitamente "List Bullet" y "List Number" a los elementos de las listas, mientras que en el documento original solo marcaban como "normal". 

## Conclusiones y ajustes necesarios
* El extractor y el rebuilder están funcionando muy bien en conjunto.
* Las diferencias de estilo ("normal" vs "Normal") son un detalle técnico de la librería que se puede ignorar, ya que visualmente representan el mismo estilo base.
* El manejo de las listas es adecuado, ya que el rebuilder aplica correctamente los estilos de lista nativos de Word (`List Bullet` y `List Number`).
* No parece haber ajustes urgentes requeridos para la reconstrucción básica de cara al Sprint 2, el pipeline actual está listo para empezar a integrarse.
