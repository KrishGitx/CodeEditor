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
    orig_qml = f.read()

# Let's test passing empty content to tabModel.append and setting codeTextArea.text directly!
qml_test = orig_qml

# 1. In loadFile, pass content: "" to tabModel.append, but store in a JS property/variable
qml_test = qml_test.replace(
    'content: content,',
    'content: "",'
)

# 2. In loadFile, after switchToTab, set activeEditorPane.codeTextArea.text = content
qml_test = qml_test.replace(
    'switchToTab(newIdx);',
    '''switchToTab(newIdx);
        if (root.activeEditorPane && root.activeEditorPane.codeTextArea) {
            root.activeEditorPane.codeTextArea.text = content;
        }'''
)

# 3. In codeTextArea, remove text: model.content || ""
qml_test = qml_test.replace(
    'text: model.content || ""',
    'text: ""'
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
comp.setData(qml_test.encode("utf-8"), base_url)
if comp.isError():
    print("Errors:", [e.toString() for e in comp.errors()])
    sys.exit(1)

editorArea = comp.create()
editorArea.setProperty("width", 1200)
editorArea.setProperty("height", 800)

for _ in range(5): app.processEvents()

print("\n--- Test: Direct TextArea Text Assignment without ListModel content bloat ---")
t0 = time.perf_counter()
editorArea.loadFile(os.path.abspath("test_data/file_a.py"), sample_text)
t1 = time.perf_counter()
app.processEvents()
t2 = time.perf_counter()
print(f"loadFile JS: {(t1 - t0)*1000:.2f} ms | processEvents: {(t2 - t1)*1000:.2f} ms | Total: {(t2 - t0)*1000:.2f} ms")

print("codeTextArea text length:", len(editorArea.property("codeTextArea").property("text")))
print("totalLineCount:", editorArea.property("totalLineCount"))

app.quit()
