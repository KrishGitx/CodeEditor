"""
test_general_smart_install_recovery.py
Comprehensive test suite verifying PART 2: General Background Error-Detection & Recovery System across DGX Studio.

Tests all 14 scenarios from Section J:
1. Missing executable with compatible DGX Studio extension available.
2. Missing executable with no suitable extension but command-line installation available.
3. Dependency already installed.
4. Incompatible runtime.
5. Compilation or syntax error that should be diagnosed rather than treated as a missing dependency.
6. Runtime exception caused by application logic.
7. Failing test assertion.
8. Permission failure.
9. Network failure.
10. Installation already in progress.
11. Command that installs successfully but does not fix original operation.
12. Case where AI cannot confidently identify a fix.
13. Cancellation, timeout, and repeated identical failures (deduplication & cooldown).
14. Successful fix followed by successful retry of original operation.
"""

import os
import sys
import time
import tempfile
import unittest
from unittest.mock import MagicMock, patch

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from PySide6.QtCore import QCoreApplication
from ExtensionManager import (
    ExtensionManager,
    classify_failure,
    DGX_MARKETPLACE_EXTENSIONS,
    set_test_installer_in_progress,
    set_test_java_environment
)


class TestGeneralSmartInstallRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    def setUp(self):
        self.ext_mgr = ExtensionManager()
        ExtensionManager.set_ai_provider(None)
        set_test_installer_in_progress(None)
        set_test_java_environment(None, None)

    def tearDown(self):
        ExtensionManager.set_ai_provider(None)
        set_test_installer_in_progress(None)
        set_test_java_environment(None, None)

    # --------------------------------------------------------------------------
    # Scenario 1: Missing executable with compatible DGX Studio extension available
    # --------------------------------------------------------------------------
    def test_01_missing_executable_with_extension_available(self):
        """
        When a missing tool or runtime maps to an official DGX Studio Marketplace extension,
        Smart Install proposes installing/enabling the extension first rather than raw CLI install.
        """
        # Ensure dgx.python is not active for this check
        if "dgx.python" in self.ext_mgr._extensions:
            self.ext_mgr._disabled_ids.add("dgx.python")
            self.ext_mgr._extensions["dgx.python"].enabled = False

        mkt = self.ext_mgr.find_compatible_marketplace_extension("python", ".py")
        self.assertTrue(mkt.get("compatible"), "Compatible extension should be found")
        self.assertEqual(mkt.get("extension_id"), "dgx.python")
        self.assertIn(mkt.get("action"), ("activate", "install"))

        # Test context resolution when python executable is missing
        with patch("ExtensionManager.locate_executable", return_value=None):
            ctx = self.ext_mgr.create_smart_install_context(
                operation="Run python script",
                operation_type="runner",
                language="python",
                file_path="main.py",
                executable="python",
                detected_missing_dependency="python"
            )
            proposal = self.ext_mgr.resolve_smart_install_context(ctx)
            self.assertIn(proposal.get("resolutionType"), ("extension_install", "extension_activate"))
            self.assertIn(proposal.get("actionType"), ("extension_install", "extension_activate"))
            self.assertTrue(proposal.get("requiresApproval"))
            self.assertEqual(proposal.get("extensionId"), "dgx.python")
            print("[PASS] Scenario 1: Missing executable with DGX extension available -> proposes extension recovery")

    # --------------------------------------------------------------------------
    # Scenario 2: Missing executable with no suitable extension -> command-first
    # --------------------------------------------------------------------------
    def test_02_missing_executable_without_extension_command_first(self):
        """
        When no DGX extension exists for a tool, falls back to command-first installation strategy.
        """
        mkt = self.ext_mgr.find_compatible_marketplace_extension("shfmt", ".sh")
        self.assertFalse(mkt.get("compatible", False), "No extension should exist for shfmt")

        # Mock AI providing valid command
        ExtensionManager.set_ai_provider(lambda p: json.dumps({
            "tool": "shfmt",
            "package": "shfmt",
            "command": "winget install --id mvdan.shfmt -e --silent" if sys.platform.startswith("win") else "brew install shfmt",
            "status": "ready"
        }))

        import json
        with patch("ExtensionManager.locate_executable", return_value=None):
            ctx = self.ext_mgr.create_smart_install_context(
                operation="Format shell script",
                operation_type="formatter",
                language="shell",
                file_path="script.sh",
                executable="shfmt",
                detected_missing_dependency="shfmt"
            )
            proposal = self.ext_mgr.resolve_smart_install_context(ctx)
            self.assertEqual(proposal.get("resolutionType"), "single_command")
            self.assertIn("shfmt", proposal.get("command", ""))
            self.assertTrue(proposal.get("needsConfirmation") or proposal.get("requiresApproval", True))
        print("[PASS] Scenario 2: Missing tool with no extension -> falls back to non-interactive command-first")

    # --------------------------------------------------------------------------
    # Scenario 3: Dependency already installed
    # --------------------------------------------------------------------------
    def test_03_dependency_already_installed(self):
        """
        When dependency is already installed, reports already_installed without running install.
        """
        ctx = self.ext_mgr.create_smart_install_context(
            operation="Execute python",
            operation_type="interpreter",
            language="python",
            executable=sys.executable
        )
        proposal = self.ext_mgr.resolve_smart_install_context(ctx)
        self.assertTrue(proposal.get("isInstalled"))
        self.assertEqual(proposal.get("status"), "already_installed")
        self.assertEqual(proposal.get("command"), "")
        print("[PASS] Scenario 3: Already installed dependency detected cleanly")

    # --------------------------------------------------------------------------
    # Scenario 4: Incompatible runtime
    # --------------------------------------------------------------------------
    def test_04_incompatible_runtime(self):
        """
        Detects runtime version mismatch (e.g. Java 17 vs JDK 21+ requirement).
        """
        diag = classify_failure(
            operation="format",
            error_message="java.lang.UnsupportedClassVersionError: com/sun/tools/javac/tree/JCTree$JCAnyPattern has been compiled by a more recent version of the Java Runtime (class file version 65.0), this compiler only recognizes class file versions up to 61.0",
            exit_code=1,
            language="java"
        )
        self.assertEqual(diag.get("category"), "unsupported_runtime_version")

        # Background recovery proposal for incompatible JDK
        compat_jdk_dir = os.path.abspath(os.path.join(tempfile.gettempdir(), "test_jdk21_compat"))
        bin_dir = os.path.join(compat_jdk_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        java_exe = os.path.join(bin_dir, "java.exe" if sys.platform.startswith("win") else "java")
        with open(java_exe, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")

        set_test_java_environment(
            active_info={"executable": r"C:\Java\jdk-17\bin\java.exe", "version": "17.0.2", "major_version": 17},
            discovered_jdks=[{"path": compat_jdk_dir, "java_exe": java_exe, "version": "21.0.6", "major_version": 21}]
        )

        ctx = {
            "operation": "format",
            "toolName": "google-java-format",
            "language": "java",
            "errorMessage": "UnsupportedClassVersionError: requires Java 21",
            "exitCode": 1
        }
        proposal = self.ext_mgr.diagnose_and_recover_workflow_failure(ctx)
        self.assertEqual(proposal.get("category"), "unsupported_runtime_version")
        self.assertEqual(proposal.get("actionType"), "runtime_config")
        print("[PASS] Scenario 4: Incompatible runtime classified and configured with compatible version")

    # --------------------------------------------------------------------------
    # Scenario 5: Compilation or syntax error -> diagnosed, NOT treated as missing tool
    # --------------------------------------------------------------------------
    def test_05_compilation_or_syntax_error(self):
        """
        Syntax or compilation errors in user code are diagnosed; no tool installation is proposed.
        """
        diag = classify_failure(
            operation="build",
            command="g++ main.cpp -o main.exe",
            error_message="main.cpp:12:5: error: expected ';' before 'return'",
            exit_code=1,
            language="cpp"
        )
        self.assertEqual(diag.get("category"), "syntax_error")

        ctx = {
            "operation": "build",
            "command": "g++ main.cpp",
            "errorMessage": "SyntaxError: unexpected token ';'",
            "exitCode": 1,
            "filePath": "main.cpp",
            "language": "cpp"
        }
        proposal = self.ext_mgr.diagnose_and_recover_workflow_failure(ctx)
        self.assertEqual(proposal.get("category"), "syntax_error")
        self.assertEqual(proposal.get("actionType"), "code_diagnosis")
        self.assertEqual(proposal.get("command"), "", "No installation command should be proposed for syntax error")
        self.assertTrue(proposal.get("requiresApproval"))
        print("[PASS] Scenario 5: Syntax error diagnosed without proposing tool installation")

    # --------------------------------------------------------------------------
    # Scenario 6: Runtime exception caused by user application logic
    # --------------------------------------------------------------------------
    def test_06_runtime_exception_user_code(self):
        """
        Runtime crashes in application code (ZeroDivisionError, IndexError, etc.) are diagnosed.
        """
        diag = classify_failure(
            operation="run",
            command="python calc.py",
            error_message="Traceback (most recent call last):\n  File 'calc.py', line 5, in <module>\n    x = 10 / 0\nZeroDivisionError: division by zero",
            exit_code=1,
            language="python"
        )
        self.assertEqual(diag.get("category"), "runtime_exception")

        ctx = {
            "operation": "run",
            "command": "python calc.py",
            "errorMessage": "ZeroDivisionError: division by zero",
            "exitCode": 1,
            "filePath": "calc.py",
            "language": "python"
        }
        proposal = self.ext_mgr.diagnose_and_recover_workflow_failure(ctx)
        self.assertEqual(proposal.get("category"), "runtime_exception")
        self.assertEqual(proposal.get("actionType"), "code_diagnosis")
        self.assertIn("ZeroDivisionError", proposal.get("proposedFix"))
        print("[PASS] Scenario 6: User-code runtime exception diagnosed without modifying files")

    # --------------------------------------------------------------------------
    # Scenario 7: Failing test assertion
    # --------------------------------------------------------------------------
    def test_07_failing_test_assertion(self):
        """
        Failing test assertions are recognized as test_failure, avoiding package manager triggers.
        """
        diag = classify_failure(
            operation="test",
            command="pytest test_app.py",
            error_message="FAILED test_app.py::test_math - AssertionError: assert 42 == 100",
            exit_code=1,
            language="python"
        )
        self.assertEqual(diag.get("category"), "test_failure")

        ctx = {
            "operation": "test",
            "command": "pytest test_app.py",
            "errorMessage": "AssertionError: assert 42 == 100",
            "exitCode": 1,
            "filePath": "test_app.py"
        }
        proposal = self.ext_mgr.diagnose_and_recover_workflow_failure(ctx)
        self.assertEqual(proposal.get("category"), "test_failure")
        self.assertEqual(proposal.get("actionType"), "code_diagnosis")
        print("[PASS] Scenario 7: Failing test assertion properly classified and diagnosed")

    # --------------------------------------------------------------------------
    # Scenario 8: Permission failure
    # --------------------------------------------------------------------------
    def test_08_permission_failure(self):
        """
        Detects permission / elevation issues and provides appropriate guidance.
        """
        diag = classify_failure(
            operation="build",
            command="make install",
            error_message="PermissionError: [Errno 13] Permission denied: '/usr/local/bin/app'",
            exit_code=13
        )
        self.assertEqual(diag.get("category"), "permission_failure")

        ctx = {
            "operation": "build",
            "errorMessage": "Permission denied: access is denied",
            "exitCode": 13
        }
        proposal = self.ext_mgr.diagnose_and_recover_workflow_failure(ctx)
        self.assertEqual(proposal.get("category"), "permission_failure")
        self.assertEqual(proposal.get("actionType"), "permission_guidance")
        print("[PASS] Scenario 8: Permission failure identified with guidance")

    # --------------------------------------------------------------------------
    # Scenario 9: Network failure
    # --------------------------------------------------------------------------
    def test_09_network_failure(self):
        """
        Detects network offline / timeout conditions and guides user.
        """
        diag = classify_failure(
            operation="tool",
            command="pip install requests",
            error_message="urllib3.exceptions.MaxRetryError: ConnectionRefusedError: Could not resolve host pypi.org",
            exit_code=1
        )
        self.assertEqual(diag.get("category"), "network_failure")

        ctx = {
            "operation": "install",
            "errorMessage": "ConnectionRefusedError: Failed to fetch package from registry",
            "exitCode": 1
        }
        proposal = self.ext_mgr.diagnose_and_recover_workflow_failure(ctx)
        self.assertEqual(proposal.get("category"), "network_failure")
        self.assertEqual(proposal.get("actionType"), "network_guidance")
        print("[PASS] Scenario 9: Network failure identified with offline guidance")

    # --------------------------------------------------------------------------
    # Scenario 10: Installation already in progress
    # --------------------------------------------------------------------------
    def test_10_installation_already_in_progress(self):
        """
        Detects active installation and avoids launching duplicate processes.
        """
        set_test_installer_in_progress(True)
        ctx = {
            "operation": "run",
            "toolName": "gcc",
            "command": "gcc main.c",
            "errorMessage": "gcc: command not found",
            "exitCode": 127
        }
        res = self.ext_mgr.diagnose_and_recover_workflow_failure(ctx)
        self.assertEqual(res.get("status"), "busy")
        self.assertIn("in progress", res.get("message"))
        print("[PASS] Scenario 10: Installation already in progress detected and duplicates avoided")

    # --------------------------------------------------------------------------
    # Scenario 11: Command installs successfully but does not fix original operation
    # --------------------------------------------------------------------------
    def test_11_install_succeeds_but_operation_fails(self):
        """
        When installation and verification succeed, but original operation still fails on retry,
        Smart Install triggers post-install AI verification and does not falsely claim victory.
        """
        ExtensionManager.set_ai_provider(lambda p: "[FIX]test-fmt --reconfigure\nOperational failure needs reconfiguration.")
        status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
            tool_name="test-fmt",
            command="pip install test-fmt",
            install_exit_code=0,
            install_stdout="Successfully installed test-fmt",
            install_stderr="",
            verify_cmd="test-fmt --version",
            verify_exit_code=0,
            verify_stdout="test-fmt 1.0.0",
            verify_stderr="",
            executable="test-fmt",
            operation_attempted="format",
            operation_exit_code=1,
            operation_error="Runtime error during format operation",
            fix_attempt_count=0
        )
        self.assertEqual(status, "FIX")
        self.assertEqual(fix_cmd, "test-fmt --reconfigure")
        ExtensionManager.set_ai_provider(None)
        print("[PASS] Scenario 11: Operation retry failure caught and corrective fix diagnosed")

    # --------------------------------------------------------------------------
    # Scenario 12: AI cannot confidently identify a fix -> safe fallback
    # --------------------------------------------------------------------------
    def test_12_ai_cannot_confidently_identify_fix(self):
        """
        When AI cannot confidently identify a fix, provides clear diagnosis and manual links;
        does NOT invent arbitrary commands.
        """
        ExtensionManager.set_ai_provider(lambda p: "")
        ctx = self.ext_mgr.create_smart_install_context(
            operation="Custom Tool",
            operation_type="tool",
            language="unknown_lang",
            executable="obscure-tool-123",
            detected_missing_dependency="obscure-tool-123"
        )
        proposal = self.ext_mgr.resolve_smart_install_context(ctx)
        self.assertEqual(proposal.get("resolutionType"), "cannot_resolve")
        self.assertEqual(proposal.get("command"), "")
        self.assertTrue(bool(proposal.get("explanation")))
        print("[PASS] Scenario 12: Safe fallback when fix cannot be confidently identified")

    # --------------------------------------------------------------------------
    # Scenario 13: Cancellation, timeout, and repeated identical failures cooldown
    # --------------------------------------------------------------------------
    def test_13_timeout_cancellation_and_repeated_failures_cooldown(self):
        """
        Times out gracefully and deduplicates repeated identical failures within 20s cooldown.
        """
        diag = classify_failure(
            operation="build",
            command="cargo build",
            error_message="subprocess.TimeoutExpired: Command 'cargo build' timed out after 300 seconds",
            exit_code=124
        )
        self.assertEqual(diag.get("category"), "timeout_or_cancellation")
        self.assertTrue(diag.get("is_transient"))

        # Test cooldown deduplication
        ctx = {
            "operation": "build",
            "toolName": "cargo",
            "command": "cargo build",
            "errorMessage": "Command timed out",
            "exitCode": 124,
            "runId": "test_cd_1"
        }
        res1 = self.ext_mgr.diagnose_and_recover_workflow_failure(ctx)
        self.assertEqual(res1.get("category"), "timeout_or_cancellation")

        # Immediate repeat within cooldown
        ctx2 = dict(ctx)
        ctx2["runId"] = "test_cd_2"
        res2 = self.ext_mgr.diagnose_and_recover_workflow_failure(ctx2)
        self.assertEqual(res2.get("status"), "deduplicated")
        print("[PASS] Scenario 13: Timeout handled and identical failure deduplicated within cooldown")

    # --------------------------------------------------------------------------
    # Scenario 14: Successful fix followed by successful retry of original operation
    # --------------------------------------------------------------------------
    def test_14_successful_fix_followed_by_successful_retry(self):
        """
        When a fix succeeds and the original operation retries successfully,
        reports overall operational resolution.
        """
        # Test extension recovery flow
        with patch.object(self.ext_mgr, "toggle_extension", return_value=True):
            with patch.object(self.ext_mgr, "get_extension") as mock_get:
                mock_ext = MagicMock()
                mock_ext.enabled = True
                mock_get.return_value = mock_ext

                with patch.object(self.ext_mgr, "retry_formatting_operation", return_value=(0, "Formatted OK", "")):
                    retried_signals = []
                    completed_signals = []
                    self.ext_mgr.originalOperationRetried.connect(lambda t, s, e: retried_signals.append((t, s, e)))
                    self.ext_mgr.smartInstallCompleted.connect(lambda t, s, m, r: completed_signals.append((t, s, m, r)))

                    success = self.ext_mgr.execute_extension_recovery(
                        extension_id="dgx.python",
                        action="enable",
                        tool_name="autopep8",
                        retry_action="format",
                        file_path="main.py"
                    )
                    self.assertTrue(success)
                    self.assertEqual(len(retried_signals), 1)
                    self.assertTrue(retried_signals[0][1], "Original operation retry must succeed")
                    self.assertEqual(len(completed_signals), 1)
                    self.assertTrue(completed_signals[0][1], "Smart install must complete with success=True")
                    print("[PASS] Scenario 14: Successful fix followed by successful retry verified")


if __name__ == "__main__":
    unittest.main()
