import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject
from main import EditorBackend
from HighlighterEngine import MultiLanguageHighlighter

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()

py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])
py_10000 = "\n".join([f"def py_func_10k_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(2500)])

# Test Viewport-Aware Highlighter
class ViewportAwareHighlighter(MultiLanguageHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.visible_start = 0
        self.visible_end = 150 # First 150 lines initially
        self.highlight_all = False

    def highlightBlock(self, text):
        if not text or not self.unified_regex or self.language in ("text", "binary", "plain"):
            self.setCurrentBlockState(0)
            return

        b_num = self.currentBlock().blockNumber()
        if not self.highlight_all and (b_num < self.visible_start or b_num > self.visible_end):
            self.setCurrentBlockState(0)
            return

        state = self.previousBlockState()
        if state <= 0: state = 0
        self._highlight_range(text, 0, len(text))
        self.setCurrentBlockState(0)

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

hl_vp = ViewportAwareHighlighter(None)
hl_vp._build_language_regex("python")

print("="*70)
print("TEST: Viewport-Aware Highlighter on 3,000 lines")
print("="*70)

t0 = time.perf_counter()
hl_vp.setDocument(text_doc)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"Viewport Highlighting (first 150 lines): setDocument: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")

print("="*70)
print("TEST: Viewport Scroll update (lines 200..350)")
print("="*70)
hl_vp.visible_start = 200
hl_vp.visible_end = 350
t0 = time.perf_counter()
hl_vp.rehighlight()
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"Viewport update on scroll: rehighlight: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
