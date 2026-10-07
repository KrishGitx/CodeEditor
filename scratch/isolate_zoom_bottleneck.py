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

editor.loadFile("large_3k.py", py_3000)
QCoreApplication.processEvents()

ta = backend.qml_text_area
pane = editor.property("activeEditorPane")
theme = root_app.property("theme")

print("\n--- ISOLATING INDIVIDUAL PROPERTY ASSIGNMENTS ---")

# Step 1: Change font on codeTextArea directly
t0 = time.perf_counter()
ta.setProperty("font.pixelSize", 16)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"ta.font.pixelSize = 16: set={(t1-t0)*1000:.2f}ms | processEvents={(t2-t1)*1000:.2f}ms | Total={(t2-t0)*1000:.2f}ms")

# Step 2: Change fontMetrics directly
fm = editor.findChild(QObject, "fontMetrics")
if fm:
    t0 = time.perf_counter()
    fm.setProperty("font.pixelSize", 16)
    t1 = time.perf_counter()
    QCoreApplication.processEvents()
    t2 = time.perf_counter()
    print(f"fontMetrics.font.pixelSize = 16: set={(t1-t0)*1000:.2f}ms | processEvents={(t2-t1)*1000:.2f}ms | Total={(t2-t0)*1000:.2f}ms")

# Step 3: Change cachedIndentLevelWidths
t0 = time.perf_counter()
cached = editor.property("cachedIndentLevelWidths")
t1 = time.perf_counter()
print(f"Reading cachedIndentLevelWidths: {(t1-t0)*1000:.2f}ms")

# Step 4: Change paneFontSize
if pane:
    t0 = time.perf_counter()
    pane.setProperty("paneFontSize", 16)
    t1 = time.perf_counter()
    QCoreApplication.processEvents()
    t2 = time.perf_counter()
    print(f"pane.paneFontSize = 16: set={(t1-t0)*1000:.2f}ms | processEvents={(t2-t1)*1000:.2f}ms | Total={(t2-t0)*1000:.2f}ms")

# Step 5: Change theme.editorFontSize
t0 = time.perf_counter()
theme.setProperty("editorFontSize", 16)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"theme.editorFontSize = 16: set={(t1-t0)*1000:.2f}ms | processEvents={(t2-t1)*1000:.2f}ms | Total={(t2-t0)*1000:.2f}ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
