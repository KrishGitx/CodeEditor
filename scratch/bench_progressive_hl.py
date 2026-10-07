import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, QTimer
from main import EditorBackend
from HighlighterEngine import MultiLanguageHighlighter

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root_app = comp.create()
editor = root_app.findChild(QObject, "editorArea")

py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])

# Configure progressive highlighter
class ProgressiveHighlighter(MultiLanguageHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initial_limit = 180
        self.highlight_all = False
        self._deferred_timer = QTimer()
        self._deferred_timer.setSingleShot(True)
        self._deferred_timer.setInterval(200)
        self._deferred_timer.timeout.connect(self._complete_highlighting)

    def attach_document(self, doc, file_path="", explicit_lang=None):
        self.file_path = file_path or ""
        self.language = explicit_lang or "python"
        self._build_language_regex(self.language)
        
        total_blocks = doc.blockCount() if doc else 0
        if total_blocks > self.initial_limit:
            self.highlight_all = False
            self.setDocument(doc)
            print("[Timing] First visible syntax highlight complete", flush=True)
            self._deferred_timer.start()
        else:
            self.highlight_all = True
            self.setDocument(doc)
            print("[Timing] Full syntax highlighting complete", flush=True)

    def _complete_highlighting(self):
        if not self.highlight_all and self.document():
            self.highlight_all = True
            t0 = time.perf_counter()
            self.rehighlight()
            t1 = time.perf_counter()
            print(f"[Timing] Full syntax highlighting complete (rehighlight took {(t1-t0)*1000:.2f} ms)", flush=True)

    def highlightBlock(self, text):
        if not text or not self.unified_regex or self.language in ("text", "binary", "plain"):
            self.setCurrentBlockState(0)
            return

        if not self.highlight_all:
            b_num = self.currentBlock().blockNumber()
            if b_num >= self.initial_limit:
                self.setCurrentBlockState(0)
                return

        state = self.previousBlockState()
        if state <= 0: state = 0
        offset = 0
        self._highlight_range(text, offset, len(text))
        self.setCurrentBlockState(0)

# Replace highlighter in backend.register_text_area
def reg_progressive(qml_text_area, file_path="", lang=""):
    qml_doc = qml_text_area.property("textDocument")
    if qml_doc:
        doc = qml_doc.textDocument()
        from HighlighterEngine import get_cpp_ptr
        doc_id = get_cpp_ptr(doc)
        if not hasattr(backend, "tab_highlighters"):
            backend.tab_highlighters = {}
        if doc_id not in backend.tab_highlighters:
            hl = ProgressiveHighlighter(None)
            hl.attach_document(doc, file_path, explicit_lang=lang)
            backend.tab_highlighters[doc_id] = hl
        backend.highlighter = backend.tab_highlighters[doc_id]

backend.register_text_area = reg_progressive

print("="*70)
print("TEST PROGRESSIVE HIGHLIGHTER ON 3,000 LINES")
print("="*70)

t0 = time.perf_counter()
editor.loadFile("sample_3000.py", py_3000)
t1 = time.perf_counter()
QCoreApplication.processEvents()
t2 = time.perf_counter()
print(f"1. Immediate File Open & First Render: loadFile: {(t1-t0)*1000:.2f} ms | first render: {(t2-t1)*1000:.2f} ms | TOTAL: {(t2-t0)*1000:.2f} ms")

print("2. Sleeping 250ms for background completion timer...")
time.sleep(0.25)
t3 = time.perf_counter()
QCoreApplication.processEvents()
t4 = time.perf_counter()
print(f"3. Deferred highlight pass duration: {(t4-t3)*1000:.2f} ms")

print("\n" + "="*70)
print("TEST TAB SWITCHING (Tab 0 <-> Tab 1)")
print("="*70)
editor.loadFile("sample_tab2.py", py_3000)
QCoreApplication.processEvents()

for i in range(4):
    target = i % 2
    t0 = time.perf_counter()
    editor.switchToTab(target)
    t1 = time.perf_counter()
    QCoreApplication.processEvents()
    t2 = time.perf_counter()
    print(f"Switch to Tab {target}: {(t2-t0)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
