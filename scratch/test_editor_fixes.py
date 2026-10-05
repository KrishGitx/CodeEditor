import sys
import os
import json

# Ensure project root is in sys.path
PROJECT_ROOT = r"c:\Users\amazi\OneDrive\Documents\DGX"
sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject
from main import EditorBackend

def run_tests():
    print("========================================")
    print("RUNNING COMPREHENSIVE EDITOR FIX TESTS")
    print("========================================")

    # 1. Test EditorBackend.format_code
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    backend = EditorBackend()
    
    notifications = []
    backend.notificationRequested.connect(lambda msg, typ, title: notifications.append((msg, typ, title)))

    print("\n--- TEST 1: Format Command ---")
    # Python formatting with autopep8
    py_bad = "def foo(x,y):\n  a=1+2\n  return a\n"
    res_py = backend.format_code("python", "test.py", py_bad, 4)
    print("Python format result success:", res_py["success"])
    assert res_py["success"] == True
    assert "def foo(x, y):" in res_py["formatted"]
    print("[PASS] Python autopep8 formatting passed")

    # JSON formatting
    json_bad = '{"a":1,"b":[2,3],"c":{"d":4}}'
    res_json = backend.format_code("json", "test.json", json_bad, 2)
    print("JSON format result success:", res_json["success"])
    assert res_json["success"] == True
    assert '"a": 1' in res_json["formatted"]
    print("[PASS] JSON formatting passed")

    # Unsupported language / no formatter available
    notifications.clear()
    res_unknown = backend.format_code("brainfuck", "test.bf", "++>--", 4)
    print("Unsupported format result available:", res_unknown["available"])
    assert res_unknown["success"] == False
    assert res_unknown["available"] == False
    assert len(notifications) > 0
    print(f"[PASS] Notification emitted for unsupported language: {notifications[0]}")

    # 2. Test QML Engine load
    print("\n--- TEST 2: QML Application Load & Components ---")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    
    from AIBackend import AIBackend
    from TerminalBackend import TerminalBackend
    from MusicPlayer import MusicPlayer
    from SettingsBackend import SettingsBackend

    ai_backend = AIBackend()
    engine.rootContext().setContextProperty("aiBackend", ai_backend)
    engine.rootContext().setContextProperty("terminalBackend", TerminalBackend())
    engine.rootContext().setContextProperty("musicPlayer", MusicPlayer())
    engine.rootContext().setContextProperty("settingsBackend", SettingsBackend())

    qml_path = os.path.join(PROJECT_ROOT, "qml", "main.qml")
    engine.load(qml_path)

    assert len(engine.rootObjects()) > 0, "Failed to load main.qml"
    root_win = engine.rootObjects()[0]
    print("[PASS] main.qml loaded successfully with NotificationToast and updated EditorArea")

    # 3. Test Notification Toast function in QML
    print("\n--- TEST 3: Notification Toast in QML ---")
    root_win.showNotification("Testing Toast Notification", "info", "System", 3000)
    print("[PASS] showNotification triggered without errors")

    print("\n========================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("========================================")

if __name__ == "__main__":
    run_tests()
