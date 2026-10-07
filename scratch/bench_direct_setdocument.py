import sys, os, time, cProfile, pstats, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QTextDocument
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject
from main import EditorBackend
from HighlighterEngine import MultiLanguageHighlighter

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)

comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root = comp.create()
editor = root.findChild(QObject, "editorArea")

lines_3000 = []
for i in range(750):
    lines_3000.append(f"def test_function_{i}(param_a, param_b):")
    lines_3000.append(f'    """Docstring for function {i} explaining operations."""')
    lines_3000.append(f"    result = param_a * {i} + len(str(param_b))")
    lines_3000.append(f"    return result")
py_3000 = "\n".join(lines_3000)

lines_10000 = []
for i in range(2500):
    lines_10000.append(f"def test_func_10k_{i}(param_a, param_b):")
    lines_10000.append(f'    """Docstring for function {i} explaining operations."""')
    lines_10000.append(f"    result = param_a * {i} + len(str(param_b))")
    lines_10000.append(f"    return result")
py_10000 = "\n".join(lines_10000)

# 1. Benchmark raw highlighter setDocument on raw QTextDocument
print("="*70)
print("TEST A: Raw QTextDocument + MultiLanguageHighlighter.setDocument")
print("="*70)
doc_raw = QTextDocument()
doc_raw.setPlainText(py_3000)

hl_raw = MultiLanguageHighlighter(None)
hl_raw._build_language_regex("python")
hl_raw._is_incremental_loading = False

t0 = time.perf_counter()
hl_raw.setDocument(doc_raw)
t1 = time.perf_counter()
print(f"setDocument on 3,000 lines (raw QTextDocument): {(t1 - t0)*1000:.2f} ms")

doc_raw_10k = QTextDocument()
doc_raw_10k.setPlainText(py_10000)
t0 = time.perf_counter()
hl_raw.setDocument(doc_raw_10k)
t1 = time.perf_counter()
print(f"setDocument on 10,000 lines (raw QTextDocument): {(t1 - t0)*1000:.2f} ms")

# 2. Benchmark inside QML EditorArea with direct setDocument (no chunk loop)
print("\n" + "="*70)
print("TEST B: QML EditorArea loadFile with standard setDocument (no chunk timer)")
print("="*70)

# Modify attach_document to just do setDocument once
def direct_attach(hl_inst, doc, file_path="", explicit_lang=None):
    hl_inst.file_path = file_path or ""
    hl_inst.language = explicit_lang or "python"
    hl_inst._build_language_regex(hl_inst.language)
    hl_inst._is_incremental_loading = False
    hl_inst.setDocument(doc)

MultiLanguageHighlighter.attach_document_incremental = direct_attach

t0 = time.perf_counter()
editor.loadFile("sample_3000.py", py_3000)
t_sync = time.perf_counter()
print(f"3000 lines loadFile synchronous call: {(t_sync - t0)*1000:.2f} ms")

for s_idx in range(1, 10):
    ts0 = time.perf_counter()
    QCoreApplication.processEvents()
    ts1 = time.perf_counter()
    ms = (ts1 - ts0) * 1000
    print(f"  processEvents slice #{s_idx}: {ms:.2f} ms")
    if ms < 0.5 and s_idx >= 3:
        break
t_total_3k = time.perf_counter()
print(f"TOTAL 3000 lines time to settled: {(t_total_3k - t0)*1000:.2f} ms")

# 10,000 lines test
print("\n" + "="*70)
print("TEST C: QML EditorArea loadFile 10,000 lines")
print("="*70)
t0 = time.perf_counter()
editor.loadFile("sample_10000.py", py_10000)
t_sync = time.perf_counter()
print(f"10,000 lines loadFile synchronous call: {(t_sync - t0)*1000:.2f} ms")

for s_idx in range(1, 10):
    ts0 = time.perf_counter()
    QCoreApplication.processEvents()
    ts1 = time.perf_counter()
    ms = (ts1 - ts0) * 1000
    print(f"  processEvents slice #{s_idx}: {ms:.2f} ms")
    if ms < 0.5 and s_idx >= 3:
        break
t_total_10k = time.perf_counter()
print(f"TOTAL 10,000 lines time to settled: {(t_total_10k - t0)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
