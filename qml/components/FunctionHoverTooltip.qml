import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property bool isOpen: false
    property string symbol: ""
    property string signature: ""
    property string docText: ""
    property string kind: "function"

    visible: isOpen && (signature.length > 0 || docText.length > 0)
    z: 9997
    width: Math.min(Math.max(contentCol.implicitWidth + 32, 380), 680)
    height: contentCol.implicitHeight + 16
    radius: 6
    color: (typeof theme !== "undefined" && theme && theme.bgPopup) ? theme.bgPopup : "#1e1e24"
    border.color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#333338"
    border.width: 1

    // Drop shadow glow
    Rectangle {
        anchors.fill: parent
        anchors.margins: -2
        radius: 8
        color: "transparent"
        border.color: "#000000"
        opacity: 0.4
        z: -1
    }

    function showAt(targetX, targetY, sym, sig, doc, symKind, parentW, parentH, targetH) {
        symbol = sym || "";
        signature = sig || "";
        docText = doc || "";
        kind = symKind || "function";

        var pW = parentW || (parent ? parent.width : 800);
        var pH = parentH || (parent ? parent.height : 600);

        var calcW = Math.min(Math.max(contentCol.implicitWidth + 32, 380), 680);
        var estH = 46 + (docText ? Math.min(140, Math.max(30, Math.ceil(docText.length / 45) * 18)) : 0);
        var calcH = Math.max(contentCol.implicitHeight + 16, estH);

        // Center / anchor on top of the hovered word
        var posX = Math.max(12, Math.min(pW - calcW - 12, targetX - 16));
        var posY = targetY - calcH - 8;
        if (posY < 8) {
            var lineH = targetH || 20;
            posY = targetY + lineH + 8; // flip below only if word is on the very top visible row
        }
        x = posX;
        y = posY;
        width = calcW;
        isOpen = true;
    }

    function hide() {
        isOpen = false;
        symbol = "";
        signature = "";
        docText = "";
    }

    ColumnLayout {
        id: contentCol
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        // Header with Signature
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: sigText.implicitHeight + 10
            radius: 4
            color: (typeof theme !== "undefined" && theme && theme.bgEditor) ? theme.bgEditor : "#141417"
            border.color: (typeof theme !== "undefined" && theme && theme.borderSubtle) ? theme.borderSubtle : "#2b2b30"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6

                VectorIcon {
                    name: root.kind === "class" ? "box" : (root.kind === "variable" ? "tag" : "code")
                    size: 13
                    color: root.kind === "class" ? "#f59e0b" : "#38bdf8"
                }

                Text {
                    id: sigText
                    Layout.fillWidth: true
                    text: root.signature.length > 0 ? root.signature : root.symbol
                    color: (typeof theme !== "undefined" && theme && theme.textBright) ? theme.textBright : "#ffffff"
                    font.pixelSize: 11
                    font.family: (typeof theme !== "undefined" && theme && (theme.editorFontFamily || theme.fontFamilyMono)) ? (theme.editorFontFamily || theme.fontFamilyMono) : "Consolas, monospace"
                    wrapMode: Text.WrapAnywhere
                }
            }
        }

        // Divider
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: (typeof theme !== "undefined" && theme && theme.borderSubtle) ? theme.borderSubtle : "#2b2b30"
            visible: root.docText.length > 0
        }

        // Documentation Body
        Flickable {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(docContentText.implicitHeight, 140)
            contentWidth: width
            contentHeight: docContentText.implicitHeight
            clip: true
            visible: root.docText.length > 0
            interactive: docContentText.implicitHeight > 140

            Text {
                id: docContentText
                width: parent.width
                text: root.docText
                color: (typeof theme !== "undefined" && theme && theme.textPrimary) ? theme.textPrimary : "#cbd5e1"
                font.pixelSize: 11
                font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                wrapMode: Text.Wrap
                lineHeight: 1.2
            }
        }
    }
}

