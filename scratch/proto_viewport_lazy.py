import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtQuick import QQuickTextDocument
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, QTimer, Slot
from HighlighterEngine import THEMES, EXT_TO_LANG, STATE_NONE, STATE_PY_TRIPLE_DOUBLE, STATE_PY_TRIPLE_SINGLE, STATE_C_BLOCK_COMMENT, STATE_HTML_COMMENT
import re

app = QGuiApplication.instance() or QGuiApplication(sys.argv)

class ViewportLazyHighlighter(QSyntaxHighlighter):
    def __init__(self, parent_document=None, theme_name="obsidian"):
        super().__init__(parent_document)
        self.theme_name = theme_name if theme_name in THEMES else "obsidian"
        self.current_theme = THEMES[self.theme_name]
        self.file_path = ""
        self.language = "python"
        self.formats = {}
        self.unified_regex = None
        self._init_formats()
        self._build_language_regex("python")

        # Viewport window tracking
        self.viewport_start = 0
        self.viewport_end = 120 # Initial visible window
        self.buffer_size = 60
        self.formatted_blocks = set() # Set of block indices that currently have formatting applied
        self.is_bulk_loading = False

    def _init_formats(self):
        self.formats.clear()
        def make_fmt(color_hex, bold=False, italic=False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color_hex))
            if bold: fmt.setFontWeight(QFont.Bold)
            if italic: fmt.setFontItalic(True)
            return fmt
        t = self.current_theme
        self.formats["keyword"] = make_fmt(t["keywords"], bold=False)
        self.formats["function"] = make_fmt(t["functions"])
        self.formats["string"] = make_fmt(t["strings"])
        self.formats["number"] = make_fmt(t["numbers"])
        self.formats["comment"] = make_fmt(t["comments"], italic=True)
        self.formats["type"] = make_fmt(t["types"])
        self.formats["operator"] = make_fmt(t["operators"])
        self.formats["preprocessor"] = make_fmt(t["preprocessor"])
        self.fmts_list = [
            None,
            self.formats["comment"],
            self.formats["string"],
            self.formats["keyword"],
            self.formats["function"],
            self.formats["number"],
            self.formats["type"],
            self.formats["preprocessor"]
        ]

    def _build_language_regex(self, lang):
        # 1. Python
        if lang == "python":
            kw = r"\b(def|class|return|if|else|elif|for|while|try|except|finally|with|as|import|from|in|is|not|and|or|lambda|yield|raise|pass|break|continue|async|await|global|nonlocal|assert|del)\b"
            pattern = (
                r"(#.*)|"                                        # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                rf"({kw})|"                                       # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+(?:\.\d+)?\b)|"                           # 5: number
                r"(\b(?:self|cls|int|str|float|list|dict|set|tuple|bool|bytes)\b)|" # 6: type
                r"(@[A-Za-z0-9_]+)"                              # 7: preprocessor/decorator
            )
            self.unified_regex = re.compile(pattern)
        elif lang in ("c", "cpp", "csharp", "java"):
            kw = r"\b(auto|break|case|char|const|continue|default|do|double|else|enum|extern|float|for|goto|if|inline|int|long|register|restrict|return|short|signed|sizeof|static|struct|switch|typedef|union|unsigned|void|volatile|while|class|namespace|using|public|private|protected|virtual|override|final|template|typename|try|catch|throw|new|delete|nullptr|true|false|this|friend|operator|constexpr|decltype|noexcept|static_assert)\b"
            types = r"\b(int8_t|int16_t|int32_t|int64_t|uint8_t|uint16_t|uint32_t|uint64_t|size_t|std|string|vector|map|unordered_map|set|unordered_set|pair|unique_ptr|shared_ptr|weak_ptr|bool|char16_t|char32_t|wchar_t)\b"
            pattern = (
                r"(//.*)|"                                        # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                rf"({kw})|"                                       # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+(?:\.\d+)?[fFlLuU]?\b)|"                  # 5: number
                rf"({types})|"                                    # 6: type
                r"(#[a-zA-Z_]\w*)"                                # 7: preprocessor
            )
            self.unified_regex = re.compile(pattern)
        elif lang in ("html", "xml"):
            pattern = (
                r"(<!--.*?-->)|"                                  # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                r"(</?[a-zA-Z0-9_-]+)|"                           # 3: tag (keyword)
                r"(\b[a-zA-Z0-9_-]+(?=\=))|"                      # 4: attribute (function)
                r"(\b\d+\b)|"                                     # 5: number
                r"(&[a-zA-Z0-9#]+;)|"                             # 6: entity
                r"(<!DOCTYPE.*?>)"                                # 7: doctype
            )
            self.unified_regex = re.compile(pattern)
        else:
            pattern = (
                r"((?:#|//).*)|"                                  # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                r"(\b(?:function|class|return|if|else|for|while)\b)|" # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+\b)"                                      # 5: number
            )
            self.unified_regex = re.compile(pattern)

    def attach_document(self, doc, file_path="", explicit_lang=None, visible_lines=120):
        self.file_path = file_path or ""
        ext = os.path.splitext(self.file_path)[1].lower() if self.file_path else ""
        new_lang = EXT_TO_LANG.get(ext, None)
        if not new_lang and explicit_lang:
            new_lang = explicit_lang.lower()
        if not new_lang:
            new_lang = "text"

        self.language = new_lang
        self._build_language_regex(new_lang)

        self.viewport_start = 0
        self.viewport_end = visible_lines
        self.formatted_blocks.clear()
        
        self.is_bulk_loading = True
        try:
            self.setDocument(doc)
        finally:
            self.is_bulk_loading = False

    def update_visible_range(self, start_line, end_line):
        doc = self.document()
        if not doc or self.language in ("text", "binary", "plain") or not self.unified_regex:
            return

        total_blocks = doc.blockCount()
        w_start = max(0, start_line - self.buffer_size)
        w_end = min(total_blocks - 1, end_line + self.buffer_size)

        self.viewport_start = w_start
        self.viewport_end = w_end

        # Check which blocks in the new viewport window need formatting
        blocks_to_format = []
        for b_num in range(w_start, w_end + 1):
            if b_num not in self.formatted_blocks:
                blocks_to_format.append(b_num)

        if not blocks_to_format:
            return

        # Rehighlight only unformatted blocks
        for b_num in blocks_to_format:
            block = doc.findBlockByNumber(b_num)
            if block.isValid():
                self.rehighlightBlock(block)

    def highlightBlock(self, text):
        if not text or not self.unified_regex or self.language in ("text", "binary", "plain"):
            self.setCurrentBlockState(STATE_NONE)
            return

        b_num = self.currentBlock().blockNumber()

        # Check if block is in active window OR if user is actively editing this block
        in_window = (b_num >= self.viewport_start and b_num <= self.viewport_end)

        # 1. State Tracking (Multiline docstrings / comments) - ALWAYS computed so state is preserved
        state = self.previousBlockState()
        if state <= 0:
            state = STATE_NONE

        offset = 0

        # Handle incoming multiline construct state from previous block
        if state == STATE_PY_TRIPLE_DOUBLE:
            end_idx = text.find('"""')
            if end_idx == -1:
                if in_window:
                    self.setFormat(0, len(text), self.formats["comment"])
                    self.formatted_blocks.add(b_num)
                self.setCurrentBlockState(STATE_PY_TRIPLE_DOUBLE)
                return
            else:
                if in_window:
                    self.setFormat(0, end_idx + 3, self.formats["comment"])
                offset = end_idx + 3
                state = STATE_NONE

        elif state == STATE_PY_TRIPLE_SINGLE:
            end_idx = text.find("'''")
            if end_idx == -1:
                if in_window:
                    self.setFormat(0, len(text), self.formats["comment"])
                    self.formatted_blocks.add(b_num)
                self.setCurrentBlockState(STATE_PY_TRIPLE_SINGLE)
                return
            else:
                if in_window:
                    self.setFormat(0, end_idx + 3, self.formats["comment"])
                offset = end_idx + 3
                state = STATE_NONE

        elif state == STATE_C_BLOCK_COMMENT:
            end_idx = text.find("*/")
            if end_idx == -1:
                if in_window:
                    self.setFormat(0, len(text), self.formats["comment"])
                    self.formatted_blocks.add(b_num)
                self.setCurrentBlockState(STATE_C_BLOCK_COMMENT)
                return
            else:
                if in_window:
                    self.setFormat(0, end_idx + 2, self.formats["comment"])
                offset = end_idx + 2
                state = STATE_NONE

        elif state == STATE_HTML_COMMENT:
            end_idx = text.find("-->")
            if end_idx == -1:
                if in_window:
                    self.setFormat(0, len(text), self.formats["comment"])
                    self.formatted_blocks.add(b_num)
                self.setCurrentBlockState(STATE_HTML_COMMENT)
                return
            else:
                if in_window:
                    self.setFormat(0, end_idx + 3, self.formats["comment"])
                offset = end_idx + 3
                state = STATE_NONE

        # Fast path for single line comments
        rem_text = text[offset:]
        s_text = rem_text.lstrip()
        is_comment = False
        if self.language in ("python", "bash", "powershell", "yaml", "toml") and s_text.startswith("#"):
            is_comment = True
        elif self.language in ("c", "cpp", "csharp", "java", "javascript", "typescript", "qml", "rust", "go", "css", "scss") and s_text.startswith("//"):
            is_comment = True
        elif self.language == "sql" and s_text.startswith("--"):
            is_comment = True

        if is_comment:
            if in_window:
                self.setFormat(offset, len(rem_text), self.formats["comment"])
                self.formatted_blocks.add(b_num)
            self.setCurrentBlockState(STATE_NONE)
            return

        # 2. Check for newly opened multiline construct in current line
        if self.language == "python":
            td_idx = rem_text.find('"""')
            ts_idx = rem_text.find("'''")
            if td_idx != -1 and (ts_idx == -1 or td_idx < ts_idx):
                close_idx = rem_text.find('"""', td_idx + 3)
                if close_idx == -1:
                    if in_window:
                        self._highlight_range(text, offset, offset + td_idx)
                        self.setFormat(offset + td_idx, len(rem_text) - td_idx, self.formats["comment"])
                        self.formatted_blocks.add(b_num)
                    self.setCurrentBlockState(STATE_PY_TRIPLE_DOUBLE)
                    return
            elif ts_idx != -1:
                close_idx = rem_text.find("'''", ts_idx + 3)
                if close_idx == -1:
                    if in_window:
                        self._highlight_range(text, offset, offset + ts_idx)
                        self.setFormat(offset + ts_idx, len(rem_text) - ts_idx, self.formats["comment"])
                        self.formatted_blocks.add(b_num)
                    self.setCurrentBlockState(STATE_PY_TRIPLE_SINGLE)
                    return

        elif self.language in ("c", "cpp", "csharp", "java", "javascript", "typescript", "qml", "rust", "go", "css", "scss"):
            c_idx = rem_text.find("/*")
            if c_idx != -1:
                close_idx = rem_text.find("*/", c_idx + 2)
                if close_idx == -1:
                    if in_window:
                        self._highlight_range(text, offset, offset + c_idx)
                        self.setFormat(offset + c_idx, len(rem_text) - c_idx, self.formats["comment"])
                        self.formatted_blocks.add(b_num)
                    self.setCurrentBlockState(STATE_C_BLOCK_COMMENT)
                    return

        elif self.language in ("html", "xml"):
            h_idx = rem_text.find("<!--")
            if h_idx != -1:
                close_idx = rem_text.find("-->", h_idx + 4)
                if close_idx == -1:
                    if in_window:
                        self._highlight_range(text, offset, offset + h_idx)
                        self.setFormat(offset + h_idx, len(rem_text) - h_idx, self.formats["comment"])
                        self.formatted_blocks.add(b_num)
                    self.setCurrentBlockState(STATE_HTML_COMMENT)
                    return

        self.setCurrentBlockState(STATE_NONE)
        if in_window:
            self._highlight_range(text, offset, len(text))
            self.formatted_blocks.add(b_num)

    def _highlight_range(self, full_text, start_pos, end_pos):
        if end_pos <= start_pos or not self.unified_regex:
            return
        sub_str = full_text[start_pos:end_pos]
        fmts = self.fmts_list
        set_fmt = self.setFormat
        for m in self.unified_regex.finditer(sub_str):
            idx = m.lastindex
            if idx and idx < len(fmts) and fmts[idx]:
                s = start_pos + m.start(idx)
                set_fmt(s, m.end(idx) - m.start(idx), fmts[idx])

# Generate 3,000 and 10,000 line sample files
py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])
py_10000 = "\n".join([f"def py_func_10k_{i}(a, b):\n    # line {i}\n    res = a + b * {i}\n    return res" for i in range(2500)])

class TestBackend(QObject):
    def __init__(self):
        super().__init__()
        self.hl = None

    @Slot(QObject, str, str)
    def register_ta(self, qml_ta, file_path, lang):
        qml_doc = qml_ta.property("textDocument")
        if qml_doc:
            doc = qml_doc.textDocument()
            self.hl = ViewportLazyHighlighter(None)
            self.hl.attach_document(doc, file_path, lang, visible_lines=120)

backend = TestBackend()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)

# Create QML TextArea
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
        Component.onCompleted: {{
            backend.register_ta(ta, "sample.py", "python")
        }}
    }}
}}
"""

print("="*70)
print("TEST: Viewport Lazy Highlighter on 3,000 lines")
print("="*70)
t0 = time.perf_counter()
comp = QQmlComponent(engine)
comp.setData(qml_code.encode('utf-8'), "")
obj = comp.create()
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"File Open & First Render: create: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")
print(f"Formatted blocks count: {len(backend.hl.formatted_blocks)} (expected ~121)")

print("\nTEST: Scroll to Line 500..550")
t0 = time.perf_counter()
backend.hl.update_visible_range(500, 550)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"Scroll to 500: update_range: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")
print(f"Formatted blocks count now: {len(backend.hl.formatted_blocks)}")

print("\nTEST: Scroll BACK to Line 500..550 (already formatted)")
t0 = time.perf_counter()
backend.hl.update_visible_range(500, 550)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"Scroll BACK (cache hit): update_range: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")

print("\nTEST: 10,000-line document")
qml_doc_10k = QQmlComponent(engine)
qml_doc_10k.setData(f"""
import QtQuick 2.15
import QtQuick.Controls 2.15
Item {{
    TextArea {{
        id: ta10k
        text: {repr(py_10000)}
        Component.onCompleted: {{
            backend.register_ta(ta10k, "sample_10k.py", "python")
        }}
    }}
}}
""".encode('utf-8'), "")
t0 = time.perf_counter()
obj_10k = qml_doc_10k.create()
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"10,000 lines File Open: create: {(t1-t0)*1000:.2f} ms | processEvents: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")
print(f"10,000 lines formatted blocks count: {len(backend.hl.formatted_blocks)}")

sys.exit(0)
