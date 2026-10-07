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
py_10000 = "\n".join([f"def func_10k_{i}(a, b):\n    # line {i}\n    res = a + b * {i}\n    return res" for i in range(2500)])

print("="*70)
print("ISOLATED JS FUNCTION TIMING TEST")
print("="*70)

# Test computeScopesForText
t0 = time.perf_counter()
scopes_3k = editor.computeScopesForText(py_3000)
t1 = time.perf_counter()
print(f"computeScopesForText (3,000 lines): {(t1-t0)*1000:.2f} ms")

t0 = time.perf_counter()
scopes_10k = editor.computeScopesForText(py_10000)
t1 = time.perf_counter()
print(f"computeScopesForText (10,000 lines): {(t1-t0)*1000:.2f} ms")

# Test computeGuideSegmentsForText
t0 = time.perf_counter()
guides_3k = editor.computeGuideSegmentsForText(py_3000)
t1 = time.perf_counter()
print(f"computeGuideSegmentsForText (3,000 lines): {(t1-t0)*1000:.2f} ms")

t0 = time.perf_counter()
guides_10k = editor.computeGuideSegmentsForText(py_10000)
t1 = time.perf_counter()
print(f"computeGuideSegmentsForText (10,000 lines): {(t1-t0)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
