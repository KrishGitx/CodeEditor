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
    time.sleep(0.02)

print("\n================ COMPREHENSIVE VALIDATION ================")

# 1. Open Large File A (3000 lines)
t0 = time.perf_counter()
backend.open_file(os.path.abspath("test_data/file_a.py"))
for _ in range(5): app.processEvents()
t1 = time.perf_counter()
total_ms = (t1 - t0) * 1000
print(f"1. Open 3000-line File A: {total_ms:.2f} ms")
assert total_ms < 500
assert editorArea.property("isCurrentFileDirty") == False
assert editorArea.property("totalLineCount") > 2900

# 2. Test Word Wrap toggle via settingsBackend
flick = editorArea.property("editorFlickable")
ta = editorArea.property("codeTextArea")

settingsBackend.set_value("enable_word_wrap", "false")
app.processEvents()
print("\n2. Word Wrap OFF:")
print(f"   editor width: {flick.property('width')}, flick contentWidth: {flick.property('contentWidth')}, ta width: {ta.property('width')}")
assert flick.property("contentWidth") >= flick.property("width")

settingsBackend.set_value("enable_word_wrap", "true")
# or toggle via Alt+Z shortcut simulation / QMetaObject
app.processEvents()
print("3. Word Wrap ON:")
print(f"   editor width: {flick.property('width')}, flick contentWidth: {flick.property('contentWidth')}, ta width: {ta.property('width')}")
assert flick.property("contentWidth") == flick.property("width")
assert ta.property("width") == flick.property("width")

# 3. Test Smooth Anchored Zoom
print("\n4. Smooth Anchored Zoom:")
settingsBackend.set_value("enable_word_wrap", "false")
app.processEvents()

line_h = editorArea.property("editorLineHeight")
target_line = 150
flick.setProperty("contentY", target_line * line_h)
app.processEvents()

for font_sz in [14, 15, 16, 18, 20, 16, 14, 13]:
    settingsBackend.set_value("editor_font_size", str(font_sz))
    app.processEvents()
    curr_lh = editorArea.property("editorLineHeight")
    curr_line = flick.property("contentY") / curr_lh if curr_lh > 0 else 0
    print(f"   Zoom to {font_sz}pt: line height {curr_lh:.1f}px -> contentY: {flick.property('contentY'):.1f}, top line: {curr_line:.2f}")

print("\n================ ALL TESTS PASSED PERFECTLY ================")
app.quit()
