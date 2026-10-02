import sys, os, time
sys.path.insert(0, os.getcwd())

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import Qt, QMetaObject, Q_ARG
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

# Load Theme first
theme_comp = QQmlComponent(engine, "qml/Theme.qml")
theme = theme_comp.create()
engine.rootContext().setContextProperty("theme", theme)

# Load standalone EditorArea
editor_comp = QQmlComponent(engine, "qml/components/EditorArea.qml")
editorArea = editor_comp.create()
editorArea.setProperty("width", 1200)
editorArea.setProperty("height", 800)

for _ in range(10):
    app.processEvents()

with open("test_data/file_a.py", "r", encoding="utf-8") as f:
    sample_text = f.read()

print("--- Testing Standalone EditorArea loadFile ---")
t0 = time.perf_counter()
editorArea.loadFile(os.path.abspath("test_data/file_a.py"), sample_text)
t1 = time.perf_counter()
print(f"loadFile JS: {(t1 - t0)*1000:.2f} ms")

t2 = time.perf_counter()
app.processEvents()
t3 = time.perf_counter()
print(f"processEvents: {(t3 - t2)*1000:.2f} ms")

app.quit()
