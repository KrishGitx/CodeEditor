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
root = comp.create()
editor = root.findChild(QObject, "editorArea")

py_3000 = "\n".join([f"def sample_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i}\n    return val + y" for i in range(750)])

editor.loadFile("test.py", py_3000)

profiler = cProfile.Profile()
profiler.enable()

QCoreApplication.processEvents()

profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumtime')
print("\n--- TOP 30 PYTHON CUMULATIVE TIME CALLS IN Tick 0 ---")
stats.print_stats(30)

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
