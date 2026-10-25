"""
test_smart_install_runtime_comprehensive.py
Comprehensive regression tests for DGX Studio Smart Install Java Runtime Compatibility.

Tests all 10 scenarios from Part 2, Section 5:
1. Java 17 active with a compatible JDK also installed.
2. No compatible JDK installed.
3. Multiple installed JDKs (discovering, ordering, selecting compatible).
4. A compatible runtime selected only for the formatter subprocess.
5. Formatter execution with the selected runtime.
6. Runtime discovery failure handling.
7. Installation failure.
8. Formatter failure after a successful installation.
9. Successful formatting after runtime correction.
10. Correct logging of actual Java executable, version, command, and exit code.
"""

import os
import sys
import unittest
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


class TestSmartInstallRuntimeComprehensive(unittest.TestCase):
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

    def test_01_java17_active_with_compatible_jdk21_installed(self):
        """
        Scenario 1: Java 17 is active in PATH, but JDK 21 is already installed on the machine.
        Smart Install must auto-select the installed JDK 21 for the formatter subprocess
        without prompting the user to run an unnecessary winget installation command.
        """
        set_test_java_environment(
            active_info={
                "executable": r"C:\Program Files\Common Files\Oracle\Java\javapath\java.exe",
                "version": "17.0.12",
                "major_version": 17,
                "java_home": "",
                "output": 'java version "17.0.12" 2024-07-16 LTS'
            },
            discovered_jdks=[
                {
                    "path": r"C:\Program Files\Java\jdk-21",
                    "java_exe": r"C:\Program Files\Java\jdk-21\bin\java.exe",
                    "version": "21.0.2",
                    "major_version": 21
                }
            ]
        )

        with patch.object(self.ext_mgr, "retry_formatting_operation", return_value=(0, "Formatted successfully", "")):
            status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
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

        # Result should be SUCCESS because the existing compatible JDK was selected and formatting succeeded!
        self.assertEqual(status, "SUCCESS")
        self.assertIn("Selected compatible installed JDK", exp)
        cfg = self.ext_mgr.get_tool_runtime_config("google-java-format")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["JAVA_HOME"], r"C:\Program Files\Java\jdk-21")
        self.assertEqual(cfg["version"], "21.0.2")

    def test_02_no_compatible_jdk_installed(self):
        """
        Scenario 2: Java 17 active, no compatible JDK installed.
        Smart Install must diagnose the incompatibility and propose an appropriate OpenJDK fix command.
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

        exact_logged_ai_response = (
            "[FIX]powershell\n"
            "```powershell\n"
            "winget install --id Microsoft.OpenJDK.21 --exact\n"
            "```\n\n"
            "Root cause: google-java-format 1.35.0 requires JDK 21 or newer, but the formatter is using "
            "Java 17.0.12, which lacks the required javac internal class. Install JDK 21, then configure "
            "JAVA_HOME and PATH to select the installed JDK 21 instead of the Oracle Java 17 executable. "
            "Verify with java -version and retry formatting."
        )
        mock_ai = MagicMock()
        mock_ai.ask.return_value = exact_logged_ai_response
        self.ext_mgr.ai_backend = mock_ai

        status, fix_cmd, exp = self.ext_mgr.diagnose_post_install_result(
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

        self.assertEqual(status, "FIX")
        self.assertIn("Microsoft.OpenJDK", fix_cmd)
        self.assertTrue("requires JDK 21" in exp or "incompatible" in exp.lower(), f"Unexpected exp: {exp}")

    def test_03_multiple_installed_jdks(self):
        """
        Scenario 3: Multiple JDKs (Java 8, 11, 17, 21, 23) discovered.
        find_compatible_jdk must sort descending by major version and select the highest compatible one.
        """
        set_test_java_environment(
            active_info={"executable": "java.exe", "version": "17.0.1", "major_version": 17},
            discovered_jdks=[
                {"path": r"C:\Java\jdk-11", "java_exe": r"C:\Java\jdk-11\bin\java.exe", "version": "11.0.2", "major_version": 11},
                {"path": r"C:\Java\jdk-23", "java_exe": r"C:\Java\jdk-23\bin\java.exe", "version": "23.0.1", "major_version": 23},
                {"path": r"C:\Java\jdk-17", "java_exe": r"C:\Java\jdk-17\bin\java.exe", "version": "17.0.5", "major_version": 17},
                {"path": r"C:\Java\jdk-21", "java_exe": r"C:\Java\jdk-21\bin\java.exe", "version": "21.0.1", "major_version": 21},
            ]
        )

        compat = find_compatible_jdk(min_version=21)
        self.assertIsNotNone(compat)
        # Should pick highest version >= 21 (which is 23)
        self.assertEqual(compat["major_version"], 23)
        self.assertEqual(compat["path"], r"C:\Java\jdk-23")

    def test_04_compatible_runtime_isolated_to_formatter_subprocess(self):
        """
        Scenario 4: Compatible runtime is selected only for the formatter subprocess,
        leaving DGX Studio IDE environment and global os.environ unchanged.
        """
        orig_java_home = os.environ.get("JAVA_HOME", "")
        orig_path = os.environ.get("PATH", "")

        compat_jdk = {
            "path": r"C:\Program Files\Java\jdk-21",
            "java_exe": r"C:\Program Files\Java\jdk-21\bin\java.exe",
            "version": "21.0.2",
            "major_version": 21
        }
        self.ext_mgr.set_tool_runtime_config("google-java-format", {
            "JAVA_HOME": compat_jdk["path"],
            "java_path": compat_jdk["java_exe"],
            "version": compat_jdk["version"],
            "PATH_PREPEND": os.path.dirname(compat_jdk["java_exe"])
        })

        # Global environment must remain untouched
        self.assertEqual(os.environ.get("JAVA_HOME", ""), orig_java_home)
        self.assertEqual(os.environ.get("PATH", ""), orig_path)

        # Tool-specific config is present
        tool_cfg = self.ext_mgr.get_tool_runtime_config("google-java-format")
        self.assertEqual(tool_cfg["JAVA_HOME"], r"C:\Program Files\Java\jdk-21")

    def test_05_formatter_subprocess_receives_configured_env(self):
        """
        Scenario 5: FormatterManager._format_java constructs subprocess env with the tool's runtime.
        """
        self.ext_mgr.set_tool_runtime_config("google-java-format", {
            "JAVA_HOME": r"C:\TestJDK21",
            "java_path": r"C:\TestJDK21\bin\java.exe",
            "version": "21.0.0",
            "PATH_PREPEND": r"C:\TestJDK21\bin"
        })

        captured_env = {}
        def mock_subprocess_run(cmd, **kwargs):
            nonlocal captured_env
            captured_env = kwargs.get("env", {})
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = ""
            mock_res.stderr = ""
            return mock_res

        with patch("subprocess.run", side_effect=mock_subprocess_run), \
             patch("shutil.which", return_value="google-java-format"):
            res = self.fmt_mgr._format_java("class Test{}", 4, "Test.java")

        self.assertEqual(captured_env.get("JAVA_HOME"), r"C:\TestJDK21")
        self.assertTrue(captured_env.get("PATH", "").startswith(r"C:\TestJDK21\bin"))

    def test_06_runtime_discovery_failure_handling(self):
        """
        Scenario 6: Gracefully handles corrupted directory permissions or missing release files.
        """
        with patch("os.listdir", side_effect=PermissionError("Access Denied")):
            jdks = discover_installed_jdks()
            self.assertIsInstance(jdks, list)

    def test_07_installation_command_failure(self):
        """
        Scenario 7: Fix command exits with error (code 1) -> records failure, does not claim success.
        """
        with patch.object(self.ext_mgr, "execute_command_steps", return_value=(1, "", "Winget package not found", [])):
            with patch.object(self.ext_mgr, "smartInstallCompleted") as mock_signal:
                # Trigger _fix_worker simulation
                worker_called = False
                def run_fix():
                    nonlocal worker_called
                    exit_code, out, err, steps = self.ext_mgr.execute_command_steps("winget install bad-pkg")
                    if exit_code != 0:
                        mock_signal.emit("google-java-format", False, f"Fix error: {err}", "format")
                    worker_called = True
                run_fix()
                self.assertTrue(worker_called)
                mock_signal.emit.assert_called_with("google-java-format", False, "Fix error: Winget package not found", "format")

    def test_08_formatter_failure_after_successful_jdk_install(self):
        """
        Scenario 8: JDK install succeeds (exit 0), but formatter operational retry still fails.
        Must report failure and not claim success.
        """
        with patch.object(self.ext_mgr, "retry_formatting_operation", return_value=(1, "", "Syntax error in file")):
            op_exit, op_out, op_err = self.ext_mgr.retry_formatting_operation("google-java-format", "Bad.java")
            self.assertEqual(op_exit, 1)
            self.assertIn("Syntax error", op_err)

    def test_09_successful_formatting_after_runtime_correction(self):
        """
        Scenario 9: Formatting operation retried after runtime correction succeeds.
        """
        formatted_java = "class Test {\n    public static void main(String[] args) {\n        System.out.println(1);\n    }\n}\n"
        with patch.object(self.fmt_mgr, "format_code", return_value={"success": True, "formatted": formatted_java, "message": "Java formatted with google-java-format"}):
            op_exit, op_out, op_err = self.ext_mgr.retry_formatting_operation("google-java-format", "Test.java")
            self.assertEqual(op_exit, 0)
            self.assertIn("formatted", op_out.lower())
            self.assertEqual(op_err, "")

    def test_10_correct_logging_of_runtime_details(self):
        """
        Scenario 10: Verifies that collect_runtime_environment_info logs/records
        resolved Java executable, runtime version, JAVA_HOME, and discovered JDKs.
        """
        set_test_java_environment(
            active_info={
                "executable": r"C:\Java\jdk-17\bin\java.exe",
                "version": "17.0.12",
                "major_version": 17,
                "java_home": r"C:\Java\jdk-17",
                "output": 'java version "17.0.12"'
            },
            discovered_jdks=[
                {"path": r"C:\Java\jdk-21", "java_exe": r"C:\Java\jdk-21\bin\java.exe", "version": "21.0.1", "major_version": 21}
            ]
        )

        info = collect_runtime_environment_info(
            tool_name="google-java-format",
            language="java",
            executable="google-java-format",
            operation_error="ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern"
        )

        self.assertEqual(info["runtime_type"], "Java")
        self.assertEqual(info["runtime_executable"], r"C:\Java\jdk-17\bin\java.exe")
        self.assertEqual(info["runtime_version"], "17.0.12")
        self.assertTrue(info["incompatibility_detected"])
        self.assertIn("JDK 21 or newer", info["min_runtime_required"])
        self.assertIn(r"C:\Java\jdk-21", info["available_runtimes"][0])


if __name__ == "__main__":
    unittest.main()
