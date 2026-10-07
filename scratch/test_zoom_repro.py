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
from main import EditorBackend, MusicPlayer, AIBackend, SettingsBackend, TerminalBackend

def test_zoom_reproduction():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    
    backend = EditorBackend()
    musicPlayer = MusicPlayer()
    aiBackend = AIBackend()
    terminalBackend = TerminalBackend()
    settingsBackend = SettingsBackend()
    backend.settings_backend = settingsBackend
    
    target_file = os.path.join(WORKSPACE_DIR, "qml", "components", "EditorArea.qml")
    with open(target_file, "r", encoding="utf-8") as f:
        file_text = f.read()
    total_lines = len(file_text.split("\n"))
    print(f"\n[Test] Target file: EditorArea.qml ({total_lines} lines)")
    
    tab_key = target_file
    backend.init_backing_document(tab_key, file_text)
    
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda warns: [print(w.toString()) for w in warns])
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("extensionManager", backend.extension_manager)
    engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
    engine.rootContext().setContextProperty("aiBackend", aiBackend)
    engine.rootContext().setContextProperty("terminalBackend", terminalBackend)
    engine.rootContext().setContextProperty("settingsBackend", settingsBackend)
    
    main_qml = os.path.join(WORKSPACE_DIR, "qml", "main.qml")
    engine.load(QUrl.fromLocalFile(main_qml))
    
    if not engine.rootObjects():
        print("[Error] Failed to load QML root object.")
        return False
        
    win = engine.rootObjects()[0]
    app.processEvents()
    
    backend.open_file(target_file)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)
    
    editor_area = win.findChild(QQuickItem, "editorArea")
    active_pane = editor_area.property("activeEditorPane")
    flickable = active_pane.findChild(QQuickItem, "editorFlickable")
    code_text_area = active_pane.findChild(QQuickItem, "codeTextArea")
    container = active_pane.findChild(QQuickItem, "materializedEditorContainer")
    
    # Check zoom at different lines
    test_lines = [1, 700, 2000, 3500, 5000]
    theme = win.property("theme")
    
    print("\n--- Testing Zoom across font sizes 8 to 40 at various lines ---")
    
    for start_line in test_lines:
        print(f"\n>>> Setting up at Line {start_line}...")
        editor_area.jumpToLine(start_line, 1)
        app.processEvents()
        
        # Test zoom in and out
        for new_font_size in [10, 12, 14, 16, 18, 20, 24, 28, 32, 20, 13]:
            # Set font size
            old_line_h = active_pane.property("paneLineHeight")
            old_content_y = flickable.property("contentY")
            old_w_start = active_pane.property("windowStartLine")
            old_w_end = active_pane.property("windowEndLine")
            
            editor_area.setEditorZoom(new_font_size)
            app.processEvents()
            time.sleep(0.02)
            app.processEvents()
            
            cur_line_h = active_pane.property("paneLineHeight")
            cur_content_y = flickable.property("contentY")
            cur_w_start = active_pane.property("windowStartLine")
            cur_w_end = active_pane.property("windowEndLine")
            
            # Check if viewport overlaps materializedEditorContainer
            view_top = cur_content_y
            view_bottom = cur_content_y + flickable.property("height")
            
            mat_top = cur_w_start * cur_line_h
            mat_bottom = (cur_w_end + 1) * cur_line_h
            
            overlap = not (view_bottom < mat_top or view_top > mat_bottom)
            
            print(f"Font {new_font_size:2d}px (lineH={cur_line_h:.1f}) | contentY={cur_content_y:.0f} (view=[{view_top/cur_line_h:.1f}..{view_bottom/cur_line_h:.1f}]) | matContainer=[{mat_top/cur_line_h:.1f}..{mat_bottom/cur_line_h:.1f}] | OVERLAP={overlap}")
            
            assert overlap, f"[BLANK DETECTED!] Viewport is outside materialized container! View=[{view_top}..{view_bottom}], Mat=[{mat_top}..{mat_bottom}]"

    print("\n=======================================================")
    print("[SUCCESS] ALL ZOOM TESTS PASSED: 0 BLANKS ACROSS ALL SCALES & LINES!")
    print("=======================================================")
    return True

if __name__ == "__main__":
    ok = test_zoom_reproduction()
    os._exit(0 if ok else 1)
