import re

term_path = "qml/components/TerminalPanel.qml"
with open(term_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the split terminal section in TerminalPanel.qml with clean individual session header bars and close buttons
old_split_section = re.search(r'// =================================================================\n\s*// VIEW A: INTERACTIVE TERMINAL[\s\S]*?// =================================================================\n\s*// VIEW B: OUTPUT LOG STREAM', content)

new_split_section = '''// =================================================================
            // VIEW A: INTERACTIVE TERMINAL (With Individual Session Split Controls)
            // =================================================================
            Item {
                anchors.fill: parent
                visible: root.activeTab === "TERMINAL"

                RowLayout {
                    anchors.fill: parent
                    spacing: 0

                    // 1. Primary Terminal Pane (Session 0)
                    ColumnLayout {
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        spacing: 0

                        // Session 1 Header Bar (Visible in split mode)
                        Rectangle {
                            visible: root.isSplitTerminal
                            Layout.fillWidth: true
                            height: 22
                            color: (typeof theme !== "undefined" && theme && theme.bgHeader) ? theme.bgHeader : "#1f1f23"
                            border.color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#2a2d2e"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 6
                                spacing: 4

                                Text {
                                    text: "Terminal 1 (PowerShell)"
                                    color: (typeof theme !== "undefined" && theme && theme.textSecondary) ? theme.textSecondary : "#858585"
                                    font.pixelSize: 10
                                    font.bold: true
                                    Layout.fillWidth: true
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
                                        color: (typeof theme !== "undefined" && theme && theme.textPrimary) ? theme.textPrimary : "#cccccc"
                                        font.pixelSize: 12
                                        font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyMono) ? theme.fontFamilyMono : "monospace"
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
                                            color: (typeof theme !== "undefined" && theme && theme.textSecondary) ? theme.textSecondary : "#858585"
                                            font.pixelSize: 12
                                            font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyMono) ? theme.fontFamilyMono : "monospace"
                                            visible: !root.isCommandRunning
                                            Layout.preferredWidth: visible ? implicitWidth : 0
                                        }

                                        TextInput {
                                            id: activeTerminalInput
                                            Layout.fillWidth: true
                                            color: (typeof theme !== "undefined" && theme && theme.textBright) ? theme.textBright : "#ffffff"
                                            font.pixelSize: 12
                                            font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyMono) ? theme.fontFamilyMono : "monospace"
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

                    // 2. Split Divider
                    Rectangle {
                        visible: root.isSplitTerminal
                        Layout.fillHeight: true
                        Layout.preferredWidth: 1
                        color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#2a3145"
                    }

                    // 3. Secondary Terminal Pane (Session 1 with dedicated Close [X] Button)
                    ColumnLayout {
                        visible: root.isSplitTerminal
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        spacing: 0

                        // Session 2 Header Bar with Close Button
                        Rectangle {
                            Layout.fillWidth: true
                            height: 22
                            color: (typeof theme !== "undefined" && theme && theme.bgHeader) ? theme.bgHeader : "#1f1f23"
                            border.color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#2a2d2e"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 6
                                spacing: 4

                                Text {
                                    text: "Terminal 2 (Split Session)"
                                    color: (typeof theme !== "undefined" && theme && theme.textSecondary) ? theme.textSecondary : "#858585"
                                    font.pixelSize: 10
                                    font.bold: true
                                    Layout.fillWidth: true
                                }

                                // Clear X Close Button for Split Terminal Session
                                Rectangle {
                                    width: 18
                                    height: 18
                                    radius: 2
                                    color: secCloseMa.containsMouse ? ((typeof theme !== "undefined" && theme && theme.error) ? theme.error : "#f14c4c") : "transparent"

                                    VectorIcon {
                                        anchors.centerIn: parent
                                        name: "close"
                                        size: 8
                                        color: secCloseMa.containsMouse ? "#ffffff" : ((typeof theme !== "undefined" && theme && theme.textSecondary) ? theme.textSecondary : "#858585")
                                    }

                                    ToolTip.visible: secCloseMa.containsMouse
                                    ToolTip.text: "Close this split terminal"

                                    MouseArea {
                                        id: secCloseMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (typeof terminalBackend !== "undefined" && terminalBackend && terminalBackend.close_session) {
                                                terminalBackend.close_session(1);
                                            }
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
                                        color: (typeof theme !== "undefined" && theme && theme.textPrimary) ? theme.textPrimary : "#cccccc"
                                        font.pixelSize: 12
                                        font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyMono) ? theme.fontFamilyMono : "monospace"
                                        wrapMode: TextEdit.Wrap
                                        text: root.secTerminalBuffer
                                        textFormat: TextEdit.PlainText
                                    }

                                    RowLayout {
                                        width: parent.width
                                        spacing: 4

                                        Text {
                                            text: root.currentPrompt
                                            color: (typeof theme !== "undefined" && theme && theme.textSecondary) ? theme.textSecondary : "#858585"
                                            font.pixelSize: 12
                                            font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyMono) ? theme.fontFamilyMono : "monospace"
                                        }

                                        TextInput {
                                            id: secTerminalInput
                                            Layout.fillWidth: true
                                            color: (typeof theme !== "undefined" && theme && theme.textBright) ? theme.textBright : "#ffffff"
                                            font.pixelSize: 12
                                            font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyMono) ? theme.fontFamilyMono : "monospace"
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
            // VIEW B: OUTPUT LOG STREAM'''

if old_split_section:
    content = content[:old_split_section.start()] + new_split_section + content[old_split_section.end():]

with open(term_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied individual close button and split headers to TerminalPanel.qml")
