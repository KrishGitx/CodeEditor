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
print("TEST 1: File Open WITHOUT Syntax Highlighter")
print("="*70)
orig_reg = backend.register_text_area
backend.register_text_area = lambda *args: None

t0 = time.perf_counter()
editor.loadFile("test_no_hl.py", py_3000)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"WITHOUT Highlighter: loadFile: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")

print("\n" + "="*70)
print("TEST 2: File Open WITH Syntax Highlighter")
print("="*70)
backend.register_text_area = orig_reg

t0 = time.perf_counter()
editor.loadFile("test_with_hl.py", py_3000)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"WITH Highlighter: loadFile: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")

print("\n" + "="*70)
print("TEST 3: Tab Switching Performance (Tab 0 <-> Tab 1)")
print("="*70)
for i in range(4):
    target_tab = i % 2
    t0 = time.perf_counter()
    editor.switchToTab(target_tab)
    t1 = time.perf_counter()
    QCoreApplication.processEvents()
    t2 = time.perf_counter()
    print(f"Switch to Tab {target_tab}: switchToTab: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
