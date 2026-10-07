with open('qml/components/SettingsDialog.qml', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update ShortcutSettingRow to support mouse gestures
old_sc_row = """    // Component: ShortcutSettingRow with Interactive Keybinding Recorder & Manual Input
    component ShortcutSettingRow: Rectangle {
        id: scRow
        property string title: ""
        property string subtitle: ""
        property string currentShortcut: ""
        property bool isRecording: false
        signal shortcutChanged(string val)"""

new_sc_row = """    // Component: ShortcutSettingRow with Interactive Keybinding Recorder & Gesture Input
    component ShortcutSettingRow: Rectangle {
        id: scRow
        property string title: ""
        property string subtitle: ""
        property string currentShortcut: ""
        property bool isGesture: false
        property bool isRecording: false
        signal shortcutChanged(string val)"""

assert old_sc_row in content, "old_sc_row not found"
content = content.replace(old_sc_row, new_sc_row, 1)

# 2. Update recorder badge and MouseArea in ShortcutSettingRow
old_badge_area = """                MouseArea {
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
                }"""

new_badge_area = """                MouseArea {
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

                        // Capture mouse button + modifier combination
                        var parts = [];
                        if (mouse.modifiers & Qt.AltModifier) parts.push("Alt");
                        if (mouse.modifiers & Qt.ControlModifier) parts.push("Ctrl");
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
                }"""

assert old_badge_area in content, "old_badge_area not found"
content = content.replace(old_badge_area, new_badge_area, 1)

# 3. Add isGesture: true and section title for Mouse Gestures in Shortcuts category
old_add_cursor = """                            ShortcutSettingRow {
                                width: parent.width
                                title: "Add Cursor (Mouse)"
                                subtitle: "Place an additional cursor at clicked position"
                                currentShortcut: theme ? theme.shortcutAddCursor : "Alt+Click"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutAddCursor = val; }
                            }"""

new_add_cursor = """                            Item { width: 1; height: 10 }
                            Text {
                                text: "Mouse & Editor Gestures"
                                color: theme ? theme.textBright : "#ffffff"
                                font.pixelSize: 13
                                font.bold: true
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Add Cursor (Mouse Gesture)"
                                subtitle: "Place an additional multi-cursor at clicked position"
                                isGesture: true
                                currentShortcut: theme ? theme.shortcutAddCursor : "Alt + Left Click"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutAddCursor = val; }
                            }"""

if old_add_cursor in content:
    content = content.replace(old_add_cursor, new_add_cursor, 1)
    print("Updated Add Cursor shortcut row to Mouse & Editor Gestures section")
else:
    print("old_add_cursor not found")

with open('qml/components/SettingsDialog.qml', 'w', encoding='utf-8') as f:
    f.write(content)

print("SettingsDialog.qml patched successfully")
