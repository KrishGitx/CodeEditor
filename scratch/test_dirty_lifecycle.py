import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtQuickControls2 import QQuickStyle
from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
app.setApplicationName("DGX Studio")
app.setOrganizationName("DGX")

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
if not root_app:
    for err in comp.errors():
        print("QML Error:", err.toString())
    sys.exit(1)

editor = root_app.findChild(QObject, "editorArea")

tmp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".py")
tmp1.write(b"def file1():\n    return 1\n")
tmp1.close()

tmp2 = tempfile.NamedTemporaryFile(delete=False, suffix=".py")
tmp2.write(b"def file2():\n    return 2\n")
tmp2.close()

try:
    print("\n--- 1. Open existing saved file ---")
    backend.open_file(tmp1.name)
    QCoreApplication.processEvents()
    dirty0 = editor.isTabDirty(0)
    print(f"Tab 0 isDirty: {dirty0} (Expected: False)")
    assert dirty0 == False, "Tab 0 should not be dirty on initial open"

    print("\n--- 2. Type one character ---")
    ta = backend.qml_text_area
    ta.insert(0, "#")
    QCoreApplication.processEvents()
    dirty_after_type = editor.isTabDirty(0)
    print(f"Tab 0 isDirty after type: {dirty_after_type} (Expected: True)")
    assert dirty_after_type == True, "Tab 0 should be dirty after typing"

    print("\n--- 3. Save file ---")
    editor.saveCurrentFile()
    QCoreApplication.processEvents()
    dirty_after_save = editor.isTabDirty(0)
    print(f"Tab 0 isDirty after save: {dirty_after_save} (Expected: False)")
    assert dirty_after_save == False, "Tab 0 should not be dirty after saving"

    print("\n--- 4. Type again, then undo back to saved baseline ---")
    ta.insert(0, "x")
    QCoreApplication.processEvents()
    dirty_retype = editor.isTabDirty(0)
    print(f"Tab 0 isDirty after re-type: {dirty_retype} (Expected: True)")
    assert dirty_retype == True, "Tab 0 should be dirty after re-type"

    ta.undo()
    QCoreApplication.processEvents()
    dirty_after_undo = editor.isTabDirty(0)
    print(f"Tab 0 isDirty after undo to baseline: {dirty_after_undo} (Expected: False)")
    assert dirty_after_undo == False, "Tab 0 should not be dirty when undone back to saved content"

    print("\n--- 5. Create new untitled file ---")
    editor.createNewFile()
    QCoreApplication.processEvents()
    untitled_idx = editor.property("activeTabIndex")
    dirty_untitled = editor.isTabDirty(untitled_idx)
    print(f"Untitled tab isDirty: {dirty_untitled} (Expected: True)")
    assert dirty_untitled == True, "New untitled file should start dirty"

    print("\n--- 6. Switch back to Tab 0 ---")
    editor.switchToTab(0)
    QCoreApplication.processEvents()
    dirty0_again = editor.isTabDirty(0)
    print(f"Tab 0 isDirty after switching back: {dirty0_again} (Expected: False)")
    assert dirty0_again == False, "Tab 0 should still not be dirty after switching back"

    print("\n>>> ALL DIRTY-STATE LIFECYCLE TESTS PASSED! <<<")

finally:
    if backend.lsp_process:
        try: backend.lsp_process.terminate()
        except Exception: pass
    try: os.unlink(tmp1.name)
    except Exception: pass
    try: os.unlink(tmp2.name)
    except Exception: pass
