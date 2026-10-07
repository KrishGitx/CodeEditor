import sys, os, time
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

print("1. Calling loadFile...")
t0 = time.perf_counter()
editor.loadFile("test.py", py_3000)
t1 = time.perf_counter()
print(f"loadFile returned in: {(t1 - t0)*1000:.2f} ms")

print("\n2. Pumping processEvents in 50 iterations...")
for i in range(30):
    t_a = time.perf_counter()
    QCoreApplication.processEvents()
    t_b = time.perf_counter()
    dur = (t_b - t_a) * 1000
    if dur > 0.5:
        print(f"  Iter {i}: {dur:.2f} ms")
    time.sleep(0.005)

sys.exit(0)
