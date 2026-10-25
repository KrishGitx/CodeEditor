import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QByteArray, qInstallMessageHandler

def qt_message_handler(mode, context, message):
    print(f"[QML] {message}")

qInstallMessageHandler(qt_message_handler)

app = QApplication(sys.argv)
engine = QQmlApplicationEngine()
qml = """
import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    TextArea {
        id: ta
        text: "context = browser.new_context(\\n    user_agent=\\n)"
        Component.onCompleted: {
            var idx = text.indexOf("wser.new_context");
            var endIdx = idx + "wser.new_context(\\n    user_agent=\\n)".length;
            ta.select(idx, endIdx);
            console.log("selectedText: " + JSON.stringify(ta.selectedText));
            console.log("selectionStart: " + ta.selectionStart + " selectionEnd: " + ta.selectionEnd);
            ta.remove(ta.selectionStart, ta.selectionEnd);
            ta.insert(idx, "wser.new_context(\\n    user_agent_fixed=\\n)");
            console.log("after insert: " + JSON.stringify(ta.text));
        }
    }
}
"""
engine.loadData(QByteArray(qml.encode('utf-8')))
app.processEvents()
