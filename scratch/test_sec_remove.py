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

def test_qml(label, qml_content):
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
    comp.setData(qml_content.encode("utf-8"), base_url)
    if comp.isError():
        print(f"[{label}] Errors:", [e.toString() for e in comp.errors()])
        return
    editorArea = comp.create()
    editorArea.setProperty("width", 1200)
    editorArea.setProperty("height", 800)

    for _ in range(5): app.processEvents()

    t0 = time.perf_counter()
    editorArea.loadFile(os.path.abspath("test_data/file_a.py"), sample_text)
    t1 = time.perf_counter()
    app.processEvents()
    t2 = time.perf_counter()
    print(f"[{label}]: loadFile {(t1 - t0)*1000:.1f} ms | processEvents {(t2 - t1)*1000:.1f} ms | Total: {(t2 - t0)*1000:.1f} ms")

print("--- Testing Secondary Editor Removal ---")
# Remove secondaryEditorContainer and replace with empty Item
sec_start = orig_qml.find("// 3. Secondary Right Editor Container")
sec_end = orig_qml.find("// =========================================================================")
if sec_start != -1 and sec_end != -1:
    qml_no_sec = orig_qml[:sec_start] + "Item { id: secondaryEditorContainer; visible: false }\n" + orig_qml[sec_end:]
    test_qml("No Secondary Editor", qml_no_sec)
else:
    print("Could not find markers")

app.quit()
