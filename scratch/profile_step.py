import sys, os, time, cProfile, pstats
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root = comp.create()
editor = root.findChild(QObject, "editorArea")

py_3000 = "\n".join([f"def sample_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i}\n    return val + y" for i in range(750)])

editor.loadFile("test.py", py_3000)
QCoreApplication.processEvents() # initial

print("Profiling single processEvents call...")
profiler = cProfile.Profile()
profiler.enable()

for _ in range(5):
    t0 = time.perf_counter()
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"  processEvents call took: {(t1 - t0)*1000:.2f} ms")

profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumtime')
stats.print_stats(20)

sys.exit(0)
