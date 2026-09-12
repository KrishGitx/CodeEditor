import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Rectangle {
    id: terminalRoot
    color: theme.bgBottomPanel

    signal closeRequested()

    property var commandHistory: []
    property int historyIndex: -1

    Connections {
        target: terminalBackend

        function onOutputReceived(text) {
            if (text === "__CLEAR_BUFFER__") {
                terminalOutputArea.text = ""
                return
            }
            terminalOutputArea.append(text)
            outputScrollView.ScrollBar.vertical.position = 1.0 - outputScrollView.ScrollBar.vertical.size
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Terminal Header Bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: theme.bgHeader

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8

                // Terminal tab indicator
                Row {
                    spacing: 8
                    Layout.alignment: Qt.AlignVCenter

                    Text {
                        text: "TERMINAL"
                        color: theme.accentColor
                        font.bold: true
                        font.pixelSize: 11
                        font.family: theme.uiFont
                        font.letterSpacing: 0.5
                    }

                    Text {
                        text: "• powershell"
                        color: theme.textMuted
                        font.pixelSize: 10
                        font.family: theme.monoFont
                    }
                }

                Item { Layout.fillWidth: true }

                // Actions: Clear, Restart, Close
                Row {
                    spacing: 4

                    // Clear button
                    Rectangle {
                        width: 22
                        height: 22
                        radius: 3
                        color: clearMouse.containsMouse ? theme.bgHover : "transparent"

                        Text {
                            text: "⊘"
                            color: theme.textSecondary
                            font.pixelSize: 11
                            anchors.centerIn: parent
                        }

                        MouseArea {
                            id: clearMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: terminalBackend.clear()
                        }
                    }

                    // Restart button
                    Rectangle {
                        width: 22
                        height: 22
                        radius: 3
                        color: restartMouse.containsMouse ? theme.bgHover : "transparent"

                        Text {
                            text: "↻"
                            color: theme.textSecondary
                            font.pixelSize: 11
                            anchors.centerIn: parent
                        }

                        MouseArea {
                            id: restartMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: terminalBackend.restart()
                        }
                    }

                    // Close / Hide button
                    Rectangle {
                        width: 22
                        height: 22
                        radius: 3
                        color: closeMouse.containsMouse ? theme.bgHover : "transparent"

                        Text {
                            text: "✕"
                            color: theme.textSecondary
                            font.pixelSize: 10
                            anchors.centerIn: parent
                        }

                        MouseArea {
                            id: closeMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: terminalRoot.closeRequested()
                        }
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

        // 2. Terminal Output ScrollView
        ScrollView {
            id: outputScrollView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            TextArea {
                id: terminalOutputArea
                readOnly: true
                color: theme.textPrimary
                font.family: theme.monoFont
                font.pixelSize: 11
                wrapMode: TextArea.Wrap
                background: Rectangle { color: "transparent" }
                leftPadding: 12
                rightPadding: 12
                topPadding: 8
                bottomPadding: 8
                selectByMouse: true
            }
        }

        // 3. Command Prompt Input Line
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            color: theme.bgBottomPanel

            Rectangle {
                color: theme.borderSubtle
                height: 1
                width: parent.width
                anchors.top: parent.top
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8
                spacing: 6

                Text {
                    text: "❯"
                    color: theme.accentColor
                    font.pixelSize: 11
                    font.bold: true
                    font.family: theme.monoFont
                }

                TextField {
                    id: cmdInput
                    Layout.fillWidth: true
                    placeholderText: "Type shell command (e.g. python, dir, git)..."
                    placeholderTextColor: theme.textMuted
                    color: theme.textPrimary
                    font.family: theme.monoFont
                    font.pixelSize: 11
                    background: Rectangle { color: "transparent" }
                    selectByMouse: true

                    onAccepted: {
                        var cmd = text.trim()
                        if (cmd.length > 0) {
                            terminalRoot.commandHistory.push(cmd)
                            terminalRoot.historyIndex = terminalRoot.commandHistory.length
                            terminalBackend.send_command(cmd)
                            text = ""
                        }
                    }

                    Keys.onPressed: function(event) {
                        if (event.key === Qt.Key_Up) {
                            if (terminalRoot.commandHistory.length > 0 && terminalRoot.historyIndex > 0) {
                                terminalRoot.historyIndex--
                                text = terminalRoot.commandHistory[terminalRoot.historyIndex]
                                event.accepted = true
                            }
                        } else if (event.key === Qt.Key_Down) {
                            if (terminalRoot.historyIndex < terminalRoot.commandHistory.length - 1) {
                                terminalRoot.historyIndex++
                                text = terminalRoot.commandHistory[terminalRoot.historyIndex]
                                event.accepted = true
                            } else {
                                terminalRoot.historyIndex = terminalRoot.commandHistory.length
                                text = ""
                                event.accepted = true
                            }
                        }
                    }
                }
            }
        }
    }

    // Top border divider
    Rectangle {
        color: theme.borderSubtle
        height: 1
        width: parent.width
        anchors.top: parent.top
    }
}
