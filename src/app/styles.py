"""
Estilos CSS personalizados para la interfaz gamificada del Generador Educativo AI.
Incluye temas, animaciones, y estilos para componentes de gamificación.
"""


def get_gamification_css() -> str:
    """Retorna el CSS completo de gamificación."""
    return """
    <style>
    /* ═══════════════════════════════════════════
       TEMA PRINCIPAL – MODO OSCURO PREMIUM
       ═══════════════════════════════════════════ */

    /* Sidebar – Panel de progreso */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a2e 100%);
    }

    [data-testid="stSidebar"] .stMetric {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 8px 12px;
    }

    [data-testid="stSidebar"] .stMetric label {
        color: #9ca3af !important;
        font-size: 0.75rem !important;
    }

    [data-testid="stSidebar"] .stMetric [data-testid="stMetricValue"] {
        color: #e94560 !important;
        font-weight: 700 !important;
    }

    /* ═══════════════════════════════════════════
       BARRA DE PROGRESO PERSONALIZADA
       ═══════════════════════════════════════════ */
    [data-testid="stSidebar"] .stProgress > div > div > div {
        background: linear-gradient(90deg, #e94560 0%, #ff6b6b 50%, #feca57 100%) !important;
        border-radius: 8px;
    }

    [data-testid="stSidebar"] .stProgress > div > div {
        background: rgba(255,255,255,0.08) !important;
        border-radius: 8px;
    }

    /* ═══════════════════════════════════════════
       BADGES GRID
       ═══════════════════════════════════════════ */
    .badge-desbloqueado {
        text-align: center;
        font-size: 1.6rem;
        cursor: help;
        transition: transform 0.2s ease;
    }
    .badge-desbloqueado:hover {
        transform: scale(1.3);
    }
    .badge-bloqueado {
        text-align: center;
        font-size: 1.6rem;
        opacity: 0.25;
        filter: grayscale(100%);
        cursor: help;
        transition: transform 0.2s ease, opacity 0.2s ease;
    }
    .badge-bloqueado:hover {
        opacity: 0.5;
        transform: scale(1.15);
    }

    /* ═══════════════════════════════════════════
       BOTÓN GENERAR – EFECTO PREMIUM
       ═══════════════════════════════════════════ */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #e94560 0%, #c23152 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(233, 69, 96, 0.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(233, 69, 96, 0.5) !important;
    }

    /* ═══════════════════════════════════════════
       TABS – ESTILO MEJORADO
       ═══════════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 24px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(233, 69, 96, 0.15) !important;
        border-bottom: 3px solid #e94560 !important;
    }

    /* ═══════════════════════════════════════════
       EXPANDER – CONTENIDO DEL DOCUMENTO
       ═══════════════════════════════════════════ */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 1rem;
    }

    /* ═══════════════════════════════════════════
       TOAST / SUCCESS / INFO – GAMIFICACIÓN
       ═══════════════════════════════════════════ */
    .stSuccess {
        border-left: 4px solid #2ecc71 !important;
    }
    .stInfo {
        border-left: 4px solid #3498db !important;
    }

    /* ═══════════════════════════════════════════
       FORMULARIOS Y SELECTORES
       ═══════════════════════════════════════════ */
    .stSelectbox label, .stMultiSelect label, .stTextArea label, .stTextInput label {
        font-weight: 500 !important;
    }

    /* ═══════════════════════════════════════════
       CHAT – MEJOR ESTILO
       ═══════════════════════════════════════════ */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        margin-bottom: 8px;
    }

    /* ═══════════════════════════════════════════
       DOWNLOAD BUTTONS 
       ═══════════════════════════════════════════ */
    .stDownloadButton > button {
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    }

    /* ═══════════════════════════════════════════
       ANIMACIÓN DE PULSO PARA LOGROS NUEVOS
       ═══════════════════════════════════════════ */
    @keyframes pulse-glow {
        0% { box-shadow: 0 0 5px rgba(233, 69, 96, 0.3); }
        50% { box-shadow: 0 0 20px rgba(233, 69, 96, 0.6); }
        100% { box-shadow: 0 0 5px rgba(233, 69, 96, 0.3); }
    }

    .logro-nuevo {
        animation: pulse-glow 2s ease-in-out 3;
        border-radius: 12px;
    }

    /* ═══════════════════════════════════════════
       FOOTER – ESTILO MEJORADO
       ═══════════════════════════════════════════ */
    footer {
        visibility: hidden;
    }
    </style>
    """
