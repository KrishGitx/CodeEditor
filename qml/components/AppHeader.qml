import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15
import QtQuick.Window 2.15

Rectangle {
    id: appHeaderRoot

    height: 34
    color: theme.bgHeader

    // -------------------------------------------------------------------------
    // Public API — preserved for main.qml
    // -------------------------------------------------------------------------
    signal openFileDialogRequested()
    signal openWorkspaceDialogRequested()
    signal settingsRequested()
    signal toggleTerminalRequested()
    signal toggleMusicRequested()
    signal toggleAIRequested()
    signal toggleZenRequested()
    signal saveRequested()
    signal newFileRequested()
    signal presetRequested(string preset)

    property string activeFilePath: ""
    property string activeProjectName: "DGX Studio"

    // -------------------------------------------------------------------------
    // Frameless-window dragging
    // -------------------------------------------------------------------------
    MouseArea {
        id: windowDragArea

        anchors.fill: parent
        anchors.rightMargin: 120

        property point clickPos: Qt.point(0, 0)

        onPressed: {
            clickPos = Qt.point(mouse.x, mouse.y)
        }

        onPositionChanged: {
            var delta = Qt.point(
                mouse.x - clickPos.x,
                mouse.y - clickPos.y
            )

            var newX = mainWindow.x + delta.x
            var newY = mainWindow.y + delta.y

            if (newY <= 0) {
                mainWindow.visibility = Window.Maximized
            } else {
                if (mainWindow.visibility === Window.Maximized)
                    mainWindow.visibility = Window.Windowed

                mainWindow.x = newX
                mainWindow.y = newY
            }
        }

        onDoubleClicked: {
            if (mainWindow.visibility === Window.Maximized)
                mainWindow.visibility = Window.Windowed
            else
                mainWindow.visibility = Window.Maximized
        }
    }

    // -------------------------------------------------------------------------
    // Header content
    // -------------------------------------------------------------------------
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Small DGX mark.
        Item {
            Layout.preferredWidth: 42
            Layout.fillHeight: true

            Rectangle {
                width: 20
                height: 20
                radius: 5
                anchors.centerIn: parent
                color: theme.accentColor

                Text {
                    anchors.centerIn: parent
                    text: "D"
                    color: "#ffffff"
                    font.family: theme.uiFont
                    font.pixelSize: 11
                    font.bold: true
                }
            }
        }

        // ---------------------------------------------------------------------
        // Menus
        // ---------------------------------------------------------------------
        Row {
            Layout.fillHeight: true
            spacing: 1

            Repeater {
                model: [
                    { label: "File", menu: "file" },
                    { label: "Edit", menu: "edit" },
                    { label: "View", menu: "view" },
                    { label: "Presets", menu: "presets" }
                ]

                delegate: Rectangle {
                    id: menuButton

                    width: menuLabel.implicitWidth + 20
                    height: parent.height
                    radius: 4
                    color: menuMouse.containsMouse
                           ? theme.bgHover
                           : "transparent"

                    Text {
                        id: menuLabel

                        anchors.centerIn: parent
                        text: modelData.label
                        color: menuMouse.containsMouse
                               ? theme.textPrimary
                               : theme.textSecondary
                        font.family: theme.uiFont
                        font.pixelSize: 11
                    }

                    MouseArea {
                        id: menuMouse

                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onClicked: {
                            // Menus are Popup/Overlay items, so calculate the
                            // clicked button's real position in the overlay.
                            var p = menuButton.mapToItem(Overlay.overlay, 0, menuButton.height)

                            if (modelData.menu === "file") {
                                fileMenu.x = p.x
                                fileMenu.y = p.y
                                fileMenu.open()
                            } else if (modelData.menu === "edit") {
                                editMenu.x = p.x
                                editMenu.y = p.y
                                editMenu.open()
                            } else if (modelData.menu === "view") {
                                viewMenu.x = p.x
                                viewMenu.y = p.y
                                viewMenu.open()
                            } else if (modelData.menu === "presets") {
                                presetsMenu.x = p.x
                                presetsMenu.y = p.y
                                presetsMenu.open()
                            }
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Center workspace identity
        // ---------------------------------------------------------------------
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Row {
                anchors.centerIn: parent
                spacing: 7

                Text {
                    text: appHeaderRoot.activeProjectName
                    color: theme.textMuted
                    font.family: theme.uiFont
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    visible: appHeaderRoot.activeFilePath.length > 0
                    text: "›"
                    color: theme.textMuted
                    font.pixelSize: 12
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    visible: appHeaderRoot.activeFilePath.length > 0
                    text: appHeaderRoot.activeFilePath
                          .split("/")
                          .pop()
                          .split("\\")
                          .pop()
                    color: theme.textSecondary
                    font.family: theme.monoFont
                    font.pixelSize: 11
                    elide: Text.ElideMiddle
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        // ---------------------------------------------------------------------
        // Window controls
        // ---------------------------------------------------------------------
        Row {
            Layout.preferredWidth: 120
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                width: 40
                height: parent.height
                color: minMouse.containsMouse
                       ? theme.bgHover
                       : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "—"
                    color: theme.textSecondary
                    font.pixelSize: 10
                }

                MouseArea {
                    id: minMouse

                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onClicked:
                        mainWindow.visibility = Window.Minimized
                }
            }

            Rectangle {
                width: 40
                height: parent.height
                color: maxMouse.containsMouse
                       ? theme.bgHover
                       : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: mainWindow.visibility === Window.Maximized
                          ? "❐"
                          : "□"
                    color: theme.textSecondary
                    font.pixelSize: 11
                }

                MouseArea {
                    id: maxMouse

                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onClicked: {
                        if (mainWindow.visibility === Window.Maximized)
                            mainWindow.visibility = Window.Windowed
                        else
                            mainWindow.visibility = Window.Maximized
                    }
                }
            }

            Rectangle {
                width: 40
                height: parent.height
                color: closeMouse.containsMouse
                       ? "#ef4444"
                       : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "×"
                    color: closeMouse.containsMouse
                           ? "#ffffff"
                           : theme.textSecondary
                    font.pixelSize: 15
                }

                MouseArea {
                    id: closeMouse

                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onClicked: mainWindow.close()
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // Shared popup styling
    // -------------------------------------------------------------------------
    component HeaderMenu: Menu {
        id: menuRoot

        background: Rectangle {
            implicitWidth: 220
            color: theme.bgCard
            radius: 8
            opacity: 0.98
        }
    }

    // -------------------------------------------------------------------------
    // File
    // -------------------------------------------------------------------------
    HeaderMenu {
        id: fileMenu

        Action {
            text: "New File    Ctrl+N"
            onTriggered: appHeaderRoot.newFileRequested()
        }

        Action {
            text: "Open File    Ctrl+O"
            onTriggered: appHeaderRoot.openFileDialogRequested()
        }

        Action {
            text: "Open Folder    Ctrl+Shift+O"
            onTriggered: appHeaderRoot.openWorkspaceDialogRequested()
        }

        Action {
            text: "Save File    Ctrl+S"
            onTriggered: appHeaderRoot.saveRequested()
        }

        MenuSeparator {}

        Action {
            text: "Preferences    Ctrl+,"
            onTriggered: appHeaderRoot.settingsRequested()
        }

        Action {
            text: "Exit DGX Studio"
            onTriggered: mainWindow.close()
        }
    }

    // -------------------------------------------------------------------------
    // Edit
    // -------------------------------------------------------------------------
    HeaderMenu {
        id: editMenu

        Action {
            text: "Find & Replace    Ctrl+F"
            onTriggered: editorArea.toggleFindBar()
        }

        Action {
            text: "Save File    Ctrl+S"
            onTriggered: appHeaderRoot.saveRequested()
        }

        MenuSeparator {}

        Action {
            text: "Command Menu    Ctrl+M"
            onTriggered:
                radialMenu.openAt(
                    mainWindow.width / 2,
                    mainWindow.height / 2
                )
        }
    }

    // -------------------------------------------------------------------------
    // View
    // -------------------------------------------------------------------------
    HeaderMenu {
        id: viewMenu

        Action {
            text: "File Explorer    Ctrl+B"
            onTriggered:
                mainWindow.explorerVisible =
                    !mainWindow.explorerVisible
        }

        Action {
            text: "AI Assistant"
            onTriggered: appHeaderRoot.toggleAIRequested()
        }

        Action {
            text: "Music Player"
            onTriggered: appHeaderRoot.toggleMusicRequested()
        }

        Action {
            text: "Terminal    Ctrl+`"
            onTriggered: appHeaderRoot.toggleTerminalRequested()
        }

        MenuSeparator {}

        Action {
            text: "Zen Mode    Ctrl+Shift+Z"
            onTriggered: appHeaderRoot.toggleZenRequested()
        }

        Action {
            text: "Preferences    Ctrl+,"
            onTriggered: appHeaderRoot.settingsRequested()
        }
    }

    // -------------------------------------------------------------------------
    // Workspace presets
    // -------------------------------------------------------------------------
    HeaderMenu {
        id: presetsMenu

        Action {
            text: "Full Studio"
            onTriggered: appHeaderRoot.presetRequested("Full")
        }

        Action {
            text: "Coding"
            onTriggered: appHeaderRoot.presetRequested("Coding")
        }

        Action {
            text: "AI Assistant"
            onTriggered: appHeaderRoot.presetRequested("AI")
        }

        Action {
            text: "Music"
            onTriggered: appHeaderRoot.presetRequested("Music")
        }

        Action {
            text: "Debugging"
            onTriggered: appHeaderRoot.presetRequested("Debugging")
        }

        Action {
            text: "Focus / Zen"
            onTriggered: appHeaderRoot.presetRequested("Focus")
        }
    }

}
