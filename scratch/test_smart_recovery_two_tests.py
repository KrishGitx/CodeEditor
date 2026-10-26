import os
import sys
import json
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ExtensionManager as em_module
from ExtensionManager import ExtensionManager


class TestSmartRecoveryTwoTests(unittest.TestCase):
    """
    Focused verification containing ONLY the 2 required tests:
    1. Backend: An eligible failure invokes the AI, and a valid decision request
       preserves the recovery session in awaiting_user_decision.
    2. Frontend integration: The decision request reaches the UI, remains visible,
       and submitting an answer resumes the same session without transitioning
       prematurely to cannot_resolve.
    """

    def setUp(self):
        self.ext_mgr = ExtensionManager()
        ExtensionManager.set_ai_provider(None)

    def tearDown(self):
        ExtensionManager.set_ai_provider(None)

    def test_01_backend_eligible_failure_invokes_ai_and_preserves_awaiting_user_decision(self):
        """
        Test 1 (Backend): An eligible failure invokes the AI, and a valid decision
        request preserves the recovery session in awaiting_user_decision.
        """
        ai_invoked = []

        def mock_ai_backend(prompt: str) -> str:
            ai_invoked.append(prompt)
            return json.dumps({
                "status": "awaiting_user_decision",
                "needs_user_decision": True,
                "title": "Select Target Toolchain",
                "diagnosis": "Multiple incompatible C++ compilers installed.",
                "explanation": "Please select the compiler toolchain to configure for this project.",
                "decision_request": {
                    "question": "Which C++ compiler should DGX Studio configure?",
                    "why_necessary": "Both GCC and Clang were detected on the system PATH.",
                    "choices": ["GCC (MinGW)", "Clang (LLVM)"],
                    "allow_custom_answer": True,
                    "resume_key": "selected_toolchain",
                    "default_choice": "GCC (MinGW)"
                },
                "command": "",
                "steps": []
            })

        ExtensionManager.set_ai_provider(mock_ai_backend)

        # An eligible build failure (configuration / toolchain ambiguity)
        fail_context = self.ext_mgr.create_smart_install_context(
            operation="build",
            operation_type="tool",
            language="cpp",
            file_path="C:\\project\\main.cpp",
            command_attempted="cmake --build .",
            exit_code=1,
            error_message="CMake Error: CMAKE_CXX_COMPILER is ambiguous between GCC and Clang."
        )

        proposal = self.ext_mgr.diagnose_and_recover_workflow_failure(fail_context)

        # 1. Verify AI was indeed invoked (not bypassed)
        self.assertTrue(len(ai_invoked) > 0, "Eligible failure must invoke AI backend")

        # 2. Verify proposal preserves awaiting_user_decision and decision_request
        self.assertEqual(proposal.get("status"), "awaiting_user_decision")
        self.assertNotEqual(proposal.get("resolutionType"), "cannot_resolve")
        self.assertTrue(proposal.get("needs_user_decision"))

        decision_req = proposal.get("decision_request") or proposal.get("decisionRequest")
        self.assertIsNotNone(decision_req, "decision_request must be preserved")
        self.assertEqual(decision_req.get("question"), "Which C++ compiler should DGX Studio configure?")
        self.assertEqual(decision_req.get("choices"), ["GCC (MinGW)", "Clang (LLVM)"])

        # 3. Verify recovery session is registered and preserved in awaiting_user_decision
        session_id = proposal.get("sessionId") or proposal.get("session_id")
        self.assertTrue(session_id, "Proposal must have an attached sessionId")
        session = self.ext_mgr._recovery_sessions.get(session_id)
        self.assertIsNotNone(session, "RecoverySession must be registered in ExtensionManager")
        self.assertEqual(session.status, "awaiting_user_decision")
        self.assertEqual(session.commands_remaining, 10)
        self.assertEqual(session.decision_request.get("resume_key"), "selected_toolchain")

    def test_02_frontend_decision_request_reaches_ui_and_resumes_without_cannot_resolve(self):
        """
        Test 2 (Frontend integration): The decision request reaches the UI, remains
        visible, and submitting an answer resumes the same session without transitioning
        prematurely to cannot_resolve.
        """
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtCore import QUrl, QCoreApplication

        app = QGuiApplication.instance()
        if not app:
            app = QGuiApplication(sys.argv)

        decision_payload = {
            "status": "awaiting_user_decision",
            "needs_user_decision": True,
            "title": "Select Target Toolchain",
            "explanation": "Please select the compiler toolchain to configure.",
            "decision_request": {
                "question": "Which C++ compiler should DGX Studio configure?",
                "why_necessary": "Both GCC and Clang were detected on the system.",
                "choices": ["GCC (MinGW)", "Clang (LLVM)"],
                "allow_custom_answer": True,
                "resume_key": "selected_toolchain",
                "default_choice": "GCC (MinGW)"
            },
            "command": "",
            "steps": []
        }

        replanned_payload = {
            "plan_changed": True,
            "proposed_total_steps": 2,
            "commands": [
                {
                    "command": "gcc --version",
                    "purpose": "Verify GCC toolchain",
                    "requires_approval": False,
                    "expected_result": "GCC version printed",
                    "failure_handling": "abort"
                }
            ],
            "needs_user_decision": False,
            "decision_request": None,
            "cannot_resolve": False,
            "recovery_complete": False,
            "final_report": ""
        }

        call_count = {"count": 0}
        def mock_ai_backend(prompt: str) -> str:
            call_count["count"] += 1
            if "USER DECISIONS AND CLARIFICATIONS" in prompt or "selected_toolchain" in prompt:
                return json.dumps(replanned_payload)
            return json.dumps(decision_payload)

        ExtensionManager.set_ai_provider(mock_ai_backend)

        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("extensionManager", self.ext_mgr)
        qml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "qml", "components", "SmartInstallDialog.qml"))
        component = engine.load(QUrl.fromLocalFile(qml_path))

        root_objs = engine.rootObjects()
        self.assertTrue(len(root_objs) > 0, "SmartInstallDialog.qml must load successfully")
        dialog = root_objs[0]

        # 1. Trigger analysis through openContext
        fail_context = self.ext_mgr.create_smart_install_context(
            operation="build",
            operation_type="tool",
            language="cpp",
            file_path="C:\\project\\main.cpp",
            command_attempted="cmake --build .",
            exit_code=1,
            error_message="CMAKE_CXX_COMPILER is ambiguous between GCC and Clang."
        )

        proposal = self.ext_mgr.resolve_smart_install_context(fail_context)
        proposal = self.ext_mgr._attach_command_recovery_session_if_needed(fail_context, proposal)
        session_id = proposal["sessionId"]

        # Simulate async signals reaching UI in full sequence
        # First recoveryPlanUpdated is emitted by _attach_command_recovery_session_if_needed,
        # then smartInstallResolved is emitted by start_smart_install_analysis
        session = self.ext_mgr._recovery_sessions[session_id]
        dialog.openContext(fail_context)
        QCoreApplication.processEvents()

        # Emit the exact signals emitted by backend in live operation
        self.ext_mgr.recoveryPlanUpdated.emit(session.to_dict())
        self.ext_mgr.smartInstallResolved.emit(proposal)
        QCoreApplication.processEvents()

        # 2. Verify UI state: must be awaiting_user_decision, NOT overwritten to cannot_resolve
        state = dialog.property("dialogState")
        self.assertEqual(state, "awaiting_user_decision", "UI must stay in awaiting_user_decision and not overwrite to cannot_resolve")

        decision_req_ui = dialog.property("userDecisionRequest")
        self.assertIsNotNone(decision_req_ui, "userDecisionRequest must be populated in UI")
        self.assertEqual(decision_req_ui.get("question"), "Which C++ compiler should DGX Studio configure?")

        # 3. Simulate user selecting choice and submitting
        # User chooses "GCC (MinGW)"
        resumed = self.ext_mgr.submit_user_decision(session_id, "GCC (MinGW)", "selected_toolchain")
        self.assertTrue(resumed, "submit_user_decision must return True")
        QCoreApplication.processEvents()

        # 4. Verify same session was resumed without transitioning to cannot_resolve
        self.assertEqual(dialog.property("recoverySessionId"), session_id, "Must retain the same session ID")
        post_state = dialog.property("dialogState")
        self.assertNotEqual(post_state, "cannot_resolve", "Must not prematurely transition to cannot_resolve")
        self.assertIn(post_state, ("ready", "executing", "completed"), "Session must resume to ready/executing/completed")

        # Verify command plan was populated for execution
        plan = dialog.property("recoveryPlan")
        self.assertTrue(len(plan) > 0, "Resumed plan must contain commands")
        self.assertEqual(plan[0].get("command"), "gcc --version")


if __name__ == "__main__":
    unittest.main()
