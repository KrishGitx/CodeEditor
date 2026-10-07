import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, Slot
from HighlighterEngine import MultiLanguageHighlighter

class ProbeBackend(QObject):
    def __init__(self):
        super().__init__()
        self.doc = None

    @Slot(str, str)
    def set_active_file(self, a, b): pass

    @Slot(QObject)
    @Slot(QObject, str)
    @Slot(QObject, str, str)
    def register_text_area(self, qml_ta, path="", lang=""):
        qml_doc = qml_ta.property("textDocument")
        doc = qml_doc.textDocument()
        print("1. Creating MultiLanguageHighlighter...")
        t0 = time.perf_counter()
        hl = MultiLanguageHighlighter(None)
        t1 = time.perf_counter()
        print(f"Created hl in: {(t1 - t0)*1000:.2f} ms")

        print("2. set_language_for_file...")
        t0 = time.perf_counter()
        hl.set_language_for_file("test.py", explicit_lang="python", force_rehighlight=False)
        t1 = time.perf_counter()
        print(f"set_language_for_file in: {(t1 - t0)*1000:.2f} ms")

        print("3. Calling hl.setDocument(doc)...")
        t0 = time.perf_counter()
        hl.setDocument(doc)
        t1 = time.perf_counter()
        print(f"hl.setDocument(doc) took: {(t1 - t0)*1000:.2f} ms")

    @Slot(str, str)
    def save_file(self, p, c): pass
    @Slot(str)
    def copy_path_to_clipboard(self, a): pass
    @Slot(str)
    def reveal_in_explorer(self, a): pass

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = ProbeBackend()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)

comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root = comp.create()
editor = root.findChild(QObject, "editorArea")

py_10000 = "\n".join([f"def large_func_{i}():\n    # Test line {i}\n    return {i} * 42" for i in range(2500)])

print("\nCalling loadFile...")
t0 = time.perf_counter()
editor.loadFile("test.py", py_10000)
t1 = time.perf_counter()
print(f"editor.loadFile call completed in: {(t1 - t0)*1000:.2f} ms")

print("\nCalling processEvents...")
t0 = time.perf_counter()
QCoreApplication.processEvents()
t1 = time.perf_counter()
print(f"processEvents completed in: {(t1 - t0)*1000:.2f} ms")

sys.exit(0)
