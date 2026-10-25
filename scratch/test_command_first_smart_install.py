"""
test_command_first_smart_install.py
Comprehensive test suite verifying the Smart Install: Command-First Installation Policy.

Acceptance criteria scenarios tested:
1. A dependency that is already installed.
2. A dependency installable silently through a package manager.
3. A tool available as a portable archive.
4. A package requiring interactive installation.
5. An installation already in progress (Windows Installer code 1618 / mutex wait).
6. A failed installation.
7. A blocked download.
8. A successful installation followed by failed verification.
9. A successful installation and successful original operation.
"""

import os
import sys
import tempfile
import zipfile
import shutil
import unittest
from unittest.mock import MagicMock, patch

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from PySide6.QtCore import QCoreApplication
from ExtensionManager import (
    ExtensionManager,
    make_command_non_interactive,
    get_official_manual_fallback,
    is_installer_in_progress,
    set_test_installer_in_progress,
    wait_for_installer_lock,
    get_managed_tools_dir,
    install_portable_runtime,
    set_test_portable_download_hook,
    set_test_java_environment,
    discover_installed_jdks,
    find_compatible_jdk
)
from FormatterManager import FormatterManager


class TestCommandFirstSmartInstall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    def setUp(self):
        self.ext_mgr = ExtensionManager()
        self.fmt_mgr = FormatterManager(extension_manager=self.ext_mgr)
        self.ext_mgr._formatter_manager = self.fmt_mgr
        ExtensionManager.set_ai_provider(None)
        set_test_java_environment(None, None)
        set_test_installer_in_progress(None)
        set_test_portable_download_hook(None)

    def tearDown(self):
        ExtensionManager.set_ai_provider(None)
        set_test_java_environment(None, None)
        set_test_installer_in_progress(None)
        set_test_portable_download_hook(None)

    # --------------------------------------------------------------------------
    # Scenario 1: A dependency that is already installed
    # --------------------------------------------------------------------------
    def test_01_dependency_already_installed(self):
        """
        Decision Order #1: Use an existing compatible tool or runtime.
        When a compatible tool/runtime is already present on the system,
        Smart Install detects it and configures the environment without running a package install.
        """
        # Simulate active Java 17 and an installed compatible JDK 21 in Microsoft folder
        jdk21_dir = os.path.abspath(os.path.join(tempfile.gettempdir(), "test_jdk21_installed"))
        bin_dir = os.path.join(jdk21_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        java_exe = os.path.join(bin_dir, "java.exe" if sys.platform.startswith("win") else "java")
        with open(java_exe, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")

        set_test_java_environment(
            active_info={
                "executable": r"C:\Java\jdk-17\bin\java.exe",
                "version": "17.0.2",
                "major_version": 17,
                "java_home": r"C:\Java\jdk-17"
            },
            discovered_jdks=[
                {
                    "path": jdk21_dir,
                    "java_exe": java_exe,
                    "version": "21.0.6",
                    "major_version": 21
                }
            ]
        )

        ctx = self.ext_mgr.create_smart_install_context(
            operation="Format Java Document",
            operation_type="formatter",
            language="java",
            file_path="Test.java",
            executable="google-java-format",
            detected_missing_dependency="google-java-format",
            stderr="java.lang.ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern",
            error_message="Runtime requires JDK 21+"
        )

        proposal = self.ext_mgr.resolve_smart_install_context(ctx)

        # Must detect compatible JDK 21, configure runtime, and NOT suggest reinstalling
        self.assertIn(proposal["strategy"], ("existing_compatible_tool", "existing_compatible_runtime"))
        self.assertTrue(proposal.get("isInstalled", False))
        self.assertEqual(proposal["command"], "")  # No installation command required!

        # Check configured runtime in ExtensionManager
        cfg = self.ext_mgr.get_tool_runtime_config("google-java-format")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.get("JAVA_HOME"), jdk21_dir)
        self.assertEqual(cfg.get("version"), "21.0.6")

    # --------------------------------------------------------------------------
    # Scenario 2: A dependency installable silently through a package manager
    # --------------------------------------------------------------------------
    def test_02_dependency_installable_silently_through_package_manager(self):
        """
        Decision Order #2: Use package manager in command-line mode with documented silent flags.
        Verifies make_command_non_interactive adds --silent, --accept-source-agreements,
        --accept-package-agreements for winget, -y --no-progress for choco, and --no-input for pip.
        """
        winget_in = "winget install --id Google.GoogleJavaFormat -e"
        winget_out = make_command_non_interactive(winget_in)
        self.assertIn("--silent", winget_out)
        self.assertIn("--accept-source-agreements", winget_out)
        self.assertIn("--accept-package-agreements", winget_out)

        choco_in = "choco install llvm"
        choco_out = make_command_non_interactive(choco_in)
        self.assertIn("-y", choco_out)
        self.assertIn("--no-progress", choco_out)

        pip_in = "pip install black"
        pip_out = make_command_non_interactive(pip_in)
        self.assertIn("--no-input", pip_out)

        # Context resolution with AI proposal produces non-interactive commands
        def mock_ai_resolver(prompt):
            return '{"tool": "awesome-tool", "package": "Awesome.Tool", "executable": "awesome-tool", "command": "winget install --id Awesome.Tool -e", "steps": ["winget install --id Awesome.Tool -e"], "verificationCommand": "awesome-tool --version", "explanation": "Installs awesome-tool silently via winget."}'

        ExtensionManager.set_ai_provider(mock_ai_resolver)

        with patch("ExtensionManager.locate_executable", return_value=None):
            ctx = self.ext_mgr.create_smart_install_context(
                operation="Install Developer Tool",
                operation_type="tool",
                language="general",
                executable="awesome-tool",
                detected_missing_dependency="awesome-tool",
                error_message="awesome-tool not found"
            )

            proposal = self.ext_mgr.resolve_smart_install_context(ctx)
            self.assertIn("--silent", proposal["command"])
            self.assertIn("--accept-package-agreements", proposal["command"])
            self.assertEqual(proposal["strategy"], "package_manager_silent")

    # --------------------------------------------------------------------------
    # Scenario 3: A tool available as a portable archive
    # --------------------------------------------------------------------------
    def test_03_tool_available_as_portable_archive(self):
        """
        Decision Order #3: Use portable installation when appropriate.
        Extracts into managed directory (~/.dgx/tools/), verifies archive integrity,
        checks architecture, configures runtime explicitly without polluting system PATH.
        """
        # Create a mock zip containing a JDK 21 directory structure
        mock_zip_dir = tempfile.mkdtemp(prefix="mock_jdk_build_")
        jdk_inner = os.path.join(mock_zip_dir, "jdk-21.0.6")
        jdk_bin = os.path.join(jdk_inner, "bin")
        os.makedirs(jdk_bin, exist_ok=True)
        java_exe_name = "java.exe" if sys.platform.startswith("win") else "java"
        mock_java_exe = os.path.join(jdk_bin, java_exe_name)
        with open(mock_java_exe, "w") as f:
            f.write("#!/bin/sh\necho 'openjdk version \"21.0.6\" 2024-10-15'\nexit 0\n")
        with open(os.path.join(jdk_inner, "release"), "w") as f:
            f.write('JAVA_VERSION="21.0.6"\nOS_NAME="Windows"\n')

        # Zip it up into a sample archive
        sample_zip_path = os.path.join(mock_zip_dir, "test_jdk.zip")
        with zipfile.ZipFile(sample_zip_path, "w") as zf:
            for root, dirs, files in os.walk(jdk_inner):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, mock_zip_dir)
                    zf.write(full_p, rel_p)

        # Hook portable downloader to copy this sample zip
        def mock_downloader(url, target_path):
            shutil.copyfile(sample_zip_path, target_path)
            return True

        set_test_portable_download_hook(mock_downloader)

        # Run portable installation
        with patch("platform.machine", return_value="AMD64"), \
             patch("sys.platform", "win32"), \
             patch("subprocess.run") as mock_subproc:
            mock_subproc.return_value = MagicMock(returncode=0, stdout='openjdk version "21.0.6" 2024-10-15', stderr="")
            ok, java_path, ver_str, err = install_portable_runtime("openjdk", min_version=21, run_id="test_run_03")

            self.assertTrue(ok, f"Portable install failed: {err}")
            self.assertTrue(os.path.isfile(java_path))
            self.assertEqual(ver_str, "21.0.6")
            self.assertIn(".dgx", java_path)
            self.assertIn("tools", java_path)

        # Cleanup mock build dir
        shutil.rmtree(mock_zip_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # Scenario 4: A package requiring interactive installation
    # --------------------------------------------------------------------------
    def test_04_package_requiring_interactive_installation(self):
        """
        Decision Order #5: Manual fallback when an installation requires interactive GUI
        or cannot run silently.
        Provides official vendor link, exact action, verification command, and resume instructions.
        Never fabricates download URLs.
        """
        # When AI or analysis discovers interactive requirement:
        fallback = get_official_manual_fallback(
            "openjdk",
            reason="Installer requires interactive GUI wizard and UAC credential dialog."
        )

        self.assertEqual(fallback["resolutionType"], "manual_installation_required")
        self.assertIn("learn.microsoft.com", fallback["officialUrl"])
        self.assertIn("learn.microsoft.com", fallback["downloadUrl"])
        self.assertTrue(len(fallback["actionRequired"]) > 0)
        self.assertEqual(fallback["verificationCommand"], "java -version")
        self.assertIn("automatically detect", fallback["resumeNote"])

        # Also test with google-java-format
        gjf_fallback = get_official_manual_fallback("google-java-format")
        self.assertIn("github.com/google/google-java-format", gjf_fallback["officialUrl"])
        self.assertEqual(gjf_fallback["verificationCommand"], "google-java-format --version")

    # --------------------------------------------------------------------------
    # Scenario 5: An installation already in progress (code 1618 / mutex wait)
    # --------------------------------------------------------------------------
    def test_05_installation_already_in_progress(self):
        """
        Section 3: Windows Installer handling.
        Detects when another installation of the same package / MSI is active (code 1618).
        Waits for existing installation to finish without terminating msiexec or unrelated processes.
        Reports progress and retries step once lock clears.
        """
        poll_count = 0
        def simulated_installer_state():
            nonlocal poll_count
            poll_count += 1
            # Active for the first 2 polls, then releases
            return poll_count <= 2

        set_test_installer_in_progress(simulated_installer_state)

        progress_messages = []
        def on_progress(msg):
            progress_messages.append(msg)

        with patch("time.sleep", return_value=None):
            lock_cleared = wait_for_installer_lock(timeout=10, progress_cb=on_progress, run_id="test_run_05")

        self.assertTrue(lock_cleared)
        self.assertTrue(len(progress_messages) > 0)
        self.assertIn("Waiting", progress_messages[0])

        # Test execute_command_steps with exit code 1618 retry
        run_count = 0
        def mock_step_runner(*args, **kwargs):
            nonlocal run_count
            run_count += 1
            if run_count == 1:
                # First run fails with 1618 (ERROR_INSTALL_ALREADY_RUNNING)
                return MagicMock(returncode=1618, stdout="", stderr="Another installation is already in progress. Complete that installation before proceeding.")
            # Second run succeeds after lock clear
            return MagicMock(returncode=0, stdout="Successfully installed.", stderr="")

        # Set installer lock to clear after 1 poll
        set_test_installer_in_progress(lambda: False)

        with patch("subprocess.run", side_effect=mock_step_runner), \
             patch("time.sleep", return_value=None):
            steps = ["winget install --id Microsoft.OpenJDK.21 --silent"]
            code, stdout, stderr, step_results = self.ext_mgr.execute_command_steps(steps, run_id="test_run_1618")

            self.assertEqual(code, 0)
            self.assertEqual(run_count, 2)  # Proves it retried cleanly without killing processes

    # --------------------------------------------------------------------------
    # Scenario 6: A failed installation
    # --------------------------------------------------------------------------
    def test_06_failed_installation(self):
        """
        Execution failure handling:
        When a command step fails (exit code != 0), halts dependent steps,
        captures real exit code and diagnostic stderr, and does not claim false success.
        """
        step1_called = False
        step2_called = False

        def mock_failing_runner(*args, **kwargs):
            nonlocal step1_called, step2_called
            cmd_arg = args[0] if args else kwargs.get("args", "")
            cmd_str = " ".join(cmd_arg) if isinstance(cmd_arg, (list, tuple)) else str(cmd_arg)
            if "tasklist" in cmd_str:
                return MagicMock(returncode=0, stdout="", stderr="")
            if "pkg1" in cmd_str:
                step1_called = True
                return MagicMock(returncode=1, stdout="", stderr="Fatal: package repository unavailable (HTTP 404)")
            if "pkg2" in cmd_str:
                step2_called = True
                return MagicMock(returncode=0, stdout="OK", stderr="")
            return MagicMock(returncode=1, stdout="", stderr="Unknown")

        with patch("subprocess.run", side_effect=mock_failing_runner):
            steps = ["winget install pkg1 --silent", "winget install pkg2 --silent"]
            code, stdout, stderr, step_results = self.ext_mgr.execute_command_steps(steps, run_id="test_run_06")

            self.assertEqual(code, 1)
            self.assertIn("HTTP 404", stderr)
            self.assertTrue(step1_called)
            self.assertFalse(step2_called, "Dependent steps must NOT execute when previous step failed!")

    # --------------------------------------------------------------------------
    # Scenario 7: A blocked download
    # --------------------------------------------------------------------------
    def test_07_blocked_download(self):
        """
        Decision Order #3 & #5: Blocked download handling.
        When portable runtime download fails (e.g. firewall blocked or offline),
        catches the network error, halts safely, and falls back to official manual vendor link.
        """
        def mock_blocked_downloader(url, target_path):
            raise RuntimeError("Connection refused: 403 Forbidden by corporate firewall proxy")

        set_test_portable_download_hook(mock_blocked_downloader)

        with patch("platform.machine", return_value="AMD64"), \
             patch("sys.platform", "win32"):
            ok, path, ver, err = install_portable_runtime("openjdk", min_version=21, run_id="test_run_07")

            self.assertFalse(ok)
            self.assertEqual(path, "")
            self.assertIn("Connection refused", err)

        # Fallback to official vendor link
        fallback = get_official_manual_fallback("openjdk", reason=err)
        self.assertEqual(fallback["resolutionType"], "manual_installation_required")
        self.assertTrue(fallback["downloadUrl"].startswith("https://learn.microsoft.com"))

    # --------------------------------------------------------------------------
    # Scenario 8: Successful installation followed by failed verification
    # --------------------------------------------------------------------------
    def test_08_successful_installation_followed_by_failed_verification(self):
        """
        Section 8: Logging and verification.
        Distinguish successful installation from successful operation.
        When installation exits with 0 but verification command exits != 0 or missing binary,
        the workflow must NOT claim SUCCESS.
        """
        # AI returns SUCCESS incorrectly despite verification exit code 1
        def mock_ai_resolver(prompt):
            return "SUCCESS"

        ExtensionManager.set_ai_provider(mock_ai_resolver)

        # Diagnose result when install was 0, but verification command was 1
        status, fix_cmd, explanation = self.ext_mgr.diagnose_post_install_result(
            tool_name="google-java-format",
            command="winget install --id Google.GoogleJavaFormat --silent",
            install_exit_code=0,
            install_stdout="Successfully installed",
            install_stderr="",
            verify_cmd="google-java-format --version",
            verify_exit_code=1,
            verify_stdout="",
            verify_stderr="'google-java-format' is not recognized as an internal or command",
            executable="google-java-format",
            verified_path="",
            operation_attempted="format",
            operation_exit_code=1,
            operation_error="Binary not found on PATH"
        )

        # Must reject false SUCCESS and recognize failure
        self.assertNotEqual(status, "SUCCESS")
        self.assertIn(status, ("FIX", "FAILED"))

    # --------------------------------------------------------------------------
    # Scenario 9: Successful installation and successful original operation
    # --------------------------------------------------------------------------
    def test_09_successful_installation_and_successful_original_operation(self):
        """
        Section 8 & 9: Successful installation AND verified operational success.
        Install exits 0, verify exits 0, and retried formatting operation exits 0.
        Workflow accurately reports genuine success.
        """
        # Create dummy verified tool binary
        temp_tool_dir = tempfile.mkdtemp(prefix="test_tool_bin_")
        tool_exe = os.path.join(temp_tool_dir, "google-java-format.exe" if sys.platform.startswith("win") else "google-java-format")
        with open(tool_exe, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")

        status, fix_cmd, explanation = self.ext_mgr.diagnose_post_install_result(
            tool_name="google-java-format",
            command="winget install --id Google.GoogleJavaFormat --silent",
            install_exit_code=0,
            install_stdout="Successfully installed",
            install_stderr="",
            verify_cmd="google-java-format --version",
            verify_exit_code=0,
            verify_stdout="google-java-format 1.25.0",
            verify_stderr="",
            executable="google-java-format",
            verified_path=tool_exe,
            operation_attempted="format",
            operation_exit_code=0,
            operation_stdout="Code formatted successfully",
            operation_stderr=""
        )

        self.assertEqual(status, "SUCCESS")
        self.assertEqual(fix_cmd, "")

        shutil.rmtree(temp_tool_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # Scenario 10: Concrete Java Formatter Workflow (Section 5)
    # --------------------------------------------------------------------------
    def test_10_java_formatter_runtime_upgrade_workflow(self):
        """
        Section 5: Concrete Java Formatter workflow:
        1. Detect existing compatible JDK.
        2. If exists, configure formatter to use it.
        3. Otherwise, try silent CLI install of JDK 21.
        4. If blocked, consider official portable JDK archive.
        5. Verify actual Java executable and version used.
        6. Retry formatting.
        7. Report success only if formatting actually succeeds.
        """
        # Step 1-2: No compatible JDK in PATH (Java 17 active)
        set_test_java_environment(
            active_info={
                "executable": r"C:\Java\jdk-17\bin\java.exe",
                "version": "17.0.2",
                "major_version": 17,
                "java_home": r"C:\Java\jdk-17"
            },
            discovered_jdks=[]  # No JDK 21 discovered initially
        )

        # AI diagnoses runtime incompatibility and proposes silent winget install
        def mock_ai_runtime_fix(prompt):
            return "[FIX]winget install --id Microsoft.OpenJDK.21 -e\nRoot cause: Active Java 17 lacks compiler internals required by google-java-format 1.25.0."

        ExtensionManager.set_ai_provider(mock_ai_runtime_fix)

        # Post-install diagnosis with Java 17 operational failure
        status, fix_cmd, explanation = self.ext_mgr.diagnose_post_install_result(
            tool_name="google-java-format",
            command="winget install --id Google.GoogleJavaFormat --silent",
            install_exit_code=0,
            install_stdout="Installed",
            install_stderr="",
            verify_cmd="google-java-format --version",
            verify_exit_code=0,
            verify_stdout="google-java-format 1.25.0",
            verify_stderr="",
            executable="google-java-format",
            operation_attempted="format",
            operation_exit_code=1,
            operation_error="java.lang.ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern",
            fix_attempt_count=0
        )

        # Step 3: Must propose non-interactive CLI installation of JDK 21
        self.assertEqual(status, "FIX")
        self.assertIn("Microsoft.OpenJDK.21", fix_cmd)
        self.assertIn("--silent", fix_cmd)
        self.assertIn("--accept-package-agreements", fix_cmd)

        ExtensionManager.set_ai_provider(None)

        # Step 4: If package installer was blocked/attempted, falls back to portable OpenJDK
        mock_zip_dir = tempfile.mkdtemp(prefix="mock_portable_jdk_")
        jdk_inner = os.path.join(mock_zip_dir, "jdk-21.0.6")
        jdk_bin = os.path.join(jdk_inner, "bin")
        os.makedirs(jdk_bin, exist_ok=True)
        java_exe = os.path.join(jdk_bin, "java.exe" if sys.platform.startswith("win") else "java")
        with open(java_exe, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        with open(os.path.join(jdk_inner, "release"), "w") as f:
            f.write('JAVA_VERSION="21.0.6"\n')

        sample_zip = os.path.join(mock_zip_dir, "jdk.zip")
        with zipfile.ZipFile(sample_zip, "w") as zf:
            for root, dirs, files in os.walk(jdk_inner):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, mock_zip_dir)
                    zf.write(full_p, rel_p)

        set_test_portable_download_hook(lambda u, t: shutil.copyfile(sample_zip, t) or True)

        # Mock successful formatting retry when portable JDK is applied
        with patch.object(self.ext_mgr, "retry_formatting_operation", return_value=(0, "Formatted OK", "")), \
             patch("platform.machine", return_value="AMD64"), \
             patch("sys.platform", "win32"), \
             patch("subprocess.run") as mock_subproc:
            mock_subproc.return_value = MagicMock(returncode=0, stdout='openjdk version "21.0.6"', stderr="")

            status2, fix2, exp2 = self.ext_mgr.diagnose_post_install_result(
                tool_name="google-java-format",
                command="winget install --id Google.GoogleJavaFormat --silent",
                install_exit_code=0,
                install_stdout="Installed",
                install_stderr="",
                verify_cmd="google-java-format --version",
                verify_exit_code=0,
                verify_stdout="google-java-format 1.25.0",
                verify_stderr="",
                executable="google-java-format",
                operation_attempted="format",
                operation_exit_code=1,
                operation_error="java.lang.ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern",
                fix_attempt_count=1  # Second attempt triggers portable runtime installation
            )

            # Step 7: Must report SUCCESS because formatting retry succeeded with portable JDK 21!
            self.assertEqual(status2, "SUCCESS")
            self.assertIn("portable OpenJDK", exp2)

        shutil.rmtree(mock_zip_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
