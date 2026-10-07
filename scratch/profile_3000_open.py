import sys, os, time, cProfile, pstats, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, QTimer
from main import EditorBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)

comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root = comp.create()
editor = root.findChild(QObject, "editorArea")

# Let's generate a 3,000 line Python file
lines_3000 = []
for i in range(750):
    lines_3000.append(f"def test_function_{i}(param_a, param_b):")
    lines_3000.append(f'    """Docstring for function {i} explaining operations."""')
    lines_3000.append(f"    result = param_a * {i} + len(str(param_b))")
    lines_3000.append(f"    return result")
py_3000 = "\n".join(lines_3000)

print(f"Total lines in sample: {len(lines_3000)}, characters: {len(py_3000)}")

# Profile loadFile with event loop iterations
print("\n" + "="*70)
print("PROFILING 3000-LINE FILE OPEN PIPELINE")
print("="*70)

pr = cProfile.Profile()
pr.enable()

t_start = time.perf_counter()
print(f"[{time.perf_counter() - t_start:.4f}s] Calling editor.loadFile('sample_3000.py', py_3000)")
editor.loadFile("sample_3000.py", py_3000)
t_after_loadfile = time.perf_counter()
print(f"[{t_after_loadfile - t_start:.4f}s] loadFile synchronous call returned (took {(t_after_loadfile - t_start)*1000:.2f}ms)")

# Let's trace individual processEvents slices
for slice_idx in range(1, 11):
    t_before_slice = time.perf_counter()
    QCoreApplication.processEvents()
    t_after_slice = time.perf_counter()
    slice_ms = (t_after_slice - t_before_slice) * 1000
    print(f"[{t_after_slice - t_start:.4f}s] processEvents slice #{slice_idx} took {slice_ms:.2f}ms")
    if slice_ms < 0.5 and slice_idx >= 5:
        break

t_end = time.perf_counter()
pr.disable()
print(f"\nTOTAL PIPELINE DURATION: {(t_end - t_start)*1000:.2f}ms")

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats(35)
print("\nTop 35 Cumulative Time Functions:\n" + s.getvalue())

s2 = io.StringIO()
ps2 = pstats.Stats(pr, stream=s2).sort_stats('time')
ps2.print_stats(25)
print("\nTop 25 Self Time Functions:\n" + s2.getvalue())

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
