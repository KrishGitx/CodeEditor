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

# Load full main.qml so Theme is properly initialized
component = QQmlComponent(engine)
component.loadUrl(QUrl.fromLocalFile("qml/main.qml"))
if component.isError():
    for err in component.errors():
        print("QML Error:", err.toString())
    sys.exit(1)
win = component.create()

editor = win.findChild(QObject, "editorArea")
if not editor:
    # Try finding EditorArea in children
    for c in win.children():
        if "EditorArea" in c.metaObject().className() or hasattr(c, "loadFile"):
            editor = c
            break

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
left_pad = code_text_area.property("leftPadding")

cached_widths_val = editor.property("cachedIndentLevelWidths")
if hasattr(cached_widths_val, "toVariant"):
    cached_widths = cached_widths_val.toVariant()
else:
    cached_widths = cached_widths_val

lines = test_doc.split("\n")
char_idx = 0
print("--- FULL APP DRIFT MEASUREMENT ---")
for lvl, line in enumerate(lines):
    letter_char = chr(ord('A') + lvl)
    local_idx = line.find(letter_char)
    global_char_idx = char_idx + local_idx
    
    rect = code_text_area.positionToRectangle(global_char_idx)
    actual_x = rect.x()
    
    cached_w = cached_widths[lvl] if lvl < len(cached_widths) else (lvl * cached_widths[1])
    calc_x = left_pad + cached_w
    diff = calc_x - actual_x
    
    print(f"Level {lvl} (col {lvl*4:2d}, '{letter_char}'): cached_w={cached_w:6.2f} | calc_x={calc_x:6.2f} | actual_text_x={actual_x:6.2f} | diff={diff:+.2f}")
    char_idx += len(line) + 1
