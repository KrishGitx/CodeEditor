"""
test_smart_install_command_planner.py - Comprehensive Unit Tests for AI Command Planning and Execution Tracking

Verifies all 16 acceptance test requirements from Section 10:
1. Initial plan with four commands.
2. Plan with fewer than four commands.
3. A dependent command that waits for the previous result.
4. Sequential command IDs (CMD-01, CMD-02, CMD-03...).
5. Correct association of output with command ID.
6. Total-step display updates when the plan changes.
7. Total-step display remains unchanged when the plan does not change.
8. Failed commands count against the command budget.
9. Replanning preserves the remaining budget and next command ID.
10. Duplicate IDs and invalid AI responses are rejected.
11. More than four commands in a batch are rejected or split safely.
12. Installation approval is required.
13. Recovery stops at the command limit.
14. Final diagnosis appears only when recovery ends.
15. Existing Smart Install regression tests still pass.
16. Existing Replace with AI tests remain unchanged and pass.
"""

import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ExtensionManager import (
    ExtensionManager,
    CommandRecord,
    RecoverySession,
    validate_ai_plan_response
)


class TestSmartInstallCommandPlanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance()
        if not cls.app:
            cls.app = QGuiApplication(sys.argv)

    def setUp(self):
        self.ext_mgr = ExtensionManager()
        self.sample_context = {
            "toolName": "shfmt",
            "executable": "shfmt",
            "operation": "Format shell script",
            "operationType": "formatter",
            "filePath": "script.sh",
            "language": "shell",
            "retryAction": "format"
        }

    # --------------------------------------------------------------------------
    # 1. Initial plan with four commands
    # --------------------------------------------------------------------------
    def test_01_initial_plan_four_commands(self):
        """Initial plan proposing four commands accepted into batch with sequential IDs."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        ai_response = {
            "plan_changed": True,
            "proposed_total_steps": 4,
            "commands": [
                {"command": "shfmt --version", "purpose": "Check installed version", "requires_approval": False},
                {"command": "where shfmt", "purpose": "Check PATH location", "requires_approval": False},
                {"command": "winget install mvdan.shfmt", "purpose": "Install shfmt", "requires_approval": True},
                {"command": "shfmt --version", "purpose": "Verify installation", "requires_approval": False}
            ],
            "needs_user_decision": True,
            "recovery_complete": False
        }
        is_valid, parsed, err = validate_ai_plan_response(ai_response, self.ext_mgr, tool_name="shfmt")
        self.assertTrue(is_valid)
        records = session.accept_new_batch(parsed["commands"], parsed["proposed_total_steps"])

        self.assertEqual(len(records), 4)
        self.assertEqual(len(session.active_batch), 4)
        self.assertEqual(session.total_steps, 4)
        self.assertEqual([r.command_id for r in records], ["CMD-01", "CMD-02", "CMD-03", "CMD-04"])
        self.assertEqual(session.format_total_steps_display(), "TOTAL STEPS: 4")
        print("[PASS] Test 01: Initial plan with four commands")

    # --------------------------------------------------------------------------
    # 2. Plan with fewer than four commands
    # --------------------------------------------------------------------------
    def test_02_plan_fewer_than_four_commands(self):
        """Plan with fewer than four commands (e.g. 2 commands)."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        ai_response = {
            "plan_changed": True,
            "proposed_total_steps": 2,
            "commands": [
                {"command": "shfmt --version", "purpose": "Check shfmt version", "requires_approval": False},
                {"command": "winget install mvdan.shfmt", "purpose": "Install shfmt package", "requires_approval": True}
            ],
            "needs_user_decision": True,
            "recovery_complete": False
        }
        is_valid, parsed, err = validate_ai_plan_response(ai_response, self.ext_mgr, tool_name="shfmt")
        self.assertTrue(is_valid)
        records = session.accept_new_batch(parsed["commands"], parsed["proposed_total_steps"])

        self.assertEqual(len(records), 2)
        self.assertEqual(len(session.active_batch), 2)
        self.assertEqual(session.total_steps, 2)
        self.assertEqual([r.command_id for r in records], ["CMD-01", "CMD-02"])
        self.assertEqual(session.format_total_steps_display(), "TOTAL STEPS: 2")
        print("[PASS] Test 02: Plan with fewer than four commands")

    # --------------------------------------------------------------------------
    # 3. A dependent command that waits for the previous result
    # --------------------------------------------------------------------------
    def test_03_dependent_command_waits_for_previous_result(self):
        """A dependent installation command waits for the diagnostic check result and approval."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        commands = [
            {"command": "shfmt --version", "purpose": "Check tool availability", "requires_approval": False},
            {"command": "winget install mvdan.shfmt", "purpose": "Install missing tool", "requires_approval": True}
        ]
        session.accept_new_batch(commands, proposed_total=2)

        # Before executing CMD-01, CMD-02 is still pending and has NOT executed
        cmd1 = session.active_batch[0]
        cmd2 = session.active_batch[1]
        self.assertEqual(cmd1.status, "pending")
        self.assertEqual(cmd2.status, "pending")

        # Mock execution for CMD-01: fails because tool is missing
        def mock_executor(cmd_str):
            if "version" in cmd_str:
                return 1, "", "'shfmt' is not recognized as an internal or external command"
            return 0, "Installed successfully", ""

        session.executor_fn = mock_executor

        # Execute CMD-01
        ok1, res1 = self.ext_mgr.execute_session_command(session.session_id, "CMD-01", executor_fn=mock_executor)
        self.assertFalse(ok1)
        self.assertEqual(cmd1.status, "failed")
        self.assertEqual(session.actual_commands_executed, 1)

        # CMD-02 cannot execute without approval
        ok2, res2 = self.ext_mgr.execute_session_command(session.session_id, "CMD-02", executor_fn=mock_executor)
        self.assertFalse(ok2)
        self.assertIn("explicit user approval", res2)
        self.assertEqual(session.status, "awaiting_approval")
        self.assertEqual(cmd2.status, "pending")

        # Now approve CMD-02
        approved = self.ext_mgr.approve_recovery_command(session.session_id, "CMD-02")
        self.assertTrue(approved)
        self.assertEqual(cmd2.status, "succeeded")
        self.assertEqual(session.actual_commands_executed, 2)
        print("[PASS] Test 03: Dependent command waits for previous result and approval")

    # --------------------------------------------------------------------------
    # 4. Sequential command IDs
    # --------------------------------------------------------------------------
    def test_04_sequential_command_ids(self):
        """Sequential command IDs: CMD-01, CMD-02, CMD-03... Never reuses IDs."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        b1 = session.accept_new_batch([
            {"command": "cmd1", "purpose": "p1"},
            {"command": "cmd2", "purpose": "p2"}
        ])
        self.assertEqual([c.command_id for c in b1], ["CMD-01", "CMD-02"])

        # Subsequent batch gets sequential non-colliding IDs
        b2 = session.accept_new_batch([
            {"command": "cmd3", "purpose": "p3"},
            {"command": "cmd4", "purpose": "p4"}
        ])
        self.assertEqual([c.command_id for c in b2], ["CMD-03", "CMD-04"])
        self.assertEqual(session.next_command_index, 5)
        print("[PASS] Test 04: Sequential command IDs without reuse")

    # --------------------------------------------------------------------------
    # 5. Correct association of output with command ID
    # --------------------------------------------------------------------------
    def test_05_correct_association_of_output_with_command_id(self):
        """Each execution's stdout, stderr, exit code, and formatted text match its exact command ID."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        session.accept_new_batch([
            {"command": "shfmt --version", "purpose": "Check version", "requires_approval": False},
            {"command": "winget install mvdan.shfmt", "purpose": "Install", "requires_approval": False}
        ])

        def mock_executor(cmd_str):
            if "version" in cmd_str:
                return 0, "shfmt v3.7.0", ""
            return 1, "Downloaded package", "Fatal error: access denied"

        self.ext_mgr.execute_session_command(session.session_id, "CMD-01", executor_fn=mock_executor)
        self.ext_mgr.execute_session_command(session.session_id, "CMD-02", executor_fn=mock_executor)

        cmd1 = session.get_command_by_id("CMD-01")
        cmd2 = session.get_command_by_id("CMD-02")

        self.assertEqual(cmd1.exit_code, 0)
        self.assertEqual(cmd1.stdout, "shfmt v3.7.0")
        self.assertEqual(cmd1.stderr, "")
        self.assertIn("CMD-01\nExit code: 0\nOutput:\nshfmt v3.7.0", cmd1.format_result())

        self.assertEqual(cmd2.exit_code, 1)
        self.assertEqual(cmd2.stdout, "Downloaded package")
        self.assertEqual(cmd2.stderr, "Fatal error: access denied")
        self.assertIn("CMD-02\nExit code: 1\nOutput:\nDownloaded package\nFatal error: access denied", cmd2.format_result())
        print("[PASS] Test 05: Output correctly associated with exact command ID")

    # --------------------------------------------------------------------------
    # 6. Total-step display updates when the plan changes
    # --------------------------------------------------------------------------
    def test_06_total_step_display_updates_when_plan_changes(self):
        """Total steps display header updates when total planned step count changes."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        session.accept_new_batch([
            {"command": "c1", "purpose": "p1"},
            {"command": "c2", "purpose": "p2"}
        ], proposed_total=2)

        # Initial display
        self.assertEqual(session.format_total_steps_display(), "TOTAL STEPS: 2")

        # Now replan with total = 4
        session.replan([
            {"command": "c3", "purpose": "p3"},
            {"command": "c4", "purpose": "p4"},
            {"command": "c5", "purpose": "p5"}
        ], proposed_total=4)

        # Total changed from 2 to 4 -> display updates!
        self.assertEqual(session.total_steps, 4)
        self.assertEqual(session.format_total_steps_display(), "TOTAL STEPS: 4")
        print("[PASS] Test 06: Total-step display updates when plan count changes")

    # --------------------------------------------------------------------------
    # 7. Total-step display remains unchanged when the plan does not change
    # --------------------------------------------------------------------------
    def test_07_total_step_display_unchanged_when_plan_does_not_change(self):
        """Total steps display header returns None (not repeated) when total count does not change."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        session.accept_new_batch([
            {"command": "c1", "purpose": "p1"}
        ], proposed_total=3)

        # First query: shows total
        self.assertEqual(session.format_total_steps_display(), "TOTAL STEPS: 3")

        # Second query with unchanged total: returns None (do not repeat total)
        self.assertIsNone(session.format_total_steps_display())
        self.assertIsNone(session.format_total_steps_display())
        print("[PASS] Test 07: Total-step display not repeated when plan count unchanged")

    # --------------------------------------------------------------------------
    # 8. Failed commands count against the command budget
    # --------------------------------------------------------------------------
    def test_08_failed_commands_count_against_budget(self):
        """A command that fails with non-zero exit code still increments executed count and consumes budget."""
        session = self.ext_mgr.create_recovery_session(self.sample_context, maximum_commands=10)
        session.accept_new_batch([{"command": "failing_cmd", "purpose": "fail", "requires_approval": False}])

        def failing_exec(c):
            return 127, "", "command not found"

        ok, out = self.ext_mgr.execute_session_command(session.session_id, "CMD-01", executor_fn=failing_exec)
        self.assertFalse(ok)
        self.assertEqual(session.actual_commands_executed, 1)
        self.assertEqual(session.commands_remaining, 9)
        self.assertEqual(session.failed_steps, 1)
        print("[PASS] Test 08: Failed commands count against budget")

    # --------------------------------------------------------------------------
    # 9. Replanning preserves the remaining budget and next command ID
    # --------------------------------------------------------------------------
    def test_09_replanning_preserves_budget_and_next_id(self):
        """Replanning clears unexecuted commands while preserving budget, history, and next sequential ID."""
        session = self.ext_mgr.create_recovery_session(self.sample_context, maximum_commands=10)
        session.accept_new_batch([
            {"command": "check_cmd", "purpose": "check", "requires_approval": False},
            {"command": "old_unexecuted", "purpose": "unexecuted", "requires_approval": False}
        ])

        # Execute check_cmd (CMD-01)
        self.ext_mgr.execute_session_command(session.session_id, "CMD-01", executor_fn=lambda c: (0, "ok", ""))
        self.assertEqual(session.actual_commands_executed, 1)
        self.assertEqual(session.commands_remaining, 9)
        self.assertEqual(session.next_command_index, 3)

        # Replan with 2 new commands
        new_batch = session.replan([
            {"command": "new_cmd1", "purpose": "new1"},
            {"command": "new_cmd2", "purpose": "new2"}
        ], proposed_total=3)

        # Budget preserved, next IDs start at CMD-03
        self.assertEqual(session.actual_commands_executed, 1)
        self.assertEqual(session.commands_remaining, 9)
        self.assertEqual([c.command_id for c in new_batch], ["CMD-03", "CMD-04"])
        # Completed history preserved
        self.assertEqual(len(session.command_history), 1)
        self.assertEqual(session.command_history[0].command_id, "CMD-01")
        print("[PASS] Test 09: Replanning preserves budget, history, and next command ID")

    # --------------------------------------------------------------------------
    # 10. Duplicate IDs and invalid AI responses are rejected
    # --------------------------------------------------------------------------
    def test_10_duplicate_ids_and_invalid_ai_responses_rejected(self):
        """Rejects duplicate command IDs in AI responses, malformed responses, and all chaining/substitution evasions."""
        # 1. Duplicate ID payload
        dup_payload = {
            "commands": [
                {"id": "CMD-01", "command": "cmd1", "purpose": "p1"},
                {"id": "CMD-01", "command": "cmd2", "purpose": "p2"}
            ]
        }
        is_val, _, err = validate_ai_plan_response(dup_payload, self.ext_mgr)
        self.assertFalse(is_val)
        self.assertIn("Duplicate command ID", err)

        # 2. Malformed JSON
        is_val, _, err = validate_ai_plan_response("{malformed: true", self.ext_mgr)
        self.assertFalse(is_val)

        # 3. Non-object root
        is_val, _, err = validate_ai_plan_response("[1, 2, 3]", self.ext_mgr)
        self.assertFalse(is_val)

        # 4. Unsafe chained command (&&)
        is_val, _, err = validate_ai_plan_response({"commands": [{"command": "echo test && rm -rf /", "purpose": "p"}]}, self.ext_mgr)
        self.assertFalse(is_val)
        self.assertIn("Command safety check failed", err)

        # 5. Semicolon chaining (;)
        is_val, _, err = validate_ai_plan_response({"commands": [{"command": "where shfmt ; calc.exe", "purpose": "p"}]}, self.ext_mgr)
        self.assertFalse(is_val)
        self.assertIn("Command safety check failed", err)

        # 6. Piping (|)
        is_val, _, err = validate_ai_plan_response({"commands": [{"command": "python --version | grep 3", "purpose": "p"}]}, self.ext_mgr)
        self.assertFalse(is_val)
        self.assertIn("Command safety check failed", err)

        # 7. Single ampersand chaining / backgrounding (&)
        is_val, _, err = validate_ai_plan_response({"commands": [{"command": "shfmt --version & calc.exe", "purpose": "p"}]}, self.ext_mgr)
        self.assertFalse(is_val)
        self.assertIn("Command safety check failed", err)

        # 8. Multiline command injection (\n)
        is_val, _, err = validate_ai_plan_response({"commands": [{"command": "shfmt --version\ncalc.exe", "purpose": "p"}]}, self.ext_mgr)
        self.assertFalse(is_val)
        self.assertIn("Command safety check failed", err)

        # 9. Command substitution ($(cmd))
        is_val, _, err = validate_ai_plan_response({"commands": [{"command": "where $(whoami)", "purpose": "p"}]}, self.ext_mgr)
        self.assertFalse(is_val)
        self.assertIn("Command safety check failed", err)

        # 10. Backtick command substitution (`cmd`)
        is_val, _, err = validate_ai_plan_response({"commands": [{"command": "where `whoami`", "purpose": "p"}]}, self.ext_mgr)
        self.assertFalse(is_val)
        self.assertIn("Command safety check failed", err)

        # 11. Encoded command execution (-enc)
        is_val, _, err = validate_ai_plan_response({"commands": [{"command": "powershell -enc AAAAA==", "purpose": "p"}]}, self.ext_mgr)
        self.assertFalse(is_val)
        self.assertIn("Command safety check failed", err)

        # 12. Output redirection (>)
        is_val, _, err = validate_ai_plan_response({"commands": [{"command": "shfmt --version > C:\\out.txt", "purpose": "p"}]}, self.ext_mgr)
        self.assertFalse(is_val)
        self.assertIn("Command safety check failed", err)

        # 13. Legitimate diagnostic queries succeed without allowing chaining
        diagnostic_cmds = [
            "shfmt --version",
            "shfmt -v",
            "where shfmt",
            "which shfmt",
            "python --version",
            "python -V",
            "go version",
            "cargo --version",
            "rustc --version",
            "node -v",
            "git --version",
            "gcc --version",
            "clang --version",
            "java -version",
            "Get-Command shfmt"
        ]
        for cmd in diagnostic_cmds:
            safe, reason = self.ext_mgr.validate_command_safety(cmd)
            self.assertTrue(safe, f"Legitimate diagnostic command rejected: '{cmd}', reason: {reason}")

        print("[PASS] Test 10: Duplicate IDs, malformed responses, and command evasions rejected; legitimate diagnostics accepted")

    # --------------------------------------------------------------------------
    # 11. More than four commands in a batch are rejected or split safely
    # --------------------------------------------------------------------------
    def test_11_more_than_four_commands_rejected_or_split(self):
        """Oversized plans (>4 commands) preserve all pending steps without loss, present up to 4, and promote upon batch completion."""
        five_cmds = {
            "commands": [
                {"command": "pip --version", "purpose": "check version", "requires_approval": False},
                {"command": "where pip", "purpose": "check location", "requires_approval": False},
                {"command": "python --version", "purpose": "check python", "requires_approval": False},
                {"command": "pip list", "purpose": "list packages", "requires_approval": False},
                {"command": "pip install pkg5", "purpose": "p5", "requires_approval": True}
            ]
        }
        # Strict mode rejects
        is_val, _, err = validate_ai_plan_response(five_cmds, self.ext_mgr, allow_oversized_split=False)
        self.assertFalse(is_val)
        self.assertIn("exceeds maximum allowed limit of 4", err)

        # Split mode preserves all 5 commands in plan
        is_val, parsed, _ = validate_ai_plan_response(five_cmds, self.ext_mgr, allow_oversized_split=True)
        self.assertTrue(is_val)
        self.assertEqual(len(parsed["commands"]), 5)
        self.assertEqual(len(parsed["batch_commands"]), 4)
        self.assertEqual(len(parsed["pending_commands"]), 1)

        # Session accepts plan: active_batch has 4, pending_queue has 1
        session = self.ext_mgr.create_recovery_session(self.sample_context, maximum_commands=10)
        session.accept_new_batch(parsed["commands"], proposed_total=5)

        self.assertEqual(len(session.active_batch), 4)
        self.assertEqual(len(session.pending_queue), 1)
        self.assertEqual(session.total_steps, 5)
        self.assertEqual([c.command_id for c in session.active_batch], ["CMD-01", "CMD-02", "CMD-03", "CMD-04"])
        self.assertEqual([c.command_id for c in session.pending_queue], ["CMD-05"])

        # Dependent command in pending queue cannot execute before preceding batch completes
        ok_premature, res_premature = self.ext_mgr.execute_session_command(session.session_id, "CMD-05")
        self.assertFalse(ok_premature)
        self.assertIn("pending queue and cannot be executed until preceding batch steps complete", res_premature)

        # Execute first 4 commands
        dummy_exec = lambda c: (0, "ok", "")
        self.ext_mgr.execute_session_command(session.session_id, "CMD-01", executor_fn=dummy_exec)
        self.ext_mgr.execute_session_command(session.session_id, "CMD-02", executor_fn=dummy_exec)
        self.ext_mgr.execute_session_command(session.session_id, "CMD-03", executor_fn=dummy_exec)
        self.ext_mgr.execute_session_command(session.session_id, "CMD-04", executor_fn=dummy_exec)

        # CMD-05 has now been promoted to active batch!
        self.assertEqual(len(session.active_batch), 1)
        self.assertEqual(session.active_batch[0].command_id, "CMD-05")
        self.assertEqual(len(session.pending_queue), 0)
        self.assertEqual(session.actual_commands_executed, 4)
        self.assertEqual(session.commands_remaining, 6)
        self.assertEqual(session.total_steps, 5)

        # CMD-05 requires approval
        ok5, res5 = self.ext_mgr.execute_session_command(session.session_id, "CMD-05", executor_fn=dummy_exec)
        self.assertFalse(ok5)
        self.assertIn("requires explicit user approval", res5)

        # User approves CMD-05
        approved = self.ext_mgr.approve_recovery_command(session.session_id, "CMD-05", executor_fn=dummy_exec)
        self.assertTrue(approved)
        self.assertEqual(session.actual_commands_executed, 5)
        self.assertEqual(session.commands_remaining, 5)
        print("[PASS] Test 11: Oversized batch preserved without step loss, promoted sequentially, and budget maintained")

    # --------------------------------------------------------------------------
    # 12. Installation approval is required
    # --------------------------------------------------------------------------
    def test_12_installation_approval_required(self):
        """Installation commands require explicit user approval before execution."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        session.executor_fn = lambda c: (0, "Successfully installed shfmt", "")
        session.accept_new_batch([
            {"command": "winget install mvdan.shfmt", "purpose": "Install shfmt", "requires_approval": True}
        ])

        # Attempting execution directly without approval fails
        ok, res = self.ext_mgr.execute_session_command(session.session_id, "CMD-01")
        self.assertFalse(ok)
        self.assertIn("requires explicit user approval", res)
        self.assertEqual(session.status, "awaiting_approval")

        # Explicit user approval executes command
        ok2 = self.ext_mgr.approve_recovery_command(session.session_id, "CMD-01")
        self.assertTrue(ok2)
        cmd = session.get_command_by_id("CMD-01")
        self.assertTrue(cmd.approved)
        print("[PASS] Test 12: Installation approval required")

    # --------------------------------------------------------------------------
    # 13. Recovery stops at the command limit
    # --------------------------------------------------------------------------
    def test_13_recovery_stops_at_command_limit(self):
        """Execution halts immediately when session command limit (default 10) is reached."""
        session = self.ext_mgr.create_recovery_session(self.sample_context, maximum_commands=3)
        session.accept_new_batch([
            {"command": "c1", "purpose": "p1", "requires_approval": False},
            {"command": "c2", "purpose": "p2", "requires_approval": False},
            {"command": "c3", "purpose": "p3", "requires_approval": False},
            {"command": "c4", "purpose": "p4", "requires_approval": False}
        ])

        dummy_exec = lambda c: (0, "ok", "")
        self.ext_mgr.execute_session_command(session.session_id, "CMD-01", executor_fn=dummy_exec)
        self.ext_mgr.execute_session_command(session.session_id, "CMD-02", executor_fn=dummy_exec)
        self.ext_mgr.execute_session_command(session.session_id, "CMD-03", executor_fn=dummy_exec)

        self.assertEqual(session.actual_commands_executed, 3)
        self.assertEqual(session.commands_remaining, 0)

        # 4th command is blocked by budget exhaustion
        ok4, res4 = self.ext_mgr.execute_session_command(session.session_id, "CMD-04", executor_fn=dummy_exec)
        self.assertFalse(ok4)
        self.assertIn("exhausted", res4)
        self.assertEqual(session.status, "limit_reached")
        print("[PASS] Test 13: Recovery stops at command limit")

    # --------------------------------------------------------------------------
    # 14. Final diagnosis appears only when recovery ends
    # --------------------------------------------------------------------------
    def test_14_final_diagnosis_appears_only_when_recovery_ends(self):
        """Final diagnosis/report is hidden during active execution and exposed only after session ends."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        session.accept_new_batch([{"command": "c1", "purpose": "p1", "requires_approval": False}])

        # While session is ready / running: final_report in to_dict is None
        session.final_report = "Report in progress"
        session.status = "executing"
        self.assertIsNone(session.to_dict()["final_report"])

        session.status = "awaiting_approval"
        self.assertIsNone(session.to_dict()["final_report"])

        # When session status ends with succeeded: final_report is exposed
        session.status = "succeeded"
        self.assertEqual(session.to_dict()["final_report"], "Report in progress")

        # When session status ends with failed: final_report is exposed
        session.status = "failed"
        self.assertEqual(session.to_dict()["final_report"], "Report in progress")
        print("[PASS] Test 14: Final diagnosis appears only when recovery ends")

    # --------------------------------------------------------------------------
    # 15. Existing Smart Install regression tests still pass
    # --------------------------------------------------------------------------
    def test_15_existing_smart_install_regression_tests(self):
        """Runs the 14-scenario general smart install recovery suite to ensure zero regressions."""
        from scratch.test_general_smart_install_recovery import TestGeneralSmartInstallRecovery
        suite = unittest.TestLoader().loadTestsFromTestCase(TestGeneralSmartInstallRecovery)
        runner = unittest.TextTestRunner(verbosity=0)
        res = runner.run(suite)
        self.assertTrue(res.wasSuccessful(), f"General smart install tests failed: {res.errors or res.failures}")
        print("[PASS] Test 15: Existing general Smart Install regression suite passes 100%")

    # --------------------------------------------------------------------------
    # 16. Existing Replace with AI tests remain unchanged and pass
    # --------------------------------------------------------------------------
    def test_16_existing_replace_with_ai_tests_pass(self):
        """Runs prompt and button acceptance suites to verify Replace with AI is completely unaffected."""
        from scratch.test_replace_with_ai_exact_prompt import TestReplaceWithAiExactPrompt
        suite1 = unittest.TestLoader().loadTestsFromTestCase(TestReplaceWithAiExactPrompt)
        runner = unittest.TextTestRunner(verbosity=0)
        res1 = runner.run(suite1)
        self.assertTrue(res1.wasSuccessful(), f"Exact prompt tests failed: {res1.errors or res1.failures}")

        from scratch.test_restore_replace_with_ai_button import test_replace_with_ai_button_restoration
        test_replace_with_ai_button_restoration()
        print("[PASS] Test 16: Existing Replace with AI prompt and button suites pass 100%")

    # --------------------------------------------------------------------------
    # 17. PowerShell call-operator compatibility & command-safety verification
    # --------------------------------------------------------------------------
    def test_17_powershell_call_operator_and_safety_checks(self):
        """
        Verifies PowerShell call-operator (&) invocation compatibility:
        - Legitimate PowerShell call-operator invocation of an executable with arguments is accepted.
        - Validator prevents command chaining without blocking legitimate executable invocation.
        - Process execution infrastructure uses validated executable paths and separate arguments directly.
        """
        # 1. Test legitimate call-operator commands
        valid_call_cmds = [
            ('& "C:\\tools\\gcc.exe" --version', "gcc"),
            ("& gcc --version", "gcc"),
            ("& 'C:\\tools\\shfmt.exe' -v", "shfmt"),
            ("& clang-format --version", "clang-format"),
        ]
        for cmd, tool in valid_call_cmds:
            is_safe, msg = self.ext_mgr.validate_command_safety(cmd, tool)
            self.assertTrue(is_safe, f"Expected safe invocation for '{cmd}', got rejection: {msg}")

        # 2. Test that chaining with & after call-operator is rejected
        chaining_attempts = [
            '& gcc --version & calc.exe',
            '& gcc --version && whoami',
            '& gcc --version ; calc.exe',
            '& gcc --version | findstr 15',
            'gcc --version & calc.exe',
            '& calc.exe',
        ]
        for bad_cmd in chaining_attempts:
            is_safe, msg = self.ext_mgr.validate_command_safety(bad_cmd, "gcc")
            self.assertFalse(is_safe, f"Expected rejection for '{bad_cmd}', but validator accepted it!")

        # 3. Test execution via process execution infrastructure with validated executable & separate args
        exit_code, stdout, stderr, results = self.ext_mgr.execute_command_steps(
            command_str="& gcc --version",
            tool_name="gcc",
            timeout=15
        )
        self.assertEqual(exit_code, 0, f"Call operator execution failed: {stderr}")
        self.assertIn("gcc", stdout.lower())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["exit_code"], 0)
        print("[PASS] Test 17: PowerShell call-operator invocation & chaining safety validated")

    # --------------------------------------------------------------------------
    # 18. Five-command plan total-step accounting and promotion invariance
    # --------------------------------------------------------------------------
    def test_18_five_command_plan_total_step_accounting(self):
        """
        Verifies total-step accounting for a 5-command plan (4 active and 1 pending):
        - Inspects how command_history, active_batch, and pending_queue are populated.
        - Verifies that commands are counted exactly once when calculating total_steps.
        - Confirms that the displayed total is 5, not a larger number caused by double-counting.
        - Confirms that promoting the pending command into the active batch does not change the total.
        """
        session = self.ext_mgr.create_recovery_session(self.sample_context, maximum_commands=10)
        plan_commands = [
            {"command": "gcc --version", "purpose": "Check GCC version", "requires_approval": False},
            {"command": "where gcc", "purpose": "Locate GCC binary", "requires_approval": False},
            {"command": "gcc -v", "purpose": "Check GCC verbose info", "requires_approval": False},
            {"command": "echo check headers", "purpose": "Verify include headers", "requires_approval": False},
            {"command": "echo verify toolchain", "purpose": "Verify complete toolchain", "requires_approval": False},
        ]

        # 1. Accept the 5-command batch
        new_records = session.accept_new_batch(plan_commands, proposed_total=5)
        self.assertEqual(len(new_records), 5)

        # 2. Inspect population: 4 active, 1 pending, 0 history
        self.assertEqual(len(session.command_history), 0)
        self.assertEqual(len(session.active_batch), 4)
        self.assertEqual(len(session.pending_queue), 1)
        self.assertEqual(session.pending_queue[0].command_id, "CMD-05")

        # 3. Verify commands are counted exactly once when calculating total_steps
        distinct_command_count = len(session.command_history) + len(session.active_batch) + len(session.pending_queue)
        self.assertEqual(distinct_command_count, 5)
        self.assertEqual(session.total_steps, 5)

        # 4. Confirm that the displayed total is 5, not a larger number caused by double-counting
        display_text = session.format_total_steps_display()
        self.assertEqual(display_text, "TOTAL STEPS: 5")

        # Confirm not repeated when queried again without count change
        self.assertIsNone(session.format_total_steps_display())

        # 5. Execute the first 4 active commands
        dummy_exec = lambda c: (0, f"Executed {c}", "")
        for idx in range(1, 5):
            cid = f"CMD-{idx:02d}"
            ok, out = self.ext_mgr.execute_session_command(session.session_id, cid, executor_fn=dummy_exec)
            self.assertTrue(ok, f"Command {cid} failed to execute")

        # 6. Verify state after the 4th command completes and triggers batch promotion:
        # active_batch was emptied, so CMD-05 was promoted from pending_queue into active_batch
        self.assertEqual(len(session.command_history), 4)
        self.assertEqual(len(session.active_batch), 1)
        self.assertEqual(session.active_batch[0].command_id, "CMD-05")
        self.assertEqual(len(session.pending_queue), 0)

        # 7. Confirm that promoting the pending command does NOT change total_steps
        promoted_distinct_count = len(session.command_history) + len(session.active_batch) + len(session.pending_queue)
        self.assertEqual(promoted_distinct_count, 5)
        self.assertEqual(session.total_steps, 5)

        # 8. Confirm format_total_steps_display() does not produce a new or duplicate display
        self.assertIsNone(session.format_total_steps_display())

        # 9. Execute the promoted 5th command (CMD-05)
        ok5, out5 = self.ext_mgr.execute_session_command(session.session_id, "CMD-05", executor_fn=dummy_exec)
        self.assertTrue(ok5)
        self.assertEqual(len(session.command_history), 5)
        self.assertEqual(len(session.active_batch), 0)
        self.assertEqual(len(session.pending_queue), 0)
        self.assertEqual(session.total_steps, 5)
        self.assertIsNone(session.format_total_steps_display())

        print("[PASS] Test 18: Five-command plan total-step accounting and promotion invariance verified")


if __name__ == "__main__":
    res = unittest.main(exit=False)
    if res.result.wasSuccessful():
        os._exit(0)
    else:
        os._exit(1)
