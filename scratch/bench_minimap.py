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
engine.rootContext().setContextProperty('backend', backend)

comp = QQmlComponent(engine, os.path.abspath('qml/main.qml'))
if comp.isError():
    print('Errors:', [e.toString() for e in comp.errors()])
    sys.exit(1)

root = comp.create()
editor = root.findChild(QObject, 'editorArea')

# Generate 3,000-line Python file content
lines_3000 = "\n".join([f"def sample_function_{i}(arg1, arg2):\n    # Comment line\n    val = {i} * 100\n    return 'result_' + str(val)" for i in range(750)])
lines_10000 = "\n".join([f"def large_function_{i}(param_a, param_b):\n    # Minimap performance test line {i}\n    x = {i} + 42\n    if x > 100:\n        return 'output'\n    return None" for i in range(1667)])

print(f"Generated 3000 lines ({len(lines_3000)} chars), 10000 lines ({len(lines_10000)} chars)")

# Benchmark 3000 lines loadFile
t0 = time.perf_counter()
editor.loadFile("test_3000.py", lines_3000)
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"3000-line file load time: {(t1 - t0)*1000:.2f} ms")

# Benchmark 10000 lines loadFile
t0 = time.perf_counter()
editor.loadFile("test_10000.py", lines_10000)
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"10000-line file load time: {(t1 - t0)*1000:.2f} ms")

print("Initial dirty states:")
print("test_3000 dirty:", editor.isTabDirty(0))
print("test_10000 dirty:", editor.isTabDirty(1))

if backend.lsp_process:
    try:
        backend.lsp_process.terminate()
    except Exception:
        pass
sys.exit(0)
