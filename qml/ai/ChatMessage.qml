import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Rectangle {
    id: chatMessageRoot
    width: parent ? parent.width : 280
    color: isUser ? theme.bgHover : theme.bgCard
    radius: 8
    border.color: isUser ? theme.borderSubtle : theme.borderSubtle
    border.width: 1

    property string role: "assistant" // "user" or "assistant"
    property string content: ""
    property string timestamp: ""
    property bool isUser: role === "user"

    implicitHeight: mainCol.implicitHeight + 16

    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        anchors.margins: 10
        spacing: 6

        // Message Header (Role + Timestamp)
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            // Avatar circle / badge
            Rectangle {
                width: 18
                height: 18
                radius: 9
                color: isUser ? theme.accentColor : theme.accentSecondary

                Text {
                    text: isUser ? "U" : "AI"
                    color: "#ffffff"
                    font.pixelSize: 9
                    font.bold: true
                    anchors.centerIn: parent
                }
            }

            Text {
                text: isUser ? "You" : "Assistant"
                color: theme.textPrimary
                font.pixelSize: 11
                font.bold: true
                font.family: theme.uiFont
                Layout.fillWidth: true
            }

            Text {
                text: chatMessageRoot.timestamp
                color: theme.textMuted
                font.pixelSize: 9
                font.family: theme.uiFont
            }
        }

        // Message Body Repeater (detecting and splitting code blocks vs regular text)
        Repeater {
            model: parseContentBlocks(chatMessageRoot.content)

            delegate: Item {
                Layout.fillWidth: true
                implicitHeight: modelData.isCode ? codeBlockItem.implicitHeight : textItem.implicitHeight

                // Text item for regular markdown/prose
                Text {
                    id: textItem
                    visible: !modelData.isCode
                    width: parent.width
                    text: modelData.text
                    color: theme.textPrimary
                    font.pixelSize: 12
                    font.family: theme.uiFont
                    wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }

                // Code block item
                CodeBlock {
                    id: codeBlockItem
                    visible: modelData.isCode
                    width: parent.width
                    language: modelData.lang || "code"
                    codeText: modelData.text
                }
            }
        }
    }

    function parseContentBlocks(rawText) {
        if (!rawText) return []
        var blocks = []
        var parts = rawText.split("```")
        for (var i = 0; i < parts.length; i++) {
            var part = parts[i]
            if (i % 2 === 1) {
                // Code block: extract optional language from first line
                var firstLineEnd = part.indexOf("\n")
                var lang = "code"
                var code = part
                if (firstLineEnd !== -1) {
                    var candidateLang = part.substring(0, firstLineEnd).trim()
                    if (candidateLang.length > 0 && candidateLang.length < 15 && !candidateLang.includes(" ")) {
                        lang = candidateLang
                        code = part.substring(firstLineEnd + 1)
                    }
                }
                blocks.push({ isCode: true, text: code.trim(), lang: lang })
            } else {
                // Regular prose
                if (part.trim().length > 0) {
                    blocks.push({ isCode: false, text: part.trim(), lang: "" })
                }
            }
        }
        return blocks
    }
}
