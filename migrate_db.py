"""
migrate_db.py — Migración incremental de edu_gen.db
Agrega las columnas y tablas nuevas sin perder datos existentes.
Ejecutar UNA SOLA VEZ antes de arrancar el servidor.

Uso:
    python migrate_db.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "edu_gen.db")

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def table_exists(cursor, table):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None

def run():
    print(f"Conectando a {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- documents: agregar current_version ---
    if not column_exists(cur, "documents", "current_version"):
        cur.execute("ALTER TABLE documents ADD COLUMN current_version INTEGER DEFAULT 1")
        print("✅ documents.current_version añadida")
    else:
        print("⏩ documents.current_version ya existe")

    # --- document_versions ---
    if not table_exists(cur, "document_versions"):
        cur.execute("""
            CREATE TABLE document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL REFERENCES documents(id),
                version_num INTEGER NOT NULL,
                content TEXT NOT NULL,
                change_label TEXT DEFAULT 'Edición',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Tabla document_versions creada")
    else:
        print("⏩ Tabla document_versions ya existe")

    # --- pipeline_runs ---
    if not table_exists(cur, "pipeline_runs"):
        cur.execute("""
            CREATE TABLE pipeline_runs (
                id TEXT PRIMARY KEY,
                document_id TEXT REFERENCES documents(id),
                tipo TEXT,
                area_curricular TEXT,
                grado TEXT,
                metodologia TEXT,
                puntaje_validacion INTEGER DEFAULT 0,
                errores_criticos INTEGER DEFAULT 0,
                errores_advertencia INTEGER DEFAULT 0,
                correcciones_aplicadas INTEGER DEFAULT 0,
                tokens_aprox INTEGER DEFAULT 0,
                duracion_ms INTEGER DEFAULT 0,
                llm_model TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Tabla pipeline_runs creada")
    else:
        print("⏩ Tabla pipeline_runs ya existe")

    conn.commit()
    conn.close()
    print("\n🎉 Migración completa. Puedes arrancar el servidor.")

if __name__ == "__main__":
    run()
