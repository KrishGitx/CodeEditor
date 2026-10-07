import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QTextDocument
from PySide6.QtCore import QCoreApplication

# Test attaching 10,000 lines with the new incremental logic
from HighlighterEngine import MultiLanguageHighlighter

app = QGuiApplication.instance() or QGuiApplication(sys.argv)

py_10000 = "\n".join([f"def sample_func_{i}(x, y):\n    # Line comment {i}\n    val = x * {i}\n    return val + y" for i in range(2500)])
doc = QTextDocument()
doc.setPlainText(py_10000)

hl = MultiLanguageHighlighter(None)

t0 = time.perf_counter()
hl.attach_document_incremental(doc, "test.py", "python")
t1 = time.perf_counter()
print(f"Initial attach_document_incremental took: {(t1 - t0)*1000:.2f} ms")

# Run event loop until background highlighting completes
ticks = 0
while hl._is_incremental_loading and ticks < 100:
    QCoreApplication.processEvents()
    time.sleep(0.01)
    ticks += 1

t2 = time.perf_counter()
print(f"Full background highlighting completed in {ticks} ticks (Total time: {(t2 - t0)*1000:.2f} ms)")
assert not hl._is_incremental_loading, "Incremental loading failed to finish"
print("SUCCESS!")
sys.exit(0)
