import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
from PySide6.QtCore import QUrl, QTimer, Qt, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
import CustomApi

def to_py(val):
    if hasattr(val, "toVariant"):
        return val.toVariant()
    return val

def test_full_indent_guides():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    main_qml_path = os.path.abspath("qml/main.qml")
    engine.load(QUrl.fromLocalFile(main_qml_path))

    root_objects = engine.rootObjects()
    assert len(root_objects) > 0, "Failed to load qml/main.qml!"
    main_window = root_objects[0]

    editor_area = main_window.findChild(QObject, "editorArea")

    print("[INFO] Testing QML computeGuideSegmentsForText & computeScopesForText...")

    # 1. Test nested scopes
    doc_nested = """function outer() {
    if (x) {
        doA();
    }
}"""
    segs_nested = to_py(editor_area.computeGuideSegmentsForText(doc_nested))
    print("Nested Segments:", segs_nested)
    assert len(segs_nested) >= 2, "Nested scopes segment count mismatch"
    assert any(s["startLine"] == 0 and s["endLine"] == 4 and s["level"] == 0 and s["hasClosingBrace"] for s in segs_nested)
    assert any(s["startLine"] == 1 and s["endLine"] == 3 and s["level"] == 1 and s["hasClosingBrace"] for s in segs_nested)
    print("[PASS] 1. Nested scopes verified in QML engine.")

    # 2. Test blank lines inside scopes
    doc_blank_inside = """if (foo) {
    code();


    moreCode();
}"""
    segs_blank_inside = to_py(editor_area.computeGuideSegmentsForText(doc_blank_inside))
    print("Blank Inside Segments:", segs_blank_inside)
    assert any(s["startLine"] == 0 and s["endLine"] == 5 and s["level"] == 0 and s["hasClosingBrace"] for s in segs_blank_inside)
    print("[PASS] 2. Blank lines inside scope continuous across all blank lines.")

    # 3. Test blank lines before first line
    doc_blank_before = """if (foo) {


    code();
}"""
    segs_blank_before = to_py(editor_area.computeGuideSegmentsForText(doc_blank_before))
    print("Blank Before Segments:", segs_blank_before)
    assert any(s["startLine"] == 0 and s["endLine"] == 4 and s["level"] == 0 and s["hasClosingBrace"] for s in segs_blank_before)
    print("[PASS] 3. Blank lines before first line starts at line 0.")

    # 4. Test closing bracket connection (blank lines before })
    doc_blank_after = """if (foo) {
    code();


}"""
    segs_blank_after = to_py(editor_area.computeGuideSegmentsForText(doc_blank_after))
    print("Blank After Segments:", segs_blank_after)
    assert any(s["startLine"] == 0 and s["endLine"] == 4 and s["level"] == 0 and s["hasClosingBrace"] for s in segs_blank_after)
    print("[PASS] 4. Closing bracket endpoint connects exactly to line 4.")

    # 5. Test comments inside scope
    doc_comments = """if (foo) {
    // Single line comment
    /* Multi line
       comment */
    code();
}"""
    segs_comments = to_py(editor_area.computeGuideSegmentsForText(doc_comments))
    print("Comments Segments:", segs_comments)
    assert any(s["startLine"] == 0 and s["endLine"] == 5 and s["level"] == 0 and s["hasClosingBrace"] for s in segs_comments)
    print("[PASS] 5. Comments inside scope do not break guide.")

    # 6. Test malformed / unclosed block
    doc_unclosed = """if (open) {
    code();"""
    segs_unclosed = to_py(editor_area.computeGuideSegmentsForText(doc_unclosed))
    print("Unclosed Segments:", segs_unclosed)
    assert any(s["startLine"] == 0 and s["endLine"] == 1 and s["level"] == 0 and not s["hasClosingBrace"] for s in segs_unclosed)
    print("[PASS] 6. Malformed/unclosed code handled safely without crashing.")

    # 7. Test mixed indentation (tabs & spaces)
    doc_mixed = "if (true) {\n\tcode1();\n        code2();\n}"
    segs_mixed = to_py(editor_area.computeGuideSegmentsForText(doc_mixed))
    print("Mixed Segments:", segs_mixed)
    assert any(s["startLine"] == 0 and s["endLine"] == 3 and s["level"] == 0 and s["hasClosingBrace"] for s in segs_mixed)
    print("[PASS] 7. Mixed tab/space indentation converted properly.")

    # 8. Test 3500-line performance in QML engine
    large_lines = []
    for i in range(500):
        large_lines.append(f"function fn_{i}() {{")
        large_lines.append("    // Comment")
        large_lines.append("    if (true) {")
        large_lines.append("        doSomething();")
        large_lines.append("")
        large_lines.append("    }")
        large_lines.append("}")
    large_doc = "\n".join(large_lines)

    t0 = time.time()
    large_segs = to_py(editor_area.computeGuideSegmentsForText(large_doc))
    dt = time.time() - t0
    print(f"[PASS] 8. 3500-line file parsed in QML engine in {dt*1000:.2f}ms. Total segments: {len(large_segs)}")
    assert dt < 0.25, f"Performance took too long: {dt}s"

    print("\n========================================================")
    print("ALL INDENTATION GUIDE GEOMETRY & RENDERING TESTS PASSED!")
    print("========================================================")
    QTimer.singleShot(100, app.quit)
    app.exec()

if __name__ == "__main__":
    test_full_indent_guides()
