# HU-42: Matriz axiológica institucional estructurada (Valor | Enfoque | Comportamiento observable | Instrumento)

**Épica:** Generación / Personalización institucional | **Prioridad:** Media | **Esfuerzo:** M

**Como** docente, **quiero** que la sección de valores y enfoques transversales se genere como una matriz con una fila por cada par valor-enfoque, indicando su comportamiento observable e instrumento de evaluación, **para** que coincida con el formato de matriz axiológica que usa mi institución en lugar de un párrafo único.

## Contexto

La reunión de planificación concluyó que *"se utiliza una matriz axiológica específica para integrar valores y enfoques transversales en la planificación."* `Unidad ejemplo.docx`, Tabla 4, confirma el formato real usado: columnas **"Valor | Enfoques transversales | Comportamientos observables | Instrumento"**, con una fila por combinación (ej. *"Fe, Amor | Búsqueda de la excelencia. Enfoque ambiental | Persevera ante errores del programa y actúa con honestidad en el uso del código."*).

`src/prompts/unidad_didactica.md` (línea 53) genera esto hoy como una única celda de texto libre: *"Valores: {valores_texto}. Enfoques: {enfoques_texto}. Comportamientos observables: [...]"* — sin estructura de filas ni columna de instrumento. **HU-36** ya resuelve **qué** lista de valores/enfoques usar (configurable, no hardcodeada a un colegio católico específico) pero no **cómo** se presentan; esta historia extiende HU-36/HU-31 al formato de salida, no a la fuente de datos.

## Criterios de aceptación

- `unidad_didactica.md` (y la sección "ENFOQUE TRANSVERSAL" de `sesion_aprendizaje.md`) generan los valores como tabla de filas Valor | Enfoque | Comportamiento observable | Instrumento, una fila por combinación resuelta por `resolver_valores_institucionales()` / `resolver_enfoques_transversales()` (HU-36).
- Si el `InstitutionProfile` (HU-31) trae su propia matriz axiológica, se usa esa; si no, se arma con el default genérico CNEB emparejando valores y enfoques.
- `StructureValidator` ajusta su verificación de `"VALORES"` para aceptar el nuevo formato tabular.

## Notas de implementación

- Depende de que HU-31 modele `valores_institucionales` con suficiente estructura — puede requerir ampliarlo de una lista plana de nombres a una lista de objetos `{valor, enfoque, comportamiento_observable, instrumento}`.

**Archivos relevantes:** `src/prompts/unidad_didactica.md`, `src/prompts/sesion_aprendizaje.md`, `src/core/valores_institucionales.py`, `src/validators/structure_validator.py`

**Depende de / relaciona con:** HU-31, HU-36
**Fuente:** notas de reunión ("Matriz de Valores" / matriz axiológica); `Unidad ejemplo.docx` (Tabla 4)
