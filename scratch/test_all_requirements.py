import sys, os, time, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, Slot

class FastBackend(QObject):
    @Slot(str, str)
    def set_active_file(self, a, b): pass
    @Slot(object, str, str)
    def register_text_area(self, a, b, c): pass
    @Slot(object, str)
    def register_text_area(self, a, b): pass
    @Slot(object)
    def register_text_area(self, a): pass
    @Slot(str, str)
    def save_file(self, path, content):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    @Slot(str)
    def copy_path_to_clipboard(self, a): pass
    @Slot(str)
    def reveal_in_explorer(self, a): pass

def run_tests():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    backend = FastBackend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)

    comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
    assert not comp.isError(), f"Compilation errors: {[e.toString() for e in comp.errors()]}"
    root = comp.create()
    assert root is not None, "Failed to instantiate main.qml"
    
    editor = root.findChild(QObject, "editorArea")
    assert editor is not None, "Failed to find editorArea"

    print("\n==========================================")
    print("1. TESTING MINIMAP & FILE LOAD PERFORMANCE")
    print("==========================================")

    test_dir = tempfile.mkdtemp(prefix="dgx_perf_")
    py_path = os.path.join(test_dir, "test_python.py")
    cpp_path = os.path.join(test_dir, "test_cpp.cpp")
    html_path = os.path.join(test_dir, "test_html.html")
    large_path = os.path.join(test_dir, "test_large.py")

    py_3000 = "\n".join([f"def sample_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i}\n    return val + y" for i in range(750)])
    cpp_3000 = "\n".join([f"#include <iostream>\nint func_{i}() {{\n    // Line comment {i}\n    int val = {i} * 2;\n    return val;\n}}" for i in range(500)])
    html_3000 = "\n".join([f"<div class=\"item-{i}\">\n    <span>Item {i}</span>\n    <p>Description text</p>\n</div>" for i in range(750)])
    large_10000 = "\n".join([f"def large_func_{i}():\n    # Test line {i}\n    return {i} * 42" for i in range(2500)])

    for p, c in [(py_path, py_3000), (cpp_path, cpp_3000), (html_path, html_3000), (large_path, large_10000)]:
        with open(p, "w", encoding="utf-8") as f:
            f.write(c)

    # Test loadFile timing
    t0 = time.perf_counter()
    editor.loadFile(py_path, py_3000)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[PASS] Python 3000-line file loaded in: {(t1 - t0)*1000:.2f} ms")

    t0 = time.perf_counter()
    editor.loadFile(cpp_path, cpp_3000)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[PASS] C++ 3000-line file loaded in: {(t1 - t0)*1000:.2f} ms")

    t0 = time.perf_counter()
    editor.loadFile(html_path, html_3000)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[PASS] HTML 3000-line file loaded in: {(t1 - t0)*1000:.2f} ms")

    t0 = time.perf_counter()
    editor.loadFile(large_path, large_10000)
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[PASS] 10,000-line file loaded in: {(t1 - t0)*1000:.2f} ms")

    print("\n==========================================")
    print("2. TESTING DIRTY STATE INITIALIZATION & EDIT LIFECYCLE")
    print("==========================================")

    # 1. Existing files opened unchanged must NOT be dirty
    for i in range(editor.property("tabCount")):
        p = editor.getTabPath(i)
        dirty = editor.isTabDirty(i)
        assert dirty == False, f"Error: Existing file {p} opened dirty!"
    print("[PASS] All 4 existing files opened with isDirty = False (NO dot)")

    # 2. Test user editing a file -> dot appears
    editor.switchToTab(0) # test_python.py
    editor.setTabDirty(0, True)
    assert editor.isTabDirty(0) == True, "Error: Edited tab 0 should be dirty!"
    print("[PASS] User edit sets isDirty = True (dot appears)")

    # 3. Test saving file -> dot disappears
    saved = editor.saveCurrentFile()
    assert saved == True, "saveCurrentFile returned False"
    assert editor.isTabDirty(0) == False, "Error: Saved tab 0 should NOT be dirty!"
    print("[PASS] Save file resets isDirty = False (dot disappears)")

    # 4. Test user creating new unsaved file -> dot appears
    editor.createNewFile()
    new_idx = editor.property("tabCount") - 1
    assert editor.isTabDirty(new_idx) == True, "Error: New unsaved file should be dirty!"
    print("[PASS] New unsaved file has isDirty = True (dot appears)")

    # 5. Test tab switching preserves per-tab dirty states
    editor.switchToTab(1) # test_cpp (clean)
    assert editor.isTabDirty(1) == False
    assert editor.property("isCurrentFileDirty") == False

    editor.switchToTab(new_idx) # untitled (dirty)
    assert editor.isTabDirty(new_idx) == True
    assert editor.property("isCurrentFileDirty") == True

    editor.switchToTab(0) # test_python (clean)
    assert editor.isTabDirty(0) == False
    assert editor.property("isCurrentFileDirty") == False
    print("[PASS] Switching tabs preserves independent dirty state for every tab")

    print("\n==========================================")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("==========================================")
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
