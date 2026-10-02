import sys, os, time
sys.path.insert(0, os.getcwd())

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import Qt, QUrl
from PySide6.QtQuickControls2 import QQuickStyle

os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
app = QGuiApplication(sys.argv)
QQuickStyle.setStyle('Basic')

with open("test_data/file_a.py", "r", encoding="utf-8") as f:
    sample_text = f.read()

def test_qml_snippet(name, qml_str):
    engine = QQmlApplicationEngine()
    comp = QQmlComponent(engine)
    comp.setData(qml_str.encode("utf-8"), QUrl(""))
    if comp.isError():
        print(f"[{name}] Errors:", comp.errors())
        return
    obj = comp.create()
    for _ in range(3): app.processEvents()

    t0 = time.perf_counter()
    ta = obj.findChild(object, "codeTextArea")
    ta.setProperty("text", sample_text)
    t1 = time.perf_counter()
    app.processEvents()
    t2 = time.perf_counter()
    print(f"[{name}] set text: {(t1 - t0)*1000:.1f} ms | processEvents: {(t2 - t1)*1000:.1f} ms | Total: {(t2 - t0)*1000:.1f} ms")

# Test 1: Bare TextArea in Item
test_qml_snippet("1. Bare TextArea", """
import QtQuick 2.15
import QtQuick.Controls 2.15
Item {
    width: 800; height: 600
    TextArea {
        id: codeTextArea; objectName: "codeTextArea"
        width: 800; height: 600
        textFormat: TextArea.PlainText
    }
}
""")

# Test 2: TextArea inside Flickable
test_qml_snippet("2. Inside Flickable", """
import QtQuick 2.15
import QtQuick.Controls 2.15
Item {
    width: 800; height: 600
    Flickable {
        id: flick
        anchors.fill: parent
        contentWidth: Math.max(width, codeTextArea.contentWidth + 34)
        contentHeight: Math.max(height, 3000 * 18 + 220)
        TextArea {
            id: codeTextArea; objectName: "codeTextArea"
            width: flick.contentWidth
            height: flick.contentHeight
            textFormat: TextArea.PlainText
        }
    }
}
""")

# Test 3: Flickable inside RowLayout and StackLayout
test_qml_snippet("3. In StackLayout", """
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
Item {
    width: 800; height: 600
    StackLayout {
        anchors.fill: parent
        Item {
            Flickable {
                id: flick
                anchors.fill: parent
                contentWidth: Math.max(width, codeTextArea.contentWidth + 34)
                contentHeight: Math.max(height, 3000 * 18 + 220)
                TextArea {
                    id: codeTextArea; objectName: "codeTextArea"
                    width: flick.contentWidth
                    height: flick.contentHeight
                    textFormat: TextArea.PlainText
                }
            }
        }
    }
}
""")

# Test 4: Full tabPane delegate structure
test_qml_snippet("4. Full tabPane delegate with canvas and gutter", """
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
Item {
    width: 800; height: 600
    RowLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            width: 48; Layout.fillHeight: true; color: "#181818"
            Flickable {
                anchors.fill: parent
                contentHeight: editorFlickable.contentHeight
                contentY: editorFlickable.contentY
            }
        }
        Item {
            Layout.fillWidth: true; Layout.fillHeight: true
            Canvas {
                id: indentGuidesCanvas; anchors.fill: parent
                onPaint: { var ctx = getContext("2d"); ctx.clearRect(0,0,width,height); }
            }
            Flickable {
                id: editorFlickable
                anchors.fill: parent
                contentWidth: Math.max(width, codeTextArea.contentWidth + 34)
                contentHeight: Math.max(height, 3000 * 18 + 220)
                TextArea {
                    id: codeTextArea; objectName: "codeTextArea"
                    width: editorFlickable.contentWidth
                    height: editorFlickable.contentHeight
                    textFormat: TextArea.PlainText
                    font.family: "Consolas"
                    font.pixelSize: 13
                    topPadding: 6; bottomPadding: 16; leftPadding: 10; rightPadding: 24
                    wrapMode: TextArea.NoWrap
                }
            }
        }
    }
}
""")

app.quit()
