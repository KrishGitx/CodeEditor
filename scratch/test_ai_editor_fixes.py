import sys
import os

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtCore import QCoreApplication, QObject, QUrl, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QJSEngine

def run_tests():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    
    # 1. Test CodeExtractor logic via QJSEngine
    js_engine = QJSEngine()
    
    with open("qml/ai/CodeExtractor.js", "r", encoding="utf-8") as f:
        js_code = f.read()
    
    js_code_clean = js_code.replace(".pragma library", "")
    js_engine.evaluate(js_code_clean)
    
    print("Testing CodeExtractor.js...")
    
    # Test 1: Python code block with explanation before and after
    res1 = js_engine.evaluate("""
        extractCodeFromMarkdown("Here is the explanation:\\n\\n```python\\ndef my_func():\\n    # line 1\\n\\n    return 42\\n```\\n\\nLet me know if this works!", "python");
    """).toString()
    expected1 = "def my_func():\n    # line 1\n\n    return 42"
    assert res1 == expected1, f"Failed test 1, got: {repr(res1)}"
    print("[PASS] Test 1: Single Python fence with explanation before & after extracted cleanly with exact blank lines & indentation")
    
    # Test 2: QML code block with indentation
    res2 = js_engine.evaluate("""
        extractCodeFromMarkdown("explanation\\n```qml\\nItem {\\n    id: root\\n    width: 100\\n}\\n```\\nmore explanation", "qml");
    """).toString()
    assert res2 == "Item {\n    id: root\n    width: 100\n}", f"Failed test 2, got: {repr(res2)}"
    print("[PASS] Test 2: QML fence with indentation preserved and surrounding text ignored")
    
    # Test 3: No language tag
    res3 = js_engine.evaluate("""
        extractCodeFromMarkdown("Here is code:\\n```\\nconsole.log('hello world');\\n```\\nEnd", "javascript");
    """).toString()
    assert res3 == "console.log('hello world');", f"Failed test 3, got: {repr(res3)}"
    print("[PASS] Test 3: Language-less code fence extracted")
    
    # Test 4: Multiple blocks with language preference (cpp vs python)
    multi_md = "Here is Python:\\n```python\\nprint('py')\\n```\\nAnd C++:\\n```cpp\\nstd::cout << 1;\\n```"
    res4_cpp = js_engine.evaluate(f'extractCodeFromMarkdown("{multi_md}", "cpp");').toString()
    assert res4_cpp == "std::cout << 1;", f"Failed test 4 cpp, got: {repr(res4_cpp)}"
    
    res4_py = js_engine.evaluate(f'extractCodeFromMarkdown("{multi_md}", "python");').toString()
    assert res4_py == "print('py')", f"Failed test 4 py, got: {repr(res4_py)}"
    print("[PASS] Test 4: Multiple code blocks preferred active language correctly")
    
    # Test 5: Unclosed code fence (streaming / truncated closing fence)
    unclosed_md = "Certainly! Here is the code:\\n```python\\ndef stream_func():\\n    return True"
    res5 = js_engine.evaluate(f'extractCodeFromMarkdown("{unclosed_md}", "python");').toString()
    assert res5 == "def stream_func():\n    return True", f"Failed test 5, got: {repr(res5)}"
    print("[PASS] Test 5: Unclosed streaming code fence extracted without outer explanation")
    
    # Test 6: Conversational text stripping when NO fences exist
    conv_md = "Here is the code:\\ndef add(a, b):\\n    return a + b\\n\\nHope this helps!"
    res6 = js_engine.evaluate(f'extractCodeFromMarkdown("{conv_md}", "python");').toString()
    assert res6 == "def add(a, b):\n    return a + b", f"Failed test 6, got: {repr(res6)}"
    print("[PASS] Test 6: Conversational header and footer stripped when no fences present")
    
    # 2. Test QML Loading & EditorArea integration
    print("\nTesting QML components loading...")
    engine = QQmlApplicationEngine()
    engine.addImportPath("qml")
    
    from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend
    
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
    print("[PASS] main.qml loaded successfully")
    
    editor_area = main_window.findChild(QObject, "editorArea")
    assert editor_area is not None, "editorArea component found"
    
    # Test 7: Verify initial state - No floating AI button merely because text is selected
    editor_area.createNewFile()
    code_text_area = editor_area.property("codeTextArea")
    assert code_text_area is not None, "codeTextArea found"
    
    original_doc = "def old_calc():\n    return 10\n\nprint('hello')\n"
    code_text_area.setProperty("text", original_doc)
    
    code_text_area.select(0, 29)
    assert editor_area.property("hasPendingAiReplacement") is False, "hasPendingAiReplacement must be False when text is just selected"
    print("[PASS] Test 7: Floating button is NOT shown merely because text is selected")
    
    # Test 8: Set pending AI replacement (simulating AI response completion)
    start_pos = 0
    end_pos = 29
    selected_snippet = "def old_calc():\n    return 10"
    replacement_code = "def new_calc():\n    return 42"
    
    editor_area.setPendingAiReplacement(start_pos, end_pos, replacement_code, selected_snippet)
    assert editor_area.property("hasPendingAiReplacement") is True, "hasPendingAiReplacement must be True after AI response"
    print("[PASS] Test 8: hasPendingAiReplacement becomes True only after AI response is generated")
    
    # User modifies or clears selection: pending replacement still anchors to saved original selection
    code_text_area.select(0, 0)
    assert editor_area.property("hasPendingAiReplacement") is True, "hasPendingAiReplacement remains True for saved selection"
    
    # Trigger replaceSelection
    res = editor_area.replaceSelection(start_pos, end_pos, replacement_code, selected_snippet)
    assert res is True, "replaceSelection succeeded"
    assert editor_area.property("hasPendingAiReplacement") is False, "hasPendingAiReplacement cleared after replacement"
    
    updated_doc = code_text_area.property("text")
    expected_doc = "def new_calc():\n    return 42\n\nprint('hello')\n"
    assert updated_doc == expected_doc, f"Expected {repr(expected_doc)}, got {repr(updated_doc)}"
    print("[PASS] Test 9: replaceSelection replaced only the specified selection range and hid the button")
    
    # Test Undo (undo insert and undo remove)
    code_text_area.undo()
    code_text_area.undo()
    doc_after_undo = code_text_area.property("text")
    assert doc_after_undo == original_doc, f"Expected {repr(original_doc)}, got {repr(doc_after_undo)}"
    print("[PASS] Test 10: Undo restored original text cleanly")
    
    # Test 11: Find/Search operates on codeTextArea and does not touch AI input
    editor_area.showFind(False)
    matches = editor_area.updateFindMatches("old_calc", False)
    match_list = matches.toVariant() if hasattr(matches, "toVariant") else list(matches)
    assert len(match_list) == 1, f"Expected 1 match, got {len(match_list)}"
    print("[PASS] Test 11: Find/Search verified on editor codeTextArea")
    
    print("\nALL AI/EDITOR UNIT & INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
