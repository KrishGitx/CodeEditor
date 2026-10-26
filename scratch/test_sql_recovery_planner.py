"""
test_sql_recovery_planner.py - Regression Test Suite for Smart Install SQL Recovery

Covers:
1. Ambiguous SQL database type: ask the user instead of guessing.
2. Confirmed SQL Server target with a missing client.
3. An installed client that is missing from PATH.
4. SQL recovery entering the new command-planning workflow.
5. Invalid compound commands remaining blocked.
6. Successful tool installation followed by failed SQL execution.

Do NOT install software during these tests.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ExtensionManager import (
    ExtensionManager,
    locate_executable,
    RecoverySession,
    CommandRecord
)


class TestSQLRecoveryPlanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance()
        if not cls.app:
            cls.app = QGuiApplication(sys.argv)
        # Create single ExtensionManager instance
        cls.ext_mgr = ExtensionManager()

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.old_resolver = ExtensionManager._custom_ai_resolver

        def mock_ai_resolver(prompt):
            p_str = str(prompt).lower()
            if "total steps" in p_str or "command planner" in p_str or "active_batch" in p_str or "cmd-" in p_str or "history" in p_str:
                return json.dumps({
                    "plan_changed": True,
                    "proposed_total_steps": 2,
                    "commands": [
                        {"command": "sqlcmd -?", "purpose": "Check installed client", "requires_approval": False},
                        {"command": "winget install --id Microsoft.SqlCmd -e --silent", "purpose": "Install sqlcmd client", "requires_approval": True}
                    ],
                    "needs_user_decision": True,
                    "recovery_complete": False
                })
            elif "post-install" in p_str or "diagnostic and recovery" in p_str:
                return "FAILED\nCannot execute SQL script: Database connection settings are not configured. A running database server is required."
            else:
                return json.dumps({
                    "resolutionType": "single_command",
                    "source": "ai",
                    "title": "Install sqlcmd",
                    "diagnosis": "Missing sqlcmd utility",
                    "explanation": "Install Microsoft's SQL Server command-line utility.",
                    "command": "winget install --id Microsoft.SqlCmd -e --silent",
                    "steps": ["Install sqlcmd"],
                    "verificationCommand": "sqlcmd -?",
                    "tool": "sqlcmd",
                    "package": "Microsoft.Sqlcmd",
                    "executable": "sqlcmd",
                    "retryOperation": True
                })

        ExtensionManager._custom_ai_resolver = mock_ai_resolver

    def tearDown(self):
        ExtensionManager._custom_ai_resolver = self.old_resolver
        import shutil
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # =========================================================================
    # Test 1: Ambiguous SQL database type: ask the user instead of guessing
    # =========================================================================
    def test_01_ambiguous_sql_database_type_asks_user(self):
        """
        When running an ambiguous .sql file without database configuration or engine markers:
        - Engine cannot be determined.
        - AI/system must NOT guess Microsoft's sqlcmd or install any client.
        - Must ask the user which database they intend to use.
        - Distinguishes database client from database server.
        """
        # Create a generic .sql file with standard SQL (no engine markers)
        sql_file = os.path.join(self.tmp_dir, "migration.sql")
        with open(sql_file, "w", encoding="utf-8") as f:
            f.write("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(100));\n")

        context = {
            "operation": "Run SQL Script",
            "operationType": "sql",
            "language": "sql",
            "filePath": sql_file,
            "errorMessage": "No runner configured for .sql files."
        }

        # 1. Verify engine detection returns ambiguous
        db_target = self.ext_mgr.detect_target_database_engine(context, sql_file)
        self.assertTrue(db_target["is_ambiguous"], "Target engine should be identified as ambiguous")
        self.assertIsNone(db_target["client_tool"], "No client tool should be guessed for ambiguous SQL")

        # 2. Verify resolve_smart_install_context returns awaiting_user_decision without guessing sqlcmd
        proposal = self.ext_mgr.resolve_smart_install_context(context)
        self.assertEqual(proposal.get("actionType"), "ask_database_type")
        self.assertEqual(proposal.get("resolutionType"), "cannot_resolve")
        self.assertTrue(proposal.get("needs_user_decision"), "Proposal must require user decision")
        self.assertEqual(proposal.get("status"), "awaiting_user_decision")
        self.assertIn("options", proposal, "Proposal must provide options for user selection")
        self.assertIn("SQLite", proposal["options"])
        self.assertIn("SQL Server", proposal["options"])
        self.assertIn("PostgreSQL", proposal["options"])
        self.assertEqual(proposal.get("command", ""), "", "Command must be empty: no automatic installer guessed")
        # Ensure it explains client vs server distinction
        self.assertIn("database server", proposal.get("explanation", "").lower())
        print("[PASS] Test 1: Ambiguous SQL database type asks user with options without guessing sqlcmd")

    # =========================================================================
    # Test 2: Confirmed SQL Server target with a missing client
    # =========================================================================
    def test_02_confirmed_sql_server_target_with_missing_client(self):
        """
        When SQL Server is confirmed as target (e.g. dialect marker or context) and client is missing:
        - Target engine is identified as Microsoft SQL Server.
        - The required client tool is identified as sqlcmd.
        - Proposes installing sqlcmd (with official silent parameters) without ambiguity.
        """
        sql_file = os.path.join(self.tmp_dir, "stored_proc.sql")
        with open(sql_file, "w", encoding="utf-8") as f:
            f.write("-- dialect: sqlserver\nUSE [master];\nGO\nSELECT * FROM sys.tables;\nGO\n")

        context = {
            "operation": "Execute SQL Script",
            "operationType": "sql",
            "language": "sql",
            "filePath": sql_file,
            "errorMessage": "No runner configured for .sql files."
        }

        # Detect engine from dialect marker
        db_target = self.ext_mgr.detect_target_database_engine(context, sql_file)
        self.assertFalse(db_target["is_ambiguous"], "Target engine should not be ambiguous")
        self.assertEqual(db_target["engine"], "sqlserver")
        self.assertEqual(db_target["client_tool"], "sqlcmd")

        # Mock locate_executable to simulate missing sqlcmd
        with patch("ExtensionManager.locate_executable", return_value=None):
            with patch("shutil.which", return_value=None):
                proposal = self.ext_mgr.resolve_smart_install_context(context)
                self.assertEqual(proposal.get("toolName"), "sqlcmd")
                self.assertFalse(proposal.get("isInstalled", True))
                # Command should install sqlcmd
                cmd = proposal.get("command", "")
                self.assertTrue(cmd != "", "Installation command should be proposed for missing sqlcmd")
                self.assertIn("sqlcmd", cmd.lower())
                self.assertIn("silent", cmd.lower())
        print("[PASS] Test 2: Confirmed SQL Server target correctly identifies sqlcmd as missing client")

    # =========================================================================
    # Test 3: An installed client that is missing from PATH
    # =========================================================================
    def test_03_installed_client_missing_from_path(self):
        """
        When sqlcmd exists on disk but is missing from current process PATH:
        - System locates the actual executable on disk.
        - System verifies it through its actual executable path.
        - Does NOT propose installing sqlcmd again.
        - Prepares PATH/runtime environment configuration.
        """
        fake_bin_dir = os.path.join(self.tmp_dir, "sqlcmd_bin")
        os.makedirs(fake_bin_dir, exist_ok=True)
        fake_sqlcmd = os.path.join(fake_bin_dir, "sqlcmd.exe")
        with open(fake_sqlcmd, "w", encoding="utf-8") as f:
            f.write("@echo off\necho Microsoft (R) SQL Server Command-line Tool\nexit /b 0\n")

        sql_file = os.path.join(self.tmp_dir, "query.sql")
        with open(sql_file, "w", encoding="utf-8") as f:
            f.write("-- dialect: sqlserver\nSELECT @@VERSION;\nGO\n")

        context = {
            "operation": "Execute SQL Script",
            "operationType": "failure",
            "language": "sql",
            "filePath": sql_file,
            "executable": "sqlcmd",
            "errorMessage": "'sqlcmd' is not recognized as an internal or external command."
        }

        # Mock shutil.which("sqlcmd") -> None (missing from current process PATH)
        # Mock locate_executable("sqlcmd") -> fake_sqlcmd (found on disk)
        with patch("shutil.which", return_value=None):
            with patch("ExtensionManager.locate_executable", return_value=fake_sqlcmd):
                # Also mock retry_sql_operation to succeed once PATH is configured
                with patch.object(self.ext_mgr, "retry_sql_operation", return_value=(0, "Microsoft SQL Server 2022", "")):
                    proposal = self.ext_mgr.resolve_smart_install_context(context)
                    self.assertEqual(proposal.get("toolName"), "sqlcmd")
                    self.assertTrue(proposal.get("isInstalled"), "Must recognize that tool is already installed")
                    self.assertEqual(proposal.get("command", ""), "", "Must not propose a new installation command")
                    self.assertEqual(proposal.get("status"), "already_installed")
                    self.assertEqual(proposal.get("verifiedPath"), fake_sqlcmd)
                    # Verify runtime config PATH_PREPEND was set
                    cfg = self.ext_mgr.get_tool_runtime_config("sqlcmd")
                    self.assertEqual(cfg.get("PATH_PREPEND"), fake_bin_dir)
        print("[PASS] Test 3: Installed client missing from PATH discovered, verified via actual path, no reinstall")

    # =========================================================================
    # Test 4: SQL recovery entering the new command-planning workflow
    # =========================================================================
    def test_04_sql_recovery_enters_recovery_session(self):
        """
        When SQL recovery requires command-based installation:
        - Enters the new RecoverySession command-planning workflow.
        - Assigns sequential CMD-XX IDs.
        - Up to 4 commands per batch.
        - Tracks step counts and budget (maximum 10).
        - Enforces user approval for installation steps while harmless queries do not require approval.
        """
        sql_file = os.path.join(self.tmp_dir, "db.sql")
        with open(sql_file, "w", encoding="utf-8") as f:
            f.write("-- dialect: sqlserver\nCREATE TABLE test (id INT);\nGO\n")

        context = {
            "operation": "Install sqlcmd",
            "operationType": "sql",
            "language": "sql",
            "filePath": sql_file,
            "toolName": "sqlcmd",
            "executable": "sqlcmd",
            "errorMessage": "No runner configured for .sql files."
        }

        with patch("ExtensionManager.locate_executable", return_value=None):
            with patch("shutil.which", return_value=None):
                proposal = self.ext_mgr.suggest_smart_install_for_failure(
                    operation="Run SQL",
                    error_output="No runner configured for .sql files.",
                    exit_code=1,
                    failed_command="sqlcmd -i db.sql",
                    lang_id="sql",
                    file_path=sql_file
                )

                # Verify RecoverySession was attached
                self.assertEqual(proposal.get("resolutionType"), "recovery_session")
                self.assertTrue("sessionId" in proposal or "session_id" in proposal)
                session_id = proposal.get("sessionId") or proposal.get("session_id")
                session = self.ext_mgr._recovery_sessions.get(session_id)
                self.assertIsNotNone(session, "Recovery session must be registered")

                # Verify active batch commands
                batch = session.active_batch
                self.assertGreaterEqual(len(batch), 1)
                self.assertLessEqual(len(batch), 4, "Batch size must not exceed 4 commands")

                # Verify sequential CMD-XX IDs
                for idx, cmd_rec in enumerate(batch, 1):
                    expected_id = f"CMD-{idx:02d}"
                    self.assertEqual(cmd_rec.command_id, expected_id)

                # Verify total steps and budget tracking
                self.assertEqual(session.total_steps, len(batch) + len(session.pending_queue))
                self.assertEqual(session.maximum_commands, 10)
                self.assertEqual(session.commands_remaining, 10)

                # Verify user approval requirement: install command requires approval, query does not
                for cmd_rec in batch:
                    if "install" in cmd_rec.command.lower():
                        self.assertTrue(cmd_rec.requires_approval, "Installation step must require user approval")
                    elif "-?" in cmd_rec.command or "--version" in cmd_rec.command:
                        self.assertFalse(cmd_rec.requires_approval, "Query/version check should not require approval")
        print("[PASS] Test 4: SQL recovery enters RecoverySession with CMD-XX IDs, budget, and approval checks")

    # =========================================================================
    # Test 5: Invalid compound commands remaining blocked
    # =========================================================================
    def test_05_invalid_compound_commands_remain_blocked(self):
        """
        Validates that validate_command_safety() blocks compound PowerShell scripts,
        chaining operators (&&, ;, ||, |), backgrounding, and destructive operations,
        while permitting legitimate single commands and PowerShell call-operator invocations.
        """
        # Blocked: chaining and compounding
        unsafe_commands = [
            'winget install Microsoft.SqlCmd ; sqlcmd -?',
            'winget install Microsoft.SqlCmd && sqlcmd -?',
            'sqlcmd -? | grep version',
            'sqlcmd -? || echo failed',
            '& "C:\\tools\\sqlcmd.exe" -? & calc.exe',
            'powershell -Command "winget install Microsoft.SqlCmd; sqlcmd -?"',
            'drop database master',
            'rm -rf /',
            'winget install Microsoft.SqlCmd\nsqlcmd -?'
        ]

        for cmd in unsafe_commands:
            is_safe, reason = ExtensionManager.validate_command_safety(cmd, tool_name="sqlcmd")
            self.assertFalse(is_safe, f"Command should be blocked: '{cmd}'")
            self.assertTrue(len(reason) > 0)

        # Allowed: legitimate individual diagnostic and installation commands
        safe_commands = [
            'winget install --id Microsoft.SqlCmd -e --silent --accept-package-agreements --accept-source-agreements',
            'sqlcmd -?',
            'sqlcmd --version',
            'where sqlcmd',
            'Get-Command sqlcmd',
            '& "C:\\Program Files\\Microsoft SQL Server\\Client SDK\\ODBC\\170\\Tools\\Binn\\sqlcmd.exe" -?',
            'setx FOO BAR'
        ]

        for cmd in safe_commands:
            is_safe, reason = ExtensionManager.validate_command_safety(cmd, tool_name="sqlcmd")
            self.assertTrue(is_safe, f"Legitimate command should be permitted: '{cmd}' -> {reason}")
        print("[PASS] Test 5: Compound commands and chaining strictly blocked; legitimate commands allowed")

    # =========================================================================
    # Test 6: Successful tool installation followed by failed SQL execution
    # =========================================================================
    def test_06_successful_installation_followed_by_failed_sql_execution(self):
        """
        When tool installation returns exit code 0 and tool verifies successfully,
        BUT SQL file execution fails (e.g. database connection not configured or server offline):
        - System must NOT declare overall success.
        - System must capture actual operational error.
        - Post-install diagnosis returns non-success failure (FAILED or MANUAL_INSTALLATION_REQUIRED)
          with the real operational error.
        """
        fake_sqlcmd = os.path.join(self.tmp_dir, "sqlcmd.exe")
        with open(fake_sqlcmd, "w", encoding="utf-8") as f:
            f.write("@echo off\nexit /b 0\n")

        # 1. Test diagnose_post_install_result directly with operational failure
        conn_err = (
            "Cannot execute SQL script: Database connection settings (server/host, database, credentials) "
            "for Microsoft SQL Server are not configured. Installing the database client does not establish a connection "
            "or provide a running database server."
        )

        status, fix_cmd, explanation = self.ext_mgr.diagnose_post_install_result(
            tool_name="sqlcmd",
            command="winget install --id Microsoft.SqlCmd -e --silent",
            install_exit_code=0,
            install_stdout="Successfully installed",
            install_stderr="",
            verify_cmd=f'"{fake_sqlcmd}" -?',
            verify_exit_code=0,
            verify_stdout="Microsoft (R) SQL Server Command-line Tool",
            verify_stderr="",
            executable=fake_sqlcmd,
            verified_path=fake_sqlcmd,
            operation_attempted="run",
            operation_exit_code=1,
            operation_stderr=conn_err,
            operation_error=conn_err
        )

        self.assertNotEqual(status, "SUCCESS", "Must not report SUCCESS when operational error occurs")
        self.assertIn(status, ("FAILED", "MANUAL_INSTALLATION_REQUIRED"))
        self.assertIn("Database connection settings", explanation)
        self.assertIn("database server", explanation)

        # 2. Test execute_smart_install_command workflow with operational retry failure
        completed_emits = []
        verified_emits = []
        retried_emits = []

        self.ext_mgr.smartInstallCompleted.connect(lambda tool, ok, msg, retry: completed_emits.append((tool, ok, msg, retry)))
        self.ext_mgr.smartInstallPostInstallVerified.connect(lambda tool, stat, msg, retry, fp, extra: verified_emits.append((tool, stat, msg)))
        self.ext_mgr.originalOperationRetried.connect(lambda tool, ok, err: retried_emits.append((tool, ok, err)))

        sql_file = os.path.join(self.tmp_dir, "test.sql")
        with open(sql_file, "w", encoding="utf-8") as f:
            f.write("-- dialect: sqlserver\nSELECT 1;\nGO\n")

        with patch.object(self.ext_mgr, "execute_command_steps", return_value=(0, "Installed", "", [{"step": 1, "exit_code": 0}])):
            with patch("ExtensionManager.locate_executable", return_value=fake_sqlcmd):
                with patch("subprocess.run") as mock_sub:
                    # Mock verification command exit 0
                    mock_v = MagicMock()
                    mock_v.returncode = 0
                    mock_v.stdout = "Microsoft SQL Server Command-line Tool"
                    mock_v.stderr = ""
                    mock_sub.return_value = mock_v

                    # Mock retry_sql_operation returning failure exit code 1
                    with patch.object(self.ext_mgr, "retry_sql_operation", return_value=(1, "", conn_err)):
                        with patch.object(self.ext_mgr, "diagnose_post_install_result", return_value=("FAILED", "", conn_err)):
                            # Execute synchronously in worker
                            res = self.ext_mgr.execute_smart_install_command(
                                tool_name="sqlcmd",
                                command="winget install --id Microsoft.SqlCmd -e --silent",
                                executable="sqlcmd",
                                retry_action="run",
                                file_path=sql_file
                            )
                            self.assertTrue(res)

                            # Wait for worker thread to complete and process Qt queued signals
                            import time
                            for _ in range(40):
                                QCoreApplication.processEvents()
                                if len(completed_emits) > 0 and len(retried_emits) > 0:
                                    break
                                time.sleep(0.05)
                            QCoreApplication.processEvents()

                            # Ensure original operation failure was recorded
                            self.assertTrue(len(retried_emits) > 0, "Original operation retry should be emitted")
                            self.assertFalse(retried_emits[0][1], "Original operation retry should report failure")

                            # Ensure smartInstallCompleted emitted False (not overall success!)
                            self.assertTrue(len(completed_emits) > 0)
                            self.assertFalse(completed_emits[0][1], "Overall completion must be False due to operation failure")
        print("[PASS] Test 6: Successful tool install followed by failed SQL execution properly diagnosed as failure")


if __name__ == "__main__":
    unittest.main()
