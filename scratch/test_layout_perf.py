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
py_10000 = "\n".join([f"def large_func_{i}():\n    # Test line {i}\n    return {i} * 42" for i in range(2500)])

print("\n--- TEST: 3,000 lines load + processEvents ---")
t0 = time.perf_counter()
editor.loadFile("test_3k.py", py_3000)
t_load = time.perf_counter()
QCoreApplication.processEvents()
t_proc = time.perf_counter()
print(f"3K loadFile: {(t_load - t0)*1000:.2f} ms | processEvents: {(t_proc - t_load)*1000:.2f} ms | Total: {(t_proc - t0)*1000:.2f} ms")

print("\n--- TEST: 10,000 lines load + processEvents ---")
t0 = time.perf_counter()
editor.loadFile("test_10k.py", py_10000)
t_load = time.perf_counter()
QCoreApplication.processEvents()
t_proc = time.perf_counter()
print(f"10K loadFile: {(t_load - t0)*1000:.2f} ms | processEvents: {(t_proc - t_load)*1000:.2f} ms | Total: {(t_proc - t0)*1000:.2f} ms")

sys.exit(0)
