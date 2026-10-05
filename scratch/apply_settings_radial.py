import re

settings_path = "qml/components/SettingsDialog.qml"
with open(settings_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update categories to include Radial Menu
content = content.replace(
    '''    property var categories: [
        { name: "General", icon: "settings" },
        { name: "Appearance", icon: "sparkles" },
        { name: "Editor", icon: "file" },
        { name: "Terminal", icon: "code" },
        { name: "Shortcuts", icon: "keyboard" }
    ]''',
    '''    property var categories: [
        { name: "General", icon: "settings" },
        { name: "Appearance", icon: "sparkles" },
        { name: "Editor", icon: "file" },
        { name: "Terminal", icon: "code" },
        { name: "Shortcuts", icon: "keyboard" },
        { name: "Radial Menu", icon: "zen" }
    ]

    property var radialConfigItems: []

    function loadRadialConfig() {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_radial_menu_config) {
            radialConfigItems = settingsBackend.get_radial_menu_config() || [];
        }
    }

    function saveRadialConfig() {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.save_radial_menu_config) {
            settingsBackend.save_radial_menu_config(JSON.stringify(radialConfigItems));
        }
    }

    function resetRadialConfig() {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.reset_radial_menu_config) {
            radialConfigItems = settingsBackend.reset_radial_menu_config() || [];
        }
    }'''
)

# 2. Update currentIndex of StackLayout
content = content.replace(
    "currentIndex: root.searchQuery.length > 0 ? 5 : root.activeCategoryIndex",
    "currentIndex: root.searchQuery.length > 0 ? 6 : root.activeCategoryIndex"
)

# 3. Add Radial Menu Tab View before search results tab
radial_tab_code = '''                    // =========================================================
                    // 5. RADIAL CONTEXT MENU TAB (Live Visual Preview & Customizer)
                    // =========================================================
                    Item {
                        id: radialSettingsTab
                        clip: true

                        RowLayout {
                            anchors.fill: parent
                            spacing: 16

                            // Left Column: Configuration List & Controls
                            ColumnLayout {
                                Layout.fillHeight: true
                                Layout.preferredWidth: 360
                                spacing: 10

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        text: "Radial Context Menu"
                                        color: theme ? theme.textBright : "#ffffff"
                                        font.pixelSize: 15
                                        font.bold: true
                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                        Layout.fillWidth: true
                                    }

                                    // Add Button
                                    Rectangle {
                                        width: 80
                                        height: 24
                                        radius: 4
                                        color: addMa.containsMouse ? (theme ? theme.accentHover : "#1084d8") : (theme ? theme.accent : "#0078d4")

                                        Text {
                                            anchors.centerIn: parent
                                            text: "+ Add Action"
                                            color: "#ffffff"
                                            font.pixelSize: 11
                                            font.bold: true
                                        }

                                        MouseArea {
                                            id: addMa
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                var arr = root.radialConfigItems.slice();
                                                arr.push({
                                                    id: "custom_" + Date.now(),
                                                    label: "Custom " + (arr.length + 1),
                                                    icon: "code",
                                                    shortcut: "Action",
                                                    enabled: true,
                                                    custom: true,
                                                    action: "Write-Host 'Custom action executed'"
                                                });
                                                root.radialConfigItems = arr;
                                                root.saveRadialConfig();
                                            }
                                        }
                                    }

                                    // Reset Button
                                    Rectangle {
                                        width: 60
                                        height: 24
                                        radius: 4
                                        color: resetMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#333333") : (theme ? theme.bgSurface : "#252526")
                                        border.color: theme ? theme.borderNormal : "#3c3c3c"
                                        border.width: 1

                                        Text {
                                            anchors.centerIn: parent
                                            text: "Reset"
                                            color: theme ? theme.textSecondary : "#cccccc"
                                            font.pixelSize: 11
                                        }

                                        MouseArea {
                                            id: resetMa
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.resetRadialConfig()
                                        }
                                    }
                                }

                                Text {
                                    text: "Customize radial menu actions, reorder, toggle visibility, and assign scripts."
                                    color: theme ? theme.textMuted : "#888888"
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }

                                ScrollView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                                    ListView {
                                        id: radialConfigListView
                                        width: parent.width
                                        model: root.radialConfigItems
                                        spacing: 6

                                        delegate: Rectangle {
                                            width: radialConfigListView.width - 8
                                            height: 52
                                            radius: 6
                                            color: theme ? theme.bgSurface : "#252526"
                                            border.color: theme ? theme.borderNormal : "#333333"
                                            border.width: 1

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.margins: 6
                                                spacing: 6

                                                // Reorder Buttons (Up / Down)
                                                Column {
                                                    spacing: 2
                                                    Rectangle {
                                                        width: 16
                                                        height: 16
                                                        radius: 2
                                                        color: upMa.containsMouse ? (theme ? theme.accent : "#0078d4") : "transparent"
                                                        Text { anchors.centerIn: parent; text: "▲"; font.pixelSize: 9; color: "#cccccc" }
                                                        MouseArea {
                                                            id: upMa
                                                            anchors.fill: parent
                                                            hoverEnabled: true
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: {
                                                                if (index > 0) {
                                                                    var arr = root.radialConfigItems.slice();
                                                                    var tmp = arr[index];
                                                                    arr[index] = arr[index - 1];
                                                                    arr[index - 1] = tmp;
                                                                    root.radialConfigItems = arr;
                                                                    root.saveRadialConfig();
                                                                }
                                                            }
                                                        }
                                                    }
                                                    Rectangle {
                                                        width: 16
                                                        height: 16
                                                        radius: 2
                                                        color: downMa.containsMouse ? (theme ? theme.accent : "#0078d4") : "transparent"
                                                        Text { anchors.centerIn: parent; text: "▼"; font.pixelSize: 9; color: "#cccccc" }
                                                        MouseArea {
                                                            id: downMa
                                                            anchors.fill: parent
                                                            hoverEnabled: true
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: {
                                                                if (index < root.radialConfigItems.length - 1) {
                                                                    var arr = root.radialConfigItems.slice();
                                                                    var tmp = arr[index];
                                                                    arr[index] = arr[index + 1];
                                                                    arr[index + 1] = tmp;
                                                                    root.radialConfigItems = arr;
                                                                    root.saveRadialConfig();
                                                                }
                                                            }
                                                        }
                                                    }
                                                }

                                                // Enabled Checkbox
                                                CheckBox {
                                                    checked: modelData.enabled !== false
                                                    onToggled: {
                                                        var arr = root.radialConfigItems.slice();
                                                        arr[index].enabled = checked;
                                                        root.radialConfigItems = arr;
                                                        root.saveRadialConfig();
                                                    }
                                                }

                                                // Icon
                                                VectorIcon {
                                                    name: modelData.icon || "file"
                                                    size: 14
                                                    color: theme ? theme.accent : "#38bdf8"
                                                }

                                                // Label and action details
                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 2

                                                    TextInput {
                                                        Layout.fillWidth: true
                                                        text: modelData.label || ""
                                                        color: theme ? theme.textPrimary : "#ffffff"
                                                        font.pixelSize: 12
                                                        font.bold: true
                                                        onEditingFinished: {
                                                            var arr = root.radialConfigItems.slice();
                                                            arr[index].label = text;
                                                            root.radialConfigItems = arr;
                                                            root.saveRadialConfig();
                                                        }
                                                    }

                                                    TextInput {
                                                        Layout.fillWidth: true
                                                        text: modelData.action || modelData.shortcut || ""
                                                        color: theme ? theme.textMuted : "#888888"
                                                        font.pixelSize: 10
                                                        font.family: "Consolas, monospace"
                                                        onEditingFinished: {
                                                            var arr = root.radialConfigItems.slice();
                                                            arr[index].action = text;
                                                            root.radialConfigItems = arr;
                                                            root.saveRadialConfig();
                                                        }
                                                    }
                                                }

                                                // Delete button
                                                Rectangle {
                                                    width: 22
                                                    height: 22
                                                    radius: 3
                                                    color: delMa.containsMouse ? (theme ? theme.error : "#f14c4c") : "transparent"
                                                    VectorIcon { anchors.centerIn: parent; name: "close"; size: 9; color: delMa.containsMouse ? "#ffffff" : "#888888" }
                                                    MouseArea {
                                                        id: delMa
                                                        anchors.fill: parent
                                                        hoverEnabled: true
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: {
                                                            var arr = root.radialConfigItems.slice();
                                                            arr.splice(index, 1);
                                                            root.radialConfigItems = arr;
                                                            root.saveRadialConfig();
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Right Column: LIVE VISUAL RADIAL PREVIEW
                            Rectangle {
                                Layout.fillHeight: true
                                Layout.fillWidth: true
                                radius: 8
                                color: theme ? theme.bgApp : "#141822"
                                border.color: theme ? theme.borderNormal : "#2a3145"
                                border.width: 1

                                Text {
                                    anchors.top: parent.top
                                    anchors.left: parent.left
                                    anchors.margins: 12
                                    text: "LIVE RADIAL MENU PREVIEW"
                                    color: theme ? theme.textMuted : "#64748b"
                                    font.pixelSize: 10
                                    font.bold: true
                                    font.letterSpacing: 1
                                }

                                Item {
                                    id: radialPreviewContainer
                                    anchors.centerIn: parent
                                    width: 280
                                    height: 280

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
                                    readonly property real previewRadius: 90

                                    // Center Disc
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 72
                                        height: 72
                                        radius: 36
                                        color: theme ? theme.bgPopup : "#151824"
                                        border.color: theme ? theme.borderNormal : "#2a3145"
                                        border.width: 2

                                        Column {
                                            anchors.centerIn: parent
                                            spacing: 2
                                            VectorIcon {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                name: "zen"
                                                size: 16
                                                color: theme ? theme.accent : "#3b82f6"
                                            }
                                            Text {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                text: "DGX"
                                                color: theme ? theme.textPrimary : "#f1f5f9"
                                                font.pixelSize: 10
                                                font.bold: true
                                            }
                                        }
                                    }

                                    // Radial Bubbles
                                    Repeater {
                                        model: radialPreviewContainer.activeItems

                                        delegate: Item {
                                            readonly property real angle: (index / Math.max(1, radialPreviewContainer.activeItems.length)) * (2 * Math.PI) - (Math.PI / 2)
                                            readonly property real nodeX: (radialPreviewContainer.width / 2) + Math.cos(angle) * radialPreviewContainer.previewRadius - 22
                                            readonly property real nodeY: (radialPreviewContainer.height / 2) + Math.sin(angle) * radialPreviewContainer.previewRadius - 22

                                            x: nodeX
                                            y: nodeY
                                            width: 44
                                            height: 44

                                            Rectangle {
                                                anchors.fill: parent
                                                radius: 22
                                                color: prevMa.containsMouse ? (theme ? theme.accent : "#3b82f6") : (theme ? theme.bgSurface : "#181c28")
                                                border.color: prevMa.containsMouse ? "#ffffff" : (theme ? theme.borderNormal : "#2a3145")
                                                border.width: 1

                                                scale: prevMa.containsMouse ? 1.15 : 1.0
                                                Behavior on scale { NumberAnimation { duration: 100 } }

                                                Column {
                                                    anchors.centerIn: parent
                                                    spacing: 1
                                                    VectorIcon {
                                                        anchors.horizontalCenter: parent.horizontalCenter
                                                        name: modelData.icon || "file"
                                                        size: 12
                                                        color: prevMa.containsMouse ? "#ffffff" : (theme ? theme.textPrimary : "#e2e8f0")
                                                    }
                                                    Text {
                                                        anchors.horizontalCenter: parent.horizontalCenter
                                                        text: modelData.label || ""
                                                        color: prevMa.containsMouse ? "#ffffff" : (theme ? theme.textSecondary : "#94a3b8")
                                                        font.pixelSize: 8
                                                        font.bold: prevMa.containsMouse
                                                    }
                                                }

                                                ToolTip.visible: prevMa.containsMouse
                                                ToolTip.text: (modelData.label || "") + (modelData.action ? " [" + modelData.action + "]" : "")

                                                MouseArea {
                                                    id: prevMa
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                                                            mainWindow.showNotification("Radial action preview: " + modelData.label, "info", "Radial Menu");
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
'''

content = content.replace(
    "// =========================================================\n                    // 5. SEARCH RESULTS TAB",
    radial_tab_code + "\n                    // =========================================================\n                    // 6. SEARCH RESULTS TAB"
)

# Add loadRadialConfig() to onVisibleChanged
content = content.replace(
    "root.loadShortcuts();",
    "root.loadShortcuts();\n                root.loadRadialConfig();"
)

with open(settings_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied Radial Menu Settings customization section to SettingsDialog.qml")
