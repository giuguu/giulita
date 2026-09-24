import streamlit as st
import sqlite3
import base64
from datetime import date, datetime, timedelta
from calendar import monthrange
from pathlib import Path

# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="Arriendos",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path("arriendos.db")

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
# BASE DE DATOS
# =========================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    cur = conn.cursor()

    # -----------------------------------------------------
    # Crear tablas si no existen
    # -----------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            condo TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            capacity INTEGER NOT NULL DEFAULT 2,
            winter_price INTEGER NOT NULL DEFAULT 0,
            summer_price INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER NOT NULL,
            guest TEXT NOT NULL DEFAULT '',
            phone TEXT DEFAULT '',
            check_in TEXT NOT NULL,
            check_in_time TEXT DEFAULT '15:00',
            check_out TEXT NOT NULL,
            check_out_time TEXT DEFAULT '11:00',
            guests INTEGER NOT NULL DEFAULT 1,
            price_night INTEGER NOT NULL DEFAULT 0,
            nights INTEGER NOT NULL DEFAULT 1,
            total INTEGER NOT NULL DEFAULT 0,
            deposit_percent REAL NOT NULL DEFAULT 0,
            deposited INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Sin abono',
            FOREIGN KEY(department_id) REFERENCES departments(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL,
            amount INTEGER NOT NULL DEFAULT 0,
            payment_date TEXT NOT NULL,
            note TEXT DEFAULT '',
            FOREIGN KEY(reservation_id) REFERENCES reservations(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS checklist (
            reservation_id INTEGER PRIMARY KEY,
            cleaning INTEGER NOT NULL DEFAULT 0,
            internet INTEGER NOT NULL DEFAULT 0,
            inspected INTEGER NOT NULL DEFAULT 0,
            keys INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(reservation_id) REFERENCES reservations(id)
        )
    """)

    # -----------------------------------------------------
    # MIGRACIÓN:
    # Si existe una base de datos antigua, agrega las
    # columnas que necesita esta versión.
    # -----------------------------------------------------
    def existing_columns(table):
        return {
            row[1]
            for row in cur.execute(f"PRAGMA table_info({table})").fetchall()
        }

    def add_column_if_missing(table, column, definition):
        columns = existing_columns(table)
        if column not in columns:
            cur.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )

    # Departamentos antiguos
    add_column_if_missing("departments", "condo", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing("departments", "name", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing("departments", "capacity", "INTEGER NOT NULL DEFAULT 2")
    add_column_if_missing("departments", "winter_price", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("departments", "summer_price", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("departments", "active", "INTEGER NOT NULL DEFAULT 1")

    # Compatibilidad con una versión anterior que usaba la columna
    # "condominium" en lugar de "condo".
    department_columns = existing_columns("departments")
    if "condominium" in department_columns:
        cur.execute("""
            UPDATE departments
            SET condo = condominium
            WHERE (condo IS NULL OR TRIM(condo) = '')
              AND condominium IS NOT NULL
        """)

    # Reservas antiguas
    add_column_if_missing("reservations", "department_id", "INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing("reservations", "guest", "TEXT NOT NULL DEFAULT ''")
    # Compatibilidad con una versión que utilizaba "guest_name".
    # No eliminamos esa columna para conservar la base de datos existente.
    add_column_if_missing("reservations", "guest_name", "TEXT NOT NULL DEFAULT ''")
    cur.execute("""
        UPDATE reservations
        SET guest_name = guest
        WHERE (guest_name IS NULL OR TRIM(guest_name) = '')
          AND guest IS NOT NULL
    """)
    add_column_if_missing("reservations", "phone", "TEXT DEFAULT ''")
    add_column_if_missing("reservations", "check_in", "TEXT NOT NULL DEFAULT '2000-01-01'")
    add_column_if_missing("reservations", "check_in_time", "TEXT DEFAULT '15:00'")
    add_column_if_missing("reservations", "check_out", "TEXT NOT NULL DEFAULT '2000-01-02'")
    add_column_if_missing("reservations", "check_out_time", "TEXT DEFAULT '11:00'")
    add_column_if_missing("reservations", "guests", "INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing("reservations", "price_night", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("reservations", "nights", "INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing("reservations", "total", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("reservations", "deposit_percent", "REAL NOT NULL DEFAULT 0")
    add_column_if_missing("reservations", "deposited", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("reservations", "status", "TEXT NOT NULL DEFAULT 'Sin abono'")

    # Tablas auxiliares: si no existían, ya fueron creadas arriba.
    # -----------------------------------------------------

    # Datos iniciales solo si no existen departamentos.
    count = cur.execute("SELECT COUNT(*) FROM departments").fetchone()[0]

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

    # Reservas de ejemplo solo si no existen.
    rcount = cur.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]

    if rcount == 0:
        dept = cur.execute("""
            SELECT id FROM departments
            WHERE condo='Serena Pacífico' AND name='Depto 305'
            LIMIT 1
        """).fetchone()

        dept2 = cur.execute("""
            SELECT id FROM departments
            WHERE condo='Oceanic' AND name='Depto 101'
            LIMIT 1
        """).fetchone()

        today = date.today()
        r1_in = today + timedelta(days=2)
        r1_out = today + timedelta(days=6)
        r2_in = today + timedelta(days=8)
        r2_out = today + timedelta(days=11)

        if dept:
            nights = (r1_out - r1_in).days
            total = nights * 70000

            cur.execute("""
                INSERT INTO reservations
                (department_id, guest, phone, check_in, check_in_time,
                 check_out, check_out_time, guests, price_night, nights,
                 total, deposit_percent, deposited, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dept["id"], "María González", "+56 9 1234 5678",
                r1_in.isoformat(), "15:00",
                r1_out.isoformat(), "11:00",
                4, 70000, nights, total, 30,
                int(total * 0.30), "Abono recibido"
            ))

            rid = cur.lastrowid

            cur.execute("""
                INSERT INTO checklist
                (reservation_id, cleaning, internet, inspected, keys)
                VALUES (?, 0, 1, 0, 1)
            """, (rid,))

        if dept2:
            nights = (r2_out - r2_in).days
            total = nights * 65000

            cur.execute("""
                INSERT INTO reservations
                (department_id, guest, phone, check_in, check_in_time,
                 check_out, check_out_time, guests, price_night, nights,
                 total, deposit_percent, deposited, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dept2["id"], "Carlos Rojas", "+56 9 9876 5432",
                r2_in.isoformat(), "16:00",
                r2_out.isoformat(), "11:00",
                3, 65000, nights, total, 100,
                total, "Pagado completamente"
            ))

            rid = cur.lastrowid

            cur.execute("""
                INSERT INTO checklist
                (reservation_id, cleaning, internet, inspected, keys)
                VALUES (?, 1, 1, 1, 1)
            """, (rid,))

    conn.commit()
    conn.close()


init_db()

# =========================================================
# FUNCIONES
# =========================================================

def money(value):
    return f"${int(value):,}".replace(",", ".")


def department_columns():
    conn = db()
    cols = {row[1] for row in conn.execute("PRAGMA table_info(departments)").fetchall()}
    conn.close()
    return cols


def insert_department(condo, name, capacity, winter, summer):
    """Inserta un departamento y es compatible con bases antiguas."""
    conn = db()
    cols = {row[1] for row in conn.execute("PRAGMA table_info(departments)").fetchall()}

    if "condominium" in cols:
        conn.execute("""
            INSERT INTO departments
            (condo, condominium, name, capacity, winter_price, summer_price)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (condo, condo, name, capacity, winter, summer))
    else:
        conn.execute("""
            INSERT INTO departments
            (condo, name, capacity, winter_price, summer_price)
            VALUES (?, ?, ?, ?, ?)
        """, (condo, name, capacity, winter, summer))

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


def get_departments():
    conn = db()
    rows = conn.execute("""
        SELECT * FROM departments
        WHERE active=1
        ORDER BY condo, name
    """).fetchall()
    conn.close()
    return rows


def get_reservations():
    conn = db()
    rows = conn.execute("""
        SELECT r.*, d.name AS dept_name, d.condo, d.capacity
        FROM reservations r
        JOIN departments d ON d.id=r.department_id
        ORDER BY r.check_in
    """).fetchall()
    conn.close()
    return rows


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
    cur = conn.cursor()

    reservation_columns = {
        row[1] for row in cur.execute("PRAGMA table_info(reservations)").fetchall()
    }

    if reservation_id:
        # Mantiene compatibilidad con bases antiguas que tienen guest_name.
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
                 total, deposit_percent, deposited, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                department_id, guest, guest, phone, check_in.isoformat(),
                check_in_time, check_out.isoformat(), check_out_time,
                guests, price_night, nights, total,
                deposit_percent, deposited, status
            ))
        else:
            cur.execute("""
                INSERT INTO reservations
                (department_id, guest, phone, check_in, check_in_time,
                 check_out, check_out_time, guests, price_night, nights,
                 total, deposit_percent, deposited, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                department_id, guest, phone, check_in.isoformat(),
                check_in_time, check_out.isoformat(), check_out_time,
                guests, price_night, nights, total,
                deposit_percent, deposited, status
            ))
        rid = cur.lastrowid

        cur.execute("""
            INSERT OR IGNORE INTO checklist
            (reservation_id, cleaning, internet, inspected, keys)
            VALUES (?, 0, 0, 0, 0)
        """, (rid,))

    conn.commit()
    conn.close()
    return rid


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
    if reservation_id is not None:
        st.session_state.selected_reservation = reservation_id


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

    for r in reservations:
        ci = date.fromisoformat(r["check_in"])
        co = date.fromisoformat(r["check_out"])
        days_to_in = (ci - today).days
        days_to_out = (co - today).days
        checklist = get_checklist(r["id"])

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

pages = [
    "Inicio",
    "Reservas",
    "Calendario",
    "Departamentos",
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
    st.caption(date.today().strftime("%d/%m/%Y"))

# =========================================================
# INICIO
# =========================================================

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
                        <div class="reservation-name">{r['guest']}</div>
                        <div class="reservation-info">
                            🏢 {r['dept_name']} · {r['condo']}<br>
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
                <div class="reminder-title">{title}</div>
                <div class="reminder-text">{text_value}</div>
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
                    <div class="detail-value">{reviewed["guest"]}</div><br>
                    <div class="detail-label">CONTACTO</div>
                    <div class="detail-value">{reviewed["phone"] or "No registrado"}</div><br>
                    <div class="detail-label">DEPARTAMENTO</div>
                    <div class="detail-value">🏢 {reviewed["condo"]} · {reviewed["dept_name"]}</div><br>
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
                    # Última comprobación, justo antes de escribir en SQLite.
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
                        st.session_state.reservation_review = None
                        st.session_state.selected_reservation = rid
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

        for r in reservations:
            ci = date.fromisoformat(r["check_in"])
            co = date.fromisoformat(r["check_out"])

            col1, col2 = st.columns([5, 1])

            with col1:
                st.markdown(
                    f"""
                    <div class="detail-box compact">
                        <b>{r['guest']}</b><br>
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
            <span class="reservation-heading-guest">{r['guest']}</span>
            <span class="reservation-heading-place">🏢 {r['condo']} · {r['dept_name']}</span>
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
                <div class="detail-value">{r['guest']}</div><br>
                <div class="detail-label">CONTACTO</div>
                <div class="detail-value">{r['phone'] or 'No registrado'}</div><br>
                <div class="detail-label">DEPARTAMENTO</div>
                <div class="detail-value">{r['condo']} · {r['dept_name']}</div>
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
                        <div class="{cls}" title="{guest_name if busy else 'Disponible'}">
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

    b1, b2 = st.columns(2)

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

    if st.button(
        "Buscar departamentos disponibles",
        type="primary"
    ):
        if search_out <= search_in:
            st.error("La salida debe ser posterior a la entrada.")
        else:
            available = []

            for d in departments:
                conflict = conflict_exists(
                    d["id"], search_in, search_out
                )
                if not conflict:
                    available.append(d)

            if available:
                st.success(f"Encontramos {len(available)} departamento(s) disponible(s).")

                for d in available:
                    st.markdown(
                        f"""
                        <div class="detail-box">
                            <b>{d['condo']} · {d['name']}</b><br>
                            <span style="color:{MUTED}">
                            Capacidad: {d['capacity']} ·
                            Precio verano: {money(d['summer_price'])}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.error("No hay departamentos disponibles para esas fechas.")


# =========================================================
# DEPARTAMENTOS
# =========================================================

def page_departamentos():
    page_section_header(
        "Departamentos",
        "Administra tus condominios, departamentos, capacidad y tarifas."
    )

    departments = get_departments()

    with st.expander("＋ Agregar departamento"):
        st.caption("Puedes registrar todos los departamentos que necesites dentro del mismo condominio.")
        condo = st.text_input("Condominio", placeholder="Ej. Serena Pacífico")
        name = st.text_input("Nombre o número del departamento", placeholder="Ej. Depto 305")
        capacity = st.number_input("Capacidad", min_value=1, value=4)
        winter = st.number_input("Precio noche invierno", min_value=0, value=60000, step=5000)
        summer = st.number_input("Precio noche verano", min_value=0, value=90000, step=5000)

        if st.button("Agregar departamento", type="primary"):
            if not condo.strip() or not name.strip():
                st.warning("Completa el condominio y el departamento.")
            else:
                insert_department(
                    condo.strip(),
                    name.strip(),
                    capacity,
                    winter,
                    summer
                )
                st.success("Departamento agregado correctamente.")
                st.rerun()

    if not departments:
        st.info("No hay departamentos registrados.")
        return

    # Agrupar por condominio
    condos = {}
    for d in departments:
        condos.setdefault(d["condo"], []).append(d)

    for condo, deps in condos.items():
        st.markdown(
            f'<div class="section-title">🏢 {condo} <span style="color:{MUTED};font-size:.78rem;font-weight:600">· {len(deps)} departamento(s)</span></div>',
            unsafe_allow_html=True
        )

        cols = st.columns(3)

        for i, d in enumerate(deps):
            with cols[i % 3]:
                st.markdown(
                    f"""
                    <div class="dept-card">
                        <div class="dept-name">{d['name']}</div>
                        <div class="dept-condo">{d['condo']}</div>
                        <div>👥 Hasta {d['capacity']} huéspedes</div>
                        <div>❄️ Invierno · {money(d['winter_price'])}</div>
                        <div>☀️ Verano · {money(d['summer_price'])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                with st.expander("Editar"):
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

                    if st.button("Guardar", key=f"save_d_{d['id']}"):
                        conn = db()
                        cols = {row[1] for row in conn.execute("PRAGMA table_info(departments)").fetchall()}
                        if "condominium" in cols:
                            conn.execute("""
                                UPDATE departments
                                SET name=?, capacity=?, winter_price=?, summer_price=?, condominium=condo
                                WHERE id=?
                            """, (new_name, new_capacity, new_winter, new_summer, d["id"]))
                        else:
                            conn.execute("""
                                UPDATE departments
                                SET name=?, capacity=?, winter_price=?, summer_price=?
                                WHERE id=?
                            """, (new_name, new_capacity, new_winter, new_summer, d["id"]))
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
                            conn.execute(
                                "DELETE FROM departments WHERE id=?",
                                (d["id"],)
                            )
                            conn.commit()
                            conn.close()
                            st.success("Departamento eliminado correctamente.")
                            st.rerun()


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

elif st.session_state.page == "Detalle":
    page_detalle()

else:
    st.session_state.page = "Inicio"
    st.rerun()

st.markdown(
    '<div class="footer-note">Arriendos · Panel de gestión</div>',
    unsafe_allow_html=True
)
