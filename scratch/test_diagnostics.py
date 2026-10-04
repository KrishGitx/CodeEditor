import sys, os, time
sys.path.insert(0, os.path.abspath("."))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, QObject, QMetaObject, Q_ARG
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtGui import QFontMetrics, QFont
from main import EditorBackend

app = QApplication.instance() or QApplication(sys.argv)
backend = EditorBackend()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)

component = QQmlComponent(engine)
component.loadUrl(QUrl.fromLocalFile("qml/components/EditorArea.qml"))
if component.isError():
    for err in component.errors():
        print("QML Error:", err.toString())
    sys.exit(1)
editor = component.create()
if not editor:
    print("Component create returned None")
    sys.exit(1)

def call_js(obj, func_name, *args):
    qargs = [Q_ARG("QVariant", a) for a in args]
    return QMetaObject.invokeMethod(obj, func_name, *qargs)

test_qml = """Item {
    property int a: 1

    Timer {
        interval: 1000

        Rectangle {
            width: 100
            height: 100
        }
    }
}"""

call_js(editor, "loadFile", "test_file.qml", test_qml)
app.processEvents()

active_pane = editor.property("activeEditorPane")
code_text_area = editor.property("codeTextArea")
editor_flickable = editor.property("editorFlickable")
font_prop = code_text_area.property("font")
fm = QFontMetrics(font_prop)

print(f"codeTextArea leftPadding: {code_text_area.property('leftPadding')}")
print(f"editorLineHeight: {editor.property('editorLineHeight')}")
print(f"charWidth (space advance): {editor.property('charWidth')}")
cached_widths_val = editor.property("cachedIndentLevelWidths")
if hasattr(cached_widths_val, "toVariant"):
    cached_widths = cached_widths_val.toVariant()
else:
    cached_widths = cached_widths_val
print(f"cachedIndentLevelWidths (first 5): {cached_widths[:5]}")

scopes_val = editor.property("activeScopeRanges")
if hasattr(scopes_val, "toVariant"):
    scopes = scopes_val.toVariant()
else:
    scopes = scopes_val
print(f"\nActive scopes ({len(scopes)}):")
for s in scopes:
    print(f"  startLine={s['startLine']}, endLine={s['endLine']}, level={s['level']}")

lines = test_qml.split("\n")
left_padding = code_text_area.property("leftPadding") - editor_flickable.property("contentX")
tab_size = 4

print("\n--- LINE BY LINE DIAGNOSTICS ---")
for l, line in enumerate(lines):
    trimmed = line.strip()
    cols = 0
    for ch in line:
        if ch == ' ':
            cols += 1
        elif ch == '\t':
            cols += tab_size - (cols % tab_size)
        else:
            break
    raw_indent = cols // tab_size if trimmed else -1
    
    # Calculate guide X for regular indent guides
    reg_x = []
    if trimmed:
        for lvl in range(1, cols // tab_size):
            w = cached_widths[lvl] if lvl < len(cached_widths) else lvl * cached_widths[1]
            reg_x.append((lvl, round(left_padding + w) + 0.5))
            
    # Calculate guide X for scope guides
    scope_x = []
    for sc in scopes:
        if sc['startLine'] + 1 <= l <= sc['endLine']:
            s_lvl = sc['level']
            w = cached_widths[s_lvl] if s_lvl < len(cached_widths) else s_lvl * cached_widths[1]
            sx = round(left_padding + w) + 0.5
            bracket = (l == sc['endLine'])
            scope_x.append((s_lvl, sx, "bracket" if bracket else "line"))
            
    # Actual text column X in TextArea
    actual_text_x = left_padding + fm.horizontalAdvance(" " * cols) if trimmed else None
    
    print(f"Line {l:2d}: '{line}'")
    print(f"   rawIndent={raw_indent}, actual_text_start_x={actual_text_x}")
    print(f"   Regular guide X: {reg_x}")
    print(f"   Scope guide X:   {scope_x}")
