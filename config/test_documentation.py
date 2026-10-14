import ast
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ProductionDocumentationTests(SimpleTestCase):
    """Keep maintainability documentation present as production code grows."""

    excluded_directories = {"migrations", "staticfiles", "venv"}

    def production_python_files(self):
        """Yield application Python files while excluding generated and test code."""

        for path in Path(settings.BASE_DIR).rglob("*.py"):
            if self.excluded_directories.intersection(path.parts):
                continue
            if path.name == "tests.py" or path.name.startswith("test_"):
                continue
            yield path

    def test_production_functions_and_classes_have_docstrings(self):
        """Report every undocumented production function or meaningful class."""

        missing = []
        for path in self.production_python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                is_function = isinstance(
                    node,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                )
                is_meaningful_class = (
                    isinstance(node, ast.ClassDef) and node.name != "Meta"
                )
                if (is_function or is_meaningful_class) and not ast.get_docstring(node):
                    relative_path = path.relative_to(settings.BASE_DIR)
                    missing.append(f"{relative_path}:{node.lineno} {node.name}")

        self.assertEqual(
            missing,
            [],
            "Production code is missing maintainability docstrings:\n"
            + "\n".join(missing),
        )
