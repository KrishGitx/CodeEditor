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
    file_a_text = f.read()

with open("test_data/file_b.py", "r", encoding="utf-8") as f:
    file_b_text = f.read()

backend = EditorBackend()
settingsBackend = SettingsBackend()
backend.settings_backend = settingsBackend

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

theme_comp = QQmlComponent(engine, "qml/Theme.qml")
theme = theme_comp.create()
engine.rootContext().setContextProperty("theme", theme)

with open("qml/components/EditorArea.qml", "r", encoding="utf-8") as f:
    editor_qml = f.read()

old_block = '''                                                        text: model.content || ""

                                                        Component.onCompleted: {
                                                            if (tabPane.index === root.activeTabIndex && typeof backend !== "undefined" && backend && backend.register_text_area) {
                                                                backend.register_text_area(codeTextArea, model.path || "", model.languageId || "text");
                                                            }
                                                            Qt.callLater(function() {
                                                                if (tabPane) {
                                                                    tabPane.paneScopeRanges = root.computeScopesForText(codeTextArea.text);
                                                                    indentGuidesCanvas.requestPaint();
                                                                }
                                                            });
                                                        }'''

new_block = '''                                                        text: ""

                                                        Component.onCompleted: {
                                                            codeTextArea.text = model.content || "";
                                                            if (tabPane.index === root.activeTabIndex && typeof backend !== "undefined" && backend && backend.register_text_area) {
                                                                backend.register_text_area(codeTextArea, model.path || "", model.languageId || "text");
                                                            }
                                                            Qt.callLater(function() {
                                                                if (tabPane) {
                                                                    tabPane.paneScopeRanges = root.computeScopesForText(codeTextArea.text);
                                                                    indentGuidesCanvas.requestPaint();
                                                                }
                                                            });
                                                        }'''

editor_qml = editor_qml.replace(old_block, new_block)

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

print("\n--- Test 1: Open File A (3000 lines) ---")
t0 = time.perf_counter()
editorArea.loadFile(os.path.abspath("test_data/file_a.py"), file_a_text)
t1 = time.perf_counter()
app.processEvents()
t2 = time.perf_counter()
print(f"File A loadFile JS: {(t1 - t0)*1000:.2f} ms | processEvents: {(t2 - t1)*1000:.2f} ms | Total: {(t2 - t0)*1000:.2f} ms")

print("\n--- Test 2: Open File B (3000 lines) ---")
t0 = time.perf_counter()
editorArea.loadFile(os.path.abspath("test_data/file_b.py"), file_b_text)
t1 = time.perf_counter()
app.processEvents()
t2 = time.perf_counter()
print(f"File B loadFile JS: {(t1 - t0)*1000:.2f} ms | processEvents: {(t2 - t1)*1000:.2f} ms | Total: {(t2 - t0)*1000:.2f} ms")

print("\n--- Test 3: Tab Switching A -> B -> A ---")
t0 = time.perf_counter()
editorArea.switchToTab(0)
app.processEvents()
t1 = time.perf_counter()
print(f"Switch to Tab 0: {(t1 - t0)*1000:.2f} ms")

t0 = time.perf_counter()
editorArea.switchToTab(1)
app.processEvents()
t1 = time.perf_counter()
print(f"Switch to Tab 1: {(t1 - t0)*1000:.2f} ms")

app.quit()
