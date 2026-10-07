import sys, os, time, gc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import (
    QGuiApplication, QTextDocument, QTextCursor, QFont, QTextCharFormat,
    QColor, QTextBlock, QAbstractTextDocumentLayout
)
from PySide6.QtCore import QCoreApplication, QRectF, QSizeF

app = QGuiApplication.instance() or QGuiApplication(sys.argv)

def profile_qtextdocument_scale(line_count):
    print(f"\n{'='*70}\nPROFILING QTEXTDOCUMENT INTERNALS: {line_count} LINES\n{'='*70}")
    
    raw_lines = [f"def func_{i}(x, y, z):\n    val = x * {i} + y - z\n    return val" for i in range(line_count // 3)]
    content = "\n".join(raw_lines)
    
    # 1. Document Creation & Text Population
    t0 = time.perf_counter()
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    font = QFont("Consolas", 13)
    doc.setDefaultFont(font)
    
    # Measure setting plain text
    doc.setPlainText(content)
    t1 = time.perf_counter()
    
    block_count = doc.blockCount()
    layout = doc.documentLayout()
    
    print(f"1. Memory / Initialization:")
    print(f"   - Total characters: {len(content):,}")
    print(f"   - Total blocks:     {block_count:,}")
    print(f"   - doc.setPlainText: {(t1 - t0)*1000:.2f} ms")
    
    # 2. Document Layout Calculation
    t0 = time.perf_counter()
    # Force layout calculation of entire document
    doc.setTextWidth(800.0)
    doc_size = doc.size()
    t1 = time.perf_counter()
    print(f"2. Layout & Geometry:")
    print(f"   - Document height:  {doc_size.height():.1f} px")
    print(f"   - doc.setTextWidth: {(t1 - t0)*1000:.2f} ms")
    
    # 3. Block Bounding Rect Lookup Cost (e.g. scrolling / cursor tracking)
    t0 = time.perf_counter()
    for _ in range(1000):
        # Query random block rect
        blk = doc.findBlockByLineNumber(line_count // 2)
        r = layout.blockBoundingRect(blk)
    t1 = time.perf_counter()
    print(f"3. Block Rect Lookups (1,000 queries): {(t1 - t0)*1000:.2f} ms ({(t1-t0):.4f} ms/query)")
    
    # 4. Keystroke Insertion (inserting a single char in the middle)
    t0 = time.perf_counter()
    cursor = QTextCursor(doc)
    mid_pos = len(content) // 2
    cursor.setPosition(mid_pos)
    cursor.insertText("a")
    # Force layout refresh
    doc_size = doc.size()
    t1 = time.perf_counter()
    print(f"4. Keystroke insertText (middle of doc + layout sync): {(t1 - t0)*1000:.2f} ms")
    
    # 5. Keystroke at Beginning (Line 0) - tests propagation to subsequent blocks
    t0 = time.perf_counter()
    cursor.setPosition(0)
    cursor.insertText("x")
    doc_size = doc.size()
    t1 = time.perf_counter()
    print(f"5. Keystroke insertText (line 0 + layout sync): {(t1 - t0)*1000:.2f} ms")
    
    # 6. Font / Zoom Change (setDefaultFont forces full relayout)
    t0 = time.perf_counter()
    font_new = QFont("Consolas", 15)
    doc.setDefaultFont(font_new)
    doc_size = doc.size()
    t1 = time.perf_counter()
    print(f"6. Font / Zoom Change (full doc relayout): {(t1 - t0)*1000:.2f} ms")
    
    # 7. Selection across 500 lines
    t0 = time.perf_counter()
    cursor.setPosition(mid_pos)
    cursor.setPosition(mid_pos + 5000, QTextCursor.KeepAnchor)
    t1 = time.perf_counter()
    print(f"7. Selection Span (5,000 chars): {(t1 - t0)*1000:.3f} ms")
    
    # 8. Syntax Highlighting Formatting Overhead
    # Format 50 lines (one visible viewport)
    t0 = time.perf_counter()
    fmt = QTextCharFormat()
    fmt.setForeground(QColor("#569cd6"))
    cursor.beginEditBlock()
    start_blk = doc.findBlockByLineNumber(line_count // 2)
    curr_blk = start_blk
    for _ in range(50):
        if not curr_blk.isValid(): break
        cursor.setPosition(curr_blk.position())
        cursor.setPosition(curr_blk.position() + min(20, curr_blk.length() - 1), QTextCursor.KeepAnchor)
        cursor.setCharFormat(fmt)
        curr_blk = curr_blk.next()
    cursor.endEditBlock()
    t1 = time.perf_counter()
    print(f"8. Viewport Syntax Formatting (50 blocks via QTextCursor): {(t1 - t0)*1000:.2f} ms")

profile_qtextdocument_scale(3000)
profile_qtextdocument_scale(10000)
profile_qtextdocument_scale(50000)
