import sys, os, time
sys.path.insert(0, os.getcwd())

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import Qt, QUrl
from PySide6.QtQuickControls2 import QQuickStyle

os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
app = QGuiApplication(sys.argv)
QQuickStyle.setStyle('Basic')

from main import EditorBackend
from SettingsBackend import SettingsBackend

backend = EditorBackend()
settingsBackend = SettingsBackend()
backend.settings_backend = settingsBackend

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

theme_comp = QQmlComponent(engine, "qml/Theme.qml")
theme = theme_comp.create()
engine.rootContext().setContextProperty("theme", theme)

test_qml = """
import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    width: 600; height: 400

    property bool enableWordWrap: false

    Flickable {
        id: flick
        anchors.fill: parent
        clip: true
        contentWidth: enableWordWrap ? width : Math.max(width, ta.contentWidth + 40)
        contentHeight: enableWordWrap ? Math.max(height, ta.contentHeight + 40) : Math.max(height, 50 * 18 + 40)

        TextArea {
            id: ta
            width: flick.enableWordWrap ? flick.width : flick.contentWidth
            height: flick.contentHeight
            wrapMode: flick.enableWordWrap ? TextArea.WrapAtWordBoundaryOrAnywhere : TextArea.NoWrap
            textFormat: TextArea.PlainText
            font.family: "Consolas"
            font.pixelSize: 13
            text: "This is a very long line of code that should demonstrate word wrap: " + "foo_bar_baz_qux_".repeat(20) + " end of long line."
        }
    }
}
"""

comp = QQmlComponent(engine)
comp.setData(test_qml.encode('utf-8'), QUrl(""))
obj = comp.create()
app.processEvents()

ta = obj.findChild(object)
print("Initial NoWrap:")
print("  contentWidth:", obj.property("enableWordWrap"))
print("  TextArea contentWidth:", ta.property("contentWidth"), "height:", ta.property("height"), "contentHeight:", ta.property("contentHeight"))

print("\nToggling WordWrap ON:")
obj.setProperty("enableWordWrap", True)
app.processEvents()
print("  TextArea contentWidth:", ta.property("contentWidth"), "height:", ta.property("height"), "contentHeight:", ta.property("contentHeight"))
print("  TextArea lineCount:", ta.property("lineCount"))

app.quit()
