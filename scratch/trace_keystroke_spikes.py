import sys, os, time, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QSurfaceFormat, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, QEvent, Qt as QtCore_Qt, QPointF, QPoint
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQuick import QQuickWindow
from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
fmt = QSurfaceFormat()
fmt.setAlphaBufferSize(8)
QSurfaceFormat.setDefaultFormat(fmt)
QQuickStyle.setStyle("Basic")

backend = EditorBackend()
musicPlayer = MusicPlayer()
aiBackend = AIBackend()
terminalBackend = TerminalBackend()
settingsBackend = SettingsBackend()
backend.settings_backend = settingsBackend

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
engine.rootContext().setContextProperty("extensionManager", backend.extension_manager)
engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
engine.rootContext().setContextProperty("aiBackend", aiBackend)
engine.rootContext().setContextProperty("terminalBackend", terminalBackend)
engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root_app = comp.create()
root_window = root_app if isinstance(root_app, QQuickWindow) else engine.rootObjects()[0]
root_window.show()
QCoreApplication.processEvents()

editor = root_app.findChild(QObject, "editorArea")

py_10000 = "\n".join([f"def py_func_10k_{i}(x, y):\n    val = x * {i}\n    return val" for i in range(3300)])

editor.loadFile("large_10k.py", py_10000)
QCoreApplication.processEvents()

ta = backend.qml_text_area
mid_pos = len(py_10000) // 2
ta.setProperty("cursorPosition", mid_pos)
QCoreApplication.processEvents()

print("\n--- DETAILED KEYSTROKE TRACE ON 10,000-LINE FILE ---")
for i in range(50):
    ch = chr(ord('a') + (i % 26))
    
    t0 = time.perf_counter()
    press = QKeyEvent(QEvent.KeyPress, QtCore_Qt.Key_A, QtCore_Qt.NoModifier, ch)
    QCoreApplication.sendEvent(root_window, press)
    t_press = time.perf_counter()
    
    release = QKeyEvent(QEvent.KeyRelease, QtCore_Qt.Key_A, QtCore_Qt.NoModifier, ch)
    QCoreApplication.sendEvent(root_window, release)
    t_release = time.perf_counter()
    
    QCoreApplication.processEvents()
    t_render = time.perf_counter()
    
    total = (t_render - t0) * 1000
    if total > 10.0:
        print(f"Key {i:2d} ('{ch}'): Total = {total:6.2f} ms | Press = {(t_press-t0)*1000:.2f} ms | Release = {(t_release-t_press)*1000:.2f} ms | Render = {(t_render-t_release)*1000:.2f} ms")
    else:
        # normal fast frame
        pass

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
