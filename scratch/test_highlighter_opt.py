import sys, os, time, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QTextDocument, QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtCore import QRegularExpression

# Approach A: Current QRegularExpression.globalMatch
from HighlighterEngine import MultiLanguageHighlighter

# Approach B: Python re.finditer compiled regex with fast tuple matching
class FastReHighlighter(QSyntaxHighlighter):
    def __init__(self, parent_doc=None):
        super().__init__(parent_doc)
        kw = (
            r"\b(?:def|class|return|import|from|if|else|elif|while|for|try|except|finally|"
            r"with|as|pass|break|continue|yield|lambda|global|nonlocal|raise|assert|"
            r"async|await|None|True|False|is|in|not|and|or)\b"
        )
        pattern = (
            r"(#.*)|"
            r"(\"[^\"]*\"|'[^']*')|"
            rf"({kw})|"
            r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"
            r"(\b\d+(?:\.\d+)?\b)|"
            r"(\b(?:self|cls|int|str|float|list|dict|set|tuple|bool|bytes)\b)|"
            r"(@[A-Za-z0-9_]+)"
        )
        self.regex = re.compile(pattern)
        self.fmt_com = QTextCharFormat(); self.fmt_com.setForeground(QColor("#5c6478"))
        self.fmt_str = QTextCharFormat(); self.fmt_str.setForeground(QColor("#98c379"))
        self.fmt_kw = QTextCharFormat(); self.fmt_kw.setForeground(QColor("#c678dd"))
        self.fmt_fn = QTextCharFormat(); self.fmt_fn.setForeground(QColor("#61afef"))
        self.fmt_num = QTextCharFormat(); self.fmt_num.setForeground(QColor("#d19a66"))
        self.fmt_type = QTextCharFormat(); self.fmt_type.setForeground(QColor("#e5c07b"))
        self.fmt_prep = QTextCharFormat(); self.fmt_prep.setForeground(QColor("#e06c75"))
        self.fmts = [None, self.fmt_com, self.fmt_str, self.fmt_kw, self.fmt_fn, self.fmt_num, self.fmt_type, self.fmt_prep]

    def highlightBlock(self, text):
        if not text:
            return
        s = text.lstrip()
        if not s:
            return
        if s.startswith('#'):
            self.setFormat(len(text) - len(s), len(s), self.fmt_com)
            return

        set_fmt = self.setFormat
        fmts = self.fmts
        for m in self.regex.finditer(text):
            idx = m.lastindex
            if idx and fmts[idx]:
                start = m.start(idx)
                set_fmt(start, m.end(idx) - start, fmts[idx])

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
py_10000 = "\n".join([f"def large_func_{i}():\n    # Test line {i}\n    return {i} * 42" for i in range(2500)])

doc1 = QTextDocument()
doc1.setPlainText(py_10000)
t0 = time.perf_counter()
hl1 = MultiLanguageHighlighter(None)
hl1.setDocument(doc1)
t1 = time.perf_counter()
print(f"Current MultiLanguageHighlighter on 10,000 lines: {(t1 - t0)*1000:.2f} ms")

doc2 = QTextDocument()
doc2.setPlainText(py_10000)
t0 = time.perf_counter()
hl2 = FastReHighlighter(None)
hl2.setDocument(doc2)
t1 = time.perf_counter()
print(f"FastReHighlighter on 10,000 lines: {(t1 - t0)*1000:.2f} ms")
