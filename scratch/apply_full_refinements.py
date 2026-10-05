import re

# 1. Update EditorArea.qml
editor_path = "qml/components/EditorArea.qml"
with open(editor_path, "r", encoding="utf-8") as f:
    editor_content = f.read()

# Remove bracketMatch properties
editor_content = re.sub(r'property int bracketMatchPos1:[^\n]*\n', '', editor_content)
editor_content = re.sub(r'property int bracketMatchPos2:[^\n]*\n', '', editor_content)

# Remove bracket matching rectangles overlay
bracket_rect_pattern = r'// Bracket Matching Highlight Overlays[\s\S]*?z:\s*14\s*\}\s*\}'
editor_content = re.sub(bracket_rect_pattern, '', editor_content)

# Remove hover handler
hover_handler_pattern = r'// Hover Information & Mouse tracking[\s\S]*?hoverDebounceTimer\.restart\(\);\s*\}\s*\}\s*\}'
editor_content = re.sub(hover_handler_pattern, '', editor_content)

# Remove hover overlays & timers and HoverTooltip and updateBracketMatching
hover_overlays_pattern = r'property var lastHoverPoint:[\s\S]*?HoverTooltip\s*\{\s*id:\s*hoverTooltip\s*\}'
editor_content = re.sub(hover_overlays_pattern, '', editor_content)

bracket_func_pattern = r'function updateBracketMatching\(\)\s*\{[\s\S]*?root\.bracketMatchPos2 = partnerPos;\s*\}'
editor_content = re.sub(bracket_func_pattern, '', editor_content)

# Remove calls to root.updateBracketMatching()
editor_content = editor_content.replace("root.updateBracketMatching();", "")

# Refine Selection Occurrence Highlighting to exact matches with subtle transparent light-blue styling
exact_occ_func = '''    function updateSelectionOccurrences() {
        if (!codeTextArea) {
            root.selectionOccurrences = [];
            return;
        }
        var sel = codeTextArea.selectedText;
        if (!sel || sel.trim().length < 2 || sel.indexOf("\\n") !== -1) {
            root.selectionOccurrences = [];
            return;
        }
        var doc = codeTextArea.text;
        var selStart = Math.min(codeTextArea.selectionStart, codeTextArea.selectionEnd);
        var selEnd = Math.max(codeTextArea.selectionStart, codeTextArea.selectionEnd);
        var occs = [];
        var idx = 0;
        var maxOcc = 100;
        var isWord = /^[a-zA-Z0-9_]+$/.test(sel);

        while ((idx = doc.indexOf(sel, idx)) !== -1) {
            if (idx !== selStart) {
                // If it's a word, enforce word boundary so substrings aren't highlighted
                var valid = true;
                if (isWord) {
                    if (idx > 0 && /[a-zA-Z0-9_]/.test(doc.charAt(idx - 1))) valid = false;
                    if (idx + sel.length < doc.length && /[a-zA-Z0-9_]/.test(doc.charAt(idx + sel.length))) valid = false;
                }
                if (valid) {
                    occs.push({ start: idx, end: idx + sel.length });
                    if (occs.length >= maxOcc) break;
                }
            }
            idx += sel.length;
        }
        root.selectionOccurrences = occs;
    }'''

occ_old_pattern = r'function updateSelectionOccurrences\(\)\s*\{[\s\S]*?root\.selectionOccurrences = occs;\s*\}'
editor_content = re.sub(occ_old_pattern, exact_occ_func, editor_content)

# Occurrence visual style: subtle transparent light-blue highlight with 0.15 opacity
editor_content = editor_content.replace(
    'color: theme ? theme.selectionHighlight : "#264f78"\n                                                                 opacity: 0.35\n                                                                 border.color: theme ? theme.borderGlow : "#60a5fa"',
    'color: "#38bdf8"\n                                                                 opacity: 0.14\n                                                                 border.color: "#38bdf840"'
)

with open(editor_path, "w", encoding="utf-8") as f:
    f.write(editor_content)
print("Updated EditorArea.qml successfully")
