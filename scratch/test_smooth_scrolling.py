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

class SmoothAsyncHighlighter(QSyntaxHighlighter):
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

        self.viewport_start = 0
        self.viewport_end = 120
        self.buffer_size = 60
        self.formatted_blocks = set()

        self._pending_blocks_queue = []
        self._slice_timer = QTimer()
        self._slice_timer.setInterval(12)
        self._slice_timer.timeout.connect(self._process_slice_queue)
        self._batch_slice_size = 30

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
        if lang == "python":
            kw = r"\b(def|class|return|if|else|elif|for|while|try|except|finally|with|as|import|from|in|is|not|and|or|lambda|yield|raise|pass|break|continue|async|await|global|nonlocal|assert|del)\b"
            pattern = (
                r"(#.*)|"
                r"(\"[^\"]*\"|'[^']*')|"
                rf"({kw})|"
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"
                r"(\b\d+(?:\.\d+)?\b)|"
                r"(\b(?:self|cls|int|str|float|list|dict|set|tuple|bool|bytes)\b)|"
                r"(@[A-Za-z0-9_]+)"
            )
            self.unified_regex = re.compile(pattern)

    def attach_document(self, doc, file_path="", explicit_lang=None, visible_lines=120):
        self.file_path = file_path or ""
        self.language = explicit_lang or "python"
        self._build_language_regex(self.language)

        self._slice_timer.stop()
        self._pending_blocks_queue.clear()
        self.formatted_blocks.clear()

        total_blocks = doc.blockCount() if doc else 0
        self.viewport_start = 0
        self.viewport_end = min(total_blocks, visible_lines + self.buffer_size)

        self.setDocument(doc)

    def update_visible_range(self, start_line, end_line):
        doc = self.document()
        if not doc or not self.unified_regex:
            return

        total_blocks = doc.blockCount()
        w_start = max(0, start_line - self.buffer_size)
        w_end = min(total_blocks - 1, end_line + self.buffer_size + 40) # Lookahead 40 lines

        self.viewport_start = w_start
        self.viewport_end = w_end

        # Find unformatted blocks
        new_blocks = [b for b in range(w_start, w_end + 1) if b not in self.formatted_blocks]
        if not new_blocks:
            return

        # Prioritize visible viewport first, then lookahead
        vp_blocks = [b for b in new_blocks if b >= start_line and b <= end_line]
        buf_blocks = [b for b in new_blocks if b < start_line or b > end_line]
        sorted_blocks = vp_blocks + buf_blocks

        # Append to queue avoiding duplicates
        existing_set = set(self._pending_blocks_queue)
        for b in sorted_blocks:
            if b not in existing_set:
                self._pending_blocks_queue.append(b)

        if not self._slice_timer.isActive():
            self._slice_timer.start()

    def _process_slice_queue(self):
        doc = self.document()
        if not doc or not self._pending_blocks_queue:
            self._slice_timer.stop()
            return

        # Process a small bounded chunk
        count = 0
        while self._pending_blocks_queue and count < self._batch_slice_size:
            b_num = self._pending_blocks_queue.pop(0)
            if b_num not in self.formatted_blocks:
                block = doc.findBlockByNumber(b_num)
                if block.isValid():
                    self.rehighlightBlock(block)
                count += 1

        if not self._pending_blocks_queue:
            self._slice_timer.stop()

    def highlightBlock(self, text):
        if not text or not self.unified_regex:
            self.setCurrentBlockState(STATE_NONE)
            return

        b_num = self.currentBlock().blockNumber()
        in_window = (b_num >= self.viewport_start and b_num <= self.viewport_end)

        state = self.previousBlockState()
        if state <= 0:
            state = STATE_NONE

        offset = 0
        rem_text = text[offset:]
        s_text = rem_text.lstrip()
        if s_text.startswith("#"):
            if in_window:
                self.setFormat(offset, len(rem_text), self.formats["comment"])
                self.formatted_blocks.add(b_num)
            self.setCurrentBlockState(STATE_NONE)
            return

        self.setCurrentBlockState(STATE_NONE)
        if in_window:
            sub_str = text[offset:]
            fmts = self.fmts_list
            set_fmt = self.setFormat
            for m in self.unified_regex.finditer(sub_str):
                idx = m.lastindex
                if idx and idx < len(fmts) and fmts[idx]:
                    s = offset + m.start(idx)
                    set_fmt(s, m.end(idx) - m.start(idx), fmts[idx])
            self.formatted_blocks.add(b_num)

py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])

class TestBackend(QObject):
    def __init__(self):
        super().__init__()
        self.hl = None

    @Slot(QObject, str, str)
    def register_ta(self, qml_ta, file_path, lang):
        qml_doc = qml_ta.property("textDocument")
        if qml_doc:
            doc = qml_doc.textDocument()
            self.hl = SmoothAsyncHighlighter(None)
            self.hl.attach_document(doc, file_path, lang, visible_lines=120)

    @Slot(int, int)
    def update_visible_range(self, s, e):
        if self.hl:
            self.hl.update_visible_range(s, e)

backend = TestBackend()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)

qml_code = f"""
import QtQuick 2.15
import QtQuick.Controls 2.15

Item {{
    width: 1000; height: 800
    Flickable {{
        id: flick
        objectName: "flick"
        anchors.fill: parent
        contentHeight: 3000 * 18
        
        Timer {{
            id: scrollIdleTimer
            interval: 100
            repeat: false
            onTriggered: {{
                var s = Math.floor(flick.contentY / 18);
                var e = s + Math.ceil(flick.height / 18);
                backend.update_visible_range(s, e);
            }}
        }}

        onContentYChanged: {{
            scrollIdleTimer.restart();
        }}

        TextArea.flickable: TextArea {{
            id: ta
            text: {repr(py_3000)}
            font.family: "Consolas"
            font.pixelSize: 13
            wrapMode: Text.NoWrap
            Component.onCompleted: {{
                backend.register_ta(ta, "sample.py", "python")
            }}
        }}
    }}
}}
"""

comp = QQmlComponent(engine)
comp.setData(qml_code.encode('utf-8'), "")
obj = comp.create()
flick = obj.findChild(QObject, "flick")
QCoreApplication.processEvents()

print("="*70)
print("TEST: Rapid Continuous Scrolling (100 scroll events in quick succession)")
print("="*70)

frame_times = []
for step in range(1, 101):
    target_y = step * 18 * 4 # 4 lines per wheel tick
    t0 = time.perf_counter()
    flick.setProperty("contentY", target_y)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    frame_times.append((t1 - t0) * 1000)

avg_time = sum(frame_times) / len(frame_times)
max_time = max(frame_times)
stutters = [t for t in frame_times if t > 16.6]

print(f"100 Continuous Scroll Events:")
print(f"  Average event time: {avg_time:.3f} ms")
print(f"  Maximum event time: {max_time:.3f} ms")
print(f"  Dropped frames (>16.6ms): {len(stutters)}/100")
print(f"  Formatted blocks so far: {len(backend.hl.formatted_blocks)}")

print("\nWaiting 150ms for idle highlighting queue...")
time.sleep(0.15)
t_idle0 = time.perf_counter()
QCoreApplication.processEvents()
t_idle1 = time.perf_counter()
print(f"Idle slice execution took: {(t_idle1 - t_idle0)*1000:.3f} ms")
print(f"Formatted blocks now: {len(backend.hl.formatted_blocks)}")

sys.exit(0)
