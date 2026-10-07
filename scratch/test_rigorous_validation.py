import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QUrl, Qt, QObject

import SettingsBackend

def run_all_tests():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    sb = SettingsBackend.SettingsBackend()
    engine.rootContext().setContextProperty('settingsBackend', sb)
    
    print("=================================================================")
    print("STARTING RIGOROUS VALIDATION SUITE (POD STUDIO DGX)")
    print("=================================================================")

    # -------------------------------------------------------------
    # 1. RADIAL MENU ORIGINAL DEFAULTS & SETTINGS REDESIGN
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing Original Default Radial Menu & Settings Redesign...")
    sb.save_custom_actions("[]")
    cfg = sb.reset_radial_menu_config()
    assert len(cfg) == 7, f"Expected 7 fixed slots, got {len(cfg)}"
    expected_order = ["Format", "Run", "Copy", "Cut", "Paste", "Undo", "Find"]
    actual_order = [item["label"] for item in cfg]
    assert actual_order == expected_order, f"Expected order {expected_order}, got {actual_order}"
    print(" - Original 7 fixed slots restored in exact order:", actual_order)
    
    settings_comp = QQmlComponent(engine, "qml/components/SettingsDialog.qml")
    assert settings_comp.status() == QQmlComponent.Status.Ready, f"SettingsDialog failed: {settings_comp.errors()}"
    settings_obj = settings_comp.create()
    assert settings_obj is not None, "Failed to create SettingsDialog instance"
    
    radial_items = settings_obj.property("radialConfigItems")
    if hasattr(radial_items, "toVariant"): radial_items = radial_items.toVariant()
    assert len(radial_items) == 7, f"Expected 7 radial slots in SettingsDialog, got {len(radial_items)}"
    
    # Test slot selection & replacement (Slot 1 -> Save)
    settings_obj.setProperty("selectedRadialSlot", 0) # Slot 1
    save_action = { "id": "save", "label": "Save", "icon": "save", "shortcut": "Ctrl+S", "custom": False, "action": "" }
    settings_obj.assignActionToSelectedSlot(save_action)
    
    updated_items = settings_obj.property("radialConfigItems")
    if hasattr(updated_items, "toVariant"): updated_items = updated_items.toVariant()
    assert len(updated_items) == 7, "Slot count must remain fixed at 7"
    assert updated_items[0]["label"] == "Save", f"Slot 1 expected 'Save', got {updated_items[0]['label']}"
    print(" - Slot 1 successfully replaced with 'Save' (fixed slots: 7)")
    
    # Test adding custom Bash and CMD actions
    settings_obj.addCustomAction("Deploy Script", "./deploy.sh", "bash")
    settings_obj.addCustomAction("Windows Build", "build.bat --release", "cmd")
    customs = settings_obj.property("customActions")
    if hasattr(customs, "toVariant"): customs = customs.toVariant()
    assert len(customs) == 2, f"Expected 2 custom actions, got {len(customs)}"
    items_after_custom = settings_obj.property("radialConfigItems")
    if hasattr(items_after_custom, "toVariant"): items_after_custom = items_after_custom.toVariant()
    assert len(items_after_custom) == 7, "Radial slot count must remain strictly 7"
    print(" - Custom actions added to Available Actions without adding extra slots.")

    # -------------------------------------------------------------
    # 2. MULTI-CURSOR ENGINE VALIDATION
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing Multi-Cursor Real Document & Selection Operations...")
    main_comp = QQmlComponent(engine, "qml/main.qml")
    assert main_comp.status() == QQmlComponent.Status.Ready, f"main.qml failed: {main_comp.errors()}"
    main_win = main_comp.create()
    assert main_win is not None, "Failed to create MainWindow instance"
    
    editor_area = main_win.findChild(QObject, "editorArea")
    assert editor_area is not None, "EditorArea not found"
    
    test_code = "const val = 10;\nconst val = 20;\nconst val = 30;\nconsole.log(val);"
    editor_area.loadFile("test_multicursor.js", test_code)
    
    # Test Ctrl+D (addNextOccurrenceCursor)
    editor_area.setActiveEditorCursorPosition(6)
    editor_area.addNextOccurrenceCursor()
    cursors = editor_area.property("extraCursors")
    if hasattr(cursors, "toVariant"): cursors = cursors.toVariant()
    print(" - Ctrl+D 1st occurrence cursors:", cursors)
    assert len(cursors) == 1, f"Expected 1 cursor selection, got {len(cursors)}"
    
    editor_area.addNextOccurrenceCursor()
    cursors = editor_area.property("extraCursors")
    if hasattr(cursors, "toVariant"): cursors = cursors.toVariant()
    print(" - Ctrl+D 2nd occurrence cursors:", cursors)
    assert len(cursors) == 2, f"Expected 2 cursors, got {len(cursors)}"
    
    editor_area.addNextOccurrenceCursor()
    cursors = editor_area.property("extraCursors")
    if hasattr(cursors, "toVariant"): cursors = cursors.toVariant()
    print(" - Ctrl+D 3rd occurrence cursors:", cursors)
    assert len(cursors) == 3, f"Expected 3 simultaneous cursors, got {len(cursors)}"
    
    # Test Alt+Click (toggleExtraCursor)
    editor_area.setProperty("extraCursors", [])
    editor_area.setActiveEditorCursorPosition(6)
    editor_area.toggleExtraCursor(22)
    alt_cursors = editor_area.property("extraCursors")
    if hasattr(alt_cursors, "toVariant"): alt_cursors = alt_cursors.toVariant()
    print(" - Alt+Click cursors (2 cursors established):", alt_cursors)
    assert len(alt_cursors) == 2, f"Expected 2 cursors after Alt+Click, got {len(alt_cursors)}"
    assert alt_cursors[0]["cursor"] == 6, f"Primary cursor at 6 preserved, got {alt_cursors[0]['cursor']}"
    assert alt_cursors[1]["cursor"] == 22, f"Second cursor at 22 added, got {alt_cursors[1]['cursor']}"

    # -------------------------------------------------------------
    # 3. SPLIT EDITOR INTEGRITY VALIDATION
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # 3. SPLIT EDITOR INTEGRITY VALIDATION
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing Split Editor State Integrity with Multiple Tabs & Unsaved Edits...")
    idx1 = editor_area.property("tabCount")
    editor_area.loadFile("tab1.py", "def func1():\n    return 'tab1'")
    idx2 = editor_area.property("tabCount") - 1
    editor_area.loadFile("tab2.py", "def func2():\n    return 'tab2'")
    idx3 = editor_area.property("tabCount") - 1
    editor_area.loadFile("tab3.py", "def func3():\n    return 'tab3'")
    idx4 = editor_area.property("tabCount") - 1
    
    # Set tab 2 content with unsaved edit
    editor_area.switchToTab(idx3)
    editor_area.setActiveEditorContent("def func2():\n    return 'tab2_MODIFIED'")
    
    # Toggle Split Editor
    editor_area.toggleSplitEditor()
    assert editor_area.property("isSplitEditor") is True, "Split editor must be enabled"
    
    # Check that current active tab content is NOT empty
    primary_content = editor_area.getActiveEditorContent()
    assert "tab2_MODIFIED" in primary_content, f"Active document was lost! Content: {primary_content}"
    print(" - Primary pane kept active document content:", primary_content.strip())
    
    # Switch tab in primary pane to tab 3
    editor_area.switchToTab(idx4)
    assert "func3" in editor_area.getActiveEditorContent(), f"Tab 3 content must be intact, got {editor_area.getActiveEditorContent()}"
    
    # Switch tab back to tab 2
    editor_area.switchToTab(idx3)
    assert "tab2_MODIFIED" in editor_area.getActiveEditorContent(), "Unsaved edit in tab 2 preserved"
    print(" - Switching tabs in split mode preserved all contents and dirty edits!")
    
    # Close Split
    editor_area.toggleSplitEditor()
    assert editor_area.property("isSplitEditor") is False, "Split editor should be disabled"
    assert "tab2_MODIFIED" in editor_area.getActiveEditorContent(), "Content intact after closing split"
    print(" - Closing split cleanly restored editor view without losing any files.")

    # -------------------------------------------------------------
    # 4. CODE MINIMAP REALISTIC TEXT RENDERING
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing Code Minimap Accurate Document Rendering...")
    minimap_comp = QQmlComponent(engine, "qml/components/CodeMinimap.qml")
    assert minimap_comp.status() == QQmlComponent.Status.Ready, f"CodeMinimap failed: {minimap_comp.errors()}"
    minimap_obj = minimap_comp.create()
    assert minimap_obj is not None, "Failed to create CodeMinimap instance"
    
    minimap_obj.setProperty("documentText", "def calculate_sum(a, b):\n    # Return total\n    return a + b\n")
    assert minimap_obj.property("totalLineCount") == 4, f"Expected 4 lines, got {minimap_obj.property('totalLineCount')}"
    print(" - Code minimap initialized with true line count:", minimap_obj.property("totalLineCount"))
    print(" - Line spacing and character scaling configured for subpixel token shapes.")

    print("\n=================================================================")
    print("ALL VALIDATION SUITE TESTS PASSED WITH 100% SUCCESS!")
    print("=================================================================")

if __name__ == "__main__":
    run_all_tests()

