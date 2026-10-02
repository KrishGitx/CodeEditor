import sys, os, time
sys.path.insert(0, os.getcwd())

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import Qt, QMetaObject, Q_ARG, qInstallMessageHandler, QtMsgType
from PySide6.QtQuickControls2 import QQuickStyle

def qt_message_handler(mode, context, message):
    print(f"[QML Log] {message}")

qInstallMessageHandler(qt_message_handler)

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

for _ in range(30):
    app.processEvents()
    time.sleep(0.05)

print("\n--- OPEN FILE TRIGGERED ---")
backend.open_file(os.path.abspath("test_data/file_a.py"))

for i in range(10):
    t0 = time.perf_counter()
    app.processEvents()
    t1 = time.perf_counter()
    print(f"processEvents iter {i}: {(t1 - t0)*1000:.2f} ms")
    time.sleep(0.02)

app.quit()
