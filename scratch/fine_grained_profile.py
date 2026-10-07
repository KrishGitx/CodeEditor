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

print("="*70)
print("FINE-GRAINED BREAKDOWN OF 3000-LINE FILE OPEN")
print("="*70)

# Hook into backend.register_text_area
old_reg = backend.register_text_area
def timed_reg(*args):
    t0 = time.perf_counter()
    res = old_reg(*args)
    t1 = time.perf_counter()
    print(f"[TIMING] register_text_area call took: {(t1-t0)*1000:.2f} ms")
    return res
backend.register_text_area = timed_reg

t0 = time.perf_counter()
editor.loadFile("test_3000.py", py_3000)
t1 = time.perf_counter()
print(f"[TIMING] loadFile returned in: {(t1-t0)*1000:.2f} ms")

for i in range(1, 10):
    t_a = time.perf_counter()
    QCoreApplication.processEvents()
    t_b = time.perf_counter()
    ms = (t_b - t_a)*1000
    print(f"[TIMING] processEvents pass #{i}: {ms:.2f} ms")
    if ms < 0.5 and i >= 3:
        break

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
