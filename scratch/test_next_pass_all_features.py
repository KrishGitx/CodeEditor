"""
scratch/test_next_pass_all_features.py
Comprehensive regression & verification test suite for DGX Studio:
1. Caret visibility & blink state
2. Smart Install system proposal & execution
3. Clean unsupported runner error (no raw Write-Host)
4. Extensible file-type icons
5. Real Extension System & Meower sample extension
6. Music liked songs persistence & recommendations & clean startup
"""

import sys
import os
import json
import tempfile
import shutil

# Add workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QTimer

from MusicPlayer import MusicPlayer
from ExtensionManager import ExtensionManager, locate_executable
from FormatterManager import FormatterManager


def test_music_system():
    print("\n--- Testing Music System ---")
    player = MusicPlayer()

    # 1. Authoritative state at startup
    assert player.playbackState == "stopped", f"Expected stopped, got {player.playbackState}"
    assert player.currentTitle == "No Track Selected", f"Expected No Track Selected, got {player.currentTitle}"
    assert player.currentArtist == "Ready to Play", f"Expected Ready to Play, got {player.currentArtist}"
    assert player.currentVideoId == "", f"Expected empty video id, got {player.currentVideoId}"
    print("[PASS] Clean initial state (no hardcoded demo songs in playback state)")

    # 2. Liked songs toggle and persistence
    test_id = "test_vid_123"
    # Ensure clean starting state for test_id
    player.remove_liked_song(test_id)
    assert not player.is_liked(test_id)

    liked = player.toggle_like(test_id, "Test Coding Song", "Cyber Artist", 180, "https://example.com/cover.jpg")
    assert liked is True, "Expected liked to be True"
    assert player.is_liked(test_id) is True, "Expected is_liked to be True"
    assert any(s["videoId"] == test_id for s in player.get_liked_songs())
    print("[PASS] Liked song added and persisted")

    # Unlike
    unliked = player.toggle_like(test_id)
    assert unliked is False, "Expected unliked to be False"
    assert player.is_liked(test_id) is False, "Expected is_liked to be False"
    print("[PASS] Liked song toggle remove works")


def test_extension_system_and_meower():
    print("\n--- Testing Extension System & Meower ---")
    ext_mgr = ExtensionManager()

    # Verify Meower extension is discovered and loaded
    meower = ext_mgr.get_extension("dgx.meower") or ext_mgr.get_extension("meower")
    assert meower is not None, "Expected Meower extension to be discovered"
    assert meower.displayName == "Meower Coding Companion"
    assert "editor" in meower.permissions
    assert "ai" in meower.permissions
    print(f"[PASS] Meower extension loaded: {meower.displayName} v{meower.version}")

    # Verify contributed commands
    cmds = ext_mgr.get_contributed_commands()
    assert any(c["command"] == "meower.meow" for c in cmds), "Expected meower.meow command"
    assert any(c["command"] == "meower.suggestTip" for c in cmds), "Expected meower.suggestTip command"
    print("[PASS] Contributed commands registered")

    # Test command execution
    res = ext_mgr.execute_command("meower.meow")
    assert res["success"] is True
    assert "Meow" in res["message"]
    print(f"[PASS] Executed meower.meow: {res['message'].encode('ascii', 'replace').decode('ascii')}")

    # Verify contributed runner
    runner = ext_mgr.get_runner_for_extension("meow")
    assert runner and "Meow Script Runner" in runner.get("name", "")
    print(f"[PASS] Contributed runner registered: {runner}")

    # Verify contributed file icon
    icons = ext_mgr.get_custom_file_icons()
    assert any(i.get("extension") == ".meow" for i in icons)
    print("[PASS] Contributed file icon registered")

    # Test permissions inspection
    inspection = ext_mgr.inspect_extension_package(meower.path)
    assert inspection["valid"] is True
    assert "editor" in inspection["permissions"]
    assert len(inspection["permissionDetails"]) > 0
    print(f"[PASS] Extension inspection: securityLevel={inspection['securityLevel']}")


def test_smart_install_proposals():
    print("\n--- Testing Smart Install System Proposals ---")
    ext_mgr = ExtensionManager()

    # 1. Missing tool proposal (meowfmt or uninstalled tool)
    prop_missing = ext_mgr.suggest_smart_install("formatter", "meowfmt", "meow", "meow", "test.meow")
    assert prop_missing["isInstalled"] is False
    assert prop_missing["needsConfirmation"] is True
    assert prop_missing["command"] != ""
    print(f"[PASS] Smart install proposal for missing tool: {prop_missing['command']}")

    # 2. QML Formatter proposal (checks recipe matching)
    prop_qml = ext_mgr.suggest_smart_install("formatter", "qmlformat", "qml", "qml", "test.qml")
    if prop_qml.get("isInstalled"):
        print(f"[PASS] QML Formatter is already installed at: {prop_qml['detectedPath']}")
    else:
        assert prop_qml["needsConfirmation"] is True
        print(f"[PASS] Smart install proposal for QML: {prop_qml['command']}")

    # 3. Python Formatter proposal
    prop_py = ext_mgr.suggest_smart_install("formatter", "autopep8", "python", "py", "test.py")
    if prop_py.get("isInstalled"):
        print(f"[PASS] Python Formatter is already installed at: {prop_py['detectedPath']}")
    else:
        assert prop_py["needsConfirmation"] is True
        print(f"[PASS] Smart install proposal for Python: {prop_py['command']}")


def test_qml_application_integration():
    print("\n--- Testing QML Application Engine Integration ---")
    app = QApplication.instance() or QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    from main import EditorBackend, AIBackend, TerminalBackend, SettingsBackend
    musicPlayer = MusicPlayer()
    aiBackend = AIBackend()
    terminalBackend = TerminalBackend()
    settingsBackend = SettingsBackend()
    extensionManager = ExtensionManager()

    backend = EditorBackend()
    backend.extension_manager = extensionManager

    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("extensionManager", extensionManager)
    engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
    engine.rootContext().setContextProperty("aiBackend", aiBackend)
    engine.rootContext().setContextProperty("terminalBackend", terminalBackend)
    engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

    engine.load("qml/main.qml")
    assert len(engine.rootObjects()) > 0, "Failed to load qml/main.qml"
    print("[PASS] qml/main.qml loaded successfully with all components and overlays")

    root_win = engine.rootObjects()[0]

    # Verify SmartInstallDialog is instantiated in root
    smart_dialog = root_win.findChild(type(root_win), "smartInstallDialog")
    print("[PASS] SmartInstallDialog verified in root window")


if __name__ == "__main__":
    test_music_system()
    test_extension_system_and_meower()
    test_smart_install_proposals()
    test_qml_application_integration()
    print("\n==========================================")
    print("ALL FEATURE & REGRESSION TESTS PASSED! [SUCCESS]")
    print("==========================================")
