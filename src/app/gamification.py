"""
Módulo de Gamificación para el Generador Educativo AI.
Maneja estadísticas del usuario, sistema de badges/logros,
y componentes de UI para Streamlit.
"""

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st


# ─────────────────────────────────────────────
# Ruta de persistencia
# ─────────────────────────────────────────────
def _stats_path() -> Path:
    """Retorna la ruta del archivo de estadísticas del usuario."""
    home = Path.home()
    stats_dir = home / ".edu_gen"
    stats_dir.mkdir(parents=True, exist_ok=True)
    return stats_dir / "user_stats.json"


# ─────────────────────────────────────────────
# Modelo de estadísticas
# ─────────────────────────────────────────────
_DEFAULT_STATS = {
    "docs_generados": 0,
    "unidades_generadas": 0,
    "sesiones_generadas": 0,
    "mejoras_realizadas": 0,
    "exportaciones_docx": 0,
    "exportaciones_txt": 0,
    "areas_usadas": [],
    "grados_usados": [],
    "dias_uso": [],          # lista de fechas "YYYY-MM-DD"
    "badges_desbloqueados": [],
    "primera_visita": True,
    "fecha_registro": None,
}


def load_stats() -> dict:
    """Carga estadísticas del usuario desde disco."""
    path = _stats_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Rellenar campos faltantes con valores por defecto
            for k, v in _DEFAULT_STATS.items():
                if k not in data:
                    data[k] = v if not isinstance(v, list) else list(v)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {k: (list(v) if isinstance(v, list) else v) for k, v in _DEFAULT_STATS.items()}


def save_stats(stats: dict):
    """Guarda estadísticas del usuario a disco."""
    path = _stats_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _ensure_session_stats():
    """Carga stats en session_state si aún no existen."""
    if "user_stats" not in st.session_state:
        st.session_state["user_stats"] = load_stats()
        # Registrar fecha de registro si es la primera vez
        stats = st.session_state["user_stats"]
        if stats.get("fecha_registro") is None:
            stats["fecha_registro"] = datetime.now().strftime("%Y-%m-%d")
            save_stats(stats)


def _registrar_dia():
    """Registra el día actual si no está registrado."""
    _ensure_session_stats()
    stats = st.session_state["user_stats"]
    hoy = datetime.now().strftime("%Y-%m-%d")
    if hoy not in stats["dias_uso"]:
        stats["dias_uso"].append(hoy)
        save_stats(stats)


# ─────────────────────────────────────────────
# Registro de eventos
# ─────────────────────────────────────────────
def registrar_generacion(tipo: str, area: str = "", grado: str = ""):
    """Registra una generación de documento (unidad o sesión)."""
    _ensure_session_stats()
    stats = st.session_state["user_stats"]
    stats["docs_generados"] += 1
    if tipo == "unidad":
        stats["unidades_generadas"] += 1
    elif tipo == "sesion":
        stats["sesiones_generadas"] += 1
    if area and area not in stats["areas_usadas"]:
        stats["areas_usadas"].append(area)
    if grado and grado not in stats["grados_usados"]:
        stats["grados_usados"].append(grado)
    _registrar_dia()
    save_stats(stats)


def registrar_mejora():
    """Registra una mejora de documento vía chat."""
    _ensure_session_stats()
    stats = st.session_state["user_stats"]
    stats["mejoras_realizadas"] += 1
    _registrar_dia()
    save_stats(stats)


def registrar_exportacion(formato: str):
    """Registra una exportación (docx o txt)."""
    _ensure_session_stats()
    stats = st.session_state["user_stats"]
    if formato == "docx":
        stats["exportaciones_docx"] += 1
    elif formato == "txt":
        stats["exportaciones_txt"] += 1
    _registrar_dia()
    save_stats(stats)


# ─────────────────────────────────────────────
# Sistema de Badges
# ─────────────────────────────────────────────
BADGES = [
    {
        "id": "primer_paso",
        "nombre": "Primer Paso",
        "icono": "🌱",
        "descripcion": "Generaste tu primer documento",
        "condicion": lambda s: s["docs_generados"] >= 1,
    },
    {
        "id": "explorador",
        "nombre": "Explorador Curricular",
        "icono": "🗺️",
        "descripcion": "Generaste documentos en 3 áreas distintas",
        "condicion": lambda s: len(s["areas_usadas"]) >= 3,
    },
    {
        "id": "maestro_detalle",
        "nombre": "Maestro del Detalle",
        "icono": "✨",
        "descripcion": "Mejoraste un documento 3+ veces con el chat",
        "condicion": lambda s: s["mejoras_realizadas"] >= 3,
    },
    {
        "id": "multi_grado",
        "nombre": "Multi-grado",
        "icono": "📚",
        "descripcion": "Generaste para 3 grados diferentes",
        "condicion": lambda s: len(s["grados_usados"]) >= 3,
    },
    {
        "id": "prolifico",
        "nombre": "Prolífico",
        "icono": "🏅",
        "descripcion": "Generaste 10 documentos",
        "condicion": lambda s: s["docs_generados"] >= 10,
    },
    {
        "id": "exportador_pro",
        "nombre": "Exportador Pro",
        "icono": "📄",
        "descripcion": "Exportaste en formato DOCX 5 veces",
        "condicion": lambda s: s["exportaciones_docx"] >= 5,
    },
    {
        "id": "maraton",
        "nombre": "Maratón",
        "icono": "🔥",
        "descripcion": "Usaste la app 5 días consecutivos",
        "condicion": lambda s: _calcular_racha(s) >= 5,
    },
    {
        "id": "perfeccionista",
        "nombre": "Perfeccionista",
        "icono": "💎",
        "descripcion": "Mejoraste documentos 10+ veces con el chat",
        "condicion": lambda s: s["mejoras_realizadas"] >= 10,
    },
]


def _calcular_racha(stats: dict) -> int:
    """Calcula la racha actual de días consecutivos de uso."""
    dias = sorted(stats.get("dias_uso", []), reverse=True)
    if not dias:
        return 0
    hoy = datetime.now().strftime("%Y-%m-%d")
    # Si el día más reciente no es hoy ni ayer, la racha está rota
    ultimo = datetime.strptime(dias[0], "%Y-%m-%d")
    hoy_dt = datetime.strptime(hoy, "%Y-%m-%d")
    if (hoy_dt - ultimo).days > 1:
        return 0
    racha = 1
    for i in range(1, len(dias)):
        dia_actual = datetime.strptime(dias[i - 1], "%Y-%m-%d")
        dia_anterior = datetime.strptime(dias[i], "%Y-%m-%d")
        if (dia_actual - dia_anterior).days == 1:
            racha += 1
        else:
            break
    return racha


def _calcular_nivel(stats: dict) -> tuple:
    """Retorna (nombre_nivel, progreso_0_1, icono) del usuario."""
    docs = stats["docs_generados"]
    mejoras = stats["mejoras_realizadas"]
    puntos = docs * 10 + mejoras * 5 + len(stats["badges_desbloqueados"]) * 20

    niveles = [
        (0,   "Principiante",  "🌱", 100),
        (100, "Intermedio",    "⭐", 300),
        (300, "Avanzado",      "🏆", 600),
        (600, "Experto",       "👑", 1000),
        (1000, "Maestro",      "💎", 2000),
    ]

    nivel_actual = niveles[0]
    siguiente = niveles[1] if len(niveles) > 1 else None

    for i, (umbral, nombre, icono, _) in enumerate(niveles):
        if puntos >= umbral:
            nivel_actual = (umbral, nombre, icono, niveles[i][3])
            siguiente = niveles[i + 1] if i + 1 < len(niveles) else None

    umbral_actual = nivel_actual[0]
    umbral_siguiente = siguiente[0] if siguiente else nivel_actual[3]
    rango = max(umbral_siguiente - umbral_actual, 1)
    progreso = min((puntos - umbral_actual) / rango, 1.0)

    return nivel_actual[1], progreso, nivel_actual[2], puntos


def check_and_celebrate():
    """
    Verifica si se desbloquearon nuevos badges.
    Retorna lista de badges recién desbloqueados.
    """
    _ensure_session_stats()
    stats = st.session_state["user_stats"]
    nuevos = []
    for badge in BADGES:
        if badge["id"] not in stats["badges_desbloqueados"]:
            try:
                if badge["condicion"](stats):
                    stats["badges_desbloqueados"].append(badge["id"])
                    nuevos.append(badge)
            except Exception:
                pass
    if nuevos:
        save_stats(stats)
    return nuevos


def celebrar_badges(nuevos_badges: list):
    """Muestra celebración visual cuando se desbloquean badges."""
    if not nuevos_badges:
        return
    st.balloons()
    for badge in nuevos_badges:
        st.toast(
            f"{badge['icono']} ¡Logro desbloqueado: **{badge['nombre']}**!",
            icon="🎉"
        )


# ─────────────────────────────────────────────
# Mensajes motivacionales
# ─────────────────────────────────────────────
_MENSAJES_GENERACION = {
    "Ciencia y Tecnología": [
        "🔬 ¡Excelente! La ciencia transforma vidas. Generando tu material...",
        "🧪 ¡CTyA es un área con mucha demanda! Preparando contenido innovador...",
    ],
    "Matemática": [
        "📐 ¡Las matemáticas son la base de todo! Creando tu unidad...",
        "🔢 ¡Gran elección! Generando material con secuencias didácticas potentes...",
    ],
    "Comunicación": [
        "📝 ¡Comunicación es clave para el desarrollo integral! Trabajando en ello...",
        "📖 ¡Lenguaje y comunicación! Creando actividades de comprensión...",
    ],
    "_default": [
        "📚 ¡Muy bien! Generando material alineado al currículo nacional...",
        "🎯 ¡Excelente elección! Preparando contenido pedagógico de calidad...",
        "✨ ¡Vamos! Creando material educativo generado con IA...",
    ],
}

_MENSAJES_MEJORA = [
    "✏️ ¡Buena idea! Refinando tu documento para hacerlo aún mejor...",
    "🔧 ¡Perfeccionando! Los mejores documentos se pulen con iteraciones...",
    "💡 ¡Excelente sugerencia! Aplicando los cambios...",
]


def get_mensaje_generacion(area: str = "") -> str:
    """Retorna un mensaje motivacional contextual para generación."""
    mensajes = _MENSAJES_GENERACION.get(area, _MENSAJES_GENERACION["_default"])
    return random.choice(mensajes)


def get_mensaje_mejora() -> str:
    """Retorna un mensaje motivacional para mejoras."""
    return random.choice(_MENSAJES_MEJORA)


# ─────────────────────────────────────────────
# Componentes de UI – Sidebar
# ─────────────────────────────────────────────
def render_sidebar_stats():
    """Renderiza el panel de estadísticas y badges en el sidebar."""
    _ensure_session_stats()
    _registrar_dia()
    stats = st.session_state["user_stats"]

    nombre_nivel, progreso, icono_nivel, puntos = _calcular_nivel(stats)
    racha = _calcular_racha(stats)
    total_badges = len(BADGES)
    desbloqueados = len(stats["badges_desbloqueados"])

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🏆 Tu Progreso")

        # Nivel y puntos
        st.markdown(
            f"**{icono_nivel} Nivel:** {nombre_nivel} · `{puntos} pts`"
        )
        st.progress(progreso, text=f"Progreso al siguiente nivel")

        # Estadísticas rápidas en columnas
        c1, c2, c3 = st.columns(3)
        c1.metric("📄 Docs", stats["docs_generados"])
        c2.metric("✏️ Mejoras", stats["mejoras_realizadas"])
        c3.metric("🔥 Racha", f"{racha}d")

        # Badges
        st.markdown(f"**🎖️ Logros:** {desbloqueados}/{total_badges}")
        _render_badges_grid(stats)

        # Mini historial
        if stats["dias_uso"]:
            dias_recientes = sorted(stats["dias_uso"], reverse=True)[:7]
            dias_str = " · ".join(
                [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in dias_recientes]
            )
            st.caption(f"📅 Últimos días activos: {dias_str}")

        st.markdown("---")


def _render_badges_grid(stats: dict):
    """Renderiza la cuadrícula de badges."""
    cols_per_row = 4
    badge_list = BADGES
    for i in range(0, len(badge_list), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(badge_list):
                badge = badge_list[idx]
                desbloqueado = badge["id"] in stats["badges_desbloqueados"]
                with col:
                    if desbloqueado:
                        st.markdown(
                            f"<div title='{badge['nombre']}: {badge['descripcion']}' "
                            f"style='text-align:center;font-size:1.6rem;cursor:help;'>"
                            f"{badge['icono']}</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<div title='{badge['nombre']}: {badge['descripcion']}' "
                            f"style='text-align:center;font-size:1.6rem;opacity:0.25;filter:grayscale(100%);cursor:help;'>"
                            f"{badge['icono']}</div>",
                            unsafe_allow_html=True,
                        )


# ─────────────────────────────────────────────
# Onboarding
# ─────────────────────────────────────────────
def render_onboarding():
    """Muestra un tour de onboarding la primera vez."""
    _ensure_session_stats()
    stats = st.session_state["user_stats"]

    if not stats.get("primera_visita", False):
        return

    with st.container():
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                        padding: 28px; border-radius: 16px; margin-bottom: 24px;
                        border: 1px solid rgba(255,255,255,0.1);">
                <h2 style="color: #e94560; margin-top: 0;">🎉 ¡Bienvenido al Generador Educativo AI!</h2>
                <p style="color: #E0E0E0; font-size: 1.1rem;">
                    Esta herramienta te ayuda a crear <strong>Unidades Didácticas</strong> y
                    <strong>Sesiones de Aprendizaje</strong> alineadas al Currículo Nacional del Perú.
                </p>
                <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 16px;">
                    <div style="flex: 1; min-width: 200px; background: rgba(255,255,255,0.05);
                                padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                        <p style="color: #e94560; font-weight: bold; margin-bottom: 4px;">1️⃣ Selecciona</p>
                        <p style="color: #B0B0B0; font-size: 0.9rem; margin: 0;">
                            Elige área curricular, grado y competencias
                        </p>
                    </div>
                    <div style="flex: 1; min-width: 200px; background: rgba(255,255,255,0.05);
                                padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                        <p style="color: #e94560; font-weight: bold; margin-bottom: 4px;">2️⃣ Genera</p>
                        <p style="color: #B0B0B0; font-size: 0.9rem; margin: 0;">
                            Haz clic en Generar y la IA creará tu documento
                        </p>
                    </div>
                    <div style="flex: 1; min-width: 200px; background: rgba(255,255,255,0.05);
                                padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                        <p style="color: #e94560; font-weight: bold; margin-bottom: 4px;">3️⃣ Mejora y exporta</p>
                        <p style="color: #B0B0B0; font-size: 0.9rem; margin: 0;">
                            Usa el chat para refinar y descarga en TXT o DOCX
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("✅ ¡Entendido, empezar!", key="btn_onboarding_cerrar", use_container_width=True):
            stats["primera_visita"] = False
            save_stats(stats)
            st.rerun()
