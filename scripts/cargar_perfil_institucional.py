"""Carga un perfil institucional (HU-31) desde un archivo JSON para un usuario.

Uso (desde la raíz del repo):
    python scripts/cargar_perfil_institucional.py <email> data/perfiles/salesiano_cusco.json --dry-run
    python scripts/cargar_perfil_institucional.py <email> data/perfiles/salesiano_cusco.json
    python scripts/cargar_perfil_institucional.py <email> data/perfiles/salesiano_cusco.json --reemplazar

Salvaguardas:
  * Valida el JSON con el mismo esquema que usa PUT /institucion.
  * Si el usuario YA tiene un perfil, no lo toca salvo que pases --reemplazar.
  * --dry-run muestra qué se guardaría sin escribir nada.
  * Las claves que empiezan con "_" (p. ej. "_fuente") son comentarios y se ignoran.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


class PerfilExistente(Exception):
    """El usuario ya tiene un perfil y no se pidió reemplazarlo."""


def leer_datos(ruta):
    """Lee y valida el JSON; devuelve un dict apto para InstitutionProfile."""
    from src.api import schemas

    crudo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    sin_comentarios = {k: v for k, v in crudo.items() if not k.startswith("_")}
    return schemas.InstitutionProfileUpdate(**sin_comentarios).model_dump()


def cargar_perfil(db, email, datos, reemplazar=False, dry_run=False):
    """Crea o reemplaza el perfil del usuario con ese email.

    Devuelve "creado", "reemplazado" o "simulado". Lanza LookupError si el
    usuario no existe y PerfilExistente si ya tiene perfil y no se pidió reemplazar.
    """
    from src.api import models

    usuario = db.query(models.User).filter(models.User.email == email).first()
    if usuario is None:
        raise LookupError(f"No existe un usuario con el email {email!r}")

    perfil = db.query(models.InstitutionProfile).filter(
        models.InstitutionProfile.user_id == usuario.id
    ).first()
    if perfil is not None and not reemplazar:
        raise PerfilExistente(
            f"{email} ya tiene un perfil institucional ({perfil.nombre_institucion!r}). "
            f"Usa --reemplazar para sobrescribirlo."
        )
    if dry_run:
        return "simulado"

    accion = "reemplazado" if perfil is not None else "creado"
    if perfil is None:
        perfil = models.InstitutionProfile(user_id=usuario.id)
        db.add(perfil)
    for campo, valor in datos.items():
        setattr(perfil, campo, valor)
    perfil.updated_at = datetime.utcnow()
    db.commit()
    return accion


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("email")
    ap.add_argument("archivo")
    ap.add_argument("--reemplazar", action="store_true", help="sobrescribe un perfil existente")
    ap.add_argument("--dry-run", action="store_true", help="no escribe en la base de datos")
    args = ap.parse_args(argv)

    datos = leer_datos(args.archivo)
    print(f"Perfil a cargar: {datos['nombre_institucion']!r}")
    for campo, valor in datos.items():
        resumen = "(vacío)" if valor in (None, "", []) else (
            f"{len(valor)} elemento(s)" if isinstance(valor, list) else f"{len(str(valor))} caracteres")
        print(f"  - {campo}: {resumen}")

    from src.api.database import SessionLocal

    db = SessionLocal()
    try:
        resultado = cargar_perfil(db, args.email, datos, reemplazar=args.reemplazar, dry_run=args.dry_run)
    except (LookupError, PerfilExistente) as e:
        print(f"ERROR: {e}")
        return 1
    finally:
        db.close()
    print({"simulado": "Simulación OK: no se escribió nada.",
           "creado": "Perfil creado.", "reemplazado": "Perfil reemplazado."}[resultado])
    return 0


if __name__ == "__main__":
    sys.exit(main())
