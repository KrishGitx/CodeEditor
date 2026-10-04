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
editor = component.create()

def call_js(obj, func_name, *args):
    qargs = [Q_ARG("QVariant", a) for a in args]
    return QMetaObject.invokeMethod(obj, func_name, *qargs)

call_js(editor, "loadFile", "test.qml", "A\n    B")
app.processEvents()

active_pane = editor.property("activeEditorPane")
code_text_area = editor.property("codeTextArea")

fm_qml = editor.findChild(QObject, "fontMetrics")
print("codeTextArea font:", code_text_area.property("font"))
print("charWidth property in editor:", editor.property("charWidth"))
print("editorLineHeight property in editor:", editor.property("editorLineHeight"))

# Let's check font metrics of codeTextArea font directly:
fm_cta = QFontMetrics(code_text_area.property("font"))
print("QFontMetrics(codeTextArea.font).horizontalAdvance(' '):", fm_cta.horizontalAdvance(" "))
print("QFontMetrics(codeTextArea.font).horizontalAdvance('    '):", fm_cta.horizontalAdvance("    "))
print("QFontMetrics(codeTextArea.font).horizontalAdvance('        '):", fm_cta.horizontalAdvance("        "))
