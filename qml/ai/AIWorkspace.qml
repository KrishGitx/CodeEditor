import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"
import "CodeExtractor.js" as CodeExtractor

Rectangle {
    id: root

    property string aiStatus: "idle" // "idle", "thinking", "streaming", "error"
    property var pendingSelectionContext: null
    property var activeSelectionContext: null

    signal insertCodeRequested(string code)
    signal replaceSelectionRequested(int startPos, int endPos, string newCode, string originalText)
    signal aiReplacementStarted(int startPos, int endPos, string originalText)
    signal aiReplacementReady(int startPos, int endPos, string newCode, string originalText)
    signal aiReplacementFailed()
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
                content: "DGX AI Assistant ready. Ask questions, generate functions, or debug code.",
                isSelectionRequest: false,
                selectionStart: -1,
                selectionEnd: -1,
                originalSelectedText: "",
                languageId: ""
            });
        }
    }

    Connections {
        target: typeof aiBackend !== "undefined" ? aiBackend : null
        ignoreUnknownSignals: true

        function onMessageReceived(msgId, role, content) {
            var ctx = root.activeSelectionContext;
            for (var i = 0; i < chatHistoryModel.count; i++) {
                if (chatHistoryModel.get(i).msgId === msgId) {
                    chatHistoryModel.setProperty(i, "content", content);
                    if (role === "assistant" && ctx) {
                        chatHistoryModel.setProperty(i, "isSelectionRequest", ctx.isSelectionRequest || false);
                        chatHistoryModel.setProperty(i, "selectionStart", ctx.selectionStart !== undefined ? ctx.selectionStart : -1);
                        chatHistoryModel.setProperty(i, "selectionEnd", ctx.selectionEnd !== undefined ? ctx.selectionEnd : -1);
                        chatHistoryModel.setProperty(i, "originalSelectedText", ctx.originalSelectedText || "");
                        chatHistoryModel.setProperty(i, "languageId", ctx.languageId || "");
                        if (ctx.isSelectionRequest) {
                            var cleanCode = CodeExtractor.extractCodeFromMarkdown(content, ctx.languageId);
                            if (cleanCode && cleanCode.trim().length > 0) {
                                root.aiReplacementReady(ctx.selectionStart, ctx.selectionEnd, cleanCode, ctx.originalSelectedText);
                            }
                        }
                    }
                    return;
                }
            }
            chatHistoryModel.append({
                msgId: msgId,
                role: role,
                content: content,
                isSelectionRequest: (role === "assistant" && ctx) ? (ctx.isSelectionRequest || false) : false,
                selectionStart: (role === "assistant" && ctx) ? (ctx.selectionStart !== undefined ? ctx.selectionStart : -1) : -1,
                selectionEnd: (role === "assistant" && ctx) ? (ctx.selectionEnd !== undefined ? ctx.selectionEnd : -1) : -1,
                originalSelectedText: (role === "assistant" && ctx) ? (ctx.originalSelectedText || "") : "",
                languageId: (role === "assistant" && ctx) ? (ctx.languageId || "") : ""
            });
            if (role === "assistant" && ctx && ctx.isSelectionRequest) {
                var cleanCode2 = CodeExtractor.extractCodeFromMarkdown(content, ctx.languageId);
                if (cleanCode2 && cleanCode2.trim().length > 0) {
                    root.aiReplacementReady(ctx.selectionStart, ctx.selectionEnd, cleanCode2, ctx.originalSelectedText);
                }
            }
            chatListView.positionViewAtEnd();
        }

        function onChunkReceived(msgId, chunk) {
            var ctx = root.activeSelectionContext;
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
                content: chunk,
                isSelectionRequest: ctx ? (ctx.isSelectionRequest || false) : false,
                selectionStart: ctx ? (ctx.selectionStart !== undefined ? ctx.selectionStart : -1) : -1,
                selectionEnd: ctx ? (ctx.selectionEnd !== undefined ? ctx.selectionEnd : -1) : -1,
                originalSelectedText: ctx ? (ctx.originalSelectedText || "") : "",
                languageId: ctx ? (ctx.languageId || "") : ""
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
                content: "Error: " + err,
                isSelectionRequest: false,
                selectionStart: -1,
                selectionEnd: -1,
                originalSelectedText: "",
                languageId: ""
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
                                content: "DGX AI Assistant ready. Ask questions, generate functions, or debug code.",
                                isSelectionRequest: false,
                                selectionStart: -1,
                                selectionEnd: -1,
                                originalSelectedText: "",
                                languageId: ""
                            });
                            root.pendingSelectionContext = null;
                            root.activeSelectionContext = null;
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

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    width: 8
                    active: true
                }

                delegate: ChatMessageItem {
                    role: model.role
                    contentText: model.content
                    isSelectionRequest: model.isSelectionRequest || false
                    selectionStart: model.selectionStart !== undefined ? model.selectionStart : -1
                    selectionEnd: model.selectionEnd !== undefined ? model.selectionEnd : -1
                    originalSelectedText: model.originalSelectedText || ""
                    languageId: model.languageId || ""
                    width: chatListView.width

                    onInsertCodeRequested: function(code) {
                        root.insertCodeRequested(code);
                    }

                    onReplaceSelectionRequested: function(startPos, endPos, code, originalText) {
                        root.replaceSelectionRequested(startPos, endPos, code, originalText);
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

    function askAboutSelection(code, startPos, endPos, langId, customPrompt) {
        var langTag = (langId || "").toLowerCase().trim();
        var basePrompt = (customPrompt && customPrompt.trim().length > 0) ? customPrompt.trim() : ("Please review and improve the selected " + (langTag ? langTag + " " : "") + "code:");
        var userMsg = basePrompt + "\n\n```" + (langTag || "") + "\n" + code + "\n```";

        var internalInstruction = "You are reviewing and improving a selected portion of an existing source file.\n" +
            "Please provide a clear and helpful explanation of:\n" +
            "- What was wrong or could be improved with the selected code\n" +
            "- What changes you made\n" +
            "- Why you made those changes\n" +
            "\n" +
            "IMPORTANT RULES FOR THE CODE BLOCK:\n" +
            "- Put the corrected code inside a Markdown code block (```" + (langTag || "") + " ... ```).\n" +
            "- The code block must contain ONLY the replacement code for the exact selected fragment.\n" +
            "- Do NOT return the entire document or recreate outer enclosing file structure (such as <!DOCTYPE html>, <html>, <body>, or outer class/module definitions) unless they were actually part of the selected text.\n" +
            "- The code inside the code block must be directly usable as a drop-in replacement for the selected portion.";

        root.pendingSelectionContext = {
            isSelectionRequest: true,
            selectionStart: (startPos !== undefined ? startPos : -1),
            selectionEnd: (endPos !== undefined ? endPos : -1),
            originalSelectedText: code,
            languageId: langTag,
            internalInstruction: internalInstruction
        };

        if (startPos !== undefined && startPos >= 0) {
            root.aiReplacementStarted(startPos, endPos, code);
        }

        inputTextArea.text = userMsg;
        submitPrompt();
    }

    function askAboutCode(code) {
        askAboutSelection(code, -1, -1, "");
    }

    function submitPrompt() {
        var query = inputTextArea.text.trim();
        if (!query) return;

        inputTextArea.text = "";

        var context = root.pendingSelectionContext;
        root.pendingSelectionContext = null;
        root.activeSelectionContext = context;

        var internalInstr = context && context.internalInstruction ? context.internalInstruction : "";

        if (typeof aiBackend !== "undefined" && aiBackend && aiBackend.send_message) {
            aiBackend.send_message(query, internalInstr);
        } else {
            chatHistoryModel.append({
                msgId: "usr_" + Date.now(),
                role: "user",
                content: query,
                isSelectionRequest: context ? context.isSelectionRequest : false,
                selectionStart: context ? context.selectionStart : -1,
                selectionEnd: context ? context.selectionEnd : -1,
                originalSelectedText: context ? context.originalSelectedText : "",
                languageId: context ? context.languageId : ""
            });

            root.aiStatus = "thinking";
            simTimer.targetContext = context;
            simTimer.targetQuery = query;
            simTimer.restart();
        }
    }

    Timer {
        id: simTimer
        interval: 400
        repeat: false
        property var targetContext: null
        property string targetQuery: ""
        onTriggered: {
            root.aiStatus = "idle";
            var ctx = simTimer.targetContext;
            var responseContent = "```" + (ctx ? ctx.languageId : "") + "\n" + (ctx ? ctx.originalSelectedText : "// generated code") + "\n```";
            chatHistoryModel.append({
                msgId: "ai_" + Date.now(),
                role: "assistant",
                content: responseContent,
                isSelectionRequest: ctx ? (ctx.isSelectionRequest || false) : false,
                selectionStart: ctx ? (ctx.selectionStart !== undefined ? ctx.selectionStart : -1) : -1,
                selectionEnd: ctx ? (ctx.selectionEnd !== undefined ? ctx.selectionEnd : -1) : -1,
                originalSelectedText: ctx ? (ctx.originalSelectedText || "") : "",
                languageId: ctx ? (ctx.languageId || "") : ""
            });
            if (ctx && ctx.isSelectionRequest) {
                var cleanSim = CodeExtractor.extractCodeFromMarkdown(responseContent, ctx.languageId);
                if (cleanSim && cleanSim.trim().length > 0) {
                    root.aiReplacementReady(ctx.selectionStart, ctx.selectionEnd, cleanSim, ctx.originalSelectedText);
                }
            }
            chatListView.positionViewAtEnd();
        }
    }
}
