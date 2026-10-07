import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QTextCursor, QTextDocument
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
hl = backend.highlighter

print("=== VIEWPORT RENDERING & LAYOUT EXPERIMENT ===")
print(f"Total blocks in QTextDocument: {doc.blockCount()}")
print(f"Highlighter viewport range: {hl.viewport_start} .. {hl.viewport_end}")
print(f"Highlighter formatted blocks count: {len(hl.formatted_blocks)}")

# Let's test how many blocks are formatted during initial open vs scrolling
flick = editor.findChild(QObject, "editorFlickable")

# Scroll down to line 1500 (approx y = 27,000)
print("\n--- Scrolling down to line 1500 (y = 27,000) ---")
t0 = time.perf_counter()
if flick:
    flick.setProperty("contentY", 27000.0)
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"Scroll to 27000.0 + processEvents: {(t1 - t0)*1000:.2f} ms")
print(f"Formatted blocks count after scroll: {len(hl.formatted_blocks)}")

# Now type at line 1500
line_1500_pos = doc.findBlockByNumber(1500).position()
print(f"\n--- Typing at line 1500 (pos = {line_1500_pos}) ---")
t0 = time.perf_counter()
ta.insert(line_1500_pos, "x = 10\n")
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"Insert at line 1500: insert={(t1-t0)*1000:.2f}ms | processEvents={(t2-t1)*1000:.2f}ms | Total={(t2-t0)*1000:.2f}ms")
print(f"Formatted blocks count after edit at 1500: {len(hl.formatted_blocks)}")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
