import re

term_path = "qml/components/TerminalPanel.qml"
with open(term_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add split terminal properties
split_props = '''    property bool isSplitTerminal: false
    property string secTerminalBuffer: "Windows PowerShell (Split Session 2)\\nCopyright (C) Microsoft Corporation. All rights reserved.\\n\\n"
    property bool isSecCommandRunning: false
'''

if "property bool isSplitTerminal:" not in content:
    content = content.replace(
        'property string activeTab: "TERMINAL"',
        split_props + '    property string activeTab: "TERMINAL"'
    )

# Connect sessionOutputReceived
session_signal_conn = '''        function onSessionOutputReceived(sessionId, text) {
            if (sessionId === 1) {
                if (text === "__CLEAR_BUFFER__") {
                    root.secTerminalBuffer = "";
                } else {
                    root.secTerminalBuffer += text;
                    scrollTimer.restart();
                }
            }
        }
'''

if "onSessionOutputReceived" not in content:
    content = content.replace(
        "function onOutputReceived(text) {",
        session_signal_conn + "\n        function onOutputReceived(text) {"
    )

# Add Split Terminal Button in Action Controls
split_btn = '''                    // Split Terminal Button
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
'''

if "Split Terminal Button" not in content:
    content = content.replace(
        "// + (New Session / Restart)",
        split_btn + "\n                    // + (New Session / Restart)"
    )

# Ensure executeCommand switches activeTab = "TERMINAL"
if 'root.activeTab = "TERMINAL";' not in content:
    content = content.replace(
        "function executeCommand(customCmd) {",
        'function executeCommand(customCmd) {\n        root.activeTab = "TERMINAL";'
    )

# Replace the single terminal pane with split-capable layout
old_term_view = '''            // =================================================================
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
                                id: activeTerminalPrompt
                                text: root.currentPrompt
                                color: theme ? theme.textSecondary : "#858585"
                                font.pixelSize: 12
                                font.family: theme ? theme.fontFamilyMono : "monospace"
                                visible: !root.isCommandRunning
                                Layout.preferredWidth: visible ? implicitWidth : 0
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
            }'''

new_term_view = '''            // =================================================================
            // VIEW A: INTERACTIVE TERMINAL (Supports Split Sessions)
            // =================================================================
            Item {
                anchors.fill: parent
                visible: root.activeTab === "TERMINAL"

                RowLayout {
                    anchors.fill: parent
                    spacing: 0

                    // Primary Terminal Pane
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
                                        id: activeTerminalPrompt
                                        text: root.currentPrompt
                                        color: theme ? theme.textSecondary : "#858585"
                                        font.pixelSize: 12
                                        font.family: theme ? theme.fontFamilyMono : "monospace"
                                        visible: !root.isCommandRunning
                                        Layout.preferredWidth: visible ? implicitWidth : 0
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

                    // Split Divider & Secondary Split Pane
                    Rectangle {
                        visible: root.isSplitTerminal
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#2a3145"
                    }

                    Item {
                        visible: root.isSplitTerminal
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
                                    text: root.secTerminalBuffer
                                    textFormat: TextEdit.PlainText
                                }

                                RowLayout {
                                    width: parent.width
                                    spacing: 4

                                    Text {
                                        text: root.currentPrompt
                                        color: theme ? theme.textSecondary : "#858585"
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
            }'''

content = content.replace(old_term_view, new_term_view)

with open(term_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied split terminal enhancements to TerminalPanel.qml")
