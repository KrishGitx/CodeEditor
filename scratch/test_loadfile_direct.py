import sys, os, time
sys.path.insert(0, os.getcwd())

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import Qt, QMetaObject, Q_ARG
from PySide6.QtQuickControls2 import QQuickStyle

os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
app = QGuiApplication(sys.argv)
QQuickStyle.setStyle('Basic')

from main import EditorBackend
from MusicPlayer import MusicPlayer
from AIBackend import AIBackend
from TerminalBackend import TerminalBackend
from SettingsBackend import SettingsBackend

backend = EditorBackend()
musicPlayer = MusicPlayer()
aiBackend = AIBackend()
terminalBackend = TerminalBackend()
settingsBackend = SettingsBackend()
backend.settings_backend = settingsBackend

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
engine.rootContext().setContextProperty("aiBackend", aiBackend)
engine.rootContext().setContextProperty("terminalBackend", terminalBackend)
engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

engine.load("qml/main.qml")
root = engine.rootObjects()[0]
editorArea = root.findChild(object, "editorArea")

for _ in range(30):
    app.processEvents()
    time.sleep(0.05)

with open("test_data/file_a.py", "r", encoding="utf-8") as f:
    content = f.read()

print("\n--- Testing loadFile directly ---")
t0 = time.perf_counter()
QMetaObject.invokeMethod(editorArea, "loadFile", Qt.DirectConnection,
                         Q_ARG(str, os.path.abspath("test_data/file_a.py")),
                         Q_ARG(str, content))
t1 = time.perf_counter()
print(f"loadFile JS call: {(t1 - t0)*1000:.2f} ms")

t2 = time.perf_counter()
app.processEvents()
t3 = time.perf_counter()
print(f"processEvents after loadFile: {(t3 - t2)*1000:.2f} ms")

app.quit()
