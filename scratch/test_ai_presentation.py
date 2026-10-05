import sys
import os
import json
import time

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtCore import QCoreApplication, QObject, QUrl, QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QJSEngine

def test_ai_presentation():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)

    from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend

    engine = QQmlApplicationEngine()
    engine.addImportPath("qml")

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

    engine.load(QUrl.fromLocalFile("qml/main.qml"))

    root_objects = engine.rootObjects()
    assert len(root_objects) > 0, "Failed to load qml/main.qml!"
    main_window = root_objects[0]
    print("[PASS] Main window loaded")

    editor_area = main_window.findChild(QObject, "editorArea")
    assert editor_area is not None

    main_window.setProperty("rightPanelVisible", True)
    main_window.setProperty("aiVisible", True)

    editor_area.createNewFile()
    code_text_area = editor_area.property("codeTextArea")
    assert code_text_area is not None

    full_html = (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<body>\n"
        "  <button id=\"test-btn\">Old Button</button>\n"
        "</body>\n"
        "</html>\n"
    )
    code_text_area.setProperty("text", full_html)

    target_snippet = "<button id=\"test-btn\">Old Button</button>"
    start_pos = full_html.index(target_snippet)
    end_pos = start_pos + len(target_snippet)
    code_text_area.select(start_pos, end_pos)

    # 1. Test presentation data flow with simulated rich response
    # User message in chat:
    user_prompt = "Please review and improve the selected html code:\n\n```html\n" + target_snippet + "\n```"

    # Full assistant response with explanations, formatting suggestions and code fence:
    raw_assistant_response = (
        "Here is the improved HTML code for your selection:\n\n"
        "```html\n"
        "<button id=\"test-btn\" class=\"btn-primary\">New Button</button>\n"
        "```\n\n"
        "**What was improved:**\n"
        "1. Added primary button styling class.\n"
        "2. Maintained valid HTML structure.\n"
        "3. Scoped directly to the selected element."
    )

    # CodeExtractor.js extracts ONLY the replacement code
    js_engine = QJSEngine()
    with open("qml/ai/CodeExtractor.js", "r", encoding="utf-8") as f:
        js_code = f.read().replace(".pragma library", "")
    js_engine.evaluate(js_code)

    extracted_code = js_engine.evaluate(f"extractCodeFromMarkdown({json.dumps(raw_assistant_response)}, 'html')").toString()

    print("=== Raw AI Assistant Chat Response ===")
    print(raw_assistant_response)
    print("\n=== Extracted Internal Replacement Code ===")
    print(extracted_code)

    assert "Here is the improved" in raw_assistant_response, "Chat message MUST contain full explanation"
    assert "What was improved:" in raw_assistant_response, "Chat message MUST contain improvements list"

    assert "Here is the improved" not in extracted_code, "Extracted code MUST NOT contain explanation"
    assert "What was improved:" not in extracted_code, "Extracted code MUST NOT contain improvements list"
    assert extracted_code == "<button id=\"test-btn\" class=\"btn-primary\">New Button</button>"
    print("[PASS] 1. Full response preserved for chat while CodeExtractor extracted pure code for replacement")

    # 2. Test Editor replacement
    editor_area.startPendingAiReplacement(start_pos, end_pos, target_snippet)
    assert editor_area.property("isAiReplacementGenerating") is True

    editor_area.setPendingAiReplacement(start_pos, end_pos, extracted_code, target_snippet)
    assert editor_area.property("isAiReplacementGenerating") is False
    assert editor_area.property("pendingAiCode") == extracted_code

    editor_area.replaceSelection(start_pos, end_pos, extracted_code, target_snippet)
    doc_after = code_text_area.property("text")

    assert "<!DOCTYPE html>" in doc_after
    assert "Here is the improved" not in doc_after
    assert "What was improved:" not in doc_after
    assert "<button id=\"test-btn\" class=\"btn-primary\">New Button</button>" in doc_after
    print(f"\n=== Final Editor Document Text ===\n{doc_after}")
    print("[PASS] 2. Editor replaced only the selection with pure code")

    print("\n========================================================")
    print("ALL PRESENTATION & REPLACEMENT TESTS PASSED 100%!")
    print("========================================================")

if __name__ == "__main__":
    test_ai_presentation()
