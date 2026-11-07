import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property string activeProjectName: ""
    property string activeFilePath: ""
    property string activeFileName: ""
    property bool isDirty: false
    property bool isMaximized: false
    property bool explorerVisible: true
    property bool terminalVisible: false
    property bool aiVisible: false

    signal newFileRequested()
    signal openFileRequested()
    signal openFolderRequested()
    signal openRecentRequested(string folderPath)
    signal saveRequested()
    signal saveAsRequested()
    signal closeTabRequested()
    signal toggleExplorerRequested()
    signal toggleTerminalRequested()
    signal toggleAiRequested()
    signal toggleMusicRequested()
    signal toggleZenRequested()
    signal toggleSplitEditorRequested()
    signal findRequested()
    signal replaceRequested()
    signal formatRequested()
    signal undoRequested()
    signal redoRequested()
    signal settingsRequested()
    signal extensionsRequested()
    signal openWebPreviewRequested()
    signal openColorPickerRequested()
    signal toggleWhiteboardRequested()
    signal runFileRequested()
    signal presetSelected(string presetName)
    signal themeSelected(string themeName)

    height: 32
    color: theme ? theme.bgHeader : "#181818"

    // Bottom single border line separating header from workspace
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: theme ? theme.borderSubtle : "#282828"
    }

    // Window Dragging Handling with Native Windows Aero Snap
    MouseArea {
        id: dragArea
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton

        onPressed: function(mouse) {
            var win = root.Window.window;
            if (win && win.startSystemMove) {
                win.startSystemMove();
            }
        }

        onDoubleClicked: function(mouse) {
            var win = (root.Window && root.Window.window) ? root.Window.window : null;
            if (typeof backend !== "undefined" && backend && backend.toggle_maximize_window) {
                backend.toggle_maximize_window();
            } else if (win) {
                if (win.visibility === Window.Maximized || win.visibility === Window.FullScreen || root.isMaximized) {
                    win.showNormal();
                } else {
                    win.showMaximized();
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 0
        spacing: 4

        // 1. DGX Studio Branding
        Text {
            text: "Pod Studio"
            color: theme ? theme.textPrimary : "#cccccc"
            font.pixelSize: 12
            font.bold: true
            font.family: theme ? theme.fontFamilyUi : "sans-serif"
            Layout.rightMargin: 6
        }

        // 2. Main Desktop Menu Bar
        Row {
            spacing: 2
            z: 10

            // File Menu
            Rectangle {
                id: fileBtn
                width: fileText.contentWidth + 14
                height: 24
                radius: theme ? theme.radiusSm : 2
                color: fileMenu.visible ? (theme ? theme.bgSurfaceActive : "#37373d") : (fileMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")

                Text {
                    id: fileText
                    anchors.centerIn: parent
                    text: "File"
                    color: theme ? theme.textPrimary : "#cccccc"
                    font.pixelSize: 12
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                MouseArea {
                    id: fileMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: fileMenu.open()
                }

                Menu {
                    id: fileMenu
                    y: fileBtn.height + 2
                    background: Rectangle {
                        implicitWidth: 230
                        color: theme ? theme.bgPopup : "#252526"
                        border.color: theme ? theme.borderNormal : "#333333"
                        radius: theme ? theme.radiusSm : 3
                    }

                    Action { text: "New File\tCtrl+N"; onTriggered: root.newFileRequested() }
                    Action { text: "Open File...\tCtrl+O"; onTriggered: root.openFileRequested() }
                    Action { text: "Open Folder...\tCtrl+Shift+O"; onTriggered: root.openFolderRequested() }
                    Menu {
                        title: "Open Recent"
                        id: recentProjectsMenu
                        Instantiator {
                            model: (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_recent_projects) ? settingsBackend.get_recent_projects() : []
                            onObjectAdded: function(index, object) { recentProjectsMenu.insertItem(index, object); }
                            onObjectRemoved: function(index, object) { recentProjectsMenu.removeItem(object); }
                            delegate: MenuItem {
                                text: (modelData && modelData.name) ? modelData.name : (modelData ? modelData.toString() : "")
                                onTriggered: root.openRecentRequested(modelData.path)
                            }
                        }
                    }
                    MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: theme ? theme.borderSubtle : "#282828" } }
                    Action { text: "Save\tCtrl+S"; onTriggered: root.saveRequested() }
                    Action { text: "Save As...\tCtrl+Shift+S"; onTriggered: root.saveAsRequested() }
                    MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: theme ? theme.borderSubtle : "#282828" } }
                    Action { text: "Close Tab\tCtrl+W"; onTriggered: root.closeTabRequested() }
                    Action { text: "Exit\tAlt+F4"; onTriggered: Qt.quit() }

                    delegate: MenuItem {
                        id: fileItm
                        implicitHeight: 28
                        implicitWidth: 230
                        contentItem: RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 8
                            Text {
                                Layout.fillWidth: true
                                text: fileItm.text.split("\t")[0]
                                color: fileItm.highlighted ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                font.pixelSize: 12
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                verticalAlignment: Text.AlignVCenter
                            }
                            Text {
                                text: fileItm.text.indexOf("\t") !== -1 ? fileItm.text.split("\t")[1] : ""
                                color: fileItm.highlighted ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                                font.pixelSize: 11
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                verticalAlignment: Text.AlignVCenter
                                visible: text.length > 0
                            }
                        }
                        background: Rectangle {
                            color: fileItm.highlighted ? (theme ? theme.bgSelected : "#04395e") : "transparent"
                        }
                    }
                }
            }

            // Edit Menu
            Rectangle {
                id: editBtn
                width: editText.contentWidth + 14
                height: 24
                radius: theme ? theme.radiusSm : 2
                color: editMenu.visible ? (theme ? theme.bgSurfaceActive : "#37373d") : (editMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")

                Text {
                    id: editText
                    anchors.centerIn: parent
                    text: "Edit"
                    color: theme ? theme.textPrimary : "#cccccc"
                    font.pixelSize: 12
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                MouseArea {
                    id: editMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: editMenu.open()
                }

                Menu {
                    id: editMenu
                    y: editBtn.height + 2
                    background: Rectangle {
                        implicitWidth: 230
                        color: theme ? theme.bgPopup : "#252526"
                        border.color: theme ? theme.borderNormal : "#333333"
                        radius: theme ? theme.radiusSm : 3
                    }

                    Action { text: "Undo\tCtrl+Z"; onTriggered: root.undoRequested() }
                    Action { text: "Redo\tCtrl+Y"; onTriggered: root.redoRequested() }
                    MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: theme ? theme.borderSubtle : "#282828" } }
                    Action { text: "Find\tCtrl+F"; onTriggered: root.findRequested() }
                    Action { text: "Replace\tCtrl+H"; onTriggered: root.replaceRequested() }
                    Action { text: "Format Document\tShift+Alt+F"; onTriggered: root.formatRequested() }

                    delegate: MenuItem {
                        id: editItm
                        implicitHeight: 28
                        implicitWidth: 230
                        contentItem: RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 8
                            Text {
                                Layout.fillWidth: true
                                text: editItm.text.split("\t")[0]
                                color: editItm.highlighted ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                font.pixelSize: 12
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                verticalAlignment: Text.AlignVCenter
                            }
                            Text {
                                text: editItm.text.indexOf("\t") !== -1 ? editItm.text.split("\t")[1] : ""
                                color: editItm.highlighted ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                                font.pixelSize: 11
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                verticalAlignment: Text.AlignVCenter
                                visible: text.length > 0
                            }
                        }
                        background: Rectangle {
                            color: editItm.highlighted ? (theme ? theme.bgSelected : "#04395e") : "transparent"
                        }
                    }
                }
            }

            // View Menu
            Rectangle {
                id: viewBtn
                width: viewText.contentWidth + 14
                height: 24
                radius: theme ? theme.radiusSm : 2
                color: viewMenu.visible ? (theme ? theme.bgSurfaceActive : "#37373d") : (viewMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")

                Text {
                    id: viewText
                    anchors.centerIn: parent
                    text: "View"
                    color: theme ? theme.textPrimary : "#cccccc"
                    font.pixelSize: 12
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                MouseArea {
                    id: viewMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: viewMenu.open()
                }

                Menu {
                    id: viewMenu
                    y: viewBtn.height + 2
                    background: Rectangle {
                        implicitWidth: 250
                        color: theme ? theme.bgPopup : "#252526"
                        border.color: theme ? theme.borderNormal : "#333333"
                        radius: theme ? theme.radiusSm : 3
                    }

                    Action { text: "Live Web Preview\tCtrl+Shift+V"; onTriggered: root.openWebPreviewRequested() }
                    Action { text: "Architecture Whiteboard\tCtrl+Alt+W"; onTriggered: root.toggleWhiteboardRequested() }
                    Action { text: "Split Editor Side-by-Side\tCtrl+\\"; onTriggered: root.toggleSplitEditorRequested() }
                    Action { text: "Inline Color Picker\tCtrl+Shift+C"; onTriggered: root.openColorPickerRequested() }
                    MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: theme ? theme.borderSubtle : "#282828" } }
                    Action { text: "Toggle Explorer\tCtrl+B"; onTriggered: root.toggleExplorerRequested() }
                    Action { text: "Toggle Terminal\tCtrl+`"; onTriggered: root.toggleTerminalRequested() }
                    Action { text: "Toggle AI Panel\t"; onTriggered: root.toggleAiRequested() }
                    Action { text: "Toggle Music Panel\t"; onTriggered: root.toggleMusicRequested() }
                    Action { text: "Zen Mode\tCtrl+Shift+Z"; onTriggered: root.toggleZenRequested() }
                    MenuSeparator { contentItem: Rectangle { implicitHeight: 1; color: theme ? theme.borderSubtle : "#282828" } }

                    Action { text: "Extensions...\tCtrl+Shift+X"; onTriggered: root.extensionsRequested() }
                    Action { text: "Preferences...\tCtrl+,"; onTriggered: root.settingsRequested() }

                    delegate: MenuItem {
                        id: viewItm
                        implicitHeight: 28
                        implicitWidth: 250
                        contentItem: RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 8
                            Text {
                                Layout.fillWidth: true
                                text: viewItm.text.split("\t")[0]
                                color: viewItm.highlighted ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                font.pixelSize: 12
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                verticalAlignment: Text.AlignVCenter
                            }
                            Text {
                                text: viewItm.text.indexOf("\t") !== -1 ? viewItm.text.split("\t")[1] : ""
                                color: viewItm.highlighted ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                                font.pixelSize: 11
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                verticalAlignment: Text.AlignVCenter
                                visible: text.length > 0
                            }
                        }
                        background: Rectangle {
                            color: viewItm.highlighted ? (theme ? theme.bgSelected : "#04395e") : "transparent"
                        }
                    }
                }
            }

            // Run Menu
            Rectangle {
                id: runBtn
                width: runText.contentWidth + 14
                height: 24
                radius: theme ? theme.radiusSm : 2
                color: runMenu.visible ? (theme ? theme.bgSurfaceActive : "#37373d") : (runMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")

                Text {
                    id: runText
                    anchors.centerIn: parent
                    text: "Run"
                    color: theme ? theme.textPrimary : "#cccccc"
                    font.pixelSize: 12
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                MouseArea {
                    id: runMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: runMenu.open()
                }

                Menu {
                    id: runMenu
                    y: runBtn.height + 2
                    background: Rectangle {
                        implicitWidth: 220
                        color: theme ? theme.bgPopup : "#252526"
                        border.color: theme ? theme.borderNormal : "#333333"
                        radius: theme ? theme.radiusSm : 3
                    }

                    Action { text: "Run Active File\tF5"; onTriggered: root.runFileRequested() }
                    Action { text: "Open Terminal\tCtrl+`"; onTriggered: root.toggleTerminalRequested() }

                    delegate: MenuItem {
                        id: runItm
                        implicitHeight: 28
                        implicitWidth: 220
                        contentItem: RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 8
                            Text {
                                Layout.fillWidth: true
                                text: runItm.text.split("\t")[0]
                                color: runItm.highlighted ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                font.pixelSize: 12
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                verticalAlignment: Text.AlignVCenter
                            }
                            Text {
                                text: runItm.text.indexOf("\t") !== -1 ? runItm.text.split("\t")[1] : ""
                                color: runItm.highlighted ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                                font.pixelSize: 11
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                verticalAlignment: Text.AlignVCenter
                                visible: text.length > 0
                            }
                        }
                        background: Rectangle {
                            color: runItm.highlighted ? (theme ? theme.bgSelected : "#04395e") : "transparent"
                        }
                    }
                }
            }
        }

        // Center Title (Active file or empty)
        Item {
            Layout.fillWidth: true
            height: parent.height

             Text {
                 anchors.centerIn: parent
                 width: Math.min(implicitWidth, Math.max(0, parent.width - 20))
                 visible: parent.width > 100
                     text: root.activeFileName ? (root.activeFileName + (root.isDirty ? " *" : "") + " - Pod Studio") : "Pod Studio"
                 color: theme ? theme.textMuted : "#656565"
                 font.pixelSize: 11
                 font.family: theme ? theme.fontFamilyUi : "sans-serif"
                 elide: Text.ElideMiddle
             }
        }

        // 3. Right Header Actions & Window Controls
        RowLayout {
            spacing: 2
            z: 10

            // 1. Toggle Primary Side Bar (Left Explorer)
            LayoutToggleButton {
                panel: "left"
                active: root.explorerVisible
                toolTipText: "Toggle Primary Side Bar (Ctrl+B)"
                onClicked: root.toggleExplorerRequested()
            }

            // 2. Toggle Panel (Bottom Terminal)
            LayoutToggleButton {
                panel: "bottom"
                active: root.terminalVisible
                toolTipText: "Toggle Panel (Ctrl+`)"
                onClicked: root.toggleTerminalRequested()
            }

            // 3. Toggle Secondary Side Bar (Right AI Workspace)
            LayoutToggleButton {
                panel: "right"
                active: root.aiVisible
                toolTipText: "Toggle Secondary Side Bar"
                onClicked: root.toggleAiRequested()
            }

            Item { width: 4; height: 1 }

            // Minimize
            Rectangle {
                width: 32
                height: 32
                color: minMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                VectorIcon {
                    anchors.centerIn: parent
                    name: "minimize"
                    size: 10
                    color: theme ? theme.textSecondary : "#858585"
                }

                MouseArea {
                    id: minMa
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        var win = (root.Window && root.Window.window) ? root.Window.window : null;
                        if (win) win.showMinimized();
                    }
                }
            }

            // Maximize / Restore
            Rectangle {
                width: 32
                height: 32
                color: maxMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                VectorIcon {
                    anchors.centerIn: parent
                    name: root.isMaximized ? "restore" : "maximize"
                    size: 10
                    color: theme ? theme.textSecondary : "#858585"
                }

                ToolTip.visible: maxMa.containsMouse
                ToolTip.text: root.isMaximized ? "Restore" : "Maximize"

                MouseArea {
                    id: maxMa
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        var win = (root.Window && root.Window.window) ? root.Window.window : null;
                        if (typeof backend !== "undefined" && backend && backend.toggle_maximize_window) {
                            backend.toggle_maximize_window();
                        } else if (win) {
                            if (win.visibility === Window.Maximized || win.visibility === Window.FullScreen || root.isMaximized) {
                                win.showNormal();
                            } else {
                                win.showMaximized();
                            }
                        }
                    }
                }
            }

            // Close Application
            Rectangle {
                width: 36
                height: 32
                color: closeAppMa.containsMouse ? (theme ? theme.error : "#f14c4c") : "transparent"

                VectorIcon {
                    anchors.centerIn: parent
                    name: "close"
                    size: 11
                    color: closeAppMa.containsMouse ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                }

                MouseArea {
                    id: closeAppMa
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: Qt.quit()
                }
            }
        }
    }
}
