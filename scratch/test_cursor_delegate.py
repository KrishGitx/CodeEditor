import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
qml = """
import QtQuick 2.15
import QtQuick.Controls 2.15

TextArea {
    id: textEdit
    text: "Hello world"
    cursorDelegate: Rectangle {
        width: 2
        color: "#38bdf8"
    }
}
"""
engine.loadData(qml.encode('utf-8'))
if engine.rootObjects():
    print("cursorDelegate loaded successfully in Qt6!")
else:
    print("Failed to load cursorDelegate!")
