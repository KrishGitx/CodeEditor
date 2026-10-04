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

backend = EditorBackend()
settingsBackend = SettingsBackend()
backend.settings_backend = settingsBackend

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

theme_comp = QQmlComponent(engine, "qml/Theme.qml")
theme = theme_comp.create()
engine.rootContext().setContextProperty("theme", theme)

with open("test_data/file_a.py", "r", encoding="utf-8") as f:
    sample_text = f.read()

with open("qml/components/EditorArea.qml", "r", encoding="utf-8") as f:
    qml_str = f.read()

# Let's inspect how the wheel handler and word wrap can be refined in EditorArea.qml
# We test in standalone EditorArea
comp = QQmlComponent(engine)
base_url = QUrl.fromLocalFile(os.path.abspath("qml/components/EditorArea.qml"))
comp.setData(qml_str.encode("utf-8"), base_url)
editorArea = comp.create()
editorArea.setProperty("width", 1200)
editorArea.setProperty("height", 800)

for _ in range(5): app.processEvents()

editorArea.loadFile(os.path.abspath("test_data/file_a.py"), sample_text)
app.processEvents()

print("Loaded file A:")
print("editorFlickable contentWidth:", editorArea.property("editorFlickable").property("contentWidth"))
print("codeTextArea wrapMode:", editorArea.property("codeTextArea").property("wrapMode"))

# Test Toggling Word Wrap
print("\n--- Testing Word Wrap Toggle ---")
theme.setProperty("enableWordWrap", True)
app.processEvents()
print("WordWrap is now TRUE:")
print("  editorFlickable contentWidth:", editorArea.property("editorFlickable").property("contentWidth"))
print("  codeTextArea width:", editorArea.property("codeTextArea").property("width"))
print("  codeTextArea wrapMode:", editorArea.property("codeTextArea").property("wrapMode"))

app.quit()
