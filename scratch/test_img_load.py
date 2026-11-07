from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
import time

app = QApplication([])
engine = QQmlApplicationEngine()
qml = b'''
import QtQuick 2.15
import QtQuick.Window 2.15

Window {
    visible: false
    property int imgStatus: img.status
    property int imgWidth: img.sourceSize.width
    Image {
        id: img
        source: "https://open-vsx.org/api/ms-python/python/2026.4.0/file/icon.png"
    }
}
'''
engine.loadData(qml)
win = engine.rootObjects()[0]

for _ in range(30):
    app.processEvents()
    time.sleep(0.1)
    if win.property("imgStatus") == 1: # Image.Ready == 1
        break

print("Status:", win.property("imgStatus"), "Width:", win.property("imgWidth"))
