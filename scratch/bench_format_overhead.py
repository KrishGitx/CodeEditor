import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject
from main import EditorBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()

py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])

# Create bare QML TextArea
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
qml_code = f"""
import QtQuick 2.15
import QtQuick.Controls 2.15

Item {{
    width: 1000; height: 800
    TextArea {{
        id: ta
        objectName: "testTextArea"
        text: {repr(py_3000)}
        font.family: "Consolas"
        font.pixelSize: 13
        wrapMode: Text.NoWrap
    }}
}}
"""
comp = QQmlComponent(engine)
comp.setData(qml_code.encode('utf-8'), "")
obj = comp.create()
ta = obj.findChild(QObject, "testTextArea")
qml_doc = ta.property("textDocument")
text_doc = qml_doc.textDocument()

# Process events to let TextArea settle first
t0 = time.perf_counter()
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"Bare TextArea initial render: {(t1-t0)*1000:.2f} ms")

# Test Highlighter 1: Empty highlightBlock (no setFormat)
class EmptyHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        pass

hl_empty = EmptyHighlighter(None)
t0 = time.perf_counter()
hl_empty.setDocument(text_doc)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"EmptyHighlighter: setDocument: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms")

# Test Highlighter 2: Dummy setFormat on every block
class DummyFormatHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fmt = QTextCharFormat()
        self.fmt.setForeground(QColor("#61afef"))
    def highlightBlock(self, text):
        self.setFormat(0, min(10, len(text)), self.fmt)

hl_dummy = DummyFormatHighlighter(None)
t0 = time.perf_counter()
hl_dummy.setDocument(text_doc)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"DummyFormatHighlighter (1 format per line): setDocument: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms")

# Test Highlighter 3: Real MultiLanguageHighlighter
from HighlighterEngine import MultiLanguageHighlighter
hl_real = MultiLanguageHighlighter(None)
hl_real._build_language_regex("python")
t0 = time.perf_counter()
hl_real.setDocument(text_doc)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"MultiLanguageHighlighter (Real): setDocument: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
