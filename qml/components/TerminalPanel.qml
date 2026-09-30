import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    signal closeRequested()

    color: theme ? theme.bgTerminal : "#181818"

    property string activeTab: "TERMINAL"
    property var commandHistory: []
    property int historyIndex: -1
    property string terminalBuffer: "PowerShell 7.x / DGX Integrated Terminal\nReady for input.\n"
    property string outputBuffer: "[DGX Build & Output log empty]\n"
    property string problemsBuffer: "No problems have been detected in the workspace.\n"

    Connections {
        target: typeof terminalBackend !== "undefined" ? terminalBackend : null
        ignoreUnknownSignals: true

        function onOutputReceived(text) {
            if (text === "__CLEAR_BUFFER__") {
                root.terminalBuffer = "";
            } else {
                root.terminalBuffer += text;
                if (!root.terminalBuffer.endsWith("\n")) {
                    root.terminalBuffer += "\n";
                }
                scrollTimer.restart();
            }
        }
    }

    Timer {
        id: scrollTimer
        interval: 30
        repeat: false
        onTriggered: {
            terminalFlickable.contentY = Math.max(0, terminalFlickable.contentHeight - terminalFlickable.height);
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. VS Code Style Header & Tabs Bar
        Rectangle {
            Layout.fillWidth: true
            height: 28
            color: theme ? theme.bgHeader : "#181818"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 2

                // Terminal Tabs (TERMINAL, OUTPUT, PROBLEMS)
                Row {
                    spacing: 12
                    Layout.fillHeight: true

                    // TERMINAL Tab
                    Rectangle {
                        height: parent.height
                        width: termTabText.contentWidth + 12
                        color: "transparent"

                        Text {
                            id: termTabText
                            anchors.centerIn: parent
                            text: "TERMINAL"
                            color: root.activeTab === "TERMINAL" ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                            font.pixelSize: 11
                            font.bold: root.activeTab === "TERMINAL"
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.left: parent.left
                            anchors.right: parent.right
                            height: 1
                            color: theme ? theme.accent : "#0078d4"
                            visible: root.activeTab === "TERMINAL"
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.activeTab = "TERMINAL";
                                activeTerminalInput.forceActiveFocus();
                            }
                        }
                    }

                    // OUTPUT Tab
                    Rectangle {
                        height: parent.height
                        width: outTabText.contentWidth + 12
                        color: "transparent"

                        Text {
                            id: outTabText
                            anchors.centerIn: parent
                            text: "OUTPUT"
                            color: root.activeTab === "OUTPUT" ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                            font.pixelSize: 11
                            font.bold: root.activeTab === "OUTPUT"
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.left: parent.left
                            anchors.right: parent.right
                            height: 1
                            color: theme ? theme.accent : "#0078d4"
                            visible: root.activeTab === "OUTPUT"
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.activeTab = "OUTPUT"
                        }
                    }

                    // PROBLEMS Tab
                    Rectangle {
                        height: parent.height
                        width: probTabText.contentWidth + 12
                        color: "transparent"

                        Text {
                            id: probTabText
                            anchors.centerIn: parent
                            text: "PROBLEMS"
                            color: root.activeTab === "PROBLEMS" ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                            font.pixelSize: 11
                            font.bold: root.activeTab === "PROBLEMS"
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.left: parent.left
                            anchors.right: parent.right
                            height: 1
                            color: theme ? theme.accent : "#0078d4"
                            visible: root.activeTab === "PROBLEMS"
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.activeTab = "PROBLEMS"
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Action Controls on right
                RowLayout {
                    spacing: 4

                    // + (New Session / Restart)
                    Rectangle {
                        width: 20
                        height: 20
                        radius: 2
                        color: newMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "new-file"
                            size: 11
                            color: theme ? theme.textSecondary : "#858585"
                        }

                        ToolTip.visible: newMa.containsMouse
                        ToolTip.text: "New Terminal"

                        MouseArea {
                            id: newMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.restart) {
                                    terminalBackend.restart();
                                }
                                root.terminalBuffer += "\n[Session restarted]\n";
                            }
                        }
                    }

                    // Clear (Trash icon)
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
                        ToolTip.text: "Clear Terminal"

                        MouseArea {
                            id: clearMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.clearTerminal()
                        }
                    }

                    // Close Panel (x)
                    Rectangle {
                        width: 20
                        height: 20
                        radius: 2
                        color: closeMa.containsMouse ? (theme ? theme.error : "#f14c4c") : "transparent"

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "close"
                            size: 9
                            color: closeMa.containsMouse ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
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
        }

        // 2. VS Code Interactive Terminal Screen
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.IBeamCursor
                onClicked: {
                    if (root.activeTab === "TERMINAL") {
                        activeTerminalInput.forceActiveFocus();
                    }
                }
            }

            Flickable {
                id: terminalFlickable
                anchors.fill: parent
                contentWidth: width
                contentHeight: Math.max(height, terminalContentColumn.height + 24)
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                TapHandler {
                    onTapped: {
                        if (root.activeTab === "TERMINAL") {
                            activeTerminalInput.forceActiveFocus();
                        }
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    width: 8
                }

                Column {
                    id: terminalContentColumn
                    width: parent.width - 16
                    x: 8
                    y: 6
                    spacing: 2

                    // 1. Terminal Log Buffer
                    TextEdit {
                        id: terminalHistoryView
                        width: parent.width
                        readOnly: true
                        selectByMouse: true
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        font.family: theme ? theme.fontFamilyMono : "monospace"
                        wrapMode: TextEdit.Wrap
                        text: root.activeTab === "TERMINAL" ? root.terminalBuffer : (root.activeTab === "OUTPUT" ? root.outputBuffer : root.problemsBuffer)
                        textFormat: TextEdit.PlainText

                        TapHandler {
                            onTapped: {
                                if (root.activeTab === "TERMINAL") {
                                    activeTerminalInput.forceActiveFocus();
                                }
                            }
                        }
                    }

                    // 2. Inline Interactive Prompt Line (Only visible on TERMINAL tab)
                    RowLayout {
                        width: parent.width
                        spacing: 4
                        visible: root.activeTab === "TERMINAL"

                        Text {
                            text: "PS >"
                            color: theme ? theme.accent : "#0078d4"
                            font.pixelSize: 12
                            font.bold: true
                            font.family: theme ? theme.fontFamilyMono : "monospace"
                        }

                        TextInput {
                            id: activeTerminalInput
                            Layout.fillWidth: true
                            color: theme ? theme.textBright : "#ffffff"
                            font.pixelSize: 12
                            font.family: theme ? theme.fontFamilyMono : "monospace"
                            selectByMouse: true
                            focus: root.activeTab === "TERMINAL"
                            cursorVisible: activeFocus

                            Keys.onPressed: function(event) {
                                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                    root.executeCommand();
                                    event.accepted = true;
                                } else if (event.key === Qt.Key_Up) {
                                    if (root.commandHistory.length > 0) {
                                        if (root.historyIndex < root.commandHistory.length - 1) {
                                            root.historyIndex++;
                                            activeTerminalInput.text = root.commandHistory[root.commandHistory.length - 1 - root.historyIndex];
                                        }
                                    }
                                    event.accepted = true;
                                } else if (event.key === Qt.Key_Down) {
                                    if (root.historyIndex > 0) {
                                        root.historyIndex--;
                                        activeTerminalInput.text = root.commandHistory[root.commandHistory.length - 1 - root.historyIndex];
                                    } else if (root.historyIndex === 0) {
                                        root.historyIndex = -1;
                                        activeTerminalInput.text = "";
                                    }
                                    event.accepted = true;
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    function executeCommand(customCmd) {
        var cmd = customCmd || activeTerminalInput.text.trim();
        if (!cmd) return;

        if (!customCmd) {
            root.commandHistory.push(cmd);
            root.historyIndex = -1;
            activeTerminalInput.text = "";
        }

        // Support 'clear' and 'cls' commands directly
        if (cmd.toLowerCase() === "clear" || cmd.toLowerCase() === "cls") {
            root.clearTerminal();
            return;
        }

        root.terminalBuffer += "PS > " + cmd + "\n";
        scrollTimer.restart();

        if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.send_command) {
            terminalBackend.send_command(cmd);
        } else {
            root.terminalBuffer += "[DGX Simulated]: " + cmd + "\n";
            scrollTimer.restart();
        }
    }

    function clearTerminal() {
        if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.clear) {
            terminalBackend.clear();
        } else {
            root.terminalBuffer = "";
        }
    }
}
