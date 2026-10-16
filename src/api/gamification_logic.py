from datetime import datetime, timedelta
from typing import List, Dict, Any

# Badges Definition (Same as original but for backend)
BADGES = [
    {"id": "primer_paso", "nombre": "Primer Paso 🌱", "descripcion": "Generaste tu primer documento educativo.", "emoji": "🌱"},
    {"id": "explorador", "nombre": "Explorador Curricular 🗺️", "descripcion": "Has usado 3 áreas curriculares distintas.", "emoji": "🗺️"},
    {"id": "maestro_detalle", "nombre": "Maestro del Detalle ✨", "descripcion": "Has realizado 5 mejoras a tus documentos.", "emoji": "✨"},
    {"id": "multi_grado", "nombre": "Multi-grado 📚", "descripcion": "Has generado contenido para 3 grados diferentes.", "emoji": "📚"},
    {"id": "prolifico", "nombre": "Prolífico 🏅", "descripcion": "Has generado 10 documentos en total.", "emoji": "🏅"},
    {"id": "exportador", "nombre": "Exportador Pro 📄", "descripcion": "Has exportado 5 documentos a DOCX o PDF.", "emoji": "📄"},
    {"id": "maraton", "nombre": "Maratón 🔥", "descripcion": "Mantuviste una racha de 3 días de uso.", "emoji": "🔥"},
    {"id": "perfeccionista", "nombre": "Perfeccionista 💎", "descripcion": "Realizaste 10 mejoras de IA.", "emoji": "💎"},
]

# HU-38: puntos por acción directa (regla documentada en DETALLES_TECNICOS §9 y
# ya usada por la app legacy en src/app/gamification.py).
PUNTOS_POR_DOCUMENTO = 10
PUNTOS_POR_MEJORA = 5
PUNTOS_POR_EXPORTACION = 15
PUNTOS_POR_INSIGNIA = 20


def calcular_puntos(stats: Any) -> int:
    """Puntos totales derivados de los contadores del usuario.

    Se calcula (no se acumula con incrementos sueltos en cada ruta) para que sea
    idempotente y no se desincronice: GET /auth/stats ya recalcula insignias y
    nivel en cada llamada, y es el único lugar que persiste `puntos`.
    """
    exportaciones = (stats.exportaciones_docx or 0) + (stats.exportaciones_pdf or 0)
    return (
        (stats.docs_generados or 0) * PUNTOS_POR_DOCUMENTO
        + (stats.mejoras_realizadas or 0) * PUNTOS_POR_MEJORA
        + exportaciones * PUNTOS_POR_EXPORTACION
        + len(stats.badges_desbloqueados or []) * PUNTOS_POR_INSIGNIA
    )


def calcular_nivel(puntos: int) -> Dict[str, Any]:
    if puntos < 100:
        return {"nombre": "Principiante", "icono": "🌱", "progreso": puntos / 100}
    elif puntos < 300:
        return {"nombre": "Intermedio", "icono": "🌿", "progreso": (puntos - 100) / 200}
    elif puntos < 600:
        return {"nombre": "Avanzado", "icono": "🌳", "progreso": (puntos - 300) / 300}
    elif puntos < 1000:
        return {"nombre": "Experto", "icono": "👑", "progreso": (puntos - 600) / 400}
    else:
        return {"nombre": "Maestro", "icono": "💎", "progreso": 1.0}

def calcular_racha(dias_uso: List[str]) -> int:
    if not dias_uso: return 0
    dias_ordenados = sorted(list(set(dias_uso)), reverse=True)
    hoy = datetime.now().date()
    ayer = hoy - timedelta(days=1)
    
    ultima_fecha = datetime.strptime(dias_ordenados[0], "%Y-%m-%d").date()
    if ultima_fecha != hoy and ultima_fecha != ayer:
        return 0
        
    racha = 1
    fecha_actual = ultima_fecha
    for i in range(1, len(dias_ordenados)):
        fecha_sig = datetime.strptime(dias_ordenados[i], "%Y-%m-%d").date()
        if (fecha_actual - fecha_sig).days == 1:
            racha += 1
            fecha_actual = fecha_sig
        else:
            break
    return racha

def check_new_badges(stats: Any) -> List[str]:
    nuevos = []
    ids_actuales = stats.badges_desbloqueados or []
    
    conditions = {
        "primer_paso": stats.docs_generados >= 1,
        "explorador": len(stats.areas_usadas or []) >= 3,
        "maestro_detalle": stats.mejoras_realizadas >= 5,
        "multi_grado": len(stats.grados_usados or []) >= 3,
        "prolifico": stats.docs_generados >= 10,
        "exportador": (stats.exportaciones_docx + stats.exportaciones_pdf) >= 5,
        "maraton": calcular_racha(stats.dias_uso or []) >= 3,
        "perfeccionista": stats.mejoras_realizadas >= 10,
    }
    
    for badge_id, condition in conditions.items():
        if condition and badge_id not in ids_actuales:
            nuevos.append(badge_id)
            
    return nuevos
