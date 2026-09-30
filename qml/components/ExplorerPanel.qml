import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property string workspacePath: ""
    property string workspaceName: "NO FOLDER OPENED"
    property string selectedFilePath: ""
    property var collapsedFolders: ({})
    property int collapseVersion: 0

    signal fileClicked(string filePath)
    signal openFolderRequested()
    signal newFileRequested()
    signal newFolderRequested()
    signal refreshRequested()

    color: theme ? theme.bgSidebar : "#181818"

    ListModel {
        id: fileTreeModel
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Explorer Header
        Rectangle {
            Layout.fillWidth: true
            height: 28
            color: theme ? theme.bgHeader : "#181818"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 6
                spacing: 4

                Text {
                    text: root.workspaceName.toUpperCase()
                    color: theme ? theme.textSecondary : "#858585"
                    font.pixelSize: 11
                    font.bold: true
                    font.letterSpacing: 0.5
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                // New File
                Rectangle {
                    width: 20
                    height: 20
                    radius: 2
                    color: newFileMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "new-file"
                        size: 11
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    ToolTip.visible: newFileMa.containsMouse
                    ToolTip.text: "New File"

                    MouseArea {
                        id: newFileMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.newFileRequested()
                    }
                }

                // New Folder
                Rectangle {
                    width: 20
                    height: 20
                    radius: 2
                    color: newFolderMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "new-folder"
                        size: 11
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    ToolTip.visible: newFolderMa.containsMouse
                    ToolTip.text: "New Folder"

                    MouseArea {
                        id: newFolderMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.newFolderRequested()
                    }
                }

                // Refresh
                Rectangle {
                    width: 20
                    height: 20
                    radius: 2
                    color: refreshMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "refresh"
                        size: 11
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    ToolTip.visible: refreshMa.containsMouse
                    ToolTip.text: "Refresh Explorer"

                    MouseArea {
                        id: refreshMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.refreshRequested()
                    }
                }
            }
        }

        // 2. Tree View
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ScrollView {
                anchors.fill: parent
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                ListView {
                    id: fileListView
                    anchors.fill: parent
                    model: fileTreeModel
                    boundsBehavior: Flickable.StopAtBounds

                    delegate: Rectangle {
                        id: itemRow
                        width: Math.max(fileListView.width, contentRow.width + 16)
                        readonly property bool isRowVisible: root.isItemVisible(model.parentFullPath, root.collapseVersion)
                        visible: isRowVisible
                        height: isRowVisible ? 22 : 0

                        color: isSelected ? (theme ? theme.bgSelected : "#04395e") : (rowMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")

                        readonly property bool isSelected: root.selectedFilePath === model.fullPath
                        readonly property bool isFolder: model.type === "Folder"
                        readonly property bool isCollapsed: isFolder && (root.collapsedFolders[model.fullPath.replace(/\\/g, "/")] === true)

                        RowLayout {
                            id: contentRow
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: Math.max(6, model.level * 12 + 6)
                            spacing: 4

                            // Chevron for Folders
                            Item {
                                width: 12
                                height: 12
                                visible: itemRow.isFolder

                                VectorIcon {
                                    anchors.centerIn: parent
                                    name: itemRow.isCollapsed ? "chevron-right" : "chevron-down"
                                    size: 8
                                    color: theme ? theme.textMuted : "#656565"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        root.toggleFolder(model.fullPath);
                                    }
                                }
                            }

                            Item {
                                width: 12
                                height: 12
                                visible: !itemRow.isFolder
                            }

                            // File / Folder Icon
                            VectorIcon {
                                name: itemRow.isFolder ? (itemRow.isCollapsed ? "folder" : "folder-open") : "file"
                                size: 12
                                color: itemRow.isFolder ? (theme ? theme.textSecondary : "#858585") : (theme ? theme.textMuted : "#656565")
                            }

                            // Label
                            Text {
                                text: model.name || ""
                                color: itemRow.isSelected ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                font.pixelSize: 12
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            }
                        }

                        MouseArea {
                            id: rowMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor

                            onClicked: {
                                if (itemRow.isFolder) {
                                    root.toggleFolder(model.fullPath);
                                } else {
                                    root.selectedFilePath = model.fullPath;
                                    root.fileClicked(model.fullPath);
                                }
                            }
                        }
                    }
                }
            }

            // Empty State
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 8
                visible: fileTreeModel.count === 0

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "You have not opened a folder."
                    color: theme ? theme.textMuted : "#656565"
                    font.pixelSize: 11
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Open Folder"
                    color: theme ? theme.accent : "#0078d4"
                    font.pixelSize: 12
                    font.underline: openFldrHover.containsMouse

                    MouseArea {
                        id: openFldrHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.openFolderRequested()
                    }
                }
            }
        }
    }

    function toggleFolder(fPath) {
        if (!fPath) return;
        var norm = fPath.replace(/\\/g, "/");
        var isCol = root.collapsedFolders[norm] === true;
        var copy = Object.assign({}, root.collapsedFolders);
        copy[norm] = !isCol;
        root.collapsedFolders = copy;
        root.collapseVersion++;
    }

    function isItemVisible(parentFullPath, version) {
        if (!parentFullPath) return true;
        var p = parentFullPath.replace(/\\/g, "/");
        var ws = root.workspacePath ? root.workspacePath.replace(/\\/g, "/") : "";
        if (p === ws) return true;

        while (p && p.length > 0) {
            if (root.collapsedFolders[p] === true) {
                return false;
            }
            if (ws && p === ws) break;
            var slash = p.lastIndexOf("/");
            if (slash <= 0) break;
            p = p.substring(0, slash);
        }
        return true;
    }

    function populateModel(rawList, fPath) {
        fileTreeModel.clear();
        root.workspacePath = fPath ? fPath.replace(/\\/g, "/") : "";
        root.workspaceName = (fPath ? fPath.split("/").pop().split("\\").pop() : "") || "PROJECT";

        if (!rawList || rawList.length === 0) return;

        var parentLevelMap = {};
        parentLevelMap[root.workspaceName] = 0;

        var folderPathMap = {};
        folderPathMap[root.workspaceName] = root.workspacePath;

        for (var i = 0; i < rawList.length; i++) {
            var item = rawList[i];
            var pId = item.parentId || root.workspaceName;
            var parentDir = folderPathMap[pId] || root.workspacePath;
            var fullPath = (parentDir + "/" + item.name).replace(/\\/g, "/");

            if (item.type === "Folder") {
                folderPathMap[item.name] = fullPath;
            }

            var level = (parentLevelMap[pId] !== undefined) ? (parentLevelMap[pId] + 1) : 0;
            if (item.type === "Folder") {
                parentLevelMap[item.name] = level;
            }

            fileTreeModel.append({
                name: item.name,
                parentId: item.parentId,
                parentFullPath: parentDir.replace(/\\/g, "/"),
                type: item.type,
                level: level,
                fullPath: fullPath
            });
        }
    }
}
