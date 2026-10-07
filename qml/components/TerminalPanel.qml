import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    signal closeRequested()
    signal problemSelected(string filePath, int line, int column)

    color: theme ? theme.bgTerminal : "#181818"

        property bool isSplitTerminal: false
    property string secTerminalBuffer: ""
    property bool isSecCommandRunning: false
    property string activeTab: "TERMINAL" // "TERMINAL", "OUTPUT", "PROBLEMS"
    property var commandHistory: []
    property int historyIndex: -1
    property bool isCommandRunning: (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.is_running_cmd) ? terminalBackend.is_running_cmd() : false
    property string currentCwd: (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.get_cwd) ? terminalBackend.get_cwd() : ((typeof backend !== "undefined" && backend && backend.folder_path) ? backend.folder_path : "C:\\")
    property string currentPrompt: (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.get_prompt) ? terminalBackend.get_prompt() : ("PS " + currentCwd + "> ")
    property string terminalBuffer: ""
    property string outputBuffer: "[DGX Output & Execution Channel Ready]\n"

    readonly property var promptMatch: {
        var buf = root.terminalBuffer;
        return buf ? buf.match(/(?:^|\r?\n)(PS [^\r\n>]+> ?|[^\r\n$]+[$#] ?)$/) : null;
    }
    readonly property string realPrompt: promptMatch ? promptMatch[1] : (root.currentPrompt || "PS > ")
    readonly property string displayedHistory: {
        if (!root.terminalBuffer) return "";
        if (promptMatch) {
            var idx = root.terminalBuffer.lastIndexOf(promptMatch[1]);
            if (idx >= 0) {
                return root.terminalBuffer.substring(0, idx);
            }
        }
        return root.terminalBuffer;
    }

    readonly property var secPromptMatch: {
        var buf = root.secTerminalBuffer;
        return buf ? buf.match(/(?:^|\r?\n)(PS [^\r\n>]+> ?|[^\r\n$]+[$#] ?)$/) : null;
    }
    readonly property string secRealPrompt: secPromptMatch ? secPromptMatch[1] : (root.currentPrompt || "PS > ")
    readonly property string secDisplayedHistory: {
        if (!root.secTerminalBuffer) return "";
        if (secPromptMatch) {
            var idx = root.secTerminalBuffer.lastIndexOf(secPromptMatch[1]);
            if (idx >= 0) {
                return root.secTerminalBuffer.substring(0, idx);
            }
        }
        return root.secTerminalBuffer;
    }

    ListModel {
        id: problemsModel
    }

    Connections {
        target: typeof terminalBackend !== "undefined" ? terminalBackend : null
        ignoreUnknownSignals: true

                function onSessionOutputReceived(sessionId, text) {
            if (sessionId === 1) {
                if (text === "__CLEAR_BUFFER__") {
                    root.secTerminalBuffer = "";
                } else {
                    root.secTerminalBuffer += text;
                    scrollTimer.restart();
                }
            }
        }

        function onOutputReceived(text) {
            if (text === "__CLEAR_BUFFER__") {
                root.terminalBuffer = "";
            } else {
                root.terminalBuffer += text;
                scrollTimer.restart();
            }
        }

        function onCommandRunningChanged(running) {
            root.isCommandRunning = running;
        }

        function onCwdChanged(newCwd) {
            root.currentCwd = newCwd;
            if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.get_prompt) {
                root.currentPrompt = terminalBackend.get_prompt();
            } else {
                root.currentPrompt = "PS " + newCwd + "> ";
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

                                        // Split Terminal Button
                    Rectangle {
                        width: 20
                        height: 20
                        radius: 2
                        visible: root.activeTab === "TERMINAL"
                        color: root.isSplitTerminal ? (theme ? theme.accent : "#0078d4") : (splitMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "zen"
                            size: 11
                            color: root.isSplitTerminal ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                        }

                        ToolTip.visible: splitMa.containsMouse
                        ToolTip.text: root.isSplitTerminal ? "Unsplit Terminal" : "Split Terminal"

                        MouseArea {
                            id: splitMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.isSplitTerminal = !root.isSplitTerminal;
                                if (root.isSplitTerminal && typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.create_session) {
                                    terminalBackend.create_session();
                                }
                            }
                        }
                    }

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
            // VIEW A: INTERACTIVE TERMINAL (Supports Split Sessions)
            // =================================================================
            Item {
                anchors.fill: parent
                visible: root.activeTab === "TERMINAL"

                RowLayout {
                    anchors.fill: parent
                    spacing: 0

                    // Primary Terminal Pane
                    ColumnLayout {
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        spacing: 0

                        // Split pane header (only shown when split is active)
                        Rectangle {
                            Layout.fillWidth: true
                            height: 22
                            visible: root.isSplitTerminal
                            color: theme ? theme.bgHeader : "#1f1f1f"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 6
                                spacing: 4

                                Text {
                                    text: "1: PowerShell"
                                    color: theme ? theme.textSecondary : "#999999"
                                    font.pixelSize: 10
                                    font.bold: true
                                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                    Layout.fillWidth: true
                                }

                                Rectangle {
                                    width: 16
                                    height: 16
                                    radius: 2
                                    color: pCloseMa.containsMouse ? (theme ? theme.error : "#f14c4c") : "transparent"

                                    VectorIcon {
                                        anchors.centerIn: parent
                                        name: "close"
                                        size: 8
                                        color: pCloseMa.containsMouse ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                    }

                                    ToolTip.visible: pCloseMa.containsMouse
                                    ToolTip.text: "Close Terminal Split 1"

                                    MouseArea {
                                        id: pCloseMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.close_session) {
                                                terminalBackend.close_session(0);
                                            }
                                            root.terminalBuffer = root.secTerminalBuffer;
                                            root.secTerminalBuffer = "";
                                            root.isSplitTerminal = false;
                                        }
                                    }
                                }
                            }
                        }

                        Item {
                            Layout.fillHeight: true
                            Layout.fillWidth: true

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
                                        text: root.displayedHistory
                                        textFormat: TextEdit.PlainText

                                        TapHandler {
                                            onTapped: activeTerminalInput.forceActiveFocus()
                                        }
                                    }

                                    RowLayout {
                                        width: parent.width
                                        spacing: 4
                                        visible: !root.isCommandRunning

                                        Text {
                                            text: root.realPrompt
                                            color: theme ? theme.accent : "#0078d4"
                                            font.pixelSize: 12
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
                                                if (event.key === Qt.Key_C && (event.modifiers & Qt.ControlModifier)) {
                                                    if (root.isCommandRunning || activeTerminalInput.selectedText.length === 0) {
                                                        if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.send_interrupt) {
                                                            terminalBackend.send_interrupt();
                                                        }
                                                        activeTerminalInput.text = "";
                                                        scrollTimer.restart();
                                                        event.accepted = true;
                                                        return;
                                                    }
                                                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                                    root.executeCommand();
                                                    event.accepted = true;
                                                } else if (event.key === Qt.Key_Up) {
                                                    if (!root.isCommandRunning && root.commandHistory.length > 0) {
                                                        if (root.historyIndex < root.commandHistory.length - 1) {
                                                            root.historyIndex++;
                                                            activeTerminalInput.text = root.commandHistory[root.commandHistory.length - 1 - root.historyIndex];
                                                        }
                                                    }
                                                    event.accepted = true;
                                                } else if (event.key === Qt.Key_Down) {
                                                    if (!root.isCommandRunning) {
                                                        if (root.historyIndex > 0) {
                                                            root.historyIndex--;
                                                            activeTerminalInput.text = root.commandHistory[root.commandHistory.length - 1 - root.historyIndex];
                                                        } else if (root.historyIndex === 0) {
                                                            root.historyIndex = -1;
                                                            activeTerminalInput.text = "";
                                                        }
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

                    // Split Divider & Secondary Split Pane
                    Rectangle {
                        visible: root.isSplitTerminal
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#2a3145"
                    }

                    ColumnLayout {
                        visible: root.isSplitTerminal
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        spacing: 0

                        // Split pane header
                        Rectangle {
                            Layout.fillWidth: true
                            height: 22
                            color: theme ? theme.bgHeader : "#1f1f1f"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 6
                                spacing: 4

                                Text {
                                    text: "2: PowerShell"
                                    color: theme ? theme.textSecondary : "#999999"
                                    font.pixelSize: 10
                                    font.bold: true
                                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                    Layout.fillWidth: true
                                }

                                Rectangle {
                                    width: 16
                                    height: 16
                                    radius: 2
                                    color: sCloseMa.containsMouse ? (theme ? theme.error : "#f14c4c") : "transparent"

                                    VectorIcon {
                                        anchors.centerIn: parent
                                        name: "close"
                                        size: 8
                                        color: sCloseMa.containsMouse ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                    }

                                    ToolTip.visible: sCloseMa.containsMouse
                                    ToolTip.text: "Close Terminal Split 2"

                                    MouseArea {
                                        id: sCloseMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.close_session) {
                                                terminalBackend.close_session(1);
                                            }
                                            root.secTerminalBuffer = "";
                                            root.isSplitTerminal = false;
                                        }
                                    }
                                }
                            }
                        }

                        Item {
                            Layout.fillHeight: true
                            Layout.fillWidth: true

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.IBeamCursor
                                onClicked: secTerminalInput.forceActiveFocus()
                            }

                            Flickable {
                                id: secTerminalFlickable
                                anchors.fill: parent
                                contentWidth: width
                                contentHeight: Math.max(height, secTerminalContentCol.height + 24)
                                boundsBehavior: Flickable.StopAtBounds
                                clip: true

                                ScrollBar.vertical: ScrollBar {
                                    policy: ScrollBar.AsNeeded
                                    width: 8
                                }

                                Column {
                                    id: secTerminalContentCol
                                    width: parent.width - 16
                                    x: 8
                                    y: 6
                                    spacing: 2

                                    TextEdit {
                                        id: secTerminalHistoryView
                                        width: parent.width
                                        readOnly: true
                                        selectByMouse: true
                                        color: theme ? theme.textPrimary : "#cccccc"
                                        font.pixelSize: 12
                                        font.family: theme ? theme.fontFamilyMono : "monospace"
                                        wrapMode: TextEdit.Wrap
                                        text: root.secDisplayedHistory
                                        textFormat: TextEdit.PlainText
                                    }

                                    RowLayout {
                                        width: parent.width
                                        spacing: 4

                                        Text {
                                            text: root.secRealPrompt
                                            color: theme ? theme.accent : "#0078d4"
                                            font.pixelSize: 12
                                            font.family: theme ? theme.fontFamilyMono : "monospace"
                                        }

                                        TextInput {
                                            id: secTerminalInput
                                            Layout.fillWidth: true
                                            color: theme ? theme.textBright : "#ffffff"
                                            font.pixelSize: 12
                                            font.family: theme ? theme.fontFamilyMono : "monospace"
                                            selectByMouse: true
                                            cursorVisible: activeFocus

                                            Keys.onPressed: function(event) {
                                                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                                    var cmd = secTerminalInput.text;
                                                    secTerminalInput.text = "";
                                                    if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.send_session_command) {
                                                        terminalBackend.send_session_command(1, cmd);
                                                    }
                                                    event.accepted = true;
                                                } else if (event.key === Qt.Key_C && (event.modifiers & Qt.ControlModifier)) {
                                                    if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.send_session_interrupt) {
                                                        terminalBackend.send_session_interrupt(1);
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
        var cmd = (typeof customCmd !== "undefined") ? customCmd : activeTerminalInput.text;
        if (!customCmd) {
            if (cmd.trim().length > 0) {
                root.commandHistory.push(cmd);
                root.historyIndex = -1;
            }
            activeTerminalInput.text = "";
        }

        if (!root.isCommandRunning) {
            // Support 'clear' and 'cls' commands directly when at shell prompt
            if (cmd.trim().toLowerCase() === "clear" || cmd.trim().toLowerCase() === "cls") {
                root.clearTerminal();
                return;
            }
        }

        if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.send_command) {
            terminalBackend.send_command(cmd);
        } else {
            if (!root.isCommandRunning) {
                root.terminalBuffer += root.currentPrompt + cmd + "\n";
            }
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
