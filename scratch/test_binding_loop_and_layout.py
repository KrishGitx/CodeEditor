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
doc = backend.text_document
pane = editor.property("activeEditorPane")
flick = pane.property("editorFlickable")

print("ta.width:", ta.property("width"), "contentWidth:", ta.property("contentWidth"))
print("flick.width:", flick.property("width"), "contentWidth:", flick.property("contentWidth"))
print("flick.height:", flick.property("height"), "contentHeight:", flick.property("contentHeight"))

# Let's test zoom time with current binding
t0 = time.perf_counter()
editor.setEditorZoom(15)
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"Zoom to 15: {(t1 - t0)*1000:.2f} ms")

editor.setEditorZoom(13)
QCoreApplication.processEvents()

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
