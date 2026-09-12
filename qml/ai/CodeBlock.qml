import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Rectangle {
    id: codeBlockRoot
    property string codeText: ""
    property string language: "code"

    color: theme.bgInput
    border.color: theme.borderSubtle
    border.width: 1
    radius: 6
    implicitHeight: 32 + Math.max(28, codeContent.contentHeight) + 16

    Column {
        anchors.fill: parent
        spacing: 0

        // Header bar with language tag, insert button, and copy button
        Rectangle {
            id: headerBar
            width: parent.width
            height: 30
            color: theme.bgCard
            radius: 6

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 8
                spacing: 6

                // Language badge
                Text {
                    text: codeBlockRoot.language.toUpperCase()
                    color: theme.accentColor
                    font.pixelSize: 10
                    font.bold: true
                    font.family: theme.monoFont
                    Layout.fillWidth: true
                }

                // Insert into Editor Button
                Rectangle {
                    id: insertBtn
                    width: insertText.implicitWidth + 12
                    height: 20
                    radius: 3
                    color: insertMouse.containsMouse ? theme.accentColor : theme.bgHover

                    Text {
                        id: insertText
                        text: "Insert ↳"
                        color: insertMouse.containsMouse ? "#ffffff" : theme.textPrimary
                        font.pixelSize: 10
                        font.family: theme.uiFont
                        anchors.centerIn: parent
                    }

                    MouseArea {
                        id: insertMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (editorArea && editorArea.textAreaItem) {
                                var pos = editorArea.textAreaItem.cursorPosition
                                editorArea.textAreaItem.insert(pos, "\n" + codeBlockRoot.codeText + "\n")
                                editorArea.textAreaItem.cursorPosition = pos + codeBlockRoot.codeText.length + 2
                            }
                        }
                    }
                }

                // Copy Button
                Rectangle {
                    id: copyBtn
                    width: copyText.implicitWidth + 12
                    height: 20
                    radius: 3
                    color: copyMouse.containsMouse ? theme.bgHover : "transparent"

                    property bool copied: false

                    Text {
                        id: copyText
                        text: copyBtn.copied ? "✓ Copied" : "Copy"
                        color: copyBtn.copied ? theme.accentSuccess : theme.textSecondary
                        font.pixelSize: 10
                        font.family: theme.uiFont
                        anchors.centerIn: parent
                    }

                    MouseArea {
                        id: copyMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            dummyCopyEdit.text = codeBlockRoot.codeText
                            dummyCopyEdit.selectAll()
                            dummyCopyEdit.copy()
                            copyBtn.copied = true
                            resetCopyTimer.restart()
                        }
                    }

                    Timer {
                        id: resetCopyTimer
                        interval: 2000
                        onTriggered: copyBtn.copied = false
                    }
                }
            }

            Rectangle {
                color: theme.borderSubtle
                height: 1
                width: parent.width
                anchors.bottom: parent.bottom
            }
        }

        // Code Content Display
        TextEdit {
            id: codeContent
            width: parent.width - 20
            x: 10
            y: 8
            text: codeBlockRoot.codeText
            color: theme.textPrimary
            font.family: theme.monoFont
            font.pixelSize: 11
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.Wrap
        }
    }

    TextEdit {
        id: dummyCopyEdit
        visible: false
    }
}
