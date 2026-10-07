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
py_10000 = "\n".join([f"def py_func_10k_{i}(a, b):\n    # line {i}\n    res = a + b * {i}\n    return res" for i in range(2500)])

print("="*70)
print("PROFILING CONTINUOUS SCROLLING ON 3,000-LINE FILE")
print("="*70)

editor.loadFile("scroll_test.py", py_3000)
QCoreApplication.processEvents()

flick = editor.findChild(QObject, "editorFlickable")

# Simulate 50 continuous wheel scroll events (scrolling down 3 lines per event)
frame_times = []
line_h = 18.0

for step in range(1, 51):
    target_y = step * line_h * 3.0 # scroll 3 lines
    t0 = time.perf_counter()
    if flick:
        flick.setProperty("contentY", target_y)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    dt_ms = (t1 - t0) * 1000
    frame_times.append(dt_ms)

avg_time = sum(frame_times) / len(frame_times)
max_time = max(frame_times)
stutters = [t for t in frame_times if t > 16.6] # frames taking longer than 60fps (16.6ms)

print(f"Continuous 50 Scroll Steps: Avg: {avg_time:.2f} ms | Max: {max_time:.2f} ms | Stutters (>16.6ms): {len(stutters)}/50")
print(f"Sample frame times (first 10): {[round(t, 2) for t in frame_times[:10]]}")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
