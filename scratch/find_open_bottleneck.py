import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, QTimer
from main import EditorBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)

comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root = comp.create()
editor = root.findChild(QObject, "editorArea")

py_10000 = "\n".join([f"def large_func_{i}():\n    # Test line {i}\n    return {i} * 42" for i in range(2500)])

print("\n--- TEST 1: Load file without register_text_area ---")
# Temporarily monkey-patch register_text_area
old_reg = backend.register_text_area
backend.register_text_area = lambda *args: None

t0 = time.perf_counter()
editor.loadFile("test1.py", py_10000)
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"Time WITHOUT register_text_area: {(t1 - t0)*1000:.2f} ms")

print("\n--- TEST 2: Load file WITH register_text_area ---")
backend.register_text_area = old_reg
t0 = time.perf_counter()
editor.loadFile("test2.py", py_10000)
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"Time WITH register_text_area: {(t1 - t0)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
