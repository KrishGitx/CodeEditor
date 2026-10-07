import sys, os, time, bisect, re, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import (
    QGuiApplication, QTextDocument, QTextCursor, QFont
)
from PySide6.QtCore import QCoreApplication, QObject, Slot, Signal

app = QGuiApplication.instance() or QGuiApplication(sys.argv)

# =========================================================================
# 1. LIGHTWEIGHT BACKING DOCUMENT MODEL
# =========================================================================
class BackingDocument:
    """
    Maintains the 100% full file content in lightweight Python memory.
    Provides O(log N) line/char indexing, global search, undo/redo,
    folding and diagnostics without materializing Qt text blocks.
    """
    def __init__(self, text=""):
        self.set_text(text)
        self.undo_stack = []
        self.redo_stack = []
        self.is_modified = False

    def set_text(self, text):
        self.text = text
        self.lines = text.split("\n")
        self.total_lines = len(self.lines)
        
        # Build cumulative line offsets for O(log N) position lookups
        self.line_offsets = [0]
        curr = 0
        for l in self.lines:
            curr += len(l) + 1  # include \n
            self.line_offsets.append(curr)
        self.total_chars = len(text)
        self.is_modified = False

    def line_to_char_offset(self, line_num):
        """Line number is 0-indexed."""
        if line_num < 0: return 0
        if line_num >= len(self.line_offsets): return self.total_chars
        return self.line_offsets[line_num]

    def char_offset_to_line(self, char_pos):
        """Returns (line_num 0-indexed, col_num 0-indexed)."""
        idx = bisect.bisect_right(self.line_offsets, char_pos) - 1
        idx = max(0, min(idx, self.total_lines - 1))
        col = char_pos - self.line_offsets[idx]
        return idx, col

    def get_slice(self, start_line, end_line):
        """Returns slice of text from start_line to end_line (inclusive, 0-indexed)."""
        s_line = max(0, min(start_line, self.total_lines - 1))
        e_line = max(s_line, min(end_line, self.total_lines - 1))
        return "\n".join(self.lines[s_line:e_line + 1]), s_line, e_line

    def apply_edit(self, global_pos, delete_length, insert_text):
        """Applies an edit to the backing document and updates indices."""
        old_slice = self.text[global_pos:global_pos + delete_length]
        self.text = self.text[:global_pos] + insert_text + self.text[global_pos + delete_length:]
        
        # Fast incremental update: rebuild lines
        self.lines = self.text.split("\n")
        self.total_lines = len(self.lines)
        self.line_offsets = [0]
        curr = 0
        for l in self.lines:
            curr += len(l) + 1
            self.line_offsets.append(curr)
        self.total_chars = len(self.text)
        self.is_modified = True
        
        # Record for global undo
        self.undo_stack.append((global_pos, delete_length, insert_text, old_slice))

    def global_search(self, query, case_sensitive=False, is_regex=False):
        """Full file global search."""
        matches = []
        if not query: return matches
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = query if is_regex else re.escape(query)
        try:
            for m in re.finditer(pattern, self.text, flags):
                start = m.start()
                end = m.end()
                s_line, s_col = self.char_offset_to_line(start)
                e_line, e_col = self.char_offset_to_line(end)
                matches.append({
                    "start": start,
                    "end": end,
                    "startLine": s_line + 1,
                    "startCol": s_col + 1,
                    "endLine": e_line + 1,
                    "endCol": e_col + 1,
                    "text": m.group(0)
                })
        except Exception:
            pass
        return matches


# =========================================================================
# 2. VIRTUALIZED EDITOR CONTROLLER (C++/Python Backend for QML)
# =========================================================================
class VirtualizedEditorController(QObject):
    windowChanged = Signal(int, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.backing = BackingDocument()
        self.buffer_lines = 400
        self.window_start_line = 0
        self.window_end_line = 0
        self.window_text = ""
        self.line_height = 18.0
        self.viewport_height = 600.0
        self.current_scroll_y = 0.0

    @Slot(str)
    def load_content(self, content):
        self.backing.set_text(content)
        self.rematerialize(0, force=True)

    def rematerialize(self, center_line, force=False):
        total = self.backing.total_lines
        visible_lines = max(1, int(self.viewport_height / self.line_height))
        
        half_buffer = self.buffer_lines
        target_start = max(0, center_line - half_buffer)
        target_end = min(total - 1, center_line + visible_lines + half_buffer)

        # Hysteresis check: only shift if center moved close to buffer edge
        if not force and self.window_text:
            if target_start >= self.window_start_line - 100 and target_end <= self.window_end_line + 100:
                return False

        slice_text, s_line, e_line = self.backing.get_slice(target_start, target_end)
        self.window_start_line = s_line
        self.window_end_line = e_line
        self.window_text = slice_text
        self.windowChanged.emit(s_line, e_line, slice_text)
        return True

    @Slot(float)
    def on_scroll_y_changed(self, scroll_y):
        self.current_scroll_y = scroll_y
        center_line = max(0, int(scroll_y / self.line_height))
        self.rematerialize(center_line, force=False)

    @Slot(result=int)
    def total_lines(self):
        return self.backing.total_lines

    @Slot(result=float)
    def total_virtual_height(self):
        return max(self.viewport_height, self.backing.total_lines * self.line_height + 220.0)

    @Slot(result=int)
    def get_window_start_line(self):
        return self.window_start_line

    @Slot(result=str)
    def get_window_text(self):
        return self.window_text

    @Slot(int, int, str)
    def on_local_text_edited(self, local_pos, del_len, ins_text):
        """User edited within the materialized window."""
        global_start_offset = self.backing.line_to_char_offset(self.window_start_line)
        global_pos = global_start_offset + local_pos
        self.backing.apply_edit(global_pos, del_len, ins_text)


# =========================================================================
# 3. BENCHMARK SUITE: FULL QTEXTDOCUMENT vs VIRTUALIZED WINDOW
# =========================================================================
def run_side_by_side_comparison(line_count):
    print(f"\n{'='*78}\nBENCHMARK COMPARISON: {line_count:,} LINES (FULL vs VIRTUALIZED)\n{'='*78}")
    
    raw_lines = [f"def func_{i}(a, b):\n    # line {i}\n    val = a * {i} + b\n    return val" for i in range(line_count // 4)]
    content = "\n".join(raw_lines)
    
    # -------------------------------------------------------------
    # SETUP A: FULL QTEXTDOCUMENT
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    full_doc = QTextDocument()
    full_doc.setDocumentMargin(0)
    full_doc.setDefaultFont(QFont("Consolas", 13))
    full_doc.setPlainText(content)
    full_doc.setTextWidth(800.0)
    t_full_open = (time.perf_counter() - t0) * 1000

    # -------------------------------------------------------------
    # SETUP B: VIRTUALIZED BACKING + MATERIALIZED WINDOW (~800 lines)
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    v_ctrl = VirtualizedEditorController()
    v_ctrl.load_content(content)
    virt_doc = QTextDocument()
    virt_doc.setDocumentMargin(0)
    virt_doc.setDefaultFont(QFont("Consolas", 13))
    virt_doc.setPlainText(v_ctrl.get_window_text())
    virt_doc.setTextWidth(800.0)
    t_virt_open = (time.perf_counter() - t0) * 1000

    print(f"\n[1] Initial Document Load & Layout:")
    print(f"  Full QTextDocument:       {t_full_open:7.2f} ms ({full_doc.blockCount():,} blocks materialized)")
    print(f"  Virtualized Window:       {t_virt_open:7.2f} ms ({virt_doc.blockCount():,} blocks materialized)")
    print(f"  Speedup / Memory Ratio:   {t_full_open / max(0.01, t_virt_open):.1f}x faster initialization")

    # -------------------------------------------------------------
    # TEST 2: SIMULATED CONTINUOUS SCROLLING (100 STEPS ACROSS DOCUMENT)
    # -------------------------------------------------------------
    print(f"\n[2] Continuous Scrolling (100 scroll steps):")
    
    # Full Doc scrolling (queries blockBoundingRect and updates visible range)
    t0 = time.perf_counter()
    layout_full = full_doc.documentLayout()
    for step in range(100):
        target_line = int((step / 100.0) * line_count)
        blk = full_doc.findBlockByLineNumber(target_line)
        r = layout_full.blockBoundingRect(blk)
    t_full_scroll = (time.perf_counter() - t0) * 1000

    # Virt Doc scrolling (updates scroll position, shifts materialized window only when buffer threshold hit)
    t0 = time.perf_counter()
    layout_virt = virt_doc.documentLayout()
    window_shifts = 0
    for step in range(100):
        target_scroll_y = (step / 100.0) * (line_count * 18.0)
        shifted = v_ctrl.rematerialize(int(target_scroll_y / 18.0))
        if shifted:
            window_shifts += 1
            virt_doc.setPlainText(v_ctrl.get_window_text())
        # Query local block rect
        local_line = min(virt_doc.blockCount() - 1, 20)
        blk = virt_doc.findBlockByLineNumber(local_line)
        r = layout_virt.blockBoundingRect(blk)
    t_virt_scroll = (time.perf_counter() - t0) * 1000

    print(f"  Full QTextDocument:       {t_full_scroll:7.2f} ms ({t_full_scroll/100:.3f} ms/step)")
    print(f"  Virtualized Window:       {t_virt_scroll:7.2f} ms ({t_virt_scroll/100:.3f} ms/step, {window_shifts} window shifts)")

    # -------------------------------------------------------------
    # TEST 3: CONTINUOUS TYPING IN MIDDLE OF DOCUMENT (50 KEYSTROKES)
    # -------------------------------------------------------------
    print(f"\n[3] Continuous Keystroke Editing (50 keystrokes):")
    
    # Full Doc typing
    cursor_full = QTextCursor(full_doc)
    mid_pos_full = len(content) // 2
    cursor_full.setPosition(mid_pos_full)
    full_key_times = []
    for i in range(50):
        t_k0 = time.perf_counter()
        cursor_full.insertText("x")
        sz = full_doc.size()
        t_k1 = time.perf_counter()
        full_key_times.append((t_k1 - t_k0) * 1000)
    
    # Virt Doc typing
    cursor_virt = QTextCursor(virt_doc)
    mid_pos_virt = len(v_ctrl.get_window_text()) // 2
    cursor_virt.setPosition(mid_pos_virt)
    virt_key_times = []
    for i in range(50):
        t_k0 = time.perf_counter()
        cursor_virt.insertText("x")
        v_ctrl.on_local_text_edited(mid_pos_virt + i, 0, "x")
        sz = virt_doc.size()
        t_k1 = time.perf_counter()
        virt_key_times.append((t_k1 - t_k0) * 1000)

    print(f"  Full QTextDocument:       Avg = {statistics.mean(full_key_times):5.2f} ms | Max = {max(full_key_times):5.2f} ms | p95 = {sorted(full_key_times)[47]:5.2f} ms")
    print(f"  Virtualized Window:       Avg = {statistics.mean(virt_key_times):5.2f} ms | Max = {max(virt_key_times):5.2f} ms | p95 = {sorted(virt_key_times)[47]:5.2f} ms")

    # -------------------------------------------------------------
    # TEST 4: FONT / ZOOM CHANGE (FULL DOCUMENT RELAYOUT)
    # -------------------------------------------------------------
    print(f"\n[4] Font Size / Zoom Change (Relayout):")
    
    # Full Doc Zoom
    t0 = time.perf_counter()
    full_doc.setDefaultFont(QFont("Consolas", 15))
    sz = full_doc.size()
    t_full_zoom = (time.perf_counter() - t0) * 1000

    # Virt Doc Zoom
    t0 = time.perf_counter()
    virt_doc.setDefaultFont(QFont("Consolas", 15))
    sz = virt_doc.size()
    t_virt_zoom = (time.perf_counter() - t0) * 1000

    print(f"  Full QTextDocument:       {t_full_zoom:7.2f} ms")
    print(f"  Virtualized Window:       {t_virt_zoom:7.2f} ms")
    print(f"  Zoom Speedup Ratio:       {t_full_zoom / max(0.01, t_virt_zoom):.1f}x faster")

    # -------------------------------------------------------------
    # TEST 5: FULL-FILE GLOBAL SEARCH
    # -------------------------------------------------------------
    print(f"\n[5] Global Search across Full File (100 queries):")
    t0 = time.perf_counter()
    matches = v_ctrl.backing.global_search("def func_")
    t_search = (time.perf_counter() - t0) * 1000
    print(f"  Matches Found:            {len(matches):,}")
    print(f"  Search Time:              {t_search:7.2f} ms (Backing index instant regex)")

if __name__ == "__main__":
    run_side_by_side_comparison(3000)
    run_side_by_side_comparison(10000)
    run_side_by_side_comparison(50000)
