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

def run_regression_test():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    
    backend = EditorBackend()
    musicPlayer = MusicPlayer()
    aiBackend = AIBackend()
    settingsBackend = SettingsBackend()
    
    # Path to real EditorArea.qml (~5,250 lines)
    target_file = os.path.join(WORKSPACE_DIR, "qml", "components", "EditorArea.qml")
    with open(target_file, "r", encoding="utf-8") as f:
        file_text = f.read()
    total_lines = len(file_text.split("\n"))
    print(f"\n[Test] Target file: EditorArea.qml ({total_lines} lines, {len(file_text)} bytes)")
    
    # Register backing document
    tab_key = target_file
    backend.init_backing_document(tab_key, file_text)
    
    total_backing_lines = backend.get_backing_total_lines(tab_key)
    assert total_backing_lines == total_lines, f"Backing lines mismatch: {total_backing_lines} vs {total_lines}"
    print(f"[Test] BackingDocument registered successfully with {total_backing_lines} lines.")
    
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda warns: [print(w.toString()) for w in warns])
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
    
    # Open tab for EditorArea.qml via backend.open_file
    backend.open_file(target_file)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)
    
    editor_area = win.findChild(QQuickItem, "editorArea")
    assert editor_area is not None, "EditorArea not found!"
    
    active_pane = editor_area.property("activeEditorPane")
    assert active_pane is not None, "activeEditorPane is None!"
    
    is_virtualized = active_pane.property("isVirtualized")
    w_start = active_pane.property("windowStartLine")
    w_end = active_pane.property("windowEndLine")
    pane_lines = active_pane.property("paneTotalLineCount")
    
    print(f"[Test] Pane state: isVirtualized={is_virtualized}, windowStartLine={w_start}, windowEndLine={w_end}, paneTotalLineCount={pane_lines}")
    assert is_virtualized is True, "EditorArea.qml should be virtualized (>800 lines)"
    assert pane_lines == total_lines, f"paneTotalLineCount should be {total_lines}, got {pane_lines}"
    
    # Verify TextArea text block count is ~800, NOT 5000+
    doc = backend.text_document
    assert doc is not None, "backend.text_document is None!"
    block_count = doc.blockCount()
    print(f"[Test] Materialized QTextDocument blockCount = {block_count}")
    assert 700 <= block_count <= 850, f"Expected ~800 blocks, got {block_count}"
    
    # Test 1: Highlighting Speed & Synchronicity
    t0 = time.perf_counter()
    highlighter = backend.highlighter
    if highlighter:
        highlighter.rehighlight()
    hl_time_ms = (time.perf_counter() - t0) * 1000
    print(f"[Test] Rehighlight 800 blocks: {hl_time_ms:.2f} ms (Synchronous, zero async queue)")
    assert hl_time_ms < 200.0, f"Highlighting took too long: {hl_time_ms} ms"
    
    # Test 2: Jump to Line 1000, 3000, 5000, 150 via QuickOpenPalette lineSelected signal
    palette = editor_area.findChild(QQuickItem, "quickOpenPalette")
    assert palette is not None, "quickOpenPalette not found!"
    
    print(f"\n--- Testing Direct Jumps (Ctrl+G / QuickOpen / Minimap) ---")
    for jump_line in [1000, 3000, 5000, 150]:
        t0 = time.perf_counter()
        palette.lineSelected.emit(jump_line)
        app.processEvents()
        t_jump = (time.perf_counter() - t0) * 1000
        cur_w_start = active_pane.property("windowStartLine")
        cur_w_end = active_pane.property("windowEndLine")
        cursor_line = editor_area.property("cursorLine")
        print(f"[Test] jumpToLine({jump_line}) took {t_jump:.2f} ms -> window=[{cur_w_start}, {cur_w_end}], cursorLine={cursor_line}")
        assert cur_w_start <= jump_line <= cur_w_end + 1, f"jumpToLine({jump_line}) outside window [{cur_w_start}, {cur_w_end}]"
        assert cursor_line == jump_line, f"cursorLine should be {jump_line}, got {cursor_line}"
        assert t_jump < 200.0, f"Jump took {t_jump:.2f} ms, expected < 200ms"

    # Test 3: Search for symbol deep in file (line ~5050) via FindReplaceBar
    find_bar = win.findChild(QQuickItem, "findReplaceBar")
    assert find_bar is not None, "findReplaceBar not found!"
    
    print(f"\n--- Testing Search across unloaded regions ---")
    search_query = "function restoreWorkspaceSession"
    
    t0 = time.perf_counter()
    editor_area.findNext(search_query, True)
    app.processEvents()
    t_search = (time.perf_counter() - t0) * 1000
    cursor_line = editor_area.property("cursorLine")
    cur_w_start = active_pane.property("windowStartLine")
    cur_w_end = active_pane.property("windowEndLine")
    print(f"[Test] findNext('{search_query}') took {t_search:.2f} ms -> found at line {cursor_line}, window=[{cur_w_start}, {cur_w_end}]")
    assert cursor_line > 5200, f"function restoreWorkspaceSession expected around line ~5258, found at {cursor_line}"
    assert cur_w_start <= cursor_line <= cur_w_end + 1, "Search result must be within active window"
    assert t_search < 250.0, f"Search took {t_search:.2f} ms, expected < 250ms"

    # Test 4: Verify slice retrieval performance
    print(f"\n--- Testing BackingDocument slicing latency ---")
    t0 = time.perf_counter()
    slice_top = backend.get_backing_slice(tab_key, 0, 800)
    slice_mid = backend.get_backing_slice(tab_key, 2000, 2800)
    slice_bot = backend.get_backing_slice(tab_key, 4400, 5200)
    t_slices = (time.perf_counter() - t0) * 1000
    print(f"[Test] 3 slice extractions (800 lines each) took {t_slices:.3f} ms (avg {t_slices/3:.3f} ms/slice)")
    assert t_slices < 2.0, f"Slice extractions took too long: {t_slices} ms"

    print("\n[SUCCESS] ALL REAL-WORLD REGRESSION TESTS PASSED ON EditorArea.qml (5,260 lines)!")
    return True

if __name__ == "__main__":
    success = run_regression_test()
    os._exit(0 if success else 1)
