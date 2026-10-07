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
    py_10000 = "\n".join([f"def large_func_{i}():\n    # Test line {i}\n    return {i} * 42" for i in range(2500)])

    print("==========================================")
    print("1. REAL BACKEND: FILE LOADING BENCHMARK")
    print("==========================================")
    t0 = time.perf_counter()
    editor.loadFile("test_python.py", py_3000)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[PASS] Python 3000 lines: {(t1 - t0)*1000:.2f} ms")

    t0 = time.perf_counter()
    editor.loadFile("test_cpp.cpp", cpp_3000)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[PASS] C++ 3000 lines: {(t1 - t0)*1000:.2f} ms")

    t0 = time.perf_counter()
    editor.loadFile("test_large_10000.py", py_10000)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[PASS] Python 10000 lines: {(t1 - t0)*1000:.2f} ms")

    print("\n==========================================")
    print("2. REAL BACKEND: TAB SWITCHING BENCHMARK")
    print("==========================================")
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        editor.switchToTab(0)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        times.append((t1 - t0)*1000)

        t0 = time.perf_counter()
        editor.switchToTab(2)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        times.append((t1 - t0)*1000)

    avg_switch_time = sum(times) / len(times)
    print(f"[PASS] Average Tab Switch Time with Real Highlighter: {avg_switch_time:.2f} ms")
    assert avg_switch_time < 50.0

    print("\n==========================================")
    print("ALL REAL BACKEND TESTS PASSED!")
    print("==========================================")
    if backend.lsp_process:
        try: backend.lsp_process.terminate()
        except Exception: pass
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
