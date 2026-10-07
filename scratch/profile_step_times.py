import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QTextDocument
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject
from HighlighterEngine import MultiLanguageHighlighter

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root = comp.create()
editor = root.findChild(QObject, "editorArea")

py_3000 = "\n".join([f"def sample_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i}\n    return val + y" for i in range(750)])
py_10000 = "\n".join([f"def large_func_{i}():\n    # Test line {i}\n    return {i} * 42" for i in range(2500)])

print("\n================ 3,000 LINES ================")
t0 = time.perf_counter()
scopes_3k = editor.computeScopesForText(py_3000)
t1 = time.perf_counter()
print(f"1. computeScopesForText (3k lines): {(t1 - t0)*1000:.2f} ms")

t0 = time.perf_counter()
guides_3k = editor.computeGuideSegmentsForText(py_3000)
t1 = time.perf_counter()
print(f"2. computeGuideSegmentsForText (3k lines): {(t1 - t0)*1000:.2f} ms")

doc3k = QTextDocument()
doc3k.setPlainText(py_3000)
t0 = time.perf_counter()
hl3k = MultiLanguageHighlighter(None)
hl3k.set_language_for_file("test.py", "python", force_rehighlight=False)
hl3k.setDocument(doc3k)
t1 = time.perf_counter()
print(f"3. setDocument + highlightBlock (3k lines): {(t1 - t0)*1000:.2f} ms")

print("\n================ 10,000 LINES ================")
t0 = time.perf_counter()
scopes_10k = editor.computeScopesForText(py_10000)
t1 = time.perf_counter()
print(f"1. computeScopesForText (10k lines): {(t1 - t0)*1000:.2f} ms")

t0 = time.perf_counter()
guides_10k = editor.computeGuideSegmentsForText(py_10000)
t1 = time.perf_counter()
print(f"2. computeGuideSegmentsForText (10k lines): {(t1 - t0)*1000:.2f} ms")

doc10k = QTextDocument()
doc10k.setPlainText(py_10000)
t0 = time.perf_counter()
hl10k = MultiLanguageHighlighter(None)
hl10k.set_language_for_file("test.py", "python", force_rehighlight=False)
hl10k.setDocument(doc10k)
t1 = time.perf_counter()
print(f"3. setDocument + highlightBlock (10k lines): {(t1 - t0)*1000:.2f} ms")

sys.exit(0)
