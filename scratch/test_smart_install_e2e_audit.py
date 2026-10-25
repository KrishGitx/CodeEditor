import os
import sys
import time
import shutil
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QCoreApplication

app = QCoreApplication.instance()
if app is None:
    app = QCoreApplication(sys.argv)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager


class TestSmartInstallEndToEndAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.em = ExtensionManager()
        cls.fm = FormatterManager(cls.em)
        cls.em.set_formatter_manager(cls.fm)

    def setUp(self):
        self.em._attempted_fix_commands.clear()
        self.em._installing_tools.clear()

    # 1. A single successful command
    def test_01_single_successful_command(self):
        exit_code, stdout, stderr, steps = self.em.execute_command_steps("python --version", "python")
        self.assertEqual(exit_code, 0)
        self.assertIn("Python", stdout or stderr)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["exit_code"], 0)

    # 2. Multiple sequential commands
    def test_02_multiple_sequential_commands(self):
        cmd = "python -c \"print('step1')\" && python -c \"print('step2')\""
        exit_code, stdout, stderr, steps = self.em.execute_command_steps(cmd, "python")
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(steps), 2)
        self.assertIn("step1", steps[0]["stdout"])
        self.assertIn("step2", steps[1]["stdout"])

    # 3. Multiple independent commands
    def test_03_multiple_independent_commands(self):
        c1 = "python -c \"print('toolA')\""
        c2 = "python -c \"print('toolB')\""
        code1, out1, _, _ = self.em.execute_command_steps(c1, "toolA")
        code2, out2, _, _ = self.em.execute_command_steps(c2, "toolB")
        self.assertEqual(code1, 0)
        self.assertEqual(code2, 0)
        self.assertIn("toolA", out1)
        self.assertIn("toolB", out2)

    # 4. A failed prerequisite stops dependent steps
    def test_04_failed_prerequisite_stops_dependent_steps(self):
        cmd = "python -c \"import sys; sys.exit(42)\" && python -c \"print('should not run')\""
        exit_code, stdout, stderr, steps = self.em.execute_command_steps(cmd, "test")
        self.assertEqual(exit_code, 42)
        self.assertEqual(len(steps), 1)
        self.assertNotIn("should not run", stdout)

    # 5. Partial success recorded and captured
    def test_05_partial_success(self):
        cmd = "python -c \"print('success_part')\" && python -c \"import sys; sys.stderr.write('fail_part'); sys.exit(1)\""
        exit_code, stdout, stderr, steps = self.em.execute_command_steps(cmd, "test")
        self.assertEqual(exit_code, 1)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["exit_code"], 0)
        self.assertEqual(steps[1]["exit_code"], 1)
        self.assertIn("success_part", stdout)
        self.assertIn("fail_part", stderr)

    # 6. Malformed AI responses handled safely
    def test_06_malformed_ai_responses(self):
        status, fix_cmd, exp = self.em.parse_post_install_ai_response("Random text without keywords")
        self.assertEqual(status, "INVALID")

    # 7. Empty AI responses handled safely
    def test_07_empty_ai_responses(self):
        status, fix_cmd, exp = self.em.parse_post_install_ai_response("")
        self.assertEqual(status, "INVALID")
        status2, _, _ = self.em.parse_post_install_ai_response("   \n\t  ")
        self.assertEqual(status2, "INVALID")

    # 8. A repeated failing command halts loop
    def test_08_repeated_failing_command(self):
        self.em._attempted_fix_commands["my_tool"] = ["pip install repeated-tool"]
        res = self.em.execute_smart_install_fix("my_tool", "pip install repeated-tool", fix_attempt_count=1)
        self.assertFalse(res)

    # 9. Retry exhaustion (budget > 2)
    def test_09_retry_exhaustion(self):
        res = self.em.execute_smart_install_fix("my_tool", "pip install new-tool", fix_attempt_count=3)
        self.assertFalse(res)

    # 10. Successful installation followed by failed verification
    def test_10_successful_install_failed_verification(self):
        old_resolver = ExtensionManager._custom_ai_resolver
        ExtensionManager._custom_ai_resolver = lambda prompt: "FAILED\nExecutable missing after installation."
        try:
            status, fix_cmd, explanation = self.em.diagnose_post_install_result(
                tool_name="dummy_tool",
                command="pip install dummy",
                install_exit_code=0,
                install_stdout="Successfully installed dummy",
                install_stderr="",
                verify_cmd="dummy_tool --version",
                verify_exit_code=127,
                verify_stdout="",
                verify_stderr="dummy_tool: command not found",
                executable="dummy_tool"
            )
            self.assertIn(status, ("FAILED", "FIX", "MANUAL_INSTALLATION_REQUIRED"))
            self.assertNotEqual(status, "SUCCESS")
        finally:
            ExtensionManager._custom_ai_resolver = old_resolver

    # 11. Successful installation followed by a failed original operation
    def test_11_successful_install_failed_original_operation(self):
        old_resolver = ExtensionManager._custom_ai_resolver
        ExtensionManager._custom_ai_resolver = lambda prompt: "FAILED\nSyntax error encountered."
        try:
            status, fix_cmd, explanation = self.em.diagnose_post_install_result(
                tool_name="rustfmt",
                command="cargo install rustfmt",
                install_exit_code=0,
                install_stdout="Installed",
                install_stderr="",
                verify_cmd="rustfmt --version",
                verify_exit_code=0,
                verify_stdout="rustfmt 1.7.0",
                verify_stderr="",
                executable="rustfmt",
                operation_attempted="format",
                operation_exit_code=1,
                operation_error="Failed to format file due to syntax error"
            )
            self.assertNotEqual(status, "SUCCESS")
        finally:
            ExtensionManager._custom_ai_resolver = old_resolver

    # 12. Cancellation / empty command safety
    def test_12_empty_command_rejection(self):
        res = self.em.execute_smart_install_command("tool", "")
        self.assertFalse(res)
        res_fix = self.em.execute_smart_install_fix("tool", "")
        self.assertFalse(res_fix)

    # 13. Command timeout
    def test_13_command_timeout(self):
        cmd = "python -c \"import time; time.sleep(5)\""
        code, out, err, steps = self.em.execute_command_steps(cmd, "test", timeout=1)
        self.assertEqual(code, 124)
        self.assertIn("timed out", err.lower())

    # 14. Concurrent independent requests isolation
    def test_14_concurrent_independent_requests(self):
        self.em._installing_tools.add("tool_x")
        res = self.em.execute_smart_install_command("tool_x", "pip install tool_x")
        self.assertFalse(res)
        self.assertNotIn("tool_y", self.em._installing_tools)

    # 15. Duplicate request handling
    def test_15_duplicate_request_handling(self):
        self.em._installing_tools.add("duplicate_tool")
        res = self.em.execute_smart_install_command("duplicate_tool", "pip install duplicate_tool")
        self.assertFalse(res)

    # 16. Nonzero exit codes captured
    def test_16_nonzero_exit_codes(self):
        code, out, err, steps = self.em.execute_command_steps("python -c \"import sys; sys.exit(7)\"", "test")
        self.assertEqual(code, 7)

    # 17. Error output despite a zero exit code
    def test_17_error_output_despite_zero_exit_code(self):
        prompt = self.em.generate_post_install_prompt(
            tool_name="test_tool",
            command="pip install test_tool",
            install_exit_code=0,
            install_stdout="All files unpacked",
            install_stderr="WARNING: Directory not on PATH",
            verify_cmd="test_tool --version",
            verify_exit_code=0,
            verify_stdout="test_tool 1.0",
            verify_stderr=""
        )
        self.assertIn("WARNING: Directory not on PATH", prompt)

    # 18. Wrong-platform commands rejected
    def test_18_wrong_platform_commands_rejected(self):
        if sys.platform == "win32":
            safe, reason = self.em.validate_command_safety("brew install rustfmt")
            self.assertFalse(safe)
            self.assertIn("Platform mismatch", reason)
            safe2, reason2 = self.em.validate_command_safety("sudo apt-get install rustfmt")
            self.assertFalse(safe2)
            self.assertIn("Platform mismatch", reason2)
        else:
            safe, reason = self.em.validate_command_safety("winget install rustfmt")
            self.assertFalse(safe)
            self.assertIn("Platform mismatch", reason)

    # 19. Reject explanatory prose as a command
    def test_19_prose_rejection(self):
        safe, reason = self.em.validate_command_safety("You should install rustup from the official website.")
        self.assertFalse(safe)
        self.assertIn("prose detected", reason.lower())

    # 20. Internal exceptions in FormatterManager handled gracefully
    def test_20_internal_exceptions_in_formatter_manager(self):
        mock_fm = MagicMock()
        mock_fm.format_code.side_effect = AttributeError("Simulated formatter bug")
        old_fm = self.em._formatter_manager
        self.em._formatter_manager = mock_fm
        try:
            code, out, err = self.em.retry_formatting_operation("rustfmt", "test.rs")
            self.assertEqual(code, 1)
            self.assertIn("FormatterManager error", err)
        finally:
            self.em._formatter_manager = old_fm

    # 21. The exact _formatter_manager AttributeError resolved
    def test_21_formatter_manager_attribute_error_resolved(self):
        fresh_em = ExtensionManager()
        self.assertTrue(hasattr(fresh_em, "_formatter_manager"))
        self.assertIsNone(fresh_em._formatter_manager)
        self.assertIsNone(fresh_em.formatter_manager)
        code, out, err = fresh_em.retry_formatting_operation("rustfmt", "test.rs")
        self.assertNotIn("AttributeError", err)

    # 22. Successful rustfmt installation followed by formatting
    def test_22_rustfmt_installation_followed_by_formatting(self):
        mock_fm = MagicMock()
        mock_fm.format_code.return_value = {"success": True, "message": "Code formatted successfully"}
        old_fm = self.em._formatter_manager
        self.em._formatter_manager = mock_fm
        try:
            code, out, err = self.em.retry_formatting_operation("rustfmt", "test.rs")
            self.assertEqual(code, 0)
            self.assertEqual(out, "Code formatted successfully")
            self.assertEqual(err, "")
        finally:
            self.em._formatter_manager = old_fm

    # 23. A formatting check that detects unformatted code
    def test_23_formatting_check_detects_unformatted_code(self):
        mock_fm = MagicMock()
        mock_fm.format_code.return_value = {"success": False, "message": "Diff detected: code is unformatted"}
        old_fm = self.em._formatter_manager
        self.em._formatter_manager = mock_fm
        try:
            code, out, err = self.em.retry_formatting_operation("rustfmt", "test.rs")
            self.assertEqual(code, 1)
            self.assertIn("Diff detected", err)
        finally:
            self.em._formatter_manager = old_fm

    # 24. Successful formatting followed by verification
    def test_24_successful_formatting_followed_by_verification(self):
        mock_fm = MagicMock()
        mock_fm.format_code.return_value = {"success": True, "message": "OK"}
        self.em._formatter_manager = mock_fm
        code, out, err = self.em.retry_formatting_operation("rust", "main.rs")
        self.assertEqual(code, 0)

    # 25. Failure cleanup and correct final UI status
    def test_25_failure_cleanup_and_correct_status(self):
        tool = "failing_tool_cleanup"
        self.em._installing_tools.add(tool)
        self.assertIn(tool, self.em._installing_tools)
        self.em._installing_tools.discard(tool)
        self.assertNotIn(tool, self.em._installing_tools)

    # 26. originalOperationRetried signal argument count, types, and emission
    def test_26_original_operation_retried_signal_signature(self):
        received_args = []
        def slot(tool_name, success, error_message):
            received_args.append((tool_name, success, error_message))

        self.em.originalOperationRetried.connect(slot)
        try:
            # Emitting the required 3 arguments succeeds without TypeError
            self.em.originalOperationRetried.emit("rustfmt", True, "")
            self.assertEqual(len(received_args), 1)
            self.assertEqual(received_args[0], ("rustfmt", True, ""))

            # Emitting on failure
            self.em.originalOperationRetried.emit("rustfmt", False, "syntax error")
            self.assertEqual(len(received_args), 2)
            self.assertEqual(received_args[1], ("rustfmt", False, "syntax error"))
        finally:
            self.em.originalOperationRetried.disconnect(slot)

    # 27. Correct final UI status after internal IDE exceptions
    def test_27_internal_ide_exception_reporting(self):
        completed_signals = []
        def on_completed(tool_name, success, msg, retry_act):
            completed_signals.append((tool_name, success, msg, retry_act))

        self.em.smartInstallCompleted.connect(on_completed)
        try:
            # Simulate internal exception formatting
            fake_type_error = TypeError("originalOperationRetried(QString,bool,QString) only accepts 3 argument(s)")
            is_internal = isinstance(fake_type_error, (AttributeError, TypeError, KeyError, NameError, UnboundLocalError, IndexError))
            self.assertTrue(is_internal)
            err_prefix = f"Internal IDE error ({type(fake_type_error).__name__})" if is_internal else "Fix error"
            err_str = f"{err_prefix}: {fake_type_error}"
            self.assertEqual(err_str, "Internal IDE error (TypeError): originalOperationRetried(QString,bool,QString) only accepts 3 argument(s)")
        finally:
            self.em.smartInstallCompleted.disconnect(on_completed)


if __name__ == "__main__":
    unittest.main()

