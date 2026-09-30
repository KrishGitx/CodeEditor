import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property var tabModel: null
    property int activeIndex: 0

    signal tabSelected(int index)
    signal tabClosed(int index)
    signal newTabRequested()

    height: 30
    color: theme ? theme.bgHeader : "#181818"

    // Single bottom border line
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: theme ? theme.borderSubtle : "#282828"
    }

    ScrollView {
        id: tabScrollView
        anchors.left: parent.left
        anchors.right: newTabBtn.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        ScrollBar.horizontal.policy: ScrollBar.AsNeeded
        ScrollBar.vertical.policy: ScrollBar.AlwaysOff
        clip: true

        Row {
            id: tabsRow
            height: parent.height
            spacing: 1

            Repeater {
                model: root.tabModel

                delegate: Rectangle {
                    id: tabItem
                    height: root.height - 1
                    width: Math.min(180, Math.max(90, tabTitleText.contentWidth + 40))
                    color: index === root.activeIndex ? (theme ? theme.bgEditor : "#1e1e1e") : (tabMa.containsMouse ? (theme ? theme.bgSurface : "#252526") : (theme ? theme.bgHeader : "#181818"))

                    // Right tab divider line
                    Rectangle {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: 1
                        color: theme ? theme.borderSubtle : "#282828"
                    }

                    // Top active line
                    Rectangle {
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 2
                        color: theme ? theme.accent : "#0078d4"
                        visible: index === root.activeIndex
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 6
                        spacing: 6

                        // File Icon
                        VectorIcon {
                            name: (model.isWhiteboard || model.languageId === "whiteboard") ? "board" : ((model.isWebPreview || model.languageId === "webpreview") ? "sparkles" : "file")
                            size: 11
                            color: index === root.activeIndex ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                        }

                        // Tab Title
                        Text {
                            id: tabTitleText
                            text: (model.title || "Untitled") + (model.isDirty ? " •" : "")
                            color: index === root.activeIndex ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                            font.pixelSize: 12
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        // Close Tab Button
                        Rectangle {
                            width: 16
                            height: 16
                            radius: 2
                            color: closeTabMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                            VectorIcon {
                                anchors.centerIn: parent
                                name: "close"
                                size: 8
                                color: closeTabMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                            }

                            MouseArea {
                                id: closeTabMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.tabClosed(index);
                                }
                            }
                        }
                    }

                    MouseArea {
                        id: tabMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                        z: -1

                        onClicked: function(mouse) {
                            if (mouse.button === Qt.LeftButton) {
                                root.tabSelected(index);
                            } else if (mouse.button === Qt.MiddleButton) {
                                root.tabClosed(index);
                            }
                        }
                    }
                }
            }
        }
    }

    // New Tab Button (+)
    Rectangle {
        id: newTabBtn
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.rightMargin: 4
        width: 24
        height: 24
        radius: 2
        color: newTabMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

        VectorIcon {
            anchors.centerIn: parent
            name: "new-file"
            size: 11
            color: theme ? theme.textSecondary : "#858585"
        }

        MouseArea {
            id: newTabMa
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.newTabRequested()
        }
    }
}
