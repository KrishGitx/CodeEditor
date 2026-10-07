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

def test_polish_features():
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
    print(f"\n=======================================================")
    print(f"[Test] Starting Virtualization Polish Verification ({total_lines} lines)")
    print(f"=======================================================")
    
    backend.init_backing_document(target_file, file_text)
    
    engine = QQmlApplicationEngine()
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
    for _ in range(8):
        app.processEvents()
        time.sleep(0.02)
    
    editor_area = win.findChild(QQuickItem, "editorArea")
    active_pane = editor_area.property("activeEditorPane")
    assert active_pane is not None, "activeEditorPane is None!"
    
    flickable = active_pane.findChild(QQuickItem, "editorFlickable")
    code_text_area = active_pane.findChild(QQuickItem, "codeTextArea")
    indent_canvas = active_pane.findChild(QQuickItem, "indentGuidesCanvas")
    code_minimap = editor_area.findChild(QQuickItem, "codeMinimap")
    
    line_h = active_pane.property("paneLineHeight") or 18.0
    
    # --- TEST 1: MINIMAP GLOBAL COORDINATES & JITTER IMMUNITY ---
    print("\n--- Test 1: Minimap Global Representation & Scroll Stability ---")
    minimap_lines = code_minimap.property("totalLineCount") if code_minimap else 0
    print(f"[Minimap] Initial totalLineCount={minimap_lines} (Expected {total_lines})")
    assert minimap_lines == total_lines, f"Minimap totalLineCount mismatch: {minimap_lines} vs {total_lines}"
    
    # Verify minimap scrollRatio matches flickable contentY continuously
    waypoints = [500, 1500, 3000, 4500, 5200]
    for wl in waypoints:
        target_y = (wl - 1) * line_h
        flickable.setProperty("contentY", target_y)
        app.processEvents()
        time.sleep(0.04) # Allow debounce
        
        m_lines = code_minimap.property("totalLineCount")
        m_scroll_ratio = code_minimap.property("scrollRatio")
        expected_ratio = target_y / max(1, flickable.property("contentHeight") - flickable.property("height"))
        
        print(f"-> Scrolled to Line {wl:4d} | Minimap totalLines={m_lines} | scrollRatio={m_scroll_ratio:.4f} (Expected {expected_ratio:.4f})")
        assert m_lines == total_lines, f"Minimap lines collapsed to {m_lines} during scroll to line {wl}!"
        assert abs(m_scroll_ratio - expected_ratio) < 0.01, f"Minimap scrollRatio deviated: {m_scroll_ratio} vs {expected_ratio}"
    
    # --- TEST 2: INDENTATION GUIDES ACTIVE & ACCURATE ACROSS UNMATERIALIZED WINDOWS ---
    print("\n--- Test 2: Indentation Guides Rendering Beyond Line 801 ---")
    for test_line in [500, 1200, 2500, 3500, 5000]:
        editor_area.jumpToLine(test_line, 1)
        app.processEvents()
        
        w_start = active_pane.property("windowStartLine")
        w_end = active_pane.property("windowEndLine")
        segments_raw = active_pane.property("paneGuideSegments")
        segments = segments_raw.toVariant() if hasattr(segments_raw, "toVariant") else segments_raw
        seg_count = len(segments) if isinstance(segments, (list, tuple)) else (segments.property("length") if hasattr(segments, "property") else 0)
        
        print(f"-> At Line {test_line:4d} | Active Window=[{w_start:4d}..{w_end:4d}] | Segments Calculated={seg_count}")
        assert w_start <= test_line <= w_end + 1, f"Line {test_line} not in window [{w_start}..{w_end}]"
        assert seg_count > 0, f"No guide segments calculated for window [{w_start}..{w_end}] at line {test_line}!"
        
        # Verify segment lines are valid local lines 0..800
        first_seg = segments[0] if isinstance(segments, list) else {}
        assert "startLine" in first_seg and "endLine" in first_seg and "level" in first_seg
        assert 0 <= first_seg["startLine"] <= 850
    
    # --- TEST 3: NO EMPTY EDITOR DURING SCROLLBAR DRAG & RELEASE ---
    print("\n--- Test 3: Instant & Continuous Code Materialization on Large Scrollbar Drag ---")
    # Simulate grabbing scrollbar at top and releasing at bottom
    t0 = time.perf_counter()
    flickable.setProperty("contentY", (total_lines - 30) * line_h)
    active_pane.checkAndShiftWindow(True, "scrollbar_release")
    app.processEvents()
    t_shift = (time.perf_counter() - t0) * 1000
    
    w_start = active_pane.property("windowStartLine")
    w_end = active_pane.property("windowEndLine")
    text_len = len(code_text_area.property("text"))
    
    print(f"-> Scrollbar direct jump to bottom took {t_shift:.2f} ms | Window=[{w_start}..{w_end}] | Materialized Chars={text_len}")
    assert text_len > 1000, "Editor was left empty after scrollbar release!"
    assert w_end >= total_lines - 1, f"Expected window end to cover file end {total_lines}, got {w_end}"
    assert t_shift < 150.0, f"Transition took too long: {t_shift:.2f} ms"
    
    # Jump back to top
    t0 = time.perf_counter()
    flickable.setProperty("contentY", 0)
    active_pane.checkAndShiftWindow(True, "scrollbar_release")
    app.processEvents()
    t_shift_top = (time.perf_counter() - t0) * 1000
    
    w_start = active_pane.property("windowStartLine")
    w_end = active_pane.property("windowEndLine")
    text_len = len(code_text_area.property("text"))
    print(f"-> Scrollbar direct jump to top took {t_shift_top:.2f} ms | Window=[{w_start}..{w_end}] | Materialized Chars={text_len}")
    assert text_len > 1000, "Editor was left empty after jump to top!"
    assert w_start == 0, f"Expected window start 0, got {w_start}"
    
    print("\n=======================================================")
    print("[SUCCESS] ALL POLISH TESTS (MINIMAP, GUIDES, ZERO-BLANK) PASSED!")
    print("=======================================================")
    return True

if __name__ == "__main__":
    ok = test_polish_features()
    os._exit(0 if ok else 1)
