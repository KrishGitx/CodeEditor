import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Rectangle {
    id: aiWorkspaceRoot
    color: theme.bgPanelRight

    signal closeRequested()
    property string aiStatus: "idle" // "idle", "thinking", "streaming", "error"

    Connections {
        target: aiBackend

        function onMessageReceived(msgId, role, content) {
            // Check if this message was already streaming and update it, or append
            var found = false
            for (var i = 0; i < chatModel.count; i++) {
                if (chatModel.get(i).msgId === msgId) {
                    chatModel.setProperty(i, "content", content)
                    found = true
                    break
                }
            }
            if (!found) {
                var now = new Date()
                var timeStr = now.toLocaleTimeString(Qt.locale(), "hh:mm")
                chatModel.append({
                    msgId: msgId,
                    role: role,
                    content: content,
                    timestamp: timeStr
                })
            }
            chatListView.positionViewAtEnd()
        }

        function onChunkReceived(msgId, chunk) {
            var found = false
            for (var i = 0; i < chatModel.count; i++) {
                if (chatModel.get(i).msgId === msgId) {
                    var curr = chatModel.get(i).content
                    chatModel.setProperty(i, "content", curr + chunk)
                    found = true
                    break
                }
            }
            if (!found) {
                var now = new Date()
                var timeStr = now.toLocaleTimeString(Qt.locale(), "hh:mm")
                chatModel.append({
                    msgId: msgId,
                    role: "assistant",
                    content: chunk,
                    timestamp: timeStr
                })
            }
            chatListView.positionViewAtEnd()
        }

        function onStatusChanged(status) {
            aiWorkspaceRoot.aiStatus = status
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. AI Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            color: theme.bgHeader

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8

                // Status pulse dot
                Rectangle {
                    width: 8
                    height: 8
                    radius: 4
                    color: {
                        if (aiWorkspaceRoot.aiStatus === "thinking" || aiWorkspaceRoot.aiStatus === "streaming") {
                            return theme.accentWarning
                        } else if (aiWorkspaceRoot.aiStatus === "error") {
                            return theme.accentError
                        } else {
                            return theme.accentSuccess
                        }
                    }
                }

                Text {
                    text: "AI WORKSPACE"
                    color: theme.textSecondary
                    font.bold: true
                    font.pixelSize: 11
                    font.family: theme.uiFont
                    font.letterSpacing: 1.0
                    Layout.fillWidth: true
                }

                // Clear Conversation Button
                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    radius: 3
                    color: clearMouse.containsMouse ? theme.bgHover : "transparent"

                    Text {
                        text: "🗑"
                        font.pixelSize: 11
                        anchors.centerIn: parent
                    }

                    MouseArea {
                        id: clearMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            chatModel.clear()
                            aiBackend.clear_chat()
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    radius: 3
                    color: closeMouse.containsMouse ? theme.bgHover : "transparent"

                    Text {
                        text: "×"
                        color: closeMouse.containsMouse ? theme.textPrimary : theme.textMuted
                        font.pixelSize: 18
                        anchors.centerIn: parent
                    }

                    MouseArea {
                        id: closeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: aiWorkspaceRoot.closeRequested()
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

        // 2. Chat Conversation View
        ListView {
            id: chatListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 10
            spacing: 10
            clip: true

            model: ListModel {
                id: chatModel
                Component.onCompleted: {
                    chatModel.append({
                        msgId: "welcome_0",
                        role: "assistant",
                        content: "👋 Welcome to **DGX Studio AI**! How can I assist with your code today?",
                        timestamp: "Now"
                    })
                }
            }

            delegate: ChatMessage {
                width: chatListView.width
                role: model.role
                content: model.content
                timestamp: model.timestamp
            }
        }

        // 3. Status indicator banner (when generating)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: (aiWorkspaceRoot.aiStatus === "thinking" || aiWorkspaceRoot.aiStatus === "streaming") ? 22 : 0
            visible: (aiWorkspaceRoot.aiStatus === "thinking" || aiWorkspaceRoot.aiStatus === "streaming")
            color: theme.bgCard

            Row {
                anchors.centerIn: parent
                spacing: 6

                Text {
                    text: aiWorkspaceRoot.aiStatus === "thinking" ? "Thinking..." : "Generating response..."
                    color: theme.accentColor
                    font.pixelSize: 10
                    font.family: theme.uiFont
                }
            }
        }

        // 4. Prompt Input Area
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(68, promptInput.contentHeight + 30)
            color: theme.bgPanelRight

            Rectangle {
                color: theme.borderSubtle
                height: 1
                width: parent.width
                anchors.top: parent.top
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                anchors.topMargin: 8
                anchors.bottomMargin: 10
                spacing: 8

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    TextArea {
                        id: promptInput
                        placeholderText: "Ask AI or generate code... (Enter to send)"
                        placeholderTextColor: theme.textMuted
                        color: theme.textPrimary
                        font.pixelSize: 12
                        font.family: theme.uiFont
                        wrapMode: TextArea.Wrap
                        background: Rectangle {
                            color: theme.bgInput
                            border.color: promptInput.activeFocus ? theme.accentColor : theme.borderSubtle
                            radius: theme.radiusMd
                        }
                        selectByMouse: true

                        Keys.onPressed: function(event) {
                            if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && !(event.modifiers & Qt.ShiftModifier)) {
                                event.accepted = true
                                sendPrompt()
                            }
                        }
                    }
                }

                // Send / Stop button
                Rectangle {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignBottom
                    radius: theme.radiusMd
                    color: sendMouse.containsMouse ? theme.accentColor : theme.bgHover

                    Text {
                        text: (aiWorkspaceRoot.aiStatus === "thinking" || aiWorkspaceRoot.aiStatus === "streaming") ? "⏹" : "➤"
                        color: sendMouse.containsMouse ? "#ffffff" : theme.textPrimary
                        font.pixelSize: 12
                        anchors.centerIn: parent
                    }

                    MouseArea {
                        id: sendMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (aiWorkspaceRoot.aiStatus === "thinking" || aiWorkspaceRoot.aiStatus === "streaming") {
                                aiBackend.cancel()
                            } else {
                                sendPrompt()
                            }
                        }
                    }
                }
            }
        }
    }

    function sendPrompt() {
        var text = promptInput.text.trim()
        if (text.length === 0) return
        promptInput.text = ""
        aiBackend.send_message(text)
    }

    // Left dividing border
    Rectangle {
        color: theme.borderSubtle
        width: 1
        height: parent.height
        anchors.left: parent.left
    }
}
