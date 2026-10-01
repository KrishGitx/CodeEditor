import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    signal closeRequested()
    signal problemSelected(string filePath, int line, int column)

    color: theme ? theme.bgTerminal : "#181818"

    property string activeTab: "TERMINAL" // "TERMINAL", "OUTPUT", "PROBLEMS"
    property var commandHistory: []
    property int historyIndex: -1
    property string terminalBuffer: "PowerShell 7.x / DGX Integrated Terminal\nReady for input.\n"
    property string outputBuffer: "[DGX Output & Execution Channel Ready]\n"

    ListModel {
        id: problemsModel
    }

    Connections {
        target: typeof terminalBackend !== "undefined" ? terminalBackend : null
        ignoreUnknownSignals: true

        function onOutputReceived(text) {
            if (text === "__CLEAR_BUFFER__") {
                root.terminalBuffer = "";
            } else {
                root.terminalBuffer += text;
                scrollTimer.restart();
            }
        }
    }

    Connections {
        target: typeof backend !== "undefined" ? backend : null
        ignoreUnknownSignals: true

        function onDiagnosticsUpdated(problems) {
            problemsModel.clear();
            if (problems && problems.length > 0) {
                for (var i = 0; i < problems.length; i++) {
                    problemsModel.append(problems[i]);
                }
            }
        }

        function onOutputLogReceived(channel, text) {
            var ts = new Date().toLocaleTimeString();
            root.outputBuffer += "[" + ts + "] [" + channel + "] " + text + "\n";
            scrollTimer.restart();
        }
    }

    function addOutputLog(channel, text) {
        var ts = new Date().toLocaleTimeString();
        root.outputBuffer += "[" + ts + "] [" + channel + "] " + text + "\n";
        scrollTimer.restart();
    }

    Timer {
        id: scrollTimer
        interval: 30
        repeat: false
        onTriggered: {
            if (root.activeTab === "TERMINAL") {
                terminalFlickable.contentY = Math.max(0, terminalFlickable.contentHeight - terminalFlickable.height);
            } else if (root.activeTab === "OUTPUT") {
                outputFlickable.contentY = Math.max(0, outputFlickable.contentHeight - outputFlickable.height);
            }
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

                    // 1.1 TERMINAL Tab
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

                    // 1.2 OUTPUT Tab
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

                    // 1.3 PROBLEMS Tab (with dynamic count badge)
                    Rectangle {
                        height: parent.height
                        width: probRow.width + 12
                        color: "transparent"

                        Row {
                            id: probRow
                            anchors.centerIn: parent
                            spacing: 5

                            Text {
                                text: "PROBLEMS"
                                color: root.activeTab === "PROBLEMS" ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                                font.pixelSize: 11
                                font.bold: root.activeTab === "PROBLEMS"
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            }

                            // Error Count Badge Pill
                            Rectangle {
                                width: Math.max(16, countText.contentWidth + 6)
                                height: 14
                                radius: 7
                                anchors.verticalCenter: parent.verticalCenter
                                color: problemsModel.count > 0 ? (theme ? theme.error : "#f14c4c") : (theme ? theme.bgSurfaceActive : "#2a2d2e")
                                visible: problemsModel.count > 0

                                Text {
                                    id: countText
                                    anchors.centerIn: parent
                                    text: problemsModel.count.toString()
                                    color: "#ffffff"
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }
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
                        visible: root.activeTab === "TERMINAL"
                        color: newMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "new-file"
                            size: 11
                            color: theme ? theme.textSecondary : "#858585"
                        }

                        ToolTip.visible: newMa.containsMouse
                        ToolTip.text: "Restart Terminal Session"

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

                    // Clear (Trash / Refresh icon)
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
                        ToolTip.text: root.activeTab === "OUTPUT" ? "Clear Output" : (root.activeTab === "PROBLEMS" ? "Re-scan Problems" : "Clear Terminal")

                        MouseArea {
                            id: clearMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.activeTab === "OUTPUT") {
                                    root.outputBuffer = "";
                                } else if (root.activeTab === "PROBLEMS") {
                                    if (typeof backend !== "undefined" && backend && backend.check_diagnostics) {
                                        backend.check_diagnostics("", "", "");
                                    }
                                } else {
                                    root.clearTerminal();
                                }
                            }
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

        // 2. Interactive Terminal / Output / Problems Screen
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            // =================================================================
            // VIEW A: INTERACTIVE TERMINAL
            // =================================================================
            Item {
                anchors.fill: parent
                visible: root.activeTab === "TERMINAL"

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.IBeamCursor
                    onClicked: activeTerminalInput.forceActiveFocus()
                }

                Flickable {
                    id: terminalFlickable
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: Math.max(height, terminalContentColumn.height + 24)
                    boundsBehavior: Flickable.StopAtBounds
                    clip: true

                    TapHandler {
                        onTapped: activeTerminalInput.forceActiveFocus()
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

                        TextEdit {
                            id: terminalHistoryView
                            width: parent.width
                            readOnly: true
                            selectByMouse: true
                            color: theme ? theme.textPrimary : "#cccccc"
                            font.pixelSize: 12
                            font.family: theme ? theme.fontFamilyMono : "monospace"
                            wrapMode: TextEdit.Wrap
                            text: root.terminalBuffer
                            textFormat: TextEdit.PlainText

                            TapHandler {
                                onTapped: activeTerminalInput.forceActiveFocus()
                            }
                        }

                        RowLayout {
                            width: parent.width
                            spacing: 4

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

            // =================================================================
            // VIEW B: OUTPUT LOG STREAM
            // =================================================================
            Item {
                anchors.fill: parent
                visible: root.activeTab === "OUTPUT"

                Flickable {
                    id: outputFlickable
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: Math.max(height, outputTextEdit.contentHeight + 24)
                    boundsBehavior: Flickable.StopAtBounds
                    clip: true

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                        width: 8
                    }

                    TextEdit {
                        id: outputTextEdit
                        width: parent.width - 16
                        x: 8
                        y: 6
                        readOnly: true
                        selectByMouse: true
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        font.family: theme ? theme.fontFamilyMono : "monospace"
                        wrapMode: TextEdit.Wrap
                        text: root.outputBuffer
                        textFormat: TextEdit.PlainText
                    }
                }
            }

            // =================================================================
            // VIEW C: LIVE PROBLEMS & DIAGNOSTICS INSPECTOR
            // =================================================================
            Item {
                anchors.fill: parent
                visible: root.activeTab === "PROBLEMS"

                // C.1 Empty State (Zero problems)
                Item {
                    anchors.fill: parent
                    visible: problemsModel.count === 0

                    Column {
                        anchors.centerIn: parent
                        spacing: 8

                        VectorIcon {
                            anchors.horizontalCenter: parent.horizontalCenter
                            name: "check"
                            size: 24
                            color: "#22c55e"
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "No problems have been detected in the workspace."
                            color: theme ? theme.textSecondary : "#858585"
                            font.pixelSize: 12
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        }
                    }
                }

                // C.2 Problems List View
                ListView {
                    id: problemsListView
                    anchors.fill: parent
                    anchors.margins: 4
                    visible: problemsModel.count > 0
                    model: problemsModel
                    clip: true
                    spacing: 2

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                        width: 8
                    }

                    delegate: Rectangle {
                        width: problemsListView.width
                        height: 32
                        radius: 3
                        color: probMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 8

                            // Error / Warning Vector Icon
                            VectorIcon {
                                name: (model.severity === "error") ? "close" : "sparkles"
                                size: 11
                                color: (model.severity === "error") ? (theme ? theme.error : "#f14c4c") : "#eab308"
                            }

                            // Error message description
                            Text {
                                text: model.message || "Syntax issue detected"
                                color: theme ? theme.textBright : "#ffffff"
                                font.pixelSize: 12
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            // Location Badge [File (line, col)]
                            Rectangle {
                                height: 18
                                width: locText.contentWidth + 10
                                radius: 3
                                color: theme ? theme.bgInput : "#252526"
                                border.color: theme ? theme.borderSubtle : "#333333"

                                Text {
                                    id: locText
                                    anchors.centerIn: parent
                                    text: (model.file || "file") + " [" + model.line + ":" + model.column + "]"
                                    color: theme ? theme.accent : "#0078d4"
                                    font.pixelSize: 10
                                    font.family: theme ? theme.fontFamilyMono : "monospace"
                                }
                            }

                            // Source Badge (e.g. Python Parser)
                            Text {
                                text: model.source || "Linter"
                                color: theme ? theme.textMuted : "#656565"
                                font.pixelSize: 10
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            }
                        }

                        MouseArea {
                            id: probMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.problemSelected(model.filePath || "", model.line || 1, model.column || 1);
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
