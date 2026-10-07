import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, QTimer
from main import EditorBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()

py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])
py_10000 = "\n".join([f"def py_func_10k_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(2500)])

# Let's test a Viewport-Window Highlighter that rehighlights blocks in the visible window
class WindowedHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window_start = 0
        self.window_end = 200
        self.language = "python"
        from HighlighterEngine import THEMES
        self.theme = THEMES["obsidian"]
        self._init_formats()
        import re
        kw = r"\b(def|class|return|if|else|elif|for|while|try|except|finally|with|as|import|from|in|is|not|and|or|lambda|yield|raise|pass|break|continue|async|await|global|nonlocal|assert|del)\b"
        types = r"\b(int|str|float|list|dict|set|tuple|bool|bytes|self|cls)\b"
        pat = rf"(#.*)|(\"[^\"]*\"|'[^']*')|({kw})|(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|(\b\d+(?:\.\d+)?\b)|({types})|(@[A-Za-z0-9_]+)"
        self.regex = re.compile(pat)

    def _init_formats(self):
        from PySide6.QtGui import QTextCharFormat, QColor, QFont
        self.fmts = [
            None,
            self._make_fmt(self.theme["comments"], italic=True),
            self._make_fmt(self.theme["strings"]),
            self._make_fmt(self.theme["keywords"]),
            self._make_fmt(self.theme["functions"]),
            self._make_fmt(self.theme["numbers"]),
            self._make_fmt(self.theme["types"]),
            self._make_fmt(self.theme["preprocessor"])
        ]

    def _make_fmt(self, col, bold=False, italic=False):
        f = QTextCharFormat()
        f.setForeground(QColor(col))
        if italic: f.setFontItalic(True)
        return f

    def highlightBlock(self, text):
        if not text: return
        b_num = self.currentBlock().blockNumber()
        if b_num < self.window_start or b_num > self.window_end:
            return
        
        fmts = self.fmts
        set_fmt = self.setFormat
        for m in self.regex.finditer(text):
            idx = m.lastindex
            if idx and idx < len(fmts) and fmts[idx]:
                set_fmt(m.start(idx), m.end(idx) - m.start(idx), fmts[idx])

    def update_visible_range(self, start_line, end_line):
        buffer = 80
        new_start = max(0, start_line - buffer)
        new_end = end_line + buffer
        
        # If range changed significantly, rehighlight visible blocks
        if abs(new_start - self.window_start) > 20 or abs(new_end - self.window_end) > 20:
            self.window_start = new_start
            self.window_end = new_end
            doc = self.document()
            if doc:
                b = doc.findBlockByNumber(self.window_start)
                while b.isValid() and b.blockNumber() <= self.window_end:
                    self.rehighlightBlock(b)
                    b = b.next()

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

hl_win = WindowedHighlighter(None)

print("="*70)
print("TEST: Windowed Highlighter on 3,000 lines")
print("="*70)
t0 = time.perf_counter()
hl_win.setDocument(text_doc)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"Initial File Open & Render: setDocument: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")

print("\nTEST: Scroll to Line 500 (rehighlighting 100 visible blocks)")
t0 = time.perf_counter()
hl_win.update_visible_range(500, 560)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"Scroll Update: rehighlight: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")

print("\nTEST: Scroll to Line 1200 (rehighlighting 100 visible blocks)")
t0 = time.perf_counter()
hl_win.update_visible_range(1200, 1260)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"Scroll Update: rehighlight: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
