import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QCoreApplication
from AIBackend import AIBackend, clean_ai_text

def test_five_sequential_selection_requests():
    print("=================================================================")
    print("TEST: 5 Sequential Selection-AI Requests Lifecycle & Diagnostics")
    print("=================================================================")

    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    backend = AIBackend()

    test_cases = [
        {
            "id": 1,
            "title": "Test 1 — C++ syntax (Missing Semicolon)",
            "lang": "cpp",
            "code": "int x = 10\ncout << x;",
            "expected_protocol": "[REPLACEMENT_CODE]",
            "expected_fix": "int x = 10;"
        },
        {
            "id": 2,
            "title": "Test 2 — C++ logic (Off-by-one Out-of-bounds)",
            "lang": "cpp",
            "code": "for (int i = 0; i <= values.size(); ++i) {\n    cout << values[i];\n}",
            "expected_protocol": "[REPLACEMENT_CODE]",
            "expected_fix": "< values.size()"
        },
        {
            "id": 3,
            "title": "Test 3 — Python (Incomplete Expression)",
            "lang": "python",
            "code": "def add(a, b):\n    return a + ",
            "expected_protocol": "[REPLACEMENT_CODE]",
            "expected_fix": "return a + b"
        },
        {
            "id": 4,
            "title": "Test 4 — JavaScript (Missing Await)",
            "lang": "javascript",
            "code": "const response = fetch(\"/api/user\");\nconst data = await response.json();",
            "expected_protocol": "[REPLACEMENT_CODE]",
            "expected_fix": "await fetch("
        },
        {
            "id": 5,
            "title": "Test 5 — C++ No Change",
            "lang": "cpp",
            "code": "int result = a + b;",
            "expected_protocol": "[NO_CHANGE]",
            "expected_fix": ""
        }
    ]

    for tc in test_cases:
        print(f"\n--- Running {tc['title']} ---")

        received_chunks = []
        received_messages = []
        status_updates = []
        error_messages = []

        def on_msg(msg_id, role, content):
            received_messages.append((msg_id, role, content))
            print(f"   [MessageReceived] role={role}, len={len(content)}")

        def on_chunk(msg_id, chunk):
            received_chunks.append(chunk)

        def on_status(status):
            status_updates.append(status)

        def on_err(err):
            error_messages.append(err)
            print(f"   [ErrorReceived] {err}")

        # Connect signals
        backend.messageReceived.connect(on_msg)
        backend.chunkReceived.connect(on_chunk)
        backend.statusChanged.connect(on_status)
        backend.errorOccurred.connect(on_err)

        user_prompt = f"Please review and improve this selected {tc['lang']} code:\n\n```{tc['lang']}\n{tc['code']}\n```"
        internal_instruction = "Focus strictly on the selected portion. If changes are needed, return [REPLACEMENT_CODE]. If no changes are needed, return [NO_CHANGE]."

        backend.send_message(user_prompt, internal_instruction)

        # Wait for completion (process Qt events)
        start_t = time.time()
        completed = False
        while time.time() - start_t < 15.0:
            app.processEvents()
            time.sleep(0.05)
            if any(role == "assistant" for _, role, _ in received_messages):
                completed = True
                break
            if error_messages:
                break

        # Disconnect signals
        backend.messageReceived.disconnect(on_msg)
        backend.chunkReceived.disconnect(on_chunk)
        backend.statusChanged.disconnect(on_status)
        backend.errorOccurred.disconnect(on_err)

        assert completed, f"Request {tc['id']} did not complete within timeout! Errors: {error_messages}"
        assert not error_messages, f"Request {tc['id']} reported unexpected errors: {error_messages}"

        # Find assistant message
        assistant_msgs = [c for _, r, c in received_messages if r == "assistant"]
        assert len(assistant_msgs) == 1, f"Expected exactly 1 assistant response for {tc['id']}, got {len(assistant_msgs)}"
        
        response_text = assistant_msgs[0]
        assert len(response_text.strip()) > 0, f"Request {tc['id']} returned an EMPTY assistant response!"
        print(f"   [PASS] Non-empty assistant response received ({len(response_text)} chars).")
        print(f"   Response Preview:\n{response_text[:120]}...\n")

        # Verify protocol marker
        assert tc['expected_protocol'] in response_text, f"Expected marker '{tc['expected_protocol']}' in response of {tc['id']}!"
        if tc['expected_fix']:
            assert tc['expected_fix'] in response_text, f"Expected fix '{tc['expected_fix']}' in response of {tc['id']}!"

        print(f"   [PASS] {tc['title']} verified successfully!")

    print("\n" + "="*65)
    print(">>> ALL 5 CONSECUTIVE SELECTION-AI REQUESTS PASSED (100%)! <<<")
    print("=================================================================")
    return True

if __name__ == "__main__":
    success = test_five_sequential_selection_requests()
    if not success:
        sys.exit(1)
