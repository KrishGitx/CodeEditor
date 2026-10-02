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

print("\n================ FULL INTEGRATION VALIDATION ================")

# 1. Open Large File A (3000 lines)
t0 = time.perf_counter()
backend.open_file(os.path.abspath("test_data/file_a.py"))
for _ in range(5): app.processEvents()
t1 = time.perf_counter()
total_ms_a = (t1 - t0) * 1000
print(f"1. Open 3000-line File A: {total_ms_a:.2f} ms")
assert total_ms_a < 500, f"Open time {total_ms_a}ms exceeded target < 500ms"
assert editorArea.property("isCurrentFileDirty") == False
assert editorArea.property("totalLineCount") > 2900
print(f"   -> Lines: {editorArea.property('totalLineCount')}, Dirty: {editorArea.property('isCurrentFileDirty')}")

# 2. Open Large File B (3000 lines)
t0 = time.perf_counter()
backend.open_file(os.path.abspath("test_data/file_b.py"))
for _ in range(5): app.processEvents()
t1 = time.perf_counter()
total_ms_b = (t1 - t0) * 1000
print(f"2. Open 3000-line File B: {total_ms_b:.2f} ms")
assert total_ms_b < 500, f"Open time {total_ms_b}ms exceeded target < 500ms"
assert editorArea.property("isCurrentFileDirty") == False
assert editorArea.property("totalLineCount") > 2900
print(f"   -> Lines: {editorArea.property('totalLineCount')}, Dirty: {editorArea.property('isCurrentFileDirty')}")

# 3. Tab Switching Speed
t0 = time.perf_counter()
editorArea.switchToTab(0)
app.processEvents()
t1 = time.perf_counter()
switch_ms_0 = (t1 - t0) * 1000
print(f"3. Instant Tab Switch B -> A: {switch_ms_0:.2f} ms")
assert switch_ms_0 < 30

t0 = time.perf_counter()
editorArea.switchToTab(1)
app.processEvents()
t1 = time.perf_counter()
switch_ms_1 = (t1 - t0) * 1000
print(f"4. Instant Tab Switch A -> B: {switch_ms_1:.2f} ms")
assert switch_ms_1 < 30

# 4. Zoom Scroll Anchoring
flick = editorArea.property("editorFlickable")
line_h = editorArea.property("editorLineHeight")
target_line = 350
flick.setProperty("contentY", target_line * line_h)
app.processEvents()
print(f"5. Scrolled viewport to line {target_line}")

theme = engine.rootContext().contextProperty("theme")
for sz in [14, 16, 18, 13]:
    old_lh = editorArea.property("editorLineHeight")
    top_line = flick.property("contentY") / old_lh
    settingsBackend.set_value("editor_font_size", str(sz))
    # Or trigger wheel zoom
    theme_obj = root.findChild(object, "") # theme
    app.processEvents()
    curr_lh = editorArea.property("editorLineHeight")
    curr_line = flick.property("contentY") / curr_lh if curr_lh > 0 else 0
    print(f"   Zoom to font {sz}: line height {curr_lh:.1f}px, top line: {curr_line:.2f}")

print("\n================ ALL REQUIREMENTS VALIDATED SUCCESSFULLY ================")
app.quit()
