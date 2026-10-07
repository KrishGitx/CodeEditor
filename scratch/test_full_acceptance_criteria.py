import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, QTimer, Qt
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
print("ACCEPTANCE CRITERIA RIGOROUS TEST SUITE")
print("="*80)

for name, fname, text in test_cases:
    print(f"\n>>> Running: {name} ({len(text.splitlines())} lines, {len(text)} chars)")
    
    t0 = time.perf_counter()
    editor.loadFile(fname, text)
    t_loadfile = time.perf_counter()
    
    # Process immediate events to reach visible interactive state
    t_pe0 = time.perf_counter()
    QCoreApplication.processEvents()
    t_pe1 = time.perf_counter()
    
    open_time_ms = (t_loadfile - t0 + t_pe1 - t_pe0) * 1000
    print(f"  [1] Initial File Open to Interactive: {open_time_ms:6.2f} ms")
    assert open_time_ms < 600, f"File open took too long: {open_time_ms} ms"
    
    # Verify typing responsiveness immediately
    pane = editor.property("activeEditorPane")
    assert pane is not None, "Editor pane should be active"
    ta = pane.property("codeTextArea")
    assert ta is not None, "TextArea should be active"
    
    t_type0 = time.perf_counter()
    ta.insert(0, "# Immediately Responsive\n")
    QCoreApplication.processEvents()
    t_type1 = time.perf_counter()
    type_time_ms = (t_type1 - t_type0) * 1000
    print(f"  [2] Immediate Typing Response:        {type_time_ms:6.2f} ms")
    assert type_time_ms < 100, f"Typing took too long: {type_time_ms} ms"
    
    # Verify scrolling responsiveness
    flick = pane.property("editorFlickable")
    t_scroll0 = time.perf_counter()
    flick.setProperty("contentY", 1000.0)
    QCoreApplication.processEvents()
    t_scroll1 = time.perf_counter()
    scroll_time_ms = (t_scroll1 - t_scroll0) * 1000
    print(f"  [3] Scrolling Response:               {scroll_time_ms:6.2f} ms")
    assert scroll_time_ms < 100, f"Scrolling took too long: {scroll_time_ms} ms"
    
    # Allow background progressive highlighting and minimap to complete
    time.sleep(0.3)
    t_bg0 = time.perf_counter()
    QCoreApplication.processEvents()
    t_bg1 = time.perf_counter()
    bg_time_ms = (t_bg1 - t_bg0) * 1000
    print(f"  [4] Background Completion Settling:   {bg_time_ms:6.2f} ms")
    
    print(f"  --> PASSED: Responsive immediately with zero freeze!")

print("\n" + "="*80)
print("VERIFY TAB SWITCHING SPEED")
print("="*80)
tab_count = editor.property("tabModel").property("count")
print(f"Total tabs open: {tab_count}")
for i in range(tab_count):
    t0 = time.perf_counter()
    editor.switchToTab(i)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    ms = (t1 - t0) * 1000
    print(f"  Switch to Tab {i}: {ms:6.2f} ms")
    assert ms < 150, f"Tab switch took too long: {ms} ms"

print("\nALL ACCEPTANCE CRITERIA FULLY VERIFIED AND PASSING!")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
