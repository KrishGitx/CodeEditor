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

def test_full_flow():
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

    # -------------------------------------------------------------
    # TEST 1: Markdown Segments Parsing & Multiple Code Blocks
    # -------------------------------------------------------------
    js_engine = QJSEngine()
    with open("qml/ai/CodeExtractor.js", "r", encoding="utf-8") as f:
        js_code = f.read().replace(".pragma library", "")
    js_engine.evaluate(js_code)

    raw_ai_multi_response = (
        "Here is the frontend component and backend handler:\n\n"
        "```html\n"
        "<button id=\"save-btn\">Save</button>\n"
        "```\n\n"
        "And the Python endpoint:\n\n"
        "```python\n"
        "def save_handler():\n"
        "    return {'status': 'saved'}\n"
        "```\n\n"
        "All set!"
    )

    segments_val = js_engine.evaluate(f"parseMarkdownSegments({json.dumps(raw_ai_multi_response)})")
    seg_len = segments_val.property("length").toInt()
    assert seg_len >= 5, f"Expected at least 5 segments, got {seg_len}"

    seg0 = segments_val.property("0")
    assert seg0.property("type").toString() == "text"
    assert "Here is the frontend" in seg0.property("text").toString()

    seg1 = segments_val.property("1")
    assert seg1.property("type").toString() == "code"
    assert seg1.property("lang").toString() == "html"
    assert seg1.property("code").toString() == '<button id="save-btn">Save</button>'

    seg3 = segments_val.property("3")
    assert seg3.property("type").toString() == "code"
    assert seg3.property("lang").toString() == "python"
    assert "def save_handler():" in seg3.property("code").toString()

    print("[PASS] TEST 1: CodeExtractor.parseMarkdownSegments properly parsed multi-block response")

    # -------------------------------------------------------------
    # TEST 2: Insert replaces editor selection with pure code
    # -------------------------------------------------------------
    editor_area.createNewFile()
    code_area = editor_area.property("codeTextArea")
    assert code_area is not None

    initial_doc = "<html>\n  <div id=\"old-placeholder\">OLD</div>\n</html>"
    code_area.setProperty("text", initial_doc)

    target_sel = '<div id="old-placeholder">OLD</div>'
    sel_start = initial_doc.index(target_sel)
    sel_end = sel_start + len(target_sel)

    # Select placeholder
    code_area.select(sel_start, sel_end)
    assert code_area.property("selectionStart") == sel_start
    assert code_area.property("selectionEnd") == sel_end

    # Click Insert on block 1 (HTML button)
    html_code = seg1.property("code").toString()
    editor_area.insertSnippet(html_code)

    updated_text = code_area.property("text")
    assert '<button id="save-btn">Save</button>' in updated_text
    assert 'OLD' not in updated_text
    assert "Here is the frontend" not in updated_text
    assert "```" not in updated_text
    print("[PASS] TEST 2: Insert on code block replaced active selection with pure code")

    # -------------------------------------------------------------
    # TEST 3: Per-File Independent Undo/Redo Stacks
    # -------------------------------------------------------------
    # Tab 0: Currently has updated_text. Let's make an edit in Tab 0
    code_area.insert(0, "<!-- FILE A HEADER -->\n")
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)
    tab0_with_header = code_area.property("text")
    assert tab0_with_header.startswith("<!-- FILE A HEADER -->")

    # Undo in Tab 0
    editor_area.undo()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)
    assert not code_area.property("text").startswith("<!-- FILE A HEADER -->")
    print("[PASS] TEST 3A: Tab 0 undo successfully reverted header insert")

    # Redo in Tab 0
    editor_area.redo()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)
    assert code_area.property("text").startswith("<!-- FILE A HEADER -->")
    print("[PASS] TEST 3B: Tab 0 redo successfully restored header insert")

    # Now open Tab 1 (File B)
    editor_area.createNewFile()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)

    code_area_b = editor_area.property("codeTextArea")
    assert code_area_b is not None
    code_area_b.setProperty("text", "def file_b():\n    pass\n")

    # Add an edit in Tab 1
    code_area_b.insert(0, "# FILE B COMMENT\n")
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)
    assert code_area_b.property("text").startswith("# FILE B COMMENT")

    # Switch back to Tab 0 (File A)
    editor_area.switchToTab(0)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)

    code_area_a = editor_area.property("codeTextArea")
    assert code_area_a.property("text").startswith("<!-- FILE A HEADER -->")

    # Undo in Tab 0: must undo ONLY Tab 0 changes and NEVER affect Tab 1!
    editor_area.undo()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)
    assert not code_area_a.property("text").startswith("<!-- FILE A HEADER -->")

    # Switch to Tab 1: verify Tab 1 content is completely untouched!
    editor_area.switchToTab(1)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)
    code_area_b_switched = editor_area.property("codeTextArea")
    assert code_area_b_switched.property("text").startswith("# FILE B COMMENT")
    print("[PASS] TEST 3C: Undo in Tab 0 did not affect Tab 1's content or state")

    # Undo in Tab 1
    editor_area.undo()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)
    assert not code_area_b_switched.property("text").startswith("# FILE B COMMENT")
    print("[PASS] TEST 3D: Undo in Tab 1 operated on Tab 1's independent undo stack")

    print("\n========================================================")
    print("ALL AI CODE RENDERING & PER-FILE UNDO/REDO TESTS PASSED!")
    print("========================================================")

if __name__ == "__main__":
    test_full_flow()
