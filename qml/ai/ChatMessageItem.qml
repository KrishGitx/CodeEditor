import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"
import "CodeExtractor.js" as CodeExtractor

Item {
    id: root

    property string role: "assistant" // "user" or "assistant"
    property string contentText: ""
    property bool isStreaming: false
    property bool isSelectionRequest: false
    property int selectionStart: -1
    property int selectionEnd: -1
    property string originalSelectedText: ""
    property string languageId: ""

    signal replaceSelectionRequested(int startPos, int endPos, string newCode, string originalText)
    signal insertCodeRequested(string code)
    signal copyCodeRequested(string text)

    width: parent ? parent.width : 280
    implicitHeight: contentColumn.implicitHeight + 8
    height: implicitHeight

    function getCleanCode() {
        if (root.isSelectionRequest) {
            return CodeExtractor.extractReplacementCode(root.contentText, root.languageId);
        }
        return CodeExtractor.extractCodeFromMarkdown(root.contentText, root.languageId);
    }

    readonly property string extractedCode: getCleanCode()
    readonly property bool hasUsableCode: extractedCode.trim().length > 0
    readonly property var segments: CodeExtractor.parseMarkdownSegments(root.contentText)

    ColumnLayout {
        id: contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 6

        // Role Header
        RowLayout {
            spacing: 6
            Layout.fillWidth: true

            Text {
                text: root.role === "user" ? "You" : "DGX AI"
                color: root.role === "user" ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textPrimary : "#cccccc")
                font.pixelSize: 11
                font.bold: true
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
            }

            Item { Layout.fillWidth: true }

            // Replace Selection button - ONLY when AI request was made from an editor code selection with valid replacement code
            Rectangle {
                visible: root.role === "assistant" && root.isSelectionRequest && root.hasUsableCode
                enabled: root.hasUsableCode
                opacity: enabled ? 1.0 : 0.4
                width: replaceText.contentWidth + 12
                height: 18
                radius: 2
                color: replaceMa.containsMouse ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgSurfaceHover : "#2a2d2e")

                Text {
                    id: replaceText
                    anchors.centerIn: parent
                    text: "Replace Selection"
                    color: "#ffffff"
                    font.pixelSize: 10
                    font.bold: true
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                ToolTip.visible: replaceMa.containsMouse
                ToolTip.text: root.hasUsableCode ? "Replace selected code in editor with extracted AI solution" : "No code block returned"

                MouseArea {
                    id: replaceMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: root.hasUsableCode ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: {
                        if (!root.hasUsableCode) return;
                        root.replaceSelectionRequested(root.selectionStart, root.selectionEnd, root.extractedCode, root.originalSelectedText);
                    }
                }
            }
        }

        // Single Unified Message Card (Continuous bubble/card for the entire response)
        Rectangle {
            id: messageCard
            Layout.fillWidth: true
            implicitHeight: messageInnerColumn.implicitHeight + 16
            radius: 4
            color: root.role === "user" ? (theme ? theme.bgSurface : "#252526") : (theme ? theme.bgEditor : "#1e1e1e")
            border.color: theme ? theme.borderSubtle : "#282828"
            border.width: 1

            ColumnLayout {
                id: messageInnerColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 8
                spacing: 8

                Repeater {
                    model: root.segments
                    delegate: ColumnLayout {
                        id: segmentItem
                        Layout.fillWidth: true
                        spacing: 4

                        readonly property var segData: modelData
                        readonly property bool isCode: segData && segData.type === "code"

                        // 1. Regular Chat Text (Explanation before/between/after code)
                        TextEdit {
                            id: regularTextEdit
                            visible: !segmentItem.isCode && segData.text.length > 0
                            Layout.fillWidth: true
                            text: segData ? segData.text : ""
                            color: theme ? theme.textPrimary : "#cccccc"
                            font.pixelSize: 12
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            wrapMode: TextEdit.Wrap
                            readOnly: true
                            selectByMouse: true
                        }

                        // 2. Embedded VS Code / ChatGPT Style Code Block Rectangle
                        Rectangle {
                            visible: segmentItem.isCode
                            Layout.fillWidth: true
                            implicitHeight: codeHeaderRect.height + codeScrollFlickable.implicitHeight + 2
                            radius: 4
                            color: theme ? theme.bgPanel : "#141414"
                            border.color: theme ? theme.borderSubtle : "#333333"
                            border.width: 1
                            clip: true

                            // Top Action Header Bar
                            Rectangle {
                                id: codeHeaderRect
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                height: 26
                                color: theme ? theme.bgHeader : "#202020"
                                border.color: theme ? theme.borderSubtle : "#333333"
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 6
                                    spacing: 6

                                    // Detected Language Label
                                    Text {
                                        text: (segData && segData.lang ? segData.lang : "code").toUpperCase()
                                        color: theme ? theme.textSecondary : "#858585"
                                        font.pixelSize: 10
                                        font.bold: true
                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                        Layout.fillWidth: true
                                    }

                                    // Copy Button
                                    Rectangle {
                                        id: copyBtnRect
                                        property bool isCopied: false
                                        width: copyContentRow.implicitWidth + 10
                                        height: 18
                                        radius: 2
                                        color: copyBtnMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#333333") : "transparent"

                                        Timer {
                                            id: resetCopyTimer
                                            interval: 1800
                                            repeat: false
                                            onTriggered: copyBtnRect.isCopied = false
                                        }

                                        RowLayout {
                                            id: copyContentRow
                                            anchors.centerIn: parent
                                            spacing: 4

                                            VectorIcon {
                                                name: copyBtnRect.isCopied ? "check" : "copy"
                                                size: 10
                                                color: copyBtnRect.isCopied ? "#4ec9b0" : (theme ? theme.textSecondary : "#858585")
                                            }

                                            Text {
                                                text: copyBtnRect.isCopied ? "Copied" : "Copy"
                                                color: copyBtnRect.isCopied ? "#4ec9b0" : (copyBtnMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textSecondary : "#858585"))
                                                font.pixelSize: 10
                                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                            }
                                        }

                                        MouseArea {
                                            id: copyBtnMa
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                var targetCode = (segData && segData.code) ? segData.code : "";
                                                if (typeof backend !== "undefined" && backend && backend.copy_to_clipboard) {
                                                    backend.copy_to_clipboard(targetCode);
                                                } else if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.copy_to_clipboard) {
                                                    extensionManager.copy_to_clipboard(targetCode);
                                                }
                                                root.copyCodeRequested(targetCode);
                                                copyBtnRect.isCopied = true;
                                                resetCopyTimer.restart();
                                            }
                                        }
                                    }

                                    // Insert Button
                                    Rectangle {
                                        id: insertBtnRect
                                        width: insertContentRow.implicitWidth + 12
                                        height: 18
                                        radius: 2
                                        color: insertBtnMa.containsMouse ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgSurfaceHover : "#2a2d2e")

                                        RowLayout {
                                            id: insertContentRow
                                            anchors.centerIn: parent
                                            spacing: 3

                                            Text {
                                                text: "Insert"
                                                color: "#ffffff"
                                                font.pixelSize: 10
                                                font.bold: true
                                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                            }
                                        }

                                        ToolTip.visible: insertBtnMa.containsMouse
                                        ToolTip.text: "Insert at cursor or replace editor selection"

                                        MouseArea {
                                            id: insertBtnMa
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                var targetCode = (segData && segData.code) ? segData.code : "";
                                                root.insertCodeRequested(targetCode);
                                            }
                                        }
                                    }
                                }
                            }

                            // Code Body with horizontal & vertical scrolling
                            Flickable {
                                id: codeScrollFlickable
                                anchors.top: codeHeaderRect.bottom
                                anchors.left: parent.left
                                anchors.right: parent.right
                                implicitHeight: Math.min(320, codeTextEdit.contentHeight + 14)
                                contentWidth: Math.max(width - 16, codeTextEdit.contentWidth)
                                contentHeight: codeTextEdit.contentHeight + 14
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds

                                ScrollBar.vertical: ScrollBar {
                                    policy: codeTextEdit.contentHeight + 14 > 320 ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                                    width: 6
                                }
                                ScrollBar.horizontal: ScrollBar {
                                    policy: ScrollBar.AsNeeded
                                    height: 6
                                }

                                TextEdit {
                                    id: codeTextEdit
                                    anchors.left: parent.left
                                    anchors.top: parent.top
                                    anchors.margins: 7
                                    text: segData ? segData.code : ""
                                    color: theme ? theme.textBright : "#e0e0e0"
                                    font.pixelSize: 12
                                    font.family: theme ? theme.fontFamilyMono : "monospace"
                                    wrapMode: TextEdit.NoWrap
                                    readOnly: true
                                    selectByMouse: true
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

