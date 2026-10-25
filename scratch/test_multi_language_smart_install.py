import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager


class TestMultiLanguageSmartInstallAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.em = ExtensionManager()
        cls.fm = FormatterManager(cls.em)
        cls.em.set_formatter_manager(cls.fm)

    def test_01_language_extension_coverage(self):
        """Verifies all required languages have dedicated extensions or resolvers."""
        expected_langs = [
            ("python", "test.py"),
            ("javascript", "test.js"),
            ("typescript", "test.ts"),
            ("html", "test.html"),
            ("css", "test.css"),
            ("json", "test.json"),
            ("cpp", "test.cpp"),
            ("c", "test.c"),
            ("rust", "test.rs"),
            ("go", "test.go"),
            ("qml", "test.qml"),
            ("sql", "test.sql"),
            ("csharp", "test.cs"),
            ("java", "test.java"),
        ]

        for lang, file_name in expected_langs:
            res = self.fm.format_code(lang, file_name, "   \n")
            # Must return a valid dict with available and success keys
            self.assertIn("available", res, f"Language {lang} must return availability status")
            self.assertIn("success", res, f"Language {lang} must return success status")

    def test_02_json_built_in_formatter(self):
        """JSON is formatted built-in without requiring external CLI."""
        raw_json = '{"b": 2, "a": 1}'
        res = self.fm.format_code("json", "test.json", raw_json, tab_size=2)
        self.assertTrue(res["success"])
        self.assertTrue(res["available"])
        self.assertIn('"a": 1', res["formatted"])

    def test_03_sql_fluff_resolution(self):
        """SQL format requests route to SQLFluff rather than rustfmt or clang-format."""
        res = self.fm.format_code("sql", "test.sql", "select 1 from dual;")
        self.assertIn("dependency", res)
        self.assertEqual(res["dependency"], "sqlfluff")
        if not res["available"]:
            self.assertIn("sqlfluff", res["installCommand"].lower())
            self.assertNotIn("rustfmt", res["installCommand"].lower())

    def test_04_csharp_csharpier_resolution(self):
        """C# format requests route to CSharpier rather than rustfmt or clang-format."""
        res = self.fm.format_code("csharp", "Program.cs", "class P { static void Main(){} }")
        self.assertIn("dependency", res)
        self.assertEqual(res["dependency"], "csharpier")
        if not res["available"]:
            self.assertIn("csharpier", res["installCommand"].lower())
            self.assertNotIn("rustfmt", res["installCommand"].lower())

    def test_05_smart_install_proposals_language_aware(self):
        """Smart Install generates non-Rust specific proposals for each language."""
        languages_and_tools = [
            ("python", "autopep8"),
            ("javascript", "prettier"),
            ("go", "gofmt"),
            ("rust", "rustfmt"),
            ("cpp", "clang-format"),
            ("sql", "sqlfluff"),
            ("csharp", "csharpier")
        ]

        from unittest.mock import MagicMock
        old_ai = getattr(self.em, "ai_backend", None)
        mock_backend = MagicMock()
        self.em.ai_backend = mock_backend

        install_cmds = {
            "python": "pip install autopep8",
            "javascript": "npm install -g prettier",
            "go": "go install golang.org/x/tools/cmd/gofmt@latest",
            "rust": "cargo install rustfmt",
            "cpp": "winget install LLVM.LLVM",
            "sql": "pip install sqlfluff",
            "csharp": "dotnet tool install -g csharpier"
        }

        try:
            for lang, tool in languages_and_tools:
                cmd = install_cmds.get(lang, f"pip install {tool}")
                mock_backend.ask.return_value = (
                    f'{{\n'
                    f'  "resolutionType": "single_command",\n'
                    f'  "tool": "{tool}",\n'
                    f'  "package": "{tool}",\n'
                    f'  "executable": "{tool}",\n'
                    f'  "command": "{cmd}",\n'
                    f'  "verificationCommand": "{tool} --version",\n'
                    f'  "explanation": "Install {tool} for {lang}."\n'
                    f'}}'
                )
                prop = self.em.suggest_smart_install("formatter", f"{lang} formatter", lang, f".{lang}", f"test.{lang}")
                self.assertEqual(prop["toolName"], tool)
                self.assertEqual(prop["command"], cmd)
                self.assertEqual(prop["languageId"], lang)
                if lang != "rust":
                    self.assertNotIn("rustfmt", prop["command"].lower())
        finally:
            self.em.ai_backend = old_ai

    def test_06_rustfmt_invoked_with_emit_stdout(self):
        """Rust extension defines --emit=stdout rather than --check for actual formatting."""
        ext = self.em.get_extension("dgx.rust")
        self.assertIsNotNone(ext)
        self.assertIsNotNone(ext.formatter)
        args = ext.formatter.get("args", [])
        self.assertIn("--emit=stdout", args)
        self.assertNotIn("--check", args)


if __name__ == "__main__":
    unittest.main()
