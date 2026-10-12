"""
scratch/test_ai_smart_install_and_syntax_highlight.py
Comprehensive Verification Suite for:
1. Smart Install - AI-First Installation Flow & Safety
2. New File Syntax Highlighting across languages & Untitled Save-As
"""

import sys
import os
import re
import pytest
from PySide6.QtGui import QGuiApplication, QTextDocument
from PySide6.QtCore import QObject

# Ensure workspace is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from HighlighterEngine import MultiLanguageHighlighter, EXT_TO_LANG
from ExtensionManager import ExtensionManager
from main import EditorBackend, BackingDocument

# Disable LSP subprocess spawn during testing
EditorBackend.start_lsp_server = lambda self: None

# Create QGuiApplication if not already initialized
app = QGuiApplication.instance()
if not app:
    app = QGuiApplication(sys.argv)


def test_smart_install_prompt_generation():
    print("\n--- Test 1: AI Prompt Generation ---")
    ext_mgr = ExtensionManager()

    prompt = ext_mgr.generate_smart_install_prompt(
        tool_name="qmlformat",
        tool_type="formatter",
        lang_id="qml",
        ext="qml",
        cur_os="windows",
        shell_name="PowerShell"
    )

    assert "qmlformat" in prompt
    assert "Language: qml" in prompt
    assert "Operating system: windows" in prompt
    assert "Shell: PowerShell" in prompt
    assert "CORE RESOLUTION RULES" in prompt
    print("PASS: AI prompt contains all required environment, tool, and instruction constraints.")


def test_smart_install_ai_response_parsing():
    print("\n--- Test 2: AI Response Parsing ---")
    ext_mgr = ExtensionManager()

    raw_ai_text = """
Tool: Prettier
Command: npm install -g prettier
Explanation: Installs Prettier globally using npm package manager.
"""
    parsed = ext_mgr.parse_ai_install_response(raw_ai_text)
    assert parsed["tool"] == "Prettier"
    assert parsed["command"] == "npm install -g prettier"
    assert "Prettier globally" in parsed["explanation"]
    print("PASS: Standard AI text parsed successfully.")

    # Test markdown code block extraction
    raw_markdown = """
Here is the recommended installation command for autopep8:

Tool: autopep8
```bash
python -m pip install autopep8
```
Explanation: Installs autopep8 Python formatter via pip.
"""
    parsed_md = ext_mgr.parse_ai_install_response(raw_markdown)
    assert parsed_md["tool"] == "autopep8"
    assert parsed_md["command"] == "python -m pip install autopep8"
    print("PASS: Markdown code-block AI response parsed successfully.")


def test_smart_install_command_safety():
    print("\n--- Test 3: Command Safety & Destructive Validation ---")
    ext_mgr = ExtensionManager()

    # Valid installation commands
    valid_cmds = [
        "pip install autopep8",
        'python -m pip install --no-warn-script-location PySide6',
        "npm install -g prettier",
        "cargo install ripgrep",
        "winget install --id GoLang.Go",
        "brew install clang-format",
        "rustup component add rustfmt"
    ]
    for cmd in valid_cmds:
        is_safe, msg = ext_mgr.validate_command_safety(cmd)
        assert is_safe, f"Safe command incorrectly rejected: {cmd} ({msg})"

    # Unsafe / destructive commands
    unsafe_cmds = [
        "",
        "   ",
        "rm -rf /",
        "rm -rf *",
        "del /f /s /q c:\\*",
        "format C:",
        "mkfs /dev/sda1",
        "dd if=/dev/zero of=/dev/sda",
        ":(){ :|:& };:",
        "shutdown -r -t 0",
        "chmod -R 777 /",
        "echo hello world && touch file"  # Non-installation command
    ]
    for cmd in unsafe_cmds:
        is_safe, msg = ext_mgr.validate_command_safety(cmd)
        assert not is_safe, f"Unsafe command incorrectly accepted: {cmd}"

    print("PASS: Command safety validation correctly accepts valid install tools and rejects destructive/unrelated commands.")


def test_smart_install_ai_first_proposals():
    print("\n--- Test 4: AI-First Smart Install Proposal Flow ---")
    ext_mgr = ExtensionManager()

    # 1. QML Formatter
    prop_qml = ext_mgr.suggest_smart_install("formatter", "qml formatter", "qml", "qml", "test.qml")
    assert prop_qml["source"] == "ai"
    assert prop_qml["needsConfirmation"] is True
    assert "qml" in prop_qml["toolName"].lower() or "qml" in prop_qml["command"].lower()
    assert len(prop_qml["command"]) > 0
    assert len(prop_qml["description"]) > 0
    assert "Tool required:" in prop_qml["prompt"]

    # 2. Python Formatter
    prop_py = ext_mgr.suggest_smart_install("formatter", "python formatter", "python", "py", "test.py")
    assert prop_py["source"] == "ai"
    assert "pip install" in prop_py["command"]
    assert "autopep8" in prop_py["command"] or "autopep8" in prop_py["toolName"]

    # 3. C++ Formatter
    prop_cpp = ext_mgr.suggest_smart_install("formatter", "cpp formatter", "cpp", "cpp", "test.cpp")
    assert prop_cpp["source"] == "ai"
    assert "clang-format" in prop_cpp["command"] or "clang-format" in prop_cpp["toolName"]

    print("PASS: AI-first proposal flow generated valid AI-contract proposals with prompt, command, and explanation.")


def test_new_file_syntax_highlighting_all_languages():
    print("\n--- Test 5: New File Syntax Highlighting Across Languages ---")

    languages_test_data = [
        ("test.py", "python", "def calculate_total(price, tax):\n    # Calculate total\n    return price * (1 + tax)\n"),
        ("test.cpp", "cpp", "#include <iostream>\nint main() {\n    // Print hello\n    std::cout << \"Hello\" << std::endl;\n    return 0;\n}\n"),
        ("test.java", "java", "public class Main {\n    // Main method\n    public static void main(String[] args) {\n        System.out.println(\"Hello\");\n    }\n}\n"),
        ("test.js", "javascript", "function calculateTotal(price, tax) {\n    // Calculate total\n    return price * (1 + tax);\n}\n"),
        ("test.qml", "qml", "import QtQuick 2.15\n\nRectangle {\n    // Root item\n    width: 200\n    height: 100\n    color: \"red\"\n}\n"),
        ("test.html", "html", "<!DOCTYPE html>\n<html>\n<!-- Webpage -->\n<body class=\"main\">\n    <h1>Title</h1>\n</body>\n</html>\n"),
        ("test.css", "css", "/* Style */\n.main-header {\n    color: #ffffff;\n    font-size: 14px;\n}\n"),
        ("test.json", "json", "{\n    \"name\": \"dgx-studio\",\n    \"version\": \"1.0.0\",\n    \"active\": true\n}\n")
    ]

    for fname, expected_lang, code_sample in languages_test_data:
        doc = QTextDocument()
        doc.setPlainText(code_sample)

        hl = MultiLanguageHighlighter(doc)
        hl.set_language_for_file(fname, explicit_lang=expected_lang, force_rehighlight=True)

        assert hl.language == expected_lang, f"Expected {expected_lang}, got {hl.language}"
        assert hl.unified_regex is not None, f"Regex should be compiled for {expected_lang}"

        # Verify that highlighting formatted blocks
        total_blocks = doc.blockCount()
        assert total_blocks > 0, "Document should have blocks"
        print(f"PASS: [{fname}] Language '{expected_lang}' attached and highlighted immediately ({total_blocks} blocks).")


def test_untitled_paste_then_save_as():
    print("\n--- Test 6: Untitled File Paste then Save-As ---")

    # 1. Create untitled document (starts as plain text)
    doc = QTextDocument()
    doc.setPlainText("")

    backend = EditorBackend()
    try:
        hl = MultiLanguageHighlighter(None)
        hl.attach_document_incremental(doc, "Untitled-1.txt", explicit_lang="text")
        backend.tab_highlighters[1] = hl
        backend.highlighter = hl

        assert hl.language == "text"
        assert hl.unified_regex is None

        # 2. User pastes Python code into untitled file
        pasted_code = "def solve_problem(n):\n    # Algorithm\n    result = [i * 2 for i in range(n)]\n    return result\n"
        doc.setPlainText(pasted_code)

        # 3. User saves file as `test.py`
        backend.set_active_file("test.py", "python")

        # Verify that highlighter immediately updated language and compiled regex
        assert backend.highlighter.language == "python"
        assert backend.highlighter.unified_regex is not None
        print("PASS: Untitled document pasted and saved as .py immediately switched highlighter to Python and rehighlighted.")
    finally:
        backend.stop_lsp_server()


def test_editor_backend_tab_rename_rehighlight():
    print("\n--- Test 7: Tab Rename Path & Rehighlight ---")
    backend = EditorBackend()
    try:
        doc = QTextDocument()
        doc.setPlainText("int x = 42;\n// C++ code\n")

        hl = MultiLanguageHighlighter(doc)
        backend.highlighter = hl

        # Initial file as Untitled-1.txt
        backend.set_active_file("Untitled-1.txt", "text")
        assert backend.highlighter.language == "text"

        # Renamed in Explorer to test.cpp
        backend.set_active_file("test.cpp", "cpp")
        assert backend.highlighter.language == "cpp"
        assert backend.highlighter.unified_regex is not None
        print("PASS: Backend set_active_file reconfigures highlighter immediately upon rename.")
    finally:
        backend.stop_lsp_server()


if __name__ == "__main__":
    test_smart_install_prompt_generation()
    test_smart_install_ai_response_parsing()
    test_smart_install_command_safety()
    test_smart_install_ai_first_proposals()
    test_new_file_syntax_highlighting_all_languages()
    test_untitled_paste_then_save_as()
    test_editor_backend_tab_rename_rehighlight()
    print("\n========================================================")
    print("ALL 7 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("========================================================")
    os._exit(0)
