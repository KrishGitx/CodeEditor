import sys
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl, QObject, Slot
from PySide6.QtGui import QTextCursor

app = QApplication(sys.argv)
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

qml = """
import QtQuick
import QtQuick.Controls

TextArea {
    id: ta
    text: "initial text"
}
"""

engine = QQmlApplicationEngine()
component = QQmlComponent(engine)
component.setData(qml.encode("utf-8"), QUrl(""))
ta = component.create()

print("Initial text:", ta.property("text"))
# Type some text via insert
ta.setProperty("cursorPosition", len(ta.property("text")))
ta.insert(len(ta.property("text")), " more")
print("After insert:", ta.property("text"))

# Now let's test undo
ta.undo()
print("After undo 1:", ta.property("text"))
ta.redo()
print("After redo 1:", ta.property("text"))

# Now let's test formatting replacement via select+insert or remove+insert or Python QTextCursor
print("\n--- Test 1: remove then insert in QML ---")
cur_len = len(ta.property("text"))
ta.remove(0, cur_len)
ta.insert(0, "formatted text")
print("After format:", ta.property("text"))
ta.undo()
print("After undo format:", ta.property("text"))
ta.undo()
print("After undo 2:", ta.property("text"))
ta.redo()
print("After redo 1:", ta.property("text"))
ta.redo()
print("After redo 2:", ta.property("text"))

print("\n--- Test 2: QTextCursor with editBlock in Python ---")
qml_doc = ta.property("textDocument")
doc = qml_doc.textDocument()
cursor = QTextCursor(doc)
cursor.beginEditBlock()
cursor.select(QTextCursor.Document)
cursor.insertText("formatted text block")
cursor.endEditBlock()
print("After editBlock format:", ta.property("text"))
ta.undo()
print("After single undo:", repr(ta.property("text")))
ta.redo()
print("After single redo:", repr(ta.property("text")))
