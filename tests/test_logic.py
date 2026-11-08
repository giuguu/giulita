"""Pruebas de las funciones puras de cálculo.

Se ejecutan sin Streamlit ni conexión a la base de datos:

    python -m unittest discover -s tests -v
"""

import unittest
from datetime import date

from logic import (
    BANK_ACCOUNT_TYPES,
    BANK_NAMES,
    bank_copy_text,
    bank_option_label,
    calculate_owner_liquidation,
    canonical_bank_name,
    detect_bank_account_type,
    format_clp,
    mask_bank_account,
    money,
    nights_between,
    payment_status,
    payment_totals,
    pending_amount,
    season_price_for,
    validate_bank_details,
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


class BankDataTests(unittest.TestCase):
    def test_known_banks_are_canonical(self):
        self.assertEqual(canonical_bank_name("Banco de Chile"), "Banco de Chile")
        self.assertEqual(canonical_bank_name("BancoEstado"), "BancoEstado")
        self.assertEqual(canonical_bank_name("Coopeuch"), "Coopeuch")
        self.assertEqual(canonical_bank_name("Mercado Pago"), "Mercado Pago")

    def test_legacy_bank_names_are_recognized(self):
        self.assertEqual(
            canonical_bank_name("Santander cta/cte"), "Banco Santander"
        )
        self.assertEqual(
            canonical_bank_name("Banco estado  cta/cte"), "BancoEstado"
        )
        self.assertEqual(
            canonical_bank_name("De Chile / corriente"), "Banco de Chile"
        )
        self.assertEqual(
            canonical_bank_name("Scotiabank corriente"), "Banco Scotiabank"
        )
        self.assertIsNone(canonical_bank_name("Banco inventado"))

    def test_account_type_is_only_inferred_when_explicit(self):
        self.assertEqual(
            detect_bank_account_type("Santander cta/cte"), "Cuenta Corriente"
        )
        self.assertEqual(
            detect_bank_account_type("BancoEstado cuenta RUT"), "Cuenta RUT"
        )
        self.assertEqual(
            detect_bank_account_type("Banco de Chile"), ""
        )

    def test_account_number_is_masked(self):
        self.assertEqual(mask_bank_account("123456789012"), "********9012")
        self.assertEqual(mask_bank_account("1234"), "****")
        self.assertEqual(mask_bank_account(""), "")

    def test_bank_copy_text_keeps_full_account_and_labels(self):
        text = bank_copy_text(
            "Ana Pérez", "Banco de Chile", "Cuenta Corriente",
            "123456789012", "Ana Pérez",
        )
        self.assertEqual(
            text,
            "Propietario: Ana Pérez\n"
            "Banco: Banco de Chile\n"
            "Tipo de cuenta: Cuenta Corriente\n"
            "Número de cuenta: 123456789012\n"
            "Titular: Ana Pérez",
        )

    def test_bank_copy_text_omits_empty_fields(self):
        self.assertEqual(
            bank_copy_text("Ana Pérez", "Efectivo"),
            "Propietario: Ana Pérez\nBanco: Efectivo",
        )

    def test_bank_validation_allows_empty_or_complete(self):
        self.assertIsNone(validate_bank_details("", "", ""))
        self.assertIsNone(
            validate_bank_details("BancoEstado", "Cuenta RUT", "12345678")
        )
        self.assertIsNone(validate_bank_details("Efectivo", "", ""))

    def test_bank_validation_rejects_incomplete_data(self):
        self.assertIn(
            "Selecciona el banco",
            validate_bank_details("", "Cuenta RUT", "12345678"),
        )
        self.assertIn(
            "tipo de cuenta",
            validate_bank_details("BancoEstado", "", "12345678"),
        )
        self.assertIn(
            "número de cuenta",
            validate_bank_details("BancoEstado", "Cuenta RUT", ""),
        )
        self.assertIn(
            "al menos 4",
            validate_bank_details("BancoEstado", "Cuenta RUT", "123"),
        )
        self.assertIn(
            "lista",
            validate_bank_details(
                "Banco inventado", "Otra", "1234",
                allowed_banks=BANK_NAMES,
            ),
        )

    def test_bank_options_have_categories(self):
        self.assertIn("🏦 Banco de Chile", bank_option_label("Banco de Chile"))
        self.assertIn("cooperativas", bank_option_label("Coopeuch"))
        self.assertIn("entidades financieras", bank_option_label("Tenpo"))
        self.assertIn("Cuenta RUT", BANK_ACCOUNT_TYPES)


if __name__ == "__main__":
    unittest.main()
