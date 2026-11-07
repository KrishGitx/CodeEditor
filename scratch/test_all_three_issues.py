import sys, os
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QObject

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()

print("--- 1. Testing Theme and EditorArea compilation ---")
theme_comp = QQmlComponent(engine, os.path.abspath('qml/Theme.qml'))
assert theme_comp.isReady(), f"Theme failed: {theme_comp.errors()}"
theme = theme_comp.create()

editor_comp = QQmlComponent(engine, os.path.abspath('qml/components/EditorArea.qml'))
assert editor_comp.isReady(), f"EditorArea failed: {editor_comp.errors()}"
editor = editor_comp.create()
editor.setProperty('theme', theme)
print("PASS: EditorArea and Theme compiled and created cleanly.")

print("\n--- 2. Testing ISSUE 1: Zoom Functionality ---")
# Load a multi-line document
code = "\n".join([f"int line_{i} = {i};" for i in range(1, 100)])
editor.loadFile("test_zoom.cpp", code)
app.processEvents()

pane = editor.property('activeEditorPane')
assert pane is not None, "Active editor pane must exist"
flickable = editor.property('editorFlickable')
assert flickable is not None, "editorFlickable must exist"

# Check initial size
init_size = theme.property('editorFontSize')
assert init_size == 14, f"Expected initial fontSize 14, got {init_size}"
print(f"Initial editorFontSize: {init_size}")

# Scroll flickable down to line 20
flickable.setProperty('contentY', 360)
app.processEvents()
scrolled_y = flickable.property('contentY')
print(f"Scrolled contentY: {scrolled_y}")

# Zoom in to 16
editor.setEditorZoom(16)
app.processEvents()
new_size = theme.property('editorFontSize')
pane_size = pane.property('paneFontSize')
assert new_size == 16, f"Expected theme fontSize 16, got {new_size}"
assert pane_size == 16, f"Expected pane fontSize 16, got {pane_size}"
print(f"After zoom in to 16: theme.fontSize={new_size}, pane.paneFontSize={pane_size}")

# Check contentY is preserved near line 20 (not jumped to 0)
zoom_y = flickable.property('contentY')
print(f"contentY after zoom: {zoom_y}")
assert zoom_y > 300, f"Zoom caused unexpected jump to top: {zoom_y}"

# Zoom out to 12
editor.setEditorZoom(12)
app.processEvents()
out_size = theme.property('editorFontSize')
pane_out_size = pane.property('paneFontSize')
assert out_size == 12, f"Expected theme fontSize 12, got {out_size}"
assert pane_out_size == 12, f"Expected pane fontSize 12, got {pane_out_size}"
print(f"After zoom out to 12: theme.fontSize={out_size}, pane.paneFontSize={pane_out_size}")

# Repeated zoom cycles
for s in [13, 14, 15, 16, 15, 14]:
    editor.setEditorZoom(s)
    app.processEvents()
    assert theme.property('editorFontSize') == s
assert flickable.property('contentY') > 200, "Content must maintain steady viewport after repeated zooms"
print("PASS: Zoom-in and zoom-out work reliably with preserved scroll position and layout metrics.")

print("\n--- 3. Testing ISSUE 2: Editor Maximize in Main Window ---")
main_comp = QQmlComponent(engine, os.path.abspath('qml/main.qml'))
assert main_comp.isReady(), f"qml/main.qml failed: {main_comp.errors()}"
main_win = main_comp.create()
assert main_win is not None, "main_win must instantiate cleanly"

# Check initial panel states
assert main_win.property('editorMaximized') == False
init_exp_vis = main_win.property('explorerVisible')
init_term_vis = main_win.property('terminalVisible')
print(f"Initial states: explorerVisible={init_exp_vis}, terminalVisible={init_term_vis}, editorMaximized=False")

# Trigger editor maximization
main_win.toggleMaximizeEditor()
app.processEvents()

assert main_win.property('editorMaximized') == True, "editorMaximized must be true"
assert main_win.property('effectiveExplorerWidth') == 0, "Explorer must collapse"
assert main_win.property('effectiveRightWidth') == 0, "Right sidebar must collapse"
assert main_win.property('effectiveTerminalHeight') == 0, "Terminal must collapse"
print("PASS: Maximizing editor collapses all surrounding panels horizontally AND vertically.")

# Trigger unmaximize / restore
main_win.toggleMaximizeEditor()
app.processEvents()

assert main_win.property('editorMaximized') == False, "editorMaximized must be restored to false"
assert main_win.property('explorerVisible') == init_exp_vis, "explorerVisible must be restored"
assert main_win.property('terminalVisible') == init_term_vis, "terminalVisible must be restored"
print("PASS: Unmaximizing restores previous panel visibility.")

print("\n--- 4. Testing ISSUE 3: Indentation Guide Scope Accuracy ---")
# Test K&R style if-else-if with same line closing and opening braces
cpp_sample = """while (i != j) {
    if (lngstring[k] == strs[j][k]) {
        if (k < strs[j].size() - 1)
            k++;
    } else if (lngstring[k] != strs[j][k]) {
        lngstring = lngstring.substr(0, k);
        if (j > 0) {
            j--;
        }
        k = 0;
    } else {
        return 0;
    }
}"""

segs = editor.computeGuideSegmentsForText(cpp_sample).toVariant()
print(f"Computed {len(segs)} segments for cpp_sample:")
for s in segs:
    print(f"  Level {s['level']}: lines {s['startLine']+1} to {s['endLine']+1}, hasClosingBrace={s['hasClosingBrace']}")

# Level 1 segments:
# 1. if block: lines 2 to 5 (hasClosingBrace=True)
# 2. else if block: lines 5 to 11 (hasClosingBrace=True)
# 3. else block: lines 11 to 13 (hasClosingBrace=True)
lvl1_segs = [s for s in segs if s['level'] == 1]
assert len(lvl1_segs) == 3, f"Expected exactly 3 distinct level 1 segments (if, else if, else), got {len(lvl1_segs)}"

# Verify first block terminates at line 5 (the '} else if' line)
assert lvl1_segs[0]['startLine'] == 1 and lvl1_segs[0]['endLine'] == 4, f"if block must terminate on line 5: {lvl1_segs[0]}"
assert lvl1_segs[0]['hasClosingBrace'] == True

# Verify second block starts at line 5 and terminates at line 11 (the '} else' line)
assert lvl1_segs[1]['startLine'] == 4 and lvl1_segs[1]['endLine'] == 10, f"else if block must start on line 5 and end on line 11: {lvl1_segs[1]}"
assert lvl1_segs[1]['hasClosingBrace'] == True

# Verify third block starts at line 11 and terminates at line 13 (the '}' line)
assert lvl1_segs[2]['startLine'] == 10 and lvl1_segs[2]['endLine'] == 12, f"else block must start on line 11 and end on line 13: {lvl1_segs[2]}"
assert lvl1_segs[2]['hasClosingBrace'] == True
print("PASS: K&R same-line closing and opening braces create separate, non-overlapping guide segments.")

# Test Java try/catch/finally
java_sample = """try {
    doA();
} catch (IOException e) {
    doB();
} catch (Exception e) {
    doC();
} finally {
    cleanup();
}"""
java_segs = editor.computeGuideSegmentsForText(java_sample).toVariant()
assert len(java_segs) == 4, f"Expected 4 segments for try/catch/catch/finally, got {len(java_segs)}"
print("PASS: Java try/catch/finally correctly segmented into 4 distinct block scopes.")

# Test nested block containing comment/blank lines
nested_sample = """if (condition) {
    if (nestedCondition) {
        // inner comment
    }
} else if (anotherCondition) {
    // another comment
}"""
nested_segs = editor.computeGuideSegmentsForText(nested_sample).toVariant()
lvl1_nested = [s for s in nested_segs if s['level'] == 1]
assert len(lvl1_nested) == 1, f"Nested block must retain its guide even with comment-only body: {nested_segs}"
assert lvl1_nested[0]['startLine'] == 1 and lvl1_nested[0]['endLine'] == 3
print("PASS: Nested block with comment-only body correctly maintains its guide segment.")

# Test Allman style braces
allman_sample = """void test()
{
    if (a)
    {
        doSomething();
    }
    else if (b)
    {
        doSomethingElse();
    }
}"""
allman_segs = editor.computeGuideSegmentsForText(allman_sample).toVariant()
allman_lvl1 = [s for s in allman_segs if s['level'] == 1]
assert len(allman_lvl1) == 2, f"Allman style if / else if must produce 2 level-1 segments: {allman_segs}"
print("PASS: Allman style opening braces on separate lines handled correctly.")

print("\n==========================================")
print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
print("==========================================")
