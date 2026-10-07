import sys, os, tempfile
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
engine.rootContext().setContextProperty('backend', backend)

comp = QQmlComponent(engine, os.path.abspath('qml/main.qml'))
if comp.isError():
    print('Errors:', [e.toString() for e in comp.errors()])
    sys.exit(1)

root = comp.create()
# Find editorArea property or child
editor = root.findChild(QObject, 'editorArea')

print('editorArea found:', editor is not None)

tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.py')
tmp.write(b'print("hello world")\n')
tmp.close()

try:
    print('Opening file:', tmp.name)
    backend.open_file(tmp.name)
    QCoreApplication.processEvents()

    # Let's inspect tabs
    tab_count = editor.property('tabCount')
    print('Tab count after open_file:', tab_count)
    for i in range(tab_count):
        is_dirty = editor.isTabDirty(i)
        path = editor.getTabPath(i)
        print(f'Tab {i}: path={path}, isDirty={is_dirty}')
finally:
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)
