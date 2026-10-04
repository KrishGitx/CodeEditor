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
component.loadUrl(QUrl.fromLocalFile("qml/main.qml"))
win = component.create()

editor = win.findChild(QObject, "editorArea")
if not editor:
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

font_sizes = [9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 24]
fonts = ["Consolas", "Courier New"]

print("=== SWEEPING FONT SIZES AND FAMILIES ===")
for font_name in fonts:
    for sz in font_sizes:
        code_text_area.setProperty("font", QFont(font_name, sz))
        app.processEvents()
        
        left_pad = code_text_area.property("leftPadding")
        cached_widths_val = editor.property("cachedIndentLevelWidths")
        if hasattr(cached_widths_val, "toVariant"):
            cached_widths = cached_widths_val.toVariant()
        else:
            cached_widths = cached_widths_val
            
        max_diff = 0.0
        lines = test_doc.split("\n")
        char_idx = 0
        for lvl, line in enumerate(lines):
            letter_char = chr(ord('A') + lvl)
            local_idx = line.find(letter_char)
            global_char_idx = char_idx + local_idx
            
            rect = code_text_area.positionToRectangle(global_char_idx)
            actual_x = rect.x()
            
            cached_w = cached_widths[lvl] if lvl < len(cached_widths) else (lvl * cached_widths[1])
            calc_x = left_pad + cached_w
            diff = abs(calc_x - actual_x)
            if diff > max_diff:
                max_diff = diff
            char_idx += len(line) + 1
            
        print(f"Font: {font_name:14s} | Size: {sz:2d} | Max Drift across 8 levels: {max_diff:.2f}px")
