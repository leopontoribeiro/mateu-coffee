# 🎨 MATEU BARISTA - DESIGN SYSTEM
# Sistema de Design Unificado para toda a aplicação

import streamlit as st
from dataclasses import dataclass
from typing import Optional, Callable
import json

# ═══════════════════════════════════════════════════════════════
# 1. PALETA DE CORES
# ═══════════════════════════════════════════════════════════════

@dataclass
class ColorPalette:
    """Paleta de cores oficial Mateu Barista"""

    # Primary - Laranja Quente (Principal)
    primary: str = "#FF8C42"
    primary_dark: str = "#FF7A28"
    primary_light: str = "#FFA866"
    primary_bg: str = "#FFF5E6"

    # Secondary - Cinza Sofisticado
    text_primary: str = "#2A2A2A"
    text_secondary: str = "#606060"
    text_tertiary: str = "#909090"
    border: str = "#E8E8E8"
    bg_light: str = "#F5F5F5"

    # Accent - Preto Elegante
    text_dark: str = "#1A1A1A"
    bg_dark: str = "#0D0D0D"

    # Functional
    success: str = "#4CAF50"
    warning: str = "#FF9800"
    error: str = "#FF6B6B"
    info: str = "#87CEEB"

    def to_dict(self) -> dict:
        return {
            'primary': self.primary,
            'primary_dark': self.primary_dark,
            'primary_light': self.primary_light,
            'primary_bg': self.primary_bg,
            'text_primary': self.text_primary,
            'text_secondary': self.text_secondary,
            'success': self.success,
            'error': self.error,
        }

COLORS = ColorPalette()

# ═══════════════════════════════════════════════════════════════
# 2. TIPOGRAFIA
# ═══════════════════════════════════════════════════════════════

@dataclass
class Typography:
    """Sistema tipográfico"""

    # Tamanhos
    h1: int = 32  # Títulos principais
    h2: int = 24  # Subtítulos
    h3: int = 20  # Seções
    body: int = 14  # Texto padrão
    caption: int = 12  # Metadados
    label: int = 12  # Labels de inputs

    # Pesos
    bold: str = "bold"
    semibold: str = "600"
    regular: str = "normal"
    light: str = "300"

    # Line Height
    tight: float = 1.2
    normal: float = 1.5
    loose: float = 1.8

TYPOGRAPHY = Typography()

# ═══════════════════════════════════════════════════════════════
# 3. ESPAÇAMENTO (8px Grid)
# ═══════════════════════════════════════════════════════════════

@dataclass
class Spacing:
    """Sistema de espaçamento com grid 8px"""

    xs: str = "4px"     # 0.5x
    sm: str = "8px"     # 1x
    md: str = "12px"    # 1.5x
    lg: str = "16px"    # 2x
    xl: str = "24px"    # 3x
    xxl: str = "32px"   # 4x
    xxxl: str = "48px"  # 6x

    # Padding/Margin padrão
    padding_card: str = "16px"
    padding_input: str = "12px"
    gap_element: str = "12px"

    # Border Radius
    radius_small: str = "8px"
    radius_default: str = "12px"
    radius_button: str = "24px"
    radius_full: str = "50%"

SPACING = Spacing()

# ═══════════════════════════════════════════════════════════════
# 4. SOMBRAS
# ═══════════════════════════════════════════════════════════════

class Shadows:
    """Sistema de sombras"""
    subtle: str = "0 2px 8px rgba(0, 0, 0, 0.08)"
    default: str = "0 4px 12px rgba(0, 0, 0, 0.12)"
    elevated: str = "0 8px 24px rgba(0, 0, 0, 0.15)"
    interactive: str = "0 4px 16px rgba(255, 140, 66, 0.2)"

SHADOWS = Shadows()

# ═══════════════════════════════════════════════════════════════
# 5. CONFIGURAÇÃO DO TEMA STREAMLIT
# ═══════════════════════════════════════════════════════════════

def apply_theme():
    """Aplica o tema global à aplicação"""
    st.set_page_config(
        page_title="Mateu Barista - Coffee Control",
        page_icon="☕",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": "Mateu Barista v1.1 - Sistema de Controle de Extrações"
        }
    )

    # CSS customizado
    css_content = f"""
    <style>
    /* VARIÁVEIS RAIZ */
    :root {{
        --primary: {COLORS.primary};
        --primary-dark: {COLORS.primary_dark};
        --primary-light: {COLORS.primary_light};
        --primary-bg: {COLORS.primary_bg};
        --text-primary: {COLORS.text_primary};
        --text-secondary: {COLORS.text_secondary};
        --text-dark: {COLORS.text_dark};
        --bg-light: {COLORS.bg_light};
        --bg-dark: {COLORS.bg_dark};
        --border: {COLORS.border};
        --success: {COLORS.success};
        --error: {COLORS.error};
        --warning: {COLORS.warning};
        --info: {COLORS.info};
        --radius: {SPACING.radius_default};
        --shadow: {SHADOWS.default};
    }}

    /* BODY E GLOBAL */
    html, body {{
        background-color: white;
        color: var(--text-primary);
        font-family: 'Inter', 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* HEADER DO APP */
    header {{
        background-color: var(--primary-bg) !important;
        border-bottom: 1px solid var(--border);
        padding: {SPACING.lg} {SPACING.xl};
    }}

    header h1 {{
        color: var(--primary) !important;
        font-size: {TYPOGRAPHY.h1}px;
        font-weight: bold;
        margin: 0;
    }}

    /* SIDEBAR */
    [data-testid="stSidebar"] {{
        background-color: var(--bg-light);
        border-right: 1px solid var(--border);
    }}

    [data-testid="stSidebar"] button {{
        background-color: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: {SPACING.radius_default} !important;
        transition: all 200ms ease-out;
        margin: {SPACING.sm} 0;
    }}

    [data-testid="stSidebar"] button:hover {{
        background-color: var(--primary-bg) !important;
        border-color: var(--primary) !important;
        color: var(--primary) !important;
    }}

    /* ABAS (TABS) */
    [data-baseweb="tab-list"] {{
        border-bottom: 2px solid var(--border);
        padding-bottom: {SPACING.sm};
    }}

    [data-baseweb="tab"] {{
        color: var(--text-secondary) !important;
        font-weight: 600;
        transition: all 200ms ease;
        border-radius: {SPACING.radius_small} {SPACING.radius_small} 0 0 !important;
    }}

    [data-baseweb="tab"][aria-selected="true"] {{
        color: var(--primary) !important;
        border-bottom: 3px solid var(--primary) !important;
        background-color: var(--primary-bg) !important;
    }}

    /* INPUTS */
    input[type="text"],
    input[type="number"],
    input[type="email"],
    input[type="password"],
    textarea,
    [data-baseweb="select"] {{
        background-color: var(--bg-light) !important;
        border: 1px solid var(--border) !important;
        border-radius: {SPACING.radius_default} !important;
        color: var(--text-primary) !important;
        padding: {SPACING.padding_input};
        font-size: {TYPOGRAPHY.body}px;
        transition: all 150ms ease;
    }}

    input[type="text"]:focus,
    input[type="number"]:focus,
    input[type="email"]:focus,
    input[type="password"]:focus,
    textarea:focus,
    [data-baseweb="select"]:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(255, 140, 66, 0.1) !important;
        outline: none !important;
    }}

    input[type="text"]::placeholder {{
        color: var(--text-secondary);
    }}

    /* LABELS */
    label {{
        color: var(--text-primary) !important;
        font-weight: 600;
        font-size: {TYPOGRAPHY.label}px;
        margin-bottom: {SPACING.sm};
    }}

    /* BOTÕES */
    button[kind="primary"] {{
        background-color: var(--primary) !important;
        color: white !important;
        border: none !important;
        border-radius: {SPACING.radius_button} !important;
        font-weight: bold;
        font-size: {TYPOGRAPHY.body}px;
        padding: {SPACING.lg} {SPACING.xl};
        transition: all 200ms ease-out;
        box-shadow: {SHADOWS.subtle};
    }}

    button[kind="primary"]:hover {{
        background-color: var(--primary-dark) !important;
        box-shadow: {SHADOWS.interactive};
        transform: translateY(-2px);
    }}

    button[kind="secondary"] {{
        background-color: var(--bg-light) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: {SPACING.radius_button} !important;
        font-weight: 600;
        transition: all 200ms ease;
    }}

    button[kind="secondary"]:hover {{
        background-color: var(--primary-bg) !important;
        border-color: var(--primary) !important;
        color: var(--primary) !important;
    }}

    /* CARDS */
    [data-testid="stMetricContainer"],
    .card-container {{
        background-color: var(--bg-light) !important;
        border: 1px solid var(--border);
        border-radius: {SPACING.radius_default};
        padding: {SPACING.padding_card};
        box-shadow: {SHADOWS.subtle};
        transition: all 300ms ease;
    }}

    [data-testid="stMetricContainer"]:hover,
    .card-container:hover {{
        box-shadow: {SHADOWS.default};
        border-color: var(--primary);
    }}

    /* MÉTRICA (STAT) */
    [data-testid="stMetricValue"] {{
        color: var(--primary) !important;
        font-size: 28px !important;
        font-weight: bold !important;
    }}

    [data-testid="stMetricLabel"] {{
        color: var(--text-secondary) !important;
        font-weight: 600;
    }}

    /* DIVIDER */
    hr {{
        border: none;
        height: 1px;
        background-color: var(--border);
        margin: {SPACING.lg} 0;
    }}

    /* SELECTBOX E MULTISELECT */
    [data-baseweb="select"],
    [data-baseweb="input"] {{
        border-radius: {SPACING.radius_default} !important;
    }}

    /* SLIDER */
    [data-baseweb="slider"] {{
        color: var(--primary) !important;
    }}

    /* ALERT/CALLOUT */
    [data-testid="stAlert"] {{
        border-radius: {SPACING.radius_default} !important;
        border-left: 4px solid var(--primary) !important;
    }}

    /* SUCCESS MESSAGE */
    .stSuccess {{
        background-color: rgba(76, 175, 80, 0.1) !important;
        border-left-color: var(--success) !important;
    }}

    /* ERROR MESSAGE */
    .stError {{
        background-color: rgba(255, 107, 107, 0.1) !important;
        border-left-color: var(--error) !important;
    }}

    /* INFO MESSAGE */
    .stInfo {{
        background-color: rgba(135, 206, 235, 0.1) !important;
        border-left-color: var(--info) !important;
    }}

    /* WARNING MESSAGE */
    .stWarning {{
        background-color: rgba(255, 152, 0, 0.1) !important;
        border-left-color: var(--warning) !important;
    }}

    /* PROGRESS BAR */
    [data-baseweb="progress-bar"] {{
        background-color: var(--primary) !important;
    }}

    /* MARKDOWN - TÍTULOS */
    h1, h2, h3, h4, h5, h6 {{
        color: var(--text-dark);
    }}

    h1 {{
        font-size: {TYPOGRAPHY.h1}px;
        font-weight: bold;
        margin-bottom: {SPACING.lg};
    }}

    h2 {{
        font-size: {TYPOGRAPHY.h2}px;
        font-weight: bold;
        margin-bottom: {SPACING.lg};
        color: var(--primary);
    }}

    h3 {{
        font-size: {TYPOGRAPHY.h3}px;
        font-weight: 600;
        margin-bottom: {SPACING.md};
    }}

    /* LINKS */
    a {{
        color: var(--primary) !important;
        text-decoration: none;
        font-weight: 600;
        transition: all 200ms ease;
    }}

    a:hover {{
        color: var(--primary-dark) !important;
        text-decoration: underline;
    }}

    /* CHECKBOX E RADIO */
    [data-baseweb="checkbox"],
    [data-baseweb="radio"] {{
        accent-color: var(--primary) !important;
    }}

    /* RESPONSIVE - MOBILE */
    @media (max-width: 640px) {{
        button {{
            width: 100% !important;
        }}

        [data-testid="stMetricContainer"] {{
            padding: {SPACING.md};
        }}

        h1 {{
            font-size: 24px;
        }}

        h2 {{
            font-size: 18px;
        }}
    }}
    </style>
    """

    st.markdown(css_content, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 6. COMPONENTES CUSTOMIZADOS
# ═══════════════════════════════════════════════════════════════

def header_component(title: str, subtitle: str = "", icon: str = "☕"):
    """Header padronizado para cada seção"""
    col1, col2 = st.columns([1, 10])
    with col1:
        st.markdown(f"<h2 style='margin: 0; font-size: 28px;'>{icon}</h2>",
                   unsafe_allow_html=True)
    with col2:
        st.markdown(f"<h2 style='margin: 0; color: {COLORS.primary};'>{title}</h2>",
                   unsafe_allow_html=True)
        if subtitle:
            st.markdown(f"<p style='margin: 0; color: {COLORS.text_secondary}; font-size: 14px;'>{subtitle}</p>",
                       unsafe_allow_html=True)
    st.divider()

def stat_card(label: str, value: str, change: Optional[str] = None,
              icon: str = "", color: str = None):
    """Card de estatística"""
    if color is None:
        color = COLORS.primary

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"<h3 style='margin: 0; font-size: 32px; color: {color};'>{icon}</h3>",
                   unsafe_allow_html=True)
    with col2:
        st.markdown(f"<p style='margin: 0; color: {COLORS.text_secondary}; font-size: 12px; font-weight: 600;'>{label}</p>",
                   unsafe_allow_html=True)
        st.markdown(f"<p style='margin: 4px 0 0 0; color: {color}; font-size: 24px; font-weight: bold;'>{value}</p>",
                   unsafe_allow_html=True)
        if change:
            st.markdown(f"<p style='margin: 4px 0 0 0; color: {COLORS.text_tertiary}; font-size: 12px;'>{change}</p>",
                       unsafe_allow_html=True)

def success_button(label: str, callback: Callable = None, key: str = None) -> bool:
    """Botão de sucesso (primário)"""
    clicked = st.button(label, key=key, use_container_width=True,
                       help=f"Clique para {label.lower()}")
    if clicked and callback:
        callback()
    return clicked

def secondary_button(label: str, callback: Callable = None, key: str = None) -> bool:
    """Botão secundário"""
    clicked = st.button(label, key=key, use_container_width=True)
    if clicked and callback:
        callback()
    return clicked

def info_box(title: str, content: str, icon: str = "ℹ️", box_type: str = "info"):
    """Caixa de informação padronizada"""
    colors_map = {
        "info": COLORS.info,
        "success": COLORS.success,
        "warning": COLORS.warning,
        "error": COLORS.error,
    }
    color = colors_map.get(box_type, COLORS.info)

    st.markdown(f"""
    <div style='
        background-color: rgba(135, 206, 235, 0.05);
        border-left: 4px solid {color};
        border-radius: {SPACING.radius_default};
        padding: {SPACING.lg};
        margin: {SPACING.lg} 0;
    '>
        <p style='margin: 0 0 {SPACING.sm} 0; font-weight: 600; color: {COLORS.text_primary};'>
            {icon} {title}
        </p>
        <p style='margin: 0; color: {COLORS.text_secondary}; font-size: 14px;'>
            {content}
        </p>
    </div>
    """, unsafe_allow_html=True)

def separator():
    """Divisor padronizado"""
    st.markdown(f"<hr style='margin: {SPACING.lg} 0; border: 1px solid {COLORS.border};'>",
               unsafe_allow_html=True)

def labeled_metric(label: str, value: str, unit: str = ""):
    """Métrica com label"""
    st.markdown(f"""
    <div style='text-align: center; padding: {SPACING.lg};'>
        <p style='margin: 0; color: {COLORS.text_secondary}; font-size: 12px; font-weight: 600;'>
            {label}
        </p>
        <p style='margin: {SPACING.sm} 0 0 0; color: {COLORS.primary}; font-size: 28px; font-weight: bold;'>
            {value}<span style='font-size: 16px;'> {unit}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 7. HELPERS
# ═══════════════════════════════════════════════════════════════

def format_number(num: float, decimals: int = 2) -> str:
    """Formata número com separador"""
    return f"{num:,.{decimals}f}".replace(",", ".")

def get_status_color(value: float, threshold: float = 50) -> str:
    """Retorna cor baseada no valor"""
    if value >= 80:
        return COLORS.success
    elif value >= threshold:
        return COLORS.warning
    return COLORS.error

def toast_message(message: str, msg_type: str = "info"):
    """Mensagem flutuante"""
    icon_map = {
        "success": "✓",
        "error": "✕",
        "warning": "⚠",
        "info": "ℹ"
    }
    color_map = {
        "success": COLORS.success,
        "error": COLORS.error,
        "warning": COLORS.warning,
        "info": COLORS.info,
    }

    st.toast(f"{icon_map.get(msg_type, 'ℹ')} {message}")
