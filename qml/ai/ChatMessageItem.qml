import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

Item {
    id: root

    property string role: "assistant" // "user" or "assistant"
    property string contentText: ""
    property bool isStreaming: false

    signal insertCodeRequested(string code)
    signal copyCodeRequested(string text)

    width: parent ? parent.width : 280
    implicitHeight: contentColumn.implicitHeight + 8
    height: implicitHeight

    ColumnLayout {
        id: contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 4

        // Role Header
        RowLayout {
            spacing: 6
            Layout.fillWidth: true

            Text {
                text: root.role === "user" ? "You" : "DGX AI"
                color: root.role === "user" ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textPrimary : "#cccccc")
                font.pixelSize: 11
                font.bold: true
            }

            Item { Layout.fillWidth: true }

            // Inline Insert button only on assistant code blocks
            Rectangle {
                visible: root.role === "assistant" && (root.contentText.indexOf("```") !== -1 || root.contentText.indexOf("def ") !== -1)
                width: insText.contentWidth + 10
                height: 18
                radius: 2
                color: insMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                Text {
                    id: insText
                    anchors.centerIn: parent
                    text: "Insert"
                    color: insMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textSecondary : "#858585")
                    font.pixelSize: 10
                }

                MouseArea {
                    id: insMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        var clean = root.contentText.replace(/```[a-zA-Z]*\n?/g, "").replace(/```/g, "");
                        root.insertCodeRequested(clean);
                    }
                }
            }
        }

        // Message Body Card
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: bodyTextEdit.contentHeight + 14
            radius: 3
            color: root.role === "user" ? (theme ? theme.bgSurface : "#252526") : (theme ? theme.bgEditor : "#1e1e1e")
            border.color: theme ? theme.borderSubtle : "#282828"
            border.width: 1

            TextEdit {
                id: bodyTextEdit
                anchors.fill: parent
                anchors.margins: 7
                text: root.contentText
                color: theme ? theme.textPrimary : "#cccccc"
                font.pixelSize: 12
                font.family: root.role === "user" ? (theme ? theme.fontFamilyUi : "sans-serif") : (theme ? theme.fontFamilyMono : "monospace")
                wrapMode: TextEdit.Wrap
                readOnly: true
                selectByMouse: true
            }
        }
    }
}
