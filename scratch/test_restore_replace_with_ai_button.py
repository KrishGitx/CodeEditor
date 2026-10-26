import sys
import os
import time

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtCore import QCoreApplication, QUrl, Qt, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem

from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend

def test_replace_with_ai_button_restoration():
    print("=" * 80)
    print("PART 1: VERIFY REPLACE WITH AI BUTTON RESTORATION & ACCEPTANCE CRITERIA")
    print("=" * 80)

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
    main_window = root_objects[0]

    editor_area = main_window.findChild(QObject, "editorArea")
    ai_workspace = main_window.findChild(QObject, "aiWorkspace")
    assert editor_area is not None, "editorArea must exist"

    # Open a new file in editorArea
    editor_area.createNewFile()
    code_text_area = editor_area.property("codeTextArea")
    assert code_text_area is not None, "codeTextArea must exist"

    sample_doc = (
        "def compute_total(a, b):\n"
        "    result = a + b;\n"
        "    return result\n"
    )
    code_text_area.setProperty("text", sample_doc)

    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)

    pill = editor_area.property("floatingAiSelectionPill") or editor_area.findChild(QQuickItem, "floatingAiSelectionPill")
    assert pill is not None, "floatingAiSelectionPill item must exist in QML hierarchy"

    # -------------------------------------------------------------------------
    # Acceptance Test 1: Selecting text does NOT show button; only AI code generation shows it
    # -------------------------------------------------------------------------
    print("\n--- Test 1: Selecting text keeps button hidden; only AI code generation shows it ---")
    assert pill.property("visible") is False, "Button must initially be hidden when nothing is selected"

    target_1 = "result = a + b;"
    start_1 = sample_doc.index(target_1)
    end_1 = start_1 + len(target_1)
    code_text_area.select(start_1, end_1)

    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)

    # User requirement: "repace with ai btn is only supp to show when ai have the code generated , not by selectin text"
    assert pill.property("visible") is False, "Button must NOT appear by merely selecting text"

    # Start generation: button must still be hidden
    editor_area.startPendingAiReplacement(start_1, end_1, target_1)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)
    assert pill.property("visible") is False, "Button must NOT appear while AI is actively generating"

    # AI arrives with generated replacement code
    replaced_code = "result = a + b"
    editor_area.setPendingAiReplacement(start_1, end_1, replaced_code, target_1)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)

    assert pill.property("visible") is True, "Button MUST appear once AI replacement code is generated"
    assert pill.property("enabled") is True, "Button must be enabled when AI code is ready"
    assert pill.property("isReplacementReady") is True, "Button is marked ready for replacement"
    print("[PASS] 1. Replace with AI button is hidden on selection and only appears when AI generates code.")

    # -------------------------------------------------------------------------
    # Acceptance Test 2: Deselection / Unrelated selection hides button; Re-selecting target restores it
    # -------------------------------------------------------------------------
    print("\n--- Test 2: Clearing hides the button, re-selecting target range restores it ---")
    code_text_area.deselect()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)
    assert pill.property("visible") is False, "Button must hide when selection is cleared"

    # Select another range without pending AI code
    target_2 = "return result"
    start_2 = sample_doc.index(target_2)
    end_2 = start_2 + len(target_2)
    code_text_area.select(start_2, end_2)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)
    assert pill.property("visible") is False, "Button must remain hidden for selection without AI code"

    # Re-select target 1 range where AI code is ready
    code_text_area.select(start_1, end_1)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)
    assert pill.property("visible") is True, "Button must reappear when target range with generated code is selected"
    print("[PASS] 2. Button cleanly hides on deselect/other selection and reappears on matching target.")

    # -------------------------------------------------------------------------
    # Acceptance Test 3: Successfully replacing code hides button; subsequent selection stays hidden
    # -------------------------------------------------------------------------
    print("\n--- Test 3: Successfully replacing code hides button and subsequent selections stay hidden ---")
    # Apply replacement
    editor_area.replaceSelection(start_1, end_1, replaced_code, target_1)
    editor_area.clearPendingAiReplacement()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)

    assert pill.property("visible") is False, "Button must hide immediately after replacement is applied"

    current_text = code_text_area.property("text")
    assert "result = a + b;" not in current_text, "Semicolon removed"
    assert "result = a + b\n" in current_text, "Replaced code in place"

    # Selecting new text afterwards must NOT show button
    new_doc = code_text_area.property("text")
    target_3 = "def compute_total(a, b):"
    s3 = new_doc.index(target_3)
    e3 = s3 + len(target_3)
    code_text_area.select(s3, e3)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)

    assert pill.property("visible") is False, "Button must NOT appear for subsequent selection without AI code"
    print("[PASS] 3. Replacement succeeded and button stays hidden on subsequent text selections.")

    # -------------------------------------------------------------------------
    # Acceptance Test 4: Failed / cancelled generation leaves button hidden
    # -------------------------------------------------------------------------
    print("\n--- Test 4: Failed / cancelled AI generation leaves button hidden ---")
    editor_area.startPendingAiReplacement(s3, e3, target_3)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)
    assert pill.property("visible") is False, "Button hidden during generation"

    if ai_workspace:
        ai_workspace.aiReplacementFailed.emit()
    editor_area.clearPendingAiReplacement()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)

    assert pill.property("visible") is False, "Button must remain hidden if generation was cancelled or failed"
    print("[PASS] 4. Failed/cancelled generation cleanly leaves button hidden.")

    # -------------------------------------------------------------------------
    # Acceptance Test 5: Toggling AI panel preserves button visibility when code is ready
    # -------------------------------------------------------------------------
    print("\n--- Test 5: Toggling AI panel preserves button visibility when code is ready ---")
    gen_code_3 = "def compute_total(x: int, y: int) -> int:"
    editor_area.setPendingAiReplacement(s3, e3, gen_code_3, target_3)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)

    assert pill.property("visible") is True, "Button is visible when AI code is generated"

    main_window.setProperty("aiVisible", False)
    main_window.setProperty("rightPanelVisible", False)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)

    assert pill.property("visible") is True, "Button remains visible while code is pending and selected"

    # Reopen AI panel
    main_window.setProperty("rightPanelVisible", True)
    main_window.setProperty("aiVisible", True)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)

    assert pill.property("visible") is True, "Button remains visible and functional after panel reopened"
    editor_area.clearPendingAiReplacement()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.01)
    assert pill.property("visible") is False, "Button hides once cleared"
    print("[PASS] 5. Toggling AI panel visibility preserves button state properly.")

    print("\n" + "=" * 80)
    print("ALL PART 1 ACCEPTANCE TESTS PASSED 100%!")
    print("=" * 80)

if __name__ == "__main__":
    test_replace_with_ai_button_restoration()
    os._exit(0)
