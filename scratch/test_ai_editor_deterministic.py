import sys
import os
import time

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtCore import QCoreApplication, QObject, QUrl, QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QJSEngine

def test_deterministic_ai_flow():
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
    print("[PASS] Main window loaded successfully")

    editor_area = main_window.findChild(QObject, "editorArea")
    assert editor_area is not None, "editorArea found"

    # =========================================================================
    # TEST 1: HTML SELECTION & RAW AI RESPONSE WITH EXPLANATIONS
    # =========================================================================
    print("\n--- TEST 1: HTML Selection & Explanation Stripping ---")
    editor_area.createNewFile()
    code_text_area = editor_area.property("codeTextArea")
    assert code_text_area is not None

    initial_html = (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head><title>DGX Studio</title></head>\n"
        "<body>\n"
        "  <div class=\"broken-box\">\n"
        "    <p>Unclosed paragraph\n"
        "  <!-- Missing tag -->\n"
        "  <p>Footer note</p>\n"
        "</body>\n"
        "</html>\n"
    )
    code_text_area.setProperty("text", initial_html)

    target_snippet = (
        "  <div class=\"broken-box\">\n"
        "    <p>Unclosed paragraph\n"
        "  <!-- Missing tag -->"
    )
    start_pos = initial_html.index(target_snippet)
    end_pos = start_pos + len(target_snippet)
    code_text_area.select(start_pos, end_pos)

    # 1. Verify button is NOT visible initially
    assert editor_area.property("hasPendingAiReplacement") is False, "Button must not show before AI response"

    # 2. Simulate raw AI response from ChatGPT with explanations before and after
    raw_ai_html_response = (
        "There's one syntax error in your HTML. The key correction is closing the <div> and <p> tags.\n\n"
        "```html\n"
        "  <div class=\"broken-box\">\n"
        "    <p>Unclosed paragraph</p>\n"
        "  </div>\n"
        "```\n\n"
        "Explanation:\n"
        "1. Added closing </p> tag.\n"
        "2. Added closing </div> tag.\n"
        "3. Indentation matches your project standards.\n\n"
        "Hope this helps!"
    )

    # Trigger via AIWorkspace JS extractor -> setPendingAiReplacement
    js_engine = QJSEngine()
    with open("qml/ai/CodeExtractor.js", "r", encoding="utf-8") as f:
        js_code = f.read().replace(".pragma library", "")
    js_engine.evaluate(js_code)

    import json
    extracted_html = js_engine.evaluate(f"extractCodeFromMarkdown({json.dumps(raw_ai_html_response)}, 'html')").toString()

    print(f"Raw AI Response:\n{raw_ai_html_response}\n")
    print(f"Extracted Code Result:\n{extracted_html}\n")

    # Assert extraction rules
    assert "There's one syntax error" not in extracted_html
    assert "The key correction is" not in extracted_html
    assert "Explanation:" not in extracted_html
    assert "Hope this helps" not in extracted_html
    assert "```" not in extracted_html
    assert extracted_html == "  <div class=\"broken-box\">\n    <p>Unclosed paragraph</p>\n  </div>"
    print("[PASS] Extraction rule verified: zero explanation text in extracted code")

    # 3. Deliver extracted code to editor
    editor_area.setPendingAiReplacement(start_pos, end_pos, extracted_html, target_snippet)

    # 4. Verify floating button state
    assert editor_area.property("hasPendingAiReplacement") is True
    assert editor_area.property("pendingAiStart") == start_pos
    assert editor_area.property("pendingAiEnd") == end_pos
    print("[PASS] Floating Replace button state active")

    # 5. Execute replacement
    res = editor_area.replaceSelection(start_pos, end_pos, extracted_html, target_snippet)
    assert res is True, "replaceSelection succeeded"
    assert editor_area.property("hasPendingAiReplacement") is False, "Button hidden after replacement"

    # 6. Verify editor document
    doc_after = code_text_area.property("text")
    assert "<!DOCTYPE html>" in doc_after
    assert "<p>Footer note</p>" in doc_after
    assert "There's one syntax error" not in doc_after
    assert "The key correction is" not in doc_after
    assert "Explanation:" not in doc_after
    assert "```" not in doc_after
    print(f"Document after replacement:\n{doc_after}")
    print("[PASS] Document replaced correctly with pure code only")

    # =========================================================================
    # TEST 2: PYTHON SELECTION & REPLACEMENT
    # =========================================================================
    print("\n--- TEST 2: Python Selection & Replacement ---")
    editor_area.createNewFile()
    code_text_area = editor_area.property("codeTextArea")
    initial_py = "import os\n\ndef old_function(x):\n    return x\n\nprint('Done')\n"
    code_text_area.setProperty("text", initial_py)

    py_target = "def old_function(x):\n    return x"
    py_start = initial_py.index(py_target)
    py_end = py_start + len(py_target)

    raw_ai_py_response = (
        "Here is the optimized Python function:\n\n"
        "```python\n"
        "def old_function(x: int) -> int:\n"
        "    \"\"\"Return computed value.\"\"\"\n"
        "    return x * 2\n"
        "```\n\n"
        "Key changes:\n"
        "- Added type hints."
    )
    extracted_py = js_engine.evaluate(f"extractCodeFromMarkdown({json.dumps(raw_ai_py_response)}, 'python')").toString()
    assert "Here is the optimized" not in extracted_py
    assert "Key changes:" not in extracted_py
    assert extracted_py == "def old_function(x: int) -> int:\n    \"\"\"Return computed value.\"\"\"\n    return x * 2"

    editor_area.setPendingAiReplacement(py_start, py_end, extracted_py, py_target)
    editor_area.replaceSelection(py_start, py_end, extracted_py, py_target)
    py_doc_after = code_text_area.property("text")
    assert "import os" in py_doc_after
    assert "print('Done')" in py_doc_after
    assert "Key changes:" not in py_doc_after
    print("[PASS] Python selection replaced cleanly")

    # =========================================================================
    # TEST 3: QML SELECTION & REPLACEMENT
    # =========================================================================
    print("\n--- TEST 3: QML Selection & Replacement ---")
    editor_area.createNewFile()
    code_text_area = editor_area.property("codeTextArea")
    initial_qml = "import QtQuick 2.15\n\nItem {\n    id: root\n    width: 100\n}\n"
    code_text_area.setProperty("text", initial_qml)

    qml_target = "    id: root\n    width: 100"
    qml_start = initial_qml.index(qml_target)
    qml_end = qml_start + len(qml_target)

    raw_ai_qml_response = (
        "Here is the updated QML code with dimensions:\n\n"
        "```qml\n"
        "    id: root\n"
        "    width: 320\n"
        "    height: 240\n"
        "    visible: true\n"
        "```\n\n"
        "Explanation:\n"
        "1. Added height and visible properties."
    )
    extracted_qml = js_engine.evaluate(f"extractCodeFromMarkdown({json.dumps(raw_ai_qml_response)}, 'qml')").toString()
    assert "Explanation:" not in extracted_qml
    assert extracted_qml == "    id: root\n    width: 320\n    height: 240\n    visible: true"

    editor_area.setPendingAiReplacement(qml_start, qml_end, extracted_qml, qml_target)
    editor_area.replaceSelection(qml_start, qml_end, extracted_qml, qml_target)
    qml_doc_after = code_text_area.property("text")
    assert "import QtQuick 2.15" in qml_doc_after
    assert "Explanation:" not in qml_doc_after
    print("[PASS] QML selection replaced cleanly")

    print("\n========================================================")
    print("ALL DETERMINISTIC TESTS PASSED 100% SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    test_deterministic_ai_flow()
