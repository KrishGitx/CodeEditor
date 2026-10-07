import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject
from main import EditorBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root_app = comp.create()
editor = root_app.findChild(QObject, "editorArea")

py_small = "def foo():\n    print('hello world')\n    return 42\n"
py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])

def run_suite(label, filename, content):
    print(f"\n{'='*60}\nSUITE: {label} ({filename})\n{'='*60}")
    t0 = time.perf_counter()
    editor.loadFile(filename, content)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"Open / Load File: {(t1 - t0)*1000:.2f} ms")
    
    ta = backend.qml_text_area
    flick = editor.findChild(QObject, "editorFlickable")

    # 1. Typing latency (average over 5 keystrokes)
    type_times = []
    for k in range(5):
        t0 = time.perf_counter()
        ta.insert(50 + k, "x")
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        type_times.append((t1 - t0)*1000)
    print(f"Typing latency (avg of 5 edits): {sum(type_times)/len(type_times):.2f} ms (runs: {[round(x,1) for x in type_times]})")

    # 2. Cursor movement latency
    cursor_times = []
    positions = [10, 50, 100, 200, 500 if len(content) > 500 else 20]
    for pos in positions:
        t0 = time.perf_counter()
        ta.setProperty("cursorPosition", pos)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        cursor_times.append((t1 - t0)*1000)
    print(f"Cursor movement latency (avg of 5): {sum(cursor_times)/len(cursor_times):.2f} ms (runs: {[round(x,1) for x in cursor_times]})")

    # 3. Selection latency
    sel_times = []
    for pos in positions:
        t0 = time.perf_counter()
        ta.select(pos, min(pos + 30, len(content)))
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        sel_times.append((t1 - t0)*1000)
    print(f"Selection latency (avg of 5): {sum(sel_times)/len(sel_times):.2f} ms (runs: {[round(x,1) for x in sel_times]})")
    ta.deselect()
    QCoreApplication.processEvents()

    # 4. Scroll latency
    scroll_times = []
    for scroll_y in [100.0, 500.0, 1200.0, 2500.0 if len(content) > 1000 else 10.0, 0.0]:
        t0 = time.perf_counter()
        if flick:
            flick.setProperty("contentY", scroll_y)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        scroll_times.append((t1 - t0)*1000)
    print(f"Scroll latency (avg of 5): {sum(scroll_times)/len(scroll_times):.2f} ms (runs: {[round(x,1) for x in scroll_times]})")

    # 5. Zoom latency
    zoom_times = []
    for z in [14, 15, 16, 15, 13]:
        t0 = time.perf_counter()
        editor.setEditorZoom(z)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        zoom_times.append((t1 - t0)*1000)
    print(f"Zoom latency (avg of 5): {sum(zoom_times)/len(zoom_times):.2f} ms (runs: {[round(x,1) for x in zoom_times]})")

    # 6. Find / highlight occurrences
    find_times = []
    for term in ["val", "def", "func", "return", ""]:
        t0 = time.perf_counter()
        editor.updateFindMatches(term, True)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        find_times.append((t1 - t0)*1000)
    print(f"Find/Highlight latency (avg of 5): {sum(find_times)/len(find_times):.2f} ms (runs: {[round(x,1) for x in find_times]})")

run_suite("Small File (~4 lines)", "small.py", py_small)
run_suite("Large File (~3000 lines)", "large_3k.py", py_3000)

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
