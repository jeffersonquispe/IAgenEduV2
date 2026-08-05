#!/usr/bin/env python3
"""
Servidor principal: levanta la API FastAPI con Uvicorn.
Uso: python run.py
"""
import sys
import os
from pathlib import Path

# Cargar variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configurar PYTHONPATH para que los imports relativos de src/ funcionen
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))
os.environ.setdefault("AWS_REGION", "us-east-1")

# Verificar uvicorn
try:
    import uvicorn
except ImportError:
    print("[ERROR] uvicorn no esta instalado.")
    print("[INFO] Ejecuta: pip install uvicorn")
    sys.exit(1)

print("[INFO] Iniciando servidor FastAPI (EduGen AI)...")
print(f"[INFO] Directorio: {os.getcwd()}")
print(f"[INFO] API disponible en: http://localhost:8000")
print(f"[INFO] Docs interactivos: http://localhost:8000/docs")
print("")

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["src"],
    )