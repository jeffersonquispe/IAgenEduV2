# HU-35: Corregir el ensamblado de competencias múltiples en el prompt

**Épica:** Calidad del contenido generado | **Prioridad:** Media | **Esfuerzo:** S

**Como** docente, **quiero** que cuando elijo varias competencias para una Unidad, el modelo reciba la instrucción reforzada de usar exactamente esas competencias, **para** que el documento generado no trate mi selección múltiple como si fuera una sola competencia.

## Contexto

Documentado en `docs/REGLAS_DE_NEGOCIO.md` §1.3. El backend une las competencias seleccionadas en el wizard con `", "`:

```python
competencias_texto = ", ".join(competencias) if isinstance(competencias, list) else competencias
```

pero `GeneratorAgent._construir_contexto_competencia()` espera separarlas por salto de línea para tratarlas como lista:

```python
competencias_lista = [c.strip() for c in competencia.split('\n') if c.strip()]
if len(competencias_lista) > 1:
    ...  # "COMPETENCIAS OBLIGATORIAS (USAR SOLO ESTAS): ... Usa EXACTAMENTE estas N."
else:
    ...  # "COMPETENCIA OBLIGATORIA (USAR SOLO ESTA): ... Usa SOLO esta competencia."
```

Como la unión usa `", "` y no `"\n"`, `competencias_lista` siempre tiene longitud 1 cuando llegan 2+ competencias — cae en la rama `else`, pensada para una sola competencia. El contenido de todas las competencias sigue llegando al modelo (van todas dentro del único string), pero con la instrucción equivocada ("usa SOLO esta" en vez de "usa EXACTAMENTE estas N"), lo que puede confundir al modelo o hacer que ignore alguna.

## Criterios de aceptación

- El separador usado al ensamblar `competencias_texto` coincide con el que espera `_construir_contexto_competencia()` (cambiar el `join` a `"\n"`, o cambiar el `split` para que acepte comas — cualquiera de los dos lados, pero deben coincidir).
- Con 2+ competencias seleccionadas, el prompt final contiene el bloque "COMPETENCIAS OBLIGATORIAS (USAR SOLO ESTAS)" con cada competencia listada por separado, no un solo bloque con "usa SOLO esta".
- Con 1 sola competencia seleccionada, el comportamiento actual (rama `else`) no cambia.
- Aplica tanto al camino estándar (`GenerationService.crear_unidad`) como al de streaming (`generar_unidad_stream_events`), que arma este mismo contexto por separado.

## Notas de implementación

- Bug puramente de "cableado" entre dos funciones que asumían formatos distintos — no requiere rediseño, solo hacer coincidir el separador en ambos lados y agregar un caso de prueba con 2+ competencias para que no vuelva a divergir en silencio.

**Archivos relevantes:** `src/api/services/generation_service.py`, `src/agents/generator_agent.py::_construir_contexto_competencia`

**Fuente:** `docs/REGLAS_DE_NEGOCIO.md` §1.3
