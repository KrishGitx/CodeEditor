import sys, os, time
sys.path.insert(0, os.getcwd())

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import Qt, QUrl
from PySide6.QtQuickControls2 import QQuickStyle

os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
app = QGuiApplication(sys.argv)
QQuickStyle.setStyle('Basic')

from main import EditorBackend
from SettingsBackend import SettingsBackend

with open("test_data/file_a.py", "r", encoding="utf-8") as f:
    sample_text = f.read()

with open("qml/components/EditorArea.qml", "r", encoding="utf-8") as f:
    editor_qml = f.read()

# Add isInitialTextLoading guard to onTextChanged
editor_qml = editor_qml.replace(
    'property bool isRestoringTab: false',
    'property bool isRestoringTab: false\n    property bool isInitialTextLoading: false'
)

editor_qml = editor_qml.replace(
    'onTextChanged: {',
    'onTextChanged: {\n                                                            if (root.isInitialTextLoading) return;'
)

editor_qml = editor_qml.replace(
    'function loadFile(path, content) {',
    'function loadFile(path, content) {\n        root.isInitialTextLoading = true;'
)

editor_qml = editor_qml.replace(
    'console.timeEnd("[Timing] loadFile total");\n    }',
    'console.timeEnd("[Timing] loadFile total");\n        Qt.callLater(function() { root.isInitialTextLoading = false; });\n    }'
)

backend = EditorBackend()
settingsBackend = SettingsBackend()
backend.settings_backend = settingsBackend

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

theme_comp = QQmlComponent(engine, "qml/Theme.qml")
theme = theme_comp.create()
engine.rootContext().setContextProperty("theme", theme)

comp = QQmlComponent(engine)
base_url = QUrl.fromLocalFile(os.path.abspath("qml/components/EditorArea.qml"))
comp.setData(editor_qml.encode("utf-8"), base_url)
if comp.isError():
    print("QML Errors:", [e.toString() for e in comp.errors()])
    sys.exit(1)

editorArea = comp.create()
editorArea.setProperty("width", 1200)
editorArea.setProperty("height", 800)

for _ in range(5):
    app.processEvents()

print("\n--- Test: Open File A with isInitialTextLoading guard ---")
t0 = time.perf_counter()
editorArea.loadFile(os.path.abspath("test_data/file_a.py"), sample_text)
t1 = time.perf_counter()
app.processEvents()
t2 = time.perf_counter()
print(f"loadFile JS: {(t1 - t0)*1000:.2f} ms | processEvents: {(t2 - t1)*1000:.2f} ms | Total: {(t2 - t0)*1000:.2f} ms")

print("Is current file dirty?:", editorArea.property("isCurrentFileDirty"))
print("Total line count:", editorArea.property("totalLineCount"))

app.quit()
