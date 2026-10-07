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

py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])

print("Loading 3000-line file...")
editor.loadFile("large_3k.py", py_3000)
QCoreApplication.processEvents()

ta = backend.qml_text_area

print("\n--- Simulating 10 consecutive keystrokes (with 50ms pause between keystrokes) ---")
for i in range(10):
    t0 = time.perf_counter()
    ta.insert(100 + i, "a")
    t1 = time.perf_counter()
    QCoreApplication.processEvents()
    t2 = time.perf_counter()
    time.sleep(0.05)
    QCoreApplication.processEvents()
    t3 = time.perf_counter()
    print(f"Keystroke {i}: insert={(t1-t0)*1000:.2f}ms | processEvents1={(t2-t1)*1000:.2f}ms | processEvents2 (after 50ms)={(t3-t2-50)*1000:.2f}ms | Total={(t3-t0-50)*1000:.2f}ms")

print("\n--- Now waiting 400ms for all debounce timers to trigger ---")
t0 = time.perf_counter()
time.sleep(0.4)
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"Debounce timers execution in processEvents: {(t1-t0-400)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
