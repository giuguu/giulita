"""Funciones puras de cálculo y formato.

Se mantienen fuera de app.py para poder probarlas sin levantar Streamlit ni
conectarse a la base de datos.
"""

from __future__ import annotations

from datetime import date, datetime


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
