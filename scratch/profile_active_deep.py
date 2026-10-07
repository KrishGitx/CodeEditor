import sys, os, time, cProfile, pstats, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject
from main import EditorBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root_app = comp.create()
editor = root_app.findChild(QObject, "editorArea")

py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])

print("Loading 3000-line file...")
editor.loadFile("large_3k.py", py_3000)
QCoreApplication.processEvents()

ta = backend.qml_text_area
doc = backend.text_document
hl = backend.highlighter

print(f"Doc block count: {doc.blockCount() if doc else 'N/A'}")
print(f"Highlighter language: {hl.language if hl else 'N/A'}")
print(f"Highlighter formatted_blocks count: {len(hl.formatted_blocks) if hl else 'N/A'}")

# Test 1: Measure what happens when inserting a character
print("\n--- TEST 1: Breakdown of Single Char Insert (Typing) ---")
# Let's instrument/profile
pr = cProfile.Profile()
pr.enable()
t0 = time.perf_counter()
ta.insert(100, "x")
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
pr.disable()

print(f"ta.insert call time: {(t1 - t0)*1000:.2f} ms")
print(f"processEvents after insert: {(t2 - t1)*1000:.2f} ms")
print(f"Total single char insert: {(t2 - t0)*1000:.2f} ms")

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('tottime')
ps.print_stats(30)
print("\nPython Profiler Top 30 for Typing:")
print(s.getvalue()[:3000])

# Test 2: Highlighter rehighlightBlock vs highlightBlock
print("\n--- TEST 2: Highlighter block highlight timing ---")
if hl:
    b = doc.findBlockByNumber(10)
    t0 = time.perf_counter()
    for _ in range(100):
        hl.rehighlightBlock(b)
    t1 = time.perf_counter()
    print(f"100 x rehighlightBlock(10): {(t1 - t0)*1000:.2f} ms ({(t1 - t0)*10:.3f} us per block)")

# Test 3: What QML handlers run on text changed / cursor changed
print("\n--- TEST 3: QML Functions Timing ---")
# Measure computeScopesForText
t0 = time.perf_counter()
res = editor.computeScopesForText(py_3000)
t1 = time.perf_counter()
print(f"computeScopesForText (3k lines): {(t1 - t0)*1000:.2f} ms")

# Measure computeGuideSegmentsForText
t0 = time.perf_counter()
res = editor.computeGuideSegmentsForText(py_3000)
t1 = time.perf_counter()
print(f"computeGuideSegmentsForText (3k lines): {(t1 - t0)*1000:.2f} ms")

# Measure getCanonicalText
t0 = time.perf_counter()
res = editor.getCanonicalText()
t1 = time.perf_counter()
print(f"getCanonicalText (3k lines): {(t1 - t0)*1000:.2f} ms")

# Measure updateSelectionOccurrences
t0 = time.perf_counter()
editor.updateSelectionOccurrences()
t1 = time.perf_counter()
print(f"updateSelectionOccurrences: {(t1 - t0)*1000:.2f} ms")

# Measure Zoom
print("\n--- TEST 4: Zoom Timing ---")
pr_zoom = cProfile.Profile()
pr_zoom.enable()
t0 = time.perf_counter()
editor.setEditorZoom(15)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
pr_zoom.disable()
print(f"setEditorZoom call: {(t1 - t0)*1000:.2f} ms")
print(f"processEvents after zoom: {(t2 - t1)*1000:.2f} ms")
print(f"Total zoom: {(t2 - t0)*1000:.2f} ms")

s = io.StringIO()
ps = pstats.Stats(pr_zoom, stream=s).sort_stats('tottime')
ps.print_stats(20)
print("\nPython Profiler Top 20 for Zoom:")
print(s.getvalue()[:2000])

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
