"""Pruebas de las funciones puras de cálculo.

Se ejecutan sin Streamlit ni conexión a la base de datos:

    python -m unittest discover -s tests -v
"""

import unittest
from datetime import date

from logic import (
    calculate_owner_liquidation,
    format_clp,
    money,
    nights_between,
    payment_status,
    payment_totals,
    pending_amount,
    season_price_for,
    validate_date_range,
)


class MoneyTests(unittest.TestCase):
    def test_money_uses_thousands_separator(self):
        self.assertEqual(money(0), "$0")
        self.assertEqual(money(1500), "$1.500")
        self.assertEqual(money(3480750), "$3.480.750")

    def test_format_clp_negative(self):
        self.assertEqual(format_clp(1990), "$1.990")
        self.assertEqual(format_clp(-1990), "-$1.990")


class LiquidationTests(unittest.TestCase):
    def test_commission_uses_gross_total(self):
        result = calculate_owner_liquidation(500000, 10, [])
        self.assertEqual(result["commission_amount"], 50000)
        self.assertEqual(result["owner_net"], 450000)

    def test_expenses_are_deducted(self):
        result = calculate_owner_liquidation(
            500000, 12, [{"amount": 25000}, {"amount": 5000}]
        )
        self.assertEqual(result["commission_amount"], 60000)
        self.assertEqual(result["expenses_total"], 30000)
        self.assertEqual(result["owner_net"], 410000)

    def test_commission_rounds_half_up(self):
        # 333 * 10% = 33.3 -> 33
        self.assertEqual(
            calculate_owner_liquidation(333, 10, [])["commission_amount"], 33
        )
        # 335 * 10% = 33.5 -> 34
        self.assertEqual(
            calculate_owner_liquidation(335, 10, [])["commission_amount"], 34
        )

    def test_zero_commission_is_allowed(self):
        result = calculate_owner_liquidation(100000, 0, [])
        self.assertEqual(result["owner_net"], 100000)

    def test_invalid_percentages(self):
        with self.assertRaises(ValueError):
            calculate_owner_liquidation(100000, -1, [])
        with self.assertRaises(ValueError):
            calculate_owner_liquidation(100000, 101, [])

    def test_negative_amounts_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_owner_liquidation(-1, 10, [])
        with self.assertRaises(ValueError):
            calculate_owner_liquidation(1000, 10, [{"amount": -5}])


class PaymentStatusTests(unittest.TestCase):
    def test_no_payment(self):
        self.assertEqual(payment_status(100000, 0), "Sin abono")

    def test_partial_payment(self):
        self.assertEqual(payment_status(100000, 50000), "Abono recibido")

    def test_full_payment(self):
        self.assertEqual(payment_status(100000, 100000), "Pagado completamente")

    def test_overpayment_counts_as_paid(self):
        self.assertEqual(payment_status(100000, 120000), "Pagado completamente")

    def test_cancelled_has_priority(self):
        self.assertEqual(payment_status(100000, 100000, cancelled=True), "Cancelada")

    def test_pending_never_negative(self):
        self.assertEqual(pending_amount(100000, 40000), 60000)
        self.assertEqual(pending_amount(100000, 150000), 0)

    def test_payment_totals_skip_voided(self):
        payments = [
            {"amount": 50000, "voided_at": None},
            {"amount": 30000, "voided_at": "2026-01-01"},
            {"amount": 20000, "voided_at": None},
        ]
        self.assertEqual(payment_totals(payments), 70000)


class DateTests(unittest.TestCase):
    def test_nights_between(self):
        self.assertEqual(
            nights_between(date(2026, 1, 1), date(2026, 1, 4)), 3
        )
        self.assertEqual(
            nights_between("2026-01-01", "2026-01-04"), 3
        )

    def test_invalid_ranges(self):
        self.assertTrue(validate_date_range("2026-01-01", "2026-01-04"))
        self.assertFalse(validate_date_range("2026-01-04", "2026-01-01"))
        self.assertFalse(validate_date_range("2026-01-01", "2026-01-01"))
        self.assertTrue(
            validate_date_range("2026-01-01", "2026-01-01", allow_same_day=True)
        )
        self.assertEqual(
            nights_between("2026-01-04", "2026-01-01"), 0
        )


class SeasonTests(unittest.TestCase):
    SEASONS = [
        {
            "id": 1, "start_date": date(2026, 1, 1),
            "end_date": date(2026, 3, 1),
            "price_per_night": 90000, "priority": 0,
            "department_id": None, "condo": None, "active": True,
        },
        {
            "id": 2, "start_date": date(2026, 2, 1),
            "end_date": date(2026, 2, 10),
            "price_per_night": 120000, "priority": 5,
            "department_id": 7, "condo": None, "active": True,
        },
    ]

    def test_general_season(self):
        self.assertEqual(
            season_price_for(self.SEASONS, "2026-01-15", 99, "Otro"), 90000
        )

    def test_department_season_wins(self):
        self.assertEqual(
            season_price_for(self.SEASONS, "2026-02-05", 7, "Serena"), 120000
        )

    def test_no_season_returns_none(self):
        self.assertIsNone(
            season_price_for(self.SEASONS, "2026-06-01", 7, "Serena")
        )

    def test_inactive_season_is_ignored(self):
        seasons = [dict(self.SEASONS[0], active=False)]
        self.assertIsNone(season_price_for(seasons, "2026-01-15"))


if __name__ == "__main__":
    unittest.main()
