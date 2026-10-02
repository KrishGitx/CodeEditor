import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

Rectangle {
    id: root

    property string aiStatus: "idle" // "idle", "thinking", "streaming", "error"

    signal insertCodeRequested(string code)
    signal closeRequested()


    color: theme ? theme.bgSidebar : "#181818"
    

    // Disabled Overlay when AI Assistant is turned off in Settings
    Rectangle {
        anchors.fill: parent
        color: theme ? theme.bgSidebar : "#181818"
        visible: theme ? !theme.enableAI : false
        z: 20

        ColumnLayout {
            anchors.centerIn: parent
            width: parent.width - 32
            spacing: 12

            VectorIcon {
                Layout.alignment: Qt.AlignHCenter
                name: "sparkles"
                size: 24
                color: theme ? theme.textMuted : "#656565"
            }

            Text {
                text: "AI Assistant (Beta) Disabled"
                color: theme ? theme.textBright : "#ffffff"
                font.pixelSize: 13
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }

            Text {
                text: "AI features are currently turned off in Settings. You can enable them anytime in Preferences."
                color: theme ? theme.textSecondary : "#858585"
                font.pixelSize: 11
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: 110
                height: 28
                radius: 4
                color: enableAiMa.containsMouse ? (theme ? theme.accentHover : "#1084d8") : (theme ? theme.accent : "#0078d4")

                Text {
                    anchors.centerIn: parent
                    text: "Turn On AI"
                    color: "#ffffff"
                    font.pixelSize: 11
                    font.bold: true
                }

                MouseArea {
                    id: enableAiMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (theme) {
                            theme.enableAI = true;
                            theme.saveSettings();
                        }
                    }
                }
            }
        }
    }

    ListModel {
        id: chatHistoryModel

        Component.onCompleted: {
            append({
                    msgId: "welcome_1",
                    role: "assistant",
                    content: "DGX AI Assistant ready. Ask questions, generate functions, or debug code."
                });
        }
    }

    Connections {
        target: typeof aiBackend !== "undefined" ? aiBackend : null
        ignoreUnknownSignals: true

        function onMessageReceived(msgId, role, content) {
            for (var i = 0; i < chatHistoryModel.count; i++) {
                if (chatHistoryModel.get(i).msgId === msgId) {
                    chatHistoryModel.setProperty(i, "content", content);
                    return;
                }
            }
            chatHistoryModel.append({
                    msgId: msgId,
                    role: role,
                    content: content
                });
            chatListView.positionViewAtEnd();
        }

        function onChunkReceived(msgId, chunk) {
            for (var i = 0; i < chatHistoryModel.count; i++) {
                if (chatHistoryModel.get(i).msgId === msgId) {
                    var current = chatHistoryModel.get(i).content;
                    chatHistoryModel.setProperty(i, "content", current + chunk);
                    chatListView.positionViewAtEnd();
                    return;
                }
            }
            chatHistoryModel.append({
                    msgId: msgId,
                    role: "assistant",
                    content: chunk
                });
            chatListView.positionViewAtEnd();
        }

        function onStatusChanged(status) {
            root.aiStatus = status;
        }

        function onErrorOccurred(err) {
            chatHistoryModel.append({
                    msgId: "err_" + Date.now(),
                    role: "assistant",
                    content: "Error: " + err
                });
            root.aiStatus = "idle";
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Header with Clear and Close Buttons
        Rectangle {
            Layout.fillWidth: true
            height: 28
            color: theme ? theme.bgHeader : "#181818"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 6
                spacing: 4

                Text {
                    text: "AI ASSISTANT"
                    color: theme ? theme.textSecondary : "#858585"
                    font.pixelSize: 11
                    font.bold: true
                    font.letterSpacing: 0.5
                    Layout.fillWidth: true
                }

                // Clear Chat
                Rectangle {
                    width: 20
                    height: 20
                    radius: 2
                    color: clearMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "refresh"
                        size: 10
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    ToolTip.visible: clearMa.containsMouse
                    ToolTip.text: "Clear Chat"

                    MouseArea {
                        id: clearMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            chatHistoryModel.clear();
                            chatHistoryModel.append({
                                    msgId: "welcome_" + Date.now(),
                                    role: "assistant",
                                    content: "DGX AI Assistant ready. Ask questions, generate functions, or debug code."
                                });
                            root.aiStatus = "idle";
                            if (typeof aiBackend !== "undefined" && aiBackend && aiBackend.clear_chat) {
                                aiBackend.clear_chat();
                            }
                        }
                    }
                }

                // Close Button (x)
                Rectangle {
                    width: 20
                    height: 20
                    radius: 2
                    color: closeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "close"
                        size: 9
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    MouseArea {
                        id: closeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.closeRequested()
                    }
                }
            }
        }

        // 2. Chat Conversation
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: chatListView
                anchors.fill: parent
                anchors.margins: 6
                model: chatHistoryModel
                spacing: 8
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                delegate: ChatMessageItem {
                    role: model.role
                    contentText: model.content
                    width: chatListView.width

                    onInsertCodeRequested: function(code) {
                        root.insertCodeRequested(code);
                    }
                }
            }
        }

        // 3. Input Area
        Rectangle {
            Layout.fillWidth: true
            height: Math.max(38, Math.min(80, inputTextArea.contentHeight + 14))
            color: theme ? theme.bgPanel : "#181818"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 4
                spacing: 4

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    TextArea {
                        id: inputTextArea
                        placeholderText: "Ask AI..."
                        placeholderTextColor: theme ? theme.textMuted : "#656565"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        wrapMode: TextArea.Wrap
                        selectByMouse: true
                        background: null

                        Keys.onPressed: function(event) {
                            if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && !(event.modifiers & Qt.ShiftModifier)) {
                                root.submitPrompt();
                                event.accepted = true;
                            }
                        }
                    }
                }

                // Send Button
                Rectangle {
                    width: 24
                    height: 24
                    radius: 2
                    color: sendMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: root.aiStatus === "thinking" || root.aiStatus === "streaming" ? "stop" : "next"
                        size: 11
                        color: theme ? theme.accent : "#0078d4"
                    }

                    MouseArea {
                        id: sendMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.aiStatus === "thinking" || root.aiStatus === "streaming") {
                                // TODO: Connect CustomApi.py here.
                                // TODO: Connect AIBackend.py here.
                                if (typeof aiBackend !== "undefined" && aiBackend) {
                                    aiBackend.cancel();
                                }
                                root.aiStatus = "idle";
                            } else {
                                root.submitPrompt();
                            }
                        }
                    }
                }
            }
        }
    }
    function askAboutCode(code) {
    console.log("AIWorkspace RECEIVED:", code)

    inputTextArea.text = "Please Review the Following code:\n" + code

    submitPrompt()
}

    function submitPrompt() {
        var query = inputTextArea.text.trim();
        if (!query) return;

        inputTextArea.text = "";

        // TODO: Connect CustomApi.py here.
        // TODO: Connect AIBackend.py here.
        if (typeof aiBackend !== "undefined" && aiBackend && aiBackend.send_message) {
            aiBackend.send_message(query);
        } else {
            chatHistoryModel.append({
                    msgId: "usr_" + Date.now(),
                    role: "user",
                    content: query
                });

            root.aiStatus = "thinking";
            simTimer.targetQuery = query;
            simTimer.restart();
        }
    }

    Timer {
        id: simTimer
        interval: 400
        repeat: false
        property string targetQuery: ""
        onTriggered: {
            root.aiStatus = "idle";
            chatHistoryModel.append({
                    msgId: "ai_" + Date.now(),
                    role: "assistant",
                    content: "DGX AI response for: " + simTimer.targetQuery
                });
            chatListView.positionViewAtEnd();
        }
    }
}
