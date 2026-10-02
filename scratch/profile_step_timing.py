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

for _ in range(40):
    app.processEvents()
    time.sleep(0.05)

print("--- Starting Open Test ---")
t0 = time.perf_counter()
backend.open_file(os.path.abspath("test_data/file_a.py"))
t1 = time.perf_counter()
print(f"open_file python call: {(t1 - t0)*1000:.2f} ms")

t2 = time.perf_counter()
app.processEvents()
t3 = time.perf_counter()
print(f"first processEvents: {(t3 - t2)*1000:.2f} ms")

for i in range(5):
    ta = time.perf_counter()
    app.processEvents()
    tb = time.perf_counter()
    print(f"subsequent processEvents {i}: {(tb - ta)*1000:.2f} ms")

app.quit()
