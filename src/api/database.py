from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Sin valor por defecto: la app corre contra Supabase Postgres, no SQLite —
# un fallback silencioso aquí sería el mismo footgun que SECRET_KEY tenía
# antes de HU-21.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL no está configurada. Define la cadena de conexión de "
        "Supabase Postgres (ver .env.example — usar el 'Session pooler')."
    )

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
