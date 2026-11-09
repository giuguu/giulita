"""Verifica que app.py y logic.py mantengan el mismo contrato de imports.

Este test reproduce el fallo de despliegue:

    ImportError: cannot import name 'BANK_ACCOUNT_TYPES' from 'logic'

Se ejecuta sin Streamlit ni conexión a la base de datos.
"""

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logic  # noqa: E402  (debe importarse después de ajustar sys.path)


def _logic_imports_from_app():
    """Nombres que app.py importa desde logic.py, leídos del AST."""
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "logic":
            names.extend(alias.name for alias in node.names)
    return names


class AppLogicContractTests(unittest.TestCase):
    def test_app_imports_only_names_defined_in_logic(self):
        imported = _logic_imports_from_app()
        self.assertTrue(imported, "app.py no importa nada desde logic.py")
        missing = sorted(name for name in imported if not hasattr(logic, name))
        self.assertEqual(
            missing,
            [],
            "app.py importa nombres que logic.py no define: "
            + ", ".join(missing),
        )

    def test_bank_data_api_is_exported(self):
        for name in (
            "BANK_GROUPS",
            "BANK_NAMES",
            "BANK_CATEGORY",
            "BANK_ACCOUNT_TYPES",
        ):
            self.assertIn(name, logic.__all__)
            self.assertTrue(hasattr(logic, name))

        self.assertIn("Cuenta RUT", logic.BANK_ACCOUNT_TYPES)
        self.assertIn("BancoEstado", logic.BANK_NAMES)

    def test_every_declared_export_exists(self):
        missing = sorted(
            name for name in logic.__all__ if not hasattr(logic, name)
        )
        self.assertEqual(missing, [], "logic.py exporta nombres inexistentes")


if __name__ == "__main__":
    unittest.main()
