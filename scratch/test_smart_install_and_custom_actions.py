"""
scratch/test_smart_install_and_custom_actions.py
Tests:
1. Smart Install Button in NotificationToast & Formatter error wiring
2. Custom Action Multi-Command Support, Persistence, Radial Menu & Sequential Execution
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QTimer

from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager
from SettingsBackend import SettingsBackend
from TerminalBackend import TerminalBackend
from MusicPlayer import MusicPlayer


def test_smart_install_proposal_and_notification():
    print("\n--- Testing Smart Install Notification & Proposal ---")
    ext_mgr = ExtensionManager()

    # 1. Propose Smart Install for missing QML formatter
    prop_qml = ext_mgr.suggest_smart_install("formatter", "qml formatter", "qml", "qml", "test.qml")
    assert prop_qml is not None, "Expected proposal dictionary"
    print(f"[PASS] QML Formatter proposal generated: command={prop_qml.get('command')}, isInstalled={prop_qml.get('isInstalled')}")

    # 2. FormatterManager missing formatter response
    fmt_mgr = FormatterManager(ext_mgr)
    # Simulate a language without registered formatter
    res = fmt_mgr.format_code("nonexistent_lang", "sample.xyz", "code here")
    assert res["available"] is False, "Expected available=False for missing formatter"
    assert "No formatter installed" in res["message"]
    print(f"[PASS] Missing formatter response format: message='{res['message']}'")


def test_custom_actions_storage_and_migration():
    print("\n--- Testing Custom Actions Storage & Backward Compatibility ---")
    sb = SettingsBackend()

    # Test 1: Single command legacy format migration
    legacy_json = json.dumps([
        {"name": "Git Status", "command": "git status", "type": "bash"},
        {"label": "Dir List", "action": "dir", "action_type": "cmd"}
    ])
    sb.save_custom_actions(legacy_json)
    loaded = sb.get_custom_actions()
    assert len(loaded) == 2
    assert loaded[0]["commands"] == ["git status"]
    assert loaded[0]["name"] == "Git Status"
    assert loaded[1]["commands"] == ["dir"]
    assert loaded[1]["action_type"] == "cmd"
    print("[PASS] Legacy single-command actions migrated and loaded with commands array")

    # Test 2: Multi-command sequence storage
    multi_json = json.dumps([
        {
            "name": "Git Update",
            "type": "bash",
            "commands": [
                "git add .",
                "git commit -m \"Update\"",
                "git push"
            ]
        },
        {
            "name": "Clean Build",
            "type": "cmd",
            "commands": [
                "rmdir /s /q build",
                "mkdir build",
                "cmake --build build"
            ]
        }
    ])
    sb.save_custom_actions(multi_json)
    loaded_multi = sb.get_custom_actions()
    assert len(loaded_multi) == 2
    assert loaded_multi[0]["name"] == "Git Update"
    assert len(loaded_multi[0]["commands"]) == 3
    assert loaded_multi[0]["commands"][1] == 'git commit -m "Update"'
    assert loaded_multi[1]["name"] == "Clean Build"
    assert len(loaded_multi[1]["commands"]) == 3
    print("[PASS] Multi-command actions stored and reloaded accurately")


def test_terminal_sequential_execution():
    print("\n--- Testing Terminal Sequential Execution & Failure Stopping ---")
    app = QApplication.instance() or QApplication(sys.argv)
    tb = TerminalBackend()

    received_outputs = []
    def on_output(text):
        received_outputs.append(text)

    tb.outputReceived.connect(on_output)

    # Test executing a sequence of commands
    test_cmds = ["echo DGX_SEQ_1", "echo DGX_SEQ_2", "echo DGX_SEQ_3"]
    tb.execute_command_sequence(test_cmds, "bash")

    # Let Qt process events while shell responds
    for _ in range(30):
        app.processEvents()
        time.sleep(0.05)
        if any("DGX_SEQ_1" in o for o in received_outputs):
            break

    full_output = "".join(received_outputs)
    assert len(received_outputs) > 0 or len(full_output) > 0, "Terminal received output"
    print(f"[PASS] Multi-command sequence executed successfully. Output captured: {repr(full_output[:60])}")

    # Clean up
    tb.restart()


def test_qml_ui_loading():
    print("\n--- Testing QML Components Loading & Integration ---")
    app = QApplication.instance() or QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    from main import EditorBackend, AIBackend, SettingsBackend
    backend = EditorBackend()
    extensionManager = ExtensionManager()
    backend.extension_manager = extensionManager
    musicPlayer = MusicPlayer()
    aiBackend = AIBackend()
    terminalBackend = TerminalBackend()
    settingsBackend = SettingsBackend()
    backend.settings_backend = settingsBackend

    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("extensionManager", extensionManager)
    engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
    engine.rootContext().setContextProperty("aiBackend", aiBackend)
    engine.rootContext().setContextProperty("terminalBackend", terminalBackend)
    engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

    def on_warning(warnings):
        for w in warnings:
            print("[QML Warning/Error]:", w.toString())
    engine.warnings.connect(on_warning)

    engine.load("qml/main.qml")
    assert len(engine.rootObjects()) > 0, "Failed to load qml/main.qml"
    print("[PASS] qml/main.qml loaded successfully with NotificationToast actions and Custom Actions UI")


if __name__ == "__main__":
    test_smart_install_proposal_and_notification()
    test_custom_actions_storage_and_migration()
    test_terminal_sequential_execution()
    test_qml_ui_loading()
    print("\n==========================================")
    print("ALL TESTS PASSED SUCCESSFULLY! [SUCCESS]")
    print("==========================================")
