with open('qml/components/SettingsDialog.qml', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Ensure loadRadialConfig() is called on completed and visible changed
old_comp_completed = """    Component.onCompleted: {
        root.activeCategoryIndex = 0;
    }"""

new_comp_completed = """    Component.onCompleted: {
        root.activeCategoryIndex = 0;
        root.loadRadialConfig();
    }
    onVisibleChanged: {
        if (visible) {
            root.loadRadialConfig();
        }
    }"""

if old_comp_completed in content:
    content = content.replace(old_comp_completed, new_comp_completed, 1)
    print("Added loadRadialConfig calls to Component.onCompleted and onVisibleChanged")
else:
    # If not found, look for Component.onCompleted in root
    content = content.replace(
        "    property var radialConfigItems: []",
        """    property var radialConfigItems: []

    Component.onCompleted: {
        root.loadRadialConfig();
    }
    onVisibleChanged: {
        if (visible) {
            root.loadRadialConfig();
        }
    }""",
        1
    )
    print("Injected Component.onCompleted and onVisibleChanged for radial config")

# 2. Remove duplicate/fake Bracket Matching toggle at lines ~670
old_fake_bracket = """                            // Bracket Matching & Auto Closing Toggle
                            SettingToggleItem {
                                width: parent.width
                                title: "Bracket Matching & Auto-Closing"
                                subtitle: "Automatically insert closing brackets and quotes"
                                checked: theme ? theme.enableBracketMatching : true
                                onToggled: function(c) { if (theme) theme.enableBracketMatching = c; }
                            }"""

if old_fake_bracket in content:
    content = content.replace(old_fake_bracket, "", 1)
    print("Removed fake bracket matching toggle in Editor tab")
else:
    print("old_fake_bracket not found in Editor tab")

# 3. Remove fake search result bracket toggle
old_fake_search_bracket = """                            // 8. Bracket Matching
                            SettingToggleItem {
                                width: parent.width
                                visible: root.matchesSearch("Bracket Matching", "auto-closing quotes parenthesis curly brackets tags")
                                title: "Bracket Matching & Auto-Closing"
                                subtitle: "Automatically insert closing brackets and quotes"
                                checked: theme ? theme.enableBracketMatching : true
                                onToggled: function(c) { if (theme) theme.enableBracketMatching = c; }
                            }"""

if old_fake_search_bracket in content:
    content = content.replace(old_fake_search_bracket, "", 1)
    print("Removed fake bracket matching toggle in Search tab")
else:
    print("old_fake_search_bracket not found in Search tab")

# 4. Update SettingShortcutRow to support Mouse Gestures recording
old_sc_row = """    component SettingShortcutRow: Rectangle {
        id: scRow
        property string title: ""
        property string subtitle: ""
        property string currentShortcut: ""
        property bool isRecording: false
        signal shortcutChanged(string val)

        height: 52
        radius: theme ? theme.radiusSm : 4
        color: scRow.isRecording ? (theme ? theme.bgSurfaceActive : "#2a2d3e") : (theme ? theme.bgSurface : "#252526")
        border.color: scRow.isRecording ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderSubtle : "#282828")
        border.width: scRow.isRecording ? 1.5 : 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            spacing: 12

            Column {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: scRow.title
                    color: theme ? theme.textPrimary : "#cccccc"
                    font.pixelSize: 12
                    font.bold: true
                    elide: Text.ElideRight
                }

                Text {
                    text: scRow.subtitle
                    color: theme ? theme.textMuted : "#656565"
                    font.pixelSize: 10
                    elide: Text.ElideRight
                }
            }

            // Key Recording Badge / Button
            Rectangle {
                id: recorderBadge
                width: Math.max(120, scBadgeText.contentWidth + 20)
                height: 28
                radius: 4
                color: scRow.isRecording ? (theme ? theme.accent : "#0078d4") : (badgeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : (theme ? theme.bgInput : "#181818"))
                border.color: scRow.isRecording ? "#ffffff" : (theme ? theme.borderNormal : "#333333")
                border.width: 1
                focus: scRow.isRecording

                Row {
                    anchors.centerIn: parent
                    spacing: 6

                    VectorIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: scRow.isRecording ? "sparkles" : "keyboard"
                        size: 11
                        color: scRow.isRecording ? "#ffffff" : (theme ? theme.accent : "#0078d4")
                    }

                    Text {
                        id: scBadgeText
                        anchors.verticalCenter: parent.verticalCenter
                        text: scRow.isRecording ? "Press Keys..." : (scRow.currentShortcut || "Not Set")
                        color: scRow.isRecording ? "#ffffff" : (theme ? theme.textBright : "#ffffff")
                        font.pixelSize: 11
                        font.bold: true
                        font.family: theme ? theme.fontFamilyMono : "monospace"
                    }
                }

                MouseArea {
                    id: badgeMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        scRow.isRecording = !scRow.isRecording;
                        if (scRow.isRecording) {
                            recorderBadge.forceActiveFocus();
                        }
                    }
                }

                Keys.onPressed: function(event) {
                    if (!scRow.isRecording) return;

                    // Allow Escape to cancel recording without modifying shortcut
                    if (event.key === Qt.Key_Escape && !event.modifiers) {
                        scRow.isRecording = false;
                        event.accepted = true;
                        return;
                    }

                    // Ignore standalone modifier presses (wait for key combo)
                    if (event.key === Qt.Key_Control || event.key === Qt.Key_Shift ||
                        event.key === Qt.Key_Alt || event.key === Qt.Key_Meta) {
                        event.accepted = true;
                        return;
                    }

                    var keyStr = "";
                    if (event.key >= Qt.Key_F1 && event.key <= Qt.Key_F12) {
                        keyStr = "F" + (event.key - Qt.Key_F1 + 1);
                    } else if (event.key >= Qt.Key_A && event.key <= Qt.Key_Z) {
                        keyStr = String.fromCharCode(event.key);
                    } else if (event.key >= Qt.Key_0 && event.key <= Qt.Key_9) {
                        keyStr = String.fromCharCode(event.key);
                    } else if (event.key === Qt.Key_QuoteLeft || event.key === Qt.Key_AsciiTilde) {
                        keyStr = "`";
                    } else if (event.key === Qt.Key_Slash) {
                        keyStr = "/";
                    } else if (event.key === Qt.Key_Backslash) {
                        keyStr = "\\\\";
                    } else if (event.key === Qt.Key_Minus) {
                        keyStr = "-";
                    } else if (event.key === Qt.Key_Equal || event.key === Qt.Key_Plus) {
                        keyStr = "=";
                    } else if (event.key === Qt.Key_Comma) {
                        keyStr = ",";
                    } else if (event.key === Qt.Key_Period) {
                        keyStr = ".";
                    } else if (event.key === Qt.Key_Semicolon) {
                        keyStr = ";";
                    } else if (event.key === Qt.Key_Apostrophe) {
                        keyStr = "'";
                    } else if (event.key === Qt.Key_BracketLeft) {
                        keyStr = "[";
                    } else if (event.key === Qt.Key_BracketRight) {
                        keyStr = "]";
                    } else if (event.key === Qt.Key_Tab) {
                        keyStr = "Tab";
                    } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        keyStr = "Return";
                    } else if (event.key === Qt.Key_Space) {
                        keyStr = "Space";
                    } else if (event.key === Qt.Key_Delete) {
                        keyStr = "Del";
                    } else if (event.key === Qt.Key_Backspace) {
                        keyStr = "Backspace";
                    } else if (event.text && event.text.length > 0) {
                        keyStr = event.text.toUpperCase();
                    }

                    if (keyStr.length > 0) {
                        var parts = [];
                        if (event.modifiers & Qt.ControlModifier) parts.push("Ctrl");
                        if (event.modifiers & Qt.AltModifier) parts.push("Alt");
                        if (event.modifiers & Qt.ShiftModifier) parts.push("Shift");
                        if (event.modifiers & Qt.MetaModifier) parts.push("Meta");
                        parts.push(keyStr);

                        var fullCombo = parts.join("+");
                        scRow.currentShortcut = fullCombo;
                        scRow.shortcutChanged(fullCombo);
                        if (theme && theme.saveSettings) {
                            theme.saveSettings();
                        }
                        scRow.isRecording = false;
                        event.accepted = true;
                    }
                }
            }
        }
    }"""

new_sc_row = """    component SettingShortcutRow: Rectangle {
        id: scRow
        property string title: ""
        property string subtitle: ""
        property string currentShortcut: ""
        property bool isGesture: false
        property bool isRecording: false
        signal shortcutChanged(string val)

        height: 52
        radius: theme ? theme.radiusSm : 4
        color: scRow.isRecording ? (theme ? theme.bgSurfaceActive : "#2a2d3e") : (theme ? theme.bgSurface : "#252526")
        border.color: scRow.isRecording ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderSubtle : "#282828")
        border.width: scRow.isRecording ? 1.5 : 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            spacing: 12

            Column {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: scRow.title
                    color: theme ? theme.textPrimary : "#cccccc"
                    font.pixelSize: 12
                    font.bold: true
                    elide: Text.ElideRight
                }

                Text {
                    text: scRow.subtitle
                    color: theme ? theme.textMuted : "#656565"
                    font.pixelSize: 10
                    elide: Text.ElideRight
                }
            }

            // Key / Mouse Recording Badge / Button
            Rectangle {
                id: recorderBadge
                width: Math.max(130, scBadgeText.contentWidth + 24)
                height: 28
                radius: 4
                color: scRow.isRecording ? (theme ? theme.accent : "#0078d4") : (badgeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : (theme ? theme.bgInput : "#181818"))
                border.color: scRow.isRecording ? "#ffffff" : (theme ? theme.borderNormal : "#333333")
                border.width: 1
                focus: scRow.isRecording

                Row {
                    anchors.centerIn: parent
                    spacing: 6

                    VectorIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: scRow.isGesture ? "cursor" : (scRow.isRecording ? "sparkles" : "keyboard")
                        size: 11
                        color: scRow.isRecording ? "#ffffff" : (theme ? theme.accent : "#0078d4")
                    }

                    Text {
                        id: scBadgeText
                        anchors.verticalCenter: parent.verticalCenter
                        text: scRow.isRecording ? (scRow.isGesture ? "Click + Keys..." : "Press Keys...") : (scRow.currentShortcut || "Not Set")
                        color: scRow.isRecording ? "#ffffff" : (theme ? theme.textBright : "#ffffff")
                        font.pixelSize: 11
                        font.bold: true
                        font.family: theme ? theme.fontFamilyMono : "monospace"
                    }
                }

                MouseArea {
                    id: badgeMa
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onPressed: function(mouse) {
                        if (!scRow.isRecording) {
                            scRow.isRecording = true;
                            recorderBadge.forceActiveFocus();
                            mouse.accepted = true;
                            return;
                        }

                        // If recording and user clicks with or without modifiers
                        var parts = [];
                        if (mouse.modifiers & Qt.ControlModifier) parts.push("Ctrl");
                        if (mouse.modifiers & Qt.AltModifier) parts.push("Alt");
                        if (mouse.modifiers & Qt.ShiftModifier) parts.push("Shift");
                        if (mouse.modifiers & Qt.MetaModifier) parts.push("Meta");

                        var btnName = "Left Click";
                        if (mouse.button === Qt.RightButton) btnName = "Right Click";
                        else if (mouse.button === Qt.MiddleButton) btnName = "Middle Click";

                        parts.push(btnName);
                        var fullCombo = parts.join(" + ");
                        scRow.currentShortcut = fullCombo;
                        scRow.shortcutChanged(fullCombo);
                        if (theme && theme.saveSettings) {
                            theme.saveSettings();
                        }
                        scRow.isRecording = false;
                        mouse.accepted = true;
                    }
                }

                Keys.onPressed: function(event) {
                    if (!scRow.isRecording) return;

                    // Allow Escape to cancel recording without modifying shortcut
                    if (event.key === Qt.Key_Escape && !event.modifiers) {
                        scRow.isRecording = false;
                        event.accepted = true;
                        return;
                    }

                    // Ignore standalone modifier presses (wait for key combo)
                    if (event.key === Qt.Key_Control || event.key === Qt.Key_Shift ||
                        event.key === Qt.Key_Alt || event.key === Qt.Key_Meta) {
                        event.accepted = true;
                        return;
                    }

                    var keyStr = "";
                    if (event.key >= Qt.Key_F1 && event.key <= Qt.Key_F12) {
                        keyStr = "F" + (event.key - Qt.Key_F1 + 1);
                    } else if (event.key >= Qt.Key_A && event.key <= Qt.Key_Z) {
                        keyStr = String.fromCharCode(event.key);
                    } else if (event.key >= Qt.Key_0 && event.key <= Qt.Key_9) {
                        keyStr = String.fromCharCode(event.key);
                    } else if (event.key === Qt.Key_QuoteLeft || event.key === Qt.Key_AsciiTilde) {
                        keyStr = "`";
                    } else if (event.key === Qt.Key_Slash) {
                        keyStr = "/";
                    } else if (event.key === Qt.Key_Backslash) {
                        keyStr = "\\\\";
                    } else if (event.key === Qt.Key_Minus) {
                        keyStr = "-";
                    } else if (event.key === Qt.Key_Equal || event.key === Qt.Key_Plus) {
                        keyStr = "=";
                    } else if (event.key === Qt.Key_Comma) {
                        keyStr = ",";
                    } else if (event.key === Qt.Key_Period) {
                        keyStr = ".";
                    } else if (event.key === Qt.Key_Semicolon) {
                        keyStr = ";";
                    } else if (event.key === Qt.Key_Apostrophe) {
                        keyStr = "'";
                    } else if (event.key === Qt.Key_BracketLeft) {
                        keyStr = "[";
                    } else if (event.key === Qt.Key_BracketRight) {
                        keyStr = "]";
                    } else if (event.key === Qt.Key_Tab) {
                        keyStr = "Tab";
                    } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        keyStr = "Return";
                    } else if (event.key === Qt.Key_Space) {
                        keyStr = "Space";
                    } else if (event.key === Qt.Key_Delete) {
                        keyStr = "Del";
                    } else if (event.key === Qt.Key_Backspace) {
                        keyStr = "Backspace";
                    } else if (event.text && event.text.length > 0) {
                        keyStr = event.text.toUpperCase();
                    }

                    if (keyStr.length > 0) {
                        var parts = [];
                        if (event.modifiers & Qt.ControlModifier) parts.push("Ctrl");
                        if (event.modifiers & Qt.AltModifier) parts.push("Alt");
                        if (event.modifiers & Qt.ShiftModifier) parts.push("Shift");
                        if (event.modifiers & Qt.MetaModifier) parts.push("Meta");
                        parts.push(keyStr);

                        var fullCombo = parts.join("+");
                        scRow.currentShortcut = fullCombo;
                        scRow.shortcutChanged(fullCombo);
                        if (theme && theme.saveSettings) {
                            theme.saveSettings();
                        }
                        scRow.isRecording = false;
                        event.accepted = true;
                    }
                }
            }
        }
    }"""

assert old_sc_row in content, "old_sc_row not found"
content = content.replace(old_sc_row, new_sc_row, 1)

# 5. Add isGesture: true to Add Cursor (Mouse) in shortcuts list
content = content.replace(
    'title: "Add Cursor (Mouse)"',
    'title: "Add Cursor (Mouse)"\n                                isGesture: true',
    1
)

with open('qml/components/SettingsDialog.qml', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated SettingsDialog.qml with radial loading, mouse gesture recording, and clean bracket settings.")
