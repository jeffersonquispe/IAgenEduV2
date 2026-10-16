"""HU-33: verificación estática del frontend (wizard y Dashboard) y de la etapa del job."""
from pathlib import Path
from types import SimpleNamespace

from src.api.services import job_service

ROOT = Path(__file__).resolve().parents[2]


def _leer(ruta):
    return (ROOT / ruta).read_text(encoding="utf-8")


def test_etapa_pasa_de_generando_a_validando():
    job = SimpleNamespace(id="j1", tipo="unidad", status="running", error=None,
                          result_document_id=None, created_at=None, updated_at=None)
    assert job_service.serializar(job)["etapa"] == "generando"
    job_service._validando.add("j1")
    try:
        assert job_service.serializar(job)["etapa"] == "validando"
    finally:
        job_service._validando.discard("j1")


def test_wizard_usa_jobs_con_polling_y_no_el_stream():
    src = _leer("frontend/src/components/GenerationWizard.jsx")
    assert "/generate/unidad/jobs" in src and "/generate/sesion/jobs" in src
    assert "/generate/jobs/${jobId}" in src
    assert "/stream'" not in src                      # ya no depende de la conexión SSE abierta
    assert "streamGenerate" not in src


def test_wizard_cerrar_detiene_el_polling_pero_no_cancela_el_job():
    src = _leer("frontend/src/components/GenerationWizard.jsx")
    # La X y Esc pasan por pedirCierre (confirma si hay datos y no hay generación en curso) y de ahí a handleClose.
    assert "const handleClose" in src and "onClick={pedirCierre}" in src and "handleClose()" in src
    assert "ejecucion.current === miEjecucion" in src     # el bucle viejo no reanima ni pisa estado
    assert "DELETE" not in src.upper().replace("DELETED", "")   # no existe cancelación en el servidor


def test_dashboard_muestra_jobs_en_curso_y_refresca_los_recientes():
    src = _leer("frontend/src/pages/Dashboard.jsx")
    assert "/generate/jobs" in src
    assert 'aria-label="Generaciones en curso"' in src
    assert "fetchDocsRef.current(0)" in src               # al terminar un job aparece en Recientes
    assert "setInterval(fetchJobs" in src                 # polling solo mientras hay jobs activos


def test_la_migracion_define_la_tabla_de_jobs():
    sql = _leer("supabase/migrations/20261008_generation_jobs.sql")
    for col in ("id", "user_id", "tipo", "status", "params", "result_document_id", "error",
                "created_at", "updated_at"):
        assert f"\n    {col} " in sql, col
    assert "IF NOT EXISTS generation_jobs" in sql
