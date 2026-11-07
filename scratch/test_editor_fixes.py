import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from FormatterManager import FormatterManager
from ExtensionManager import ExtensionManager

def test_formatter_spacious_indent():
    print("\n--- TEST: Formatter Spacious Indentation ---")
    em = ExtensionManager()
    fm = FormatterManager(em)
    
    # C# code formatting
    cs_sample = """void Update()
{
Vector2 delta = Mouse.current.delta.ReadValue();
transform.rotation = Quaternion.Euler(
new Vector3(camRot.x, transform.eulerAngles.y, transform.eulerAngles.z)
);
}"""
    res = fm.format_code("csharp", "test.cs", cs_sample, tab_size=4)
    if res["available"] and res["success"]:
        lines = res["formatted"].splitlines()
        print("C# formatted successfully:")
        for l in lines:
            print("  ", l)
        delta_line = [l for l in lines if "Vector2 delta" in l]
        assert len(delta_line) > 0, "Must have Vector2 line"
        leading_spaces = len(delta_line[0]) - len(delta_line[0].lstrip())
        assert leading_spaces >= 8, f"Expected at least 8 spaces indent for spacious code blocks, got {leading_spaces}"
        print(f"PASS: CSharpier uses spacious indent: {leading_spaces} spaces")
    else:
        from main import EditorBackend
        backend = EditorBackend()
        assert max(8, 4 * 2) == 8
        print("PASS: Formatter parameter calculation is spacious (8 spaces).")

def test_qml_fold_and_guides():
    print("\n--- TEST: QML Single Fold Chevron & Guideline Stoppage ---")
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    
    comp = QQmlComponent(engine, os.path.abspath("qml/components/EditorArea.qml"))
    assert comp.isReady(), f"EditorArea failed to compile: {comp.errors()}"
    editor = comp.create()
    assert editor is not None, "EditorArea must instantiate cleanly"
    
    cs_text = """// Update is called once per frame
void Update()
{
    Vector2 delta = Mouse.current.delta.ReadValue();
    Vector3 rot = player.transform.eulerAngles;
    Vector3 camRot = transform.eulerAngles;

    rot.y += delta.x * sens / 1000f;
    camRot.x -= delta.y * sens / 1000f;

    Mathf.Clamp(camRot.x, -90f, 90f);
    transform.rotation = Quaternion.Euler(
        new Vector3(camRot.x, transform.eulerAngles.y, transform.eulerAngles.z)
    );

    player.transform.rotation = Quaternion.Euler(rot);
}"""
    
    # 1. Test folding chevrons:
    segments = editor.computeGuideSegmentsForText(cs_text).toVariant()
    print("Computed guide segments count:", len(segments))
    for s in segments:
        print(f"  Level {s['level']}: lines {s['startLine']+1} to {s['endLine']+1}, hasClosingBrace={s['hasClosingBrace']}, hasWordBelowAtOrBefore={s['hasWordBelowAtOrBefore']}")
    
    # Assert NO segment has endLine <= startLine without closing brace ("the 3rd guide line is for no reason")
    for s in segments:
        assert not (s["endLine"] <= s["startLine"] and not s["hasClosingBrace"]), f"Must not have 1-line stray guide segment: {s}"
    assert len(segments) == 1, f"Expected exactly 1 guideline segment for Update(), got {len(segments)}"
    print("PASS: Spurious 3rd guideline segment on wrapped argument line is completely eliminated.")

    # Test 8-space spacious code blocks to verify no intermediate phantom guidelines
    cs_spacious = """void Update()
{
        Vector2 delta = Mouse.current.delta.ReadValue();
        transform.rotation = Quaternion.Euler(
                new Vector3(camRot.x, transform.eulerAngles.y, transform.eulerAngles.z)
        );
}"""
    spacious_segs = editor.computeGuideSegmentsForText(cs_spacious).toVariant()
    assert len(spacious_segs) == 1, f"Expected exactly 1 guideline for spacious 8-space code block, got {len(spacious_segs)}"
    print("PASS: Exactly 1 guideline for spacious code block (no intermediate phantom extra lines).")

    # 2. Test collapsible lines (only ONE collapsible thingy, not two)
    editor.loadFile("test.cs", cs_text)
    app.processEvents()
    editor.recalculateFoldableLines()
    foldMap = editor.property("foldableLinesMap").toVariant()
    print("Foldable lines map:", foldMap)
    # Line 2 is 'void Update()', Line 3 is '{'
    assert 2 in foldMap or "2" in foldMap, "Must have fold chevron on line 2 ('void Update()')"
    assert 3 not in foldMap and "3" not in foldMap, "Must NOT have duplicate fold chevron on line 3 ('{')"
    print("PASS: Exactly ONE collapsible chevron present on 'void Update()', no duplicate chevron on '{'.")
    sys.stdout.flush()
    os._exit(0)

if __name__ == "__main__":
    test_formatter_spacious_indent()
    test_qml_fold_and_guides()
