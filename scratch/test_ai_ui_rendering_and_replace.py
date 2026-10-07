import sys
import os

sys.path.insert(0, r"c:\Users\amazi\OneDrive\Documents\DGX")

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QObject

from main import EditorBackend
from AIBackend import AIBackend
from TerminalBackend import TerminalBackend
from SettingsBackend import SettingsBackend
from MusicPlayer import MusicPlayer

def test_ui_rendering():
    print("=" * 70)
    print("TESTING AI RESPONSE UI RENDERING & REPLACEMENT STATE")
    print("=" * 70)

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
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
    root_objects = engine.rootObjects()
    assert len(root_objects) > 0, "Failed to load qml/main.qml"

    comp = QQmlComponent(engine, "qml/ai/ChatMessageItem.qml")
    assert comp.status() == QQmlComponent.Ready, f"ChatMessageItem failed to load: {comp.errorString()}"

    # 1. Test [NO_CHANGE] response
    no_change_text = "The selected code has no bugs. It is already correct.\n\n[NO_CHANGE]"
    item_nc = comp.create()
    item_nc.setProperty("role", "assistant")
    item_nc.setProperty("isSelectionRequest", True)
    item_nc.setProperty("contentText", no_change_text)
    item_nc.setProperty("languageId", "cpp")

    segments_nc = item_nc.property("segments").toVariant()
    extracted_nc = item_nc.property("extractedCode")
    has_code_nc = item_nc.property("hasUsableCode")

    assert len(segments_nc) > 0, "Segments must not be empty for [NO_CHANGE]"
    assert extracted_nc == "", f"Extracted code must be empty for [NO_CHANGE], got: {extracted_nc}"
    assert has_code_nc is False, "hasUsableCode must be False for [NO_CHANGE]"
    print(f"[PASS] ChatMessageItem with [NO_CHANGE]: Explanation displayed ('{segments_nc[0]['text']}'), Replace disabled")

    # 2. Test Bare [NO_CHANGE] marker without extra text
    item_bare_nc = comp.create()
    item_bare_nc.setProperty("role", "assistant")
    item_bare_nc.setProperty("isSelectionRequest", True)
    item_bare_nc.setProperty("contentText", "[NO_CHANGE]")
    item_bare_nc.setProperty("languageId", "cpp")

    segments_bare_nc = item_bare_nc.property("segments").toVariant()
    assert len(segments_bare_nc) > 0, "Bare [NO_CHANGE] must produce a non-empty explanation segment"
    assert item_bare_nc.property("hasUsableCode") is False, "Bare [NO_CHANGE] hasUsableCode must be False"
    print(f"[PASS] ChatMessageItem with bare [NO_CHANGE]: Auto-supplied text: '{segments_bare_nc[0]['text']}'")

    # 3. Test [INSUFFICIENT_CONTEXT] response
    insuff_text = "The bug is in the loop boundary outside the selection.\n\n[INSUFFICIENT_CONTEXT]"
    item_ic = comp.create()
    item_ic.setProperty("role", "assistant")
    item_ic.setProperty("isSelectionRequest", True)
    item_ic.setProperty("contentText", insuff_text)
    item_ic.setProperty("languageId", "cpp")

    segments_ic = item_ic.property("segments").toVariant()
    extracted_ic = item_ic.property("extractedCode")
    has_code_ic = item_ic.property("hasUsableCode")

    assert len(segments_ic) > 0, "Segments must not be empty for [INSUFFICIENT_CONTEXT]"
    assert extracted_ic == "", f"Extracted code must be empty for [INSUFFICIENT_CONTEXT], got: {extracted_ic}"
    assert has_code_ic is False, "hasUsableCode must be False for [INSUFFICIENT_CONTEXT]"
    print(f"[PASS] ChatMessageItem with [INSUFFICIENT_CONTEXT]: Explanation displayed ('{segments_ic[0]['text']}'), Replace disabled")

    # 4. Test [REPLACEMENT_CODE] response
    repl_text = "I fixed the missing semicolon.\n\n[REPLACEMENT_CODE]\n```cpp\nint result = a + b;\n```\n\nThis completes the statement."
    item_repl = comp.create()
    item_repl.setProperty("role", "assistant")
    item_repl.setProperty("isSelectionRequest", True)
    item_repl.setProperty("contentText", repl_text)
    item_repl.setProperty("languageId", "cpp")

    segments_repl = item_repl.property("segments").toVariant()
    extracted_repl = item_repl.property("extractedCode")
    has_code_repl = item_repl.property("hasUsableCode")

    assert len(segments_repl) >= 2, f"Segments must contain text and code blocks, got {len(segments_repl)}"
    assert extracted_repl.strip() == "int result = a + b;", f"Extracted code mismatch: {extracted_repl}"
    assert has_code_repl is True, "hasUsableCode must be True for [REPLACEMENT_CODE]"
    print("[PASS] ChatMessageItem with [REPLACEMENT_CODE]: Full explanation and code block displayed, Replace enabled")

    # 5. Test Multiple Code Blocks with [REPLACEMENT_CODE]
    multi_text = (
        "Here is the issue:\n```cpp\nint x = divide(10, 0); // Crashes\n```\n\n"
        "Here is the fix:\n\n[REPLACEMENT_CODE]\n```cpp\nint divide(int a, int b) {\n    if (b == 0) return 0;\n    return a / b;\n}\n```"
    )
    item_multi = comp.create()
    item_multi.setProperty("role", "assistant")
    item_multi.setProperty("isSelectionRequest", True)
    item_multi.setProperty("contentText", multi_text)
    item_multi.setProperty("languageId", "cpp")

    extracted_multi = item_multi.property("extractedCode")
    assert "divide(10, 0)" not in extracted_multi, "Must not extract explanatory code before [REPLACEMENT_CODE]"
    assert "if (b == 0) return 0;" in extracted_multi, "Must extract the block after [REPLACEMENT_CODE]"
    print("[PASS] ChatMessageItem with multiple code blocks: Extracted only the block after [REPLACEMENT_CODE]")

    print("\n" + "=" * 70)
    print("ALL AI UI & EXTRACTION TESTS PASSED (100% PASS)")
    print("=" * 70)

if __name__ == "__main__":
    test_ui_rendering()
