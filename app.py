import streamlit as st
import os
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2.pool import ThreadedConnectionPool
import base64
import unicodedata
import json
from io import BytesIO
from html import escape as html_escape
from datetime import date, datetime, timedelta
from calendar import monthrange
from pathlib import Path
from psycopg2 import errors as pg_errors
import acceso
import activacion

# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="Arriendos",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# La base de datos principal está en Supabase/PostgreSQL.

# Paleta
FUCHSIA = "#D9468D"
FUCHSIA_DARK = "#B83272"
PINK_LIGHT = "#FCE7F3"
PINK_SOFT = "#FFF7FB"
PINK_BORDER = "#F5C2DD"
TEXT = "#2A2330"
MUTED = "#766C78"
WHITE = "#FFFFFF"
GREEN = "#16865B"
GREEN_BG = "#EAF8F1"
ORANGE = "#C77700"
ORANGE_BG = "#FFF4DD"
RED = "#C83D56"
RED_BG = "#FDECEF"

# =========================================================
# ESTILOS
# =========================================================

st.markdown(
    f"""
    <style>
    .stApp {{
        background: {PINK_SOFT};
        color: {TEXT};
    }}

    [data-testid="stSidebar"] {{
        background: {WHITE};
        border-right: 1px solid {PINK_BORDER};
    }}

    [data-testid="stSidebar"] * {{
        color: {TEXT};
    }}

    h1, h2, h3, h4, h5, h6 {{
        color: {TEXT} !important;
        font-weight: 700 !important;
    }}

    .main-title {{
        font-size: 2.25rem;
        font-weight: 800;
        color: {TEXT};
        margin-bottom: 0.1rem;
    }}

    .subtitle {{
        color: {MUTED};
        font-size: 1rem;
        margin-bottom: 1.4rem;
    }}

    .brand {{
        font-size: 1.55rem;
        font-weight: 800;
        color: {FUCHSIA} !important;
        margin-bottom: 0.15rem;
    }}

    .brand-small {{
        color: {MUTED} !important;
        font-size: 0.78rem;
        margin-bottom: 1rem;
    }}

    .metric-card {{
        background: {WHITE};
        border: 1px solid {PINK_BORDER};
        border-radius: 18px;
        padding: 18px 20px;
        min-height: 120px;
        box-shadow: 0 5px 18px rgba(217,70,141,0.06);
    }}

    .metric-label {{
        color: {MUTED};
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 7px;
    }}

    .metric-value {{
        color: {TEXT};
        font-size: 1.65rem;
        font-weight: 800;
    }}

    .metric-accent {{
        color: {FUCHSIA};
    }}

    .section-title {{
        color: {TEXT} !important;
        font-size: 1.25rem;
        font-weight: 800;
        margin-top: 1.4rem;
        margin-bottom: 0.8rem;
    }}

    .reservation-card {{
        background: {WHITE};
        border: 1px solid {PINK_BORDER};
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 10px;
        box-shadow: 0 5px 18px rgba(217,70,141,0.06);
    }}

    .reservation-tag {{
        color: {FUCHSIA_DARK};
        background: {PINK_LIGHT};
        border-radius: 999px;
        padding: 5px 10px;
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    .reservation-name {{
        color: {TEXT};
        font-size: 1.08rem;
        font-weight: 800;
        margin-top: 10px;
    }}

    .reservation-info {{
        color: {MUTED};
        font-size: 0.88rem;
        line-height: 1.55;
    }}

    /* Historial de liquidaciones: mismo lenguaje visual que Inicio. */
    .liq-card-inner {{
        padding: 1px 1px 3px;
        min-height: 166px;
    }}
    .liq-card-tag {{
        display: inline-block;
        color: {FUCHSIA_DARK};
        background: {PINK_LIGHT};
        border-radius: 999px;
        padding: 5px 10px;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .035em;
        text-transform: uppercase;
    }}
    .liq-card-guest {{
        color: {TEXT};
        font-size: 1.14rem;
        font-weight: 800;
        line-height: 1.35;
        margin: 12px 0 5px;
        overflow-wrap: anywhere;
    }}
    .liq-card-department {{
        color: {FUCHSIA_DARK};
        font-weight: 750;
        font-size: .86rem;
        margin-bottom: 8px;
        overflow-wrap: anywhere;
    }}
    .liq-card-meta {{
        color: {MUTED};
        font-size: .84rem;
        line-height: 1.75;
        overflow-wrap: anywhere;
    }}
    .liq-card-result {{
        margin: 13px 0 7px;
        padding-top: 12px;
        border-top: 1px solid {PINK_BORDER};
        display: flex;
        gap: 8px;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
    }}
    .liq-card-result-label {{
        color: {MUTED};
        font-size: .79rem;
        font-weight: 650;
    }}
    .liq-card-result-amount {{
        color: {FUCHSIA_DARK};
        font-size: 1.2rem;
        font-weight: 850;
    }}
    /* Los contenedores guardan los botones dentro de la tarjeta. */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.liq-card-inner) {{
        border-color: {PINK_BORDER} !important;
        background: {WHITE} !important;
        border-radius: 18px !important;
        box-shadow: 0 5px 18px rgba(217,70,141,.06);
    }}

    .reminder {{
        background: {WHITE};
        border-left: 5px solid {FUCHSIA};
        border-top: 1px solid {PINK_BORDER};
        border-right: 1px solid {PINK_BORDER};
        border-bottom: 1px solid {PINK_BORDER};
        border-radius: 14px;
        padding: 13px 15px;
        margin-bottom: 9px;
    }}

    .reminder-title {{
        color: {TEXT};
        font-weight: 750;
    }}

    .reminder-text {{
        color: {MUTED};
        font-size: 0.86rem;
        margin-top: 3px;
    }}

    .dept-card {{
        background: {WHITE};
        border: 1px solid {PINK_BORDER};
        border-radius: 18px;
        padding: 18px;
        min-height: 175px;
        box-shadow: 0 5px 18px rgba(217,70,141,0.06);
    }}

    .building-card {{
        position: relative;
        border-radius: 22px;
        overflow: hidden;
        min-height: 220px;
        margin: 8px 0 10px;
        background: linear-gradient(135deg, #d9468d 0%, #b83272 100%);
        box-shadow: 0 8px 24px rgba(217,70,141,0.10);
    }}

    .building-card img {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}

    .building-overlay {{
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, rgba(42,35,48,.78) 0%, rgba(42,35,48,.43) 56%, rgba(42,35,48,.12) 100%);
    }}

    .building-content {{
        position: relative;
        z-index: 2;
        min-height: 220px;
        padding: 28px;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
    }}

    .building-kicker {{
        color: #FFE7F3;
        font-size: .78rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .08em;
    }}

    .building-name {{
        color: white;
        font-size: 1.75rem;
        font-weight: 850;
        line-height: 1.05;
        margin-top: 6px;
    }}

    .building-count {{
        color: rgba(255,255,255,.92);
        font-size: .92rem;
        margin-top: 8px;
    }}

    .building-fallback {{
        background: linear-gradient(135deg, #d9468d 0%, #b83272 60%, #8f285d 100%);
    }}

    .departments-inside {{
        background: rgba(255,255,255,.60);
        border-radius: 18px;
        padding: 6px 0 2px;
        margin-bottom: 12px;
    }}

    .search-result-card {{
        background: {WHITE};
        border: 1px solid {PINK_BORDER};
        border-radius: 18px;
        padding: 17px;
        min-height: 150px;
        box-shadow: 0 5px 18px rgba(217,70,141,0.05);
        margin-bottom: 10px;
    }}

    .search-result-building {{
        color: {FUCHSIA_DARK};
        font-size: .78rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .04em;
    }}

    .search-result-name {{
        color: {TEXT};
        font-size: 1.08rem;
        font-weight: 850;
        margin: 4px 0 9px;
    }}

    .dept-name {{
        color: {TEXT};
        font-size: 1.08rem;
        font-weight: 800;
    }}

    .dept-condo {{
        color: {FUCHSIA_DARK};
        font-size: 0.82rem;
        font-weight: 700;
        margin: 4px 0 12px;
    }}

    .detail-box {{
        background: {WHITE};
        border: 1px solid {PINK_BORDER};
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 5px 18px rgba(217,70,141,0.05);
        margin-bottom: 14px;
    }}

    .detail-label {{
        color: {MUTED};
        font-size: 0.78rem;
        font-weight: 600;
    }}

    .detail-value {{
        color: {TEXT};
        font-size: 1rem;
        font-weight: 750;
    }}

    .reservation-heading {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        margin: 2px 0 18px;
    }}

    .reservation-heading-guest {{
        color: {TEXT};
        font-size: 1rem;
        font-weight: 700;
    }}

    .reservation-heading-place {{
        display: inline-flex;
        align-items: center;
        background: {PINK_LIGHT};
        color: {FUCHSIA_DARK};
        border: 1px solid {PINK_BORDER};
        border-radius: 999px;
        padding: 6px 11px;
        font-size: .82rem;
        font-weight: 750;
    }}

    .danger-zone {{
        margin-top: 18px;
        padding-top: 14px;
        border-top: 1px solid {PINK_BORDER};
    }}

    .availability-free {{
        color: {GREEN};
        background: {GREEN_BG};
        border-radius: 10px;
        padding: 8px 12px;
        font-weight: 750;
    }}

    .availability-busy {{
        color: {RED};
        background: {RED_BG};
        border-radius: 10px;
        padding: 8px 12px;
        font-weight: 750;
    }}

    .calendar-day {{
        background: {WHITE};
        border: 1px solid #EEE6EC;
        border-radius: 10px;
        min-height: 65px;
        padding: 8px;
        margin: 2px;
    }}

    .calendar-day.busy {{
        background: {PINK_LIGHT};
        border-color: {PINK_BORDER};
    }}

    .calendar-day-number {{
        font-weight: 800;
        color: {TEXT};
    }}

    .calendar-day-label {{
        color: {MUTED};
        font-size: 0.7rem;
        margin-top: 4px;
    }}

    div.stButton > button {{
        border-radius: 10px;
        border: 1px solid {PINK_BORDER};
        background: {WHITE};
        color: {FUCHSIA_DARK};
        font-weight: 700;
        min-height: 40px;
    }}

    div.stButton > button:hover {{
        border-color: {FUCHSIA};
        color: {FUCHSIA_DARK};
        background: {PINK_LIGHT};
    }}

    div.stButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"],
    [data-testid="stFormSubmitButton"] button[kind="primary"] {{
        background: {FUCHSIA_DARK} !important;
        border-color: {FUCHSIA_DARK} !important;
        color: #FFFFFF !important;
    }}

    div.stButton > button[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover,
    [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {{
        background: #9C255F !important;
        border-color: #9C255F !important;
        color: #FFFFFF !important;
    }}

    div.stButton > button[kind="primary"] *,
    [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] *,
    [data-testid="stFormSubmitButton"] button[kind="primary"] * {{
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }}

    /* =========================
       CONTROLES DE FORMULARIO
       ========================= */

    /* Las etiquetas no deben desaparecer con el tema oscuro del navegador/Streamlit. */
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] *,
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label {{
        color: {TEXT} !important;
        opacity: 1 !important;
        visibility: visible !important;
    }}

    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input {{
        background: {WHITE} !important;
        background-color: {WHITE} !important;
        color: {TEXT} !important;
        -webkit-text-fill-color: {TEXT} !important;
        border: 1px solid {PINK_BORDER} !important;
        border-radius: 10px !important;
        color-scheme: light !important;
    }}

    [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
        background: {WHITE} !important;
        background-color: {WHITE} !important;
        color: {TEXT} !important;
        border: 1px solid {PINK_BORDER} !important;
        border-radius: 10px !important;
        box-shadow: none !important;
        color-scheme: light !important;
    }}

    [data-testid="stSelectbox"] div[data-baseweb="select"] *,
    [data-testid="stMultiSelect"] [data-baseweb="select"] * {{
        color: {TEXT} !important;
        -webkit-text-fill-color: {TEXT} !important;
    }}

    /* El menú desplegable también queda claro y legible. */
    [role="listbox"],
    [role="option"] {{
        background: {WHITE} !important;
        color: {TEXT} !important;
    }}

    [role="option"] * {{
        color: {TEXT} !important;
    }}

    /* Radio / Vista del calendario */
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] label *,
    [data-testid="stRadio"] p {{
        color: {TEXT} !important;
        opacity: 1 !important;
    }}

    /* Slider */
    [data-testid="stSlider"] [data-testid="stWidgetLabel"] *,
    [data-testid="stSlider"] p {{
        color: {TEXT} !important;
    }}

    /* Evita que el tema del sistema convierta los controles en negros. */
    [data-testid="stTextInput"],
    [data-testid="stNumberInput"],
    [data-testid="stDateInput"],
    [data-testid="stTimeInput"],
    [data-testid="stSelectbox"] {{
        color-scheme: light !important;
    }}

    /* Calendario: evita que los textos se corten en pantallas angostas. */
    .calendar-day {{
        background: {WHITE};
        border: 1px solid #EEE6EC;
        border-radius: 10px;
        min-height: 62px;
        padding: 7px 5px;
        margin: 1px;
        overflow: hidden;
    }}

    .calendar-day.busy {{
        background: {PINK_LIGHT};
        border-color: {PINK_BORDER};
    }}

    .calendar-day-number {{
        font-weight: 800;
        color: {TEXT};
        font-size: .9rem;
    }}

    .calendar-status {{
        font-size: .68rem;
        font-weight: 700;
        margin-top: 5px;
        white-space: nowrap;
    }}

    .calendar-status.free {{ color: {GREEN}; }}
    .calendar-status.busy {{ color: {RED}; }}

    @media (max-width: 768px) {{
        .main-title {{ font-size: 1.8rem; }}
        .subtitle {{ font-size: .9rem; }}
        .calendar-day {{ min-height: 54px; padding: 6px 3px; }}
        .calendar-status {{ font-size: .6rem; }}
        .calendar-day-number {{ font-size: .8rem; }}
    }}

    .payment-status {{
        background: {PINK_LIGHT};
        color: {FUCHSIA_DARK};
        border: 1px solid {PINK_BORDER};
        border-radius: 10px;
        padding: 9px 12px;
        font-size: .82rem;
        margin: 4px 0 10px;
    }}

    .payment-history-title {{
        color: {TEXT};
        font-weight: 800;
        margin: 12px 0 7px;
    }}

    .payment-row {{
        display: flex;
        align-items: center;
        gap: 10px;
        background: {WHITE};
        border: 1px solid #EEE6EC;
        border-radius: 10px;
        padding: 8px 11px;
        margin-bottom: 6px;
        color: {MUTED};
        font-size: .82rem;
    }}

    .payment-row strong {{
        color: {TEXT};
        margin-left: auto;
    }}

    @media (max-width: 768px) {{
        .payment-row {{
            flex-wrap: wrap;
        }}
    }}

    .payment-summary {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 0 0 10px 0;
    }}

    .payment-card {{
        background: {WHITE};
        border: 1px solid {PINK_BORDER};
        border-radius: 14px;
        padding: 12px 14px;
        min-height: 76px;
    }}

    .payment-card-label {{
        color: {FUCHSIA_DARK};
        font-size: .76rem;
        font-weight: 800;
        margin-bottom: 4px;
    }}

    .payment-card-value {{
        color: {TEXT};
        font-size: 1.25rem;
        line-height: 1.15;
        font-weight: 800;
    }}

    .detail-box.compact {{
        margin-bottom: 0;
    }}

    .payment-section {{
        margin-top: .8rem;
    }}

    @media (max-width: 768px) {{
        .payment-summary {{
            grid-template-columns: 1fr;
            gap: 8px;
        }}
        .payment-card {{
            min-height: 64px;
        }}
        .payment-card-value {{
            font-size: 1.15rem;
        }}
    }}

    .hero {{
        position: relative;
        min-height: 390px;
        border-radius: 28px;
        overflow: hidden;
        margin: 0 0 2rem 0;
        background: linear-gradient(135deg, #d9468d, #b83272);
        box-shadow: 0 12px 35px rgba(184,50,114,0.14);
    }}

    .hero-image {{
        position: absolute !important;
        top: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        left: 0 !important;
        width: 100% !important;
        max-width: none !important;
        min-width: 100% !important;
        height: 100% !important;
        min-height: 100% !important;
        object-fit: cover !important;
        object-position: center center !important;
        display: block !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    .hero-overlay {{
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, rgba(36,18,31,.76) 0%, rgba(36,18,31,.48) 48%, rgba(36,18,31,.18) 100%);
        z-index: 1;
    }}

    /* Encabezado visual para cada sección principal */
    .page-hero {{
        min-height: 245px;
        margin-bottom: 1.5rem;
    }}

    .page-hero .hero-content {{
        min-height: 245px;
        padding: 32px 38px;
    }}

    .page-hero .hero-title {{
        font-size: clamp(2rem, 4vw, 3.35rem);
    }}

    .page-hero .hero-text {{
        max-width: 760px;
        margin-top: 9px;
    }}

    @media (max-width: 768px) {{
        .page-hero {{
            min-height: 220px;
            border-radius: 22px;
        }}
        .page-hero .hero-content {{
            min-height: 220px;
            padding: 24px 22px;
        }}
    }}

    .hero-no-image {{
        background: linear-gradient(135deg, #d9468d 0%, #b83272 55%, #8f285d 100%);
    }}

    .hero-content {{
        position: relative;
        z-index: 2;
        min-height: 390px;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        padding: 42px;
    }}

    .hero-kicker {{
        color: #ffd9eb;
        font-size: .82rem;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }}

    .hero-title {{
        color: #ffffff !important;
        font-size: clamp(2.2rem, 5vw, 4.4rem);
        line-height: 1.02;
        font-weight: 850;
        margin: 0;
        letter-spacing: -.04em;
    }}

    .hero-text {{
        color: #fff7fb;
        font-size: 1.05rem;
        max-width: 650px;
        margin-top: 14px;
        line-height: 1.6;
    }}

    .hero-date {{
        display: inline-block;
        width: fit-content;
        margin-top: 18px;
        color: #ffffff;
        background: rgba(255,255,255,.16);
        border: 1px solid rgba(255,255,255,.28);
        border-radius: 999px;
        padding: 8px 13px;
        font-size: .85rem;
        font-weight: 700;
        backdrop-filter: blur(5px);
    }}

    .home-intro {{
        color: #766C78;
        font-size: .95rem;
        margin: 0 0 1.2rem 0;
    }}

    @media (max-width: 768px) {{
        .hero {{
            min-height: 330px;
            border-radius: 22px;
            margin-top: .3rem;
        }}
        .hero-content {{
            min-height: 330px;
            padding: 26px 22px;
        }}
        .hero-title {{
            font-size: 2.35rem;
        }}
        .hero-text {{
            font-size: .94rem;
        }}
    }}

    .footer-note {{
        color: {MUTED};
        font-size: 0.78rem;
        text-align: center;
        margin-top: 2rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# DISEÑO DEL LOGIN (pantalla dividida, foto personalizable)
# =========================================================

LOGIN_CSS = """
<style>
/* Pantallas públicas: colores suaves, texto legible y botones rosados. */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stDecoration"] { display: none !important; }
.stApp {
    background:
      radial-gradient(ellipse at 7% 10%, rgba(250, 196, 224, .33), transparent 37%),
      radial-gradient(ellipse at 94% 90%, rgba(213, 204, 245, .30), transparent 40%),
      linear-gradient(135deg, #fffafd 0%, #fbedf5 52%, #f3edf9 100%) !important;
    color: #3c2d3d !important;
    min-height: 100vh;
}
[data-testid="stMainBlockContainer"] {
    max-width: 1120px !important;
    padding-top: clamp(1.4rem, 4vh, 3.4rem) !important;
    padding-bottom: 3.5rem !important;
}
.auth-overline {
    text-align: center;
    font-size: .77rem;
    font-weight: 800;
    letter-spacing: .21em;
    color: #85516f !important;
    text-transform: uppercase;
    margin: 0 0 1.5rem;
}
/* Las dos tarjetas forman una sola experiencia en cada etapa. */
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-visual-anchor),
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor),
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-welcome-anchor) {
    border: 1px solid #f1dbe8 !important;
    border-radius: 28px !important;
    background: #fff !important;
    box-shadow: 0 15px 46px rgba(96, 43, 86, .08), 0 2px 9px rgba(96, 43, 86, .04);
    overflow: hidden;
    min-height: 575px;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-visual-anchor) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-welcome-anchor) > div {
    padding: .85rem 1.15rem 1.35rem;
}
.auth-visual-anchor, .auth-form-anchor, .auth-welcome-anchor { height: 0; font-size: 0; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-visual-anchor) [data-testid="stImage"] img {
    width: 100%;
    height: clamp(255px, 37vh, 340px);
    object-fit: cover;
    object-position: center;
    border-radius: 18px;
}
.auth-visual-fallback {
    height: clamp(255px, 37vh, 340px);
    border-radius: 18px;
    background: linear-gradient(160deg, #ffe3ee 0%, #f6c2db 55%, #fbe6f1 100%);
    overflow: hidden;
}
.auth-visual-fallback svg { display: block; width: 100%; height: 100%; }
.auth-welcome {
    color: #b83272 !important;
    text-align: center;
    font-weight: 850;
    font-size: clamp(1.85rem, 3.3vw, 2.5rem);
    letter-spacing: -.04em;
    margin: .55rem 0 .2rem;
}
.auth-welcome-text {
    color: #665263 !important;
    font-size: .95rem;
    text-align: center;
    line-height: 1.6;
    max-width: 350px;
    margin: .2rem auto 1.2rem;
}
.auth-mini-divider {
    height: 3px;
    width: 52px;
    background: #edc0d7;
    border-radius: 999px;
    margin: 0 auto;
}
/* Bienvenida: no se muestran campos de acceso. */
.auth-welcome-kicker {
    color: #9c2d6a !important;
    font-size: .75rem;
    letter-spacing: .13em;
    font-weight: 850;
    margin: 2.45rem 0 1.2rem;
    text-transform: uppercase;
}
.auth-welcome-headline {
    font-size: clamp(2rem, 3.4vw, 3rem);
    font-weight: 850;
    line-height: 1.15;
    letter-spacing: -.045em;
    color: #482b44 !important;
    margin: 0 0 1.15rem;
}
.auth-welcome-description {
    font-size: 1.02rem;
    line-height: 1.7;
    color: #624e60 !important;
    margin: 0 0 1.55rem;
}
.auth-welcome-features {
    color: #624e60 !important;
    font-size: .94rem;
    line-height: 1.8;
    background: #fff7fb;
    border: 1px solid #f7dce9;
    border-radius: 16px;
    padding: 15px 18px;
    margin: 0 0 1.45rem;
}
.auth-welcome-features strong { color: #5a3551 !important; }
.auth-access-note {
    text-align: center;
    color: #715b6d !important;
    font-size: .82rem;
    margin-top: .85rem;
}
/* Encabezado con globos, solo en el formulario. */
.auth-header-art {
    height: 155px;
    margin: -.85rem -1.15rem .9rem;
    overflow: hidden;
    border-radius: 18px 18px 26% 26% / 18px 18px 11% 11%;
    background: #f8dce9;
}
.auth-header-art svg { width: 100%; height: 100%; display: block; }
.auth-form-kicker {
    font-size: .74rem;
    font-weight: 850;
    letter-spacing: .15em;
    color: #984067 !important;
    text-align: center;
    margin-top: .15rem;
}
.auth-form-heading {
    font-size: clamp(1.8rem, 3vw, 2.3rem);
    font-weight: 850;
    letter-spacing: -.04em;
    line-height: 1.2;
    color: #482b44 !important;
    text-align: center;
    margin: .35rem 0 .4rem;
}
.auth-form-subtitle {
    color: #665263 !important;
    font-size: .92rem;
    line-height: 1.5;
    text-align: center;
    margin-bottom: .85rem;
}
/* Inputs y etiquetas: forzamos contraste independientemente del tema de Streamlit. */
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stForm"] {
    border: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stWidgetLabel"] *,
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) label,
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stExpander"] summary {
    color: #482b44 !important;
    opacity: 1 !important;
    font-weight: 700;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stTextInput"] input {
    background: #fffafe !important;
    color: #36283a !important;
    -webkit-text-fill-color: #36283a !important;
    border: 1px solid #e9bfd5 !important;
    border-radius: 12px !important;
    min-height: 44px;
    padding-left: .85rem !important;
    color-scheme: light !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stTextInput"] input::placeholder {
    color: #786574 !important;
    -webkit-text-fill-color: #786574 !important;
    opacity: 1 !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stTextInput"] input:focus {
    border-color: #b83272 !important;
    box-shadow: 0 0 0 3px rgba(184,50,114,.13) !important;
}
/* Empezar, iniciar sesión, recuperar contraseña: todos rosados, nunca naranja. */
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-welcome-anchor) [data-testid="stButton"] button[kind="primary"],
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stFormSubmitButton"] button,
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) button[kind="primaryFormSubmit"] {
    background: #b83272 !important;
    border: 1px solid #b83272 !important;
    border-radius: 999px !important;
    min-height: 3rem !important;
    box-shadow: 0 7px 18px rgba(184,50,114,.12);
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-welcome-anchor) [data-testid="stButton"] button[kind="primary"]:hover,
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stFormSubmitButton"] button:hover,
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) button[kind="primaryFormSubmit"]:hover {
    background: #99275c !important;
    border-color: #99275c !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-welcome-anchor) [data-testid="stButton"] button[kind="primary"] *,
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stFormSubmitButton"] button *,
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) button[kind="primaryFormSubmit"] * {
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    font-weight: 800 !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stButton"] button[kind="secondary"] {
    background: #fff3fa !important;
    border-color: #f0d4e1 !important;
    color: #8b2456 !important;
    border-radius: 999px !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stButton"] button[kind="secondary"] * {
    color: #8b2456 !important;
    -webkit-text-fill-color: #8b2456 !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor) [data-testid="stExpander"] {
    background: #fffafd;
    border: 1px solid #f0d4e1;
    border-radius: 13px;
}
.auth-authorized {
    text-align: center;
    color: #715b6d !important;
    font-size: .8rem;
    margin-top: .65rem;
}
@media (max-width: 780px) {
    [data-testid="stMainBlockContainer"] {
        padding-top: 1.15rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.auth-visual-anchor),
    [data-testid="stVerticalBlockBorderWrapper"]:has(.auth-form-anchor),
    [data-testid="stVerticalBlockBorderWrapper"]:has(.auth-welcome-anchor) {
        min-height: auto;
        border-radius: 22px !important;
    }
    .auth-header-art { height: 115px; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.auth-visual-anchor) [data-testid="stImage"] img,
    .auth-visual-fallback { height: 205px; }
    .auth-welcome-headline { font-size: 2.05rem; }
    .auth-welcome-kicker { margin-top: .25rem; }
    .auth-welcome { font-size: 1.85rem; }
}
</style>
"""

# =========================================================
# BASE DE DATOS · SUPABASE / POSTGRESQL
# =========================================================

def _database_url():
    """Obtiene la conexión guardada en Streamlit Secrets."""
    try:
        url = st.secrets["DATABASE_URL"]
    except Exception:
        url = os.getenv("DATABASE_URL")

    if not url:
        st.error(
            "No se encontró DATABASE_URL. En Streamlit ve a Settings → Secrets "
            "y guarda la conexión de Supabase."
        )
        st.stop()

    return str(url)


def _convert_placeholders(sql):
    """Permite conservar las consultas antiguas que usan ? como marcador."""
    return sql.replace("?", "%s")


class PgCursor:
    """Adaptador pequeño para mantener la sintaxis que ya usa la app."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=None):
        self._cursor.execute(_convert_placeholders(sql), params or ())
        return self

    def executemany(self, sql, seq_of_params):
        self._cursor.executemany(_convert_placeholders(sql), seq_of_params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


@st.cache_resource
def _connection_pool():
    """Reutiliza conexiones a Supabase para evitar reconectar en cada rerun."""
    return ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=_database_url(),
        sslmode="require",
        connect_timeout=10,
    )


class PgConnection:
    def __init__(self, admin=False):
        self._pool = _connection_pool()
        self._conn = self._pool.getconn()
        self._released = False

        # Si Supabase cerró una conexión inactiva, la reemplazamos.
        if self._conn.closed:
            try:
                self._pool.putconn(self._conn, close=True)
            except Exception:
                pass
            self._conn = self._pool.getconn()

        # TODAS las consultas de pantallas usan el rol PostgreSQL authenticated.
        # El rol postgres de DATABASE_URL se reserva para esquema/gestión Auth.
        # SET LOCAL se revierte con commit/rollback: seguro con Transaction pooler.
        if not admin:
            profile = st.session_state.get("auth_profile")
            uid = st.session_state.get("auth_uid")
            if not profile or not uid or str(profile["user_id"]) != str(uid):
                self._pool.putconn(self._conn)
                self._released = True
                raise PermissionError("Inicia sesión para consultar la base de datos.")
            try:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (str(uid),))
                    cur.execute("SELECT set_config('request.jwt.claims', %s, true)",
                                (json.dumps({"sub": str(uid), "role": "authenticated"}),))
                    cur.execute("SELECT set_config('request.jwt.claim.role', 'authenticated', true)")
                    cur.execute("SET LOCAL ROLE authenticated")
            except Exception:
                self._conn.rollback()
                self._pool.putconn(self._conn)
                self._released = True
                raise

    def cursor(self):
        return PgCursor(self._conn.cursor(cursor_factory=DictCursor))

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()
        # Evita pantallas desactualizadas después de guardar una reserva,
        # departamento, pago o una asignación de propietario.
        for name in ("_departments_for_user", "_reservations_for_user"):
            cached_fn = globals().get(name)
            if cached_fn is not None:
                cached_fn.clear()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._released:
            return
        try:
            # Las consultas SELECT también abren una transacción en psycopg2.
            # La dejamos limpia antes de devolverla al pool.
            self._conn.rollback()
        except Exception:
            pass
        try:
            self._pool.putconn(self._conn)
        finally:
            self._released = True


def db(admin=False):
    # admin=True solo está permitido para creación de esquema, alta de cuentas
    # y lectura del índice RUT -> Auth, nunca para consultas de páginas.
    try:
        return PgConnection(admin=admin)
    except PermissionError:
        st.error("No tienes una sesión autorizada.")
        st.stop()
    except Exception:
        st.error(
            "No fue posible conectar con Supabase. Revisa DATABASE_URL y "
            "que el SQL de migración se haya aplicado correctamente."
        )
        st.stop()


def _existing_columns(cur, table):
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=?
    """, (table,))
    return {row["column_name"] for row in cur.fetchall()}


def table_columns(table):
    allowed = {"departments", "reservations", "payments", "checklist"}
    if table not in allowed:
        raise ValueError("Tabla no permitida")

    conn = db()
    cur = conn.cursor()
    columns = _existing_columns(cur, table)
    conn.close()
    return columns


@st.cache_resource
def init_db():
    """Compatibilidad con tablas existentes; operaciones DDL exclusivamente backend."""
    conn = db(admin=True)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id BIGSERIAL PRIMARY KEY,
            condo TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            capacity INTEGER NOT NULL DEFAULT 2,
            winter_price BIGINT NOT NULL DEFAULT 0,
            summer_price BIGINT NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id BIGSERIAL PRIMARY KEY,
            department_id BIGINT NOT NULL REFERENCES departments(id),
            guest TEXT NOT NULL DEFAULT '',
            guest_name TEXT NOT NULL DEFAULT '',
            phone TEXT DEFAULT '',
            check_in TEXT NOT NULL,
            check_in_time TEXT DEFAULT '15:00',
            check_out TEXT NOT NULL,
            check_out_time TEXT DEFAULT '11:00',
            guests INTEGER NOT NULL DEFAULT 1,
            price_night BIGINT NOT NULL DEFAULT 0,
            nights INTEGER NOT NULL DEFAULT 1,
            total BIGINT NOT NULL DEFAULT 0,
            deposit_percent DOUBLE PRECISION NOT NULL DEFAULT 0,
            deposited BIGINT NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Sin abono'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id BIGSERIAL PRIMARY KEY,
            reservation_id BIGINT NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
            amount BIGINT NOT NULL DEFAULT 0,
            payment_date TEXT NOT NULL DEFAULT '',
            note TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS checklist (
            id BIGSERIAL PRIMARY KEY,
            reservation_id BIGINT NOT NULL UNIQUE REFERENCES reservations(id) ON DELETE CASCADE,
            cleaning INTEGER NOT NULL DEFAULT 0,
            internet INTEGER NOT NULL DEFAULT 0,
            inspected INTEGER NOT NULL DEFAULT 0,
            keys INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Una sola fotografía por edificio/condominio. Se guarda en Supabase
    # para que no se pierda cuando Streamlit se reinicie.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS condo_images (
            condo_key TEXT PRIMARY KEY,
            condo_name TEXT NOT NULL DEFAULT '',
            image_data BYTEA NOT NULL,
            image_mime TEXT NOT NULL DEFAULT 'image/jpeg',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    # Supabase puede exponer las tablas nuevas mediante Data API.
    # Activamos RLS para que la foto no quede accesible públicamente por la API.
    cur.execute("ALTER TABLE condo_images ENABLE ROW LEVEL SECURITY")

    def add_column_if_missing(table, column, definition):
        columns = _existing_columns(cur, table)
        if column not in columns:
            cur.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')

    add_column_if_missing("departments", "condo", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing("departments", "name", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing("departments", "capacity", "INTEGER NOT NULL DEFAULT 2")
    add_column_if_missing("departments", "winter_price", "BIGINT NOT NULL DEFAULT 0")
    add_column_if_missing("departments", "summer_price", "BIGINT NOT NULL DEFAULT 0")
    add_column_if_missing("departments", "active", "INTEGER NOT NULL DEFAULT 1")

    dept_cols = _existing_columns(cur, "departments")
    if "condominium" in dept_cols:
        cur.execute("""
            UPDATE departments
            SET condo = condominium
            WHERE (condo IS NULL OR TRIM(condo) = '')
              AND condominium IS NOT NULL
        """)

    add_column_if_missing("reservations", "department_id", "BIGINT")
    add_column_if_missing("reservations", "guest", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing("reservations", "guest_name", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing("reservations", "phone", "TEXT DEFAULT ''")
    add_column_if_missing("reservations", "check_in", "TEXT NOT NULL DEFAULT '2000-01-01'")
    add_column_if_missing("reservations", "check_in_time", "TEXT DEFAULT '15:00'")
    add_column_if_missing("reservations", "check_out", "TEXT NOT NULL DEFAULT '2000-01-02'")
    add_column_if_missing("reservations", "check_out_time", "TEXT DEFAULT '11:00'")
    add_column_if_missing("reservations", "guests", "INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing("reservations", "price_night", "BIGINT NOT NULL DEFAULT 0")
    add_column_if_missing("reservations", "nights", "INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing("reservations", "total", "BIGINT NOT NULL DEFAULT 0")
    add_column_if_missing("reservations", "deposit_percent", "DOUBLE PRECISION NOT NULL DEFAULT 0")
    add_column_if_missing("reservations", "deposited", "BIGINT NOT NULL DEFAULT 0")
    add_column_if_missing("reservations", "status", "TEXT NOT NULL DEFAULT 'Sin abono'")

    res_cols = _existing_columns(cur, "reservations")
    if "nightly_price" in res_cols:
        cur.execute("""
            UPDATE reservations
            SET price_night = nightly_price
            WHERE COALESCE(price_night, 0) = 0
              AND nightly_price IS NOT NULL
        """)

    cur.execute("""
        UPDATE reservations
        SET guest_name = guest
        WHERE (guest_name IS NULL OR TRIM(guest_name) = '')
          AND guest IS NOT NULL
    """)

    add_column_if_missing("payments", "payment_date", "TEXT NOT NULL DEFAULT ''")
    payment_cols = _existing_columns(cur, "payments")
    if "date" in payment_cols:
        cur.execute("""
            UPDATE payments
            SET payment_date = "date"
            WHERE (payment_date IS NULL OR TRIM(payment_date) = '')
              AND "date" IS NOT NULL
        """)

    add_column_if_missing("checklist", "cleaning", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("checklist", "internet", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("checklist", "inspected", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("checklist", "keys", "INTEGER NOT NULL DEFAULT 0")


    # Liquidaciones para propietarios: una por reserva y preferencias por departamento.
    # Los importes de cada liquidación se guardan como fotografía histórica.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS owner_liquidation_settings (
            department_id BIGINT PRIMARY KEY REFERENCES departments(id) ON DELETE CASCADE,
            owner_name TEXT NOT NULL DEFAULT '',
            commission_percent SMALLINT NOT NULL DEFAULT 10
                CHECK (commission_percent IN (10, 12)),
            usual_costs JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS owner_liquidations (
            id BIGSERIAL PRIMARY KEY,
            reservation_id BIGINT NOT NULL UNIQUE
                REFERENCES reservations(id) ON DELETE CASCADE,
            owner_name TEXT NOT NULL DEFAULT '',
            condo_name TEXT NOT NULL DEFAULT '',
            department_name TEXT NOT NULL DEFAULT '',
            guest_name TEXT NOT NULL DEFAULT '',
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            nights INTEGER NOT NULL DEFAULT 0,
            price_night BIGINT NOT NULL DEFAULT 0,
            gross_total BIGINT NOT NULL DEFAULT 0,
            commission_percent SMALLINT NOT NULL CHECK (commission_percent IN (10, 12)),
            commission_amount BIGINT NOT NULL DEFAULT 0,
            expenses JSONB NOT NULL DEFAULT '[]'::jsonb,
            expenses_total BIGINT NOT NULL DEFAULT 0,
            owner_net BIGINT NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    # El acceso desde la aplicación es mediante la conexión privada a PostgreSQL;
    # se impide que la Data API pública exponga estas tablas sin políticas.
    cur.execute("ALTER TABLE owner_liquidation_settings ENABLE ROW LEVEL SECURITY")
    cur.execute("ALTER TABLE owner_liquidations ENABLE ROW LEVEL SECURITY")

    count = cur.execute("SELECT COUNT(*) AS total FROM departments").fetchone()["total"]
    if count == 0:
        departments = [
            ("Serena Pacífico", "Depto 101", 4, 60000, 90000),
            ("Serena Pacífico", "Depto 202", 5, 65000, 95000),
            ("Serena Pacífico", "Depto 305", 4, 70000, 100000),
            ("Serena Pacífico", "Depto 406", 6, 75000, 110000),
            ("Las Gredas", "Depto 1", 4, 60000, 90000),
            ("Las Gredas", "Depto 2", 5, 65000, 95000),
            ("Las Gredas", "Depto 3", 6, 70000, 105000),
            ("Oceanic", "Depto 101", 4, 65000, 95000),
            ("Oceanic", "Depto 202", 5, 70000, 105000),
        ]
        cur.executemany("""
            INSERT INTO departments
            (condo, name, capacity, winter_price, summer_price)
            VALUES (?, ?, ?, ?, ?)
        """, departments)

    conn.commit()
    conn.close()


init_db()

# =========================================================
# CONTROL DE ACCESO · RUT + CONTRASEÑA
# =========================================================

def _profile_by_rut(rut):
    conn = db(admin=True)
    try:
        row = conn.execute("""
            SELECT user_id, rut, full_name, login_email, role, owner_id,
                   is_active, must_change_password
            FROM public.user_profiles WHERE rut=?
        """, (rut,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _profile_by_uid(uid):
    conn = db(admin=True)
    try:
        row = conn.execute("""
            SELECT user_id, rut, full_name, login_email, role, owner_id,
                   is_active, must_change_password
            FROM public.user_profiles WHERE user_id=?::uuid
        """, (uid,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def current_role():
    profile = st.session_state.get("auth_profile") or {}
    return profile.get("role")


def is_admin():
    return current_role() == "admin"


def _finish_first_access(uid):
    """Marca la invitación completada tras autenticar con una contraseña personal."""
    conn = db(admin=True)
    try:
        cur = conn.execute("""
            UPDATE public.user_profiles
            SET must_change_password = FALSE
            WHERE user_id = ?::uuid AND is_active = TRUE
        """, (uid,))
        if cur.rowcount != 1:
            raise ValueError("No se pudo completar la activación.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _render_login_illustration():
    """Ilustración elegida por la usuaria o globos suaves de respaldo."""
    with st.container(border=True):
        st.markdown('<div class="auth-visual-anchor"></div>', unsafe_allow_html=True)
        foto = Path(__file__).resolve().parent / "login.png"
        if foto.is_file():
            st.image(str(foto), use_container_width=True)
        else:
            st.markdown('''<div class="auth-visual-fallback" aria-label="Ilustración decorativa de globos aerostáticos">
                <svg viewBox="0 0 440 340" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <defs>
                        <linearGradient id="balloonA" x1="0" y1="0" x2="1" y2="1">
                            <stop stop-color="#ff2b8b"/><stop offset="1" stop-color="#ba2675"/>
                        </linearGradient>
                        <linearGradient id="balloonB" x1="0" y1="0" x2="0" y2="1">
                            <stop stop-color="#f998bc"/><stop offset="1" stop-color="#e94b8b"/>
                        </linearGradient>
                    </defs>
                    <circle cx="218" cy="185" r="115" fill="#ffe7f1"/>
                    <path d="M0 258 Q60 214 121 258 T244 250 T440 250 V340 H0Z" fill="#fff3f8"/>
                    <path d="M0 291 Q87 241 159 298 T338 286 T440 292 V340 H0Z" fill="#fff"/>
                    <g transform="translate(154 38)">
                        <path d="M0 74 C-36 25 -27 -12 0 -12 C27 -12 36 25 0 74Z" fill="url(#balloonA)"/>
                        <path d="M0 -12 C-12 -8 -16 45 0 74 C16 45 12 -8 0 -12Z" fill="#ffe1eb"/>
                        <path d="M0 -12 C-4 -8 -5 44 0 74 C5 44 4 -8 0 -12Z" fill="#ff5b9e"/>
                        <path d="M-10 66 L-7 84 M10 66 L7 84" stroke="#82405e" stroke-width="2"/>
                        <rect x="-11" y="82" width="22" height="12" rx="2" fill="#89506a"/>
                    </g>
                    <g transform="translate(289 104) scale(.65)">
                        <path d="M0 74 C-36 25 -27 -12 0 -12 C27 -12 36 25 0 74Z" fill="url(#balloonB)"/>
                        <path d="M0 -12 C-12 -8 -16 45 0 74 C16 45 12 -8 0 -12Z" fill="#ffe8f1"/>
                        <path d="M-10 66 L-7 84 M10 66 L7 84" stroke="#82405e" stroke-width="2"/>
                        <rect x="-11" y="82" width="22" height="12" rx="2" fill="#89506a"/>
                    </g>
                    <g fill="#fff" opacity=".93">
                        <circle cx="84" cy="253" r="17"/><circle cx="106" cy="244" r="26"/><circle cx="137" cy="255" r="17"/>
                        <circle cx="328" cy="277" r="21"/><circle cx="354" cy="263" r="31"/><circle cx="390" cy="276" r="22"/>
                    </g>
                </svg>
            </div>''', unsafe_allow_html=True)
        st.markdown('<div class="auth-welcome">Tus arriendos, a tu ritmo</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="auth-welcome-text">Tu próxima reserva, tu calendario '
                    'y tus propiedades, siempre a mano.</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-mini-divider"></div>', unsafe_allow_html=True)


def page_login():
    """Acceso de dos etapas: bienvenida → RUT y contraseña.

    Conserva las invitaciones/recuperación de cuenta y el acceso seguro por RUT.
    """
    # Debe mostrarse también durante la bienvenida para que los enlaces de
    # invitación/recuperación sigan funcionando sin un inicio de sesión previo.
    activacion.render_activation()
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)

    if st.session_state.get("auth_step") not in ("welcome", "login"):
        st.session_state["auth_step"] = "welcome"

    st.markdown('<div class="auth-overline">ARRIENDOS TEMPORALES</div>',
                unsafe_allow_html=True)

    izquierda, derecha = st.columns([.96, 1.04], gap="large", vertical_alignment="center")

    with izquierda:
        _render_login_illustration()

    if st.session_state["auth_step"] == "welcome":
        with derecha:
            with st.container(border=True):
                st.markdown('<div class="auth-welcome-anchor"></div>', unsafe_allow_html=True)
                st.markdown('<div class="auth-welcome-kicker">TU LUGAR PARA ORGANIZARTE</div>',
                            unsafe_allow_html=True)
                st.markdown('<div class="auth-welcome-headline">Bienvenido a tu espacio de arriendos</div>',
                            unsafe_allow_html=True)
                st.markdown("""<div class="auth-welcome-description">
                    Tus reservas, departamentos y fechas importantes,
                    organizados de forma sencilla en un solo lugar.
                </div>""", unsafe_allow_html=True)
                st.markdown("""<div class="auth-welcome-features">
                    <strong>Todo lo que necesitas para gestionar tus arriendos:</strong><br>
                    Reservas y calendario · Departamentos · Liquidaciones
                </div>""", unsafe_allow_html=True)
                if st.button("Empezar", key="auth_start", type="primary",
                             use_container_width=True):
                    st.session_state["auth_step"] = "login"
                    st.rerun()
                st.markdown('<div class="auth-access-note">Acceso exclusivo para personas autorizadas.</div>',
                            unsafe_allow_html=True)
        return

    with derecha:
        with st.container(border=True):
            st.markdown('<div class="auth-form-anchor"></div>', unsafe_allow_html=True)
            st.markdown('''<div class="auth-header-art">
                <svg viewBox="0 0 470 167" preserveAspectRatio="xMidYMid slice"
                     xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <rect width="470" height="167" fill="#f6beda"/>
                    <g opacity=".72">
                        <path d="M20 -25 C-28 33 7 107 49 96 C90 85 99 22 48 -25" fill="#e97eae"/>
                        <path d="M48 -25 C33 7 36 71 49 96 C62 71 65 7 48 -25" fill="#fce2ec"/>
                        <path d="M29 80 L35 110 M69 80 L63 110" stroke="#a95080" stroke-width="2"/>
                        <rect x="32" y="110" width="35" height="14" rx="3" fill="#b15b88"/>
                    </g>
                    <g opacity=".58" transform="translate(212 48) scale(.54)">
                        <path d="M0 60 C-40 7 -30 -25 0 -25 C30 -25 40 7 0 60Z" fill="#db72a8"/>
                        <path d="M0 -25 C-14 -19 -19 29 0 60 C19 29 14 -19 0 -25Z" fill="#ffeaf2"/>
                        <path d="M-8 55 L-5 70 M8 55 L5 70" stroke="#874a72" stroke-width="3"/>
                        <rect x="-10" y="70" width="20" height="12" rx="3" fill="#a65a86"/>
                    </g>
                    <path d="M-30 160 Q70 96 155 142 T354 127 T500 124 V188 H-30Z" fill="#ffeaf3"/>
                    <path d="M-20 174 Q92 127 170 166 T362 160 T500 154 V191 H-20Z" fill="#fff8fb"/>
                    <g fill="#fff8fb">
                        <circle cx="382" cy="125" r="31"/><circle cx="418" cy="107" r="39"/>
                        <circle cx="462" cy="132" r="32"/>
                    </g>
                </svg>
            </div>''', unsafe_allow_html=True)
            st.markdown('<div class="auth-form-kicker">TU CUENTA PERSONAL</div>',
                        unsafe_allow_html=True)
            st.markdown('<div class="auth-form-heading">Iniciar sesión</div>',
                        unsafe_allow_html=True)
            st.markdown('<div class="auth-form-subtitle">Ingresa con tu RUT y '
                        'tu contraseña personal.</div>', unsafe_allow_html=True)

            with st.form("rut_login"):
                rut = st.text_input("RUT", placeholder="12.345.678-5")
                pwd = st.text_input("Contraseña", type="password",
                                    placeholder="Ingresa tu contraseña")
                sent = st.form_submit_button("Iniciar sesión", type="primary",
                                             use_container_width=True)

            if sent:
                try:
                    acceso.sign_in(rut, pwd, _profile_by_rut, _finish_first_access)
                except Exception as error:
                    st.error(
                        f"Error al iniciar sesión. Tipo: {type(error).__name__}" 
                    )
                else:
                    st.session_state.page = "Inicio"
                    st.rerun()

            with st.expander("¿Olvidaste tu contraseña?"):
                st.caption("Solicita un enlace de recuperación al correo de tu cuenta.")
                with st.form("password_recovery"):
                    recovered_rut = st.text_input("Tu RUT", key="recover_rut")
                    send_recovery = st.form_submit_button("Solicitar enlace")
                if send_recovery:
                    try:
                        r = acceso.normalize_rut(recovered_rut)
                        p = _profile_by_rut(r)
                        if p and p.get("is_active"):
                            acceso.send_password_recovery(p["login_email"])
                    except Exception:
                        pass
                    st.info("Si tu cuenta tiene acceso habilitado, recibirás instrucciones por correo.")

            st.markdown('<div class="auth-authorized">Acceso exclusivo para cuentas '
                        'autorizadas.</div>', unsafe_allow_html=True)

            if st.button("← Volver a bienvenida", key="auth_back", use_container_width=True):
                st.session_state["auth_step"] = "welcome"
                st.rerun()


try:
    _profile = acceso.current_profile(_profile_by_uid)
except Exception:
    st.error("No se pudo comprobar la sesión. Revisa los Secrets de Supabase Auth.")
    st.stop()
if _profile is None:
    st.markdown("<style>[data-testid='stSidebar'] {display:none !important;}</style>",
                unsafe_allow_html=True)
    page_login()
    st.stop()

# =========================================================
# FUNCIONES
# =========================================================

def money(value):
    return f"${int(value):,}".replace(",", ".")


def department_columns():
    return table_columns("departments")


def insert_department(condo, name, capacity, winter, summer, owner_id):
    """Inserta un departamento y mantiene compatibilidad con esquemas antiguos."""
    conn = db()
    cols = department_columns()

    if "condominium" in cols:
        conn.execute("""
            INSERT INTO departments
            (condo, condominium, name, capacity, winter_price, summer_price, owner_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (condo, condo, name, capacity, winter, summer, owner_id))
    else:
        conn.execute("""
            INSERT INTO departments
            (condo, name, capacity, winter_price, summer_price, owner_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (condo, name, capacity, winter, summer, owner_id))

    conn.commit()
    conn.close()


def delete_reservation(reservation_id):
    """Elimina la reserva y sus datos asociados."""
    conn = db()
    conn.execute("DELETE FROM payments WHERE reservation_id=?", (reservation_id,))
    conn.execute("DELETE FROM checklist WHERE reservation_id=?", (reservation_id,))
    conn.execute("DELETE FROM reservations WHERE id=?", (reservation_id,))
    conn.commit()
    conn.close()


@st.cache_data(ttl=15, max_entries=128, show_spinner=False)
def _departments_for_user(user_id, owner_id):
    """Caché por usuario. Nunca compartir resultados entre propietarios."""
    conn = db()
    try:
        rows = conn.execute("""
            SELECT d.*, o.rut AS owner_rut, o.full_name AS owner_name
            FROM departments d LEFT JOIN owners o ON o.id=d.owner_id
            WHERE d.active=1
            ORDER BY d.condo, d.name
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_departments():
    profile = st.session_state["auth_profile"]
    return _departments_for_user(str(st.session_state["auth_uid"]),
                                 str(profile.get("owner_id") or "admin"))


@st.cache_data(ttl=15, max_entries=128, show_spinner=False)
def _reservations_for_user(user_id, owner_id):
    """RLS sigue aplicado al consultar y la caché está aislada por identidad."""
    conn = db()
    try:
        rows = conn.execute("""
            SELECT r.*, d.name AS dept_name, d.condo, d.capacity
            FROM reservations r
            JOIN departments d ON d.id=r.department_id
            ORDER BY r.check_in
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_reservations():
    profile = st.session_state["auth_profile"]
    return _reservations_for_user(str(st.session_state["auth_uid"]),
                                  str(profile.get("owner_id") or "admin"))


def get_reservation(reservation_id):
    conn = db()
    row = conn.execute("""
        SELECT r.*, d.name AS dept_name, d.condo, d.capacity
        FROM reservations r
        JOIN departments d ON d.id=r.department_id
        WHERE r.id=?
    """, (reservation_id,)).fetchone()
    conn.close()
    return row


def conflict_exists(department_id, check_in, check_out, ignore_id=None):
    conn = db()

    query = """
        SELECT id, guest, check_in, check_out
        FROM reservations
        WHERE department_id=?
          AND check_in < ?
          AND check_out > ?
    """
    params = [department_id, check_out.isoformat(), check_in.isoformat()]

    if ignore_id is not None:
        query += " AND id != ?"
        params.append(ignore_id)

    row = conn.execute(query, params).fetchone()
    conn.close()
    return row


def save_reservation(
    department_id, guest, phone, check_in, check_in_time,
    check_out, check_out_time, guests, price_night,
    deposit_percent, status, reservation_id=None
):
    nights = (check_out - check_in).days
    total = nights * price_night
    deposited = round(total * (deposit_percent / 100))

    conn = db()
    try:
        cur = conn.cursor()
        reservation_columns = table_columns("reservations")

        if reservation_id:
            if not is_admin():
                raise PermissionError("Solo la administradora puede editar una reserva.")
            if "guest_name" in reservation_columns:
                cur.execute("""
                    UPDATE reservations
                    SET department_id=?, guest=?, guest_name=?, phone=?, check_in=?,
                        check_in_time=?, check_out=?, check_out_time=?,
                        guests=?, price_night=?, nights=?, total=?,
                        deposit_percent=?, deposited=?, status=?
                    WHERE id=?
                """, (
                    department_id, guest, guest, phone, check_in.isoformat(),
                    check_in_time, check_out.isoformat(), check_out_time,
                    guests, price_night, nights, total,
                    deposit_percent, deposited, status, reservation_id
                ))
            else:
                cur.execute("""
                    UPDATE reservations
                    SET department_id=?, guest=?, phone=?, check_in=?,
                        check_in_time=?, check_out=?, check_out_time=?,
                        guests=?, price_night=?, nights=?, total=?,
                        deposit_percent=?, deposited=?, status=?
                    WHERE id=?
                """, (
                    department_id, guest, phone, check_in.isoformat(),
                    check_in_time, check_out.isoformat(), check_out_time,
                    guests, price_night, nights, total,
                    deposit_percent, deposited, status, reservation_id
                ))
            rid = reservation_id
        else:
            if "guest_name" in reservation_columns:
                cur.execute("""
                    INSERT INTO reservations
                    (department_id, guest, guest_name, phone, check_in, check_in_time,
                     check_out, check_out_time, guests, price_night, nights,
                     total, deposit_percent, deposited, status, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                """, (
                    department_id, guest, guest, phone, check_in.isoformat(),
                    check_in_time, check_out.isoformat(), check_out_time,
                    guests, price_night, nights, total,
                    deposit_percent, deposited, status, st.session_state["auth_uid"]
                ))
            else:
                cur.execute("""
                    INSERT INTO reservations
                    (department_id, guest, phone, check_in, check_in_time,
                     check_out, check_out_time, guests, price_night, nights,
                     total, deposit_percent, deposited, status, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                """, (
                    department_id, guest, phone, check_in.isoformat(),
                    check_in_time, check_out.isoformat(), check_out_time,
                    guests, price_night, nights, total,
                    deposit_percent, deposited, status, st.session_state["auth_uid"]
                ))

            rid = cur.fetchone()["id"]

            cur.execute("""
                INSERT INTO checklist
                (reservation_id, cleaning, internet, inspected, keys)
                VALUES (?, 0, 0, 0, 0)
                ON CONFLICT (reservation_id) DO NOTHING
            """, (rid,))

        conn.commit()
        return rid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_checklist(reservation_id, cleaning, internet, inspected, keys):
    conn = db()
    conn.execute("""
        INSERT INTO checklist
        (reservation_id, cleaning, internet, inspected, keys)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(reservation_id)
        DO UPDATE SET
            cleaning=excluded.cleaning,
            internet=excluded.internet,
            inspected=excluded.inspected,
            keys=excluded.keys
    """, (
        reservation_id,
        int(cleaning),
        int(internet),
        int(inspected),
        int(keys),
    ))
    conn.commit()
    conn.close()


def get_checklist(reservation_id):
    conn = db()
    row = conn.execute("""
        SELECT * FROM checklist WHERE reservation_id=?
    """, (reservation_id,)).fetchone()
    conn.close()
    return row


def set_page(page, reservation_id=None):
    st.session_state.page = page
    if page in ("Inicio", "Reservas", "Calendario", "Departamentos", "Liquidaciones", "Propietarios", "Mi cuenta"):
        # Los accesos directos desde Detalle no deben volver accidentalmente a Inicio.
        st.session_state.nav_choice = page
    if reservation_id is not None:
        st.session_state.selected_reservation = reservation_id
        if page == "Liquidaciones":
            st.session_state.liquidation_selected_reservation = int(reservation_id)
            st.session_state.liq_condo_filter = "Todos"
            st.session_state.liq_department_filter = "Todos"
            st.session_state.liq_select_reservation = int(reservation_id)
            st.session_state.liq_view = "Preparar liquidación"


def add_payment(reservation_id, amount, note):
    conn = db()
    conn.execute("""
        INSERT INTO payments
        (reservation_id, amount, payment_date, note)
        VALUES (?, ?, ?, ?)
    """, (reservation_id, amount, date.today().isoformat(), note))
    conn.execute("""
        UPDATE reservations
        SET deposited = deposited + ?
        WHERE id=?
    """, (amount, reservation_id))

    row = conn.execute("""
        SELECT total, deposited FROM reservations WHERE id=?
    """, (reservation_id,)).fetchone()

    status = "Pagado completamente" if row["deposited"] >= row["total"] else "Abono recibido"

    conn.execute("""
        UPDATE reservations SET status=? WHERE id=?
    """, (status, reservation_id))

    conn.commit()
    conn.close()


def get_payments(reservation_id):
    conn = db()
    rows = conn.execute("""
        SELECT * FROM payments
        WHERE reservation_id=?
        ORDER BY payment_date DESC, id DESC
    """, (reservation_id,)).fetchall()
    conn.close()
    return rows


def reminders_for(reservations):
    today = date.today()
    reminders = []

    # Antes se abría una conexión y se consultaba checklist por CADA reserva,
    # incluso por reservas antiguas. Ahora consultamos solo las llegadas de mañana.
    tomorrow_ids = [int(r["id"]) for r in reservations
                    if date.fromisoformat(r["check_in"]) == today + timedelta(days=1)]
    checklists = {}
    if tomorrow_ids:
        conn = db()
        try:
            rows = conn.execute(
                "SELECT reservation_id, cleaning, internet "
                "FROM checklist WHERE reservation_id = ANY(%s)",
                (tomorrow_ids,),
            ).fetchall()
            checklists = {int(row["reservation_id"]): row for row in rows}
        finally:
            conn.close()

    for r in reservations:
        ci = date.fromisoformat(r["check_in"])
        co = date.fromisoformat(r["check_out"])
        days_to_in = (ci - today).days
        days_to_out = (co - today).days
        checklist = checklists.get(int(r["id"])) if days_to_in == 1 else None

        if days_to_in == 2:
            reminders.append((
                "important",
                "Confirmar hora de llegada",
                f"{r['guest']} llega en 2 días a {r['dept_name']} · {r['condo']}",
                r["id"]
            ))

        if days_to_in == 1:
            if not checklist or not checklist["cleaning"]:
                reminders.append((
                    "urgent",
                    "Aseo pendiente",
                    f"{r['dept_name']} recibe a {r['guest']} mañana.",
                    r["id"]
                ))
            if not checklist or not checklist["internet"]:
                reminders.append((
                    "important",
                    "Verificar internet",
                    f"Revisar internet antes del check-in de {r['guest']}.",
                    r["id"]
                ))

        if days_to_out == 1:
            reminders.append((
                "important",
                "Check-out mañana",
                f"Enviar instrucciones de salida a {r['guest']}.",
                r["id"]
            ))

        if days_to_in == 0:
            reminders.append((
                "today",
                "Check-in hoy",
                f"{r['guest']} llega hoy a {r['dept_name']}.",
                r["id"]
            ))

        if days_to_out == 0:
            reminders.append((
                "today",
                "Check-out hoy",
                f"{r['guest']} debe salir hoy de {r['dept_name']}.",
                r["id"]
            ))

    return reminders


# =========================================================
# ESTADO DE NAVEGACIÓN
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "Inicio"

if "selected_reservation" not in st.session_state:
    st.session_state.selected_reservation = None

pages = ["Inicio", "Reservas", "Calendario", "Departamentos", "Liquidaciones"]
if is_admin():
    pages.append("Propietarios")
pages.append("Mi cuenta")

with st.sidebar:
    st.markdown('<div class="brand">🌸 Arriendos</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="brand-small">Gestión de reservas temporales</div>',
        unsafe_allow_html=True
    )

    # El widget tiene su propia clave; NO modificamos esa clave desde los botones.
    # "Detalle" es una pantalla interna y no aparece en el menú.
    # Cuando estamos allí, mostramos Inicio seleccionado para evitar
    # el error ValueError: 'Detalle' is not in list.
    visible_page = (
        st.session_state.page
        if st.session_state.page in pages
        else "Inicio"
    )

    nav_choice = st.radio(
        "MENÚ",
        pages,
        index=pages.index(visible_page),
        key="nav_choice"
    )

    # No reemplazar una pantalla interna (Detalle) por el valor del radio.
    if st.session_state.page in pages and nav_choice != st.session_state.page:
        st.session_state.page = nav_choice

    st.divider()

    st.caption(f"{st.session_state['auth_profile']['full_name']}")
    st.caption("Administración" if is_admin() else "Panel de propietario")
    st.caption(date.today().strftime("%d/%m/%Y"))
    if st.button("Cerrar sesión", use_container_width=True):
        acceso.clear_session()
        st.session_state["auth_step"] = "welcome"
        st.rerun()

# =========================================================
# INICIO
# =========================================================

@st.cache_data(show_spinner=False)
def _portada_data_uri():
    """Busca automáticamente una imagen cuyo nombre sea portada."""
    base_dir = Path(__file__).resolve().parent
    extensiones = {".jpg", ".jpeg", ".png", ".webp"}

    # Busca primero en la carpeta de la aplicación y luego en assets.
    carpetas = [base_dir, base_dir / "assets"]

    for carpeta in carpetas:
        if not carpeta.is_dir():
            continue

        # Acepta portada.jpg, portada.jpeg, portada.png, etc.
        # También acepta nombres como portada_1.jpg o portada-final.png.
        for archivo in sorted(carpeta.iterdir()):
            if not archivo.is_file():
                continue
            if archivo.suffix.lower() not in extensiones:
                continue
            if not archivo.stem.lower().startswith("portada"):
                continue

            try:
                datos = archivo.read_bytes()
                tipos = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".webp": "image/webp",
                }
                mime = tipos[archivo.suffix.lower()]
                encoded = base64.b64encode(datos).decode("utf-8")
                return f"data:{mime};base64,{encoded}"
            except Exception:
                continue

    return None


def _slug_archivo(texto):
    """Convierte un nombre de condominio a un nombre de archivo simple."""
    normalizado = unicodedata.normalize("NFKD", str(texto))
    normalizado = "".join(c for c in normalizado if not unicodedata.combining(c))
    limpio = "".join(c.lower() if c.isalnum() else "_" for c in normalizado)
    while "__" in limpio:
        limpio = limpio.replace("__", "_")
    return limpio.strip("_")


def _archivo_a_data_uri(file_path):
    """Convierte una imagen local a data URI para usarla dentro de las tarjetas."""
    try:
        if not file_path.exists() or not file_path.is_file():
            return None
        tipos = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        mime = tipos.get(file_path.suffix.lower())
        if not mime:
            return None
        encoded = base64.b64encode(file_path.read_bytes()).decode("utf-8")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return None


@st.cache_data(ttl=3600, max_entries=256, show_spinner=False)
def _get_condo_image_cached(user_id, condo_key):
    """Caché de imágenes por usuario para evitar mezclar accesos de propietarios."""
    if not condo_key:
        return None

    conn = db()
    try:
        row = conn.execute(
            "SELECT image_data, image_mime FROM condo_images WHERE condo_key=?",
            (condo_key,)
        ).fetchone()
        if not row or not row["image_data"]:
            return None
        return bytes(row["image_data"]), (row["image_mime"] or "image/jpeg")
    finally:
        conn.close()


def _get_condo_image_row(condo):
    """Compatibilidad: devuelve los bytes/mime cacheados del edificio."""
    return _get_condo_image_cached(str(st.session_state["auth_uid"]),
                                   _slug_archivo(condo))


def _condo_has_saved_image(condo):
    return _get_condo_image_row(condo) is not None


def save_condo_image(condo, uploaded_file):
    """Guarda o reemplaza la fotografía de un edificio en Supabase."""
    if uploaded_file is None:
        return

    image_bytes = uploaded_file.getvalue()
    if not image_bytes:
        raise ValueError("La imagen está vacía.")

    # Evita guardar fotografías enormes dentro de PostgreSQL.
    max_bytes = 5 * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise ValueError("La imagen supera 5 MB. Usa una foto más liviana.")

    mime = getattr(uploaded_file, "type", None) or "image/jpeg"
    allowed_mimes = {"image/jpeg", "image/png", "image/webp"}
    if mime not in allowed_mimes:
        raise ValueError("Formato no permitido. Usa JPG, PNG o WEBP.")

    condo_name = str(condo).strip()
    condo_key = _slug_archivo(condo_name)
    if not condo_key:
        raise ValueError("Escribe primero el nombre del edificio.")

    conn = db()
    try:
        conn.execute(
            """
            INSERT INTO condo_images
            (condo_key, condo_name, image_data, image_mime, updated_at)
            VALUES (?, ?, ?, ?, NOW())
            ON CONFLICT(condo_key) DO UPDATE SET
                condo_name=EXCLUDED.condo_name,
                image_data=EXCLUDED.image_data,
                image_mime=EXCLUDED.image_mime,
                updated_at=NOW()
            """,
            (condo_key, condo_name, psycopg2.Binary(image_bytes), mime)
        )
        conn.commit()
        _get_condo_image_cached.clear()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_condo_image_if_unused(condo):
    """Borra la foto solo cuando ya no quedan departamentos de ese edificio."""
    condo_key = _slug_archivo(condo)
    conn = db()
    try:
        remaining = conn.execute(
            "SELECT COUNT(*) AS total FROM departments WHERE condo=?",
            (condo,)
        ).fetchone()["total"]
        if int(remaining) == 0:
            conn.execute("DELETE FROM condo_images WHERE condo_key=?", (condo_key,))
            conn.commit()
            _get_condo_image_cached.clear()
    finally:
        conn.close()


def _condo_image_data_uri(condo):
    """
    Busca primero la foto persistente del edificio en Supabase.
    Si aún no existe, prueba archivos locales y finalmente portada.jpg.
    """
    saved = _get_condo_image_row(condo)
    if saved:
        try:
            raw, mime = saved
            encoded = base64.b64encode(raw).decode("utf-8")
            return f"data:{mime};base64,{encoded}"
        except Exception:
            pass

    base_dir = Path(__file__).resolve().parent
    slug = _slug_archivo(condo)
    carpetas = [base_dir, base_dir / "assets", base_dir / "assets" / "edificios"]
    nombres_base = [slug, f"edificio_{slug}", f"condominio_{slug}"]
    extensiones = [".jpg", ".jpeg", ".png", ".webp"]

    for carpeta in carpetas:
        for nombre in nombres_base:
            for extension in extensiones:
                uri = _archivo_a_data_uri(carpeta / f"{nombre}{extension}")
                if uri:
                    return uri

    # Si todavía no tienes una foto específica del edificio,
    # se usa portada.jpg para que la tarjeta nunca quede vacía.
    return _portada_data_uri()


_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]
_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def fecha_espanol(fecha):
    return f"{_DIAS[fecha.weekday()]} {fecha.day} de {_MESES[fecha.month - 1]} de {fecha.year}"


def fecha_corta_espanol(fecha):
    return f"{fecha.day} {_MESES[fecha.month - 1][:3]}"


def page_section_header(title, subtitle, kicker="Gestión de arriendos temporales"):
    """Muestra la misma portada de Inicio, usando portada.jpg como imagen real."""
    image_uri = _portada_data_uri()

    if image_uri:
        hero_html = f"""
        <section class="hero page-hero">
            <img class="hero-image" src="{image_uri}" alt="Portada de la aplicación">
            <div class="hero-overlay"></div>
            <div class="hero-content">
                <div class="hero-kicker">{kicker}</div>
                <h1 class="hero-title">{title}</h1>
                <div class="hero-text">{subtitle}</div>
            </div>
        </section>
        """
    else:
        hero_html = f"""
        <section class="hero page-hero hero-no-image">
            <div class="hero-content">
                <div class="hero-kicker">{kicker}</div>
                <h1 class="hero-title">{title}</h1>
                <div class="hero-text">{subtitle}</div>
            </div>
        </section>
        """

    st.markdown(hero_html, unsafe_allow_html=True)


def page_inicio():
    reservations = get_reservations()
    today = date.today()

    # Portada: busca automáticamente cualquier imagen cuyo nombre comience con "portada".
    image_uri = _portada_data_uri()

    if image_uri:
        hero_html = f"""
        <section class="hero">
            <img class="hero-image" src="{image_uri}" alt="Portada de la aplicación">
            <div class="hero-overlay"></div>
            <div class="hero-content">
                <div class="hero-kicker">Gestión de arriendos temporales</div>
                <h1 class="hero-title">Tu espacio,<br>tus reservas.</h1>
                <div class="hero-text">Organiza tus departamentos, reservas, pagos y pendientes en un solo lugar.</div>
                <div class="hero-date">📅 {fecha_espanol(today).capitalize()}</div>
            </div>
        </section>
        """
    else:
        hero_html = f"""
        <section class="hero hero-no-image">
            <div class="hero-content">
                <div class="hero-kicker">Gestión de arriendos temporales</div>
                <h1 class="hero-title">Tu espacio,<br>tus reservas.</h1>
                <div class="hero-text">Organiza tus departamentos, reservas, pagos y pendientes en un solo lugar.</div>
                <div class="hero-date">📅 {fecha_espanol(today).capitalize()}</div>
            </div>
        </section>
        """

    st.markdown(hero_html, unsafe_allow_html=True)

    st.markdown('<div class="home-intro">Aquí tienes una vista rápida de lo que necesita tu atención.</div>', unsafe_allow_html=True)

    current_month = today.month
    current_year = today.year

    month_res = [
        r for r in reservations
        if date.fromisoformat(r["check_in"]).month == current_month
        and date.fromisoformat(r["check_in"]).year == current_year
    ]

    income = sum(r["total"] for r in month_res)
    nights = sum(r["nights"] for r in month_res)
    pending = sum(max(r["total"] - r["deposited"], 0) for r in month_res)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">INGRESOS DEL MES</div>
                <div class="metric-value metric-accent">{money(income)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">RESERVAS DEL MES</div>
                <div class="metric-value">{len(month_res)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">NOCHES ARRENDADAS</div>
                <div class="metric-value">{nights}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">SALDO PENDIENTE</div>
                <div class="metric-value">{money(pending)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown('<div class="section-title">Próximos arriendos</div>', unsafe_allow_html=True)

    upcoming = [
        r for r in reservations
        if date.fromisoformat(r["check_out"]) >= today
    ][:6]

    if not upcoming:
        st.info("No hay próximos arriendos registrados.")
    else:
        cols = st.columns(3)

        for i, r in enumerate(upcoming):
            ci = date.fromisoformat(r["check_in"])
            co = date.fromisoformat(r["check_out"])

            with cols[i % 3]:
                st.markdown(
                    f"""
                    <div class="reservation-card">
                        <span class="reservation-tag">Próximo arriendo</span>
                        <div class="reservation-name">{html_escape(str(r['guest']))}</div>
                        <div class="reservation-info">
                            🏢 {html_escape(str(r['dept_name']))} · {html_escape(str(r['condo']))}<br>
                            📅 {fecha_corta_espanol(ci)} → {fecha_corta_espanol(co)} {co.year}<br>
                            👥 {r['guests']} huéspedes · 🌙 {r['nights']} noches
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.button(
                    "Ver reserva",
                    key=f"detail_{r['id']}",
                    use_container_width=True,
                    on_click=set_page,
                    args=("Detalle", r["id"]),
                )

    st.markdown('<div class="section-title">🔔 Recordatorios</div>', unsafe_allow_html=True)

    reminders = reminders_for(reservations)

    if not reminders:
        st.success("Todo al día. No tienes recordatorios pendientes para hoy.")

    for kind, title, text_value, rid in reminders[:8]:
        st.markdown(
            f"""
            <div class="reminder">
                <div class="reminder-title">{html_escape(title)}</div>
                <div class="reminder-text">{html_escape(text_value)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.button(
            "Abrir reserva",
            key=f"rem_{kind}_{rid}_{title}",
            on_click=set_page,
            args=("Detalle", rid),
        )


# =========================================================
# RESERVAS
# =========================================================

def page_reservas():
    page_section_header(
        "Reservas",
        "Crea, revisa y administra tus reservas de forma simple y ordenada."
    )

    tab_new, tab_list = st.tabs(["＋ Nueva reserva", "Reservas registradas"])

    departments = get_departments()

    with tab_new:
        if not departments:
            st.warning("Primero debes registrar un departamento.")
            return

        options = {
            f"{d['condo']} · {d['name']}": d for d in departments
        }

        selected_label = st.selectbox(
            "Departamento",
            list(options.keys()),
            key="new_dept"
        )
        selected_dept = options[selected_label]

        c1, c2 = st.columns(2)

        with c1:
            guest = st.text_input("Nombre del huésped", key="new_guest")
            phone = st.text_input("Teléfono / contacto", key="new_phone")
            check_in = st.date_input(
                "Entrada",
                value=date.today(),
                key="new_checkin"
            )
            check_in_time = st.time_input(
                "Hora de check-in",
                value=datetime.strptime("15:00", "%H:%M").time(),
                key="new_checkin_time"
            )

        with c2:
            guests = st.number_input(
                "Cantidad de huéspedes",
                min_value=1,
                max_value=int(selected_dept["capacity"]),
                value=1,
                key="new_guests"
            )
            check_out = st.date_input(
                "Salida",
                value=date.today() + timedelta(days=1),
                key="new_checkout"
            )
            check_out_time = st.time_input(
                "Hora de check-out",
                value=datetime.strptime("11:00", "%H:%M").time(),
                key="new_checkout_time"
            )

        price = st.number_input(
            "Precio por noche",
            min_value=0,
            value=int(selected_dept["summer_price"]),
            step=5000,
            key="new_price"
        )

        deposit_percent = st.slider(
            "Porcentaje de abono",
            min_value=0,
            max_value=100,
            value=30,
            key="new_deposit_percent"
        )

        valid_dates = check_out > check_in

        if valid_dates:
            nights = (check_out - check_in).days
            total = nights * price
            deposit = round(total * deposit_percent / 100)
            balance = total - deposit
        else:
            nights = 0
            total = 0
            deposit = 0
            balance = 0
            st.error("El check-out debe ser posterior al check-in.")

        # Los cálculos se muestran mientras completas la reserva,
        # pero NO se comprueba disponibilidad todavía.
        st.markdown(
            f"""
            <div class="payment-summary">
                <div class="payment-card">
                    <div class="payment-card-label">NOCHES</div>
                    <div class="payment-card-value">{nights}</div>
                </div>
                <div class="payment-card">
                    <div class="payment-card-label">TOTAL</div>
                    <div class="payment-card-value">{money(total)}</div>
                </div>
                <div class="payment-card">
                    <div class="payment-card-label">ABONO</div>
                    <div class="payment-card-value">{money(deposit)}</div>
                </div>
                <div class="payment-card">
                    <div class="payment-card-label">SALDO INICIAL</div>
                    <div class="payment-card-value">{money(balance)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        current_snapshot = (
            selected_dept["id"],
            guest.strip(),
            phone.strip(),
            check_in.isoformat(),
            check_in_time.strftime("%H:%M"),
            check_out.isoformat(),
            check_out_time.strftime("%H:%M"),
            int(guests),
            int(price),
            int(deposit_percent),
        )

        reviewed = st.session_state.get("reservation_review")
        reviewed_snapshot = (
            reviewed.get("snapshot")
            if isinstance(reviewed, dict)
            else None
        )

        # Si el usuario cambia cualquier dato después de revisar,
        # se exige volver a revisar antes de guardar.
        if reviewed_snapshot is not None and reviewed_snapshot != current_snapshot:
            st.session_state.reservation_review = None
            reviewed = None
            reviewed_snapshot = None
            st.info("Cambiaste un dato de la reserva. Presiona nuevamente «Revisar reserva» para actualizar la revisión.")

        if st.button(
            "👁️ Revisar reserva",
            type="primary",
            use_container_width=True,
            key="review_reservation"
        ):
            if not guest.strip():
                st.warning("Ingresa el nombre del huésped antes de revisar.")
                st.session_state.reservation_review = None
            elif not valid_dates:
                st.error("Corrige las fechas antes de revisar.")
                st.session_state.reservation_review = None
            else:
                st.session_state.reservation_review = {
                    "snapshot": current_snapshot,
                    "department_id": selected_dept["id"],
                    "condo": selected_dept["condo"],
                    "dept_name": selected_dept["name"],
                    "guest": guest.strip(),
                    "phone": phone.strip(),
                    "check_in": check_in,
                    "check_in_time": check_in_time,
                    "check_out": check_out,
                    "check_out_time": check_out_time,
                    "guests": int(guests),
                    "price": int(price),
                    "deposit_percent": int(deposit_percent),
                    "nights": nights,
                    "total": total,
                    "deposit": deposit,
                    "balance": balance,
                }
                st.rerun()

        reviewed = st.session_state.get("reservation_review")

        if isinstance(reviewed, dict):
            st.markdown(
                '<div class="section-title">Revisión de la reserva</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <div class="detail-box">
                    <div class="detail-label">HUÉSPED</div>
                    <div class="detail-value">{html_escape(reviewed["guest"])}</div><br>
                    <div class="detail-label">CONTACTO</div>
                    <div class="detail-value">{html_escape(reviewed["phone"] or "No registrado")}</div><br>
                    <div class="detail-label">DEPARTAMENTO</div>
                    <div class="detail-value">🏢 {html_escape(reviewed["condo"])} · {html_escape(reviewed["dept_name"])}</div><br>
                    <div class="detail-label">ESTADÍA</div>
                    <div class="detail-value">
                        {reviewed["check_in"].strftime("%d/%m/%Y")} · {reviewed["check_in_time"].strftime("%H:%M")}
                        → {reviewed["check_out"].strftime("%d/%m/%Y")} · {reviewed["check_out_time"].strftime("%H:%M")}
                    </div><br>
                    <div class="detail-label">HUÉSPEDES</div>
                    <div class="detail-value">{reviewed["guests"]}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <div class="payment-summary">
                    <div class="payment-card">
                        <div class="payment-card-label">NOCHES</div>
                        <div class="payment-card-value">{reviewed["nights"]}</div>
                    </div>
                    <div class="payment-card">
                        <div class="payment-card-label">TOTAL</div>
                        <div class="payment-card-value">{money(reviewed["total"])}</div>
                    </div>
                    <div class="payment-card">
                        <div class="payment-card-label">ABONO</div>
                        <div class="payment-card-value">{money(reviewed["deposit"])}</div>
                    </div>
                    <div class="payment-card">
                        <div class="payment-card-label">SALDO INICIAL</div>
                        <div class="payment-card-value">{money(reviewed["balance"])}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.info("La disponibilidad se comprobará recién al guardar la reserva.")

            save_col, cancel_col = st.columns(2)

            with save_col:
                if st.button(
                    "💾 Guardar reserva",
                    type="primary",
                    use_container_width=True,
                    key="confirm_reservation"
                ):
                    # Última comprobación visual; PostgreSQL evita cruces simultáneos.
                    conflict = conflict_exists(
                        reviewed["department_id"],
                        reviewed["check_in"],
                        reviewed["check_out"]
                    )

                    if conflict:
                        st.error(
                            f"❌ No se puede guardar. El departamento ya está reservado "
                            f"por {conflict['guest']} desde "
                            f"{date.fromisoformat(conflict['check_in']).strftime('%d/%m/%Y')} "
                            f"hasta {date.fromisoformat(conflict['check_out']).strftime('%d/%m/%Y')}."
                        )
                    else:
                        try:
                            rid = save_reservation(
                                reviewed["department_id"],
                                reviewed["guest"],
                                reviewed["phone"],
                                reviewed["check_in"],
                                reviewed["check_in_time"].strftime("%H:%M"),
                                reviewed["check_out"],
                                reviewed["check_out_time"].strftime("%H:%M"),
                                reviewed["guests"],
                                reviewed["price"],
                                reviewed["deposit_percent"],
                                "Pagado completamente" if reviewed["deposit_percent"] == 100 else (
                                    "Sin abono" if reviewed["deposit_percent"] == 0 else "Abono recibido"
                                )
                            )
                        except psycopg2.errors.ExclusionViolation:
                            st.error("Otro usuario reservó esas fechas antes. Revisa el calendario.")
                        except Exception:
                            st.error("No fue posible confirmar la reserva. Revisa disponibilidad y permisos.")
                        else:
                            st.session_state.reservation_review = None
                            st.session_state.selected_reservation = rid
                            st.success("Reserva confirmada y compartida en ambos calendarios.")
                            st.rerun()

            with cancel_col:
                if st.button(
                    "Cancelar revisión",
                    use_container_width=True,
                    key="cancel_reservation_review"
                ):
                    st.session_state.reservation_review = None
                    st.rerun()

    with tab_list:
        reservations = get_reservations()

        for r in reservations:
            ci = date.fromisoformat(r["check_in"])
            co = date.fromisoformat(r["check_out"])

            col1, col2 = st.columns([5, 1])

            with col1:
                st.markdown(
                    f"""
                    <div class="detail-box compact">
                        <b>{html_escape(str(r['guest']))}</b><br>
                        <span style="color:{MUTED}">
                        {r['condo']} · {r['dept_name']} ·
                        {ci.strftime('%d/%m/%Y')} → {co.strftime('%d/%m/%Y')}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col2:
                st.button(
                    "Abrir",
                    key=f"open_res_{r['id']}",
                    use_container_width=True,
                    on_click=set_page,
                    args=("Detalle", r["id"]),
                )


# =========================================================
# DETALLE
# =========================================================

def page_detalle():
    rid = st.session_state.get("selected_reservation")

    if not rid:
        st.warning("No se ha seleccionado ninguna reserva.")
        st.button(
            "← Volver a Inicio",
            on_click=set_page,
            args=("Inicio",)
        )
        return

    r = get_reservation(rid)

    if not r:
        st.error("No se encontró la reserva.")
        return

    st.button(
        "← Volver",
        on_click=set_page,
        args=("Inicio",)
    )

    st.markdown('<div class="main-title">Detalle de reserva</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="reservation-heading">
            <span class="reservation-heading-guest">{html_escape(str(r['guest']))}</span>
            <span class="reservation-heading-place">🏢 {html_escape(str(r['condo']))} · {html_escape(str(r['dept_name']))}</span>
        </div>""",
        unsafe_allow_html=True
    )

    ci = date.fromisoformat(r["check_in"])
    co = date.fromisoformat(r["check_out"])
    balance = max(r["total"] - r["deposited"], 0)

    st.markdown('<div class="section-title">Información</div>', unsafe_allow_html=True)

    info1, info2 = st.columns(2)

    with info1:
        st.markdown(
            f"""
            <div class="detail-box compact">
                <div class="detail-label">HUÉSPED</div>
                <div class="detail-value">{html_escape(str(r['guest']))}</div><br>
                <div class="detail-label">CONTACTO</div>
                <div class="detail-value">{html_escape(str(r['phone'] or 'No registrado'))}</div><br>
                <div class="detail-label">DEPARTAMENTO</div>
                <div class="detail-value">{html_escape(str(r['condo']))} · {html_escape(str(r['dept_name']))}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with info2:
        st.markdown(
            f"""
            <div class="detail-box">
                <div class="detail-label">CHECK-IN</div>
                <div class="detail-value">{ci.strftime('%d/%m/%Y')} · {r['check_in_time']}</div><br>
                <div class="detail-label">CHECK-OUT</div>
                <div class="detail-value">{co.strftime('%d/%m/%Y')} · {r['check_out_time']}</div><br>
                <div class="detail-label">CAPACIDAD DEL DEPARTAMENTO</div>
                <div class="detail-value">{r['capacity']} huéspedes</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if not is_admin():
        st.markdown('<div class="section-title">Estado de la reserva</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", money(r["total"]))
        c2.metric("Abonado", money(r["deposited"]))
        c3.metric("Saldo", money(balance))
        st.caption("La administradora gestiona pagos, modificaciones y liquidaciones.")
        return

    st.button(
        "Crear o consultar liquidación del propietario",
        key=f"liquidation_shortcut_{rid}",
        on_click=set_page,
        args=("Liquidaciones", rid),
    )

    st.markdown('<div class="section-title payment-section">💳 Pagos</div>', unsafe_allow_html=True)

    # Resumen personalizado para mantener el diseño rosado/fucsia.
    st.markdown(
        f"""
        <div class="payment-summary">
            <div class="payment-card">
                <div class="payment-card-label">TOTAL</div>
                <div class="payment-card-value">{money(r["total"])}</div>
            </div>
            <div class="payment-card">
                <div class="payment-card-label">ABONADO</div>
                <div class="payment-card-value">{money(r["deposited"])}</div>
            </div>
            <div class="payment-card">
                <div class="payment-card-label">SALDO</div>
                <div class="payment-card-value">{money(balance)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="payment-status"><b>{r["status"]}</b> · Abono configurado: {r["deposit_percent"]:.0f}%</div>',
        unsafe_allow_html=True
    )

    with st.expander("＋ Registrar pago", expanded=False):
        pay1, pay2 = st.columns(2)
        with pay1:
            amount = st.number_input(
                "Monto del pago",
                min_value=0,
                step=5000,
                key=f"pay_amount_{rid}"
            )
        with pay2:
            note = st.text_input(
                "Nota (opcional)",
                key=f"pay_note_{rid}"
            )

        if st.button(
            "Registrar pago",
            type="primary",
            use_container_width=True,
            key=f"save_pay_{rid}"
        ):
            if amount <= 0:
                st.warning("Ingresa un monto mayor a 0.")
            else:
                add_payment(rid, amount, note)
                st.success("Pago registrado.")
                st.rerun()

    payments = get_payments(rid)

    if payments:
        st.markdown('<div class="payment-history-title">Historial de pagos</div>', unsafe_allow_html=True)
        for p in payments:
            note_text = f' · {p["note"]}' if p["note"] else ''
            st.markdown(
                f'<div class="payment-row"><span>{p["payment_date"]}</span><strong>{money(p["amount"])}</strong><span>{note_text}</span></div>',
                unsafe_allow_html=True
            )

    st.markdown('<div class="section-title">🧹 Preparación del departamento</div>', unsafe_allow_html=True)

    checklist = get_checklist(rid)

    cleaning = st.checkbox(
        "Aseo listo",
        value=bool(checklist["cleaning"]) if checklist else False,
        key=f"clean_{rid}"
    )

    internet = st.checkbox(
        "Internet funcionando",
        value=bool(checklist["internet"]) if checklist else False,
        key=f"internet_{rid}"
    )

    inspected = st.checkbox(
        "Departamento revisado",
        value=bool(checklist["inspected"]) if checklist else False,
        key=f"inspect_{rid}"
    )

    keys = st.checkbox(
        "Llaves preparadas",
        value=bool(checklist["keys"]) if checklist else False,
        key=f"keys_{rid}"
    )

    if st.button(
        "Guardar checklist",
        type="primary",
        key=f"save_check_{rid}"
    ):
        update_checklist(rid, cleaning, internet, inspected, keys)
        st.success("Checklist actualizado.")

    st.markdown('<div class="section-title">✏️ Editar reserva</div>', unsafe_allow_html=True)

    departments = get_departments()
    dept_map = {
        f"{d['condo']} · {d['name']}": d for d in departments
    }

    current_label = f"{r['condo']} · {r['dept_name']}"

    with st.expander("Editar datos de la reserva"):
        edit_dept_label = st.selectbox(
            "Departamento",
            list(dept_map.keys()),
            index=list(dept_map.keys()).index(current_label),
            key=f"edit_dept_{rid}"
        )

        ed = dept_map[edit_dept_label]

        ec1, ec2 = st.columns(2)

        with ec1:
            edit_guest = st.text_input(
                "Huésped",
                value=r["guest"],
                key=f"edit_guest_{rid}"
            )
            edit_phone = st.text_input(
                "Teléfono",
                value=r["phone"],
                key=f"edit_phone_{rid}"
            )
            edit_checkin = st.date_input(
                "Entrada",
                value=ci,
                key=f"edit_ci_{rid}"
            )

        with ec2:
            edit_checkout = st.date_input(
                "Salida",
                value=co,
                key=f"edit_co_{rid}"
            )
            edit_guests = st.number_input(
                "Huéspedes",
                min_value=1,
                max_value=int(ed["capacity"]),
                value=min(int(r["guests"]), int(ed["capacity"])),
                key=f"edit_guests_{rid}"
            )
            edit_price = st.number_input(
                "Precio por noche",
                min_value=0,
                value=int(r["price_night"]),
                step=5000,
                key=f"edit_price_{rid}"
            )

        edit_deposit = st.slider(
            "Porcentaje de abono",
            0,
            100,
            int(r["deposit_percent"]),
            key=f"edit_dep_{rid}"
        )

        if edit_checkout <= edit_checkin:
            st.error("El check-out debe ser posterior al check-in.")
        else:
            edit_conflict = conflict_exists(
                ed["id"], edit_checkin, edit_checkout, ignore_id=rid
            )

            if edit_conflict:
                st.error("Las fechas chocan con otra reserva de este departamento.")

            if st.button(
                "Guardar cambios",
                type="primary",
                key=f"edit_save_{rid}",
                disabled=bool(edit_conflict)
            ):
                nights = (edit_checkout - edit_checkin).days
                total = nights * edit_price
                deposited = int(r["deposited"])

                if deposited > total:
                    deposited = total

                status = (
                    "Pagado completamente"
                    if deposited >= total
                    else ("Sin abono" if deposited == 0 else "Abono recibido")
                )

                conn = db()
                conn.execute("""
                    UPDATE reservations
                    SET department_id=?, guest=?, phone=?,
                        check_in=?, check_out=?, guests=?,
                        price_night=?, nights=?, total=?,
                        deposit_percent=?, deposited=?, status=?
                    WHERE id=?
                """, (
                    ed["id"], edit_guest, edit_phone,
                    edit_checkin.isoformat(), edit_checkout.isoformat(),
                    edit_guests, edit_price, nights, total,
                    edit_deposit, deposited, status, rid
                ))
                conn.commit()
                conn.close()

                st.success("Reserva actualizada.")
                st.rerun()


    # -----------------------------------------------------
    # ELIMINAR RESERVA
    # -----------------------------------------------------
    st.markdown('<div class="danger-zone"></div>', unsafe_allow_html=True)

    if st.button(
        "🗑️ Eliminar reserva",
        key=f"delete_reservation_{rid}",
    ):
        st.session_state[f"confirm_delete_{rid}"] = True
        st.rerun()

    if st.session_state.get(f"confirm_delete_{rid}", False):
        st.warning(
            f"Vas a eliminar la reserva de {r['guest']} ({r['condo']} · {r['dept_name']}). "
            "También se eliminarán sus pagos y checklist. Esta acción no se puede deshacer."
        )
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button(
                "Sí, eliminar reserva",
                key=f"confirm_delete_yes_{rid}",
                type="primary",
                use_container_width=True
            ):
                delete_reservation(rid)
                st.session_state.pop(f"confirm_delete_{rid}", None)
                st.session_state.pop("selected_reservation", None)
                st.session_state.page = "Reservas"
                st.rerun()
        with dc2:
            if st.button(
                "Cancelar",
                key=f"confirm_delete_no_{rid}",
                use_container_width=True
            ):
                st.session_state.pop(f"confirm_delete_{rid}", None)
                st.rerun()


# =========================================================
# CALENDARIO
# =========================================================

def page_calendario():
    page_section_header(
        "Calendario",
        "Consulta la disponibilidad de tus departamentos antes de ofrecer fechas."
    )

    departments = get_departments()
    reservations = get_reservations()

    condos = sorted({d["condo"] for d in departments})

    if not condos:
        st.warning("No hay departamentos registrados.")
        return

    condo = st.selectbox("Condominio", condos, index=0)

    condo_depts = [d for d in departments if d["condo"] == condo]

    mode = st.radio(
        "Vista",
        ["Todos los departamentos", "Un departamento"],
        horizontal=True
    )

    if mode == "Un departamento":
        dept_label = st.selectbox(
            "Departamento",
            [d["name"] for d in condo_depts]
        )
        selected_depts = [d for d in condo_depts if d["name"] == dept_label]
    else:
        selected_depts = condo_depts

    c1, c2 = st.columns(2)

    with c1:
        year = st.number_input(
            "Año",
            min_value=2025,
            max_value=2035,
            value=date.today().year
        )

    with c2:
        month = st.selectbox(
            "Mes",
            list(range(1, 13)),
            index=date.today().month - 1,
            format_func=lambda x: _MESES[x - 1].capitalize()
        )

    st.markdown(
        f'<div class="section-title">{_MESES[month - 1].capitalize()} de {year}</div>',
        unsafe_allow_html=True
    )

    # Leyenda
    st.markdown(
        f"""
        <span class="availability-free">Disponible</span>
        &nbsp;&nbsp;
        <span class="availability-busy">Reservado</span>
        """,
        unsafe_allow_html=True
    )

    days = monthrange(year, month)[1]

    for dept in selected_depts:
        st.markdown(
            f'<div class="section-title">{dept["name"]}</div>',
            unsafe_allow_html=True
        )

        cols = st.columns(7)
        weekday_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

        for i, name in enumerate(weekday_names):
            cols[i].markdown(
                f"<div style='text-align:center;color:{MUTED};font-weight:700;font-size:.78rem'>{name}</div>",
                unsafe_allow_html=True
            )

        first_weekday = date(year, month, 1).weekday()

        cells = [None] * first_weekday + list(range(1, days + 1))

        while len(cells) % 7 != 0:
            cells.append(None)

        for start in range(0, len(cells), 7):
            cols = st.columns(7)

            for idx, day_num in enumerate(cells[start:start + 7]):
                with cols[idx]:
                    if day_num is None:
                        st.write("")
                        continue

                    current = date(year, month, day_num)

                    busy = False
                    guest_name = ""

                    for r in reservations:
                        if r["department_id"] != dept["id"]:
                            continue

                        ri = date.fromisoformat(r["check_in"])
                        ro = date.fromisoformat(r["check_out"])

                        if ri <= current < ro:
                            busy = True
                            guest_name = r["guest"]
                            break

                    cls = "calendar-day busy" if busy else "calendar-day"
                    status_class = "busy" if busy else "free"
                    status_text = "Ocup." if busy else "Libre"
                    dot = "🔴" if busy else "🟢"

                    st.markdown(
                        f"""
                        <div class="{cls}" title="{html_escape(str(guest_name)) if busy else 'Disponible'}">
                            <div class="calendar-day-number">{day_num}</div>
                            <div class="calendar-status {status_class}">{dot} {status_text}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if busy:
                        st.caption(guest_name)

    st.divider()

    st.markdown('<div class="section-title">🔎 Buscar disponibilidad</div>', unsafe_allow_html=True)
    st.caption("Filtra por fechas, edificio y capacidad mínima de huéspedes.")

    max_capacity = max(int(d["capacity"]) for d in departments) if departments else 1
    search_condos = ["Todos los edificios"] + sorted({d["condo"] for d in departments})

    b1, b2, b3, b4 = st.columns([1.15, 1.15, 1, 1.35])

    with b1:
        search_in = st.date_input(
            "Entrada",
            value=date.today(),
            key="search_in"
        )

    with b2:
        search_out = st.date_input(
            "Salida",
            value=date.today() + timedelta(days=2),
            key="search_out"
        )

    with b3:
        min_capacity = st.number_input(
            "Capacidad mínima",
            min_value=1,
            max_value=max_capacity,
            value=min(4, max_capacity),
            step=1,
            key="search_capacity",
            help="Ejemplo: si eliges 5, aparecerán departamentos para 5 o más personas."
        )

    with b4:
        search_condo = st.selectbox(
            "Edificio / condominio",
            search_condos,
            key="search_condo"
        )

    if st.button(
        "🔍 Buscar departamentos disponibles",
        type="primary",
        use_container_width=True
    ):
        if search_out <= search_in:
            st.error("La salida debe ser posterior a la entrada.")
        else:
            available = []

            for d in departments:
                if int(d["capacity"]) < int(min_capacity):
                    continue
                if search_condo != "Todos los edificios" and d["condo"] != search_condo:
                    continue

                conflict = conflict_exists(
                    d["id"], search_in, search_out
                )
                if not conflict:
                    available.append(d)

            if available:
                st.success(
                    f"Encontramos {len(available)} departamento(s) disponible(s) "
                    f"para {int(min_capacity)} o más huésped(es)."
                )

                nights_search = (search_out - search_in).days
                result_cols = st.columns(3)

                for i, d in enumerate(available):
                    with result_cols[i % 3]:
                        total_reference = nights_search * int(d["summer_price"])
                        st.markdown(
                            f"""
                            <div class="search-result-card">
                                <div class="search-result-building">🏢 {html_escape(str(d['condo']))}</div>
                                <div class="search-result-name">{html_escape(str(d['name']))}</div>
                                <div>👥 Hasta {d['capacity']} huéspedes</div>
                                <div>🌙 {nights_search} noche(s)</div>
                                <div>☀️ Verano · {money(d['summer_price'])} / noche</div>
                                <div style="margin-top:7px;font-weight:800;color:{FUCHSIA_DARK}">
                                    Referencia verano: {money(total_reference)}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
            else:
                st.warning(
                    "No encontramos departamentos disponibles con esas fechas y capacidad. "
                    "Prueba cambiando las fechas, el edificio o la capacidad mínima."
                )


# =========================================================
# DEPARTAMENTOS
# =========================================================

def page_departamentos():
    if not is_admin():
        page_section_header("Mis departamentos", "Propiedades vinculadas a tu RUT.")
        departments = get_departments()
        if not departments:
            st.info("Aún no tienes departamentos asociados. Solicita a la administradora que los asigne.")
            return
        cols = st.columns(3)
        for i, d in enumerate(departments):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{html_escape(d['condo'])} · {html_escape(d['name'])}**")
                    st.write(f"Capacidad: {d['capacity']} huéspedes")
                    st.write(f"Invierno: {money(d['winter_price'])}")
                    st.write(f"Verano: {money(d['summer_price'])}")
                    st.caption(f"RUT propietario: {d['owner_rut']}")
        return
    page_section_header(
        "Departamentos",
        "Explora tus edificios y administra los departamentos de cada uno."
    )

    departments = get_departments()
    owners = admin_owners()
    owner_labels = {f"{o['full_name']} · {o['rut']}": o['id'] for o in owners}
    if not owners:
        st.warning("Primero registra un propietario desde la sección Propietarios.")

    with st.expander("＋ Agregar departamento"):
        st.caption(
            "Registra el departamento y, si es un edificio nuevo, puedes subir su fotografía. "
            "La foto queda guardada en Supabase y se reutiliza para todos sus departamentos."
        )

        condo = st.text_input(
            "Edificio / condominio",
            placeholder="Ej. Serena Pacífico",
            key="new_department_condo"
        )
        name = st.text_input(
            "Nombre o número del departamento",
            placeholder="Ej. Depto 305",
            key="new_department_name"
        )

        selected_owner_label = st.selectbox(
            "RUT del dueño / propietario", list(owner_labels),
            key="new_department_owner", disabled=not bool(owner_labels),
        ) if owner_labels else None

        clean_condo = condo.strip()
        existing_condo_names = {str(d["condo"]).strip() for d in departments}
        same_existing = next(
            (c for c in existing_condo_names if c.casefold() == clean_condo.casefold()),
            None
        ) if clean_condo else None

        if same_existing:
            if _condo_has_saved_image(same_existing):
                st.success(
                    f"{same_existing} ya tiene una fotografía guardada. "
                    "Puedes dejar este campo vacío o subir otra para reemplazarla."
                )
            else:
                st.info(
                    f"{same_existing} ya existe, pero todavía no tiene una fotografía guardada. "
                    "Puedes agregarla ahora."
                )

        building_photo = st.file_uploader(
            "Foto del edificio (opcional)",
            type=["jpg", "jpeg", "png", "webp"],
            key="new_building_photo",
            help="Máximo 5 MB. La misma foto se usará para todos los departamentos de este edificio."
        )

        if building_photo is not None:
            st.image(building_photo, caption="Vista previa de la fotografía", use_container_width=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            capacity = st.number_input(
                "Capacidad", min_value=1, value=4, key="new_department_capacity"
            )
        with c2:
            winter = st.number_input(
                "Precio noche invierno", min_value=0, value=60000, step=5000,
                key="new_department_winter"
            )
        with c3:
            summer = st.number_input(
                "Precio noche verano", min_value=0, value=90000, step=5000,
                key="new_department_summer"
            )

        if st.button("Agregar departamento", type="primary", use_container_width=True):
            if not clean_condo or not name.strip() or not selected_owner_label:
                st.warning("Completa el edificio, departamento y propietario.")
            else:
                # Si el usuario escribió el mismo edificio con diferencias de mayúsculas,
                # reutilizamos el nombre que ya existe para mantener todo agrupado.
                final_condo = same_existing or clean_condo

                try:
                    # Si se subió una imagen, se guarda primero. Si el edificio ya tenía
                    # una foto, esta operación la reemplaza.
                    if building_photo is not None:
                        save_condo_image(final_condo, building_photo)

                    insert_department(
                        final_condo,
                        name.strip(),
                        capacity,
                        winter,
                        summer,
                        owner_labels[selected_owner_label]
                    )
                    st.success("Departamento agregado correctamente.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"No se pudo guardar el departamento: {exc}")

    if not departments:
        st.info("No hay departamentos registrados.")
        return

    condos = {}
    for d in departments:
        condos.setdefault(d["condo"], []).append(d)

    st.markdown('<div class="section-title">Tus edificios</div>', unsafe_allow_html=True)
    st.caption("Presiona cada edificio para mostrar u ocultar sus departamentos.")

    for condo, deps in sorted(condos.items(), key=lambda item: item[0].lower()):
        slug = _slug_archivo(condo)
        state_key = f"condo_open_{slug}"
        if state_key not in st.session_state:
            st.session_state[state_key] = False

        image_uri = _condo_image_data_uri(condo)

        with st.container(border=True):
            if image_uri:
                st.markdown(
                    f"""
                    <div class="building-card">
                        <img src="{image_uri}" alt="{condo}">
                        <div class="building-overlay"></div>
                        <div class="building-content">
                            <div class="building-kicker">Edificio / condominio</div>
                            <div class="building-name">{html_escape(str(condo))}</div>
                            <div class="building-count">🏠 {len(deps)} departamento(s)</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div class="building-card building-fallback">
                        <div class="building-content">
                            <div class="building-kicker">Edificio / condominio</div>
                            <div class="building-name">{html_escape(str(condo))}</div>
                            <div class="building-count">🏠 {len(deps)} departamento(s)</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            top_left, top_right = st.columns([3, 1])
            with top_left:
                is_open = bool(st.session_state[state_key])
                button_text = "▲ Ocultar departamentos" if is_open else "▼ Ver departamentos"
                if st.button(
                    button_text,
                    key=f"toggle_{slug}",
                    use_container_width=True
                ):
                    st.session_state[state_key] = not is_open
                    st.rerun()

            with top_right:
                with st.popover("📷 Foto", use_container_width=True):
                    st.caption("Cambia la fotografía del edificio. Se guardará permanentemente en Supabase.")
                    replacement_photo = st.file_uploader(
                        "Nueva fotografía",
                        type=["jpg", "jpeg", "png", "webp"],
                        key=f"replace_photo_{slug}",
                        help="Máximo 5 MB."
                    )
                    if replacement_photo is not None:
                        st.image(replacement_photo, caption="Vista previa", use_container_width=True)
                        if st.button(
                            "Guardar nueva foto",
                            type="primary",
                            key=f"save_photo_{slug}",
                            use_container_width=True
                        ):
                            try:
                                save_condo_image(condo, replacement_photo)
                                st.success("Fotografía actualizada.")
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                            except Exception as exc:
                                st.error(f"No se pudo guardar la fotografía: {exc}")

            if st.session_state[state_key]:
                st.markdown('<div class="departments-inside"></div>', unsafe_allow_html=True)
                dept_cols = st.columns(3)

                for i, d in enumerate(deps):
                    with dept_cols[i % 3]:
                        st.markdown(
                            f"""
                            <div class="dept-card">
                                <div class="dept-name">{html_escape(str(d['name']))}</div>
                                <div class="dept-condo">{html_escape(str(d['condo']))}</div>
                                <div>RUT dueño: {d['owner_rut'] or 'Sin asignar'}</div>
                                <div>👥 Hasta {d['capacity']} huéspedes</div>
                                <div>❄️ Invierno · {money(d['winter_price'])}</div>
                                <div>☀️ Verano · {money(d['summer_price'])}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        with st.expander("Modificar"):
                            current_owner_id = d["owner_id"]
                            owner_options = ["Sin asignar"] + list(owner_labels)
                            owner_current_label = next(
                                (lbl for lbl, oid in owner_labels.items() if oid == current_owner_id),
                                "Sin asignar",
                            )
                            selected_edit_owner = st.selectbox(
                                "RUT propietario", owner_options,
                                index=owner_options.index(owner_current_label),
                                key=f"owner_d_{d['id']}",
                            )
                            next_owner_id = owner_labels.get(selected_edit_owner)
                            new_name = st.text_input(
                                "Nombre",
                                value=d["name"],
                                key=f"dn_{d['id']}"
                            )
                            new_capacity = st.number_input(
                                "Capacidad",
                                min_value=1,
                                value=int(d["capacity"]),
                                key=f"dc_{d['id']}"
                            )
                            new_winter = st.number_input(
                                "Invierno",
                                min_value=0,
                                value=int(d["winter_price"]),
                                step=5000,
                                key=f"dw_{d['id']}"
                            )
                            new_summer = st.number_input(
                                "Verano",
                                min_value=0,
                                value=int(d["summer_price"]),
                                step=5000,
                                key=f"ds_{d['id']}"
                            )

                            if st.button("Guardar cambios", key=f"save_d_{d['id']}", use_container_width=True):
                                conn = db()
                                cols_db = department_columns()
                                if "condominium" in cols_db:
                                    conn.execute("""
                                        UPDATE departments
                                        SET name=?, capacity=?, winter_price=?, summer_price=?, owner_id=?, condominium=condo
                                        WHERE id=?
                                    """, (new_name, new_capacity, new_winter, new_summer, next_owner_id, d["id"]))
                                else:
                                    conn.execute("""
                                        UPDATE departments
                                        SET name=?, capacity=?, winter_price=?, summer_price=?, owner_id=?
                                        WHERE id=?
                                    """, (new_name, new_capacity, new_winter, new_summer, next_owner_id, d["id"]))
                                conn.commit()
                                conn.close()
                                st.success("Departamento actualizado.")
                                st.rerun()

                            st.markdown('<div class="danger-zone"></div>', unsafe_allow_html=True)

                            if st.button(
                                "🗑️ Eliminar departamento",
                                key=f"delete_d_{d['id']}",
                                use_container_width=True
                            ):
                                conn = db()
                                reservation_count = conn.execute(
                                    "SELECT COUNT(*) FROM reservations WHERE department_id=?",
                                    (d["id"],)
                                ).fetchone()[0]

                                if reservation_count:
                                    conn.close()
                                    st.error(
                                        "No se puede eliminar este departamento porque "
                                        f"tiene {reservation_count} reserva(s) asociada(s). "
                                        "Elimina o gestiona primero esas reservas."
                                    )
                                else:
                                    old_condo = d["condo"]
                                    conn.execute(
                                        "DELETE FROM departments WHERE id=?",
                                        (d["id"],)
                                    )
                                    conn.commit()
                                    conn.close()
                                    delete_condo_image_if_unused(old_condo)
                                    st.success("Departamento eliminado correctamente.")
                                    st.rerun()



# =========================================================
# LIQUIDACIONES PARA PROPIETARIOS
# =========================================================

EXPENSE_PRESETS = (
    ("aseo", "Aseo"),
    ("sabanas", "Lavado de sábanas"),
    ("ventanas", "Limpieza de ventanas"),
)


def format_clp(value):
    """Moneda CLP correcta para montos negativos, sin decimales."""
    value = int(value)
    return ("-" if value < 0 else "") + money(abs(value))


def calculate_owner_liquidation(gross_total, commission_percent, expenses):
    """La comisión corresponde al bruto reservado, nunca al abono recibido."""
    gross_total = int(gross_total)
    commission_percent = int(commission_percent)
    if gross_total < 0 or commission_percent not in (10, 12):
        raise ValueError("Monto o porcentaje de comisión no permitido.")
    commission = (gross_total * commission_percent + 50) // 100
    expenses_total = 0
    for item in expenses:
        amount = int(item["amount"])
        if amount < 0:
            raise ValueError("Los gastos no pueden ser negativos.")
        expenses_total += amount
    return {
        "gross_total": gross_total,
        "commission_amount": commission,
        "expenses_total": expenses_total,
        "owner_net": gross_total - commission - expenses_total,
    }


def get_owner_liquidation_settings(department_id):
    conn = db()
    try:
        row = conn.execute(
            "SELECT * FROM owner_liquidation_settings WHERE department_id=?",
            (department_id,)
        ).fetchone()
        return dict(row) if row else {
            "owner_name": "", "commission_percent": 10, "usual_costs": {}
        }
    finally:
        conn.close()


def get_owner_liquidation(reservation_id):
    conn = db()
    try:
        row = conn.execute(
            "SELECT * FROM owner_liquidations WHERE reservation_id=?",
            (reservation_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_owner_liquidations():
    conn = db()
    try:
        rows = conn.execute("""
            SELECT * FROM owner_liquidations
            ORDER BY updated_at DESC, id DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_owner_liquidation(reservation, owner_name, commission_percent,
                           expenses, notes, usual_costs):
    """Guarda una liquidación por reserva y los gastos frecuentes por departamento.

    Consulta nuevamente el total real de la reserva antes de guardar, para evitar
    usar un total antiguo si la reserva fue editada en otra sesión.
    """
    rid = int(reservation["id"])
    conn = db()
    try:
        cur = conn.cursor()
        fresh = cur.execute("""
            SELECT r.*, d.name AS dept_name, d.condo
            FROM reservations r
            JOIN departments d ON d.id=r.department_id
            WHERE r.id=? FOR UPDATE OF r
        """, (rid,)).fetchone()
        if not fresh:
            raise ValueError("La reserva fue eliminada. Actualiza la pantalla.")
        if any(fresh[k] != reservation[k] for k in
               ("total", "check_in", "check_out", "department_id")):
            raise ValueError("La reserva cambió desde que abriste la liquidación. Recarga y revisa los montos.")
        amounts = calculate_owner_liquidation(fresh["total"], commission_percent, expenses)
        cur.execute("""
            INSERT INTO owner_liquidations (
                reservation_id, owner_name, condo_name, department_name, guest_name,
                check_in, check_out, nights, price_night, gross_total,
                commission_percent, commission_amount, expenses, expenses_total,
                owner_net, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?, ?, NOW())
            ON CONFLICT (reservation_id) DO UPDATE SET
                owner_name=EXCLUDED.owner_name,
                condo_name=EXCLUDED.condo_name,
                department_name=EXCLUDED.department_name,
                guest_name=EXCLUDED.guest_name,
                check_in=EXCLUDED.check_in,
                check_out=EXCLUDED.check_out,
                nights=EXCLUDED.nights,
                price_night=EXCLUDED.price_night,
                gross_total=EXCLUDED.gross_total,
                commission_percent=EXCLUDED.commission_percent,
                commission_amount=EXCLUDED.commission_amount,
                expenses=EXCLUDED.expenses,
                expenses_total=EXCLUDED.expenses_total,
                owner_net=EXCLUDED.owner_net,
                notes=EXCLUDED.notes,
                updated_at=NOW()
        """, (
            rid, owner_name.strip(), fresh["condo"], fresh["dept_name"],
            fresh["guest"], fresh["check_in"], fresh["check_out"],
            int(fresh["nights"]), int(fresh["price_night"]),
            amounts["gross_total"], int(commission_percent),
            amounts["commission_amount"], json.dumps(expenses, ensure_ascii=False),
            amounts["expenses_total"], amounts["owner_net"], notes.strip(),
        ))
        cur.execute("""
            INSERT INTO owner_liquidation_settings
                (department_id, owner_name, commission_percent, usual_costs, updated_at)
            VALUES (?, ?, ?, ?::jsonb, NOW())
            ON CONFLICT (department_id) DO UPDATE SET
                owner_name=EXCLUDED.owner_name,
                commission_percent=EXCLUDED.commission_percent,
                usual_costs=EXCLUDED.usual_costs,
                updated_at=NOW()
        """, (
            fresh["department_id"], owner_name.strip(), int(commission_percent),
            json.dumps(usual_costs, ensure_ascii=False)
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@st.cache_data(show_spinner=False, max_entries=256)
def owner_liquidation_pdf(statement):
    """Genera el comprobante PDF desde datos previamente guardados."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=19 * mm, rightMargin=19 * mm,
        topMargin=20 * mm, bottomMargin=18 * mm,
        title=f"Liquidación arriendo {statement['id']}",
        author="Administración de arriendos",
    )
    dark = colors.HexColor("#26212A")
    muted = colors.HexColor("#77717A")
    accent = colors.HexColor("#B83272")
    light = colors.HexColor("#FAF1F6")
    white = colors.white
    normal = ParagraphStyle("liq_normal", fontName="Helvetica", fontSize=9.5,
                            leading=14, textColor=dark)
    small = ParagraphStyle("liq_small", parent=normal, fontSize=8.5,
                           leading=12, textColor=muted)
    title_style = ParagraphStyle("liq_title", parent=normal, fontName="Helvetica-Bold",
                                 fontSize=19, leading=24)
    section = ParagraphStyle("liq_section", parent=normal, fontName="Helvetica-Bold",
                             fontSize=10.5, spaceAfter=8)
    right = ParagraphStyle("liq_right", parent=normal, alignment=TA_RIGHT)
    row = ParagraphStyle("liq_row", parent=normal, fontSize=9, leading=13)
    row_bold = ParagraphStyle("liq_row_bold", parent=row, fontName="Helvetica-Bold")
    amount_style = ParagraphStyle("liq_amount", parent=row, alignment=TA_RIGHT)
    amount_bold = ParagraphStyle("liq_amount_bold", parent=amount_style,
                                 fontName="Helvetica-Bold")
    esc = lambda s: html_escape(str(s or ""))

    def pdf_date(raw):
        try:
            return date.fromisoformat(str(raw)[:10]).strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(raw)

    dated = statement.get("issued_at")
    if dated and hasattr(dated, "strftime"):
        issued = dated.strftime("%d/%m/%Y")
    else:
        issued = pdf_date(dated or date.today().isoformat())

    story = [
        Paragraph("LIQUIDACIÓN DE ARRIENDO", title_style),
        Spacer(1, 4 * mm),
        Paragraph("Detalle de ingresos y descuentos para el propietario", small),
        Spacer(1, 10 * mm),
    ]
    information = [
        [Paragraph("<b>Comprobante</b>", normal),
         Paragraph(f"LIQ-{int(statement['id']):06d}", right)],
        [Paragraph("<b>Fecha de emisión</b>", normal), Paragraph(issued, right)],
        [Paragraph("<b>Propietario</b>", normal),
         Paragraph(esc(statement.get("owner_name") or "No informado"), right)],
        [Paragraph("<b>Condominio</b>", normal),
         Paragraph(esc(statement.get("condo_name")), right)],
        [Paragraph("<b>Departamento</b>", normal),
         Paragraph(esc(statement.get("department_name")), right)],
        [Paragraph("<b>Huésped</b>", normal),
         Paragraph(esc(statement.get("guest_name")), right)],
        [Paragraph("<b>Entrada / salida</b>", normal),
         Paragraph(f"{pdf_date(statement['check_in'])} - {pdf_date(statement['check_out'])}", right)],
        [Paragraph("<b>Noches / valor por noche</b>", normal),
         Paragraph(f"{int(statement['nights'])} / {format_clp(statement['price_night'])}", right)],
    ]
    info = Table(information, colWidths=[70 * mm, 102 * mm], hAlign="LEFT")
    info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, -1), (-1, -1), .6, colors.HexColor("#E3D8DF")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([info, Spacer(1, 10 * mm), Paragraph("RESUMEN DE LA LIQUIDACIÓN", section)])
    expenses = statement.get("expenses") or []
    if isinstance(expenses, str):
        expenses = json.loads(expenses)
    lines = [
        [Paragraph("CONCEPTO", row_bold), Paragraph("MONTO", amount_bold)],
        [Paragraph("Total del arriendo", row),
         Paragraph(format_clp(statement["gross_total"]), amount_style)],
        [Paragraph(f"Comisión de administración ({int(statement['commission_percent'])}%)", row),
         Paragraph("-" + format_clp(statement["commission_amount"]), amount_style)],
    ]
    for item in expenses:
        lines.append([
            Paragraph(esc(item.get("concept", "Gasto")), row),
            Paragraph("-" + format_clp(item.get("amount", 0)), amount_style)
        ])
    if not expenses:
        lines.append([Paragraph("Otros gastos: sin cargos", row), Paragraph("$0", amount_style)])
    lines.append([
        Paragraph("TOTAL A ENTREGAR AL PROPIETARIO", row_bold),
        Paragraph(format_clp(statement["owner_net"]), amount_bold),
    ])
    tab = Table(lines, colWidths=[124 * mm, 48 * mm], hAlign="LEFT", repeatRows=1)
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), light),
        ("TEXTCOLOR", (0, 0), (-1, 0), accent),
        ("BACKGROUND", (0, -1), (-1, -1), light),
        ("LINEABOVE", (0, -1), (-1, -1), 1, accent),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 1), (-1, -2), .35, colors.HexColor("#E8E2E5")),
    ]))
    story.append(tab)
    if statement.get("notes", "").strip():
        story.extend([
            Spacer(1, 8 * mm), Paragraph("OBSERVACIONES", section),
            Paragraph(esc(statement["notes"]).replace("\n", "<br/>"), normal)
        ])
    story.extend([
        Spacer(1, 11 * mm),
        Paragraph("Documento interno de liquidación. No constituye boleta ni factura tributaria.", small)
    ])
    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#E4DCE1"))
        canvas.line(19 * mm, 15 * mm, 191 * mm, 15 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(muted)
        canvas.drawString(19 * mm, 11 * mm, "Arriendos temporales · Liquidación para propietario")
        canvas.drawRightString(191 * mm, 11 * mm, f"Página {document.page}")
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def filter_owner_liquidations(statements, condo="Todos", department="Todos", search=""):
    """Filtra comprobantes históricos por edificio, departamento y huésped/propietario."""
    def normalize(value):
        value = unicodedata.normalize("NFKD", str(value or ""))
        return "".join(c for c in value if not unicodedata.combining(c)).casefold()

    needle = normalize(search.strip())
    result = []
    for item in statements:
        place = f"{item['condo_name']} · {item['department_name']}"
        if condo != "Todos" and item["condo_name"] != condo:
            continue
        if department != "Todos" and place != department:
            continue
        if needle and needle not in normalize(
            f"{item.get('guest_name', '')} {item.get('owner_name', '')} "
            f"{place} {item.get('check_in', '')}"
        ):
            continue
        result.append(item)
    # Ver primero a quién llegó más recientemente, no el último documento editado.
    return sorted(result, key=lambda x: (str(x["check_in"]), int(x["id"])), reverse=True)


def page_historial_liquidaciones():
    st.markdown('<div class="section-title">Liquidaciones guardadas</div>', unsafe_allow_html=True)
    statements = list_owner_liquidations()
    if not statements:
        st.info("Todavía no hay liquidaciones guardadas. Puedes crear una en Preparar liquidación.")
        return

    condos = ["Todos"] + sorted({str(d["condo_name"]) for d in statements})
    a, b, c = st.columns([1, 1, 1.35])
    with a:
        condo = st.selectbox("Condominio", condos, key="liq_history_condo")
    departments = ["Todos"] + sorted({
        f"{d['condo_name']} · {d['department_name']}"
        for d in statements if condo == "Todos" or d["condo_name"] == condo
    })
    if st.session_state.get("liq_history_department", "Todos") not in departments:
        st.session_state.liq_history_department = "Todos"
    with b:
        department = st.selectbox("Departamento", departments, key="liq_history_department")
    with c:
        search = st.text_input(
            "Buscar huésped o propietario", key="liq_history_search",
            placeholder="Escribe un nombre…"
        )

    visible = filter_owner_liquidations(statements, condo, department, search)
    st.caption(f"Mostrando {len(visible)} de {len(statements)} liquidaciones, ordenadas por fecha de llegada.")
    if not visible:
        st.info("No hay liquidaciones que coincidan con los filtros.")
        return

    for i, document in enumerate(visible):
        if i % 3 == 0:
            columns = st.columns(3, gap="medium")
        sid = int(document["id"])
        guest = html_escape(str(document.get("guest_name") or "Sin nombre"))
        condo_name = html_escape(str(document.get("condo_name") or ""))
        dept_name = html_escape(str(document.get("department_name") or ""))
        owner = html_escape(str(document.get("owner_name") or "Sin registrar"))
        arrival = date.fromisoformat(str(document["check_in"])[:10]).strftime("%d/%m/%Y")
        departure = date.fromisoformat(str(document["check_out"])[:10]).strftime("%d/%m/%Y")
        with columns[i % 3]:
            with st.container(border=True):
                st.markdown(f"""
                    <div class="liq-card-inner">
                        <span class="liq-card-tag">Llegada · {arrival}</span>
                        <div class="liq-card-guest">{guest}</div>
                        <div class="liq-card-department">{dept_name} · {condo_name}</div>
                        <div class="liq-card-meta">
                            <strong>Salida:</strong> {departure}<br>
                            <strong>Propietario:</strong> {owner}<br>
                            <strong>Comprobante:</strong> LIQ-{sid:06d}
                        </div>
                        <div class="liq-card-result">
                            <span class="liq-card-result-label">Para el propietario</span>
                            <span class="liq-card-result-amount">{format_clp(document['owner_net'])}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                action_pdf, action_edit = st.columns([1.2, 0.8], gap="small")
                with action_pdf:
                    try:
                        pdf_bytes = owner_liquidation_pdf(document)
                    except ImportError:
                        st.caption("Falta ReportLab para descargar PDFs.")
                    else:
                        st.download_button(
                            "Descargar PDF", data=pdf_bytes,
                            file_name=f"liquidacion_{sid:06d}_{_slug_archivo(document['guest_name'])}.pdf",
                            mime="application/pdf", key=f"liq_pdf_card_{sid}",
                            use_container_width=True
                        )
                with action_edit:
                    if is_admin() and st.button("Editar", key=f"liq_edit_card_{sid}", use_container_width=True):
                        st.session_state.liquidation_selected_reservation = int(document["reservation_id"])
                        st.session_state.liq_condo_filter = "Todos"
                        st.session_state.liq_department_filter = "Todos"
                        st.session_state.liq_select_reservation = int(document["reservation_id"])
                        st.session_state.liq_view = "Preparar liquidación"
                        st.rerun()


def page_preparar_liquidacion():
    st.markdown('<div class="section-title">Preparar liquidación</div>', unsafe_allow_html=True)
    st.caption("El propietario y los precios habituales de aseo y lavado se recuerdan por departamento cuando guardas.")
    reservations = list(get_reservations())
    if not reservations:
        st.info("Registra una reserva para preparar la liquidación de su propietario.")
    else:
        condos = ["Todos"] + sorted({r["condo"] for r in reservations})
        condo_filter = st.selectbox("Filtrar por condominio", condos, key="liq_condo_filter")
        available = [r for r in reservations if condo_filter == "Todos" or r["condo"] == condo_filter]
        department_labels = ["Todos"] + sorted({
            f"{r['condo']} · {r['dept_name']}" for r in available
        })
        # Al cambiar el condominio, un filtro de departamento anterior puede dejar
        # de existir. Lo restablecemos antes de crear el widget.
        if st.session_state.get("liq_department_filter", "Todos") not in department_labels:
            st.session_state.liq_department_filter = "Todos"
        dept_filter = st.selectbox(
            "Filtrar por departamento", department_labels,
            key="liq_department_filter"
        )
        if dept_filter != "Todos":
            available = [r for r in available if f"{r['condo']} · {r['dept_name']}" == dept_filter]
        options = {int(r["id"]): r for r in available}
        ids = list(options)
        wanted = st.session_state.get("liquidation_selected_reservation")
        if not ids:
            st.info("No hay reservas para los filtros seleccionados.")
            return
        if st.session_state.get("liq_select_reservation") not in ids:
            st.session_state.liq_select_reservation = wanted if wanted in ids else ids[0]
        selected = st.selectbox(
            "Seleccionar reserva",
            ids,
            index=ids.index(wanted) if wanted in ids else 0,
            format_func=lambda rid: (
                f"{options[rid]['condo']} · {options[rid]['dept_name']} | "
                f"{options[rid]['guest']} | {options[rid]['check_in']} al {options[rid]['check_out']} "
                f"(N.º {rid})"
            ),
            key="liq_select_reservation",
        )
        r = options[selected]
        rid = int(r["id"])
        saved = get_owner_liquidation(rid)
        settings = get_owner_liquidation_settings(r["department_id"])
        costs = settings.get("usual_costs") or {}
        if isinstance(costs, str):
            costs = json.loads(costs)
        version = st.session_state.get(f"liq_refresh_{rid}", 0)
        prefix = f"owner_{rid}_v{version}"

        st.markdown(f"**{r['condo']} · {r['dept_name']}**  |  {r['guest']}")
        st.caption(
            f"Entrada: {date.fromisoformat(r['check_in']):%d/%m/%Y} · "
            f"Salida: {date.fromisoformat(r['check_out']):%d/%m/%Y} · "
            f"{r['nights']} noches · Precio/noche: {money(r['price_night'])}"
        )
        if saved and (
            int(saved["gross_total"]) != int(r["total"])
            or saved["check_in"] != r["check_in"]
            or saved["check_out"] != r["check_out"]
            or saved["department_name"] != r["dept_name"]
            or saved["condo_name"] != r["condo"]
        ):
            st.warning(
                "La reserva cambió después de guardar esta liquidación. "
                "Revisa los importes y presiona Guardar liquidación para actualizar el comprobante."
            )

        c_owner, c_pct = st.columns([3, 2])
        with c_owner:
            owner_name = st.text_input(
                "Nombre del propietario (opcional)",
                value=((saved.get("owner_name") or settings.get("owner_name", "")) if saved else settings.get("owner_name", "")),
                key=f"{prefix}_owner",
            )
        with c_pct:
            previous_pct = int(saved["commission_percent"] if saved else settings.get("commission_percent", 10))
            commission_percent = st.radio(
                "Comisión sobre el total del arriendo",
                [10, 12], index=[10, 12].index(previous_pct),
                format_func=lambda p: f"{p}%", horizontal=True,
                key=f"{prefix}_commission",
            )

        saved_expenses = saved.get("expenses") or [] if saved else []
        if isinstance(saved_expenses, str):
            saved_expenses = json.loads(saved_expenses)
        saved_standard = {x.get("code"): x for x in saved_expenses}
        expenses = []
        usual_costs = dict(costs)
        st.markdown("#### Gastos del arriendo")
        st.caption("Los valores habituales se recuerdan por departamento. Puedes activarlos, quitarlos o cambiar sus montos en cada arriendo.")
        for code, concept in EXPENSE_PRESETS:
            stored = saved_standard.get(code)
            default_cost = int(stored["amount"]) if stored else int(costs.get(code, 0))
            default_checked = bool(stored) if saved else bool(default_cost > 0 and code != "ventanas")
            chk_col, amt_col = st.columns([2, 1])
            with chk_col:
                enabled = st.checkbox(
                    concept, value=default_checked, key=f"{prefix}_{code}_enabled"
                )
            with amt_col:
                amount = st.number_input(
                    f"Valor de {concept}", min_value=0, value=default_cost,
                    step=1000, key=f"{prefix}_{code}_amount",
                    label_visibility="collapsed",
                )
            # Los importes usados quedan como referencia para el próximo arriendo.
            if int(amount) > 0:
                usual_costs[code] = int(amount)
            if enabled and amount > 0:
                expenses.append({"code": code, "concept": concept, "amount": int(amount)})
        existing_repair = saved_standard.get("reparaciones") if saved else None
        with st.expander("Arreglos o reparaciones (si hubo)", expanded=bool(existing_repair)):
            repairs_enabled = st.checkbox(
                "Incluir arreglos/reparaciones", value=bool(existing_repair),
                key=f"{prefix}_repairs_enabled"
            )
            rep_description = st.text_input(
                "Descripción del arreglo", value=(existing_repair or {}).get("description", ""),
                placeholder="Ej.: cambio de llave del baño", key=f"{prefix}_repair_description"
            )
            rep_amount = st.number_input(
                "Costo total del arreglo", min_value=0,
                value=int((existing_repair or {}).get("amount", 0)),
                step=1000, key=f"{prefix}_repair_amount"
            )
        if repairs_enabled and rep_amount > 0:
            expenses.append({
                "code": "reparaciones",
                "concept": f"Arreglos/reparaciones: {rep_description.strip() or 'Sin detalle'}",
                "description": rep_description.strip(), "amount": int(rep_amount),
            })
        saved_custom = [x for x in saved_expenses if x.get("code") == "otro"]
        with st.expander("Otros gastos (opcional)", expanded=bool(saved_custom)):
            extra_count = st.number_input(
                "Cantidad de gastos adicionales", min_value=0, max_value=15,
                value=len(saved_custom), step=1, key=f"{prefix}_extra_count"
            )
            for idx in range(int(extra_count)):
                prior = saved_custom[idx] if idx < len(saved_custom) else {}
                ec1, ec2 = st.columns([2, 1])
                with ec1:
                    extra_concept = st.text_input(
                        f"Concepto #{idx+1}", value=prior.get("concept", ""),
                        key=f"{prefix}_extra_name_{idx}"
                    )
                with ec2:
                    extra_amount = st.number_input(
                        f"Monto #{idx+1}", min_value=0,
                        value=int(prior.get("amount", 0)), step=1000,
                        key=f"{prefix}_extra_amount_{idx}"
                    )
                if extra_amount and extra_concept.strip():
                    expenses.append({
                        "code": "otro", "concept": extra_concept.strip(),
                        "amount": int(extra_amount),
                    })
                elif extra_amount and not extra_concept.strip():
                    st.warning(f"Agrega una descripción para el gasto adicional #{idx+1}.")
        notes = st.text_area(
            "Observaciones para el propietario (opcional)",
            value=saved["notes"] if saved else "",
            key=f"{prefix}_notes"
        )
        amounts = calculate_owner_liquidation(r["total"], commission_percent, expenses)
        st.markdown("#### Resumen calculado automáticamente")
        summary_data = [
            ("TOTAL ARRIENDO", amounts["gross_total"]),
            (f"COMISIÓN ({commission_percent}%)", amounts["commission_amount"]),
            ("GASTOS", amounts["expenses_total"]),
            ("PARA EL PROPIETARIO", amounts["owner_net"]),
        ]
        for col, (label, amount) in zip(st.columns(4), summary_data):
            with col:
                st.markdown(
                    f'<div class="metric-card"><div class="metric-label">{label}</div>'
                    f'<div class="metric-value">{format_clp(amount)}</div></div>',
                    unsafe_allow_html=True
                )
        st.caption(
            f"Cálculo: {format_clp(amounts['gross_total'])} - "
            f"{format_clp(amounts['commission_amount'])} - "
            f"{format_clp(amounts['expenses_total'])} = "
            f"{format_clp(amounts['owner_net'])}"
        )
        if amounts["owner_net"] < 0:
            st.warning("Los descuentos superan el ingreso del arriendo. Revisa los gastos antes de guardar.")
        if st.button(
            "Guardar liquidación", type="primary", use_container_width=True,
            key=f"{prefix}_save"
        ):
            try:
                save_owner_liquidation(r, owner_name, commission_percent, expenses, notes, usual_costs)
            except Exception as exc:
                st.error(f"No fue posible guardar la liquidación: {exc}")
            else:
                st.session_state[f"liq_refresh_{rid}"] = version + 1
                st.success("Liquidación guardada en Supabase. Ya puedes descargar su PDF.")
                st.rerun()

        if saved:
            st.divider()
            st.markdown("**Comprobante guardado**")
            st.caption("Este PDF contiene el último resumen guardado, no los cambios que aún no hayas guardado.")
            try:
                saved_pdf = owner_liquidation_pdf(saved)
            except ImportError:
                st.warning("No se puede generar el PDF. Agrega reportlab>=4.2,<5 en requirements.txt y vuelve a desplegar.")
            else:
                st.download_button(
                    "Descargar PDF de la liquidación",
                    data=saved_pdf,
                    file_name=f"liquidacion_{int(saved['id']):06d}_{_slug_archivo(saved['department_name'])}.pdf",
                    mime="application/pdf", use_container_width=True,
                    key=f"{prefix}_download"
                )


def page_liquidaciones():
    if not is_admin():
        page_section_header("Mis liquidaciones", "Comprobantes de tus departamentos.")
        page_historial_liquidaciones()
        return
    # Usa la misma portada y paleta que la pantalla Inicio.
    page_section_header(
        "Liquidaciones",
        "Consulta tus liquidaciones por huésped, llegada y departamento, o prepara el comprobante para cada propietario."
    )
    st.caption("La comisión se calcula sobre el total del arriendo, no sobre los abonos.")
    if "liq_view" not in st.session_state:
        st.session_state.liq_view = "Historial"
    view = st.segmented_control(
        "Vista de liquidaciones", ["Historial", "Preparar liquidación"],
        key="liq_view", label_visibility="collapsed"
    )
    if view == "Preparar liquidación":
        page_preparar_liquidacion()
    else:
        page_historial_liquidaciones()



# =========================================================
# PROPIETARIOS / CUENTAS AUTORIZADAS
# =========================================================

def admin_owners():
    if not is_admin():
        raise PermissionError("Sin permiso")
    conn = db()
    try:
        return [dict(r) for r in conn.execute("""
            SELECT o.*, p.user_id, p.is_active AS login_active,
                   p.login_email AS account_email, p.must_change_password AS invitation_pending
            FROM public.owners o LEFT JOIN public.user_profiles p ON p.owner_id=o.id
            ORDER BY o.full_name
        """).fetchall()]
    finally:
        conn.close()


def page_propietarios():
    if not is_admin():
        st.stop()
    page_section_header("Propietarios", "Registra propietarios y autoriza el acceso por RUT.")
    st.caption("Tener un RUT registrado no habilita el acceso. Debe existir una cuenta Auth activa.")

    with st.expander("＋ Registrar propietario", expanded=False):
        with st.form("form_nuevo_propietario", clear_on_submit=True):
            rut_input = st.text_input("RUT del propietario")
            nombre = st.text_input("Nombre completo")
            telefono = st.text_input("Teléfono (opcional)")
            email = st.text_input("Correo real para la cuenta y recuperación (opcional al registrar)")
            submit = st.form_submit_button("Guardar propietario", type="primary")
        if submit:
            try:
                rut = acceso.normalize_rut(rut_input)
                if not nombre.strip():
                    raise ValueError("Ingresa el nombre del propietario.")
                conn = db()
                try:
                    conn.execute("""
                        INSERT INTO public.owners (rut, full_name, phone, email)
                        VALUES (?, ?, ?, ?)
                    """, (rut, nombre.strip(), telefono.strip(), email.strip().lower()))
                    conn.commit()
                finally:
                    conn.close()
                st.success("Propietario registrado. Ahora puedes vincular sus departamentos.")
                st.rerun()
            except psycopg2.errors.UniqueViolation:
                st.error("Ese RUT ya está registrado.")
            except Exception as exc:
                st.error(f"No se pudo registrar al propietario: {exc}")

    owners = admin_owners()
    if not owners:
        st.info("Todavía no hay propietarios.")
        return
    depts = get_departments()
    for o in owners:
        with st.container(border=True):
            left, right = st.columns([2, 2])
            with left:
                st.markdown(f"**{html_escape(o['full_name'])}**")
                st.caption(f"RUT: {o['rut']} · {o['phone'] or 'Sin teléfono'}")
            with right:
                st.caption("Invitación pendiente" if o.get("user_id") and o.get("invitation_pending")
                           else "Acceso activo" if o.get("user_id") and o.get("login_active")
                           else "Sin acceso" if not o.get("user_id") else "Acceso deshabilitado")
                dep_count = sum(int(d['owner_id']==o['id']) for d in depts)
                st.caption(f"Departamentos asociados: {dep_count}")
            if not o.get("user_id"):
                with st.expander("Enviar invitación de acceso"):
                    st.info("El propietario recibirá un enlace para crear una contraseña personal. "
                            "No se utilizará su RUT como contraseña.")
                    with st.form(f"activar_{o['id']}"):
                        real_email = st.text_input("Correo del propietario", value=o['email'] or "",
                                                   key=f"mail_owner_{o['id']}")
                        verified = st.checkbox("Confirmo que el correo pertenece al propietario",
                                               key=f"checked_email_owner_{o['id']}")
                        activate = st.form_submit_button("Enviar invitación", type="primary")
                    if activate:
                        if not verified or '@' not in real_email:
                            st.error("Verifica el correo del propietario.")
                        else:
                            auth_uid = None
                            try:
                                auth_uid = acceso.invite_owner(real_email, o['full_name'])
                                conn = db()
                                try:
                                    conn.execute("""
                                        INSERT INTO public.user_profiles
                                        (user_id, rut, full_name, login_email, role, owner_id,
                                         is_active, must_change_password)
                                        VALUES (?::uuid, ?, ?, ?, 'owner', ?, true, true)
                                    """, (auth_uid, o['rut'], o['full_name'], real_email.strip().lower(), o['id']))
                                    conn.execute("UPDATE public.owners SET email=? WHERE id=?",
                                                 (real_email.strip().lower(), o['id']))
                                    conn.commit()
                                finally:
                                    conn.close()
                                st.success("Invitación solicitada. El propietario debe abrir el enlace "
                                           "del correo, crear una contraseña y luego ingresar con su RUT.")
                            except Exception:
                                if auth_uid:
                                    try:
                                        acceso.delete_auth_user(auth_uid)
                                    except Exception:
                                        pass
                                st.error("No se pudo enviar la invitación. Verifica el correo, "
                                         "la configuración SMTP y la URL pública de la app.")
            else:
                enabled = bool(o.get("login_active"))
                if st.button("Deshabilitar acceso" if enabled else "Habilitar acceso",
                             key=f"toggle_profile_{o['id']}"):
                    conn = db()
                    try:
                        conn.execute("UPDATE public.user_profiles SET is_active=? WHERE owner_id=?",
                                     (not enabled, o['id']))
                        conn.commit()
                    finally:
                        conn.close()
                    st.rerun()
                if enabled:
                    with st.expander("Enviar enlace para crear o recuperar contraseña"):
                        st.caption("Supabase enviará un enlace al correo registrado. "
                                   "No restablece la contraseña al RUT.")
                        if st.button("Enviar enlace", key=f"reset_owner_{o['id']}"):
                            try:
                                acceso.send_password_recovery(o['account_email'])
                                st.success("Solicitud enviada. El propietario debe revisar su correo.")
                            except Exception:
                                st.error("No se pudo enviar. Revisa SMTP y el correo registrado.")


def page_mi_cuenta():
    p = st.session_state['auth_profile']
    page_section_header("Mi cuenta", "Información personal y seguridad.")
    st.write(f"**Nombre:** {p['full_name']}")
    st.write(f"**RUT:** {p['rut']}")
    st.write(f"**Rol:** {'Administradora' if is_admin() else 'Propietario'}")
    with st.form("cambiar_clave"):
        pwd = st.text_input("Nueva contraseña (mínimo 12 caracteres)", type="password")
        confirm = st.text_input("Repite la contraseña", type="password")
        submit = st.form_submit_button("Cambiar mi contraseña", type="primary")
    if submit:
        if pwd != confirm:
            st.error("Las contraseñas no coinciden.")
        else:
            try:
                acceso.change_password(pwd)
                st.success("Contraseña cambiada. Inicia sesión nuevamente.")
            except Exception:
                st.error("No se pudo cambiar la contraseña. Vuelve a iniciar sesión e inténtalo.")


# =========================================================
# ROUTER
# =========================================================

if st.session_state.page == "Inicio":
    page_inicio()

elif st.session_state.page == "Reservas":
    page_reservas()

elif st.session_state.page == "Calendario":
    page_calendario()

elif st.session_state.page == "Departamentos":
    page_departamentos()

elif st.session_state.page == "Liquidaciones":
    page_liquidaciones()

elif st.session_state.page == "Detalle":
    page_detalle()

elif st.session_state.page == "Propietarios" and is_admin():
    page_propietarios()

elif st.session_state.page == "Mi cuenta":
    page_mi_cuenta()

else:
    st.session_state.page = "Inicio"
    st.rerun()

st.markdown(
    '<div class="footer-note">Arriendos · Panel de gestión</div>',
    unsafe_allow_html=True
)
