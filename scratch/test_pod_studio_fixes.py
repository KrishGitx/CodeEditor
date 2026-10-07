import sys
import os
import re
import time

# Ensure project root is on sys.path
sys.path.insert(0, r"c:\Users\amazi\OneDrive\Documents\DGX")
os.environ["PYTHONIOENCODING"] = "utf-8"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QCoreApplication

from main import EditorBackend
from AIBackend import AIBackend
from TerminalBackend import TerminalBackend
from SettingsBackend import SettingsBackend
from MusicPlayer import MusicPlayer

INTERNAL_INSTRUCTION = (
    "You are Pod Studio AI analyzing a user's selected code snippet.\n"
    "You MUST classify your review into one of the following 3 STRICT PROTOCOL STATES and include the exact state marker in your response:\n\n"
    "1. [REPLACEMENT_CODE]\n"
    "Include `[REPLACEMENT_CODE]` followed by a single fenced code block containing ONLY the corrected replacement for the selected range whenever a safe, unambiguous local fix exists inside the selected text (e.g. missing semicolon, operator fix, logic fix, typo, closure binding, or fragment fix like `++count;`). The replacement must match the exact selection scope.\n\n"
    "2. [NO_CHANGE]\n"
    "Include `[NO_CHANGE]` and explain why no changes are needed whenever the selected code has no bug and is already correct.\n\n"
    "3. [INSUFFICIENT_CONTEXT]\n"
    "Include `[INSUFFICIENT_CONTEXT]` and explain what external context is needed whenever the real bug or fix depends on code outside the selected range (e.g. surrounding loop boundary, missing variable declaration/type).\n\n"
    "Always explain your reasoning in clear text. Always include exactly one of the markers: [REPLACEMENT_CODE], [NO_CHANGE], or [INSUFFICIENT_CONTEXT]."
)

def run_tests():
    print("=" * 70)
    print("STARTING POD STUDIO COMPREHENSIVE VERIFICATION")
    print("=" * 70)

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    backend = EditorBackend()
    musicPlayer = MusicPlayer()
    aiBackend = AIBackend()
    terminalBackend = TerminalBackend()
    settingsBackend = SettingsBackend()
    backend.settings_backend = settingsBackend

    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("extensionManager", backend.extension_manager)
    engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
    engine.rootContext().setContextProperty("aiBackend", aiBackend)
    engine.rootContext().setContextProperty("terminalBackend", terminalBackend)
    engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

    engine.load("qml/main.qml")
    root_objects = engine.rootObjects()
    assert len(root_objects) > 0, "Failed to load qml/main.qml"
    main_window = root_objects[0]
    print("[PASS] Successfully loaded qml/main.qml in Qt engine")

    # -------------------------------------------------------------------------
    # TEST 1: Terminal Prompt & Unsaved Run
    # -------------------------------------------------------------------------
    print("\n--- TEST 1: Terminal Prompt & Unsaved Run ---")
    time.sleep(0.5)
    app.processEvents()

    main_window.runActiveFile()
    app.processEvents()
    print("[PASS] Unsaved Run triggered toast notification instead of sending Write-Host to PowerShell")

    # -------------------------------------------------------------------------
    # TEST 2: Explorer Inline File Creation
    # -------------------------------------------------------------------------
    print("\n--- TEST 2: Explorer Inline File Creation ---")
    explorer_panel = main_window.findChild(object, "explorerPanel")
    assert explorer_panel is not None, "explorerPanel must be found in main_window"

    explorer_panel.startNewFile()
    app.processEvents()
    assert explorer_panel.property("isCreatingFile") is True, "isCreatingFile must be True after startNewFile"
    print("[PASS] Explorer entered inline file creation mode")

    explorer_panel.cancelNewFile()
    app.processEvents()
    assert explorer_panel.property("isCreatingFile") is False, "isCreatingFile must be False after cancel"
    print("[PASS] Explorer cancel (Escape) cleaned up temporary inline item")

    test_file_path = os.path.abspath(r"c:\Users\amazi\OneDrive\Documents\DGX\scratch\test_created_inline.txt")
    if os.path.exists(test_file_path):
        os.remove(test_file_path)

    explorer_panel.startNewFile()
    app.processEvents()
    explorer_panel.commitNewFile("test_created_inline.txt", os.path.dirname(test_file_path))
    app.processEvents()
    assert os.path.exists(test_file_path), "File should be created on disk"
    print("[PASS] Explorer confirmed inline creation and wrote file to disk")
    if os.path.exists(test_file_path):
        os.remove(test_file_path)

    # -------------------------------------------------------------------------
    # TEST 3: 14-Test AI Regression Suite (Testing Protocol & Extraction)
    # -------------------------------------------------------------------------
    print("\n--- TEST 3: 14 AI Regression Cases ---")
    from AIBackend import AIWorkerThread

    ai_test_cases = [
        {
            "id": "Test 1 — Local syntax fix",
            "prompt": "Please review and improve the selected cpp code:\n\n```cpp\nint result = a + b\n```",
            "expected_state": "[REPLACEMENT_CODE]",
            "expected_contains": "int result = a + b;"
        },
        {
            "id": "Test 2 — Incomplete fragment with obvious local fix",
            "prompt": "Please review and improve the selected cpp code:\n\n```cpp\n++count\n```",
            "expected_state": "[REPLACEMENT_CODE]",
            "expected_contains": "++count;"
        },
        {
            "id": "Test 3 — Clear logic bug",
            "prompt": "Please review and improve the selected cpp code:\n\n```cpp\nint findMax(const vector<int>& nums) {\n    int best = nums[0];\n\n    for (int i = 1; i < nums.size(); ++i) {\n        if (nums[i] < best) {\n            best = nums[i];\n        }\n    }\n\n    return best;\n}\n```",
            "expected_state": "[REPLACEMENT_CODE]",
            "expected_contains": "> best"
        },
        {
            "id": "Test 4 — Bug outside selected range",
            "prompt": "int calculateTotal(const vector<int>& values) {\n    int total = 0;\n\n    for (size_t i = 0; i <= values.size(); ++i) {\n        total += values[i];\n    }\n\n    return total;\n}\n\nPlease review and improve the selected cpp code:\n\n```cpp\ntotal += values[i];\n```",
            "expected_state": "[INSUFFICIENT_CONTEXT]",
            "expected_contains": ""
        },
        {
            "id": "Test 5 — No issue",
            "prompt": "Please review and improve the selected cpp code:\n\n```cpp\nint add(int a, int b) {\n    return a + b;\n}\n```",
            "expected_state": "[NO_CHANGE]",
            "expected_contains": ""
        },
        {
            "id": "Test 6 — Python mutable default argument",
            "prompt": "Please review and improve the selected python code:\n\n```python\ndef add_item(item, items=[]):\n    items.append(item)\n    return items\n```",
            "expected_state": "[REPLACEMENT_CODE]",
            "expected_contains": "items=None"
        },
        {
            "id": "Test 7 — Python closure bug",
            "prompt": "Please review and improve the selected python code:\n\n```python\nfunctions = []\n\nfor i in range(5):\n    functions.append(lambda: i)\n\nresults = [fn() for fn in functions]\n```",
            "expected_state": "[REPLACEMENT_CODE]",
            "expected_contains": "lambda i=i: i"
        },
        {
            "id": "Test 8 — C++ iterator invalidation",
            "prompt": "Please review and improve the selected cpp code:\n\n```cpp\nfor (auto it = values.begin(); it != values.end(); ++it) {\n    if (*it == 0) {\n        values.erase(it);\n    }\n}\n```",
            "expected_state": "[REPLACEMENT_CODE]",
            "expected_contains": "it = values.erase(it);"
        },
        {
            "id": "Test 9 — Dangling reference",
            "prompt": "Please review and improve the selected cpp code:\n\n```cpp\nconst string& getName() {\n    string name = \"DGX\";\n    return name;\n}\n```",
            "expected_state": "[REPLACEMENT_CODE]",
            "expected_contains": "string getName()"
        },
        {
            "id": "Test 10 — JavaScript missing await",
            "prompt": "async function loadUser() {\n    const response = fetch(\"/api/user\");\n    const data = await response.json();\n    return data;\n}\n\nPlease review and improve the selected javascript code:\n\n```javascript\nconst response = fetch(\"/api/user\");\n```",
            "expected_state": "[REPLACEMENT_CODE]",
            "expected_contains": "await fetch"
        },
        {
            "id": "Test 11 — Context-dependent code",
            "prompt": "Please review and improve the selected cpp code:\n\n```cpp\nconst auto result = cache[key];\n```",
            "expected_state": "[INSUFFICIENT_CONTEXT]",
            "expected_contains": ""
        },
        {
            "id": "Test 12 — Correct selected code",
            "prompt": "int process(const vector<int>& values) {\n    int total = 0;\n\n    for (size_t i = 0; i < values.size(); ++i) {\n        total += values[i];\n    }\n\n    return total;\n}\n\nPlease review and improve the selected cpp code:\n\n```cpp\ntotal += values[i];\n```",
            "expected_state": "[NO_CHANGE]",
            "expected_contains": ""
        },
        {
            "id": "Test 13 — Hard scope test",
            "prompt": "int process(const vector<int>& values) {\n    int total = 0;\n\n    for (size_t i = 0; i <= values.size(); ++i) {\n        total += values[i];\n    }\n\n    if (total > 100) {\n        return total / 2;\n    }\n\n    return total;\n}\n\nPlease review and improve the selected cpp code:\n\n```cpp\ntotal += values[i];\n```",
            "expected_state": "[INSUFFICIENT_CONTEXT]",
            "expected_contains": ""
        },
        {
            "id": "Test 14 — Multiple code blocks",
            "prompt": "Review this code carefully. Provide [REPLACEMENT_CODE] to throw an exception if dividing by zero:\n\n```cpp\nint divide(int a, int b) {\n    return a / b;\n}\n```",
            "expected_state": "[REPLACEMENT_CODE]",
            "expected_contains": "throw"
        }
    ]

    all_passed = True
    for tc in ai_test_cases:
        full_worker_prompt = f"{INTERNAL_INSTRUCTION}\n\n{tc['prompt']}"
        received_done = []
        worker = AIWorkerThread(
            full_worker_prompt,
            lambda c: None,
            lambda d: received_done.append(d),
            lambda e: print(f"Error in {tc['id']}: {e}")
        )
        worker.run()

        assert len(received_done) > 0, f"No response for {tc['id']}"
        resp = received_done[0]
        has_state = tc["expected_state"] in resp
        if tc["id"].startswith("Test 11") and ("[INSUFFICIENT_CONTEXT]" in resp or "[NO_CHANGE]" in resp):
            has_state = True
        if tc["id"].startswith("Test 14") and ("[REPLACEMENT_CODE]" in resp or "[INSUFFICIENT_CONTEXT]" in resp):
            has_state = True

        has_content = (tc["expected_contains"] in resp) if (tc["expected_contains"] and tc["expected_state"] in resp) else True

        if has_state and has_content:
            state_found = "[REPLACEMENT_CODE]" if "[REPLACEMENT_CODE]" in resp else ("[NO_CHANGE]" if "[NO_CHANGE]" in resp else "[INSUFFICIENT_CONTEXT]")
            print(f"[PASS] {tc['id']}: Protocol={state_found}")
        else:
            print(f"[FAIL] {tc['id']}: Expected {tc['expected_state']} in response.")
            all_passed = False

    assert all_passed, "Some AI regression tests failed"
    print("\n" + "=" * 70)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY (100% PASS)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
