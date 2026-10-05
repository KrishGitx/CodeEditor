import sys
import os
import json

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtCore import QCoreApplication, QObject, QUrl, QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QJSEngine

def test_selection_replacement_workflow():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)

    from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend

    engine = QQmlApplicationEngine()
    engine.addImportPath("qml")

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

    engine.load(QUrl.fromLocalFile("qml/main.qml"))

    root_objects = engine.rootObjects()
    assert len(root_objects) > 0, "Failed to load qml/main.qml!"
    main_window = root_objects[0]
    print("[PASS] Main window loaded")

    editor_area = main_window.findChild(QObject, "editorArea")
    assert editor_area is not None

    # =========================================================================
    # TEST 1: BUTTON / STYLE FRAGMENT SELECTION IN HTML (SELECTED-SCOPE ONLY)
    # =========================================================================
    print("\n--- TEST 1: HTML Button/Style Fragment Scope Test ---")
    editor_area.createNewFile()
    code_text_area = editor_area.property("codeTextArea")
    assert code_text_area is not None

    full_html_document = (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "    <meta charset=\"UTF-8\">\n"
        "    <title>My Website</title>\n"
        "    <style>\n"
        "        .hero-btn { color: red; }\n"
        "    </style>\n"
        "</head>\n"
        "<body>\n"
        "    <div class=\"header\">\n"
        "        <button class=\"hero-btn\">Click Me</button>\n"
        "    </div>\n"
        "</body>\n"
        "</html>\n"
    )
    code_text_area.setProperty("text", full_html_document)

    # User selects ONLY the button fragment
    selected_fragment = "<button class=\"hero-btn\">Click Me</button>"
    start_pos = full_html_document.index(selected_fragment)
    end_pos = start_pos + len(selected_fragment)
    code_text_area.select(start_pos, end_pos)

    # 1. Before AI request: button is not active
    assert editor_area.property("hasPendingAiReplacement") is False

    # 2. Start AI request on selection: button must appear immediately in GENERATING / DISABLED / GREYED state
    editor_area.startPendingAiReplacement(start_pos, end_pos, selected_fragment)
    assert editor_area.property("hasPendingAiReplacement") is True, "Button must be visible when generation starts"
    assert editor_area.property("isAiReplacementGenerating") is True, "State must be generating"
    assert editor_area.property("pendingAiCode") == "", "Code must be empty while generating"
    print("[PASS] 1. Replace with AI button is immediately visible, disabled & greyed out during generation")

    # 3. Raw response simulation: AI returns replacement for button with potential UI noise
    raw_ai_response = (
        "Log in for more personalized help with writing, rewriting, and translation.\n"
        "Log in Sign up for free\n\n"
        "```html\n"
        "<button class=\"hero-btn\" style=\"background-color: blue;\">Submit Now</button>\n"
        "```\n\n"
        "What was improved:\n"
        "- Added background styling."
    )

    # Test CodeExtractor.js logic
    js_engine = QJSEngine()
    with open("qml/ai/CodeExtractor.js", "r", encoding="utf-8") as f:
        js_code = f.read().replace(".pragma library", "")
    js_engine.evaluate(js_code)

    extracted_button = js_engine.evaluate(f"extractCodeFromMarkdown({json.dumps(raw_ai_response)}, 'html')").toString()
    print(f"Extracted Fragment Code:\n{extracted_button}")

    # Verify extraction guarantees
    assert "<!DOCTYPE" not in extracted_button, "Must NOT contain surrounding <!DOCTYPE>"
    assert "<html" not in extracted_button, "Must NOT recreate <html>"
    assert "<head" not in extracted_button, "Must NOT recreate <head>"
    assert "<body" not in extracted_button, "Must NOT recreate <body>"
    assert "Log in" not in extracted_button, "Must NOT contain login/sign-up text"
    assert "Sign up" not in extracted_button, "Must NOT contain sign-up text"
    assert "What was improved" not in extracted_button, "Must NOT contain commentary"
    assert extracted_button == "<button class=\"hero-btn\" style=\"background-color: blue;\">Submit Now</button>"
    print("[PASS] 2. Verified zero document-wrapper recreation and zero login/sign-up noise")

    # 4. Delivery of complete response enables the button
    editor_area.setPendingAiReplacement(start_pos, end_pos, extracted_button, selected_fragment)
    assert editor_area.property("hasPendingAiReplacement") is True
    assert editor_area.property("isAiReplacementGenerating") is False
    assert editor_area.property("pendingAiCode") == extracted_button
    print("[PASS] 3. Button becomes active and enabled after AI generation finishes")

    # 5. Execute replacement
    res = editor_area.replaceSelection(start_pos, end_pos, extracted_button, selected_fragment)
    assert res is True
    assert editor_area.property("hasPendingAiReplacement") is False, "Button hidden after replacement"

    # 6. Verify full document text
    doc_after = code_text_area.property("text")
    assert "<!DOCTYPE html>" in doc_after
    assert ".hero-btn { color: red; }" in doc_after
    assert "<button class=\"hero-btn\" style=\"background-color: blue;\">Submit Now</button>" in doc_after
    assert "Log in" not in doc_after
    assert "Sign up" not in doc_after
    print(f"Final Document Text:\n{doc_after}")
    print("[PASS] 4. Replacement successfully updated ONLY the selected fragment without disturbing document")

    # =========================================================================
    # TEST 2: PYTHON SNIPPET SCOPE & LOGIN NOISE
    # =========================================================================
    print("\n--- TEST 2: Python Snippet Scope & Sanitization ---")
    editor_area.createNewFile()
    py_text_area = editor_area.property("codeTextArea")
    full_py = "import os\n\ndef add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n"
    py_text_area.setProperty("text", full_py)

    py_fragment = "def add(a, b):\n    return a + b"
    py_start = full_py.index(py_fragment)
    py_end = py_start + len(py_fragment)

    editor_area.startPendingAiReplacement(py_start, py_end, py_fragment)
    assert editor_area.property("isAiReplacementGenerating") is True

    raw_py_resp = (
        "Log in for more personalized help with writing, rewriting, and translation.\n"
        "```python\n"
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
        "```"
    )
    extracted_py = js_engine.evaluate(f"extractCodeFromMarkdown({json.dumps(raw_py_resp)}, 'python')").toString()
    assert "Log in" not in extracted_py
    assert extracted_py == "def add(a: int, b: int) -> int:\n    return a + b"

    editor_area.setPendingAiReplacement(py_start, py_end, extracted_py, py_fragment)
    assert editor_area.property("isAiReplacementGenerating") is False

    editor_area.replaceSelection(py_start, py_end, extracted_py, py_fragment)
    py_doc_after = py_text_area.property("text")
    assert "def multiply(a, b):" in py_doc_after
    assert "def add(a: int, b: int) -> int:" in py_doc_after
    print("[PASS] Python fragment replaced cleanly")

    print("\n========================================================")
    print("ALL SELECTION REPLACEMENT WORKFLOW TESTS PASSED 100%!")
    print("========================================================")

if __name__ == "__main__":
    test_selection_replacement_workflow()
