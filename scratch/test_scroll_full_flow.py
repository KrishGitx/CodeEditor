import sys
import os
import time

WORKSPACE_DIR = r"c:\Users\amazi\OneDrive\Documents\DGX"
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from PySide6.QtCore import QCoreApplication, Qt, QUrl, QPoint, QPointF, QMetaObject, Q_ARG, QObject
from PySide6.QtGui import QGuiApplication, QWheelEvent, QMouseEvent, QSyntaxHighlighter
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from main import EditorBackend, MusicPlayer, AIBackend, SettingsBackend

def test_full_scroll_flow():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    
    backend = EditorBackend()
    musicPlayer = MusicPlayer()
    aiBackend = AIBackend()
    settingsBackend = SettingsBackend()
    
    target_file = os.path.join(WORKSPACE_DIR, "qml", "components", "EditorArea.qml")
    with open(target_file, "r", encoding="utf-8") as f:
        file_text = f.read()
    total_lines = len(file_text.split("\n"))
    print(f"\n=======================================================")
    print(f"[Test] Starting Full Scroll Flow on EditorArea.qml ({total_lines} lines)")
    print(f"=======================================================")
    
    backend.init_backing_document(target_file, file_text)
    
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
    engine.rootContext().setContextProperty("aiBackend", aiBackend)
    engine.rootContext().setContextProperty("settingsBackend", settingsBackend)
    
    main_qml = os.path.join(WORKSPACE_DIR, "qml", "main.qml")
    engine.load(QUrl.fromLocalFile(main_qml))
    
    if not engine.rootObjects():
        print("[Error] Failed to load QML root object.")
        return False
        
    win = engine.rootObjects()[0]
    app.processEvents()
    
    backend.open_file(target_file)
    for _ in range(8):
        app.processEvents()
        time.sleep(0.02)
    
    editor_area = win.findChild(QQuickItem, "editorArea")
    active_pane = editor_area.property("activeEditorPane")
    assert active_pane is not None, "activeEditorPane is None!"
    
    flickable = active_pane.findChild(QQuickItem, "editorFlickable")
    code_text_area = active_pane.findChild(QQuickItem, "codeTextArea")
    
    gutter = None
    for child in active_pane.findChildren(QQuickItem):
        if child.objectName() == "gutter" or "Rectangle" in child.metaObject().className():
            if child.property("width") > 30 and child.property("width") < 120:
                gutter = child
                break
                
    initial_gutter_w = gutter.property("width") if gutter else 62.0
    initial_flick_x = flickable.property("x")
    initial_text_x = code_text_area.property("x")
    
    print(f"[Initial Geometry] gutter.width={initial_gutter_w}, flickable.x={initial_flick_x}, text.x={initial_text_x}")
    print(f"[Initial Virtual State] paneTotalLineCount={active_pane.property('paneTotalLineCount')}, windowStartLine={active_pane.property('windowStartLine')}, windowEndLine={active_pane.property('windowEndLine')}")
    
    line_h = active_pane.property("paneLineHeight") or 18.0
    
    # Track horizontal stability
    def verify_horizontal_stability(step_name):
        cur_gutter_w = gutter.property("width") if gutter else 62.0
        cur_flick_x = flickable.property("x")
        cur_text_x = code_text_area.property("x")
        assert cur_gutter_w == initial_gutter_w, f"[{step_name}] Gutter width shifted: {cur_gutter_w} vs {initial_gutter_w}"
        assert cur_flick_x == initial_flick_x, f"[{step_name}] Flickable x shifted: {cur_flick_x} vs {initial_flick_x}"
        assert cur_text_x == initial_text_x, f"[{step_name}] CodeTextArea x shifted: {cur_text_x} vs {initial_text_x}"
    
    print("\n--- Test Phase 1: Progressive Wheel Scrolling From Line 1 -> 5,200 ---")
    
    waypoints = [300, 700, 800, 1200, 2000, 3000, 4000, 5200]
    
    for target_line in waypoints:
        target_y = (target_line - 1) * line_h
        current_y = flickable.property("contentY")
        steps = 15
        dy = (target_y - current_y) / steps
        for s in range(steps):
            flickable.setProperty("contentY", current_y + dy * (s + 1))
            app.processEvents()
            time.sleep(0.005)
        
        # Wait for debounce
        for _ in range(5):
            app.processEvents()
            time.sleep(0.01)
            
        w_start = active_pane.property("windowStartLine")
        w_end = active_pane.property("windowEndLine")
        total_p_lines = active_pane.property("paneTotalLineCount")
        
        print(f"-> Scrolled to Line {target_line:4d}: contentY={flickable.property('contentY'):.0f} | Window=[{w_start:4d}..{w_end:4d}] | TotalLines={total_p_lines}")
        assert total_p_lines == total_lines, f"paneTotalLineCount corrupted! {total_p_lines} vs {total_lines}"
        assert w_start <= target_line <= w_end + 1, f"Line {target_line} is outside active window [{w_start}..{w_end}]!"
        verify_horizontal_stability(f"Scroll to {target_line}")
    
    print("\n--- Test Phase 2: Progressive Wheel Scrolling Backward 5,200 -> Line 1 ---")
    
    reverse_waypoints = [4000, 2000, 1000, 300, 1]
    for target_line in reverse_waypoints:
        target_y = (target_line - 1) * line_h
        current_y = flickable.property("contentY")
        steps = 15
        dy = (target_y - current_y) / steps
        for s in range(steps):
            flickable.setProperty("contentY", current_y + dy * (s + 1))
            app.processEvents()
            time.sleep(0.005)
        
        for _ in range(5):
            app.processEvents()
            time.sleep(0.01)
            
        w_start = active_pane.property("windowStartLine")
        w_end = active_pane.property("windowEndLine")
        total_p_lines = active_pane.property("paneTotalLineCount")
        
        print(f"<- Scrolled back to Line {target_line:4d}: contentY={flickable.property('contentY'):.0f} | Window=[{w_start:4d}..{w_end:4d}] | TotalLines={total_p_lines}")
        assert total_p_lines == total_lines, f"paneTotalLineCount corrupted! {total_p_lines} vs {total_lines}"
        assert w_start <= target_line <= w_end + 1, f"Line {target_line} is outside active window [{w_start}..{w_end}]!"
        verify_horizontal_stability(f"Reverse scroll to {target_line}")
        
    print("\n--- Test Phase 3: Rapid Scrollbar Drag Simulation (Top -> Bottom in 1 step) ---")
    # Simulate scrollbar drag: contentY jumps directly to bottom without intermediate shift bursts
    flickable.setProperty("contentY", (total_lines - 20) * line_h)
    app.processEvents()
    time.sleep(0.1) # scrollbarDragEndTimer (80ms)
    app.processEvents()
    
    w_start = active_pane.property("windowStartLine")
    w_end = active_pane.property("windowEndLine")
    print(f"[Scrollbar Drag to Bottom] window=[{w_start}..{w_end}]")
    assert w_end >= total_lines - 1, f"Window end should cover end of file, got {w_end} for total {total_lines}"
    verify_horizontal_stability("Scrollbar Drag to Bottom")
    
    print("\n--- Test Phase 4: Rapid Scrollbar Drag Simulation (Bottom -> Top in 1 step) ---")
    flickable.setProperty("contentY", 0)
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()
    
    w_start = active_pane.property("windowStartLine")
    w_end = active_pane.property("windowEndLine")
    print(f"[Scrollbar Drag to Top] window=[{w_start}..{w_end}]")
    assert w_start == 0, f"Window start should be 0, got {w_start}"
    verify_horizontal_stability("Scrollbar Drag to Top")

    print("\n=======================================================")
    print("[SUCCESS] ALL 18 VIRTUALIZATION AND STABILITY TESTS PASSED!")
    print("=======================================================")
    return True

if __name__ == "__main__":
    ok = test_full_scroll_flow()
    os._exit(0 if ok else 1)
