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

print("--- Running Component Diagnostics ---")
test_variant("Baseline", orig_qml)

# Variant 1: CodeMinimap visible: false
v1 = orig_qml.replace("visible: theme ? theme.enableMinimap : true", "visible: false")
test_variant("Minimap hidden", v1)

# Variant 2: Canvas IndentGuides onPaint return immediately
v2 = orig_qml.replace("onPaint: {", "onPaint: { return;")
test_variant("Canvas onPaint bypassed", v2)

# Variant 3: No backend.register_text_area
v3 = orig_qml.replace("backend.register_text_area", "// backend.register_text_area")
test_variant("No register_text_area", v3)

# Variant 4: TextArea fixed width/height instead of editorFlickable.contentWidth/Height
v4 = orig_qml.replace("width: editorFlickable.contentWidth\n                                                        height: editorFlickable.contentHeight", "width: 2000; height: 50000")
test_variant("TextArea fixed size (no binding to flickable)", v4)

# Variant 5: Gutter visible: false
v5 = orig_qml.replace("visible: theme ? theme.enableLineNumbers : true", "visible: false")
test_variant("Gutter hidden", v5)

# Variant 6: No wrapMode on TextArea
v6 = orig_qml.replace("wrapMode: (theme && theme.enableWordWrap) ? TextArea.Wrap : TextArea.NoWrap", "wrapMode: TextArea.NoWrap")
test_variant("WrapMode NoWrap static", v6)

# Variant 7: Repeater in Gutter model: 0
v7 = orig_qml.replace("model: gutter.visibleLineCount > 0 ? gutter.visibleLineCount : 0", "model: 0")
test_variant("Gutter Repeater 0 items", v7)

app.quit()
