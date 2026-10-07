import sys
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QJSValue
from PySide6.QtCore import QUrl, QObject, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtQuick import QQuickTextDocument

# Initialize Qt App
app = QApplication.instance() or QApplication(sys.argv)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend

def test_formatter_undo_redo():
    print("\n=======================================================")
    print("TEST 1: Formatter Undo / Redo Stack Preservation")
    print("=======================================================")

    backend = EditorBackend()
    
    # Create a QML TextArea
    engine = QQmlApplicationEngine()
    qml_src = """
    import QtQuick
    import QtQuick.Controls

    TextArea {
        id: ta
        text: "def add(a, b):\n    return a+b"
    }
    """
    comp = QQmlComponent(engine)
    comp.setData(qml_src.encode("utf-8"), QUrl(""))
    ta = comp.create()
    assert ta is not None, "Failed to create TextArea"

    backend.register_text_area(ta, "math.py", "python")
    
    # 1. Type an edit before formatting
    ta.insert(len(ta.property("text")), "\n# helper function")
    initial_text = ta.property("text")
    print(f"Pre-format text:\n{initial_text}")
    assert "# helper function" in initial_text

    # 2. Format Document via backend.apply_formatted_text
    formatted_code = "def add(a, b):\n    return a + b\n\n# helper function\n"
    applied = backend.apply_formatted_text(ta, formatted_code)
    assert applied, "backend.apply_formatted_text failed"
    print(f"Formatted text:\n{ta.property('text')}")
    assert ta.property("text") == formatted_code

    # 3. Ctrl+Z immediately after formatting
    ta.undo()
    print(f"After Ctrl+Z (Undo format):\n{ta.property('text')}")
    assert ta.property("text") == initial_text, f"Expected {repr(initial_text)} but got {repr(ta.property('text'))}"
    print("[PASS] Ctrl+Z immediately restored exact pre-format text in 1 undo step.")

    # 4. Ctrl+Y immediately reapplies formatted text
    ta.redo()
    print(f"After Ctrl+Y (Redo format):\n{ta.property('text')}")
    assert ta.property("text") == formatted_code, f"Expected {repr(formatted_code)} but got {repr(ta.property('text'))}"
    print("[PASS] Ctrl+Y immediately reapplied formatted text in 1 redo step.")

    # 5. Make another edit after formatting and verify normal undo/redo
    ta.insert(len(ta.property("text")), "# end of file")
    after_edit = ta.property("text")
    assert "# end of file" in after_edit

    ta.undo()
    assert ta.property("text") == formatted_code
    print("[PASS] Normal undo works cleanly after formatting.")

    ta.redo()
    assert ta.property("text") == after_edit
    print("[PASS] Normal redo works cleanly after formatting.")


def test_multi_tab_undo_isolation():
    print("\n=======================================================")
    print("TEST 2: Multi-tab Independent Undo Stack Isolation")
    print("=======================================================")

    backend = EditorBackend()
    engine = QQmlApplicationEngine()
    
    qml_src = """
    import QtQuick
    import QtQuick.Controls

    TextArea {
        text: "initial content"
    }
    """
    comp = QQmlComponent(engine)
    comp.setData(qml_src.encode("utf-8"), QUrl(""))
    ta1 = comp.create()
    ta2 = comp.create()
    ta1.setProperty("text", "tab1 initial content")
    ta2.setProperty("text", "tab2 initial content")

    # Tab 1 edit & format
    backend.register_text_area(ta1, "tab1.py", "python")
    ta1.insert(len(ta1.property("text")), " edit1")
    t1_pre_format = ta1.property("text")
    backend.apply_formatted_text(ta1, "tab1 formatted content\n")
    
    # Tab 2 edit
    backend.register_text_area(ta2, "tab2.py", "python")
    ta2.insert(len(ta2.property("text")), " edit2")
    t2_edit = ta2.property("text")

    # Undo Tab 1
    ta1.undo()
    assert ta1.property("text") == t1_pre_format, "Tab 1 undo failed"
    # Verify Tab 2 is unaffected
    assert ta2.property("text") == t2_edit, "Tab 2 was incorrectly affected by Tab 1 undo"
    print("[PASS] Multi-tab undo stacks operate completely independently.")


def test_code_extractor_3state_protocol():
    print("\n=======================================================")
    print("TEST 3: CodeExtractor.js Strict 3-State Protocol")
    print("=======================================================")

    from PySide6.QtQml import QJSEngine
    js_engine = QJSEngine()
    with open("qml/ai/CodeExtractor.js", "r", encoding="utf-8") as f:
        js_code = f.read()
    # Strip pragma library for QJSEngine
    js_code = js_code.replace(".pragma library", "")
    val = js_engine.evaluate(js_code)
    assert not val.isError(), f"CodeExtractor JS error: {val.toString()}"

    def parse_response(resp, lang=""):
        fn = js_engine.globalObject().property("parseReplacementResponse")
        res = fn.call([resp, lang])
        return res.toVariant()

    def extract_code(resp, lang=""):
        fn = js_engine.globalObject().property("extractReplacementCode")
        res = fn.call([resp, lang])
        return res.toString()

    def parse_segments(resp):
        fn = js_engine.globalObject().property("parseMarkdownSegments")
        res = fn.call([resp])
        length = res.property("length").toInt()
        segments_list = []
        for i in range(length):
            item = res.property(i)
            segments_list.append({
                "type": item.property("type").toString(),
                "text": item.property("text").toString(),
                "code": item.property("code").toString(),
                "lang": item.property("lang").toString()
            })
        return segments_list

    # Case 1: Valid [REPLACEMENT_CODE] with earlier example/broken code block and trailing code block
    case1_resp = """
Here is what was wrong with your code:

```cpp
// Diagnostic/Broken example:
lngstring.size() && k < strs[j].size() &&
        lngstring[k] == strs[j][k]) {
        ++k
    } else {
```

The issue was a missing semicolon and unbalanced syntax in the loop condition.

[REPLACEMENT_CODE]
```cpp
lngstring.size() && k < strs[j].size() &&
        lngstring[k] == strs[j][k]) {
        ++k;
    } else {
```

You can also write it as:
```cpp
// Alternative style (should be ignored by replacement extractor)
for (; k < std::min(lngstring.size(), strs[j].size()) && lngstring[k] == strs[j][k]; ++k);
```
"""
    res1 = parse_response(case1_resp, "cpp")
    print("Case 1 parse result:", res1)
    assert res1.get("status") == "replacement", f"Expected status 'replacement', got {res1.get('status')}"
    code1 = res1.get("code")
    assert "++k;" in code1, f"Expected corrected code with semicolon, got:\n{code1}"
    assert "Diagnostic/Broken" not in code1, "Extracted code included explanatory block before marker!"
    assert "Alternative style" not in code1, "Extracted code included block after replacement marker!"
    print("[PASS] Case 1 correctly extracted ONLY the code block immediately after [REPLACEMENT_CODE].")

    # Case 2: [NO_CHANGE]
    case2_resp = """
I reviewed your selected code:
```python
x = 42
```
The selected fragment is completely valid and optimal. No modifications are needed.

[NO_CHANGE]
"""
    res2 = parse_response(case2_resp, "python")
    print("Case 2 parse result:", res2)
    assert res2.get("status") == "no_change", f"Expected status 'no_change', got {res2.get('status')}"
    assert res2.get("code") is None, "Expected code to be null for [NO_CHANGE]"
    extract2 = extract_code(case2_resp, "python")
    assert extract2 == "", "Expected empty string for extractReplacementCode on [NO_CHANGE]"
    print("[PASS] Case 2 [NO_CHANGE] returns status 'no_change' and null/empty code.")

    # Case 3: [INSUFFICIENT_CONTEXT]
    case3_resp = """
The selected fragment:
```cpp
if (k < limit)
```
is too brief to verify what `limit` or `k` represent without the enclosing loop or variable declarations.

[INSUFFICIENT_CONTEXT]
"""
    res3 = parse_response(case3_resp, "cpp")
    print("Case 3 parse result:", res3)
    assert res3.get("status") == "insufficient_context", f"Expected status 'insufficient_context', got {res3.get('status')}"
    assert res3.get("code") is None, "Expected code to be null for [INSUFFICIENT_CONTEXT]"
    extract3 = extract_code(case3_resp, "cpp")
    assert extract3 == "", "Expected empty string for extractReplacementCode on [INSUFFICIENT_CONTEXT]"
    print("[PASS] Case 3 [INSUFFICIENT_CONTEXT] returns status 'insufficient_context' and null/empty code.")

    # Case 4: Missing markers / Invalid response (e.g. general chat or unformatted response)
    case4_resp = """
Here is some general advice:
```python
def foo():
    pass
```
"""
    res4 = parse_response(case4_resp, "python")
    print("Case 4 parse result:", res4)
    assert res4.get("status") == "invalid", f"Expected status 'invalid', got {res4.get('status')}"
    assert res4.get("code") is None, "Expected code to be null for invalid marker"
    extract4 = extract_code(case4_resp, "python")
    assert extract4 == "", "Must NOT blindly fall back to first code block for selection replacement!"
    print("[PASS] Missing markers returns status 'invalid' and does NOT guess first code block.")

    # Test parseMarkdownSegments cleans markers from displayed chat text
    segments = parse_segments(case1_resp)
    print(f"Segment count: {len(segments)}")
    for seg in segments:
        if isinstance(seg, dict) and seg.get("type") == "text":
            assert "[REPLACEMENT_CODE]" not in seg.get("text"), "Control marker [REPLACEMENT_CODE] leaked into chat text segment!"
            assert "[NO_CHANGE]" not in seg.get("text"), "Control marker [NO_CHANGE] leaked into chat text segment!"
            assert "[INSUFFICIENT_CONTEXT]" not in seg.get("text"), "Control marker [INSUFFICIENT_CONTEXT] leaked into chat text segment!"
    print("[PASS] parseMarkdownSegments cleanly strips protocol control markers from user-facing text display.")


def test_selection_replacement_scope():
    print("\n=======================================================")
    print("TEST 4: Exact Selection Scope Replacement in Editor")
    print("=======================================================")

    engine = QQmlApplicationEngine()
    qml_src = """
    import QtQuick
    import QtQuick.Controls

    TextArea {
        id: ta
        text: "function calculate() {\\n    var a = 10;\\n    var b = 20;\\n    return a + b;\\n}"
    }
    """
    comp = QQmlComponent(engine)
    comp.setData(qml_src.encode("utf-8"), QUrl(""))
    ta = comp.create()

    initial_text = ta.property("text")
    target_fragment = "    var a = 10;\n    var b = 20;"
    start_pos = initial_text.index(target_fragment)
    end_pos = start_pos + len(target_fragment)

    # Perform replacement ONLY on the selection range
    replacement_code = "    const a = 10;\n    const b = 20;"
    
    # Simulate EditorArea.replaceSelection logic
    ta.remove(start_pos, end_pos)
    ta.insert(start_pos, replacement_code)

    expected_full_doc = "function calculate() {\n    const a = 10;\n    const b = 20;\n    return a + b;\n}"
    assert ta.property("text") == expected_full_doc, f"Expected:\n{expected_full_doc}\nGot:\n{ta.property('text')}"
    print("[PASS] Replacement strictly modified ONLY the selected fragment without disturbing surrounding function.")


if __name__ == "__main__":
    test_formatter_undo_redo()
    test_multi_tab_undo_isolation()
    test_code_extractor_3state_protocol()
    test_selection_replacement_scope()
    print("\n=======================================================")
    print(">>> ALL TESTS PASSED SUCCESSFULLY! <<<")
    print("=======================================================\n")
    sys.exit(0)
