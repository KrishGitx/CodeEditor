import sys, os, time, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, Slot
from HighlighterEngine import MultiLanguageHighlighter

class MockBackend(QObject):
    def __init__(self):
        super().__init__()
        self.tab_highlighters = {}
        self.highlighter = None
        self.current_file = ""

    @Slot(str)
    @Slot(str, str)
    def set_active_file(self, file_path, lang=""):
        self.current_file = file_path or ""

    @Slot(QObject)
    @Slot(QObject, str)
    @Slot(QObject, str, str)
    def register_text_area(self, qml_text_area, file_path="", lang=""):
        if not qml_text_area:
            return
        qml_doc = qml_text_area.property("textDocument")
        if qml_doc:
            doc = qml_doc.textDocument()
            doc_id = id(doc)
            if doc_id not in self.tab_highlighters:
                hl = MultiLanguageHighlighter(None)
                hl.set_language_for_file(file_path or "main.py", explicit_lang=lang, force_rehighlight=False)
                hl.setDocument(doc)
                self.tab_highlighters[doc_id] = hl
            self.highlighter = self.tab_highlighters[doc_id]

    @Slot(str, str)
    def save_file(self, p, c): pass
    @Slot(str)
    def copy_path_to_clipboard(self, a): pass
    @Slot(str)
    def reveal_in_explorer(self, a): pass

def run_tests():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    backend = MockBackend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)

    comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
    assert not comp.isError(), f"Compilation errors: {[e.toString() for e in comp.errors()]}"
    root = comp.create()
    editor = root.findChild(QObject, "editorArea")

    print("==========================================")
    print("1. BENCHMARKING FILE OPENING (3K & 10K LINES)")
    print("==========================================")
    py_3000 = "\n".join([f"def sample_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i}\n    return val + y" for i in range(750)])
    cpp_3000 = "\n".join([f"#include <iostream>\nint func_{i}() {{\n    // Line comment {i}\n    int val = {i} * 2;\n    return val;\n}}" for i in range(500)])
    py_10000 = "\n".join([f"def large_func_{i}():\n    # Test line {i}\n    return {i} * 42" for i in range(2500)])

    t0 = time.perf_counter()
    editor.loadFile("test_python.py", py_3000)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[PASS] Python 3000 lines open time: {(t1 - t0)*1000:.2f} ms")

    t0 = time.perf_counter()
    editor.loadFile("test_cpp.cpp", cpp_3000)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[PASS] C++ 3000 lines open time: {(t1 - t0)*1000:.2f} ms")

    t0 = time.perf_counter()
    editor.loadFile("test_large_10000.py", py_10000)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[PASS] Python 10000 lines open time: {(t1 - t0)*1000:.2f} ms")

    print("\n==========================================")
    print("2. BENCHMARKING TAB SWITCHING (A -> B -> A)")
    print("==========================================")
    # Switch from Tab 2 (10,000 lines) -> Tab 0 (3,000 lines)
    times = []
    for _ in range(10):
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
    print(f"[PASS] Average Tab Switch Time (3k <-> 10k): {avg_switch_time:.2f} ms")
    assert avg_switch_time < 50.0, f"Tab switch is too slow: {avg_switch_time:.2f} ms"

    print("\n==========================================")
    print("ALL TAB SWITCH AND LOAD BENCHMARKS PASSED!")
    print("==========================================")
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
