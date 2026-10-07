import sys, os, time, cProfile, pstats, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QTextCursor
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

py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])

editor.loadFile("large_3k.py", py_3000)
QCoreApplication.processEvents()

ta = backend.qml_text_area
doc = backend.text_document

print("\n--- DETAILED BREAKDOWN OF ZOOM ON 3,000-LINE FILE ---")

# Let's isolate what happens when font size changes:
# 1. Direct QFont on QTextDocument vs QML property changes
pr = cProfile.Profile()
pr.enable()

t0 = time.perf_counter()
editor.setEditorZoom(16)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()

pr.disable()

print(f"1. setEditorZoom JS call: {(t1 - t0)*1000:.2f} ms")
print(f"2. processEvents (layout/rendering/bindings): {(t2 - t1)*1000:.2f} ms")
print(f"3. Total Zoom time: {(t2 - t0)*1000:.2f} ms")

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('tottime')
ps.print_stats(30)
print("\nPython Profiler Top 30 during Zoom:")
print(s.getvalue()[:3000])

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
