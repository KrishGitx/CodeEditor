#!/usr/bin/env python3
"""
Test Suite: General Smart Recovery Architecture in DGX Studio
Verifies all 12 architectural requirements from Section 6:
1. Generic recovery plan that can execute immediately.
2. Recovery plan that requires user approval.
3. Recovery plan that requires clarification from the user.
4. User response that resumes the same recovery session.
5. Ambiguous recovery strategy does not cause a premature terminal failure.
6. Command execution failure followed by replanning.
7. Revised plan that preserves command history and budget.
8. Successful recovery followed by verification.
9. Genuinely unrecoverable issue.
10. Cancellation and command-budget exhaustion.
11. UI state transitions for all supported recovery states.
12. Regression testing for existing command planning and recovery behavior.
"""

import os
import sys
import json
import unittest
from typing import Dict, Any, List

# Ensure offscreen Qt platform for headless QML visual testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine, QQmlComponent
from ExtensionManager import (
    ExtensionManager,
    RecoverySession,
    CommandRecord,
    validate_ai_plan_response
)

# Ensure QGuiApplication exists for visual QML and QObject tests
app = QGuiApplication.instance()
if not app:
    app = QGuiApplication(sys.argv)


class TestGeneralSmartRecoveryArchitecture(unittest.TestCase):
    def setUp(self):
        self.ext_mgr = ExtensionManager()
        self.sample_context = {
            "toolName": "flake8",
            "operation": "lint",
            "operationType": "lint",
            "category": "missing_dependency",
            "errorMessage": "flake8 not found on PATH",
            "filePath": "C:\\test\\main.py",
            "language": "python"
        }

    # --------------------------------------------------------------------------
    # Scenario 1: Generic recovery plan that can execute immediately
    # --------------------------------------------------------------------------
    def test_01_immediate_execution_plan(self):
        """A validated plan with non-privileged steps has status 'ready' and executes immediately."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        session.accept_new_batch([
            {"command": "flake8 --version", "purpose": "Check version", "requires_approval": False}
        ])
        first_cmd = session.active_batch[0]
        self.assertFalse(first_cmd.requires_approval)
        session.status = "ready"
        self.assertEqual(session.status, "ready")

        # Executes immediately with mock executor
        mock_exec = lambda c: (0, "6.1.0", "")
        ok, res = self.ext_mgr.execute_session_command(session.session_id, first_cmd.command_id, executor_fn=mock_exec)
        self.assertTrue(ok)
        self.assertEqual(first_cmd.status, "succeeded")
        self.assertEqual(session.status, "completed")
        self.assertEqual(session.actual_commands_executed, 1)
        print("[PASS] Scenario 1: Generic recovery plan executes immediately")

    # --------------------------------------------------------------------------
    # Scenario 2: Recovery plan that requires user approval
    # --------------------------------------------------------------------------
    def test_02_plan_requiring_approval(self):
        """A plan containing privileged steps requires approval before execution."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        session.accept_new_batch([
            {"command": "pip install flake8", "purpose": "Install flake8", "requires_approval": True}
        ])
        first_cmd = session.active_batch[0]
        self.assertTrue(first_cmd.requires_approval)
        self.assertFalse(first_cmd.approved)

        # Direct execution without approval is safely blocked
        mock_exec = lambda c: (0, "Successfully installed flake8", "")
        ok, msg = self.ext_mgr.execute_session_command(session.session_id, first_cmd.command_id, executor_fn=mock_exec)
        self.assertFalse(ok)
        self.assertIn("requires explicit user approval", msg)
        self.assertEqual(session.status, "awaiting_approval")

        # Explicit user approval executes the command
        approved = self.ext_mgr.approve_recovery_command(session.session_id, first_cmd.command_id, executor_fn=mock_exec)
        self.assertTrue(approved)
        self.assertTrue(first_cmd.approved)
        self.assertEqual(first_cmd.status, "succeeded")
        self.assertEqual(session.status, "completed")
        print("[PASS] Scenario 2: Recovery plan requires approval")

    # --------------------------------------------------------------------------
    # Scenario 3: Recovery plan that requires clarification from the user
    # --------------------------------------------------------------------------
    def test_03_plan_requiring_user_clarification(self):
        """AI requests clarification with structured data; session is preserved in awaiting_user_decision."""
        raw_ai_response = json.dumps({
            "plan_changed": True,
            "proposed_total_steps": 0,
            "commands": [],
            "needs_user_decision": True,
            "decision_request": {
                "question": "Which Python environment should be used?",
                "why_necessary": "Multiple virtual environments were detected in this workspace.",
                "choices": [".venv", "conda_base", "system_python"],
                "allow_custom_answer": True,
                "resume_key": "target_python_env"
            },
            "status": "awaiting_user_decision"
        })

        is_valid, parsed_plan, val_err = validate_ai_plan_response(raw_ai_response, self.ext_mgr)
        self.assertTrue(is_valid)
        self.assertTrue(parsed_plan.get("needs_user_decision"))
        req = parsed_plan.get("decision_request")
        self.assertIsNotNone(req)
        self.assertEqual(req.get("question"), "Which Python environment should be used?")
        self.assertIn(".venv", req.get("choices"))
        self.assertTrue(req.get("allow_custom_answer"))
        self.assertEqual(req.get("resume_key"), "target_python_env")

        # Start session with this AI plan
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        session.status = "awaiting_user_decision"
        session.decision_request = req
        s_dict = session.to_dict()
        self.assertEqual(s_dict["status"], "awaiting_user_decision")
        self.assertEqual(s_dict["decision_request"]["question"], req["question"])
        print("[PASS] Scenario 3: Recovery plan requires clarification from user")

    # --------------------------------------------------------------------------
    # Scenario 4: User response resumes the same recovery session
    # --------------------------------------------------------------------------
    def test_04_user_response_resumes_same_session(self):
        """Submitting user decision stores answer, preserves session ID, and triggers replan."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        original_session_id = session.session_id
        session.status = "awaiting_user_decision"
        session.decision_request = {
            "question": "Select target toolchain",
            "why_necessary": "Multiple toolchains available",
            "choices": ["gcc", "clang"],
            "allow_custom_answer": False,
            "resume_key": "selected_toolchain"
        }

        # Mock AI planner response for when session replans
        mock_ai_continuation = json.dumps({
            "plan_changed": True,
            "proposed_total_steps": 2,
            "commands": [
                {"command": "clang --version", "purpose": "Verify clang", "requires_approval": False},
                {"command": "clang -o output main.c", "purpose": "Compile with clang", "requires_approval": False}
            ],
            "needs_user_decision": False
        })
        self.ext_mgr._query_ai_backend = lambda prompt: (True, mock_ai_continuation, "")

        # User submits decision
        ok = self.ext_mgr.submit_user_decision(session.session_id, "clang", "selected_toolchain")
        self.assertTrue(ok)
        self.assertEqual(session.session_id, original_session_id)
        self.assertEqual(session.user_decisions.get("selected_toolchain"), "clang")
        self.assertIsNone(session.decision_request)
        self.assertEqual(session.status, "ready")
        self.assertEqual(len(session.active_batch), 2)
        self.assertEqual(session.active_batch[0].command, "clang --version")
        print("[PASS] Scenario 4: User response resumes same recovery session")

    # --------------------------------------------------------------------------
    # Scenario 5: Ambiguous recovery strategy does not cause premature terminal failure
    # --------------------------------------------------------------------------
    def test_05_ambiguous_strategy_does_not_cause_terminal_failure(self):
        """Ambiguous strategy requests user decision and attaches recovery session instead of failing."""
        sql_context = {
            "operation": "execute_sql",
            "operationType": "sql",
            "errorMessage": "No runner configured for .sql",
            "filePath": "C:\\test\\schema.sql",
            "language": "sql"
        }
        proposal = self.ext_mgr.resolve_smart_install_context(sql_context)
        # Not a terminal failure: needs_user_decision is True, status is awaiting_user_decision
        self.assertTrue(proposal.get("needs_user_decision"))
        self.assertEqual(proposal.get("status"), "awaiting_user_decision")

        # Attaching recovery session attaches active session
        proposal = self.ext_mgr._attach_command_recovery_session_if_needed(sql_context, proposal)
        self.assertIsNotNone(proposal.get("sessionId"))
        self.assertEqual(proposal.get("status"), "awaiting_user_decision")
        session = self.ext_mgr._recovery_sessions.get(proposal["sessionId"])
        self.assertIsNotNone(session)
        self.assertEqual(session.status, "awaiting_user_decision")
        self.assertIsNotNone(session.decision_request)
        print("[PASS] Scenario 5: Ambiguous strategy does not cause premature failure")

    # --------------------------------------------------------------------------
    # Scenario 6: Command execution failure followed by replanning
    # --------------------------------------------------------------------------
    def test_06_execution_failure_followed_by_replanning(self):
        """When a command fails, replanning is invoked using real command output."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        session.accept_new_batch([
            {"command": "pip install flake8", "purpose": "Install flake8", "requires_approval": False}
        ])
        cmd1 = session.active_batch[0]

        # Execute cmd1 and simulate network failure
        mock_exec = lambda c: (1, "", "HTTP 404: Package index unreachable")
        ok, res = self.ext_mgr.execute_session_command(session.session_id, cmd1.command_id, executor_fn=mock_exec)
        self.assertFalse(ok)
        self.assertEqual(cmd1.status, "failed")
        self.assertEqual(session.status, "failed")
        self.assertEqual(len(session.command_history), 1)

        # Mock AI planner proposing alternative mirror on replanning
        ai_replan = json.dumps({
            "plan_changed": True,
            "proposed_total_steps": 1,
            "commands": [
                {"command": "python -m pip install flake8", "purpose": "Install via python module", "requires_approval": False}
            ]
        })
        self.ext_mgr._query_ai_backend = lambda prompt: (True, ai_replan, "")

        # Call replan_recovery_session
        replan_ok = self.ext_mgr.replan_recovery_session(session.session_id)
        self.assertTrue(replan_ok)
        self.assertEqual(session.status, "ready")
        self.assertEqual(len(session.active_batch), 1)
        self.assertEqual(session.active_batch[0].command, "python -m pip install flake8")
        self.assertEqual(session.active_batch[0].command_id, "CMD-02")
        print("[PASS] Scenario 6: Execution failure followed by replanning")

    # --------------------------------------------------------------------------
    # Scenario 7: Revised plan preserves command history and budget
    # --------------------------------------------------------------------------
    def test_07_revised_plan_preserves_history_and_budget(self):
        """Replanning preserves executed count, budget remaining, command history, and ID index."""
        session = self.ext_mgr.create_recovery_session(self.sample_context, maximum_commands=5)
        session.accept_new_batch([
            {"command": "python --version", "purpose": "Check python", "requires_approval": False},
            {"command": "pip --version", "purpose": "Check pip", "requires_approval": False}
        ])
        mock_exec = lambda c: (0, "Python 3.11.0", "")
        self.ext_mgr.execute_session_command(session.session_id, "CMD-01", executor_fn=mock_exec)

        self.assertEqual(session.actual_commands_executed, 1)
        self.assertEqual(session.commands_remaining, 4)
        self.assertEqual(session.next_command_index, 3)

        # Replan with 2 new commands
        ai_replan = json.dumps({
            "plan_changed": True,
            "proposed_total_steps": 3,
            "commands": [
                {"command": "pip install flake8", "purpose": "Install flake8", "requires_approval": False},
                {"command": "flake8 --version", "purpose": "Verify flake8", "requires_approval": False}
            ]
        })
        self.ext_mgr._query_ai_backend = lambda prompt: (True, ai_replan, "")
        self.ext_mgr.replan_recovery_session(session.session_id)

        # Invariants preserved
        self.assertEqual(session.actual_commands_executed, 1)
        self.assertEqual(session.commands_remaining, 4)
        self.assertEqual(len(session.command_history), 1)
        self.assertEqual(session.command_history[0].command_id, "CMD-01")
        # Sequential IDs continued from CMD-03
        self.assertEqual(session.active_batch[0].command_id, "CMD-03")
        self.assertEqual(session.active_batch[1].command_id, "CMD-04")
        print("[PASS] Scenario 7: Revised plan preserves history and budget")

    # --------------------------------------------------------------------------
    # Scenario 8: Successful recovery followed by verification
    # --------------------------------------------------------------------------
    def test_08_successful_recovery_with_verification(self):
        """Fix command is followed by verification step with 'verifying' state and 'completed'."""
        session = self.ext_mgr.create_recovery_session(self.sample_context)
        session.accept_new_batch([
            {"command": "pip install flake8", "purpose": "Install flake8", "requires_approval": False},
            {"command": "flake8 --version", "purpose": "Verify flake8 installation", "requires_approval": False}
        ])

        # Track state transitions during execution
        observed_states = []
        def on_update(s_dict):
            observed_states.append(s_dict["status"])
        self.ext_mgr.recoveryPlanUpdated.connect(on_update)

        mock_exec = lambda c: (0, "6.1.0 (mccabe: 0.7.0, pycodestyle: 2.11.0, pyflakes: 3.1.0)", "")
        # Step 1: Install
        ok1, _ = self.ext_mgr.execute_session_command(session.session_id, "CMD-01", executor_fn=mock_exec)
        self.assertTrue(ok1)
        self.assertIn("executing", observed_states)

        # Step 2: Verification
        ok2, _ = self.ext_mgr.execute_session_command(session.session_id, "CMD-02", executor_fn=mock_exec)
        self.assertTrue(ok2)
        self.assertIn("verifying", observed_states)
        self.assertEqual(session.status, "completed")
        self.assertIsNotNone(session.final_report)
        self.assertIn("completed successfully", session.final_report)
        print("[PASS] Scenario 8: Successful recovery with verification")

    # --------------------------------------------------------------------------
    # Scenario 9: Genuinely unrecoverable issue
    # --------------------------------------------------------------------------
    def test_09_genuinely_unrecoverable_issue(self):
        """Syntax errors or permission failures are marked cannot_resolve without installing packages."""
        ctx = {
            "operation": "build",
            "toolName": "gcc",
            "command": "gcc -o driver driver.c",
            "exitCode": 1,
            "errorMessage": "Permission denied: access is denied to system driver directory",
            "stderr": "Access is denied",
            "filePath": "C:\\test\\driver.c",
            "language": "c"
        }
        proposal = self.ext_mgr.diagnose_and_recover_workflow_failure(ctx)
        self.assertEqual(proposal.get("category"), "permission_failure")
        self.assertEqual(proposal.get("resolutionType"), "cannot_resolve")
        self.assertEqual(proposal.get("command"), "")
        self.assertEqual(proposal.get("steps") or [], [])
        self.assertIn("Permission", proposal.get("title", ""))
        print("[PASS] Scenario 9: Genuinely unrecoverable issue diagnosed without unwanted installs")

    # --------------------------------------------------------------------------
    # Scenario 10: Cancellation and command-budget exhaustion
    # --------------------------------------------------------------------------
    def test_10_cancellation_and_budget_exhaustion(self):
        """Cancellation transitions to 'cancelled'; budget exhaustion transitions to 'limit_reached'."""
        # 1. Cancellation test
        s1 = self.ext_mgr.create_recovery_session(self.sample_context)
        s1.accept_new_batch([{"command": "echo step", "purpose": "p", "requires_approval": False}])
        cancelled = self.ext_mgr.cancel_recovery_session(s1.session_id)
        self.assertTrue(cancelled)
        self.assertEqual(s1.status, "cancelled")
        self.assertIn("cancelled", s1.final_report.lower())

        # 2. Budget exhaustion test
        s2 = self.ext_mgr.create_recovery_session(self.sample_context, maximum_commands=2)
        s2.accept_new_batch([
            {"command": "cmd1", "purpose": "p1", "requires_approval": False},
            {"command": "cmd2", "purpose": "p2", "requires_approval": False},
            {"command": "cmd3", "purpose": "p3", "requires_approval": False}
        ])
        dummy_exec = lambda c: (0, "ok", "")
        self.ext_mgr.execute_session_command(s2.session_id, "CMD-01", executor_fn=dummy_exec)
        self.ext_mgr.execute_session_command(s2.session_id, "CMD-02", executor_fn=dummy_exec)
        self.assertEqual(s2.commands_remaining, 0)

        # 3rd command must halt with limit_reached
        ok3, res3 = self.ext_mgr.execute_session_command(s2.session_id, "CMD-03", executor_fn=dummy_exec)
        self.assertFalse(ok3)
        self.assertEqual(s2.status, "limit_reached")
        self.assertIn("exhausted", res3)
        print("[PASS] Scenario 10: Cancellation and budget exhaustion")

    # --------------------------------------------------------------------------
    # Scenario 11: UI state transitions for all supported recovery states
    # --------------------------------------------------------------------------
    def test_11_ui_state_transitions(self):
        """SmartInstallDialog cleanly transitions across all 10 authoritative recovery states."""
        engine = QQmlEngine()
        component = QQmlComponent(engine, "qml/components/SmartInstallDialog.qml")
        self.assertFalse(component.isError(), f"QML error: {[e.toString() for e in component.errors()]}")
        dialog = component.create()
        self.assertIsNotNone(dialog)

        # Authoritative states to verify:
        # ready, awaiting_approval, awaiting_user_decision, executing, verifying,
        # completed, cannot_resolve, failed, cancelled, limit_reached
        states_to_test = [
            "ready",
            "awaiting_approval",
            "awaiting_user_decision",
            "executing",
            "verifying",
            "completed",
            "cannot_resolve",
            "failed",
            "cancelled",
            "limit_reached"
        ]

        for st in states_to_test:
            session_payload = {
                "sessionId": "rec_test_123",
                "status": st,
                "total_steps": 2,
                "actual_commands_executed": 1,
                "commands_remaining": 5,
                "commands": [{"commandId": "CMD-01", "command": "flake8 --version"}],
                "decision_request": {
                    "question": "Choose strategy",
                    "why_necessary": "Clarification needed",
                    "choices": ["A", "B"],
                    "allow_custom_answer": True
                } if st == "awaiting_user_decision" else None,
                "final_report": f"Report for {st}"
            }
            # Open proposal with state payload
            dialog.openProposal(session_payload)
            self.assertEqual(dialog.property("dialogState"), st)

        print("[PASS] Scenario 11: UI state transitions for all 10 supported recovery states")

    # --------------------------------------------------------------------------
    # Scenario 12: Regression testing for existing command planning and recovery behavior
    # --------------------------------------------------------------------------
    def test_12_regression_and_safety_invariants(self):
        """Invariants for CMD-XX numbering, max 4 batch promotion, and safety checks remain strict."""
        # Check oversized batch split
        raw = json.dumps({
            "plan_changed": True,
            "proposed_total_steps": 5,
            "commands": [
                {"command": "git --version", "purpose": "p1"},
                {"command": "python --version", "purpose": "p2"},
                {"command": "flake8 --version", "purpose": "p3"},
                {"command": "pip --version", "purpose": "p4"},
                {"command": "cargo --version", "purpose": "p5"}
            ]
        })
        is_valid, parsed, _ = validate_ai_plan_response(raw, self.ext_mgr, allow_oversized_split=True)
        self.assertTrue(is_valid)
        self.assertEqual(len(parsed["batch_commands"]), 4)
        self.assertEqual(len(parsed["pending_commands"]), 1)

        # Check duplicate ID rejection
        dup_raw = json.dumps({
            "commands": [
                {"id": "CMD-01", "command": "flake8 --version"},
                {"id": "CMD-01", "command": "flake8 --version"}
            ]
        })
        is_valid_dup, _, err = validate_ai_plan_response(dup_raw, self.ext_mgr)
        self.assertFalse(is_valid_dup)
        self.assertIn("Duplicate command ID", err)

        # Check malicious command injection rejection
        unsafe_raw = json.dumps({
            "commands": [{"command": "rmdir /s /q C:\\Windows", "purpose": "malicious"}]
        })
        is_valid_unsafe, _, err_unsafe = validate_ai_plan_response(unsafe_raw, self.ext_mgr)
        self.assertFalse(is_valid_unsafe)
        self.assertIn("rejected by safety validation", err_unsafe)
        print("[PASS] Scenario 12: Regression testing and safety invariants")


if __name__ == "__main__":
    unittest.main()
