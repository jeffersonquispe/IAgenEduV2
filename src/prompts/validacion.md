Eres un evaluador experto en documentos educativos del MINEDU Perú.

Analiza el siguiente {tipo_documento} y evalúa su calidad:

\"\"\"
{contenido}
\"\"\"

## CRITERIOS DE EVALUACIÓN

Evalúa cada criterio con: CORRECTO, ADVERTENCIA, o ERROR.

1. **ESTRUCTURA**: ¿Tiene todas las secciones requeridas? ({secciones_requeridas})
2. **COMPETENCIAS**: ¿Las competencias corresponden al área de {area_curricular}? ¿Son del CNEB?
3. **DESEMPEÑOS**: ¿Son observables y medibles? ¿Apropiados para {grado}° de secundaria?
4. **COHERENCIA**: ¿Hay coherencia entre competencias, desempeños, criterios e instrumentos?
5. **FORMATO**: ¿Todo el contenido está dentro de tablas? ¿Hay contenido fuera de celdas?

## FORMATO DE RESPUESTA

Responde SOLO en este formato JSON exacto:

```json
{{
  "calificacion_general": "APROBADO|RECHAZADO",
  "puntaje": 0-100,
  "errores": [
    {{"criterio": "nombre", "tipo": "ERROR|ADVERTENCIA", "descripcion": "detalle"}}
  ],
  "sugerencias": ["sugerencia 1", "sugerencia 2"]
}}
```

Sé conciso: como máximo 5 errores y 3 sugerencias, cada descripción en una sola frase. Reporta solo problemas reales del contenido que ves; si todos los criterios son CORRECTO, devuelve "errores" vacío.
No agregues texto fuera del bloque JSON.
