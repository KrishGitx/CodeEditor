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
py_10000 = "\n".join([f"def py_func_10k_{i}(a, b):\n    # line {i}\n    res = a + b * {i}\n    return res" for i in range(2500)])

print("="*80)
print("DIAGNOSTIC BENCHMARK: ACTIVE & INACTIVE LARGE FILE ZOOM / OPERATIONS")
print("="*80)

# SCENARIO A: Only small files open
print("\n>>> SETUP SCENARIO A: Only small files open")
editor.loadFile("small1.py", py_small)
QCoreApplication.processEvents()
editor.loadFile("small2.py", py_small)
QCoreApplication.processEvents()

t0 = time.perf_counter()
editor.setEditorZoom(15)
QCoreApplication.processEvents()
t1 = time.perf_counter()
zoom_scen_a = (t1 - t0) * 1000
print(f"  [Scenario A] Zoom with 2 small files: {zoom_scen_a:.2f} ms")

# Reset zoom
editor.setEditorZoom(13)
QCoreApplication.processEvents()

# SCENARIO C (3k): 3,000-line file open but INACTIVE (small file active)
print("\n>>> SETUP SCENARIO C: 3,000-line file open but INACTIVE, small file active")
editor.loadFile("large_3k.py", py_3000)
QCoreApplication.processEvents()
# Switch back to small file (tab 0)
editor.switchToTab(0)
QCoreApplication.processEvents()

t0 = time.perf_counter()
editor.setEditorZoom(15)
QCoreApplication.processEvents()
t1 = time.perf_counter()
zoom_scen_c_3k = (t1 - t0) * 1000
print(f"  [Scenario C - 3k inactive] Zoom in small file: {zoom_scen_c_3k:.2f} ms (vs Scenario A {zoom_scen_a:.2f} ms)")

# Reset zoom
editor.setEditorZoom(13)
QCoreApplication.processEvents()

# SCENARIO C (10k): 10,000-line file open but INACTIVE
print("\n>>> SETUP SCENARIO C (10k): 10,000-line file open but INACTIVE, small file active")
editor.loadFile("large_10k.py", py_10000)
QCoreApplication.processEvents()
# Switch back to small file (tab 0)
editor.switchToTab(0)
QCoreApplication.processEvents()

t0 = time.perf_counter()
editor.setEditorZoom(15)
QCoreApplication.processEvents()
t1 = time.perf_counter()
zoom_scen_c_10k = (t1 - t0) * 1000
print(f"  [Scenario C - 10k inactive] Zoom in small file: {zoom_scen_c_10k:.2f} ms (vs Scenario A {zoom_scen_a:.2f} ms)")

# Reset zoom
editor.setEditorZoom(13)
QCoreApplication.processEvents()

# SCENARIO B: 3,000-line file is ACTIVE - Measure Operations
print("\n>>> SETUP SCENARIO B: 3,000-line file is ACTIVE")
editor.switchToTab(2) # tab with large_3k.py
QCoreApplication.processEvents()

# 1. Typing latency
ta = backend.qml_text_area
t0 = time.perf_counter()
ta.insert(100, "x")
QCoreApplication.processEvents()
t1 = time.perf_counter()
type_lat = (t1 - t0) * 1000
print(f"  [Scenario B] Typing latency (single char insert): {type_lat:.2f} ms")

# 2. Zoom in active 3k file
t0 = time.perf_counter()
editor.setEditorZoom(15)
QCoreApplication.processEvents()
t1 = time.perf_counter()
zoom_scen_b_3k = (t1 - t0) * 1000
print(f"  [Scenario B] Zoom in active 3k file: {zoom_scen_b_3k:.2f} ms")
editor.setEditorZoom(13)
QCoreApplication.processEvents()

# 3. Cursor movement
t0 = time.perf_counter()
ta.setProperty("cursorPosition", 1500)
QCoreApplication.processEvents()
t1 = time.perf_counter()
cursor_lat = (t1 - t0) * 1000
print(f"  [Scenario B] Cursor movement: {cursor_lat:.2f} ms")

# 4. Selection
t0 = time.perf_counter()
ta.select(1500, 1550)
QCoreApplication.processEvents()
t1 = time.perf_counter()
sel_lat = (t1 - t0) * 1000
print(f"  [Scenario B] Selection latency: {sel_lat:.2f} ms")

# 5. Find / Highlight occurrences
t0 = time.perf_counter()
editor.updateFindMatches("val", True)
QCoreApplication.processEvents()
t1 = time.perf_counter()
find_lat = (t1 - t0) * 1000
print(f"  [Scenario B] Find/Highlight 'val' occurrences: {find_lat:.2f} ms")

# 6. Scroll
flick = editor.findChild(QObject, "editorFlickable")
t0 = time.perf_counter()
if flick:
    flick.setProperty("contentY", 3000.0)
QCoreApplication.processEvents()
t1 = time.perf_counter()
scroll_lat = (t1 - t0) * 1000
print(f"  [Scenario B] Scroll latency: {scroll_lat:.2f} ms")

print("\n" + "="*80)
if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
