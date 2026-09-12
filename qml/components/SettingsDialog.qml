import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Popup {
    id: settingsRoot

    width: Math.min(820, parent ? parent.width - 80 : 820)
    height: Math.min(620, parent ? parent.height - 80 : 620)

    anchors.centerIn: parent
    modal: true
    focus: true
    padding: 0

    property string selectedCategory: "Appearance"

    // ─────────────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────────────

    function categoryVisible(category) {
        return selectedCategory === category
    }

    function setAccent(value) {
        theme.accentColor = value
    }

    background: Rectangle {
        color: theme.bgCard
        radius: theme.radiusLg
        border.color: theme.borderSubtle
        border.width: 1

        // Soft inner edge
        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            color: "transparent"
            radius: theme.radiusLg - 1
            border.color: Qt.rgba(
                Qt.color(theme.textPrimary).r,
                Qt.color(theme.textPrimary).g,
                Qt.color(theme.textPrimary).b,
                0.035
            )
            border.width: 1
        }
    }

    contentItem: ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ═════════════════════════════════════════════════════════════════════
        // HEADER
        // ═════════════════════════════════════════════════════════════════════

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 68
            color: theme.bgHeader

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 18
                spacing: 14

                Rectangle {
                    width: 34
                    height: 34
                    radius: 9
                    color: theme.bgActive
                    border.color: theme.borderSubtle
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "⚙"
                        color: theme.accentColor
                        font.pixelSize: 17
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: "Settings"
                        color: theme.textPrimary
                        font.family: theme.uiFont
                        font.pixelSize: 16
                        font.bold: true
                    }

                    Text {
                        text: "Customize your DGX Studio workspace"
                        color: theme.textMuted
                        font.family: theme.uiFont
                        font.pixelSize: 10
                    }
                }

                Rectangle {
                    width: 32
                    height: 32
                    radius: 8
                    color: closeMouse.containsMouse
                           ? theme.bgHover
                           : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "×"
                        color: theme.textSecondary
                        font.pixelSize: 20
                        font.family: theme.uiFont
                    }

                    MouseArea {
                        id: closeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onClicked: settingsRoot.close()
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: theme.borderSubtle
            }
        }

        // ═════════════════════════════════════════════════════════════════════
        // BODY
        // ═════════════════════════════════════════════════════════════════════

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // ─────────────────────────────────────────────────────────────────
            // SIDEBAR
            // ─────────────────────────────────────────────────────────────────

            Rectangle {
                Layout.preferredWidth: 190
                Layout.fillHeight: true
                color: theme.bgSidebar

                ColumnLayout {
                    anchors.fill: parent
                    anchors.topMargin: 18
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 3

                    Text {
                        text: "PREFERENCES"
                        color: theme.textMuted
                        font.family: theme.uiFont
                        font.pixelSize: 9
                        font.bold: true
                        font.letterSpacing: 1.0

                        Layout.leftMargin: 10
                        Layout.bottomMargin: 7
                    }

                    Repeater {
                        model: [
                            {
                                name: "Appearance",
                                subtitle: "Theme & interface",
                                icon: "◐"
                            },
                            {
                                name: "Editor",
                                subtitle: "Code editing",
                                icon: "▤"
                            },
                            {
                                name: "Music",
                                subtitle: "Playback & visualizer",
                                icon: "♫"
                            },
                            {
                                name: "General",
                                subtitle: "Workspace behavior",
                                icon: "•"
                            }
                        ]

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 52
                            radius: 8

                            color: settingsRoot.selectedCategory === modelData.name
                                   ? theme.bgActive
                                   : categoryMouse.containsMouse
                                     ? theme.bgHover
                                     : "transparent"

                            border.color: settingsRoot.selectedCategory === modelData.name
                                           ? Qt.rgba(
                                                 Qt.color(theme.accentColor).r,
                                                 Qt.color(theme.accentColor).g,
                                                 Qt.color(theme.accentColor).b,
                                                 0.25
                                             )
                                           : "transparent"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 8
                                spacing: 10

                                Rectangle {
                                    Layout.preferredWidth: 30
                                    Layout.preferredHeight: 30
                                    radius: 7

                                    color: settingsRoot.selectedCategory === modelData.name
                                           ? Qt.rgba(
                                                 Qt.color(theme.accentColor).r,
                                                 Qt.color(theme.accentColor).g,
                                                 Qt.color(theme.accentColor).b,
                                                 0.13
                                             )
                                           : "transparent"

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.icon
                                        color: settingsRoot.selectedCategory === modelData.name
                                               ? theme.accentColor
                                               : theme.textSecondary
                                        font.pixelSize: 15
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1

                                    Text {
                                        text: modelData.name
                                        color: settingsRoot.selectedCategory === modelData.name
                                               ? theme.textPrimary
                                               : theme.textSecondary

                                        font.family: theme.uiFont
                                        font.pixelSize: 11
                                        font.bold: settingsRoot.selectedCategory === modelData.name
                                    }

                                    Text {
                                        text: modelData.subtitle
                                        color: theme.textMuted
                                        font.family: theme.uiFont
                                        font.pixelSize: 9
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }
                            }

                            MouseArea {
                                id: categoryMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor

                                onClicked: {
                                    settingsRoot.selectedCategory = modelData.name
                                }
                            }
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }

                    Text {
                        text: "DGX STUDIO"
                        color: theme.textMuted
                        font.family: theme.uiFont
                        font.pixelSize: 8
                        font.bold: true
                        font.letterSpacing: 1
                        Layout.leftMargin: 10
                    }

                    Text {
                        text: "v2.0"
                        color: theme.textMuted
                        font.family: theme.uiFont
                        font.pixelSize: 9
                        Layout.leftMargin: 10
                        Layout.bottomMargin: 12
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    width: 1
                    height: parent.height
                    color: theme.borderSubtle
                }
            }

            // ─────────────────────────────────────────────────────────────────
            // CONTENT
            // ─────────────────────────────────────────────────────────────────

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: theme.bgRoot

                ScrollView {
                    id: settingsScroll

                    anchors.fill: parent
                    anchors.margins: 24
                    clip: true

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded

                        contentItem: Rectangle {
                            implicitWidth: 5
                            radius: 3
                            color: theme.scrollThumb
                            opacity: 0.7
                        }

                        background: Rectangle {
                            color: "transparent"
                        }
                    }

                    ColumnLayout {
                        width: settingsScroll.availableWidth
                        spacing: 26

                        // ═════════════════════════════════════════════════════
                        // APPEARANCE
                        // ═════════════════════════════════════════════════════

                        ColumnLayout {
                            visible: settingsRoot.categoryVisible("Appearance")
                            Layout.fillWidth: true
                            spacing: 20

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                Text {
                                    text: "Appearance"
                                    color: theme.textPrimary
                                    font.family: theme.uiFont
                                    font.pixelSize: 18
                                    font.bold: true
                                }

                                Text {
                                    text: "Choose how DGX Studio looks and feels."
                                    color: theme.textMuted
                                    font.family: theme.uiFont
                                    font.pixelSize: 10
                                }
                            }

                            // Theme section
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Text {
                                    text: "COLOR THEME"
                                    color: theme.textSecondary
                                    font.family: theme.uiFont
                                    font.pixelSize: 9
                                    font.bold: true
                                    font.letterSpacing: 1
                                }

                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: 4
                                    columnSpacing: 8
                                    rowSpacing: 8

                                    Repeater {
                                        model: [
                                            {
                                                name: "Obsidian",
                                                color: "#090b10",
                                                edge: "#252c38",
                                                accent: "#8b7cff"
                                            },
                                            {
                                                name: "Midnight",
                                                color: "#080b14",
                                                edge: "#1b2440",
                                                accent: "#7aa2f7"
                                            },
                                            {
                                                name: "Dracula",
                                                color: "#191a23",
                                                edge: "#35364e",
                                                accent: "#bd93f9"
                                            },
                                            {
                                                name: "Nord",
                                                color: "#242933",
                                                edge: "#3b4252",
                                                accent: "#88c0d0"
                                            },
                                            {
                                                name: "Monokai",
                                                color: "#1c1d1a",
                                                edge: "#3a3b34",
                                                accent: "#a6e22e"
                                            },
                                            {
                                                name: "Light",
                                                color: "#ffffff",
                                                edge: "#d6dbe4",
                                                accent: "#2563eb"
                                            },
                                            {
                                                name: "Paper",
                                                color: "#fbf9f5",
                                                edge: "#d4cec2",
                                                accent: "#8b6834"
                                            },
                                            {
                                                name: "Glass",
                                                color: "#101722",
                                                edge: "#3a4a60",
                                                accent: "#7dd3fc"
                                            }
                                        ]

                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 72
                                            radius: 8
                                            color: modelData.color

                                            border.color: theme.currentTheme === modelData.name
                                                          ? modelData.accent
                                                          : modelData.edge
                                            border.width: theme.currentTheme === modelData.name
                                                          ? 2
                                                          : 1

                                            // Accent preview line
                                            Rectangle {
                                                anchors.left: parent.left
                                                anchors.right: parent.right
                                                anchors.bottom: parent.bottom
                                                anchors.leftMargin: 10
                                                anchors.rightMargin: 10
                                                anchors.bottomMargin: 10
                                                height: 2
                                                radius: 1
                                                color: modelData.accent
                                                opacity: 0.8
                                            }

                                            Column {
                                                anchors.left: parent.left
                                                anchors.top: parent.top
                                                anchors.leftMargin: 11
                                                anchors.topMargin: 10
                                                spacing: 2

                                                Text {
                                                    text: modelData.name
                                                    color: theme.currentTheme === "Light" ||
                                                           theme.currentTheme === "Paper"
                                                           ? "#29251f"
                                                           : "#edf0f5"
                                                    font.family: theme.uiFont
                                                    font.pixelSize: 10
                                                    font.bold: true
                                                }

                                                Text {
                                                    text: theme.currentTheme === modelData.name
                                                          ? "ACTIVE"
                                                          : "Select"
                                                    color: modelData.accent
                                                    font.family: theme.uiFont
                                                    font.pixelSize: 8
                                                    font.bold: true
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor

                                                onClicked: {
                                                    theme.currentTheme = modelData.name
                                                    theme.accentColor = modelData.accent
                                                    backend.set_theme(modelData.name)
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Accent section
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Text {
                                    text: "ACCENT COLOR"
                                    color: theme.textSecondary
                                    font.family: theme.uiFont
                                    font.pixelSize: 9
                                    font.bold: true
                                    font.letterSpacing: 1
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Repeater {
                                        model: [
                                            "#0ea5e9",
                                            "#8b5cf6",
                                            "#10b981",
                                            "#f59e0b",
                                            "#ef4444",
                                            "#ec4899",
                                            "#6366f1",
                                            "#14b8a6"
                                        ]

                                        delegate: Rectangle {
                                            Layout.preferredWidth: 30
                                            Layout.preferredHeight: 30
                                            radius: 15
                                            color: modelData

                                            border.color: theme.accentColor === modelData
                                                          ? theme.textPrimary
                                                          : "transparent"
                                            border.width: 2

                                            Rectangle {
                                                anchors.fill: parent
                                                anchors.margins: 4
                                                radius: width / 2
                                                color: "transparent"
                                                border.color: Qt.rgba(1, 1, 1, 0.18)
                                                border.width: 1
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor

                                                onClicked: settingsRoot.setAccent(modelData)
                                            }
                                        }
                                    }
                                }
                            }

                            // Interface section
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0

                                Text {
                                    text: "INTERFACE"
                                    color: theme.textSecondary
                                    font.family: theme.uiFont
                                    font.pixelSize: 9
                                    font.bold: true
                                    font.letterSpacing: 1
                                    Layout.bottomMargin: 8
                                }

                                SettingRow {
                                    title: "Smooth UI animations"
                                    description: "Animate non-essential interface transitions."
                                    checked: theme.animationsEnabled
                                    onToggled: theme.animationsEnabled = checked
                                }

                                SettingRow {
                                    title: "Music visualizations"
                                    description: "Enable reactive visual effects in the music player."
                                    checked: theme.musicVisualizationsEnabled
                                    onToggled: theme.musicVisualizationsEnabled = checked
                                }

                                SettingRow {
                                    title: "Compact spacing"
                                    description: "Reduce padding throughout the interface."
                                    checked: theme.compactMode
                                    onToggled: theme.compactMode = checked
                                }
                            }
                        }

                        // ═════════════════════════════════════════════════════
                        // EDITOR
                        // ═════════════════════════════════════════════════════

                        ColumnLayout {
                            visible: settingsRoot.categoryVisible("Editor")
                            Layout.fillWidth: true
                            spacing: 20

                            ColumnLayout {
                                spacing: 3

                                Text {
                                    text: "Editor"
                                    color: theme.textPrimary
                                    font.family: theme.uiFont
                                    font.pixelSize: 18
                                    font.bold: true
                                }

                                Text {
                                    text: "Configure code editing and navigation."
                                    color: theme.textMuted
                                    font.family: theme.uiFont
                                    font.pixelSize: 10
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0

                                Text {
                                    text: "EDITOR"
                                    color: theme.textSecondary
                                    font.family: theme.uiFont
                                    font.pixelSize: 9
                                    font.bold: true
                                    font.letterSpacing: 1
                                    Layout.bottomMargin: 8
                                }

                                SettingRow {
                                    title: "Line numbers"
                                    description: "Show line numbers beside the editor."
                                    checked: theme.lineNumbersVisible
                                    onToggled: theme.lineNumbersVisible = checked
                                }

                                SettingRow {
                                    title: "Word wrap"
                                    description: "Wrap long lines instead of scrolling horizontally."
                                    checked: theme.wordWrap
                                    onToggled: theme.wordWrap = checked
                                }

                                SettingRow {
                                    title: "Bracket matching"
                                    description: "Highlight matching brackets and quotes."
                                    checked: theme.bracketMatching
                                    onToggled: theme.bracketMatching = checked
                                }

                                SettingRow {
                                    title: "Minimap"
                                    description: "Display a compact code overview."
                                    checked: theme.minimapVisible
                                    onToggled: theme.minimapVisible = checked
                                }
                            }

                            // Font size
                            Rectangle {
                                Layout.fillWidth: true
                                height: 58
                                radius: 8
                                color: theme.bgCard
                                border.color: theme.borderSubtle
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 10

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        Text {
                                            text: "Editor font size"
                                            color: theme.textPrimary
                                            font.family: theme.uiFont
                                            font.pixelSize: 11
                                        }

                                        Text {
                                            text: "Current size: " + theme.editorFontSize + " px"
                                            color: theme.textMuted
                                            font.family: theme.uiFont
                                            font.pixelSize: 9
                                        }
                                    }

                                    SpinBox {
                                        from: 10
                                        to: 28
                                        value: theme.editorFontSize

                                        onValueChanged: {
                                            theme.editorFontSize = value

                                            if (editorArea)
                                                editorArea.editorFontSize = value
                                        }
                                    }
                                }
                            }
                        }

                        // ═════════════════════════════════════════════════════
                        // MUSIC
                        // ═════════════════════════════════════════════════════

                        ColumnLayout {
                            visible: settingsRoot.categoryVisible("Music")
                            Layout.fillWidth: true
                            spacing: 20

                            ColumnLayout {
                                spacing: 3

                                Text {
                                    text: "Music"
                                    color: theme.textPrimary
                                    font.family: theme.uiFont
                                    font.pixelSize: 18
                                    font.bold: true
                                }

                                Text {
                                    text: "Control playback visuals and the audio experience."
                                    color: theme.textMuted
                                    font.family: theme.uiFont
                                    font.pixelSize: 10
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 76
                                radius: 9
                                color: Qt.rgba(
                                    Qt.color(theme.accentColor).r,
                                    Qt.color(theme.accentColor).g,
                                    Qt.color(theme.accentColor).b,
                                    0.08
                                )
                                border.color: Qt.rgba(
                                    Qt.color(theme.accentColor).r,
                                    Qt.color(theme.accentColor).g,
                                    Qt.color(theme.accentColor).b,
                                    0.20
                                )
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 12

                                    Text {
                                        text: "♫"
                                        color: theme.accentColor
                                        font.pixelSize: 22
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3

                                        Text {
                                            text: "DGX Audio Engine"
                                            color: theme.textPrimary
                                            font.family: theme.uiFont
                                            font.pixelSize: 11
                                            font.bold: true
                                        }

                                        Text {
                                            text: "FFmpeg PCM direct streaming"
                                            color: theme.textSecondary
                                            font.family: theme.uiFont
                                            font.pixelSize: 9
                                        }

                                        Text {
                                            text: "YTMusic search backend"
                                            color: theme.textMuted
                                            font.family: theme.uiFont
                                            font.pixelSize: 9
                                        }
                                    }
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0

                                Text {
                                    text: "PLAYBACK"
                                    color: theme.textSecondary
                                    font.family: theme.uiFont
                                    font.pixelSize: 9
                                    font.bold: true
                                    font.letterSpacing: 1
                                    Layout.bottomMargin: 8
                                }

                                SettingRow {
                                    title: "Reactive vinyl & visualizations"
                                    description: "Allow the vinyl and visual effects to react to playback."
                                    checked: theme.musicVisualizationsEnabled
                                    onToggled: theme.musicVisualizationsEnabled = checked
                                }

                                SettingRow {
                                    title: "Continuous vinyl rotation"
                                    description: "Keep the record rotating while a song is playing."
                                    checked: theme.animationsEnabled
                                    onToggled: theme.animationsEnabled = checked
                                }
                            }
                        }

                        // ═════════════════════════════════════════════════════
                        // GENERAL
                        // ═════════════════════════════════════════════════════

                        ColumnLayout {
                            visible: settingsRoot.categoryVisible("General")
                            Layout.fillWidth: true
                            spacing: 20

                            ColumnLayout {
                                spacing: 3

                                Text {
                                    text: "General"
                                    color: theme.textPrimary
                                    font.family: theme.uiFont
                                    font.pixelSize: 18
                                    font.bold: true
                                }

                                Text {
                                    text: "Workspace and application preferences."
                                    color: theme.textMuted
                                    font.family: theme.uiFont
                                    font.pixelSize: 10
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0

                                Text {
                                    text: "WORKSPACE"
                                    color: theme.textSecondary
                                    font.family: theme.uiFont
                                    font.pixelSize: 9
                                    font.bold: true
                                    font.letterSpacing: 1
                                    Layout.bottomMargin: 8
                                }

                                SettingRow {
                                    title: "Auto-save files on close"
                                    description: "Save modified files before closing the workspace."
                                    checked: true
                                }

                                SettingRow {
                                    title: "Remember workspace"
                                    description: "Restore the previous workspace when DGX Studio starts."
                                    checked: true
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: theme.borderSubtle
                            }

                            ColumnLayout {
                                spacing: 3

                                Text {
                                    text: "DGX Studio"
                                    color: theme.textSecondary
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    font.bold: true
                                }

                                Text {
                                    text: "v2.0  •  PySide6 + QML"
                                    color: theme.textMuted
                                    font.family: theme.uiFont
                                    font.pixelSize: 9
                                }
                            }
                        }

                        Item {
                            Layout.preferredHeight: 12
                        }
                    }
                }
            }
        }
    }

    // ═════════════════════════════════════════════════════════════════════════
    // REUSABLE SETTING ROW
    // ═════════════════════════════════════════════════════════════════════════

    component SettingRow: Rectangle {
        id: settingRow

        property string title: ""
        property string description: ""
        property bool checked: false

        signal toggled(bool checked)

        Layout.fillWidth: true
        height: 64

        color: rowMouse.containsMouse
               ? theme.bgHover
               : "transparent"

        radius: 8

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 10
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3

                Text {
                    text: settingRow.title
                    color: theme.textPrimary
                    font.family: theme.uiFont
                    font.pixelSize: 11
                }

                Text {
                    text: settingRow.description
                    color: theme.textMuted
                    font.family: theme.uiFont
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            Switch {
                checked: settingRow.checked

                onToggled: settingRow.toggled(checked)
            }
        }

        MouseArea {
            id: rowMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            z: -1
        }
    }
}
