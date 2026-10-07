import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QTextCursor
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

print("Loading 3000-line file...")
editor.loadFile("large_3k.py", py_3000)
QCoreApplication.processEvents()

ta = backend.qml_text_area
doc = backend.text_document

print("\n--- Measuring typing with different components isolated ---")

# Step 1: Direct QTextCursor edit on QTextDocument vs ta.insert
t0 = time.perf_counter()
cursor = QTextCursor(doc)
cursor.setPosition(100)
cursor.insertText("a")
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"Direct QTextCursor.insertText: {(t1 - t0)*1000:.2f} ms | processEvents: {(t2 - t1)*1000:.2f} ms | Total: {(t2 - t0)*1000:.2f} ms")

# Step 2: ta.insert
t0 = time.perf_counter()
ta.insert(100, "b")
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"ta.insert: {(t1 - t0)*1000:.2f} ms | processEvents: {(t2 - t1)*1000:.2f} ms | Total: {(t2 - t0)*1000:.2f} ms")

# Let's inspect what QML property changes fire
# Let's check paneTotalLineCount, gutter, minimap, etc.
if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
