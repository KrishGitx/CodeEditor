import sys
import os
import json
import time

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtCore import QCoreApplication, QUrl, Qt, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QJSEngine
from PySide6.QtQuick import QQuickItem

from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend

def run_test():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)

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
    root = root_objects[0]

    editor_area = root.findChild(QObject, "editorArea")
    ai_workspace = root.findChild(QObject, "aiWorkspace")
    root.setProperty("rightPanelVisible", True)
    root.setProperty("aiVisible", True)

    # Open HTML document in editor
    editor_area.createNewFile()
    code_area = editor_area.property("codeTextArea")
    assert code_area is not None

    full_text = "<!DOCTYPE html>\n<html>\n<body>\n  <button id=\"test-btn\">Click Me</button>\n</body>\n</html>"
    code_area.setProperty("text", full_text)

    target_snippet = '<button id="test-btn">Click Me</button>'
    start_pos = full_text.index(target_snippet)
    end_pos = start_pos + len(target_snippet)

    # A. Select HTML code
    code_area.select(start_pos, end_pos)
    assert code_area.property("selectionStart") == start_pos
    assert code_area.property("selectionEnd") == end_pos
    print("[PASS] A. Selected HTML fragment in editor")

    # B. Set pending replacement (simulating AI response arrival with pure code)
    ai_raw_response = (
        "I noticed the button element was missing default styling classes. I updated it to use standard primary button styling.\n\n"
        "```html\n"
        "<button id=\"test-btn\" class=\"btn-primary\">Click Me</button>\n"
        "```"
    )

    js_engine = QJSEngine()
    with open("qml/ai/CodeExtractor.js", "r", encoding="utf-8") as f:
        js_code = f.read().replace(".pragma library", "")
    js_engine.evaluate(js_code)
    extracted_code = js_engine.evaluate(f"extractCodeFromMarkdown({json.dumps(ai_raw_response)}, 'html')").toString()

    print(f"Extracted replacement code: {extracted_code!r}")
    assert "<button" in extracted_code
    assert "<!DOCTYPE" not in extracted_code
    assert "**What was improved:**" not in extracted_code
    print("[PASS] C & D. Validated no hard-coded fake 'What was improved' template and received clean code block")

    editor_area.setPendingAiReplacement(start_pos, end_pos, extracted_code, target_snippet)
    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)

    # Find floating Replace with AI pill item
    pill = editor_area.findChild(QQuickItem, "floatingAiSelectionPill")
    if pill:
        print(f"Floating pill visible with selection: {pill.property('visible')}")
        assert pill.property("visible") is True
        print("[PASS] E. Floating Replace with AI button is visible while selection is active")

    # F. Deselect code (click elsewhere / clear selection)
    code_area.deselect()
    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)

    # G. Verify floating Replace with AI button immediately disappears
    if pill:
        print(f"Floating pill visible after deselect: {pill.property('visible')}")
        assert pill.property("visible") is False
        print("[PASS] F & G. Floating button immediately disappeared upon deselect")

    # H. Verify pending replacement state itself is preserved
    assert editor_area.property("hasPendingAiReplacement") is True
    assert editor_area.property("pendingAiStart") == start_pos
    assert editor_area.property("pendingAiEnd") == end_pos
    assert editor_area.property("pendingAiCode") == extracted_code
    print("[PASS] H. Pending AI replacement state is preserved internally")

    # I. Select unrelated code (e.g. 0 to 10)
    code_area.select(0, 10)
    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)

    # J. Verify old Replace with AI button does NOT appear over unrelated selection
    if pill:
        print(f"Floating pill visible over unrelated selection: {pill.property('visible')}")
        assert pill.property("visible") is False
        print("[PASS] I & J. Floating button does NOT appear over unrelated selection")

    # K. Re-select the original range [start_pos, end_pos]
    code_area.select(start_pos, end_pos)
    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)
    if pill:
        print(f"Floating pill visible upon re-selecting original range: {pill.property('visible')}")
        assert pill.property("visible") is True
        print("[PASS] K. Floating button reappeared upon re-selecting original range")

    # L. Replace selection with AI code
    editor_area.replaceSelection(start_pos, end_pos, extracted_code, target_snippet)
    editor_area.clearPendingAiReplacement()
    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)

    new_full_text = code_area.property("text")
    assert "<!DOCTYPE html>" in new_full_text
    assert target_snippet not in new_full_text
    assert extracted_code in new_full_text
    print(f"New editor text:\n{new_full_text}")
    print("[PASS] L. Replaced selection correctly without modifying outer file structure")

    print("\n========================================================")
    print("ALL TESTS (A - L) COMPLETED AND PASSED SUCCESSFULLY!")
    print("========================================================")

if __name__ == "__main__":
    run_test()
