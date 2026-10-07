import sys, os, time
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

# Test files: Python 3k, C++ 3k, HTML 3k, Python 10k
py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])
cpp_3000 = "\n".join([f"int cpp_func_{i}(int x, double y) {{\n    // Calculation {i}\n    int val = x * {i} + static_cast<int>(y);\n    return val;\n}}" for i in range(600)])
html_3000 = "\n".join([f"<div id='section_{i}' class='card-item'>\n    <h3>Section {i} Title</h3>\n    <p>This is paragraph content for section {i}.</p>\n</div>" for i in range(750)])
py_10000 = "\n".join([f"def func_10k_{i}(a, b):\n    # line {i}\n    res = a + b * {i}\n    return res" for i in range(2500)])

test_cases = [
    ("Python 3,000 lines", "test_3000.py", py_3000),
    ("C++ 3,000 lines", "test_3000.cpp", cpp_3000),
    ("HTML 3,000 lines", "test_3000.html", html_3000),
    ("Python 10,000 lines", "test_10000.py", py_10000),
]

print("="*80)
print("STAGE-BY-STAGE TIMING AUDIT (WITH REVERTED CHUNK TIMER / NORMAL HIGHLIGHTER)")
print("="*80)

for name, fname, text in test_cases:
    print(f"\n>>> Running Test Case: {name} ({len(text.splitlines())} lines, {len(text)} chars)")
    
    t0 = time.perf_counter()
    editor.loadFile(fname, text)
    t_loadfile = time.perf_counter()
    
    # Process immediate events
    t_pe0 = time.perf_counter()
    QCoreApplication.processEvents()
    t_pe1 = time.perf_counter()
    
    # Process any deferred events (timers, etc.)
    time.sleep(0.12) # wait for 100ms minimap timer
    t_pe_def0 = time.perf_counter()
    QCoreApplication.processEvents()
    t_pe_def1 = time.perf_counter()
    
    print(f"  Stage 1: loadFile() synchronous call:      {(t_loadfile - t0)*1000:6.2f} ms")
    print(f"  Stage 2: processEvents() (editor visible):  {(t_pe1 - t_pe0)*1000:6.2f} ms")
    print(f"  Stage 3: Deferred timers / Minimap paint:   {(t_pe_def1 - t_pe_def0)*1000:6.2f} ms")
    print(f"  Total Time to Completely Responsive:       {((t_loadfile - t0) + (t_pe1 - t_pe0) + (t_pe_def1 - t_pe_def0))*1000:6.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
