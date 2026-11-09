"""Funciones puras de cálculo y formato.

Se mantienen fuera de app.py para poder probarlas sin levantar Streamlit ni
conectarse a la base de datos.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime


# Contrato público del módulo. app.py importa estos nombres directamente; si
# alguno desaparece, el test tests/test_app_logic_contract.py falla antes del
# despliegue en lugar de romper Streamlit Cloud.
__all__ = [
    "STATUS_NO_DEPOSIT",
    "STATUS_PARTIAL",
    "STATUS_PAID",
    "STATUS_CANCELLED",
    "VALID_STATUSES",
    "BANK_GROUPS",
    "BANK_NAMES",
    "BANK_CATEGORY",
    "BANK_ACCOUNT_TYPES",
    "canonical_bank_name",
    "detect_bank_account_type",
    "mask_bank_account",
    "bank_copy_text",
    "bank_option_label",
    "validate_bank_details",
    "money",
    "format_clp",
    "calculate_owner_liquidation",
    "payment_status",
    "pending_amount",
    "payment_totals",
    "nights_between",
    "validate_date_range",
    "season_price_for",
]


STATUS_NO_DEPOSIT = "Sin abono"
STATUS_PARTIAL = "Abono recibido"
STATUS_PAID = "Pagado completamente"
STATUS_CANCELLED = "Cancelada"

VALID_STATUSES = (
    STATUS_NO_DEPOSIT,
    STATUS_PARTIAL,
    STATUS_PAID,
    STATUS_CANCELLED,
)

# =========================================================
# DATOS BANCARIOS DE PROPIETARIOS
# =========================================================

# La lista separa bancos, cooperativas y entidades financieras para no
# presentar como banco a una entidad que no lo es. Banco del Desarrollo ya no
# existe como banco independiente (fue absorbido por Scotiabank), por eso no se
# incluye como opción duplicada.
BANK_GROUPS = (
    ("Bancos", (
        "Banco de Chile",
        "BancoEstado",
        "Banco Santander",
        "Banco BCI",
        "Banco Itaú",
        "Banco Scotiabank",
        "Banco Falabella",
        "Banco Ripley",
        "Banco Security",
        "Banco BICE",
        "Banco Internacional",
        "Banco Consorcio",
        "Banco BTG Pactual Chile",
    )),
    ("Cooperativas", (
        "Coopeuch",
    )),
    ("Entidades financieras", (
        "Tenpo",
        "Mercado Pago",
    )),
    ("Otros", (
        "Efectivo",
        "Otros",
    )),
)

BANK_NAMES = tuple(name for _, names in BANK_GROUPS for name in names)
BANK_CATEGORY = {
    name: category for category, names in BANK_GROUPS for name in names
}

BANK_ACCOUNT_TYPES = (
    "Cuenta Corriente",
    "Cuenta Vista",
    "Cuenta de Ahorro",
    "Cuenta RUT",
    "Cuenta Chequera Electrónica",
    "Otra",
)

_BANK_ALIASES = (
    (re.compile(r"santander"), "Banco Santander"),
    (re.compile(r"banco\s*estado|(^|[^a-z])estado([^a-z]|$)"), "BancoEstado"),
    (re.compile(r"bci|credito e inversiones"), "Banco BCI"),
    (re.compile(r"falabella"), "Banco Falabella"),
    (re.compile(r"scotiabank"), "Banco Scotiabank"),
    (re.compile(r"itau"), "Banco Itaú"),
    (re.compile(r"ripley"), "Banco Ripley"),
    (re.compile(r"security"), "Banco Security"),
    (re.compile(r"bice"), "Banco BICE"),
    (re.compile(r"consorcio"), "Banco Consorcio"),
    (re.compile(r"internacional"), "Banco Internacional"),
    (re.compile(r"btg"), "Banco BTG Pactual Chile"),
    (re.compile(r"coopeuch"), "Coopeuch"),
    (re.compile(r"tenpo"), "Tenpo"),
    (re.compile(r"mercado\s*pago"), "Mercado Pago"),
    (re.compile(r"efectivo"), "Efectivo"),
    (re.compile(r"(^|[^a-z])chile([^a-z]|$)"), "Banco de Chile"),
)


def _fold(value) -> str:
    """Normaliza mayúsculas, tildes y separadores para comparar texto."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().replace("/", " ").split())


def canonical_bank_name(value) -> str | None:
    """Devuelve el nombre canónico del banco/entidad o ``None`` si no se conoce.

    Se usa para reconocer los valores antiguos que mezclaban banco y tipo de
    cuenta, por ejemplo ``"Santander cta/cte"``.
    """
    text = _fold(value)
    if not text:
        return None
    for name in BANK_NAMES:
        if _fold(name) == text:
            return name
    for pattern, name in _BANK_ALIASES:
        if pattern.search(text):
            return name
    return None


def detect_bank_account_type(value) -> str:
    """Infiere el tipo de cuenta solo cuando el texto lo menciona con claridad."""
    text = _fold(value)
    if not text:
        return ""
    if (
        re.search(r"\b(cta|cuenta)\s+(cte|corriente)\b", text)
        or re.search(r"\bcorriente\b", text)
    ):
        return "Cuenta Corriente"
    if (
        re.search(r"\b(cta|cuenta)\s+vista\b", text)
        or re.search(r"\bvista\b", text)
    ):
        return "Cuenta Vista"
    if (
        re.search(r"\b(cta|cuenta)\s+ahorro\b", text)
        or re.search(r"\bahorro\b", text)
    ):
        return "Cuenta de Ahorro"
    if re.search(r"\brut\b", text):
        return "Cuenta RUT"
    if re.search(r"chequera", text):
        return "Cuenta Chequera Electrónica"
    return ""


def mask_bank_account(value) -> str:
    """Enmascara el número de cuenta dejando visibles solo los últimos 4."""
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 4:
        return "****"
    return "********" + text[-4:]


def bank_copy_text(owner_name, bank="", account_type="", account="", holder=""):
    """Texto listo para copiar con los datos bancarios de un propietario."""
    lines = []
    owner_name = str(owner_name or "").strip()
    if owner_name:
        lines.append(f"Propietario: {owner_name}")
    for label, value in (
        ("Banco", bank),
        ("Tipo de cuenta", account_type),
        ("Número de cuenta", account),
        ("Titular", holder),
    ):
        value = str(value or "").strip()
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def bank_option_label(name) -> str:
    """Etiqueta agrupada para el selector de banco."""
    if not name:
        return "Selecciona un banco o entidad"
    category = BANK_CATEGORY.get(name)
    if category is None:
        return f"• {name} (otro)"
    icon = {
        "Bancos": "🏦",
        "Cooperativas": "🤝",
        "Entidades financieras": "💳",
        "Otros": "•",
    }[category]
    suffix = "" if category == "Bancos" else f" · {category.lower()}"
    return f"{icon} {name}{suffix}"


def validate_bank_details(
    bank, account_type, account, allowed_banks=None, holder=""
) -> str | None:
    """Valida que los datos bancarios estén completos o totalmente vacíos.

    Devuelve un mensaje de error o ``None`` si son válidos. ``Efectivo`` es una
    forma de pago, no un banco: puede existir sin tipo ni número de cuenta.
    """
    bank = str(bank or "").strip()
    account_type = str(account_type or "").strip()
    account = str(account or "").strip()
    holder = str(holder or "").strip()

    if not any((bank, account_type, account, holder)):
        return None
    if not bank:
        return "Selecciona el banco o entidad."
    if allowed_banks is not None and bank not in allowed_banks:
        return "Selecciona un banco o entidad de la lista."
    if bank == "Efectivo" and not account_type and not account:
        return None
    if not account_type:
        return "Selecciona el tipo de cuenta."
    if account_type not in BANK_ACCOUNT_TYPES:
        return "Selecciona un tipo de cuenta válido."
    if not account:
        return "Ingresa el número de cuenta."
    if len(account) < 4:
        return "El número de cuenta debe tener al menos 4 caracteres."
    return None


def money(value) -> str:
    """Formatea un monto entero en pesos chilenos."""
    return f"${int(value):,}".replace(",", ".")


def format_clp(value) -> str:
    """Moneda CLP correcta para montos negativos, sin decimales."""
    value = int(value)
    return ("-" if value < 0 else "") + money(abs(value))


def calculate_owner_liquidation(gross_total, commission_percent, expenses):
    """Calcula la liquidación del propietario sobre el bruto de la reserva.

    La comisión nunca se calcula sobre los abonos recibidos: se aplica al total
    del arriendo, que es la base acordada con el propietario.
    """
    gross_total = int(gross_total)
    commission_percent = int(commission_percent)
    if gross_total < 0:
        raise ValueError("El total del arriendo no puede ser negativo.")
    if commission_percent < 0 or commission_percent > 100:
        raise ValueError("El porcentaje de comisión debe estar entre 0 y 100.")
    commission = (gross_total * commission_percent + 50) // 100
    expenses_total = 0
    for item in expenses or []:
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


def payment_status(total, paid, cancelled=False) -> str:
    """Estado coherente de una reserva a partir del dinero realmente pagado."""
    if cancelled:
        return STATUS_CANCELLED
    total = int(total or 0)
    paid = int(paid or 0)
    if paid <= 0:
        return STATUS_NO_DEPOSIT
    if total > 0 and paid >= total:
        return STATUS_PAID
    return STATUS_PARTIAL


def pending_amount(total, paid) -> int:
    """Saldo pendiente, nunca negativo (los pagos de más se controlan aparte)."""
    return max(int(total or 0) - int(paid or 0), 0)


def payment_totals(payments) -> int:
    """Suma solo los pagos vigentes (no anulados)."""
    total = 0
    for payment in payments or []:
        if payment.get("voided_at"):
            continue
        total += int(payment.get("amount") or 0)
    return total


def nights_between(check_in, check_out) -> int:
    """Noches entre dos fechas ISO o date."""
    ci = _as_date(check_in)
    co = _as_date(check_out)
    return max((co - ci).days, 0)


def validate_date_range(check_in, check_out, allow_same_day=False):
    """Devuelve True si el rango es utilizable para una reserva."""
    ci = _as_date(check_in)
    co = _as_date(check_out)
    if allow_same_day:
        return co >= ci
    return co > ci


def season_price_for(seasons, target, department_id=None, condo=None):
    """Precio de temporada aplicable a una fecha.

    Prioridad:
      1. Temporada del departamento exacto.
      2. Temporada del condominio.
      3. Temporada general.
    A igual prioridad, gana la de mayor ``priority`` y luego la más reciente.
    """
    target = _as_date(target)
    candidates = []
    for season in seasons or []:
        if not season.get("active", True):
            continue
        start = _as_date(season["start_date"])
        end = _as_date(season["end_date"])
        if not (start <= target < end):
            continue
        season_dept = season.get("department_id")
        season_condo = (season.get("condo") or "").strip().casefold()
        if season_dept is not None:
            if department_id is not None and int(season_dept) == int(department_id):
                scope = 3
            else:
                continue
        elif season_condo:
            if condo and season_condo == str(condo).strip().casefold():
                scope = 2
            else:
                continue
        else:
            scope = 1
        candidates.append((
            scope,
            int(season.get("priority") or 0),
            int(season.get("id") or 0),
            int(season["price_per_night"]),
        ))
    if not candidates:
        return None
    return max(candidates)[3]


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
