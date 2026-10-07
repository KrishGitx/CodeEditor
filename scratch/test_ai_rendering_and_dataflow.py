import sys
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QUrl, QTimer

app = QApplication.instance() or QApplication(sys.argv)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import AIBackend as ai_mod
ai_mod.custom_api_available = False
from main import EditorBackend, AIBackend

def test_full_ai_rendering_and_dataflow():
    print("\n=======================================================")
    print("TEST: Full AI Response Rendering, Streaming & Dataflow")
    print("=======================================================")

    ai_backend = AIBackend()
    editor_backend = EditorBackend()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("aiBackend", ai_backend)
    engine.rootContext().setContextProperty("backend", editor_backend)

    # Load AIWorkspace
    comp = QQmlComponent(engine, QUrl.fromLocalFile(os.path.abspath("qml/ai/AIWorkspace.qml")))
    assert not comp.isError(), f"AIWorkspace load error: {comp.errorString()}"
    ai_ws = comp.create()
    assert ai_ws is not None, "Failed to create AIWorkspace"

    chat_model = ai_ws.findChild(object, "")  # access list model or check count
    # Let's inspect chatHistoryModel
    # In AIWorkspace.qml: chatHistoryModel has initial welcome message (count = 1)

    cpp_selection = "if (k < strs[j].size() - 1)\n    k++"
    start_pos = 10
    end_pos = 10 + len(cpp_selection)

    replacement_ready_events = []
    def on_replacement_ready(s, e, new_code, orig):
        replacement_ready_events.append({
            "start": s,
            "end": e,
            "new_code": new_code,
            "orig": orig
        })

    ai_ws.aiReplacementReady.connect(on_replacement_ready)

    # Trigger selection review
    ai_ws.askAboutSelection(cpp_selection, start_pos, end_pos, "cpp", "")

    # Process events to allow streaming and completion
    import time
    start_wait = time.time()
    while not replacement_ready_events and (time.time() - start_wait < 5.0):
        app.processEvents()
        time.sleep(0.05)

    print(f"Replacement ready events received: {len(replacement_ready_events)}")
    assert len(replacement_ready_events) >= 1, "Expected aiReplacementReady signal to be emitted"
    rep = replacement_ready_events[-1]
    print(f"Extracted replacement code:\n{rep['new_code']}")
    assert "k++;" in rep['new_code'], "Expected corrected semicolon in replacement code"
    assert rep['start'] == start_pos
    assert rep['end'] == end_pos

    # Test Chat Message item rendering
    qml_item_comp = QQmlComponent(engine, QUrl.fromLocalFile(os.path.abspath("qml/ai/ChatMessageItem.qml")))
    assert not qml_item_comp.isError(), f"ChatMessageItem load error: {qml_item_comp.errorString()}"

    # Verify rendering of response containing full explanation + replacement
    full_response = """The selected fragment has a missing semicolon in the loop step.

```cpp
// Diagnostic/Broken example:
k++
```

I corrected the semicolon while preserving the exact selection scope.

[REPLACEMENT_CODE]
```cpp
if (k < strs[j].size() - 1)
    k++;
```

The rest of the function logic is untouched."""

    msg_item = qml_item_comp.create()
    msg_item.setProperty("role", "assistant")
    msg_item.setProperty("isSelectionRequest", True)
    msg_item.setProperty("selectionStart", start_pos)
    msg_item.setProperty("selectionEnd", end_pos)
    msg_item.setProperty("originalSelectedText", cpp_selection)
    msg_item.setProperty("languageId", "cpp")
    msg_item.setProperty("contentText", full_response)

    segments = msg_item.property("segments")
    length = segments.property("length").toInt() if segments else 0
    print(f"Parsed chat segments count: {length}")
    assert length >= 4, f"Expected at least 4 segments (text, code, text, code, text), got {length}"

    for idx in range(length):
        seg = segments.property(idx)
        print(f"  Segment {idx}: type={seg.property('type').toString()}, text={repr(seg.property('text').toString()[:30])}, code={repr(seg.property('code').toString()[:30])}")

    extracted_code = msg_item.property("extractedCode")
    print(f"ChatMessageItem extractedCode:\n{extracted_code}")
    assert "k++;" in extracted_code
    assert "Diagnostic" not in extracted_code

    has_usable = msg_item.property("hasUsableCode")
    assert has_usable is True, "Expected hasUsableCode to be true"

    print("[PASS] ChatMessageItem properly renders explanation, example block, reasoning, and replacement block without truncation!")
    print("\n>>> ALL AI RENDERING & DATAFLOW TESTS PASSED (100%)! <<<\n")
    sys.exit(0)

if __name__ == "__main__":
    test_full_ai_rendering_and_dataflow()
