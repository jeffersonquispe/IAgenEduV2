# HU-36: Hacer configurables los valores y enfoques transversales institucionales

> ✅ **Implementada la parte urgente** (default neutral), pendiente la parte que depende de HU-31. Nuevo módulo `src/core/valores_institucionales.py`: `VALORES_CNEB_DEFAULT` (genérico, sin contenido confesional) es ahora el default real usado por `generator_agent.py` y `legacy_generator.py` — ambos importaban la constante hardcodeada por separado (duplicada), ahora ambos llaman a `resolver_valores_institucionales()`/`resolver_enfoques_transversales()`. El listado católico original se conserva como `VALORES_CATOLICO_PRESET`, disponible pero ya no es el comportamiento por defecto. Verificado que el prompt real generado ya no contiene "Jesucristo". Las funciones `resolver_*` ya aceptan un `institution_profile` opcional — es el punto de extensión listo para que HU-31/HU-32 lo conecten cuando exista perfil institucional persistente; **sin HU-31 implementada, ese caso sigue pendiente**.

**Épica:** Generación / Personalización institucional | **Prioridad:** Alta | **Esfuerzo:** S-M

**Como** docente de cualquier institución (no solo confesional/católica), **quiero** que los valores y enfoques transversales que aparecen en mis documentos correspondan a mi propia institución, **para** no recibir documentos con valores religiosos específicos que no representan a mi colegio.

## Contexto

Documentado en `docs/REGLAS_DE_NEGOCIO.md` §1.7 — hallazgo de severidad alta. `generator_agent.py` tiene hardcodeadas dos listas que **no son los valores genéricos del CNEB/MINEDU**, sino los de una institución católica/parroquial específica:

```python
VALORES_PERMITIDOS = [
    "Participación", "Respeto", "Solidaridad", "Conciencia crítica",
    "Compromiso ambiental", "Apertura y acogida", "Gratitud y donación",
    "Compasión y misericordia", "Cuidado y promoción de la vida",
    "Discernimiento y compromiso", "Encuentro personal con Jesucristo",
    "Caridad", "Experiencia comunitaria de la fe",
]
```

Todo documento generado hoy, sin importar qué colegio use el sistema, incluye esta lista en la sección "Valores y Enfoques Transversales". Esto hace que el sistema no sea institucionalmente neutral — un problema real si se piensa en distribuir la herramienta más allá del colegio para el que se escribió originalmente.

## Criterios de aceptación

- `VALORES_PERMITIDOS` y `ENFOQUES_TRANSVERSALES_PERMITIDOS` dejan de ser constantes hardcodeadas de un único colegio y pasan a ser configurables por institución.
- Si el docente tiene un `InstitutionProfile` (HU-31) con `valores_institucionales` propios, el generador los usa en vez de la lista actual.
- Si no hay perfil institucional configurado, el sistema usa como *default* los **valores genéricos del CNEB/MINEDU** (no los actuales, que son de una institución específica) — para que un docente que nunca configuró su perfil no reciba contenido confesional por defecto.
- La lista actual (los 13 valores católicos) queda disponible como una opción más que un colegio confesional puede elegir explícitamente, no como el comportamiento por defecto del sistema.

## Notas de implementación

- **Depende de HU-31** para el caso "perfil configurado". El caso "sin perfil → usar default genérico MINEDU" se puede resolver antes, de forma independiente, y es la parte más urgente de esta historia (es la que corrige la falta de neutralidad hoy).
- Si se implementa antes que HU-31, dejar el punto de extensión ya preparado (una función que resuelva "¿qué valores usar?" en vez de la constante importada directamente) para que HU-32 solo tenga que conectar la fuente institucional cuando exista.

**Archivos relevantes:** `src/agents/generator_agent.py` (`VALORES_PERMITIDOS`, `ENFOQUES_TRANSVERSALES_PERMITIDOS`)

**Depende de / relaciona con:** **HU-31**, **HU-32**
**Fuente:** `docs/REGLAS_DE_NEGOCIO.md` §1.7
