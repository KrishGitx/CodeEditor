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
                            var parseRes = CodeExtractor.parseReplacementResponse(content, ctx.languageId, ctx.originalSelectedText);
                            if (parseRes.status === "replacement" && parseRes.code && parseRes.code.trim().length > 0) {
                                root.aiReplacementReady(ctx.selectionStart, ctx.selectionEnd, parseRes.code, ctx.originalSelectedText);
                            } else {
                                root.aiReplacementFailed();
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
                var parseRes2 = CodeExtractor.parseReplacementResponse(content, ctx.languageId, ctx.originalSelectedText);
                if (parseRes2.status === "replacement" && parseRes2.code && parseRes2.code.trim().length > 0) {
                    root.aiReplacementReady(ctx.selectionStart, ctx.selectionEnd, parseRes2.code, ctx.originalSelectedText);
                } else {
                    root.aiReplacementFailed();
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

    function askAboutSelection(code, startPos, endPos, langId, customPrompt, surroundingContext, totalDocLength) {
        var langTag = (langId || "").toLowerCase().trim();
        var docLen = (totalDocLength !== undefined && totalDocLength > 0) ? totalDocLength : (code ? code.length : -1);
        var isFullFile = (startPos === 0 && docLen > 0 && endPos >= docLen) || (code && docLen > 0 && code.length >= docLen);

        var basePrompt = (customPrompt && customPrompt.trim().length > 0) ? customPrompt.trim() : ("Please review and improve the selected " + (langTag ? langTag + " " : "") + "code:");
        var userMsg = basePrompt + "\n\n```" + (langTag || "") + "\n" + code + "\n```";

        if (surroundingContext && surroundingContext.trim().length > 0 && surroundingContext.trim() !== code.trim()) {
            userMsg += "\n\nSurrounding file context (FOR REASONING ONLY - DO NOT INCLUDE IN REPLACEMENT):\n```" + (langTag || "") + "\n" + surroundingContext.trim() + "\n```";
        }

        var internalInstruction = "SELECTION REPLACEMENT MODE\n" +
            "The user has selected a specific region of an existing source file" + (isFullFile ? " (which spans the entire file)." : ".") + "\n" +
            "Your response is NOT a request to rewrite or regenerate the entire file or block.\n" +
            "You MUST reason about the selected region and surrounding context, but your replacement output MUST remain limited to the exact selected scope.\n\n" +
            "CORE PRINCIPLE:\n" +
            "THE PROVIDED CODE IS THE SOURCE OF TRUTH.\n" +
            "Only modify the minimum text required to fix the requested problem.\n\n" +
            "Strict Code Preservation Rules:\n" +
            "1. Preserve all provided code EXACTLY unless a specific change is required to solve the user's request.\n" +
            "2. MINIMAL EDIT PRINCIPLE: Think of the task as a surgical edit. Only fix the broken part (e.g. changing an incomplete or broken statement) and preserve every other line, variable name, string literal, comment, URL, browser setting, import, indentation, and formatting verbatim as supplied.\n" +
            "3. Do NOT rewrite the whole block, do NOT regenerate unchanged code, and do NOT replace equivalent code with an alternative implementation.\n" +
            "4. Do NOT rename variables, reorder lines, change quotes/formatting, 'clean up', or modernize code that was not requested.\n" +
            "5. Do NOT create a complete example, new application, or boilerplate when only a fragment was selected.\n" +
            "6. Never return the full source file unless the user's selected scope itself is the full file.\n" +
            "7. Never return unrelated surrounding code or duplicate unselected code.\n" +
            "8. If the selected fragment can be fixed independently, return ONLY its complete corrected replacement preserving all unchanged lines.\n" +
            "9. If the correct fix requires code outside the selection, return:\n" +
            "   [INSUFFICIENT_CONTEXT]\n" +
            "10. If no useful modification is necessary or the code is already correct, return:\n" +
            "   [NO_CHANGE]\n" +
            "11. If a replacement is possible, return exactly:\n" +
            "   [REPLACEMENT_CODE]\n" +
            "   ```" + (langTag || "") + "\n" +
            "   complete replacement for ONLY the selected region\n" +
            "   ```\n" +
            "12. The fenced block must contain ONLY replacement source code.\n" +
            "13. Keep explanations, diagnostics, and reasoning OUTSIDE the code block.\n" +
            "14. Do not include phrases like 'here is the complete code' or conversational text inside the code block.\n\n" +
            "Always explain your reasoning in clear text outside the code block. Always include exactly one of the markers: [REPLACEMENT_CODE], [NO_CHANGE], or [INSUFFICIENT_CONTEXT].";

        root.pendingSelectionContext = {
            isSelectionRequest: true,
            selectionStart: (startPos !== undefined ? startPos : -1),
            selectionEnd: (endPos !== undefined ? endPos : -1),
            originalSelectedText: code,
            languageId: langTag,
            surroundingContext: surroundingContext || "",
            totalDocLength: docLen,
            isFullFile: isFullFile,
            internalInstruction: internalInstruction
        };

        if (startPos !== undefined && startPos >= 0) {
            root.aiReplacementStarted(startPos, endPos, code);
        }

        submitPrompt(userMsg);
    }

    function askAboutCode(code) {
        askAboutSelection(code, -1, -1, "");
    }

    function sendDirectPrompt(promptText) {
        if (!promptText || promptText.trim().length === 0) return;
        submitPrompt(promptText.trim());
    }

    function submitPrompt(directQuery) {
        var query = (directQuery !== undefined && typeof directQuery === "string") ? directQuery.trim() : inputTextArea.text.trim();
        if (!query) return;

        if (directQuery === undefined) {
            inputTextArea.text = "";
        }

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
            var responseContent = "Explanation of code...\n\n```" + (ctx ? ctx.languageId : "") + "\n// example problem\n```\n\n[REPLACEMENT_CODE]\n```" + (ctx ? ctx.languageId : "") + "\n" + (ctx ? ctx.originalSelectedText : "// generated code") + "\n```";
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
                var parseResSim = CodeExtractor.parseReplacementResponse(responseContent, ctx.languageId, ctx.originalSelectedText);
                if (parseResSim.status === "replacement" && parseResSim.code && parseResSim.code.trim().length > 0) {
                    root.aiReplacementReady(ctx.selectionStart, ctx.selectionEnd, parseResSim.code, ctx.originalSelectedText);
                } else {
                    root.aiReplacementFailed();
                }
            }
            chatListView.positionViewAtEnd();
        }
    }
}
