"""
test_smart_install_runtime_compatibility.py
Automated regression tests for DGX Studio Smart Install:
AI-Powered Runtime Compatibility Diagnosis and Automatic Fix Recommendations.

Covers tests A, B, C, D, E from Section 11 of the specification.
"""

import os
import sys
import unittest
import time
from unittest.mock import MagicMock, patch

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from PySide6.QtCore import QCoreApplication
from ExtensionManager import (
    ExtensionManager,
    set_test_java_environment,
    discover_installed_jdks,
    find_compatible_jdk,
    collect_runtime_environment_info
)
from FormatterManager import FormatterManager


class TestSmartInstallRuntimeCompatibility(unittest.TestCase):
    def setUp(self):
        self.app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        self.ext_mgr = ExtensionManager()
        self.fmt_mgr = FormatterManager(extension_manager=self.ext_mgr)
        self.ext_mgr._formatter_manager = self.fmt_mgr
        ExtensionManager.set_ai_provider(None)
        set_test_java_environment(None, None)

    def tearDown(self):
        ExtensionManager.set_ai_provider(None)
        set_test_java_environment(None, None)

    def test_01_prompt_contains_required_preamble_and_facts(self):
        """Verify prompt contains exact Section 2 preamble and factual runtime details."""
        set_test_java_environment(
            active_info={
                "executable": r"C:\Program Files\Common Files\Oracle\Java\javapath\java.exe",
                "version": "17.0.12",
                "major_version": 17,
                "java_home": "",
                "output": 'java version "17.0.12" 2024-07-16 LTS'
            },
            discovered_jdks=[]
        )

        prompt = self.ext_mgr.generate_post_install_prompt(
            tool_name="google-java-format",
            command="npm install -g google-java-format",
            install_exit_code=0,
            install_stdout="added 1 package",
            install_stderr="",
            verify_cmd="google-java-format --version",
            verify_exit_code=0,
            verify_stdout="google-java-format 1.25.0",
            verify_stderr="",
            executable="google-java-format",
            language="java",
            operation_attempted="format",
            operation_exit_code=1,
            operation_stderr="java.lang.ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern",
            operation_error="java.lang.ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern"
        )

        # Check exact Section 2 preamble
        self.assertIn("You are DGX Studio's post-install diagnostic and recovery AI.", prompt)
        self.assertIn("Do not confuse successful installation with successful operation.", prompt)
        self.assertIn("Do not merely repeat the error.", prompt)
        self.assertIn("Identify the likely root cause and recommend the safest appropriate fix.", prompt)
        self.assertIn("Prefer a concrete, executable command over vague instructions.", prompt)
        self.assertIn("Never fabricate a diagnosis or claim that an untested fix is guaranteed", prompt)

        # Check Section 3 factual execution & runtime context
        self.assertIn("google-java-format", prompt)
        self.assertIn("17.0.12", prompt)
        self.assertIn(r"C:\Program Files\Common Files\Oracle\Java\javapath\java.exe", prompt)
        self.assertIn("JCTree$JCAnyPattern", prompt)
        self.assertIn("JDK 21 or newer", prompt)

    def test_02_test_a_google_java_format_java17_incompatibility_diagnosis(self):
        """
        TEST A: google-java-format installed, Java 17 active, JCAnyPattern ClassNotFoundException.
        Expected: AI recommends a compatible JDK and supplies an appropriate installation command.
        """
        set_test_java_environment(
            active_info={
                "executable": r"C:\Program Files\Common Files\Oracle\Java\javapath\java.exe",
                "version": "17.0.12",
                "major_version": 17,
                "java_home": "",
                "output": 'java version "17.0.12" 2024-07-16 LTS'
            },
            discovered_jdks=[]
        )

        # Mock AI responding with compatible JDK recommendation
        expected_diagnosis = (
            "The formatter is installed, but its execution is incompatible with the Java runtime currently being used. "
            "The current JDK is Java 17, while the installed google-java-format version requires a newer JDK. "
            "Install a compatible JDK and ensure the formatter actually uses it."
        )
        expected_cmd = "winget install --id Microsoft.OpenJDK.25 -e --accept-source-agreements --accept-package-agreements"

        mock_ai = MagicMock()
        mock_ai.ask.return_value = f"{expected_diagnosis}\n\n[FIX] {expected_cmd}"
        self.ext_mgr.ai_backend = mock_ai

        status, fix_cmd, explanation = self.ext_mgr.diagnose_post_install_result(
            tool_name="google-java-format",
            command="npm install -g google-java-format",
            install_exit_code=0,
            install_stdout="added 1 package in 2s",
            install_stderr="",
            verify_cmd="google-java-format --version",
            verify_exit_code=0,
            verify_stdout="google-java-format: Version 1.25.0",
            verify_stderr="",
            executable="google-java-format",
            language="java",
            operation_attempted="format",
            operation_exit_code=1,
            operation_stderr="java.lang.ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern",
            operation_error="java.lang.ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern"
        )

        self.assertEqual(status, "FIX")
        self.assertIn("Microsoft.OpenJDK.25", fix_cmd)
        self.assertIn("Java 17", explanation)
        self.assertIn("newer JDK", explanation)

    def test_03_test_b_jdk25_installed_mismatch_detected_and_configured(self):
        """
        TEST B: JDK 25 installed, but formatter still resolves Java 17.
        Expected: DGX detects the runtime mismatch and configures the formatter to use the newly installed JDK.
        """
        set_test_java_environment(
            active_info={
                "executable": r"C:\Program Files\Common Files\Oracle\Java\javapath\java.exe",
                "version": "17.0.12",
                "major_version": 17,
                "java_home": "",
                "output": 'java version "17.0.12"'
            },
            discovered_jdks=[
                {
                    "path": r"C:\Program Files\Microsoft\jdk-25.0.1",
                    "java_exe": r"C:\Program Files\Microsoft\jdk-25.0.1\bin\java.exe",
                    "version": "25.0.1",
                    "major_version": 25
                }
            ]
        )

        # Detect runtime mismatch and auto-configure formatter
        reconfigured, msg = self.ext_mgr.ensure_tool_runtime_compatibility("google-java-format", "java")
        self.assertTrue(reconfigured)
        self.assertIn("Configured google-java-format to use compatible JDK", msg)

        # Verify tool runtime config is recorded
        cfg = self.ext_mgr.get_tool_runtime_config("google-java-format")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.get("JAVA_HOME"), r"C:\Program Files\Microsoft\jdk-25.0.1")
        self.assertEqual(cfg.get("java_path"), r"C:\Program Files\Microsoft\jdk-25.0.1\bin\java.exe")

    def test_04_test_c_compatible_jdk_active_formatter_succeeds(self):
        """
        TEST C: Compatible JDK active, formatter succeeds -> SUCCESS.
        """
        set_test_java_environment(
            active_info={
                "executable": r"C:\Program Files\Microsoft\jdk-25.0.1\bin\java.exe",
                "version": "25.0.1",
                "major_version": 25,
                "java_home": r"C:\Program Files\Microsoft\jdk-25.0.1",
                "output": 'openjdk version "25.0.1"'
            },
            discovered_jdks=[]
        )

        mock_ai = MagicMock()
        mock_ai.ask.return_value = "SUCCESS\nFormatter executed successfully under JDK 25."
        self.ext_mgr.ai_backend = mock_ai

        status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
            tool_name="google-java-format",
            command="winget install --id Microsoft.OpenJDK.25",
            install_exit_code=0,
            install_stdout="Successfully installed",
            install_stderr="",
            verify_cmd="google-java-format --version",
            verify_exit_code=0,
            verify_stdout="google-java-format: Version 1.25.0",
            verify_stderr="",
            executable="google-java-format",
            language="java",
            is_post_fix=True,
            operation_attempted="format",
            operation_exit_code=0,
            operation_stdout="Formatted successfully",
            operation_stderr="",
            operation_error=""
        )

        self.assertEqual(status, "SUCCESS")
        self.assertEqual(fix_cmd, "")

    def test_05_test_d_install_succeeds_but_operation_fails_no_false_success(self):
        """
        TEST D: Installation succeeds, but actual operation still fails.
        Expected: No false success. Capture and diagnose the new error.
        """
        # Even if AI mistakenly returns "SUCCESS", DGX must guard against false success when operation failed
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "SUCCESS"
        self.ext_mgr.ai_backend = mock_ai

        status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
            tool_name="google-java-format",
            command="npm install -g google-java-format",
            install_exit_code=0,
            install_stdout="added 1 package",
            install_stderr="",
            verify_cmd="google-java-format --version",
            verify_exit_code=0,
            verify_stdout="google-java-format: Version 1.25.0",
            verify_stderr="",
            executable="google-java-format",
            language="java",
            operation_attempted="format",
            operation_exit_code=1,
            operation_stderr="java.lang.ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern",
            operation_error="java.lang.ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern"
        )

        self.assertNotEqual(status, "SUCCESS")
        self.assertEqual(status, "FIX")
        self.assertIn("Microsoft.OpenJDK.25", fix_cmd)

    def test_06_test_e_gpt_cannot_determine_safe_fix(self):
        """
        TEST E: GPT cannot determine a safe fix -> FAILED or MANUAL_INSTALLATION_REQUIRED as appropriate.
        """
        mock_ai = MagicMock()
        mock_ai.ask.return_value = "MANUAL_INSTALLATION_REQUIRED\nProprietary SDK requires manual download from vendor portal."
        self.ext_mgr.ai_backend = mock_ai

        status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
            tool_name="custom-compiler",
            command="install-compiler",
            install_exit_code=0,
            install_stdout="Compiler installed",
            install_stderr="",
            verify_cmd="custom-compiler --version",
            verify_exit_code=0,
            verify_stdout="v1.0",
            verify_stderr="",
            operation_attempted="compile",
            operation_exit_code=1,
            operation_stderr="Missing proprietary runtime library libfoo.so"
        )

        self.assertEqual(status, "MANUAL_INSTALLATION_REQUIRED")
        self.assertEqual(fix_cmd, "")

    def test_07_diagnose_operation_failure_signal_emission(self):
        """Verify diagnose_operation_failure emits smartInstallFixProposed with explicit user approval required."""
        set_test_java_environment(
            active_info={
                "executable": r"C:\Program Files\Common Files\Oracle\Java\javapath\java.exe",
                "version": "17.0.12",
                "major_version": 17,
                "java_home": "",
                "output": 'java version "17.0.12"'
            },
            discovered_jdks=[]
        )

        mock_ai = MagicMock()
        mock_ai.ask.return_value = (
            "The formatter requires JDK 21+ but active runtime is Java 17.\n"
            "[FIX] winget install --id Microsoft.OpenJDK.25 -e --accept-source-agreements --accept-package-agreements"
        )
        self.ext_mgr.ai_backend = mock_ai

        fix_proposed = []
        self.ext_mgr.smartInstallFixProposed.connect(
            lambda name, cmd, exp, act, fp, vcmd, count: fix_proposed.append((name, cmd, exp))
        )

        self.ext_mgr.diagnose_operation_failure(
            tool_name="google-java-format",
            error_message="java.lang.ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern",
            retry_action="format",
            file_path="Test.java",
            language="java"
        )

        # Wait for background thread
        start = time.time()
        while not fix_proposed and time.time() - start < 3.0:
            self.app.processEvents()
            time.sleep(0.05)

        self.assertTrue(len(fix_proposed) > 0)
        tool, cmd, exp = fix_proposed[0]
        self.assertEqual(tool, "google-java-format")
        self.assertIn("Microsoft.OpenJDK.25", cmd)


if __name__ == "__main__":
    unittest.main()
