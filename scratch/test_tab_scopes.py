import sys, os, time
sys.path.insert(0, os.path.abspath("."))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, QObject, QMetaObject, Q_ARG
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtGui import QFontMetrics
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

def get_scopes(ed):
    val = ed.property("activeScopeRanges")
    if hasattr(val, "toVariant"):
        try:
            return val.toVariant()
        except:
            pass
    return val

# Open DocA as Tab 0
doc_a_content = "Item {\n    Timer {\n    }\n}"
call_js(editor, "loadFile", "DocA.qml", doc_a_content)
app.processEvents()
s_a1 = get_scopes(editor)
print("DocA initial scopes:", s_a1)

# Open DocB as Tab 1
doc_b_content = "Rectangle {\n    Text {\n        property int b: 2\n    }\n}"
call_js(editor, "loadFile", "DocB.qml", doc_b_content)
app.processEvents()
s_b = get_scopes(editor)
print("DocB scopes:", s_b)

# Switch back to Tab 0 (DocA)
call_js(editor, "switchToTab", 0)
app.processEvents()
s_a2 = get_scopes(editor)
print("DocA after switch back scopes:", s_a2)

# Switch to Tab 1 (DocB)
call_js(editor, "switchToTab", 1)
app.processEvents()
s_b2 = get_scopes(editor)
print("DocB after switch back scopes:", s_b2)
