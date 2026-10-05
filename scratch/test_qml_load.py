import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QTimer

from HighlighterEngine import MultiLanguageHighlighter
from AIBackend import AIBackend
from TerminalBackend import TerminalBackend
from SettingsBackend import SettingsBackend
from MusicPlayer import MusicPlayer
from main import EditorBackend

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
def on_warning(warnings):
    for w in warnings:
        print("[QML Warning/Error]:", w.toString())
engine.warnings.connect(on_warning)

backend = EditorBackend()
musicPlayer = MusicPlayer()
aiBackend = AIBackend()
terminalBackend = TerminalBackend()
settingsBackend = SettingsBackend()
backend.settings_backend = settingsBackend

engine.rootContext().setContextProperty("backend", backend)
engine.rootContext().setContextProperty("extensionManager", backend.extension_manager)
engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
engine.rootContext().setContextProperty("aiBackend", aiBackend)
engine.rootContext().setContextProperty("terminalBackend", terminalBackend)
engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

engine.load("qml/main.qml")
if not engine.rootObjects():
    print("FAILED TO LOAD QML ROOT OBJECT")
    sys.exit(1)

print("SUCCESS: Root QML object loaded successfully!")
sys.exit(0)
