import sys, os
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
from PySide6.QtGui import QGuiApplication, QTextCursor
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
qml_code = """import QtQuick 2.15
import QtQuick.Controls 2.15
TextArea {
    text: "Initial text"
}
"""
comp = QQmlComponent(engine)
comp.setData(qml_code.encode("utf-8"), "")
ta = comp.create()
qml_doc = ta.property('textDocument')
doc = qml_doc.textDocument()
doc.setModified(False)

print('doc.isModified initially:', doc.isModified())

modified_events = []
doc.modificationChanged.connect(lambda m: modified_events.append(m))

cur = QTextCursor(doc)
cur.movePosition(QTextCursor.End)
cur.insertText(' edit')

print('doc.isModified after edit:', doc.isModified())
print('Events after edit:', modified_events)

doc.undo()
print('doc.isModified after undo:', doc.isModified())
print('Events after undo:', modified_events)
