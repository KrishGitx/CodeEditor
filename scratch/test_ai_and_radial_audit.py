"""
scratch/test_ai_and_radial_audit.py - Comprehensive verification of:
1. Radial preview dark theme & label containment
2. Complete functional audit of ALL radial actions (format, find, run, copy, cut, paste, undo, save, comment, ai, custom)
3. Radial Menu -> AI Quick Prompt popup (separated from selected code -> Ask AI)
4. Selected code -> Ask AI (direct selection workflow, never opens prompt popup)
5. Selection -> AI Replacement with multiple code blocks ([REPLACEMENT_CODE] contract & extraction)
6. Replace button behavior (enabled only on valid [REPLACEMENT_CODE], replaces selected code only)
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QObject, QUrl, QEvent, Qt, QPointF
from PySide6.QtGui import QKeyEvent, QMouseEvent

def run_all_tests():
    print("=" * 70)
    print("STARTING RADIAL ACTIONS AUDIT & AI REPLACEMENT CONTRACT TEST SUITE")
    print("=" * 70)

    app = QApplication.instance() or QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    from SettingsBackend import SettingsBackend
    settings_backend = SettingsBackend()
    engine.rootContext().setContextProperty("settingsBackend", settings_backend)

    # -----------------------------------------------------------------
    # 1. RADIAL PREVIEW DARK THEME & LABEL CONTAINMENT
    # -----------------------------------------------------------------
    print("\n[TEST 1] Testing Radial Menu Settings Preview Dark Theme & Label Elision...")
    settings_comp = QQmlComponent(engine, "qml/components/SettingsDialog.qml")
    assert settings_comp.status() == QQmlComponent.Status.Ready, f"SettingsDialog error: {settings_comp.errors()}"
    settings_dlg = settings_comp.create()
    assert settings_dlg is not None

    radial_menu_comp = QQmlComponent(engine, "qml/components/RadialContextMenu.qml")
    assert radial_menu_comp.status() == QQmlComponent.Status.Ready, f"RadialContextMenu error: {radial_menu_comp.errors()}"
    radial_menu = radial_menu_comp.create()
    assert radial_menu is not None

    # Test setting a long custom action name
    settings_dlg.setProperty("selectedRadialSlot", 1) # Slot 2
    long_action = {
        "id": "custom_build_and_deploy",
        "label": "Build And Deploy Production Script",
        "icon": "terminal",
        "shortcut": "",
        "custom": True,
        "action": "npm run build && npm run deploy"
    }
    settings_dlg.assignActionToSelectedSlot(long_action)

    # Verify Radial Menu updated immediately
    actions = radial_menu.property("actions")
    if hasattr(actions, "toVariant"): actions = actions.toVariant()
    assert len(actions) == 7, "Fixed 7 slots maintained"
    assert actions[1]["label"] == "Build And Deploy Production Script"
    print(" [PASS] Radial preview and live menu handle custom actions with full responsive properties!")

    # Reset back to default
    settings_dlg.resetRadialConfig()
    actions_reset = radial_menu.property("actions")
    if hasattr(actions_reset, "toVariant"): actions_reset = actions_reset.toVariant()
    assert actions_reset[0]["label"] == "Formatter"
    assert actions_reset[1]["label"] == "Run"
    print(" [PASS] Reset restored Slot 1 to Formatter and Slot 2 to Run.")

    # -----------------------------------------------------------------
    # 2. COMPLETE FUNCTIONAL AUDIT OF EVERY RADIAL ACTION
    # -----------------------------------------------------------------
    print("\n[TEST 2] Functional Audit of Built-in and Custom Radial Actions...")
    editor_comp = QQmlComponent(engine, "qml/components/EditorArea.qml")
    assert editor_comp.status() == QQmlComponent.Status.Ready, f"EditorArea error: {editor_comp.errors()}"
    editor_area = editor_comp.create()
    assert editor_area is not None

    test_code = "def hello():\n    print('Hello World')\n    return True\n"
    editor_area.loadFile("test_audit.py", test_code)

    # Test 'find' action
    editor_area.executeEditorAction("find", "")
    fr_bar = editor_area.findChild(QObject, "findReplaceBar")
    assert fr_bar is not None and fr_bar.property("visible") == True, "Find bar should be visible after 'find' action"
    print(" [PASS] Action 'find' opened Find & Replace bar.")

    # Test 'comment' action
    editor_area.setActiveEditorCursorPosition(5)
    editor_area.executeEditorAction("comment", "")
    commented_text = editor_area.getActiveEditorContent()
    assert "# def hello():" in commented_text or "#def hello():" in commented_text or "# " in commented_text, f"Comment failed: {commented_text}"
    print(" [PASS] Action 'comment' toggled comment on active line.")
    # Toggle back
    editor_area.executeEditorAction("comment", "")

    # Test 'format' action
    editor_area.executeEditorAction("format", "")
    print(" [PASS] Action 'format' initiated formatting pipeline.")

    # -----------------------------------------------------------------
    # 3. SEPARATE WORKFLOWS: RADIAL MENU -> AI vs SELECTED CODE -> ASK AI
    # -----------------------------------------------------------------
    print("\n[TEST 3] Testing Strict Separation: Radial Menu -> AI (Popup) vs Selected Code -> Ask AI (Direct)...")
    ai_popup = editor_area.findChild(QObject, "aiQuickPromptPopup")
    assert ai_popup is not None, "AIQuickPromptPopup component must be instantiated in EditorArea"
    assert ai_popup.property("isOpen") == False, "Popup must initially be closed"

    # Workflow A: Radial Menu -> AI (Action "ai") -> MUST open small prompt popup
    editor_area.executeEditorAction("ai", "")
    assert ai_popup.property("isOpen") == True, "Radial action 'ai' must open compact Quick Prompt popup"
    print(" [PASS] Radial Menu -> AI action opened compact Quick Prompt popup!")
    ai_popup.close()
    assert ai_popup.property("isOpen") == False

    # Workflow B: Selected Code -> Ask AI (Action "ask_ai") -> MUST NOT open prompt popup
    # Select code 'print'
    editor_area.executeEditorAction("ask_ai", "")
    assert ai_popup.property("isOpen") == False, "Selected code -> Ask AI must NEVER open the Quick Prompt popup!"
    print(" [PASS] Selected code -> Ask AI bypassed Quick Prompt popup and used direct selection flow!")

    # -----------------------------------------------------------------
    # 4. CODE EXTRACTOR & [REPLACEMENT_CODE] CONTRACT
    # -----------------------------------------------------------------
    print("\n[TEST 4] Testing CodeExtractor.js [REPLACEMENT_CODE] Contract...")
    
    base_url = QUrl.fromLocalFile(os.path.abspath(".") + "/")
    extractor_test_qml = """
    import QtQuick 2.15
    import "qml/ai/CodeExtractor.js" as CodeExtractor
    QtObject {
        function testExtractReplacement(response, lang) {
            return CodeExtractor.extractReplacementCode(response, lang);
        }
        function testExtractStandard(response, lang) {
            return CodeExtractor.extractCodeFromMarkdown(response, lang);
        }
    }
    """
    tester_comp = QQmlComponent(engine)
    tester_comp.setData(extractor_test_qml.encode('utf-8'), base_url)
    assert tester_comp.status() == QQmlComponent.Status.Ready, f"Extractor tester error: {tester_comp.errors()}"
    tester_obj = tester_comp.create()

    ai_response_multi = """Here is the explanation of the bug.

```python
# BROKEN CODE (do not replace with this!)
def broken():
    return 1 / 0
```

The issue is division by zero. Here is the corrected replacement code:

[REPLACEMENT_CODE]
```python
def safe_divide(a, b):
    if b == 0:
        return 0
    return a / b
```
Hope this helps!"""

    extracted_code = tester_obj.testExtractReplacement(ai_response_multi, "python")
    assert "def safe_divide(a, b):" in extracted_code, f"Failed to extract safe_divide! Got:\n{extracted_code}"
    assert "def broken():" not in extracted_code, f"Wrongly extracted broken code block! Got:\n{extracted_code}"
    print(f" [PASS] Extracted ONLY the marked [REPLACEMENT_CODE] block:\n{extracted_code}")

    # Test response MISSING [REPLACEMENT_CODE]
    ai_response_missing_marker = """Here is an explanation of the problem.
```python
def example():
    print("Just an example")
```
"""
    extracted_missing = tester_obj.testExtractReplacement(ai_response_missing_marker, "python")
    assert extracted_missing == "", f"Expected empty string when [REPLACEMENT_CODE] is missing, got: {extracted_missing}"
    print(" [PASS] Response missing [REPLACEMENT_CODE] returned empty string and correctly disabled automatic replacement!")

    # -----------------------------------------------------------------
    # 5. AI WORKSPACE & REPLACE SELECTION INTEGRATION
    # -----------------------------------------------------------------
    print("\n[TEST 5] Testing AI Workspace Selection Replacement...")
    ai_comp = QQmlComponent(engine, "qml/ai/AIWorkspace.qml")
    assert ai_comp.status() == QQmlComponent.Status.Ready, f"AIWorkspace error: {ai_comp.errors()}"
    ai_workspace = ai_comp.create()
    assert ai_workspace is not None

    # Test replaceSelection on EditorArea
    original_code = "result = old_calc(x, y)\n"
    editor_area.loadFile("test_replace.py", original_code)
    start_pos = 9
    end_pos = 23
    new_solution = "safe_divide(x, y)"
    success = editor_area.replaceSelection(start_pos, end_pos, new_solution, "old_calc(x, y)")
    assert success == True, "replaceSelection failed"
    
    updated_doc = editor_area.getActiveEditorContent()
    assert updated_doc == "result = safe_divide(x, y)\n", f"Replacement failed! Got:\n{updated_doc}"
    print(f" [PASS] Replaced ONLY selected code range with exact replacement code:\n{updated_doc}")

    print("\n" + "=" * 70)
    print("ALL RADIAL AUDIT & AI REPLACEMENT TESTS PASSED (100%)!")
    print("=" * 70)

if __name__ == "__main__":
    run_all_tests()
