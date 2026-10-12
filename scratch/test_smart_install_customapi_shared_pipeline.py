"""
test_smart_install_customapi_shared_pipeline.py - Verification that Smart Install and Ask AI share the exact same AI pipeline
"""

import sys
import os
import unittest
import json
from unittest.mock import patch, MagicMock

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from PySide6.QtCore import QCoreApplication
from AIBackend import AIBackend
from ExtensionManager import ExtensionManager


class TestSmartInstallCustomApiSharedPipeline(unittest.TestCase):
    def setUp(self):
        self.app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        self.ai_backend = AIBackend()
        self.ext_mgr = ExtensionManager()
        self.ext_mgr.ai_backend = self.ai_backend
        AIBackend.set_ai_provider(None)

    def tearDown(self):
        AIBackend.set_ai_provider(None)

    def test_01_smart_install_and_ask_ai_share_same_centralized_ai_backend(self):
        """Smart Install and Ask AI route through the exact same centralized AIBackend instance."""
        calls = []
        def mock_customapi(prompt):
            calls.append(prompt)
            if "format sql" in prompt.lower() or "sqlfluff" in prompt.lower():
                return json.dumps({
                    "resolutionType": "single_command",
                    "source": "ai",
                    "title": "Install SQLFluff",
                    "diagnosis": "SQLFluff is missing",
                    "explanation": "Installs SQLFluff via pip",
                    "command": "python -m pip install sqlfluff",
                    "verificationCommand": "sqlfluff --version",
                    "tool": "sqlfluff",
                    "package": "sqlfluff",
                    "executable": "sqlfluff"
                })
            return "This is Ask AI answering a standard question."

        AIBackend.set_ai_provider(mock_customapi)

        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        # 1. Test Smart Install query through ExtensionManager
        ctx = self.ext_mgr.create_smart_install_context(
            operation="Format SQL",
            operation_type="formatter",
            language="sql",
            file_path="query.sql",
            executable="sqlfluff"
        )
        with patch("builtins.print", side_effect=capturing_print):
            proposal = self.ext_mgr.resolve_smart_install_context(ctx)

        # Verify logs for Smart Install
        self.assertTrue(any("[SmartInstall] AI analysis started" in l for l in logs))
        self.assertTrue(any("[SmartInstall] Sending request through existing AI backend" in l for l in logs))
        self.assertTrue(any("[SmartInstall] CustomApi request sent" in l for l in logs))
        self.assertTrue(any("[SmartInstall] CustomApi response received" in l for l in logs))
        self.assertEqual(proposal["source"], "ai")
        self.assertEqual(proposal["command"], "python -m pip install sqlfluff")

        # 2. Test Ask AI query through the exact same AIBackend
        ask_ai_results = []
        self.ai_backend.messageReceived.connect(lambda mid, role, content: ask_ai_results.append((role, content)))
        self.ai_backend.send_message("What is DGX Studio?")

        import time
        time.sleep(0.5)
        self.app.processEvents()

        self.assertTrue(len(ask_ai_results) >= 2)
        # Assistant responded using the same provider
        self.assertEqual(ask_ai_results[-1][0], "assistant")
        self.assertIn("This is Ask AI answering a standard question.", ask_ai_results[-1][1])
        # Verify 2 calls were routed to the shared AI pipeline
        self.assertEqual(len(calls), 2)

    def test_02_customapi_failure_logs_and_returns_ai_unavailable_without_fake_fallback(self):
        """When CustomApi fails, Smart Install logs the exact failure and returns ai_unavailable without fake AI."""
        def failing_ai(prompt):
            raise ConnectionError("CustomApi Playwright connection refused: target closed")

        AIBackend.set_ai_provider(failing_ai)

        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        ctx = self.ext_mgr.create_smart_install_context(
            operation="Format unknown",
            operation_type="formatter",
            language="unknown"
        )
        with patch("builtins.print", side_effect=capturing_print):
            proposal = self.ext_mgr.resolve_smart_install_context(ctx)

        self.assertTrue(any("[SmartInstall] Sending request through existing AI backend" in l for l in logs))
        self.assertTrue(any("[SmartInstall] CustomApi request failed: CustomApi Playwright connection refused" in l for l in logs))
        self.assertEqual(proposal["source"], "ai_unavailable")
        self.assertEqual(proposal["resolutionType"], "cannot_resolve")
        self.assertEqual(proposal["command"], "")
        self.assertIn("CustomApi Playwright connection refused", proposal["explanation"])

    def test_03_ready_state_is_not_ai_unavailable(self):
        """Before clicking analyze, the context has NOT queried AI and is NOT ai_unavailable."""
        ctx = self.ext_mgr.create_smart_install_context(
            operation="Run Rust",
            operation_type="runner",
            language="rust",
            file_path="main.rs"
        )
        self.assertNotIn("source", ctx)
        self.assertFalse(ctx.get("command"))


if __name__ == "__main__":
    unittest.main()
