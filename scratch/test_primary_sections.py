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
    orig_lines = f.readlines()

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

print("--- Testing Primary Editor Sections ---")

# Test A: Remove lines 1064 to 1344 (Right-click overlay, radial menu, standard context menu, autocomplete popup, color picker)
# 1-indexed lines 1064:1344 is slice 1063:1344
prefix_A = "".join(orig_lines[:1063])
suffix_A = "".join(orig_lines[1344:])
test_qml("No Overlays/Popups (lines 1064-1344 removed)", prefix_A + suffix_A)

# Test B: In tabPane delegate, simplify TextArea (lines 581:1039, so slice 580:1039)
prefix_B = "".join(orig_lines[:580])
suffix_B = "".join(orig_lines[1039:])
simple_ta = """                                                    TextArea {
                                                        id: codeTextArea
                                                        objectName: "codeTextArea"
                                                        width: editorFlickable.contentWidth
                                                        height: editorFlickable.contentHeight
                                                        textFormat: TextArea.PlainText
                                                        text: model.content || ""
                                                        Component.onCompleted: {
                                                            if (typeof backend !== "undefined" && backend.register_text_area) {
                                                                backend.register_text_area(codeTextArea, model.path, model.languageId);
                                                            }
                                                        }
                                                    }
"""
test_qml("Simple TextArea (no key handlers/tap handlers/overlays)", prefix_B + simple_ta + suffix_B)

app.quit()
