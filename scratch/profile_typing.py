import sys, os, time, cProfile, pstats
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

py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])
editor.loadFile("large_3k.py", py_3000)
QCoreApplication.processEvents()

ta = backend.qml_text_area

print("\n--- Typing single char test ---")
# Warm up
t0 = time.perf_counter()
ta.insert(100, "a")
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"Char 1 insert latency: {(t1-t0)*1000:.2f} ms")

t0 = time.perf_counter()
ta.insert(101, "b")
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"Char 2 insert latency: {(t1-t0)*1000:.2f} ms")

t0 = time.perf_counter()
ta.insert(102, "c")
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"Char 3 insert latency: {(t1-t0)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
