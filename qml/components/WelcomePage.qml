import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    signal newFileRequested()
    signal openFileRequested()
    signal openFolderRequested()
    signal openRecentRequested(string folderPath)

    property var recentProjectsList: []

    function reloadRecentProjects() {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_recent_projects) {
            root.recentProjectsList = settingsBackend.get_recent_projects();
        }
    }

    Component.onCompleted: {
        reloadRecentProjects();
    }

    Connections {
        target: typeof settingsBackend !== "undefined" ? settingsBackend : null
        ignoreUnknownSignals: true
        function onRecentProjectsChanged(list) {
            root.recentProjectsList = list || [];
        }
    }

    color: theme ? theme.bgEditor : "#1e1e1e"

    Item {
        anchors.centerIn: parent
        width: 480
        height: Math.min(parent.height - 40, 520)

        ColumnLayout {
            anchors.fill: parent
            spacing: 14

            // DGX Studio Title & Subtitle
            ColumnLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 4

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "DGX Studio"
                    color: theme ? theme.textBright : "#ffffff"
                    font.pixelSize: 24
                    font.bold: true
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Fast, intelligent, ambient code editor"
                    color: theme ? theme.textSecondary : "#858585"
                    font.pixelSize: 13
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }
            }

            Item { height: 4 }

            // Action Buttons
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 12

                // New File Action
                Rectangle {
                    width: 150
                    height: 34
                    radius: theme ? theme.radiusSm : 3
                    color: newFileMa.containsMouse ? (theme ? theme.bgSurfaceActive : "#37373d") : (theme ? theme.bgSurface : "#252526")
                    border.color: theme ? theme.borderNormal : "#333333"
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 8

                        VectorIcon {
                            name: "new-file"
                            size: 13
                            color: theme ? theme.textPrimary : "#cccccc"
                        }

                        Text {
                            text: "New File"
                            color: theme ? theme.textPrimary : "#cccccc"
                            font.pixelSize: 12
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        }
                    }

                    MouseArea {
                        id: newFileMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.newFileRequested()
                    }
                }

                // Open File Action
                Rectangle {
                    width: 150
                    height: 34
                    radius: theme ? theme.radiusSm : 3
                    color: openFileMa.containsMouse ? (theme ? theme.bgSurfaceActive : "#37373d") : (theme ? theme.bgSurface : "#252526")
                    border.color: theme ? theme.borderNormal : "#333333"
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 8

                        VectorIcon {
                            name: "file"
                            size: 13
                            color: theme ? theme.textPrimary : "#cccccc"
                        }

                        Text {
                            text: "Open File"
                            color: theme ? theme.textPrimary : "#cccccc"
                            font.pixelSize: 12
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        }
                    }

                    MouseArea {
                        id: openFileMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.openFileRequested()
                    }
                }
            }

            // Open Folder Action
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: 312
                height: 34
                radius: theme ? theme.radiusSm : 3
                color: openFolderMa.containsMouse ? (theme ? theme.bgSurfaceActive : "#37373d") : (theme ? theme.bgSurface : "#252526")
                border.color: theme ? theme.borderNormal : "#333333"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 8

                    VectorIcon {
                        name: "folder-open"
                        size: 13
                        color: theme ? theme.accent : "#0078d4"
                    }

                    Text {
                        text: "Open Folder / Workspace"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        font.bold: true
                    }
                }

                MouseArea {
                    id: openFolderMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.openFolderRequested()
                }
            }

            Item { height: 6 }

            // Divider Line
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: theme ? theme.borderSubtle : "#282828"
            }

            // Recent Section
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "Recent Workspaces"
                        color: theme ? theme.textSecondary : "#858585"
                        font.pixelSize: 12
                        font.bold: true
                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: "Clear"
                        color: theme ? theme.textMuted : "#656565"
                        font.pixelSize: 11
                        visible: root.recentProjectsList && root.recentProjectsList.length > 0
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof settingsBackend !== "undefined" && settingsBackend) {
                                    settingsBackend.clear_recent_projects();
                                }
                            }
                        }
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    Column {
                        width: parent.width
                        spacing: 2

                        Repeater {
                            model: root.recentProjectsList

                            delegate: Rectangle {
                                width: parent.width
                                height: 38
                                radius: theme ? theme.radiusSm : 3
                                color: recMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: 8

                                    VectorIcon {
                                        name: "folder-open"
                                        size: 12
                                        color: recMa.containsMouse ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                                    }

                                    Column {
                                        Layout.fillWidth: true
                                        spacing: 1

                                        Text {
                                            text: modelData.name || "Workspace"
                                            color: recMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                            font.pixelSize: 12
                                            font.bold: true
                                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                            elide: Text.ElideRight
                                            width: parent.width
                                        }

                                        Text {
                                            text: modelData.path || ""
                                            color: theme ? theme.textMuted : "#656565"
                                            font.pixelSize: 10
                                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                            elide: Text.ElideMiddle
                                            width: parent.width
                                        }
                                    }
                                }

                                MouseArea {
                                    id: recMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (typeof backend !== "undefined" && backend && backend.open_Workspace) {
                                            backend.open_Workspace(modelData.path);
                                        }
                                        root.openRecentRequested(modelData.path);
                                    }
                                }
                            }
                        }

                        Text {
                            text: "No recent workspaces opened yet"
                            color: theme ? theme.textMuted : "#656565"
                            font.pixelSize: 11
                            font.italic: true
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            visible: !root.recentProjectsList || root.recentProjectsList.length === 0
                            anchors.horizontalCenter: parent.horizontalCenter
                            topPadding: 16
                        }
                    }
                }
            }
        }
    }
}
