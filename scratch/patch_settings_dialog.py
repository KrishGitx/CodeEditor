with open('qml/components/SettingsDialog.qml', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Mouse Wheel Zoom to SettingToggleItem & add Auto Close Brackets/Quotes
old_mouse_wheel = '''                            // Setting: Mouse Wheel Zoom
                            Rectangle {
                                width: parent.width
                                height: 50
                                color: "transparent"

                                Column {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 3

                                    Text {
                                        text: "Mouse Wheel Zoom"
                                        color: theme ? theme.textPrimary : "#cccccc"
                                        font.pixelSize: 13
                                        font.bold: true
                                    }

                                    Text {
                                        text: "Zoom font size when scrolling with mouse wheel and holding Ctrl"
                                        color: theme ? theme.textMuted : "#858585"
                                        font.pixelSize: 11
                                    }
                                }

                                Switch {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    checked: (typeof theme !== "undefined" && theme) ? theme.enableMouseWheelZoom : true
                                    onToggled: {
                                        if (typeof theme !== "undefined" && theme) {
                                            theme.enableMouseWheelZoom = checked;
                                            theme.saveSettings();
                                        }
                                    }
                                }
                            }'''

new_mouse_wheel = '''                            // Setting: Mouse Wheel Zoom
                            SettingToggleItem {
                                width: parent.width
                                title: "Mouse Wheel Zoom"
                                subtitle: "Zoom font size when scrolling with mouse wheel and holding Ctrl"
                                checked: (typeof theme !== "undefined" && theme && typeof theme.enableMouseWheelZoom !== "undefined") ? theme.enableMouseWheelZoom : true
                                onToggled: function(c) {
                                    if (typeof theme !== "undefined" && theme) {
                                        theme.enableMouseWheelZoom = c;
                                        if (theme.saveSettings) theme.saveSettings();
                                    }
                                }
                            }

                            // Setting: Auto Close Brackets/Quotes
                            SettingToggleItem {
                                width: parent.width
                                title: "Auto Close Brackets & Quotes"
                                subtitle: "Automatically insert matching closing brackets and quotes when typing (, [, {, \\", '"
                                checked: (typeof theme !== "undefined" && theme && typeof theme.autoCloseBracketsQuotes !== "undefined") ? theme.autoCloseBracketsQuotes : true
                                onToggled: function(c) {
                                    if (typeof theme !== "undefined" && theme) {
                                        theme.autoCloseBracketsQuotes = c;
                                        if (theme.saveSettings) theme.saveSettings();
                                    }
                                }
                            }'''

if old_mouse_wheel in content:
    content = content.replace(old_mouse_wheel, new_mouse_wheel, 1)
    print("Replaced Mouse Wheel Zoom with SettingToggleItem and added Auto Close Brackets/Quotes")
else:
    print("Mouse Wheel Zoom not found")

# 2. Add subtle border around Detail Settings View
old_detail_bg = '''            // Detail Settings View with StackLayout
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: theme ? theme.bgEditor : "#1e1e1e"'''

new_detail_bg = '''            // Detail Settings View with StackLayout
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: theme ? theme.bgEditor : "#1e1e1e"
                border.color: theme ? theme.borderSubtle : "#282828"
                border.width: 1'''

if old_detail_bg in content:
    content = content.replace(old_detail_bg, new_detail_bg, 1)
    print("Added subtle border to Settings detail container")
else:
    print("old_detail_bg not found")

# 3. Update Radial Menu Preview container bounds calculation
old_radial_preview = '''                                Item {
                                    id: radialPreviewContainer
                                    anchors.centerIn: parent
                                    width: 240
                                    height: 240

                                    // Filter enabled items for preview
                                    readonly property var activeItems: {
                                        var list = [];
                                        if (root.radialConfigItems) {
                                            for (var i = 0; i < root.radialConfigItems.length; i++) {
                                                if (root.radialConfigItems[i].enabled !== false) {
                                                    list.push(root.radialConfigItems[i]);
                                                }
                                            }
                                        }
                                        return list;
                                    }
                                    readonly property real previewRadius: 75'''

new_radial_preview = '''                                Item {
                                    id: radialPreviewContainer
                                    anchors.centerIn: parent
                                    width: Math.min(parent.width - 24, 240)
                                    height: Math.min(parent.height - 40, 240)

                                    // Filter enabled items for preview
                                    readonly property var activeItems: {
                                        var list = [];
                                        if (root.radialConfigItems) {
                                            for (var i = 0; i < root.radialConfigItems.length; i++) {
                                                if (root.radialConfigItems[i].enabled !== false) {
                                                    list.push(root.radialConfigItems[i]);
                                                }
                                            }
                                        }
                                        return list;
                                    }
                                    readonly property real previewRadius: Math.max(38, Math.min(75, (Math.min(width, height) / 2) - 28))'''

if old_radial_preview in content:
    content = content.replace(old_radial_preview, new_radial_preview, 1)
    print("Updated radial preview bounds")
else:
    print("old_radial_preview not found")

with open('qml/components/SettingsDialog.qml', 'w', encoding='utf-8') as f:
    f.write(content)
print("SettingsDialog.qml patched")
