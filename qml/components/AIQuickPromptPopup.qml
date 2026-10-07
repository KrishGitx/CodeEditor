import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: root
    objectName: "aiQuickPromptPopup"

    property bool isOpen: false

    signal promptSubmitted(string prompt)
    signal closeRequested()

    anchors.fill: parent
    visible: isOpen
    z: 9999

    // Backdrop
    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    function open(initialPrompt) {
        promptInput.text = initialPrompt || "";
        isOpen = true;
        promptInput.forceActiveFocus();
        if (promptInput.text.length > 0) {
            promptInput.selectAll();
        }
    }

    function close() {
        isOpen = false;
        root.closeRequested();
    }

    function submit() {
        var query = promptInput.text.trim();
        if (query.length > 0) {
            root.promptSubmitted(query);
            root.close();
        }
    }

    // Modal Card (Matching Quick Open design)
    Rectangle {
        id: promptCard
        width: Math.min(parent.width - 48, 520)
        height: 52
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 40
        radius: theme ? theme.radiusMd : 6
        color: theme ? theme.bgPopup : "#252526"
        border.color: theme ? theme.borderNormal : "#333333"
        border.width: 1

        // Elevation Glow
        Rectangle {
            anchors.fill: parent
            anchors.margins: -2
            radius: 8
            color: "transparent"
            border.color: "#000000"
            opacity: 0.35
            z: -1
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            spacing: 10

            VectorIcon {
                name: "sparkles"
                size: 16
                color: theme ? theme.accent : "#0078d4"
            }

            TextField {
                id: promptInput
                Layout.fillWidth: true
                placeholderText: "Ask AI..."
                placeholderTextColor: theme ? theme.textMuted : "#656565"
                color: theme ? theme.textBright : "#ffffff"
                font.pixelSize: 13
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                background: null
                selectByMouse: true
                selectionColor: theme ? theme.bgSelected : "#04395e"
                selectedTextColor: theme ? theme.textBright : "#ffffff"

                Keys.onReturnPressed: root.submit()
                Keys.onEnterPressed: root.submit()
                Keys.onEscapePressed: root.close()
            }

            Rectangle {
                width: 26
                height: 22
                radius: 3
                color: theme ? theme.bgSurface : "#1e1e1e"
                border.color: theme ? theme.borderSubtle : "#333333"
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "↵"
                    color: theme ? theme.textSecondary : "#858585"
                    font.pixelSize: 12
                    font.bold: true
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.submit()
                }
            }
        }
    }
}
