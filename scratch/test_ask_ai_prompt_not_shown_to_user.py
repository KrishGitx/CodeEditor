"""
test_ask_ai_prompt_not_shown_to_user.py - Verify prompt sent with selected code is never shown to user.

Verifies:
1. Calling askAboutSelection() in AIWorkspace sends only the code block to the user-facing chat model.
2. The prompt template ("Review the provided code selection and fix any bugs that exist...") is NOT in the user chat bubble.
3. The prompt template is passed to the AI worker as internalInstruction so the model receives the full bug-fix prompt.
4. AIBackend.send_message emits only the user-visible prompt to messageReceived, never the prompt template.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from AIBackend import AIBackend, clean_ai_text
from AIReplacementEngine import SELECTION_BUG_FIX_PROMPT, build_selection_prompt


class TestAskAiPromptNotShownToUser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv)

    def test_01_build_selection_prompt_isolation(self):
        code = "def calculate(x, y):\n    return x + y"
        user_prompt, internal_instr = build_selection_prompt(code, "python")

        # user_prompt must contain the code
        self.assertIn("def calculate", user_prompt)
        # user_prompt must NOT contain the prompt template
        self.assertNotIn("Review the provided code selection", user_prompt)
        self.assertNotIn("SUCCESS", user_prompt)
        self.assertNotIn("[Fixed Code]", user_prompt)

        # internal_instr must contain the prompt template
        self.assertIn("Review the provided code selection", internal_instr)
        self.assertIn("SUCCESS", internal_instr)
        self.assertIn("[Fixed Code]", internal_instr)

    def test_02_backend_send_message_filters_prompt_from_ui(self):
        backend = AIBackend()
        received_messages = []
        backend.messageReceived.connect(lambda mid, role, content: received_messages.append((role, content)))

        # Even if someone sends a combined prompt directly to send_message:
        combined = f"{SELECTION_BUG_FIX_PROMPT}\n\n```python\nprint('hello')\n```"
        backend.send_message(combined)

        # UI received message for 'user' must NOT contain the prompt template
        user_msgs = [c for r, c in received_messages if r == "user"]
        self.assertEqual(len(user_msgs), 1)
        self.assertNotIn("Review the provided code selection", user_msgs[0])
        self.assertIn("print('hello')", user_msgs[0])

        backend.cancel()

    def test_03_ai_workspace_ask_about_selection_chat_history(self):
        engine = QQmlApplicationEngine()
        backend = AIBackend()
        engine.rootContext().setContextProperty("aiBackend", backend)

        comp = QQmlComponent(engine, QUrl.fromLocalFile(os.path.abspath("qml/ai/AIWorkspace.qml")))
        self.assertFalse(comp.isError(), f"AIWorkspace load error: {comp.errorString()}")
        ai_ws = comp.create()
        self.assertIsNotNone(ai_ws)

        received_user_contents = []
        backend.messageReceived.connect(lambda mid, role, content: received_user_contents.append(content) if role == "user" else None)

        test_code = "if count = 5:\n    print(count)"
        # Call askAboutSelection
        ai_ws.askAboutSelection(test_code, 0, len(test_code), "python", "", "", len(test_code))

        # Check what was emitted to messageReceived (what shows to user)
        self.assertEqual(len(received_user_contents), 1)
        emitted_to_user = received_user_contents[0]

        # The prompt we send with code should NOT show to user
        self.assertNotIn("Review the provided code selection", emitted_to_user)
        self.assertNotIn("If there are no bugs", emitted_to_user)
        self.assertNotIn("[Fixed Code]", emitted_to_user)
        self.assertNotIn("IMPORTANT:", emitted_to_user)

        # But the selected code itself should be present in the user message
        self.assertIn("if count = 5:", emitted_to_user)

        # Check that the worker thread received the full prompt template + code
        self.assertIsNotNone(backend.active_worker)
        worker_prompt = backend.active_worker.prompt
        self.assertIn("Review the provided code selection and fix any bugs that exist.", worker_prompt)
        self.assertIn("if count = 5:", worker_prompt)

        backend.cancel()


if __name__ == "__main__":
    unittest.main()
