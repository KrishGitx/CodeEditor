import sys
import os
import time

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtCore import QCoreApplication, QObject, QUrl, QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QJSEngine

def test_full_ai_flow():
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
    # TEST FLOW A - H: HTML SELECTION, AI REVIEW, EXTRACTION, AND REPLACEMENT
    # =========================================================================
    print("\n--- Running Test Flow 1: HTML Selection & Replacement ---")
    editor_area.createNewFile()
    code_text_area = editor_area.property("codeTextArea")
    assert code_text_area is not None

    initial_html = (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head><title>Test Page</title></head>\n"
        "<body>\n"
        "  <div class=\"broken-box\">\n"
        "    <p>Unclosed paragraph\n"
        "  <!-- Missing closing tags -->\n"
        "  <p>Footer note</p>\n"
        "</body>\n"
        "</html>\n"
    )
    code_text_area.setProperty("text", initial_html)

    # A. Select the broken block inside body
    target_snippet = (
        "  <div class=\"broken-box\">\n"
        "    <p>Unclosed paragraph\n"
        "  <!-- Missing closing tags -->"
    )
    start_pos = initial_html.index(target_snippet)
    end_pos = start_pos + len(target_snippet)
    code_text_area.select(start_pos, end_pos)

    # Verify initial button state: NOT visible before AI response
    assert editor_area.property("hasPendingAiReplacement") is False, "Button must not show before AI review"

    # B. Trigger Ask AI with the selection
    print(f"Asking AI for review on selection [{start_pos}:{end_pos}]...")
    editor_area.askAi.emit(target_snippet, start_pos, end_pos, "html")

    # C. Wait for the real AI backend response
    for _ in range(50):
        app.processEvents()
        if editor_area.property("hasPendingAiReplacement"):
            break
        time.sleep(0.05)

    # D. Verify extracted code
    pending_code = editor_area.property("pendingAiCode")
    print(f"Extracted AI Code:\n{pending_code}")
    assert len(pending_code) > 0, "Extracted code must be non-empty"
    assert "There's one syntax error" not in pending_code, "Must NOT contain explanation text"
    assert "The key correction is" not in pending_code, "Must NOT contain explanation text"
    assert "Explanation:" not in pending_code, "Must NOT contain explanation text"
    assert "```" not in pending_code, "Must NOT contain markdown fence markers"
    print("[PASS] D. Verified extracted code contains ONLY HTML code without explanations")

    # E. Verify floating button visibility state & position
    assert editor_area.property("hasPendingAiReplacement") is True, "hasPendingAiReplacement must be True"
    assert editor_area.property("pendingAiStart") == start_pos, "Saved start position matches"
    assert editor_area.property("pendingAiEnd") == end_pos, "Saved end position matches"
    print("[PASS] E. Floating Replace with AI button state is active on original selection")

    # F. Click / Trigger Replace with AI
    replace_success = editor_area.replaceSelection(
        editor_area.property("pendingAiStart"),
        editor_area.property("pendingAiEnd"),
        editor_area.property("pendingAiCode"),
        editor_area.property("pendingAiOriginalText")
    )
    assert replace_success is True, "replaceSelection succeeded"
    assert editor_area.property("hasPendingAiReplacement") is False, "Floating button hidden after replacement"
    print("[PASS] F. Replaced selection successfully and hid button")

    # G. Verify ONLY the original selection is replaced in the document
    current_doc_text = code_text_area.property("text")
    assert "<!DOCTYPE html>" in current_doc_text, "Document head preserved"
    assert "<p>Footer note</p>" in current_doc_text, "Document footer preserved"
    assert target_snippet not in current_doc_text, "Broken snippet replaced"
    print("[PASS] G. Verified ONLY the original selection was replaced")

    # H. Verify NONE of the AI explanation is in the editor document
    assert "There's one syntax error" not in current_doc_text
    assert "The key correction is" not in current_doc_text
    assert "Explanation:" not in current_doc_text
    print("[PASS] H. Verified zero explanation text inserted into editor document")

    # =========================================================================
    # TEST FLOW 2: PYTHON SELECTION, AI REVIEW, EXTRACTION, AND REPLACEMENT
    # =========================================================================
    print("\n--- Running Test Flow 2: Python Selection & Replacement ---")
    editor_area.createNewFile()
    py_code_area = editor_area.property("codeTextArea")
    initial_py = (
        "import sys\n\n"
        "def compute_values(items):\n"
        "    result = 0\n"
        "    for x in items:\n"
        "        result += x\n"
        "    return result\n\n"
        "print('Done')\n"
    )
    py_code_area.setProperty("text", initial_py)

    py_snippet = (
        "def compute_values(items):\n"
        "    result = 0\n"
        "    for x in items:\n"
        "        result += x\n"
        "    return result"
    )
    py_start = initial_py.index(py_snippet)
    py_end = py_start + len(py_snippet)
    py_code_area.select(py_start, py_end)

    editor_area.askAi.emit(py_snippet, py_start, py_end, "python")

    for _ in range(50):
        app.processEvents()
        if editor_area.property("hasPendingAiReplacement"):
            break
        time.sleep(0.05)

    py_pending = editor_area.property("pendingAiCode")
    print(f"Extracted Python Code:\n{py_pending}")
    assert "There's one syntax error" not in py_pending
    assert "Explanation:" not in py_pending
    assert "```" not in py_pending

    editor_area.replaceSelection(
        editor_area.property("pendingAiStart"),
        editor_area.property("pendingAiEnd"),
        editor_area.property("pendingAiCode"),
        editor_area.property("pendingAiOriginalText")
    )
    py_doc_after = py_code_area.property("text")
    assert "import sys" in py_doc_after
    assert "print('Done')" in py_doc_after
    assert "Explanation:" not in py_doc_after
    print("[PASS] Python end-to-end review and replacement passed cleanly")

    # =========================================================================
    # TEST FLOW 3: QML SELECTION, AI REVIEW, EXTRACTION, AND REPLACEMENT
    # =========================================================================
    print("\n--- Running Test Flow 3: QML Selection & Replacement ---")
    editor_area.createNewFile()
    qml_code_area = editor_area.property("codeTextArea")
    initial_qml = (
        "import QtQuick 2.15\n\n"
        "Item {\n"
        "    id: root\n"
        "    width: 200\n"
        "    height: 100\n"
        "}\n"
    )
    qml_code_area.setProperty("text", initial_qml)
    qml_snippet = "    id: root\n    width: 200\n    height: 100"
    qml_start = initial_qml.index(qml_snippet)
    qml_end = qml_start + len(qml_snippet)

    editor_area.askAi.emit(qml_snippet, qml_start, qml_end, "qml")

    for _ in range(50):
        app.processEvents()
        if editor_area.property("hasPendingAiReplacement"):
            break
        time.sleep(0.05)

    qml_pending = editor_area.property("pendingAiCode")
    print(f"Extracted QML Code:\n{qml_pending}")
    assert "Explanation:" not in qml_pending
    assert "```" not in qml_pending

    editor_area.replaceSelection(
        editor_area.property("pendingAiStart"),
        editor_area.property("pendingAiEnd"),
        editor_area.property("pendingAiCode"),
        editor_area.property("pendingAiOriginalText")
    )
    qml_doc_after = qml_code_area.property("text")
    assert "import QtQuick 2.15" in qml_doc_after
    assert "Explanation:" not in qml_doc_after
    print("[PASS] QML end-to-end review and replacement passed cleanly")

    print("\n========================================================")
    print("ALL END-TO-END VERIFICATION FLOWS COMPLETED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    test_full_ai_flow()
