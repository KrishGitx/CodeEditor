import os
import sys
import unittest
import io
import time
import json
from unittest.mock import MagicMock, patch

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from ExtensionManager import ExtensionManager, locate_executable
from FormatterManager import FormatterManager


from PySide6.QtCore import QCoreApplication, Qt


class TestSmartInstallCompleteRebuild(unittest.TestCase):
    def setUp(self):
        self.app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        self.ext_mgr = ExtensionManager()
        self.fmt_mgr = FormatterManager(extension_manager=self.ext_mgr)
        ExtensionManager.set_ai_provider(None)

    def tearDown(self):
        ExtensionManager.set_ai_provider(None)

    def test_01_formatter_missing_button_appears_click_invokes_ai(self):
        """TEST 1: Operation fails because formatter is missing -> Context created -> AI analysis invoked on click -> single_command."""
        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        # 1. Operation fails and context is created
        with patch("builtins.print", side_effect=capturing_print):
            ctx = self.ext_mgr.create_smart_install_context(
                operation="Format SQL document",
                operation_type="formatter",
                language="sql",
                file_path="query.sql",
                error_message="No formatter installed for sql."
            )

        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["operation"], "Format SQL document")
        self.assertEqual(ctx["language"], "sql")
        # Ensure command is NOT yet resolved in context
        self.assertNotIn("command", ctx)
        self.assertTrue(any("[SmartInstall] Entry point created" in l for l in logs))
        self.assertTrue(any("[SmartInstall] Entry point shown" in l for l in logs))

        # 2. Click Smart Install -> AI analysis is invoked
        def mock_ai_sql(prompt):
            return (
                "{\n"
                '  "resolutionType": "single_command",\n'
                '  "source": "ai",\n'
                '  "title": "Install SQLFluff",\n'
                '  "diagnosis": "SQLFluff formatter is not installed in the active Python environment.",\n'
                f'  "command": {json.dumps(f"\"{sys.executable}\" -m pip install --no-warn-script-location sqlfluff")},\n'
                '  "verificationCommand": "sqlfluff --version",\n'
                '  "tool": "sqlfluff",\n'
                '  "package": "sqlfluff",\n'
                '  "executable": "sqlfluff",\n'
                '  "retryOperation": true\n'
                "}"
            )

        ExtensionManager.set_ai_provider(mock_ai_sql)
        logs.clear()
        with patch("builtins.print", side_effect=capturing_print):
            proposal = self.ext_mgr.resolve_smart_install_context(ctx)

        self.assertTrue(any("[SmartInstall] AI analysis started" in l for l in logs))
        self.assertTrue(any("[SmartInstall] Sending request through existing AI backend" in l or "[SmartInstall] AI request sent" in l for l in logs))
        self.assertTrue(any("[SmartInstall] CustomApi response received" in l or "[SmartInstall] AI request completed" in l for l in logs))
        self.assertEqual(proposal["source"], "ai")
        self.assertEqual(proposal["resolutionType"], "single_command")
        self.assertIn("pip install", proposal["command"])

    def test_02_button_appears_before_any_command_exists(self):
        """TEST 2: Smart Install button exists before any command exists."""
        ctx = self.ext_mgr.create_smart_install_context(
            operation="Run rust file",
            operation_type="runner",
            language="rust",
            file_path="main.rs"
        )
        self.assertIsNotNone(ctx)
        self.assertFalse(ctx.get("command", False))
        # Context exists, which determines button visibility independently of command availability
        self.assertTrue(len(ctx["operation"]) > 0)
        self.assertEqual(ctx["language"], "rust")

    def test_03_ai_returns_single_command(self):
        """TEST 3: AI returns single_command -> command displayed, Install button action, no fake fallback."""
        def mock_ai(prompt):
            return (
                "{\n"
                '  "resolutionType": "single_command",\n'
                '  "source": "ai",\n'
                '  "title": "Install Prettier",\n'
                '  "diagnosis": "Prettier executable is missing.",\n'
                '  "explanation": "Installs Prettier code formatter globally via npm.",\n'
                '  "command": "npm install -g prettier",\n'
                '  "verificationCommand": "prettier --version",\n'
                '  "tool": "prettier",\n'
                '  "package": "prettier",\n'
                '  "executable": "prettier"\n'
                "}"
            )
        ExtensionManager.set_ai_provider(mock_ai)
        ctx = self.ext_mgr.create_smart_install_context(operation="Format JavaScript", operation_type="formatter", language="javascript")
        proposal = self.ext_mgr.resolve_smart_install_context(ctx)

        self.assertEqual(proposal["resolutionType"], "single_command")
        self.assertEqual(proposal["source"], "ai")
        self.assertEqual(proposal["command"], "npm install -g prettier")
        self.assertEqual(proposal["verifyCommand"], "prettier --version")

    def test_04_ai_returns_complex_setup(self):
        """TEST 4: AI returns complex_setup -> setup plan displayed, Approve Setup action."""
        def mock_ai_complex(prompt):
            return (
                "{\n"
                '  "resolutionType": "complex_setup",\n'
                '  "source": "ai",\n'
                '  "title": "Setup Embedded C++ Toolchain",\n'
                '  "diagnosis": "Toolchain requires multiple environment configuration steps.",\n'
                '  "explanation": "Multiple steps are needed to configure ARM toolchain.",\n'
                '  "steps": [\n'
                '    "winget install --id Arm.GnuArmEmbeddedToolchain -e",\n'
                '    "winget install --id Ninja-build.Ninja -e",\n'
                '    "cmake -B build -G Ninja"\n'
                '  ],\n'
                '  "verificationCommand": "arm-none-eabi-gcc --version"\n'
                "}"
            )
        ExtensionManager.set_ai_provider(mock_ai_complex)
        ctx = self.ext_mgr.create_smart_install_context(operation="Build firmware", operation_type="compiler", language="cpp")
        proposal = self.ext_mgr.resolve_smart_install_context(ctx)

        self.assertEqual(proposal["resolutionType"], "complex_setup")
        self.assertEqual(proposal["source"], "ai")
        self.assertEqual(len(proposal["steps"]), 3)
        self.assertIn("Arm.GnuArmEmbeddedToolchain", proposal["steps"][0])

    def test_05_ai_cannot_resolve(self):
        """TEST 5: AI says issue cannot safely be resolved -> cannot_resolve, no install command."""
        def mock_ai_cannot(prompt):
            return (
                "{\n"
                '  "resolutionType": "cannot_resolve",\n'
                '  "source": "ai",\n'
                '  "title": "Proprietary Driver Missing",\n'
                '  "diagnosis": "Hardware vendor license requires manual web download.",\n'
                '  "explanation": "Automated installation is not permitted by license."\n'
                "}"
            )
        ExtensionManager.set_ai_provider(mock_ai_cannot)
        ctx = self.ext_mgr.create_smart_install_context(operation="Connect to DB", operation_type="driver", language="sql")
        proposal = self.ext_mgr.resolve_smart_install_context(ctx)

        self.assertEqual(proposal["resolutionType"], "cannot_resolve")
        self.assertEqual(proposal["source"], "ai")
        self.assertEqual(proposal["command"], "")
        self.assertIn("manual web download", proposal["diagnosis"])

    def test_06_ai_provider_genuinely_fails(self):
        """TEST 6: AI provider genuinely fails -> AI request was actually attempted -> ai_unavailable."""
        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        def failing_ai(prompt):
            raise ConnectionError("AI backend timeout after 10s")

        ExtensionManager.set_ai_provider(failing_ai)
        ctx = self.ext_mgr.create_smart_install_context(operation="Resolve tool", operation_type="cli", language="unknown")
        
        with patch("builtins.print", side_effect=capturing_print):
            proposal = self.ext_mgr.resolve_smart_install_context(ctx)

        self.assertTrue(any("[SmartInstall] AI analysis started" in l for l in logs))
        self.assertTrue(any("[SmartInstall] Sending request through existing AI backend" in l or "[SmartInstall] AI request sent" in l for l in logs))
        self.assertTrue(any("AI backend timeout" in l for l in logs))
        self.assertEqual(proposal["source"], "ai_unavailable")
        self.assertEqual(proposal["resolutionType"], "cannot_resolve")
        self.assertEqual(proposal["command"], "")

    def test_07_ai_not_called_yet_is_not_ai_unavailable(self):
        """TEST 7: Before AI is called, context state is NOT ai_unavailable."""
        ctx = self.ext_mgr.create_smart_install_context(
            operation="Format file",
            operation_type="formatter",
            language="csharp"
        )
        self.assertNotIn("source", ctx)
        self.assertNotEqual(ctx.get("source"), "ai_unavailable")

    def test_08_invalid_ai_response_triggers_corrective_retry(self):
        """TEST 8: AI returns invalid package/JSON -> One corrective retry -> If valid, accepted."""
        calls = []
        def mock_ai_flaky(prompt):
            calls.append(prompt)
            if len(calls) == 1:
                # First response has invalid multi-word package hallucination
                return (
                    "{\n"
                    '  "resolutionType": "single_command",\n'
                    '  "package": "csharp formatter tool package",\n'
                    '  "command": "dotnet tool install -g csharp formatter tool package"\n'
                    "}"
                )
            else:
                # Corrective retry gives valid package
                return (
                    "{\n"
                    '  "resolutionType": "single_command",\n'
                    '  "title": "Install CSharpier",\n'
                    '  "package": "csharpier",\n'
                    '  "executable": "dotnet-csharpier",\n'
                    '  "command": "dotnet tool install -g csharpier",\n'
                    '  "verificationCommand": "dotnet csharpier --version"\n'
                    "}"
                )

        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        ExtensionManager.set_ai_provider(mock_ai_flaky)
        ctx = self.ext_mgr.create_smart_install_context(operation="Format C#", operation_type="formatter", language="csharp")
        with patch("builtins.print", side_effect=capturing_print):
            proposal = self.ext_mgr.resolve_smart_install_context(ctx)

        self.assertEqual(len(calls), 2)
        self.assertTrue(any("[SmartInstall] Corrective AI retry started" in l for l in logs))
        self.assertEqual(proposal["resolutionType"], "single_command")
        self.assertEqual(proposal["command"], "dotnet tool install -g csharpier")
        self.assertEqual(proposal["packageName"], "csharpier")

    def test_09_csharp_missing_formatter_strictly_isolates_and_never_falls_back_to_clang(self):
        """TEST 9: C# missing formatter strictly isolates C# tooling and never falls back to clang-format."""
        def mock_ai_bad_cross(prompt):
            return (
                "{\n"
                '  "resolutionType": "single_command",\n'
                '  "package": "clang-format",\n'
                '  "command": "pip install clang-format"\n'
                "}"
            )
        ExtensionManager.set_ai_provider(mock_ai_bad_cross)
        ctx = self.ext_mgr.create_smart_install_context(operation="Format C#", operation_type="formatter", language="csharp")
        proposal = self.ext_mgr.resolve_smart_install_context(ctx)

        # Cross-language validation failed and corrective prompt was sent; since mock persisted invalid, cannot_resolve
        self.assertEqual(proposal["resolutionType"], "cannot_resolve")
        self.assertEqual(proposal["command"], "")
        self.assertNotIn("clang-format", proposal["command"])

    def test_10_java_application_error_does_not_misdiagnose_installed_java(self):
        """TEST 10: Java is installed but reports JDBC driver error -> do NOT try to install Java JDK."""
        ctx = self.ext_mgr.create_smart_install_context(
            operation="Run Java App",
            operation_type="runtime",
            language="java",
            file_path="App.java",
            command_attempted="java App",
            exit_code=1,
            stderr="java.sql.SQLException: No suitable driver found for jdbc:postgresql://localhost:5432/db"
        )
        prompt = self.ext_mgr.generate_smart_install_prompt(context=ctx)
        self.assertIn("java.sql.SQLException", prompt)
        self.assertIn("Do NOT recommend software that is already proven to be installed", prompt)

    def test_11_successful_installation_verification_and_retry(self):
        """TEST 11: Successful installation -> verify -> refresh -> retry original operation -> success."""
        completed_results = []
        self.ext_mgr.smartInstallCompleted.connect(
            lambda name, ok, msg, retry: completed_results.append((name, ok, msg, retry)),
            type=Qt.ConnectionType.DirectConnection
        )

        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        mock_ai = MagicMock()
        mock_ai.ask.return_value = "SUCCESS\nTool verified."
        self.ext_mgr.ai_backend = mock_ai

        with patch("builtins.print", side_effect=capturing_print):
            ret = self.ext_mgr.execute_smart_install_command(
                tool_name="test-helper-tool",
                command=f'"{sys.executable}" -c "pass"',
                executable="python",
                retry_action="format",
                file_path="test.py",
                verify_command=f'"{sys.executable}" --version'
            )
            self.assertTrue(ret)
            start_t = time.time()
            while time.time() - start_t < 6.0 and len(completed_results) == 0:
                if self.app:
                    self.app.processEvents()
                time.sleep(0.05)
            if self.app:
                self.app.processEvents()

        self.assertTrue(len(completed_results) > 0)
        tool_name, success, msg, retry_action = completed_results[0]
        self.assertTrue(success)
        self.assertEqual(retry_action, "format")
        self.assertTrue(any("[SmartInstall] User approved install" in l for l in logs))
        self.assertTrue(any("[SmartInstall] Installation started" in l for l in logs))
        self.assertTrue(any("[SmartInstall] Verification started" in l for l in logs))
        self.assertTrue(any("[SmartInstall] Cache invalidation" in l for l in logs))
        self.assertTrue(any("[SmartInstall] Environment refresh" in l for l in logs))
        self.assertTrue(any("[SmartInstall] Original operation retry: format" in l for l in logs))
        self.assertTrue(any("[SmartInstall] Retry result: triggered" in l for l in logs))


if __name__ == "__main__":
    unittest.main()
