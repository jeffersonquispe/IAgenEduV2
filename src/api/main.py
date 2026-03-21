from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import auth, generation, export, data, metrics

# Create DB tables (new tables: document_versions, pipeline_runs auto-created)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Generador Educativo API",
    description="Backend API para la plataforma de generación de documentos educativos",
    version="2.1.0"
)

# Configure CORS for React frontend (Vite defaults to port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(generation.router)
app.include_router(export.router)
app.include_router(data.router)
app.include_router(metrics.router)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API del Generador Educativo AI", "status": "online"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
