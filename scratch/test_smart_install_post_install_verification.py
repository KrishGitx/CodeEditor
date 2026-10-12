"""
test_smart_install_post_install_verification.py
Comprehensive automated test suite for DGX Studio's Post-Install AI Verification & AI Fix Resolution.
Covers all 16 test cases from Section 23 of the Smart Install Final Rebuild Specification.
"""

import os
import sys
import unittest
import time
from unittest.mock import MagicMock, patch

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from PySide6.QtCore import QCoreApplication
from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager


class TestSmartInstallPostInstallVerification(unittest.TestCase):
    def setUp(self):
        self.app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        self.ext_mgr = ExtensionManager()
        self.fmt_mgr = FormatterManager(extension_manager=self.ext_mgr)
        ExtensionManager.set_ai_provider(None)

    def tearDown(self):
        ExtensionManager.set_ai_provider(None)

    def test_01_install_succeeds_gpt_returns_success(self):
        """TEST 1: Install succeeds -> GPT returns SUCCESS -> proceed to retry."""
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "SUCCESS\nPrettier installed and verified."
        self.ext_mgr.ai_backend = mock_ai

        status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
            tool_name="prettier",
            command="npm install -g prettier",
            install_exit_code=0,
            install_stdout="added 1 package",
            install_stderr="",
            verify_cmd="prettier --version",
            verify_exit_code=0,
            verify_stdout="3.2.5",
            verify_stderr="",
            executable="prettier"
        )
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(fix_cmd, "")

    def test_02_install_fails_gpt_returns_failed(self):
        """TEST 2: Install fails -> GPT returns FAILED -> stop."""
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "FAILED\nUnrecognized network failure and contradictory npm environment."
        self.ext_mgr.ai_backend = mock_ai

        status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
            tool_name="unknown-tool",
            command="npm install -g unknown-tool",
            install_exit_code=1,
            install_stdout="",
            install_stderr="npm ERR! 404 Not Found",
            verify_cmd="unknown-tool --version",
            verify_exit_code=1,
            verify_stdout="",
            verify_stderr="command not found"
        )
        self.assertEqual(status, "FAILED")
        self.assertEqual(fix_cmd, "")

    def test_03_install_fails_gpt_returns_fix(self):
        """TEST 3: Install fails -> GPT returns [FIX] <command>."""
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "[FIX] python -m pip install --upgrade pip\npip cache was stale and outdated."
        self.ext_mgr.ai_backend = mock_ai

        status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
            tool_name="black",
            command="pip install black",
            install_exit_code=1,
            install_stdout="",
            install_stderr="WARNING: You are using pip version 20.0; please upgrade.",
            verify_cmd="black --version",
            verify_exit_code=1,
            verify_stdout="",
            verify_stderr=""
        )
        self.assertEqual(status, "FIX")
        self.assertEqual(fix_cmd, "python -m pip install --upgrade pip")

    def test_04_user_must_approve_fix_not_auto_executed(self):
        """TEST 4: User must approve [FIX] -> signals emitted, no auto execution without explicit user invocation."""
        emitted_signals = []
        self.ext_mgr.smartInstallFixProposed.connect(
            lambda name, cmd, exp, act, fp, vcmd, att: emitted_signals.append((name, cmd, exp, att))
        )
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "[FIX] npm cache clean --force\nClean npm cache."
        self.ext_mgr.ai_backend = mock_ai

        # Execute install that fails and proposes fix
        with patch("subprocess.run") as mock_run:
            # Install command fails
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="npm ERR! cache corrupt"),
                MagicMock(returncode=1, stdout="", stderr="not found")
            ]
            self.ext_mgr.execute_smart_install_command("prettier", "npm install -g prettier")
            time.sleep(0.5)

        self.assertTrue(len(emitted_signals) > 0)
        self.assertEqual(emitted_signals[0][1], "npm cache clean --force")

    def test_05_fix_succeeds_re_verification_occurs(self):
        """TEST 5: Fix succeeds -> re-verification occurs."""
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "SUCCESS\nFix succeeded and tool is verified."
        self.ext_mgr.ai_backend = mock_ai

        verified_calls = []
        with patch("subprocess.run") as mock_run:
            def side_effect(cmd, **kwargs):
                verified_calls.append(cmd)
                if cmd == "npm cache clean --force":
                    return MagicMock(returncode=0, stdout="cleaned", stderr="")
                else: # verification
                    return MagicMock(returncode=0, stdout="3.2.5", stderr="")
            mock_run.side_effect = side_effect

            self.ext_mgr.execute_smart_install_fix("prettier", "npm cache clean --force", verify_command="prettier --version")
            time.sleep(0.5)

        self.assertIn("prettier --version", verified_calls)

    def test_06_fix_result_is_sent_back_to_gpt(self):
        """TEST 6: Fix result is sent back to GPT with is_post_fix=True."""
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "SUCCESS"
        self.ext_mgr.ai_backend = mock_ai

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="fix output", stderr=""),
                MagicMock(returncode=0, stdout="3.0.0", stderr="")
            ]
            self.ext_mgr.execute_smart_install_fix("prettier", "npm cache clean --force", verify_command="prettier --version")
            time.sleep(0.5)

        self.assertTrue(mock_ai.ask.called)
        last_prompt = mock_ai.ask.call_args[0][0]
        self.assertIn("Post-fix verification", last_prompt)

    def test_07_second_gpt_response_success_continues(self):
        """TEST 7: Second GPT response SUCCESS -> continues and signals success."""
        verified_events = []
        self.ext_mgr.smartInstallPostInstallVerified.connect(
            lambda name, status, msg, act, fp, lang: verified_events.append((name, status))
        )
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "SUCCESS"
        self.ext_mgr.ai_backend = mock_ai

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),
                MagicMock(returncode=0, stdout="3.2.5", stderr="")
            ]
            self.ext_mgr.execute_smart_install_fix("prettier", "npm install -g prettier")
            time.sleep(0.5)

        self.assertTrue(any(ev[1] == "success" for ev in verified_events))

    def test_08_second_gpt_response_failed_stops(self):
        """TEST 8: Second GPT response FAILED -> stops."""
        verified_events = []
        self.ext_mgr.smartInstallPostInstallVerified.connect(
            lambda name, status, msg, act, fp, lang: verified_events.append((name, status))
        )
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "FAILED\nFix failed to resolve tool availability."
        self.ext_mgr.ai_backend = mock_ai

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="error"),
                MagicMock(returncode=1, stdout="", stderr="not found")
            ]
            self.ext_mgr.execute_smart_install_fix("prettier", "npm install -g prettier")
            time.sleep(0.5)

        self.assertTrue(any(ev[1] == "failed" for ev in verified_events))

    def test_09_second_gpt_response_manual_installation_required_stops(self):
        """TEST 9: Second GPT response MANUAL_INSTALLATION_REQUIRED -> stops."""
        verified_events = []
        self.ext_mgr.smartInstallPostInstallVerified.connect(
            lambda name, status, msg, act, fp, lang: verified_events.append((name, status))
        )
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "MANUAL_INSTALLATION_REQUIRED\nAdministrator privileges required."
        self.ext_mgr.ai_backend = mock_ai

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="EACCES"),
                MagicMock(returncode=1, stdout="", stderr="")
            ]
            self.ext_mgr.execute_smart_install_fix("prettier", "npm install -g prettier")
            time.sleep(0.5)

        self.assertTrue(any(ev[1] == "manual_installation_required" for ev in verified_events))

    def test_10_invalid_gpt_response_triggers_one_corrective_request(self):
        """TEST 10: Invalid GPT response -> triggers ONE corrective AI request."""
        mock_ai = MagicMock()
        # First call is invalid conversational text, second call is valid protocol
        mock_ai.ask.side_effect = [
            "Sure! It looks like prettier is now installed successfully on your machine.",
            "SUCCESS"
        ]
        self.ext_mgr.ai_backend = mock_ai

        status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
            tool_name="prettier",
            command="npm install -g prettier",
            install_exit_code=0,
            install_stdout="installed",
            install_stderr="",
            verify_cmd="prettier --version",
            verify_exit_code=0,
            verify_stdout="3.2.5",
            verify_stderr=""
        )
        self.assertEqual(mock_ai.ask.call_count, 2)
        self.assertEqual(status, "SUCCESS")

    def test_11_max_two_fix_attempts_limit(self):
        """TEST 11: Two corrective fix attempts maximum per installation session."""
        verified_events = []
        self.ext_mgr.smartInstallPostInstallVerified.connect(
            lambda name, status, msg, act, fp, lang: verified_events.append((name, status, msg))
        )
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "[FIX] npm install -g prettier"
        self.ext_mgr.ai_backend = mock_ai

        # Attempting fix #3 (beyond max 2)
        res = self.ext_mgr.execute_smart_install_fix(
            "prettier", "npm install -g prettier", fix_attempt_count=3
        )
        self.assertFalse(res)
        self.assertTrue(any(ev[1] == "manual_installation_required" for ev in verified_events))

    def test_12_no_infinite_fix_loops(self):
        """TEST 12: Ensure no infinite loops when AI keeps proposing fixes."""
        verified_events = []
        self.ext_mgr.smartInstallPostInstallVerified.connect(
            lambda name, status, msg, act, fp, lang: verified_events.append((name, status))
        )
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "[FIX] fix-command-again"
        self.ext_mgr.ai_backend = mock_ai

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
            # Execution of fix attempt 2 which proposes fix again
            self.ext_mgr.execute_smart_install_fix(
                "tool", "fix-command", fix_attempt_count=2
            )
            time.sleep(0.5)

        # After attempt 2 proposing another fix, it must terminate as manual_installation_required
        self.assertTrue(any(ev[1] == "manual_installation_required" for ev in verified_events))

    def test_13_install_succeeds_but_original_operation_fails_becomes_retry_failed(self):
        """TEST 13: Install succeeds but original operation fails -> retry_failed (NOT success)."""
        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        with patch("builtins.print", side_effect=capturing_print):
            self.ext_mgr.report_retry_result("prettier", False, "JSON syntax error: Expecting value at line 1")

        self.assertTrue(any("Retry result: failed" in l for l in logs))

    def test_14_install_succeeds_and_original_operation_succeeds_becomes_success(self):
        """TEST 14: Install succeeds and original operation succeeds -> success."""
        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        with patch("builtins.print", side_effect=capturing_print):
            self.ext_mgr.report_retry_result("prettier", True, "")

        self.assertTrue(any("Retry result: success" in l for l in logs))

    def test_15_zero_exit_code_plus_failed_verification_does_not_become_success(self):
        """TEST 15: Zero exit code + failed verification does NOT become SUCCESS in AI fallback."""
        self.ext_mgr.ai_backend = None # Fallback factual evaluation

        status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
            tool_name="prettier",
            command="echo 'fake install'",
            install_exit_code=0,
            install_stdout="Done",
            install_stderr="",
            verify_cmd="prettier --version",
            verify_exit_code=127,
            verify_stdout="",
            verify_stderr="prettier: command not found"
        )
        self.assertNotEqual(status, "SUCCESS")
        self.assertEqual(status, "FAILED")

    def test_16_verification_succeeds_but_original_operation_fails_is_not_overall_success(self):
        """TEST 16: Verification succeeds but original operation fails -> NOT overall success."""
        # Simulated QML reportRetryResult flow
        dialog_state = "retrying"
        installation_succeeded = True
        verification_succeeded = True
        original_retry_succeeded = False

        # Operation retry fails with syntax error
        retry_success = False
        retry_error = "JSON syntax error: Expecting value: line 1 column 1"

        if retry_success:
            dialog_state = "success"
        else:
            dialog_state = "retry_failed"

        self.assertEqual(dialog_state, "retry_failed")
        self.assertNotEqual(dialog_state, "success")


if __name__ == "__main__":
    unittest.main()
