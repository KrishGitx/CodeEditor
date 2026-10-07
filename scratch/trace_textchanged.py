import sys, os, tempfile, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, qInstallMessageHandler
from main import EditorBackend

def msg_handler(mode, context, message):
    print(f'[QML MSG] {message}')

qInstallMessageHandler(msg_handler)

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty('backend', backend)

comp = QQmlComponent(engine, os.path.abspath('qml/main.qml'))
root = comp.create()
editor = root.findChild(QObject, 'editorArea')

tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.py')
tmp.write(b'print("hello world")\n')
tmp.close()

try:
    print('Calling open_file...')
    backend.open_file(tmp.name)
    print('After open_file...')
    QCoreApplication.processEvents()
finally:
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)
    if backend.lsp_process:
        try: backend.lsp_process.terminate()
        except Exception: pass
