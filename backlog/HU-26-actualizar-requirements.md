# HU-26: `requirements.txt` fiel a las dependencias reales

**Épica:** Calidad técnica | **Prioridad:** Alta | **Esfuerzo:** S

**Como** desarrollador que clona el proyecto por primera vez, **quiero** que `requirements.txt` instale todo lo necesario para correr la app activa (FastAPI + React), **para** no descubrir en pleno arranque que faltan `fastapi`, `sqlalchemy`, `uvicorn`, etc.

## Contexto

`requirements.txt` solo lista `streamlit`, `boto3`, `pyngrok`, `python-dotenv`, `python-docx`, `debugpy` — las dependencias de la app Streamlit legacy. El venv actual del proyecto sí tiene instalados `fastapi==0.135.1`, `sqlalchemy==2.0.48`, `uvicorn==0.41.0`, `pydantic==2.12.5`, `python-jose==3.5.0`, `passlib==1.7.4`, `python-docx==1.2.0`, `fpdf2==2.8.7` (y `weasyprint`, mencionado en `docs/DETALLES_TECNICOS.md` §14), pero **ninguno de estos aparece en `requirements.txt`**. `pip install -r requirements.txt` desde cero no deja el proyecto en un estado funcional para `python run.py`.

## Criterios de aceptación

- `requirements.txt` (o un `requirements-api.txt` separado, si se prefiere no mezclar ambas apps) incluye todas las dependencias que usa realmente `src/api/` y `src/agents/`.
- Verificación: en un venv nuevo, `pip install -r requirements.txt` seguido de `python run.py` levanta el servidor sin `ModuleNotFoundError`.
- `CLAUDE.md` se actualiza para quitar la nota sobre la discrepancia una vez resuelta.

## Notas de implementación

- Generar la lista real con `pip freeze` desde el venv actual (ya usado para diagnosticar esto) y depurarla a las dependencias directas, no todo el árbol transitivo.

**Archivos relevantes:** `requirements.txt`, `CLAUDE.md`
