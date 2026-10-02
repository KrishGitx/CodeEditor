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

def test_variant(name, modified_qml):
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
    comp.setData(modified_qml.encode("utf-8"), base_url)
    if comp.isError():
        print(f"[{name}] QML Error:", [e.toString() for e in comp.errors()])
        return

    editorArea = comp.create()
    editorArea.setProperty("width", 1200)
    editorArea.setProperty("height", 800)

    for _ in range(5):
        app.processEvents()

    t0 = time.perf_counter()
    editorArea.loadFile(os.path.abspath("test_data/file_a.py"), sample_text)
    t1 = time.perf_counter()
    app.processEvents()
    t2 = time.perf_counter()
    print(f"[{name}] loadFile: {(t1 - t0)*1000:.1f} ms | processEvents: {(t2 - t1)*1000:.1f} ms | Total: {(t2 - t0)*1000:.1f} ms")

print("--- Testing Text Assignment Variants ---")

# Variant A: text: "" initially, then set text in Timer / Qt.callLater
vA = orig_qml.replace('text: model.content || ""', 'text: ""')
test_variant("TextArea text empty", vA)

# Variant B: In loadFile, append with content: ""
vB = orig_qml.replace('content: content,', 'content: "",')
test_variant("tabModel.append with empty content", vB)

# Variant C: Replace StackLayout with single Item
vC = orig_qml.replace('StackLayout {\n                                id: tabEditorStack', 'Item {\n                                id: tabEditorStack')
test_variant("StackLayout -> Item", vC)

app.quit()
