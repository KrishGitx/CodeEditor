import os
import sys
import unittest
import shutil
import subprocess

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from ExtensionManager import ExtensionManager, resolve_python_tool, resolve_dotnet_global_tool, locate_executable
from FormatterManager import FormatterManager


class TestAiPoweredSmartInstallSystem(unittest.TestCase):
    def setUp(self):
        self.ext_mgr = ExtensionManager()
        self.fmt_mgr = FormatterManager(extension_manager=self.ext_mgr)
        # Reset custom AI provider before each test
        ExtensionManager.set_ai_provider(None)

    def tearDown(self):
        ExtensionManager.set_ai_provider(None)

    def test_01_ai_unavailable_returns_authentic_state_and_no_fake_ai(self):
        """TEST H: When AI is unavailable, return authentic ai_unavailable state without faking AI or badge."""
        ExtensionManager.set_ai_provider(None)
        
        # Request Smart Install for missing tool when AI is offline
        prop = self.ext_mgr.suggest_smart_install("formatter", "sqlfluff", "sql", "sql", "test.sql")
        self.assertIsNotNone(prop)
        self.assertEqual(prop["source"], "ai_unavailable")
        self.assertNotEqual(prop["source"], "ai")
        self.assertEqual(prop["resolutionType"], "cannot_resolve")
        self.assertEqual(prop["command"], "")
        self.assertIn("AI is unavailable", prop["description"])

    def test_02_genuine_ai_resolution_single_command(self):
        """TEST I & TEST A: Genuine AI recommendation with source='ai' and verified execution."""
        def mock_ai_sql(prompt):
            self.assertIn("sqlfluff", prompt.lower())
            return (
                "Tool: SQLFluff (SQL Formatter)\n"
                "Dependency Type: formatter\n"
                "Package: sqlfluff\n"
                "Executable: sqlfluff\n"
                "Resolution Type: single_command\n"
                f'Command: "{sys.executable}" -m pip install --no-warn-script-location sqlfluff\n'
                "Verify: sqlfluff --version\n"
                "Explanation: Installs SQLFluff, the standard SQL linter and code formatter via pip."
            )

        ExtensionManager.set_ai_provider(mock_ai_sql)
        prop = self.ext_mgr.suggest_smart_install("formatter", "sqlfluff", "sql", "sql", "test.sql")

        self.assertEqual(prop["source"], "ai")
        self.assertEqual(prop["resolutionType"], "single_command")
        self.assertEqual(prop["packageName"], "sqlfluff")
        self.assertEqual(prop["executable"], "sqlfluff")
        self.assertIn("pip install", prop["command"])
        self.assertEqual(prop["retryAction"], "format")

    def test_03_csharp_formatter_ai_resolution_and_isolation(self):
        """TEST B & TEST F: C# formatter resolves to CSharpier via AI and NEVER uses clang-format."""
        def mock_ai_cs(prompt):
            self.assertIn("csharp", prompt.lower())
            return (
                "Tool: CSharpier (C# Formatter)\n"
                "Dependency Type: formatter\n"
                "Package: csharpier\n"
                "Executable: dotnet-csharpier\n"
                "Resolution Type: single_command\n"
                "Command: dotnet tool install -g csharpier\n"
                "Verify: dotnet csharpier --version\n"
                "Explanation: Installs CSharpier via .NET global tool."
            )

        ExtensionManager.set_ai_provider(mock_ai_cs)
        prop = self.ext_mgr.suggest_smart_install("formatter", "csharpier", "csharp", "cs", "Program.cs")

        self.assertEqual(prop["source"], "ai")
        self.assertEqual(prop["packageName"], "csharpier")
        self.assertIn("dotnet tool install", prop["command"])
        self.assertNotIn("clang-format", prop["command"])

        # Ensure FormatterManager never falls back to clang-format
        cs_res = self.fmt_mgr.format_code("csharp", "Program.cs", "class Foo { int x; }")
        self.assertNotIn("clang-format", cs_res.get("message", "").lower())

    def test_04_java_runtime_resolution_and_executable_check(self):
        """TEST C & TEST D: Java runtime check preserves working runtime and resolves missing runtime via AI."""
        # 1. Java runtime existing check
        is_java_present = bool(locate_executable("java"))
        if is_java_present:
            self.assertTrue(self.ext_mgr.is_executable_installed("java"))

        # 2. AI resolution when java is requested
        def mock_ai_java(prompt):
            return (
                "Tool: Java Development Kit (JDK)\n"
                "Dependency Type: runtime\n"
                "Package: Oracle.JDK.21\n"
                "Executable: java\n"
                "Resolution Type: single_command\n"
                "Command: winget install --id Oracle.JDK.21 -e\n"
                "Verify: java --version\n"
                "Explanation: Installs Java Development Kit for executing Java applications."
            )

        ExtensionManager.set_ai_provider(mock_ai_java)
        prop = self.ext_mgr.suggest_smart_install("runtime", "java", "java", "java", "Main.java")
        self.assertEqual(prop["source"], "ai")
        self.assertEqual(prop["dependencyType"], "runtime")
        self.assertEqual(prop["retryAction"], "run")

    def test_05_unknown_dependency_safety(self):
        """TEST G: Unknown dependency with AI cannot_resolve returns safe failure state without arbitrary commands."""
        def mock_ai_unk(prompt):
            return (
                "Tool: unknown-custom-tool\n"
                "Dependency Type: other\n"
                "Package: unknown-custom-tool\n"
                "Executable: unknown-custom-tool\n"
                "Resolution Type: cannot_resolve\n"
                "Command: \n"
                "Verify: unknown-custom-tool --version\n"
                "Explanation: Could not determine how to install this tool."
            )

        ExtensionManager.set_ai_provider(mock_ai_unk)
        prop = self.ext_mgr.suggest_smart_install("other", "unknown-custom-tool", "custom", "xyz")
        self.assertEqual(prop["source"], "ai")
        self.assertEqual(prop["resolutionType"], "cannot_resolve")
        self.assertEqual(prop["command"], "")

    def test_06_validation_reprompt_without_silent_hardcoded_substitution(self):
        """Verify invalid AI response is re-prompted and blocked if still invalid rather than hardcoding."""
        attempts = []

        def mock_ai_flaky(prompt):
            attempts.append(prompt)
            if len(attempts) == 1:
                # First attempt returns invalid package name with spaces
                return (
                    "Tool: SQL Formatter\n"
                    "Dependency Type: formatter\n"
                    "Package: sql formatter tool\n"
                    "Executable: sqlformat\n"
                    "Resolution Type: single_command\n"
                    "Command: pip install sql formatter tool\n"
                    "Verify: sqlformat --version\n"
                    "Explanation: Installs sql formatter."
                )
            else:
                # Re-prompted second attempt returns corrected package
                return (
                    "Tool: SQLFluff (SQL Formatter)\n"
                    "Dependency Type: formatter\n"
                    "Package: sqlfluff\n"
                    "Executable: sqlfluff\n"
                    "Resolution Type: single_command\n"
                    f'Command: "{sys.executable}" -m pip install --no-warn-script-location sqlfluff\n'
                    "Verify: sqlfluff --version\n"
                    "Explanation: Installs SQLFluff via pip."
                )

        ExtensionManager.set_ai_provider(mock_ai_flaky)
        prop = self.ext_mgr.suggest_smart_install("formatter", "sqlfluff", "sql", "sql", "test.sql")

        self.assertEqual(len(attempts), 2)
        self.assertEqual(prop["source"], "ai")
        self.assertEqual(prop["packageName"], "sqlfluff")
        self.assertEqual(prop["resolutionType"], "single_command")

    def test_07_failure_context_analysis(self):
        """Verify suggest_smart_install_for_failure passes full error and command context to AI."""
        received_prompt = []

        def mock_ai_failure(prompt):
            received_prompt.append(prompt)
            return (
                "Tool: Python Package pytest\n"
                "Dependency Type: package\n"
                "Package: pytest\n"
                "Executable: pytest\n"
                "Resolution Type: single_command\n"
                f'Command: "{sys.executable}" -m pip install pytest\n'
                "Verify: pytest --version\n"
                "Explanation: Installs missing pytest test runner package."
            )

        ExtensionManager.set_ai_provider(mock_ai_failure)
        err_msg = "ModuleNotFoundError: No module named 'pytest'"
        prop = self.ext_mgr.suggest_smart_install_for_failure(
            operation="Test Runner",
            error_output=err_msg,
            exit_code=1,
            failed_command=f'"{sys.executable}" -m pytest test_suite.py',
            lang_id="python",
            ext="py",
            file_path="test_suite.py"
        )

        self.assertTrue(len(received_prompt) > 0)
        self.assertIn("ModuleNotFoundError", received_prompt[0])
        self.assertIn("Test Runner", received_prompt[0])
        self.assertEqual(prop["source"], "ai")
        self.assertEqual(prop["packageName"], "pytest")


if __name__ == "__main__":
    unittest.main()
