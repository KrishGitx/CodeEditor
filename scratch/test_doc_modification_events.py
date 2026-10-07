import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QTextCursor
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

tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".py")
tmp.write(b"def test():\n    return 42\n")
tmp.close()

try:
    print("Opening file...")
    backend.open_file(tmp.name)
    QCoreApplication.processEvents()

    doc = backend.text_document
    print("doc:", doc)
    print("doc.isModified initially:", doc.isModified() if doc else "No doc")
    
    # Let's test doc.setModified(False)
    if doc:
        doc.setModified(False)
        print("doc.isModified after setModified(False):", doc.isModified())

        events = []
        doc.modificationChanged.connect(lambda m: events.append(m))

        # Insert char
        ta = backend.qml_text_area
        ta.insert(0, "# ")
        QCoreApplication.processEvents()
        print("doc.isModified after insert:", doc.isModified(), "events:", events)

        # Undo
        doc.undo()
        QCoreApplication.processEvents()
        print("doc.isModified after undo:", doc.isModified(), "events:", events)

        # Redo
        doc.redo()
        QCoreApplication.processEvents()
        print("doc.isModified after redo:", doc.isModified(), "events:", events)

        # Save simulation -> doc.setModified(False)
        doc.setModified(False)
        print("doc.isModified after save:", doc.isModified())

finally:
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)
    if backend.lsp_process:
        try: backend.lsp_process.terminate()
        except Exception: pass
