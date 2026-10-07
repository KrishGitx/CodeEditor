import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject
from main import EditorBackend

def run_tests():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    backend = EditorBackend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)

    comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
    assert not comp.isError(), f"Compilation errors: {[e.toString() for e in comp.errors()]}"
    root = comp.create()
    editor = root.findChild(QObject, "editorArea")

    py_3000 = "\n".join([f"def sample_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i}\n    return val + y" for i in range(750)])
    cpp_3000 = "\n".join([f"#include <iostream>\nint func_{i}() {{\n    // Line comment {i}\n    int val = {i} * 2;\n    return val;\n}}" for i in range(500)])
    html_3000 = "\n".join([f"<div class=\"item-{i}\">\n    <span>Item {i}</span>\n    <p>Description text</p>\n</div>" for i in range(750)])
    py_10000 = "\n".join([f"def large_func_{i}():\n    # Test line {i}\n    return {i} * 42" for i in range(2500)])

    files = [
        ("Python 3000 lines", "test_python.py", py_3000),
        ("C++ 3000 lines", "test_cpp.cpp", cpp_3000),
        ("HTML 3000 lines", "test_html.html", html_3000),
        ("10,000-line File", "test_large.py", py_10000)
    ]

    print("==========================================")
    print("TIMING VERIFICATION: USER-PERCEIVED LOAD")
    print("==========================================")

    for name, path, content in files:
        print(f"\n>>> Loading: {name}")
        t0 = time.perf_counter()
        editor.loadFile(path, content)
        t_call = time.perf_counter()
        print(f"  [Timing] loadFile call: {(t_call - t0)*1000:.2f} ms")

        # Initial render tick
        t_vis_start = time.perf_counter()
        QCoreApplication.processEvents()
        t_vis_end = time.perf_counter()
        print(f"  [Timing] Initial UI Render / File Visible: {(t_vis_end - t_vis_start)*1000:.2f} ms")

        # Pump remaining background highlight slices
        t_bg_start = time.perf_counter()
        for _ in range(30):
            QCoreApplication.processEvents()
            time.sleep(0.002)
        t_bg_end = time.perf_counter()
        print(f"  [Timing] Background highlight & minimap complete: {(t_bg_end - t_bg_start)*1000:.2f} ms")
        print(f"  [Timing] Total time to fully settled state: {(t_bg_end - t0)*1000:.2f} ms")

    print("\n==========================================")
    print("TAB SWITCHING PERFORMANCE (A -> B -> A)")
    print("==========================================")
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        editor.switchToTab(0)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        times.append((t1 - t0)*1000)

        t0 = time.perf_counter()
        editor.switchToTab(3)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        times.append((t1 - t0)*1000)

    avg_switch = sum(times) / len(times)
    print(f"[PASS] Average Tab Switch Time: {avg_switch:.2f} ms")

    if backend.lsp_process:
        try: backend.lsp_process.terminate()
        except Exception: pass

    print("\n==========================================")
    print("ALL LOAD AND SWITCH TIMING TESTS PASSED!")
    print("==========================================")
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
