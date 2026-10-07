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

py_small = "def foo():\n    print('hello world')\n    return 42\n"
py_10000 = "\n".join([f"def py_func_10k_{i}(a, b):\n    # line {i}\n    res = a + b * {i}\n    return res" for i in range(2500)])

editor.loadFile("small1.py", py_small)
QCoreApplication.processEvents()
editor.loadFile("large_10k.py", py_10000)
QCoreApplication.processEvents()
editor.switchToTab(0)
QCoreApplication.processEvents()

print("\nProfiling 1 zoom event in small tab with 10k inactive tab...")
pr = cProfile.Profile()
pr.enable()

t0 = time.perf_counter()
editor.setEditorZoom(15)
QCoreApplication.processEvents()
t1 = time.perf_counter()

pr.disable()
print(f"Total time: {(t1-t0)*1000:.2f} ms")
ps = pstats.Stats(pr).sort_stats('cumtime')
ps.print_stats(35)

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
