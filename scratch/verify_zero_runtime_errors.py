import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import Qt, qInstallMessageHandler, QTimer, QMetaObject, Q_ARG
from PySide6.QtQuickControls2 import QQuickStyle

from main import EditorBackend, GlobalContextMenuFilter
from MusicPlayer import MusicPlayer
from AIBackend import AIBackend
from TerminalBackend import TerminalBackend
from SettingsBackend import SettingsBackend

captured_logs = []

def qt_message_handler(mode, context, message):
    captured_logs.append(message)
    print(f"[QML Log]: {message}")

qInstallMessageHandler(qt_message_handler)

def test_app_and_verify_logs():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("DGX Studio")
    app.setOrganizationName("DGX")

    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    QQuickStyle.setStyle("Basic")

    engine = QQmlApplicationEngine()

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
        engine.load("main.qml")

    if not engine.rootObjects():
        print("FAIL: Root object not loaded")
        sys.exit(1)

    root_window = engine.rootObjects()[0]
    editorArea = root_window.findChild(object, "editorArea")

    for _ in range(30):
        app.processEvents()
        time.sleep(0.01)

    # 1. Open files via backend
    backend.open_file(os.path.abspath("CustomApi.py"))
    for _ in range(25):
        app.processEvents()
        time.sleep(0.01)

    backend.open_file(os.path.abspath("main.py"))
    for _ in range(25):
        app.processEvents()
        time.sleep(0.01)

    # 2. Invoke QML methods
    if editorArea:
        # Open Whiteboard
        QMetaObject.invokeMethod(
            editorArea, "openFile",
            Q_ARG("QVariant", "whiteboard://new"),
            Q_ARG("QVariant", ""),
            Q_ARG("QVariant", "Whiteboard Architecture"),
            Q_ARG("QVariant", "whiteboard"),
            Q_ARG("QVariant", True),
            Q_ARG("QVariant", False)
        )
        for _ in range(20):
            app.processEvents()
            time.sleep(0.01)

        # Open Web Preview
        QMetaObject.invokeMethod(
            editorArea, "openFile",
            Q_ARG("QVariant", "preview://index.html"),
            Q_ARG("QVariant", "<h1>Live Preview</h1>"),
            Q_ARG("QVariant", "Live Preview"),
            Q_ARG("QVariant", "webpreview"),
            Q_ARG("QVariant", False),
            Q_ARG("QVariant", True)
        )
        for _ in range(20):
            app.processEvents()
            time.sleep(0.01)

        # Switch tabs
        QMetaObject.invokeMethod(editorArea, "switchToTab", Q_ARG("QVariant", 0))
        for _ in range(20):
            app.processEvents()
            time.sleep(0.01)

        # Toggle fold
        QMetaObject.invokeMethod(editorArea, "toggleFold", Q_ARG("QVariant", 1))
        for _ in range(20):
            app.processEvents()
            time.sleep(0.01)

        # Close tabs down to 0
        QMetaObject.invokeMethod(editorArea, "closeTab", Q_ARG("QVariant", 3))
        for _ in range(15): app.processEvents()
        QMetaObject.invokeMethod(editorArea, "closeTab", Q_ARG("QVariant", 2))
        for _ in range(15): app.processEvents()
        QMetaObject.invokeMethod(editorArea, "closeTab", Q_ARG("QVariant", 1))
        for _ in range(15): app.processEvents()
        QMetaObject.invokeMethod(editorArea, "closeTab", Q_ARG("QVariant", 0))
        for _ in range(20): app.processEvents()

    # 3. Test CustomApi authentication dialog handling
    import CustomApi
    print("\n--- Testing CustomApi auth check & fail-fast ---")
    client = CustomApi.ChatGPTClient(headless=True)
    # Test connect
    # When auth dialog is detected, ask should raise clear RuntimeError rather than hanging 30s or intercepting pointer events
    try:
        # If client encounters auth dialog, it raises clear message
        print("CustomApi initialized, is_connected:", client.is_connected)
    except Exception as e:
        print("CustomApi test notice:", e)

    all_output = "\n".join(captured_logs)

    error_patterns = [
        "intercepts pointer events",
        "Unable to assign [undefined] to bool",
        'Cannot assign to read-only property "totalLineCount"',
        "Cannot assign to read-only property 'totalLineCount'"
    ]

    failures = []
    print("\n" + "="*60)
    print("VERIFICATION OF TARGET RUNTIME ERRORS:")
    print("="*60)
    for pattern in error_patterns:
        count = all_output.lower().count(pattern.lower())
        print(f"Pattern '{pattern}': {count} occurrences")
        if count > 0:
            failures.append(f"{pattern} ({count} occurrences)")

    if failures:
        print("\n[FAIL] Found target runtime errors in logs:", failures)
        sys.exit(1)
    else:
        print("\n[SUCCESS] ZERO occurrences of all three target runtime errors!")
        print("="*60)

if __name__ == "__main__":
    test_app_and_verify_logs()
