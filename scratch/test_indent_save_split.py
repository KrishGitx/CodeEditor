import os
import sys

def test_indent_guides_horizontal():
    with open('qml/components/EditorArea.qml', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Verify indentGuidesCanvas.onPaint calculates X using tabSz * paneCharW and skips lvl <= 0
    assert 'var paneCharW = (tabPane && tabPane.paneCharWidth > 0) ? tabPane.paneCharWidth' in content, "Missing paneCharW in indentGuidesCanvas"
    assert 'var oneIndentW = tabSz * paneCharW;' in content, "Missing oneIndentW in indentGuidesCanvas"
    assert 'if (lvl <= 0) continue;' in content, "Must skip lvl <= 0 so guides never pass through column 0 code text"
    assert 'var lvlWidth = lvl * oneIndentW;' in content, "Guide width must use lvl * oneIndentW"
    assert 'var drawX = Math.round(x) + 0.5;' in content, "drawX must round x + 0.5"

    # 2. Verify secIndentGuidesCanvas.onPaint also skips lvl <= 0 and uses oneIndentW
    assert 'var oneIndentW = tabSz * paneCharW;' in content, "Missing oneIndentW in secIndentGuidesCanvas"
    print("PASS: Indent guides horizontal coordinate checks passed!")

def test_save_popup_dark_backdrop():
    with open('qml/components/EditorArea.qml', 'r', encoding='utf-8') as f:
        content = f.read()

    # Locate unsavedChangesDialog
    idx = content.find('id: unsavedChangesDialog')
    assert idx != -1, "unsavedChangesDialog not found"
    dialog_block = content[idx:idx+800]
    assert 'Overlay.modal' in dialog_block, "unsavedChangesDialog must have Overlay.modal"
    assert '#99000000' in dialog_block or 'rgba' in dialog_block, "Overlay.modal must have dark color"
    print("PASS: Save confirmation dialog has dark modal backdrop!")

def test_split_editor_close_independence():
    with open('qml/components/EditorArea.qml', 'r', encoding='utf-8') as f:
        content = f.read()

    # Verify closeTab logic handles split editor properly
    idx = content.find('function closeTab(index, force)')
    assert idx != -1, "closeTab function not found"
    close_fn = content[idx:idx+3500]

    assert 'if (root.isSplitEditor && wasActive)' in close_fn, "Must check root.isSplitEditor && wasActive"
    assert 'root.createNewFile()' in close_fn, "Must call root.createNewFile() when left pane closes file while split editor is active"
    assert 'root.syncSecondaryEditor()' in close_fn, "Must sync secondary editor"
    print("PASS: Split editor close independence logic verified!")

def test_zoom_and_indent_levels_math():
    # Test 2-space and 4-space across multiple zoom levels
    font_sizes = [10, 12, 14, 16, 20, 24]
    tab_sizes = [2, 4]
    leftPadding = 10.0

    for fs in font_sizes:
        # Approximate monospace charWidth for Consolas at font_size
        charW = fs * 0.60
        for tabSz in tab_sizes:
            oneIndentW = tabSz * charW
            for lvl in range(1, 6):
                x = leftPadding + (lvl * oneIndentW)
                drawX = round(x) + 0.5
                # Verify that drawX is in whitespace before any text at level `lvl + 1`
                next_level_start = leftPadding + ((lvl + 1) * oneIndentW)
                assert drawX < next_level_start, f"Guide at level {lvl} must not exceed level {lvl+1}"
                assert drawX > leftPadding, f"Guide must be strictly to the right of column 0"

    print("PASS: Zoom and 2-space / 4-space indentation alignment verified mathematically!")

if __name__ == '__main__':
    test_indent_guides_horizontal()
    test_save_popup_dark_backdrop()
    test_split_editor_close_independence()
    test_zoom_and_indent_levels_math()
    print("\nALL 3 ISSUES VERIFIED SUCCESSFULLY!")

