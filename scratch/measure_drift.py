import sys, os
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

test_doc = """A
    B
        C
            D
                E
                    F
                        G
                            H"""

call_js(editor, "loadFile", "test_drift.qml", test_doc)
app.processEvents()

active_pane = editor.property("activeEditorPane")
code_text_area = editor.property("codeTextArea")
font_prop = code_text_area.property("font")
left_pad = code_text_area.property("leftPadding")

print(f"leftPadding: {left_pad}")
print(f"tabSize: 4")

# Let's check cachedIndentLevelWidths from QML
cached_widths_val = editor.property("cachedIndentLevelWidths")
if hasattr(cached_widths_val, "toVariant"):
    cached_widths = cached_widths_val.toVariant()
else:
    cached_widths = cached_widths_val

print("\n--- MEASURING ACTUAL TEXTAREA CHARACTER POSITIONS ---")
# Lines in test_doc:
# Line 0: "A" -> pos 0 is 'A' (col 0)
# Line 1: "    B" -> pos 2 is start of line, pos 6 is 'B' (col 4)
# Line 2: "        C" -> pos 8 is start of line, pos 16 is 'C' (col 8)
# Line 3: "            D" -> pos 18 is start of line, pos 30 is 'D' (col 12)
# Line 4: "                E" -> pos 32 is start of line, pos 48 is 'E' (col 16)
# Line 5: "                    F" -> pos 50 is start of line, pos 70 is 'F' (col 20)
# Line 6: "                        G" -> pos 72 is start of line, pos 96 is 'G' (col 24)
# Line 7: "                            H" -> pos 98 is start of line, pos 126 is 'H' (col 28)

lines = test_doc.split("\n")
char_idx = 0
for lvl, line in enumerate(lines):
    # Find position of the letter in this line
    letter_char = chr(ord('A') + lvl)
    local_idx = line.find(letter_char)
    global_char_idx = char_idx + local_idx
    
    # Get TextArea positionToRectangle
    rect = code_text_area.positionToRectangle(global_char_idx)
    actual_x = rect.x()
    
    # Calculate guide X for this level
    cached_w = cached_widths[lvl] if lvl < len(cached_widths) else (lvl * cached_widths[1])
    calc_x = left_pad + cached_w
    diff = calc_x - actual_x
    
    print(f"Level {lvl} (col {lvl*4:2d}, '{letter_char}'): cached_w={cached_w:6.2f} | calc_x={calc_x:6.2f} | actual_text_x={actual_x:6.2f} | diff={diff:+.2f}")
    
    char_idx += len(line) + 1
