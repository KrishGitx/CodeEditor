import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Rectangle {
    id: explorerRoot
    color: theme.bgSidebar

    signal fileSelected(string filePath, string fileName)
    signal openWorkspaceRequested()

    property string currentWorkspacePath: ""
    property string activeFilePath: ""
    property string searchFilter: ""

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ═══════════════════════════════════════════════════════════════
        // 1. Sidebar Header
        // ═══════════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            color: theme.bgHeader

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8

                Text {
                    text: "PROJECT EXPLORER"
                    color: theme.textSecondary
                    font.bold: true
                    font.pixelSize: 11
                    font.family: theme.uiFont
                    font.letterSpacing: 0.8
                    Layout.fillWidth: true
                }

                // Open Workspace Button
                Rectangle {
                    width: 24
                    height: 24
                    radius: 4
                    color: openFolderMouse.containsMouse ? theme.bgHover : "transparent"

                    Text {
                        text: "📁"
                        font.pixelSize: 11
                        anchors.centerIn: parent
                    }

                    MouseArea {
                        id: openFolderMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: explorerRoot.openWorkspaceRequested()
                    }
                }
            }

            Rectangle {
                color: theme.borderSubtle
                height: 1
                width: parent.width
                anchors.bottom: parent.bottom
            }
        }

        // ═══════════════════════════════════════════════════════════════
        // 2. Project Folder / Filter Header
        // ═══════════════════════════════════════════════════════════════
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            color: theme.bgSidebar

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6

                TextField {
                    id: fileFilterInput
                    Layout.fillWidth: true
                    placeholderText: explorerRoot.currentWorkspacePath !== "" ? "Filter files..." : "No project folder"
                    placeholderTextColor: theme.textMuted
                    color: theme.textPrimary
                    font.pixelSize: 11
                    font.family: theme.uiFont
                    enabled: explorerRoot.currentWorkspacePath !== ""
                    background: Rectangle {
                        color: fileFilterInput.activeFocus ? theme.bgInput : "transparent"
                        border.color: fileFilterInput.activeFocus ? theme.accentColor : "transparent"
                        radius: theme.radiusSm
                    }
                    onTextChanged: {
                        explorerRoot.searchFilter = fileFilterInput.text.toLowerCase().trim()
                    }
                }
            }

            Rectangle {
                color: theme.borderSubtle
                height: 1
                width: parent.width
                anchors.bottom: parent.bottom
            }
        }

        // ═══════════════════════════════════════════════════════════════
        // 3. File Tree View
        // ═══════════════════════════════════════════════════════════════
        ListView {
            id: fileList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: ListModel { id: treeModel }

            // Empty state when no folder opened
            Item {
                anchors.fill: parent
                visible: treeModel.count === 0

                Column {
                    anchors.centerIn: parent
                    spacing: 12
                    width: parent.width - 32

                    Text {
                        text: "No Folder Opened"
                        color: theme.textSecondary
                        font.pixelSize: 13
                        font.bold: true
                        font.family: theme.uiFont
                        horizontalAlignment: Text.AlignHCenter
                        width: parent.width
                    }

                    Text {
                        text: "Open a project directory to explore, edit, and run code."
                        color: theme.textMuted
                        font.pixelSize: 11
                        font.family: theme.uiFont
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        width: parent.width
                    }

                    Button {
                        text: "Open Folder (Ctrl+Shift+O)"
                        anchors.horizontalCenter: parent.horizontalCenter
                        onClicked: explorerRoot.openWorkspaceRequested()
                        background: Rectangle {
                            color: parent.hovered ? theme.accentColor : theme.bgCard
                            border.color: theme.accentColor
                            radius: 6
                            implicitWidth: 170
                            implicitHeight: 32
                        }
                        contentItem: Text {
                            text: parent.text
                            color: parent.hovered ? "#ffffff" : theme.textPrimary
                            font.pixelSize: 11
                            font.family: theme.uiFont
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }

            function isItemVisible(type, name) {
                if (type === "Folder") {
                    for (var x = 0; x < treeModel.count; x++) {
                        if (treeModel.get(x).parentId === name) {
                            var currentVis = treeModel.get(x).canSee
                            treeModel.setProperty(x, "canSee", !currentVis)
                        }
                    }
                }
            }

            function getPadding(index, parentId) {
                var depth = 0
                for (var x = index - 1; x >= 0; x--) {
                    if (treeModel.get(x).name === parentId) {
                        depth += 1 + getPadding(x, treeModel.get(x).parentId)
                    }
                }
                return depth
            }

            function getFullPath(index, parentId) {
                var path = ""
                for (var x = index - 1; x >= 0; x--) {
                    if (treeModel.get(x).name === parentId) {
                        path += getFullPath(x, treeModel.get(x).parentId) + treeModel.get(x).name + "/"
                    }
                }
                return path
            }

            delegate: Rectangle {
                id: itemDelegate
                width: fileList.width
                
                readonly property bool matchesFilter: explorerRoot.searchFilter === "" || name.toLowerCase().includes(explorerRoot.searchFilter)
                readonly property bool shouldShow: canSee && matchesFilter

                height: shouldShow ? 28 : 0
                visible: shouldShow
                color: itemMouse.containsMouse ? theme.bgHover : "transparent"

                property bool isFolder: type === "Folder"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8 + (fileList.getPadding(index, parentId) * 12)
                    anchors.rightMargin: 8
                    spacing: 6

                    // Folder arrow or file icon
                    Text {
                        text: isFolder ? "▾" : getFileIcon(name)
                        color: isFolder ? theme.textSecondary : getFileColor(name)
                        font.pixelSize: isFolder ? 11 : 12
                        Layout.preferredWidth: 14
                        horizontalAlignment: Text.AlignHCenter
                    }

                    // File or folder name
                    Text {
                        text: name
                        color: itemMouse.containsMouse ? theme.textPrimary : theme.textSecondary
                        font.pixelSize: 12
                        font.family: theme.uiFont
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: itemMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onClicked: {
                        if (isFolder) {
                            fileList.isItemVisible(type, name)
                        } else {
                            var relPath = fileList.getFullPath(index, parentId) + name
                            var fullPath = explorerRoot.currentWorkspacePath
                            if (!fullPath.endsWith("/") && !fullPath.endsWith("\\")) {
                                fullPath += "/"
                            }
                            fullPath += relPath
                            explorerRoot.fileSelected(fullPath, name)
                        }
                    }
                }
            }
        }
    }

    // Helper functions for icons & colors
    function getFileIcon(fileName) {
        var ext = fileName.split(".").pop().toLowerCase()
        switch (ext) {
            case "py": return "🐍"
            case "js": case "ts": case "jsx": case "tsx": return "📜"
            case "cpp": case "c": case "h": case "hpp": return "⚙️"
            case "html": case "htm": return "🌐"
            case "css": case "scss": return "🎨"
            case "json": case "yaml": case "yml": case "toml": return "📋"
            case "md": return "📝"
            case "qml": return "💠"
            case "rs": return "🦀"
            case "go": return "🔷"
            case "sql": return "🗄️"
            case "sh": case "bat": case "ps1": return "⚡"
            default: return "📄"
        }
    }

    function getFileColor(fileName) {
        var ext = fileName.split(".").pop().toLowerCase()
        switch (ext) {
            case "py": return "#38bdf8"
            case "js": case "ts": return "#facc15"
            case "cpp": case "c": return "#60a5fa"
            case "html": return "#f97316"
            case "css": return "#38bdf8"
            case "json": return "#4ade80"
            case "qml": return "#a855f7"
            case "rs": return "#f87171"
            case "go": return "#38bdf8"
            default: return theme.textSecondary
        }
    }

    function populateModel(list, rootPath) {
        explorerRoot.currentWorkspacePath = rootPath
        treeModel.clear()
        for (var i = 0; i < list.length; i++) {
            var item = list[i]
            item.canSee = true
            treeModel.append(item)
        }
    }

    // Right border divider
    Rectangle {
        color: theme.borderSubtle
        width: 1
        height: parent.height
        anchors.right: parent.right
    }
}
