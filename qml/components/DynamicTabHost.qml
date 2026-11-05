import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: theme ? theme.bgEditor : "#1e1e1e"

    property var tabData: null
    signal closeRequested()

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Custom Tab Header
        Rectangle {
            Layout.fillWidth: true
            height: 38
            color: theme ? theme.bgHeader : "#181818"
            border.color: theme ? theme.borderSubtle : "#282828"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 12
                spacing: 8

                VectorIcon {
                    name: (root.tabData && root.tabData.icon) ? root.tabData.icon : "sparkles"
                    size: 14
                    color: theme ? theme.accent : "#0078d4"
                }

                Text {
                    text: (root.tabData && root.tabData.title) ? root.tabData.title : "Extension View"
                    font.pixelSize: 13
                    font.bold: true
                    color: theme ? theme.textBright : "#ffffff"
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                    Layout.fillWidth: true
                }

                Rectangle {
                    width: 24
                    height: 24
                    radius: 3
                    visible: !root.tabData || root.tabData.closable !== false
                    color: tabCloseMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "close"
                        size: 10
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    MouseArea {
                        id: tabCloseMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.closeRequested()
                    }
                }
            }
        }

        // Tab Content Area
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            padding: 24

            DynamicComponentRenderer {
                width: Math.max(380, parent ? parent.width - 48 : 400)
                componentData: root.tabData ? root.tabData.content : null
                onActionTriggered: {
                    if (typeof extensionManager !== "undefined" && extensionManager && root.tabData) {
                        extensionManager.triggerUiAction("tab", root.tabData.id, componentId, actionName, payload);
                    }
                }
            }
        }
    }
}

