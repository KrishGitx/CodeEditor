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
comp.setData(orig_qml.encode("utf-8"), base_url)
editorArea = comp.create()
editorArea.setProperty("width", 1200)
editorArea.setProperty("height", 800)

for _ in range(5): app.processEvents()

print("\n--- Detailed step-by-step profiling of EditorArea ---")
tabModel = editorArea.findChild(object, "") # let's access via JS

# Let's call loadFile and measure what happens inside
# We can evaluate JS snippets on editorArea
def eval_js(js_code):
    return engine.evaluate(js_code)

t0 = time.perf_counter()
editorArea.loadFile(os.path.abspath("test_data/file_a.py"), sample_text)
t1 = time.perf_counter()
print(f"loadFile JS invocation returned in: {(t1 - t0)*1000:.2f} ms")

# Now let's process events with high resolution
t_prev = time.perf_counter()
for i in range(20):
    t_start = time.perf_counter()
    app.processEvents()
    t_end = time.perf_counter()
    print(f"  processEvents #{i:2d}: {(t_end - t_start)*1000:7.2f} ms (elapsed since start: {(t_end - t0)*1000:7.2f} ms)")
    if (t_end - t_start) < 2.0 and i > 3:
        break

app.quit()
