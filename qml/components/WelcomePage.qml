import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    signal newFileRequested()
    signal openFileRequested()
    signal openFolderRequested()

    color: theme ? theme.bgEditor : "#1e1e1e"

    Item {
        anchors.centerIn: parent
        width: 440
        height: 380

        ColumnLayout {
            anchors.fill: parent
            spacing: 16

            // DGX Studio Title & Subtitle
            ColumnLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 6

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "DGX Studio"
                    color: theme ? theme.textPrimary : "#cccccc"
                    font.pixelSize: 22
                    font.bold: true
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Start coding with DGX Studio"
                    color: theme ? theme.textSecondary : "#858585"
                    font.pixelSize: 13
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }
            }

            Item { height: 8 }

            // Action Buttons
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 12

                // New File Action
                Rectangle {
                    width: 140
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
                    width: 140
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
                width: 292
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
                        color: theme ? theme.textPrimary : "#cccccc"
                    }

                    Text {
                        text: "Open Folder"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
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

            Item { height: 12 }

            // Divider Line
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: theme ? theme.borderSubtle : "#282828"
            }

            // Recent Section
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Text {
                    text: "Recent"
                    color: theme ? theme.textSecondary : "#858585"
                    font.pixelSize: 12
                    font.bold: true
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                Text {
                    text: "No recent projects"
                    color: theme ? theme.textMuted : "#656565"
                    font.pixelSize: 11
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }
            }
        }
    }
}
