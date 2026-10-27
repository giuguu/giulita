import streamlit as st
import altair as alt
import pandas as pd
import os
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2.pool import ThreadedConnectionPool
import base64
import unicodedata
import json
import csv
from io import BytesIO, StringIO
from collections import defaultdict
from html import escape as html_escape
from datetime import date, datetime, timedelta
from calendar import monthrange
from pathlib import Path
from zoneinfo import ZoneInfo
from contextlib import contextmanager

from logic import (
    calculate_owner_liquidation,
    format_clp,
    money,
    payment_status,
    season_price_for,
)

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

# Zona horaria oficial del negocio (Chile continental).
TZ_CL = ZoneInfo("America/Santiago")


def now_cl():
    """Fecha y hora actual en Chile, sin depender de la zona del servidor."""
    return datetime.now(TZ_CL)


def today_cl():
    return now_cl().date()


def esc(value):
    """Escapa texto dinámico antes de insertarlo en HTML."""
    return html_escape("" if value is None else str(value))


STATUS_NO_DEPOSIT = "Sin abono"
STATUS_PARTIAL = "Abono recibido"
STATUS_PAID = "Pagado completamente"
STATUS_CANCELLED = "Cancelada"
STATUSES = (STATUS_NO_DEPOSIT, STATUS_PARTIAL, STATUS_PAID, STATUS_CANCELLED)

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

    .availability-blocked {{
        color: {ORANGE};
        background: {ORANGE_BG};
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

    .calendar-day.blocked {{
        background: {ORANGE_BG};
        border-color: #F3D9A6;
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

    div.stButton > button[kind="primary"] {{
        background: {FUCHSIA};
        border-color: {FUCHSIA};
        color: white;
    }}

    div.stButton > button[kind="primary"]:hover {{
        background: {FUCHSIA_DARK};
        border-color: {FUCHSIA_DARK};
        color: white;
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

    .calendar-day.blocked {{
        background: {ORANGE_BG};
        border-color: #F3D9A6;
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
    .calendar-status.blocked {{ color: {ORANGE}; }}

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
        grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
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

    /* ---------- Ajustes visuales modernos ---------- */
    html, body, [class*="css"], .stApp {{
        font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
    }}

    .metric-card, .payment-card, .detail-box, .reservation-card {{
        transition: transform .16s ease, box-shadow .16s ease;
    }}

    .metric-card:hover, .payment-card:hover, .reservation-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 26px rgba(217,70,141,0.10);
    }}

    .payment-card {{
        background: linear-gradient(180deg, {WHITE} 0%, {PINK_SOFT} 100%);
    }}

    .section-title {{
        border-left: 4px solid {FUCHSIA};
        padding-left: 10px;
        line-height: 1.25;
    }}

    div[data-testid="stButton"] > button {{
        border-radius: 11px;
        font-weight: 650;
        transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
    }}

    div[data-testid="stButton"] > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(217,70,141,.16);
    }}

    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stDateInput"] input,
    textarea {{
        border-radius: 10px !important;
    }}

    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus,
    div[data-testid="stDateInput"] input:focus,
    textarea:focus {{
        border-color: {FUCHSIA} !important;
        box-shadow: 0 0 0 3px rgba(217,70,141,.14) !important;
    }}

    [data-testid="stSidebar"] .stRadio label {{
        border-radius: 10px;
        padding: 4px 8px;
        transition: background .12s ease;
    }}

    [data-testid="stSidebar"] .stRadio label:hover {{
        background: {PINK_LIGHT};
    }}

    .payment-row.voided {{
        opacity: .6;
        text-decoration: line-through;
    }}

    .status-pill {{
        display: inline-block;
        border-radius: 999px;
        padding: 4px 10px;
        font-size: .76rem;
        font-weight: 800;
        background: {PINK_LIGHT};
        color: {FUCHSIA_DARK};
        border: 1px solid {PINK_BORDER};
    }}

    .status-pill.ok {{
        background: {GREEN_BG};
        color: {GREEN};
        border-color: #BDE8D5;
    }}

    .status-pill.warn {{
        background: {ORANGE_BG};
        color: {ORANGE};
        border-color: #F3D9A6;
    }}

    .status-pill.danger {{
        background: {RED_BG};
        color: {RED};
        border-color: #F3C4CD;
    }}

    .owner-card {{
        background: {WHITE};
        border: 1px solid {PINK_BORDER};
        border-radius: 16px;
        padding: 16px 18px;
        margin-bottom: 10px;
    }}

    .report-table-wrap {{
        overflow-x: auto;
        border: 1px solid {PINK_BORDER};
        border-radius: 14px;
        margin: 6px 0 14px;
        background: {WHITE};
    }}

    .report-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: .9rem;
    }}

    .report-table thead th {{
        background: linear-gradient(135deg, {FUCHSIA} 0%, {FUCHSIA_DARK} 100%);
        color: {WHITE};
        font-weight: 700;
        text-align: left;
        padding: 10px 14px;
        white-space: nowrap;
    }}

    .report-table tbody td {{
        padding: 9px 14px;
        border-top: 1px solid {PINK_BORDER};
        color: {TEXT};
        white-space: nowrap;
    }}

    .report-table tbody tr:nth-child(even) {{
        background: {PINK_SOFT};
    }}

    .report-table tbody tr:hover {{
        background: {PINK_LIGHT};
    }}

    .report-table tbody tr:last-child td {{
        border-bottom: none;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

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
        maxconn=10,
        dsn=_database_url(),
        sslmode="require",
        connect_timeout=10,
        application_name="arriendos-app",
        # El pooler puede heredar una sesión de solo lectura si otra herramienta
        # hizo SET default_transaction_read_only. La app necesita escritura.
        options="-c default_transaction_read_only=off -c statement_timeout=30000",
    )


class PgConnection:
    def __init__(self):
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

    def cursor(self):
        return PgCursor(self._conn.cursor(cursor_factory=DictCursor))

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            try:
                self.rollback()
            except Exception:
                pass
        self.close()
        return False

    def __del__(self):
        # Red de seguridad para no agotar el pool si una función falla antes
        # de llamar a close().
        try:
            self.close()
        except Exception:
            pass


def db():
    try:
        return PgConnection()
    except Exception:
        st.error(
            "No fue posible conectar con Supabase. Revisa DATABASE_URL en "
            "Streamlit Secrets y confirma que estás usando la URI del Transaction pooler."
        )
        st.stop()


@contextmanager
def db_connection():
    """Conexión con cierre garantizado incluso si hay una excepción."""
    conn = db()
    try:
        yield conn
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


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
    try:
        cur = conn.cursor()
        return _existing_columns(cur, table)
    finally:
        conn.close()


@st.cache_resource
def init_db():
    """Verifica que la base tenga la migración aplicada.

    La app ya no crea tablas ni siembra datos al arrancar: el esquema se
    administra con los archivos de migrations/.
    """
    conn = db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                to_regclass('public.departments') IS NOT NULL AS departments,
                to_regclass('public.reservations') IS NOT NULL AS reservations,
                to_regclass('public.payments') IS NOT NULL AS payments,
                to_regclass('public.owner_liquidations') IS NOT NULL AS liquidations,
                to_regclass('public.seasons') IS NOT NULL AS seasons,
                to_regclass('public.department_blocks') IS NOT NULL AS blocks,
                EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='payments'
                      AND column_name='voided_at'
                ) AS payments_migrated,
                EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='reservations'
                      AND column_name='deposit_due'
                ) AS reservations_migrated
        """)
        row = cur.fetchone()
        missing = [
            name for name in
            ("departments", "reservations", "payments", "liquidations", "seasons", "blocks")
            if not row[name]
        ]
        if missing:
            st.error(
                "Falta aplicar la migración de la base. Tablas ausentes: "
                + ", ".join(missing)
                + ". Ejecuta migrations/001_improvements.sql."
            )
            st.stop()
        if not row["payments_migrated"] or not row["reservations_migrated"]:
            st.error(
                "La base no tiene la migración 001 aplicada. "
                "Ejecuta migrations/001_improvements.sql antes de usar la app."
            )
            st.stop()
    finally:
        conn.close()


init_db()

# =========================================================
# FUNCIONES
# =========================================================

def department_columns():
    return table_columns("departments")


def insert_department(
    condo, name, capacity, winter, summer,
    owner_id=None, address="", access_instructions="",
    wifi_name="", wifi_password="", notes="",
    default_check_in_time="15:00", default_check_out_time="11:00",
):
    """Inserta un departamento con los datos operativos opcionales."""
    conn = db()
    try:
        cur = conn.cursor()
        rid = cur.execute("""
            INSERT INTO departments
                (condo, name, capacity, winter_price, summer_price, owner_id,
                 address, access_instructions, wifi_name, wifi_password, notes,
                 default_check_in_time, default_check_out_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """, (
            condo.strip(), name.strip(), int(capacity), int(winter), int(summer),
            owner_id, address.strip(), access_instructions.strip(),
            wifi_name.strip(), wifi_password.strip(), notes.strip(),
            default_check_in_time, default_check_out_time,
        )).fetchone()["id"]
        conn.commit()
        return rid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_department(department_id, **fields):
    """Actualiza solo columnas permitidas de un departamento."""
    allowed = {
        "condo", "name", "capacity", "winter_price", "summer_price",
        "owner_id", "address", "access_instructions", "wifi_name",
        "wifi_password", "notes", "default_check_in_time",
        "default_check_out_time", "active", "archived_at",
    }
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        return
    assignments = ", ".join(f"{key}=?" for key in clean)
    conn = db()
    try:
        conn.execute(
            f"UPDATE departments SET {assignments} WHERE id=?",
            (*clean.values(), int(department_id)),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def archive_department(department_id):
    """Oculta un departamento sin borrar su historial."""
    conn = db()
    try:
        conn.execute(
            "UPDATE departments SET active=0, archived_at=NOW() WHERE id=?",
            (int(department_id),),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_department_safe(department_id):
    """Elimina un departamento solo si no tiene reservas ni liquidaciones."""
    conn = db()
    try:
        cur = conn.cursor()
        row = cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM reservations WHERE department_id=?) AS reservations,
                (SELECT COUNT(*) FROM owner_liquidations ol
                   JOIN reservations r ON r.id=ol.reservation_id
                  WHERE r.department_id=?) AS liquidations,
                condo
            FROM departments WHERE id=?
        """, (department_id, department_id, department_id)).fetchone()
        if not row:
            raise ValueError("El departamento ya no existe.")
        if row["reservations"] or row["liquidations"]:
            raise ValueError(
                "El departamento tiene reservas o liquidaciones asociadas. "
                "Archívalo en lugar de eliminarlo."
            )
        cur.execute("DELETE FROM departments WHERE id=?", (department_id,))
        conn.commit()
        return row["condo"]
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_departments(include_inactive=False):
    conn = db()
    try:
        where = (
            "" if include_inactive
            else "WHERE COALESCE(d.active, 1)=1 AND d.archived_at IS NULL"
        )
        return conn.execute(f"""
            SELECT d.*, o.full_name AS owner_display_name
            FROM departments d
            LEFT JOIN owners o ON o.id=d.owner_id
            {where}
            ORDER BY d.condo, d.name
        """).fetchall()
    finally:
        conn.close()


def get_department(department_id):
    conn = db()
    try:
        return conn.execute("""
            SELECT d.*, o.full_name AS owner_display_name
            FROM departments d
            LEFT JOIN owners o ON o.id=d.owner_id
            WHERE d.id=?
        """, (department_id,)).fetchone()
    finally:
        conn.close()


def get_owners(active_only=False):
    conn = db()
    try:
        where = "WHERE active=TRUE" if active_only else ""
        return conn.execute(f"""
            SELECT * FROM owners {where} ORDER BY active DESC, full_name
        """).fetchall()
    finally:
        conn.close()


def save_owner(full_name, rut="", phone="", email="", bank_name="",
               bank_account="", bank_holder="", commission_percent=10,
               notes="", active=True, owner_id=None):
    conn = db()
    try:
        cur = conn.cursor()
        if owner_id:
            cur.execute("""
                UPDATE owners
                SET full_name=?, rut=?, phone=?, email=?, bank_name=?,
                    bank_account=?, bank_holder=?, commission_percent=?,
                    notes=?, active=?
                WHERE id=?
            """, (
                full_name.strip(), rut.strip(), phone.strip(), email.strip(),
                bank_name.strip(), bank_account.strip(), bank_holder.strip(),
                int(commission_percent), notes.strip(), bool(active), int(owner_id),
            ))
            new_id = int(owner_id)
        else:
            new_id = cur.execute("""
                INSERT INTO owners
                    (full_name, rut, phone, email, bank_name, bank_account,
                     bank_holder, commission_percent, notes, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            """, (
                full_name.strip(), rut.strip(), phone.strip(), email.strip(),
                bank_name.strip(), bank_account.strip(), bank_holder.strip(),
                int(commission_percent), notes.strip(), bool(active),
            )).fetchone()["id"]
        conn.commit()
        return new_id
    except psycopg2.errors.UniqueViolation as exc:
        conn.rollback()
        raise ValueError(
            "Ya existe un propietario con ese RUT. Revisa los datos."
        ) from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_seasons(department_id=None, condo=None, active_only=True):
    conn = db()
    try:
        filters = []
        params = []
        if active_only:
            filters.append("active=TRUE")
        if department_id is not None:
            filters.append("(department_id=? OR department_id IS NULL)")
            params.append(int(department_id))
        if condo:
            filters.append("(condo=? OR condo IS NULL OR condo='')")
            params.append(condo)
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        return conn.execute(f"""
            SELECT * FROM seasons {where}
            ORDER BY start_date, priority DESC, id
        """, params).fetchall()
    finally:
        conn.close()


def add_season(name, start_date, end_date, price_per_night,
               department_id=None, condo=None, min_nights=1, priority=0):
    conn = db()
    try:
        rid = conn.execute("""
            INSERT INTO seasons
                (name, start_date, end_date, price_per_night, min_nights,
                 department_id, condo, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """, (
            name.strip(), start_date, end_date, int(price_per_night),
            int(min_nights), department_id,
            condo.strip() if condo else None, int(priority),
        )).fetchone()["id"]
        conn.commit()
        return rid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_season(season_id):
    conn = db()
    try:
        conn.execute("DELETE FROM seasons WHERE id=?", (int(season_id),))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_blocks(department_id=None):
    conn = db()
    try:
        where = "WHERE b.department_id=?" if department_id is not None else ""
        params = (int(department_id),) if department_id is not None else ()
        return conn.execute(f"""
            SELECT b.*, d.condo, d.name AS dept_name
            FROM department_blocks b
            JOIN departments d ON d.id=b.department_id
            {where}
            ORDER BY b.start_date
        """, params).fetchall()
    finally:
        conn.close()


def add_block(department_id, start_date, end_date, reason="Mantención"):
    conn = db()
    try:
        rid = conn.execute("""
            INSERT INTO department_blocks (department_id, start_date, end_date, reason)
            VALUES (?, ?, ?, ?)
            RETURNING id
        """, (int(department_id), start_date, end_date, reason.strip())).fetchone()["id"]
        conn.commit()
        return rid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_block(block_id):
    conn = db()
    try:
        conn.execute("DELETE FROM department_blocks WHERE id=?", (int(block_id),))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


RESERVATION_SELECT = """
    SELECT r.*, d.name AS dept_name, d.condo, d.capacity, d.owner_id,
           o.full_name AS owner_display_name,
           COALESCE(pay.paid, 0) AS paid
    FROM reservations r
    JOIN departments d ON d.id=r.department_id
    LEFT JOIN owners o ON o.id=d.owner_id
    LEFT JOIN (
        SELECT reservation_id, SUM(amount) AS paid
        FROM payments
        WHERE voided_at IS NULL
        GROUP BY reservation_id
    ) pay ON pay.reservation_id=r.id
"""


def get_reservations(include_cancelled=False):
    conn = db()
    try:
        where = "" if include_cancelled else "WHERE r.status <> 'Cancelada'"
        return conn.execute(f"""
            {RESERVATION_SELECT}
            {where}
            ORDER BY r.check_in
        """).fetchall()
    finally:
        conn.close()


def get_reservation(reservation_id):
    conn = db()
    try:
        return conn.execute(
            f"{RESERVATION_SELECT} WHERE r.id=?",
            (int(reservation_id),),
        ).fetchone()
    finally:
        conn.close()


def conflict_exists(department_id, check_in, check_out, ignore_id=None):
    """Choque con otra reserva vigente, usando las columnas DATE."""
    conn = db()
    try:
        query = """
            SELECT id, guest, check_in, check_out
            FROM reservations
            WHERE department_id=?
              AND status <> 'Cancelada'
              AND COALESCE(check_in_date, check_in::date) < ?::date
              AND COALESCE(check_out_date, check_out::date) > ?::date
        """
        params = [int(department_id), check_out, check_in]
        if ignore_id is not None:
            query += " AND id <> ?"
            params.append(int(ignore_id))
        return conn.execute(query, params).fetchone()
    finally:
        conn.close()


def block_conflict_exists(department_id, check_in, check_out):
    conn = db()
    try:
        return conn.execute("""
            SELECT id, start_date, end_date, reason
            FROM department_blocks
            WHERE department_id=?
              AND daterange(start_date, end_date, '[)')
                  && daterange(?::date, ?::date, '[)')
        """, (int(department_id), check_in, check_out)).fetchone()
    finally:
        conn.close()


def recompute_reservation(cur, reservation_id):
    """Deja deposited y status en función de los pagos vigentes."""
    row = cur.execute(
        "SELECT id, total, status FROM reservations WHERE id=? FOR UPDATE",
        (int(reservation_id),),
    ).fetchone()
    if not row:
        return None
    if row["status"] == STATUS_CANCELLED:
        return row["status"]
    paid = cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS paid
        FROM payments
        WHERE reservation_id=? AND voided_at IS NULL
    """, (int(reservation_id),)).fetchone()["paid"]
    status = payment_status(row["total"], paid)
    cur.execute("""
        UPDATE reservations SET deposited=?, status=? WHERE id=?
    """, (int(paid), status, int(reservation_id)))
    return status


def save_reservation(
    department_id, guest, phone, check_in, check_in_time,
    check_out, check_out_time, guests, price_night,
    deposit_percent, status=None, reservation_id=None, *,
    email="", document="", source="Directo", notes="",
    initial_payment=0, payment_method="Transferencia",
):
    """Crea o actualiza una reserva.

    ``deposited`` y ``status`` nunca se escriben a mano: se recalculan desde la
    tabla de pagos. El porcentaje de abono solo define el monto esperado
    (``deposit_due``).
    """
    nights = (check_out - check_in).days
    if nights <= 0:
        raise ValueError("El check-out debe ser posterior al check-in.")
    total = nights * int(price_night)
    deposit_due = min(total, round(total * (int(deposit_percent) / 100)))
    conn = db()
    try:
        cur = conn.cursor()
        if reservation_id:
            cur.execute("""
                UPDATE reservations
                SET department_id=?, guest=?, guest_name=?, phone=?, check_in=?,
                    check_in_time=?, check_out=?, check_out_time=?, guests=?,
                    price_night=?, nights=?, total=?, deposit_percent=?,
                    deposit_due=?, email=?, document=?, source=?, notes=?
                WHERE id=?
            """, (
                int(department_id), guest.strip(), guest.strip(), phone.strip(),
                check_in.isoformat(), check_in_time, check_out.isoformat(),
                check_out_time, int(guests), int(price_night), nights, total,
                int(deposit_percent), deposit_due, email.strip(), document.strip(),
                source.strip() or "Directo", notes.strip(), int(reservation_id),
            ))
            recompute_reservation(cur, reservation_id)
            rid = int(reservation_id)
        else:
            rid = cur.execute("""
                INSERT INTO reservations
                    (department_id, guest, guest_name, phone, check_in,
                     check_in_time, check_out, check_out_time, guests,
                     price_night, nights, total, deposit_percent, deposit_due,
                     deposited, status, email, document, source, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'Sin abono',
                        ?, ?, ?, ?)
                RETURNING id
            """, (
                int(department_id), guest.strip(), guest.strip(), phone.strip(),
                check_in.isoformat(), check_in_time, check_out.isoformat(),
                check_out_time, int(guests), int(price_night), nights, total,
                int(deposit_percent), deposit_due, email.strip(), document.strip(),
                source.strip() or "Directo", notes.strip(),
            )).fetchone()["id"]
            cur.execute("""
                INSERT INTO checklist (reservation_id, cleaning, internet, inspected, keys)
                VALUES (?, 0, 0, 0, 0)
                ON CONFLICT (reservation_id) DO NOTHING
            """, (int(rid),))
            if int(initial_payment or 0) > 0:
                amount = min(int(initial_payment), total)
                cur.execute("""
                    INSERT INTO payments
                        (reservation_id, amount, payment_date, note, method)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    int(rid), amount, today_cl(), "Pago inicial de la reserva",
                    payment_method.strip() or "Transferencia",
                ))
            recompute_reservation(cur, rid)
        conn.commit()
        return int(rid)
    except psycopg2.errors.ExclusionViolation as exc:
        conn.rollback()
        raise ValueError(
            "Las fechas se cruzan con otra reserva vigente de este departamento."
        ) from exc
    except psycopg2.errors.IntegrityError as exc:
        conn.rollback()
        raise ValueError(f"No se pudo guardar la reserva: {exc}") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_reservation(reservation_id):
    """Elimina una reserva solo si no tiene pagos ni liquidaciones."""
    conn = db()
    try:
        cur = conn.cursor()
        row = cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM payments WHERE reservation_id=?) AS payments,
                (SELECT COUNT(*) FROM owner_liquidations WHERE reservation_id=?) AS liquidations
        """, (reservation_id, reservation_id)).fetchone()
        if row["payments"] or row["liquidations"]:
            raise ValueError(
                "La reserva tiene pagos o liquidaciones. Cancélala para conservar "
                "el historial en lugar de eliminarla."
            )
        cur.execute("DELETE FROM checklist WHERE reservation_id=?", (reservation_id,))
        cur.execute("DELETE FROM reservations WHERE id=?", (reservation_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cancel_reservation(reservation_id, reason=""):
    conn = db()
    try:
        conn.execute("""
            UPDATE reservations
            SET status='Cancelada', cancelled_at=NOW(), cancelled_reason=?
            WHERE id=?
        """, (reason.strip(), int(reservation_id)))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reactivate_reservation(reservation_id):
    conn = db()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE reservations
            SET status='Sin abono', cancelled_at=NULL, cancelled_reason=''
            WHERE id=?
        """, (int(reservation_id),))
        recompute_reservation(cur, reservation_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_checklist(reservation_id, cleaning, internet, inspected, keys):
    """Guarda el checklist de preparación de una reserva."""
    conn = db()
    try:
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
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_checklist(reservation_id):
    conn = db()
    try:
        return conn.execute("""
            SELECT * FROM checklist WHERE reservation_id=?
        """, (reservation_id,)).fetchone()
    finally:
        conn.close()


def set_page(page, reservation_id=None):
    st.session_state.page = page
    if page in ("Inicio", "Reservas", "Calendario", "Departamentos",
                "Propietarios", "Reportes", "Liquidaciones"):
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


def add_payment(reservation_id, amount, note="", payment_date=None,
                method="Transferencia", reference=""):
    """Registra un pago real, sin permitir sobrepagos."""
    amount = int(amount)
    if amount <= 0:
        raise ValueError("El monto del pago debe ser mayor que 0.")
    conn = db()
    try:
        cur = conn.cursor()
        row = cur.execute("""
            SELECT id, total, status, deposited
            FROM reservations WHERE id=? FOR UPDATE
        """, (int(reservation_id),)).fetchone()
        if not row:
            raise ValueError("La reserva no existe.")
        if row["status"] == STATUS_CANCELLED:
            raise ValueError("No se pueden registrar pagos en una reserva cancelada.")
        paid = cur.execute("""
            SELECT COALESCE(SUM(amount), 0) AS paid
            FROM payments WHERE reservation_id=? AND voided_at IS NULL
        """, (int(reservation_id),)).fetchone()["paid"]
        if int(paid) + amount > int(row["total"]):
            raise ValueError(
                f"El pago supera el saldo pendiente ({money(max(int(row['total']) - int(paid), 0))})."
            )
        cur.execute("""
            INSERT INTO payments
                (reservation_id, amount, payment_date, note, method, reference)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            int(reservation_id), amount, payment_date or today_cl(),
            note.strip(), method.strip() or "Transferencia", reference.strip(),
        ))
        status = recompute_reservation(cur, reservation_id)
        conn.commit()
        return {
            "amount": amount,
            "status": status,
            "paid": int(paid) + amount,
            "balance": max(int(row["total"]) - int(paid) - amount, 0),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def void_payment(payment_id, reason=""):
    """Anula un pago sin borrarlo y recalcula la reserva."""
    conn = db()
    try:
        cur = conn.cursor()
        payment = cur.execute("""
            SELECT id, reservation_id, voided_at
            FROM payments WHERE id=? FOR UPDATE
        """, (int(payment_id),)).fetchone()
        if not payment:
            raise ValueError("El pago no existe.")
        if payment["voided_at"]:
            return
        cur.execute("""
            UPDATE payments
            SET voided_at=NOW(), void_reason=?
            WHERE id=?
        """, (reason.strip(), int(payment_id)))
        recompute_reservation(cur, payment["reservation_id"])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_payments(reservation_id):
    conn = db()
    try:
        return conn.execute("""
            SELECT * FROM payments
            WHERE reservation_id=?
            ORDER BY payment_date DESC, id DESC
        """, (int(reservation_id),)).fetchall()
    finally:
        conn.close()


def get_checklists_map():
    """Carga todos los checklists en una sola consulta."""
    conn = db()
    try:
        rows = conn.execute("SELECT * FROM checklist").fetchall()
        return {int(row["reservation_id"]): row for row in rows}
    finally:
        conn.close()


def reminders_for(reservations, checklists=None):
    today = today_cl()
    reminders = []
    checklists = checklists if checklists is not None else get_checklists_map()

    for r in reservations:
        if r["status"] == STATUS_CANCELLED:
            continue
        ci = date.fromisoformat(str(r["check_in"])[:10])
        co = date.fromisoformat(str(r["check_out"])[:10])
        days_to_in = (ci - today).days
        days_to_out = (co - today).days
        checklist = checklists.get(int(r["id"]))

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
                    "urgent", "Aseo pendiente",
                    f"{r['dept_name']} recibe a {r['guest']} mañana.", r["id"]
                ))
            if not checklist or not checklist["internet"]:
                reminders.append((
                    "important", "Verificar internet",
                    f"Revisar internet antes del check-in de {r['guest']}.", r["id"]
                ))
        if days_to_out == 1:
            reminders.append((
                "important", "Check-out mañana",
                f"Enviar instrucciones de salida a {r['guest']}.", r["id"]
            ))
        if days_to_in == 0:
            reminders.append((
                "today", "Check-in hoy",
                f"{r['guest']} llega hoy a {r['dept_name']}.", r["id"]
            ))
        if days_to_out == 0:
            reminders.append((
                "today", "Check-out hoy",
                f"{r['guest']} debe salir hoy de {r['dept_name']}.", r["id"]
            ))
    return reminders


# =========================================================
# ESTADO DE NAVEGACIÓN
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "Inicio"

if "selected_reservation" not in st.session_state:
    st.session_state.selected_reservation = None

pages = [
    "Inicio",
    "Reservas",
    "Calendario",
    "Departamentos",
    "Propietarios",
    "Reportes",
    "Liquidaciones",
]

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

    st.caption("Panel de administración")
    st.caption(today_cl().strftime("%d/%m/%Y"))

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


def _make_thumbnail(image_bytes, size=(800, 800), quality=72):
    """Genera una miniatura JPEG liviana para no enviar la foto completa."""
    try:
        from PIL import Image
    except Exception:
        return None

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            image.thumbnail(size, Image.LANCZOS)
            buffer = BytesIO()
            image.save(
                buffer, format="JPEG", quality=quality, optimize=True,
                progressive=True,
            )
            return buffer.getvalue()
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def _get_condo_image_cached(condo_key, thumb=True):
    """Trae una foto de Supabase y la mantiene en caché para evitar descargas repetidas.

    Por defecto usa la miniatura; si aún no existe, cae a la imagen original.
    """
    if not condo_key:
        return None

    conn = db()
    try:
        if thumb:
            row = conn.execute(
                """
                SELECT thumb_data, thumb_mime, image_data, image_mime
                FROM condo_images WHERE condo_key=?
                """,
                (condo_key,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT image_data, image_mime FROM condo_images WHERE condo_key=?",
                (condo_key,),
            ).fetchone()

        if not row:
            return None

        if thumb and row.get("thumb_data"):
            return bytes(row["thumb_data"]), (row["thumb_mime"] or "image/jpeg")
        if row.get("image_data"):
            return bytes(row["image_data"]), (row["image_mime"] or "image/jpeg")
        return None
    finally:
        conn.close()


def _get_condo_image_row(condo, thumb=True):
    """Devuelve los bytes/mime cacheados del edificio."""
    return _get_condo_image_cached(_slug_archivo(condo), thumb)


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

    thumb_bytes = _make_thumbnail(image_bytes)
    thumb_mime = "image/jpeg" if thumb_bytes else None

    conn = db()
    try:
        conn.execute(
            """
            INSERT INTO condo_images
                (condo_key, condo_name, image_data, image_mime,
                 thumb_data, thumb_mime, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, NOW())
            ON CONFLICT(condo_key) DO UPDATE SET
                condo_name=EXCLUDED.condo_name,
                image_data=EXCLUDED.image_data,
                image_mime=EXCLUDED.image_mime,
                thumb_data=EXCLUDED.thumb_data,
                thumb_mime=EXCLUDED.thumb_mime,
                updated_at=NOW()
            """,
            (
                condo_key, condo_name, psycopg2.Binary(image_bytes), mime,
                psycopg2.Binary(thumb_bytes) if thumb_bytes else None,
                thumb_mime,
            ),
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
    today = today_cl()
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
    pending = sum(max(r["total"] - r["paid"], 0) for r in month_res)

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
                        <div class="reservation-name">{esc(r['guest'])}</div>
                        <div class="reservation-info">
                            🏢 {esc(r['dept_name'])} · {esc(r['condo'])}<br>
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

    reminders = reminders_for(reservations, get_checklists_map())

    if not reminders:
        st.success("Todo al día. No tienes recordatorios pendientes para hoy.")

    for kind, title, text_value, rid in reminders[:8]:
        st.markdown(
            f"""
            <div class="reminder">
                <div class="reminder-title">{esc(title)}</div>
                <div class="reminder-text">{esc(text_value)}</div>
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
                value=today_cl(),
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
                key=f"new_guests_{selected_dept['id']}"
            )
            check_out = st.date_input(
                "Salida",
                value=today_cl() + timedelta(days=1),
                key="new_checkout"
            )
            check_out_time = st.time_input(
                "Hora de check-out",
                value=datetime.strptime("11:00", "%H:%M").time(),
                key="new_checkout_time"
            )

        season_price = season_price_for(
            get_seasons(selected_dept["id"], selected_dept["condo"]),
            check_in,
            selected_dept["id"],
            selected_dept["condo"],
        )
        suggested_prices = {"Verano": int(selected_dept["summer_price"])}
        if int(selected_dept["winter_price"]) != int(selected_dept["summer_price"]):
            suggested_prices["Invierno"] = int(selected_dept["winter_price"])
        if season_price is not None:
            suggested_prices["Temporada"] = int(season_price)

        price_source = st.radio(
            "Precio sugerido",
            list(suggested_prices.keys()),
            horizontal=True,
            key=f"new_price_source_{selected_dept['id']}",
            help=(
                "Elige una referencia y luego ajusta el valor si hace falta. "
                "«Temporada» aparece solo si hay una temporada configurada."
            ),
        )

        price = st.number_input(
            "Precio por noche",
            min_value=0,
            value=int(suggested_prices[price_source]),
            step=5000,
            key=f"new_price_{selected_dept['id']}_{price_source}"
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

        initial_payment = st.number_input(
            "Pago inicial realmente recibido (opcional)",
            min_value=0,
            max_value=max(int(total), 0),
            value=min(int(deposit), int(total)) if valid_dates else 0,
            step=5000,
            key=(
                "new_initial_payment_"
                f"{selected_dept['id']}_{check_in}_{check_out}_"
                f"{int(price)}_{int(deposit_percent)}"
            ),
            help=(
                "Se guardará como un pago en el historial. Si todavía no has "
                "recibido dinero, déjalo en 0."
            ),
        )

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
                    <div class="payment-card-label">ABONO ESPERADO</div>
                    <div class="payment-card-value">{money(deposit)}</div>
                </div>
                <div class="payment-card">
                    <div class="payment-card-label">PAGO INICIAL</div>
                    <div class="payment-card-value">{money(initial_payment)}</div>
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
            int(initial_payment),
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
                    "initial_payment": int(initial_payment),
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
                    <div class="detail-value">{esc(reviewed["guest"])}</div><br>
                    <div class="detail-label">CONTACTO</div>
                    <div class="detail-value">{esc(reviewed["phone"] or "No registrado")}</div><br>
                    <div class="detail-label">DEPARTAMENTO</div>
                    <div class="detail-value">🏢 {esc(reviewed["condo"])} · {esc(reviewed["dept_name"])}</div><br>
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
                        <div class="payment-card-label">ABONO ESPERADO</div>
                        <div class="payment-card-value">{money(reviewed["deposit"])}</div>
                    </div>
                    <div class="payment-card">
                        <div class="payment-card-label">PAGO INICIAL</div>
                        <div class="payment-card-value">{money(reviewed["initial_payment"])}</div>
                    </div>
                    <div class="payment-card">
                        <div class="payment-card-label">SALDO INICIAL</div>
                        <div class="payment-card-value">{money(reviewed["balance"] - reviewed["initial_payment"])}</div>
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
                    # Última comprobación, justo antes de escribir en SQLite.
                    conflict = conflict_exists(
                        reviewed["department_id"],
                        reviewed["check_in"],
                        reviewed["check_out"]
                    )
                    block = block_conflict_exists(
                        reviewed["department_id"],
                        reviewed["check_in"],
                        reviewed["check_out"]
                    )

                    if block:
                        st.error(
                            "❌ No se puede guardar. El departamento está bloqueado por "
                            f"mantención: {block['reason']} "
                            f"({block['start_date']:%d/%m/%Y} al {block['end_date']:%d/%m/%Y})."
                        )
                    elif conflict:
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
                                None,
                                initial_payment=reviewed["initial_payment"],
                            )
                        except ValueError as exc:
                            st.error(f"No se pudo guardar la reserva: {exc}")
                        except Exception as exc:
                            st.error(f"Error inesperado al guardar la reserva: {exc}")
                        else:
                            st.session_state.reservation_review = None
                            st.session_state.selected_reservation = rid
                            st.session_state.page = "Detalle"
                            st.success("Reserva guardada correctamente.")
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

        if not reservations:
            st.info("Todavía no hay reservas registradas.")

        for r in reservations:
            ci = date.fromisoformat(str(r["check_in"])[:10])
            co = date.fromisoformat(str(r["check_out"])[:10])
            paid = int(r["paid"] or 0)
            balance = max(int(r["total"]) - paid, 0)
            pill = (
                "ok" if r["status"] == STATUS_PAID
                else "warn" if paid > 0
                else ""
            )

            col1, col2 = st.columns([5, 1])

            with col1:
                st.markdown(
                    f"""
                    <div class="detail-box compact">
                        <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center">
                            <b>{esc(r['guest'])}</b>
                            <span class="status-pill {pill}">{esc(r['status'])}</span>
                        </div>
                        <span style="color:{MUTED}">
                        {esc(r['condo'])} · {esc(r['dept_name'])} ·
                        {ci.strftime('%d/%m/%Y')} → {co.strftime('%d/%m/%Y')}
                        </span><br>
                        <span style="color:{MUTED};font-size:.85rem">
                        Total {money(r['total'])} · Pagado {money(paid)} ·
                        Saldo {money(balance)}
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

    payments = get_payments(rid)
    paid = sum(int(p["amount"]) for p in payments if not p["voided_at"])
    balance = max(int(r["total"]) - paid, 0)
    deposit_due = int(r["deposit_due"] or 0)
    cancelled = r["status"] == STATUS_CANCELLED

    status_css = (
        "ok" if r["status"] == STATUS_PAID
        else "danger" if cancelled
        else "warn"
    )
    st.markdown(
        f"""<div class="reservation-heading">
            <span class="reservation-heading-guest">{esc(r['guest'])}</span>
            <span class="reservation-heading-place">🏢 {esc(r['condo'])} · {esc(r['dept_name'])}</span>
            <span class="status-pill {status_css}">{esc(r['status'])}</span>
        </div>""",
        unsafe_allow_html=True
    )

    ci = date.fromisoformat(str(r["check_in"])[:10])
    co = date.fromisoformat(str(r["check_out"])[:10])

    if cancelled:
        st.warning(
            "Esta reserva está cancelada y sus fechas quedaron liberadas. "
            f"Motivo: {r['cancelled_reason'] or 'sin detalle'}"
        )

    st.markdown('<div class="section-title">Información</div>', unsafe_allow_html=True)

    info1, info2 = st.columns(2)

    with info1:
        st.markdown(
            f"""
            <div class="detail-box compact">
                <div class="detail-label">HUÉSPED</div>
                <div class="detail-value">{esc(r['guest'])}</div><br>
                <div class="detail-label">CONTACTO</div>
                <div class="detail-value">{esc(r['phone'] or 'No registrado')}</div><br>
                <div class="detail-label">DEPARTAMENTO</div>
                <div class="detail-value">{esc(r['condo'])} · {esc(r['dept_name'])}</div><br>
                <div class="detail-label">PROPIETARIO</div>
                <div class="detail-value">{esc(r['owner_display_name'] or 'Sin asignar')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with info2:
        st.markdown(
            f"""
            <div class="detail-box">
                <div class="detail-label">CHECK-IN</div>
                <div class="detail-value">{ci.strftime('%d/%m/%Y')} · {esc(r['check_in_time'])}</div><br>
                <div class="detail-label">CHECK-OUT</div>
                <div class="detail-value">{co.strftime('%d/%m/%Y')} · {esc(r['check_out_time'])}</div><br>
                <div class="detail-label">HUÉSPEDES / ORIGEN</div>
                <div class="detail-value">{r['guests']} huéspedes · {esc(r['source'] or 'Directo')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.button(
        "Crear o consultar liquidación del propietario",
        key=f"liquidation_shortcut_{rid}",
        on_click=set_page,
        args=("Liquidaciones", rid),
    )

    st.markdown('<div class="section-title payment-section">💳 Pagos</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="payment-summary">
            <div class="payment-card">
                <div class="payment-card-label">TOTAL RESERVA</div>
                <div class="payment-card-value">{money(r["total"])}</div>
            </div>
            <div class="payment-card">
                <div class="payment-card-label">PAGADO</div>
                <div class="payment-card-value">{money(paid)}</div>
            </div>
            <div class="payment-card">
                <div class="payment-card-label">ABONO ESPERADO</div>
                <div class="payment-card-value">{money(deposit_due)}</div>
            </div>
            <div class="payment-card">
                <div class="payment-card-label">SALDO</div>
                <div class="payment-card-value">{money(balance)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption(
        f"El abono esperado se calculó con {float(r['deposit_percent']):.0f}% del total. "
        "El estado se actualiza solo con pagos registrados."
    )

    if not cancelled:
        with st.expander("＋ Registrar pago", expanded=False):
            pay1, pay2, pay3 = st.columns([1, 1, 1])
            with pay1:
                amount = st.number_input(
                    "Monto del pago",
                    min_value=0,
                    max_value=max(balance, 0),
                    value=min(5000, max(balance, 0)),
                    step=5000,
                    key=f"pay_amount_{rid}_{paid}",
                )
            with pay2:
                payment_date = st.date_input(
                    "Fecha del pago",
                    value=today_cl(),
                    key=f"pay_date_{rid}",
                )
            with pay3:
                method = st.selectbox(
                    "Medio de pago",
                    ["Transferencia", "Efectivo", "Tarjeta", "Depósito", "Otro"],
                    key=f"pay_method_{rid}",
                )
            pay4, pay5 = st.columns(2)
            with pay4:
                reference = st.text_input(
                    "Referencia / comprobante (opcional)",
                    key=f"pay_ref_{rid}",
                )
            with pay5:
                note = st.text_input(
                    "Nota (opcional)",
                    key=f"pay_note_{rid}",
                )

            if st.button(
                "Registrar pago",
                type="primary",
                use_container_width=True,
                key=f"save_pay_{rid}",
                disabled=balance <= 0,
            ):
                try:
                    add_payment(
                        rid, amount, note, payment_date, method, reference
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Pago registrado y saldo actualizado.")
                    st.rerun()

    if payments:
        st.markdown(
            '<div class="payment-history-title">Historial de pagos</div>',
            unsafe_allow_html=True,
        )
        for p in payments:
            payment_day = p["payment_date"]
            if hasattr(payment_day, "strftime"):
                payment_day = payment_day.strftime("%d/%m/%Y")
            note_text = f' · {esc(p["note"])}' if p["note"] else ""
            ref_text = f' · Ref. {esc(p["reference"])}' if p["reference"] else ""
            voided = bool(p["voided_at"])
            void_label = " · ANULADO" if voided else ""
            st.markdown(
                f'<div class="payment-row{" voided" if voided else ""}">'
                f'<span>{payment_day} · {esc(p["method"] or "Transferencia")}</span>'
                f'<strong>{money(p["amount"])}</strong>'
                f'<span>{note_text}{ref_text}{void_label}</span></div>',
                unsafe_allow_html=True,
            )
            if not voided:
                with st.popover("Anular este pago", use_container_width=False):
                    st.caption(
                        "El pago no se borra: queda marcado como anulado para "
                        "mantener el historial."
                    )
                    void_reason = st.text_input(
                        "Motivo de la anulación",
                        key=f"void_reason_{p['id']}",
                    )
                    if st.button(
                        "Confirmar anulación",
                        key=f"void_btn_{p['id']}",
                        type="primary",
                    ):
                        try:
                            void_payment(p["id"], void_reason)
                        except ValueError as exc:
                            st.error(str(exc))
                        else:
                            st.success("Pago anulado y saldo recalculado.")
                            st.rerun()

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
        try:
            update_checklist(rid, cleaning, internet, inspected, keys)
        except Exception as exc:
            st.error(f"No se pudo guardar el checklist: {exc}")
        else:
            st.success("Checklist actualizado.")
            st.rerun()

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
            edit_email = st.text_input(
                "Email",
                value=r["email"] or "",
                key=f"edit_email_{rid}"
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
                key=f"edit_guests_{rid}_{ed['id']}"
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

        edit_source_options = ["Directo", "Booking", "Airbnb", "WhatsApp", "Otro"]
        current_source = r["source"] or "Directo"
        edit_source = st.selectbox(
            "Origen de la reserva",
            edit_source_options,
            index=(
                edit_source_options.index(current_source)
                if current_source in edit_source_options else 0
            ),
            key=f"edit_source_{rid}",
        )
        edit_notes = st.text_area(
            "Notas internas",
            value=r["notes"] or "",
            key=f"edit_notes_{rid}",
        )

        st.caption(
            "El porcentaje de abono solo define el monto esperado. "
            "El estado y lo pagado se calculan desde el historial de pagos."
        )

        if edit_checkout <= edit_checkin:
            st.error("El check-out debe ser posterior al check-in.")
        else:
            edit_conflict = conflict_exists(
                ed["id"], edit_checkin, edit_checkout, ignore_id=rid
            )
            edit_block = block_conflict_exists(
                ed["id"], edit_checkin, edit_checkout
            )

            if edit_block:
                st.error(
                    "Las fechas chocan con un bloqueo por mantención: "
                    f"{edit_block['reason']}."
                )
            elif edit_conflict:
                st.error("Las fechas chocan con otra reserva de este departamento.")

            if st.button(
                "Guardar cambios",
                type="primary",
                key=f"edit_save_{rid}",
                disabled=bool(edit_conflict or edit_block),
            ):
                try:
                    save_reservation(
                        ed["id"], edit_guest, edit_phone,
                        edit_checkin, r["check_in_time"],
                        edit_checkout, r["check_out_time"],
                        edit_guests, edit_price, edit_deposit,
                        None, rid,
                        email=edit_email,
                        source=edit_source,
                        notes=edit_notes,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"No se pudo actualizar la reserva: {exc}")
                else:
                    st.success("Reserva actualizada.")
                    st.rerun()


    # -----------------------------------------------------
    # CANCELAR / ELIMINAR
    # -----------------------------------------------------
    st.markdown('<div class="section-title">Cancelar o eliminar</div>', unsafe_allow_html=True)

    if cancelled:
        if st.button("Reactivar reserva", key=f"reactivate_{rid}"):
            try:
                reactivate_reservation(rid)
            except Exception as exc:
                st.error(f"No se pudo reactivar la reserva: {exc}")
            else:
                st.success("Reserva reactivada. Revisa que las fechas sigan disponibles.")
                st.rerun()
    else:
        with st.expander("Cancelar reserva (conserva el historial)"):
            st.caption(
                "Al cancelar, las fechas se liberan para nuevas reservas, pero se "
                "mantienen los pagos y las liquidaciones asociadas."
            )
            cancel_reason = st.text_input(
                "Motivo de la cancelación",
                key=f"cancel_reason_{rid}",
                placeholder="Ej.: el huésped no pudo viajar",
            )
            if st.button(
                "Confirmar cancelación",
                key=f"confirm_cancel_{rid}",
                type="primary",
            ):
                try:
                    cancel_reservation(rid, cancel_reason)
                except Exception as exc:
                    st.error(f"No se pudo cancelar la reserva: {exc}")
                else:
                    st.success("Reserva cancelada y fechas liberadas.")
                    st.rerun()

    with st.expander("Eliminar definitivamente"):
        st.caption(
            "Solo se permite eliminar reservas sin pagos ni liquidaciones. "
            "Si ya hay dinero registrado, usa la cancelación para no perder el historial."
        )
        if st.button(
            "🗑️ Eliminar definitivamente",
            key=f"delete_reservation_{rid}",
        ):
            st.session_state[f"confirm_delete_{rid}"] = True
            st.rerun()

        if st.session_state.get(f"confirm_delete_{rid}", False):
            st.warning(
                f"Vas a eliminar la reserva de {r['guest']} "
                f"({r['condo']} · {r['dept_name']}). Esta acción no se puede deshacer."
            )
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button(
                    "Sí, eliminar reserva",
                    key=f"confirm_delete_yes_{rid}",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        delete_reservation(rid)
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"No se pudo eliminar la reserva: {exc}")
                    else:
                        st.session_state.pop(f"confirm_delete_{rid}", None)
                        st.session_state.pop("selected_reservation", None)
                        st.session_state.page = "Reservas"
                        st.rerun()
            with dc2:
                if st.button(
                    "Cancelar",
                    key=f"confirm_delete_no_{rid}",
                    use_container_width=True,
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
    blocks = get_blocks()

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
            value=today_cl().year
        )

    with c2:
        month = st.selectbox(
            "Mes",
            list(range(1, 13)),
            index=today_cl().month - 1,
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
        &nbsp;&nbsp;
        <span class="availability-blocked">Mantención</span>
        """,
        unsafe_allow_html=True
    )

    days = monthrange(year, month)[1]

    for dept in selected_depts:
        st.markdown(
            f'<div class="section-title">{esc(dept["name"])}</div>',
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
                    blocked = False
                    guest_name = ""
                    block_reason = ""

                    for b in blocks:
                        if b["department_id"] != dept["id"]:
                            continue
                        if b["start_date"] <= current < b["end_date"]:
                            blocked = True
                            block_reason = b["reason"]
                            break

                    if not blocked:
                        for r in reservations:
                            if r["department_id"] != dept["id"]:
                                continue

                            ri = date.fromisoformat(str(r["check_in"])[:10])
                            ro = date.fromisoformat(str(r["check_out"])[:10])

                            if ri <= current < ro:
                                busy = True
                                guest_name = r["guest"]
                                break

                    cls = (
                        "calendar-day busy" if busy
                        else "calendar-day blocked" if blocked
                        else "calendar-day"
                    )
                    status_class = "busy" if busy else "blocked" if blocked else "free"
                    status_text = "Ocup." if busy else "Mant." if blocked else "Libre"
                    dot = "🔴" if busy else "🛠️" if blocked else "🟢"
                    title_text = (
                        guest_name if busy
                        else block_reason if blocked
                        else "Disponible"
                    )

                    st.markdown(
                        f"""
                        <div class="{cls}" title="{esc(title_text)}">
                            <div class="calendar-day-number">{day_num}</div>
                            <div class="calendar-status {status_class}">{dot} {status_text}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if busy:
                        st.caption(guest_name)
                    elif blocked:
                        st.caption(f"Mantención: {block_reason}")

    st.divider()

    st.markdown('<div class="section-title">🔎 Buscar disponibilidad</div>', unsafe_allow_html=True)
    st.caption("Filtra por fechas, edificio y capacidad mínima de huéspedes.")

    max_capacity = max(int(d["capacity"]) for d in departments) if departments else 1
    search_condos = ["Todos los edificios"] + sorted({d["condo"] for d in departments})

    b1, b2, b3, b4 = st.columns([1.15, 1.15, 1, 1.35])

    with b1:
        search_in = st.date_input(
            "Entrada",
            value=today_cl(),
            key="search_in"
        )

    with b2:
        search_out = st.date_input(
            "Salida",
            value=today_cl() + timedelta(days=2),
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
                block = block_conflict_exists(
                    d["id"], search_in, search_out
                )
                if not conflict and not block:
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
                        season_price = season_price_for(
                            get_seasons(d["id"], d["condo"]),
                            search_in,
                            d["id"],
                            d["condo"],
                        )
                        night_price = season_price or int(d["summer_price"])
                        total_reference = nights_search * night_price
                        st.markdown(
                            f"""
                            <div class="search-result-card">
                                <div class="search-result-building">🏢 {esc(d['condo'])}</div>
                                <div class="search-result-name">{esc(d['name'])}</div>
                                <div>👥 Hasta {d['capacity']} huéspedes</div>
                                <div>🌙 {nights_search} noche(s)</div>
                                <div>🌤️ {money(night_price)} / noche</div>
                                <div style="margin-top:7px;font-weight:800;color:{FUCHSIA_DARK}">
                                    Referencia: {money(total_reference)}
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
    page_section_header(
        "Departamentos",
        "Explora tus edificios y administra los departamentos de cada uno."
    )

    departments = get_departments()
    owners = get_owners(active_only=True)
    owner_labels = {
        (f"{o['full_name']} · {o['rut']}" if o["rut"] else o["full_name"]): int(o["id"])
        for o in owners
    }

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

        owner_choice = st.selectbox(
            "Propietario",
            ["Sin asignar"] + list(owner_labels.keys()),
            key="new_department_owner",
            help="Puedes crear propietarios en la sección Propietarios del menú.",
        )
        new_owner_id = owner_labels.get(owner_choice) if owner_choice != "Sin asignar" else None

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
            if not clean_condo or not name.strip():
                st.warning("Completa el edificio/condominio y el departamento.")
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
                        owner_id=new_owner_id,
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
                        <img src="{image_uri}" alt="{esc(condo)}">
                        <div class="building-overlay"></div>
                        <div class="building-content">
                            <div class="building-kicker">Edificio / condominio</div>
                            <div class="building-name">{esc(condo)}</div>
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
                            <div class="building-name">{esc(condo)}</div>
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
                                <div class="dept-name">{esc(d['name'])}</div>
                                <div class="dept-condo">{esc(d['condo'])}</div>
                                <div>👥 Hasta {d['capacity']} huéspedes</div>
                                <div>❄️ Invierno · {money(d['winter_price'])}</div>
                                <div>☀️ Verano · {money(d['summer_price'])}</div>
                                <div>👤 {esc(d['owner_display_name'] or 'Sin propietario')}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        with st.expander("Modificar"):
                            new_name = st.text_input(
                                "Nombre", value=d["name"], key=f"dn_{d['id']}"
                            )
                            new_capacity = st.number_input(
                                "Capacidad", min_value=1,
                                value=int(d["capacity"]), key=f"dc_{d['id']}"
                            )
                            new_winter = st.number_input(
                                "Invierno", min_value=0,
                                value=int(d["winter_price"]), step=5000,
                                key=f"dw_{d['id']}"
                            )
                            new_summer = st.number_input(
                                "Verano", min_value=0,
                                value=int(d["summer_price"]), step=5000,
                                key=f"ds_{d['id']}"
                            )
                            owner_options = ["Sin asignar"] + list(owner_labels.keys())
                            current_owner_label = next(
                                (label for label, oid in owner_labels.items()
                                 if oid == d["owner_id"]),
                                "Sin asignar",
                            )
                            edit_owner = st.selectbox(
                                "Propietario", owner_options,
                                index=owner_options.index(current_owner_label),
                                key=f"downer_{d['id']}",
                            )
                            edit_owner_id = (
                                owner_labels.get(edit_owner)
                                if edit_owner != "Sin asignar" else None
                            )
                            new_address = st.text_input(
                                "Dirección", value=d["address"] or "",
                                key=f"daddr_{d['id']}"
                            )
                            new_wifi_name = st.text_input(
                                "WiFi (red)", value=d["wifi_name"] or "",
                                key=f"dwifi_{d['id']}"
                            )
                            new_wifi_pass = st.text_input(
                                "WiFi (clave)", value=d["wifi_password"] or "",
                                key=f"dpass_{d['id']}", type="password"
                            )
                            new_notes = st.text_area(
                                "Notas internas", value=d["notes"] or "",
                                key=f"dnotes_{d['id']}"
                            )

                            if st.button(
                                "Guardar cambios", key=f"save_d_{d['id']}",
                                use_container_width=True,
                            ):
                                try:
                                    update_department(
                                        d["id"], name=new_name.strip(),
                                        capacity=int(new_capacity),
                                        winter_price=int(new_winter),
                                        summer_price=int(new_summer),
                                        owner_id=edit_owner_id,
                                        address=new_address.strip(),
                                        wifi_name=new_wifi_name.strip(),
                                        wifi_password=new_wifi_pass.strip(),
                                        notes=new_notes.strip(),
                                    )
                                except Exception as exc:
                                    st.error(f"No se pudo actualizar: {exc}")
                                else:
                                    st.success("Departamento actualizado.")
                                    st.rerun()

                            st.markdown('<div class="danger-zone"></div>', unsafe_allow_html=True)

                            if st.button(
                                "Archivar departamento",
                                key=f"archive_d_{d['id']}",
                                use_container_width=True,
                                help="Lo oculta de las listas sin borrar su historial.",
                            ):
                                try:
                                    archive_department(d["id"])
                                except Exception as exc:
                                    st.error(f"No se pudo archivar: {exc}")
                                else:
                                    st.success("Departamento archivado.")
                                    st.rerun()

                            if st.button(
                                "🗑️ Eliminar definitivamente",
                                key=f"delete_d_{d['id']}",
                                use_container_width=True,
                            ):
                                st.session_state[f"confirm_del_dept_{d['id']}"] = True
                                st.rerun()

                            if st.session_state.get(f"confirm_del_dept_{d['id']}", False):
                                st.warning(
                                    "Solo se puede eliminar si no tiene reservas ni "
                                    "liquidaciones. Esta acción no se puede deshacer."
                                )
                                dc1, dc2 = st.columns(2)
                                with dc1:
                                    if st.button(
                                        "Sí, eliminar",
                                        key=f"confirm_del_dept_yes_{d['id']}",
                                        type="primary",
                                        use_container_width=True,
                                    ):
                                        try:
                                            old_condo = delete_department_safe(d["id"])
                                        except ValueError as exc:
                                            st.error(str(exc))
                                        except Exception as exc:
                                            st.error(f"No se pudo eliminar: {exc}")
                                        else:
                                            st.session_state.pop(
                                                f"confirm_del_dept_{d['id']}", None
                                            )
                                            delete_condo_image_if_unused(old_condo)
                                            st.success("Departamento eliminado.")
                                            st.rerun()
                                with dc2:
                                    if st.button(
                                        "Cancelar",
                                        key=f"confirm_del_dept_no_{d['id']}",
                                        use_container_width=True,
                                    ):
                                        st.session_state.pop(
                                            f"confirm_del_dept_{d['id']}", None
                                        )
                                        st.rerun()

                        with st.expander("Temporadas y precios"):
                            seasons = [
                                season for season in get_seasons(d["id"], d["condo"])
                                if season["department_id"] == d["id"]
                            ]
                            if seasons:
                                for season in seasons:
                                    sc1, sc2 = st.columns([4, 1])
                                    with sc1:
                                        st.markdown(
                                            f"**{esc(season['name'])}** · "
                                            f"{season['start_date']:%d/%m/%Y} → "
                                            f"{season['end_date']:%d/%m/%Y} · "
                                            f"{money(season['price_per_night'])}/noche"
                                        )
                                    with sc2:
                                        if st.button(
                                            "Quitar",
                                            key=f"del_season_{season['id']}",
                                            use_container_width=True,
                                        ):
                                            try:
                                                delete_season(season["id"])
                                            except Exception as exc:
                                                st.error(str(exc))
                                            else:
                                                st.rerun()
                            else:
                                st.caption("Sin temporadas propias. Se usan los precios de invierno/verano.")

                            with st.form(key=f"season_form_{d['id']}"):
                                season_name = st.text_input(
                                    "Nombre de la temporada",
                                    value="Temporada alta",
                                )
                                sd1, sd2 = st.columns(2)
                                with sd1:
                                    season_start = st.date_input(
                                        "Desde", value=today_cl()
                                    )
                                with sd2:
                                    season_end = st.date_input(
                                        "Hasta", value=today_cl() + timedelta(days=30)
                                    )
                                season_price = st.number_input(
                                    "Precio por noche", min_value=0,
                                    value=int(d["summer_price"]), step=5000,
                                )
                                season_priority = st.number_input(
                                    "Prioridad", min_value=0, value=10, step=1,
                                    help="Si dos temporadas se cruzan, gana la de mayor prioridad."
                                )
                                if st.form_submit_button(
                                    "Agregar temporada", use_container_width=True
                                ):
                                    if season_end <= season_start:
                                        st.error("La fecha final debe ser posterior a la inicial.")
                                    else:
                                        try:
                                            add_season(
                                                season_name, season_start, season_end,
                                                season_price, department_id=d["id"],
                                                priority=season_priority,
                                            )
                                        except Exception as exc:
                                            st.error(f"No se pudo guardar la temporada: {exc}")
                                        else:
                                            st.success("Temporada agregada.")
                                            st.rerun()

                        with st.expander("Bloqueos por mantención"):
                            dept_blocks = get_blocks(d["id"])
                            if dept_blocks:
                                for block in dept_blocks:
                                    bc1, bc2 = st.columns([4, 1])
                                    with bc1:
                                        st.markdown(
                                            f"**{esc(block['reason'])}** · "
                                            f"{block['start_date']:%d/%m/%Y} → "
                                            f"{block['end_date']:%d/%m/%Y}"
                                        )
                                    with bc2:
                                        if st.button(
                                            "Quitar",
                                            key=f"del_block_{block['id']}",
                                            use_container_width=True,
                                        ):
                                            try:
                                                delete_block(block["id"])
                                            except Exception as exc:
                                                st.error(str(exc))
                                            else:
                                                st.rerun()
                            else:
                                st.caption("Sin bloqueos. Las fechas están disponibles para reservar.")

                            with st.form(key=f"block_form_{d['id']}"):
                                block_reason = st.text_input(
                                    "Motivo", value="Mantención"
                                )
                                bd1, bd2 = st.columns(2)
                                with bd1:
                                    block_start = st.date_input(
                                        "Desde", value=today_cl()
                                    )
                                with bd2:
                                    block_end = st.date_input(
                                        "Hasta", value=today_cl() + timedelta(days=7)
                                    )
                                if st.form_submit_button(
                                    "Agregar bloqueo", use_container_width=True
                                ):
                                    if block_end <= block_start:
                                        st.error("La fecha final debe ser posterior a la inicial.")
                                    else:
                                        try:
                                            add_block(
                                                d["id"], block_start, block_end,
                                                block_reason,
                                            )
                                        except Exception as exc:
                                            st.error(
                                                "No se pudo bloquear: "
                                                f"{exc}"
                                            )
                                        else:
                                            st.success("Bloqueo agregado.")
                                            st.rerun()


# =========================================================
# PROPIETARIOS
# =========================================================

def page_propietarios():
    page_section_header(
        "Propietarios",
        "Datos de contacto, banco y comisión de cada propietario.",
    )

    owners = get_owners()
    departments = get_departments(include_inactive=True)

    with st.expander("＋ Nuevo propietario", expanded=not owners):
        with st.form("new_owner_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                full_name = st.text_input("Nombre completo")
                rut = st.text_input("RUT")
                phone = st.text_input("Teléfono")
                email = st.text_input("Email")
            with c2:
                bank_name = st.text_input("Banco")
                bank_account = st.text_input("Cuenta")
                bank_holder = st.text_input("Titular de la cuenta")
                commission = st.number_input(
                    "Comisión (%)", min_value=0, max_value=100,
                    value=10, step=1,
                )
            notes = st.text_area("Notas")
            if st.form_submit_button(
                "Guardar propietario", type="primary",
                use_container_width=True,
            ):
                if not full_name.strip():
                    st.error("Ingresa el nombre del propietario.")
                else:
                    try:
                        save_owner(
                            full_name, rut, phone, email, bank_name,
                            bank_account, bank_holder, commission, notes,
                        )
                    except Exception as exc:
                        st.error(f"No se pudo guardar: {exc}")
                    else:
                        st.success("Propietario guardado.")
                        st.rerun()

    if not owners:
        st.info("Aún no hay propietarios registrados.")
        return

    for owner in owners:
        owned = [d for d in departments if d["owner_id"] == owner["id"]]
        active_label = "Activo" if owner["active"] else "Inactivo"
        st.markdown(
            f"""
            <div class="owner-card">
                <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
                    <div>
                        <div style="font-size:1.08rem;font-weight:800">{esc(owner['full_name'])}</div>
                        <div style="color:{MUTED};font-size:.86rem">
                            {esc(owner['rut'] or 'Sin RUT')} · {esc(owner['phone'] or 'Sin teléfono')} · {esc(owner['email'] or 'Sin email')}
                        </div>
                    </div>
                    <span class="status-pill {'ok' if owner['active'] else 'danger'}">{active_label}</span>
                </div>
                <div style="margin-top:8px;color:{MUTED};font-size:.88rem">
                    Comisión: <b>{owner['commission_percent']}%</b> ·
                    {len(owned)} departamento(s) asignado(s)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"Editar datos de {owner['full_name']}"):
            with st.form(f"owner_form_{owner['id']}"):
                c1, c2 = st.columns(2)
                with c1:
                    e_full = st.text_input(
                        "Nombre completo", value=owner["full_name"]
                    )
                    e_rut = st.text_input("RUT", value=owner["rut"] or "")
                    e_phone = st.text_input("Teléfono", value=owner["phone"] or "")
                    e_email = st.text_input("Email", value=owner["email"] or "")
                with c2:
                    e_bank = st.text_input("Banco", value=owner["bank_name"] or "")
                    e_account = st.text_input(
                        "Cuenta", value=owner["bank_account"] or ""
                    )
                    e_holder = st.text_input(
                        "Titular", value=owner["bank_holder"] or ""
                    )
                    e_commission = st.number_input(
                        "Comisión (%)", min_value=0, max_value=100,
                        value=int(owner["commission_percent"]), step=1,
                    )
                e_notes = st.text_area("Notas", value=owner["notes"] or "")
                e_active = st.checkbox("Activo", value=bool(owner["active"]))
                if st.form_submit_button(
                    "Guardar cambios", type="primary",
                    use_container_width=True,
                ):
                    try:
                        save_owner(
                            e_full, e_rut, e_phone, e_email, e_bank,
                            e_account, e_holder, e_commission, e_notes,
                            e_active, owner_id=owner["id"],
                        )
                    except Exception as exc:
                        st.error(f"No se pudo actualizar: {exc}")
                    else:
                        st.success("Propietario actualizado.")
                        st.rerun()


# =========================================================
# REPORTES
# =========================================================

def _report_table(rows, numeric_columns=()):
    """Muestra una tabla compacta con la identidad rosada de la app."""
    if not rows:
        st.info("Sin datos para el período.")
        return

    columns = list(rows[0].keys())
    numeric = {str(column) for column in numeric_columns}

    head = "".join(f"<th>{esc(column)}</th>" for column in columns)
    body = []
    for row in rows:
        cells = []
        for column in columns:
            align = "right" if column in numeric else "left"
            cells.append(
                f'<td style="text-align:{align}">{esc(row.get(column, ""))}</td>'
            )
        body.append(f"<tr>{''.join(cells)}</tr>")

    st.markdown(
        f"""
        <div class="report-table-wrap">
            <table class="report-table">
                <thead><tr>{head}</tr></thead>
                <tbody>{''.join(body)}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_reportes():
    page_section_header(
        "Reportes",
        "Ingresos, cobros, ocupación y liquidación estimada por período.",
    )

    reservations_all = get_reservations(include_cancelled=True)
    departments = get_departments(include_inactive=True)
    owners = get_owners()

    r1, r2 = st.columns(2)
    with r1:
        year = st.number_input(
            "Año", min_value=2024, max_value=2035,
            value=today_cl().year, step=1, key="report_year",
        )
    with r2:
        month = st.selectbox(
            "Mes", list(range(1, 13)),
            index=today_cl().month - 1,
            format_func=lambda m: _MESES[m - 1].capitalize(),
            key="report_month",
        )

    month_start = date(int(year), int(month), 1)
    month_end = date(
        int(year), int(month), monthrange(int(year), int(month))[1]
    )

    month_res = [
        r for r in reservations_all
        if r["status"] != STATUS_CANCELLED
        and month_start <= date.fromisoformat(str(r["check_in"])[:10]) <= month_end
    ]

    total_income = sum(int(r["total"]) for r in month_res)
    total_paid = sum(int(r["paid"]) for r in month_res)
    total_pending = max(total_income - total_paid, 0)
    total_nights = sum(int(r["nights"]) for r in month_res)
    active_depts = [d for d in departments if d["active"]]
    available_nights = max(len(active_depts) * (month_end - month_start).days + len(active_depts), 1)
    occupancy = min(total_nights / available_nights * 100, 100)

    m1, m2, m3, m4 = st.columns(4)
    metrics = [
        ("INGRESOS RESERVADOS", money(total_income)),
        ("COBRADO", money(total_paid)),
        ("SALDO PENDIENTE", money(total_pending)),
        ("OCUPACIÓN", f"{occupancy:.0f}%"),
    ]
    for column, (label, value) in zip((m1, m2, m3, m4), metrics):
        with column:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div></div>',
                unsafe_allow_html=True,
            )

    st.caption(
        f"{len(month_res)} reserva(s) · {total_nights} noche(s) vendidas en "
        f"{len(active_depts)} departamento(s) activo(s)."
    )

    if not month_res:
        st.info("No hay reservas cuyo check-in caiga en el período seleccionado.")
        return

    st.markdown('<div class="section-title">Por edificio</div>', unsafe_allow_html=True)
    by_condo = defaultdict(lambda: {"reservas": 0, "ingresos": 0, "cobrado": 0, "saldo": 0, "noches": 0})
    for r in month_res:
        row = by_condo[r["condo"]]
        row["reservas"] += 1
        row["ingresos"] += int(r["total"])
        row["cobrado"] += int(r["paid"])
        row["saldo"] += max(int(r["total"]) - int(r["paid"]), 0)
        row["noches"] += int(r["nights"])

    chart_rows = []
    for condo, data in sorted(by_condo.items()):
        chart_rows.append({
            "Edificio": condo, "Tipo": "Ingresos",
            "Monto": int(data["ingresos"]),
        })
        chart_rows.append({
            "Edificio": condo, "Tipo": "Cobrado",
            "Monto": int(data["cobrado"]),
        })

    chart = (
        alt.Chart(pd.DataFrame(chart_rows))
        .mark_bar(cornerRadiusEnd=5)
        .encode(
            x=alt.X(
                "Monto:Q",
                title=None,
                axis=alt.Axis(
                    format=",.0f", gridColor=PINK_LIGHT, labelColor=MUTED,
                    domainColor=PINK_BORDER, tickColor=PINK_BORDER,
                ),
            ),
            y=alt.Y(
                "Edificio:N",
                title=None,
                sort=alt.EncodingSortField(
                    field="Monto", op="sum", order="descending"
                ),
                axis=alt.Axis(
                    labelColor=TEXT, domainColor=PINK_BORDER,
                    tickColor=PINK_BORDER,
                ),
            ),
            xOffset=alt.XOffset("Tipo:N", sort=["Ingresos", "Cobrado"]),
            color=alt.Color(
                "Tipo:N",
                scale=alt.Scale(
                    domain=["Ingresos", "Cobrado"],
                    range=[FUCHSIA, "#F4A6CD"],
                ),
                legend=alt.Legend(orient="top", title=None, labelColor=TEXT),
            ),
            tooltip=[
                alt.Tooltip("Edificio:N"),
                alt.Tooltip("Tipo:N"),
                alt.Tooltip("Monto:Q", format=",.0f", title="Monto (CLP)"),
            ],
        )
        .properties(height=max(120, 44 * len(by_condo)))
    )
    st.altair_chart(chart, use_container_width=True)
    st.caption(
        "Rosado fuerte: ingresos reservados. Rosado suave: dinero ya cobrado."
    )

    _report_table(
        [
            {
                "Edificio": condo,
                "Reservas": data["reservas"],
                "Noches": data["noches"],
                "Ingresos": money(data["ingresos"]),
                "Cobrado": money(data["cobrado"]),
                "Saldo": money(data["saldo"]),
            }
            for condo, data in sorted(by_condo.items())
        ],
        numeric_columns=("Reservas", "Noches", "Ingresos", "Cobrado", "Saldo"),
    )

    st.markdown('<div class="section-title">Por propietario</div>', unsafe_allow_html=True)
    owner_commission = {int(o["id"]): int(o["commission_percent"]) for o in owners}
    by_owner = defaultdict(lambda: {"reservas": 0, "ingresos": 0, "comision": 0, "neto": 0})
    for r in month_res:
        key = r["owner_display_name"] or "Sin asignar"
        row = by_owner[key]
        row["reservas"] += 1
        row["ingresos"] += int(r["total"])
        pct = owner_commission.get(int(r["owner_id"]), 0) if r["owner_id"] else 0
        commission = (int(r["total"]) * pct + 50) // 100
        row["comision"] += commission
        row["neto"] += int(r["total"]) - commission
    _report_table(
        [
            {
                "Propietario": name,
                "Reservas": data["reservas"],
                "Ingresos": money(data["ingresos"]),
                "Comisión estimada": money(data["comision"]),
                "Neto estimado": money(data["neto"]),
            }
            for name, data in sorted(by_owner.items())
        ],
        numeric_columns=(
            "Reservas", "Ingresos", "Comisión estimada", "Neto estimado",
        ),
    )
    st.caption(
        "La comisión estimada usa el porcentaje del propietario. "
        "Los gastos reales se descuentan al preparar cada liquidación."
    )

    export_rows = []
    for r in month_res:
        export_rows.append({
            "Reserva": r["id"],
            "Edificio": r["condo"],
            "Departamento": r["dept_name"],
            "Huésped": r["guest"],
            "Check-in": r["check_in"],
            "Check-out": r["check_out"],
            "Noches": r["nights"],
            "Total": r["total"],
            "Pagado": r["paid"],
            "Saldo": max(int(r["total"]) - int(r["paid"]), 0),
            "Estado": r["status"],
            "Propietario": r["owner_display_name"] or "",
        })
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(export_rows[0].keys()))
    writer.writeheader()
    writer.writerows(export_rows)
    st.download_button(
        "Descargar reporte CSV",
        data=buffer.getvalue().encode("utf-8-sig"),
        file_name=f"reporte_{int(year)}_{int(month):02d}.csv",
        mime="text/csv",
        use_container_width=True,
    )


# =========================================================
# LIQUIDACIONES PARA PROPIETARIOS
# =========================================================

EXPENSE_PRESETS = (
    ("aseo", "Aseo"),
    ("sabanas", "Lavado de sábanas"),
    ("ventanas", "Limpieza de ventanas"),
)


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
        issued = pdf_date(dated or today_cl().isoformat())

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


def save_owner_statement(owner_id, period_start, period_end, items, notes=""):
    """Guarda un estado de cuenta mensual con el detalle de sus liquidaciones."""
    gross = sum(int(item["gross_total"]) for item in items)
    commission = sum(int(item["commission_amount"]) for item in items)
    expenses = sum(int(item["expenses_total"]) for item in items)
    net = sum(int(item["net_total"]) for item in items)
    conn = db()
    try:
        cur = conn.cursor()
        statement_id = cur.execute("""
            INSERT INTO owner_statements
                (owner_id, period_start, period_end, gross_total,
                 commission_total, expenses_total, net_total, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """, (
            int(owner_id), period_start, period_end, gross,
            commission, expenses, net, notes.strip(),
        )).fetchone()["id"]
        for item in items:
            cur.execute("""
                INSERT INTO owner_statement_items
                    (statement_id, reservation_id, owner_liquidation_id,
                     condo_name, department_name, guest_name, check_in, check_out,
                     nights, price_night, gross_total, commission_percent,
                     commission_amount, expenses_total, net_total, detail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)
            """, (
                int(statement_id), int(item["reservation_id"]),
                item.get("owner_liquidation_id"),
                item["condo_name"], item["department_name"], item["guest_name"],
                item["check_in"], item["check_out"], int(item["nights"]),
                int(item["price_night"]), int(item["gross_total"]),
                int(item["commission_percent"]), int(item["commission_amount"]),
                int(item["expenses_total"]), int(item["net_total"]),
                json.dumps(item.get("detail") or {}, ensure_ascii=False),
            ))
        conn.commit()
        return int(statement_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_owner_statements(owner_id=None):
    conn = db()
    try:
        where = "WHERE s.owner_id=?" if owner_id is not None else ""
        params = (int(owner_id),) if owner_id is not None else ()
        return conn.execute(f"""
            SELECT s.*, o.full_name AS owner_name
            FROM owner_statements s
            JOIN owners o ON o.id=s.owner_id
            {where}
            ORDER BY s.period_start DESC, s.id DESC
        """, params).fetchall()
    finally:
        conn.close()


def mark_owner_statement_paid(statement_id, reference=""):
    conn = db()
    try:
        conn.execute("""
            UPDATE owner_statements
            SET status='Pagada', paid_at=NOW(), payment_reference=?
            WHERE id=?
        """, (reference.strip(), int(statement_id)))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def page_resumen_mensual():
    st.markdown('<div class="section-title">Resumen mensual por propietario</div>', unsafe_allow_html=True)
    st.caption(
        "Agrupa las liquidaciones de un mes, guarda el estado de cuenta y "
        "marca cuándo fue pagado al propietario."
    )
    owners = get_owners()
    if not owners:
        st.info("Primero registra propietarios en la sección Propietarios.")
        return

    owner_map = {
        (f"{o['full_name']} · {o['rut']}" if o["rut"] else o["full_name"]): o
        for o in owners
    }
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        owner_label = st.selectbox(
            "Propietario", list(owner_map.keys()), key="stmt_owner"
        )
    with c2:
        year = st.number_input(
            "Año", min_value=2024, max_value=2035,
            value=today_cl().year, step=1, key="stmt_year",
        )
    with c3:
        month = st.selectbox(
            "Mes", list(range(1, 13)),
            index=today_cl().month - 1,
            format_func=lambda m: _MESES[m - 1].capitalize(),
            key="stmt_month",
        )
    owner = owner_map[owner_label]
    period_start = date(int(year), int(month), 1)
    period_end = date(int(year), int(month), monthrange(int(year), int(month))[1])

    reservations = get_reservations(include_cancelled=True)
    reservation_map = {int(r["id"]): r for r in reservations}
    liquidations = list_owner_liquidations()
    items = []
    for liquidation in liquidations:
        reservation = reservation_map.get(int(liquidation["reservation_id"]))
        if not reservation:
            continue
        check_in = date.fromisoformat(str(liquidation["check_in"])[:10])
        if not (period_start <= check_in <= period_end):
            continue
        belongs = int(reservation["owner_id"] or 0) == int(owner["id"])
        same_name = (
            str(liquidation["owner_name"]).strip().casefold()
            == str(owner["full_name"]).strip().casefold()
        )
        if not belongs and not same_name:
            continue
        items.append({
            "reservation_id": int(liquidation["reservation_id"]),
            "owner_liquidation_id": int(liquidation["id"]),
            "condo_name": liquidation["condo_name"],
            "department_name": liquidation["department_name"],
            "guest_name": liquidation["guest_name"],
            "check_in": check_in,
            "check_out": date.fromisoformat(str(liquidation["check_out"])[:10]),
            "nights": int(liquidation["nights"]),
            "price_night": int(liquidation["price_night"]),
            "gross_total": int(liquidation["gross_total"]),
            "commission_percent": int(liquidation["commission_percent"]),
            "commission_amount": int(liquidation["commission_amount"]),
            "expenses_total": int(liquidation["expenses_total"]),
            "net_total": int(liquidation["owner_net"]),
            "detail": liquidation.get("expenses") or [],
        })

    if not items:
        st.info("No hay liquidaciones guardadas para ese propietario y período.")
    else:
        st.dataframe(
            [
                {
                    "Reserva": item["reservation_id"],
                    "Departamento": item["department_name"],
                    "Huésped": item["guest_name"],
                    "Llegada": item["check_in"].strftime("%d/%m/%Y"),
                    "Bruto": money(item["gross_total"]),
                    "Comisión": money(item["commission_amount"]),
                    "Gastos": money(item["expenses_total"]),
                    "Neto": money(item["net_total"]),
                }
                for item in items
            ],
            use_container_width=True, hide_index=True,
        )
        totals = {
            "bruto": sum(i["gross_total"] for i in items),
            "comision": sum(i["commission_amount"] for i in items),
            "gastos": sum(i["expenses_total"] for i in items),
            "neto": sum(i["net_total"] for i in items),
        }
        st.markdown(
            f"""
            <div class="payment-summary">
                <div class="payment-card"><div class="payment-card-label">BRUTO</div>
                    <div class="payment-card-value">{money(totals['bruto'])}</div></div>
                <div class="payment-card"><div class="payment-card-label">COMISIÓN</div>
                    <div class="payment-card-value">{money(totals['comision'])}</div></div>
                <div class="payment-card"><div class="payment-card-label">GASTOS</div>
                    <div class="payment-card-value">{money(totals['gastos'])}</div></div>
                <div class="payment-card"><div class="payment-card-label">NETO PROPIETARIO</div>
                    <div class="payment-card-value">{money(totals['neto'])}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        statement_notes = st.text_input(
            "Observaciones del estado de cuenta", key="stmt_notes"
        )
        if st.button(
            "Guardar estado de cuenta del mes",
            type="primary", use_container_width=True,
            key="stmt_save",
        ):
            try:
                statement_id = save_owner_statement(
                    owner["id"], period_start, period_end, items,
                    statement_notes,
                )
            except Exception as exc:
                st.error(f"No se pudo guardar el estado de cuenta: {exc}")
            else:
                st.success(f"Estado de cuenta guardado (N.º {statement_id}).")
                st.rerun()

    st.divider()
    st.markdown('<div class="section-title">Estados de cuenta guardados</div>', unsafe_allow_html=True)
    statements = list_owner_statements(owner["id"])
    if not statements:
        st.caption("Todavía no hay estados de cuenta guardados para este propietario.")
    for statement in statements:
        sc1, sc2, sc3 = st.columns([3, 2, 1])
        with sc1:
            st.markdown(
                f"**{statement['period_start']:%d/%m/%Y} → "
                f"{statement['period_end']:%d/%m/%Y}** · "
                f"{money(statement['net_total'])} neto"
            )
        with sc2:
            st.caption(
                f"Bruto {money(statement['gross_total'])} · "
                f"Comisión {money(statement['commission_total'])} · "
                f"Gastos {money(statement['expenses_total'])} · "
                f"Estado: {statement['status']}"
            )
        with sc3:
            if statement["status"] != "Pagada":
                if st.button(
                    "Marcar pagada",
                    key=f"stmt_paid_{statement['id']}",
                    use_container_width=True,
                ):
                    try:
                        mark_owner_statement_paid(
                            statement["id"],
                            f"Pago {today_cl():%d/%m/%Y}",
                        )
                    except Exception as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
            else:
                st.caption(
                    f"Pagada {statement['paid_at']:%d/%m/%Y}"
                    if statement["paid_at"] else "Pagada"
                )


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
                    if st.button("Editar", key=f"liq_edit_card_{sid}", use_container_width=True):
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

        st.markdown(f"**{esc(r['condo'])} · {esc(r['dept_name'])}**  |  {esc(r['guest'])}")
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
            # Solo recordamos como habitual el gasto que realmente se usó.
            # Si se desmarca, no debe reactivarse solo en la próxima liquidación.
            if enabled and int(amount) > 0:
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
    # Usa la misma portada y paleta que la pantalla Inicio.
    page_section_header(
        "Liquidaciones",
        "Consulta tus liquidaciones por huésped, llegada y departamento, o prepara el comprobante para cada propietario."
    )
    st.caption("La comisión se calcula sobre el total del arriendo, no sobre los abonos.")
    if "liq_view" not in st.session_state:
        st.session_state.liq_view = "Historial"
    view = st.segmented_control(
        "Vista de liquidaciones",
        ["Historial", "Preparar liquidación", "Resumen mensual"],
        key="liq_view", label_visibility="collapsed"
    )
    if view == "Preparar liquidación":
        page_preparar_liquidacion()
    elif view == "Resumen mensual":
        page_resumen_mensual()
    else:
        page_historial_liquidaciones()


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

elif st.session_state.page == "Propietarios":
    page_propietarios()

elif st.session_state.page == "Reportes":
    page_reportes()

elif st.session_state.page == "Liquidaciones":
    page_liquidaciones()

elif st.session_state.page == "Detalle":
    page_detalle()

else:
    st.session_state.page = "Inicio"
    st.rerun()

st.markdown(
    '<div class="footer-note">Arriendos · Panel de gestión</div>',
    unsafe_allow_html=True
)
