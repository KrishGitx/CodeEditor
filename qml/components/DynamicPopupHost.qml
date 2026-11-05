import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    anchors.fill: parent
    color: Qt.rgba(0, 0, 0, 0.70)
    visible: Boolean(popupData && popupData.id)
    z: 230
    opacity: visible ? 1.0 : 0.0

    property var popupData: (typeof extensionManager !== "undefined" && extensionManager && extensionManager.activePopup) ? extensionManager.activePopup : null
    signal closeRequested()

    Behavior on opacity { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            if (root.popupData && root.popupData.modal && root.popupData.closable !== false) {
                root.closeRequested();
            }
        }
    }

    // Modal Card Elevation Shadow
    Rectangle {
        x: dialogCard.x - 6
        y: dialogCard.y - 6
        width: dialogCard.width + 12
        height: dialogCard.height + 12
        radius: dialogCard.radius + 6
        color: "transparent"
        border.color: "#00000066"
        border.width: 6
        visible: root.visible
    }

    // Custom Modal Card
    Rectangle {
        id: dialogCard
        width: Math.min(parent.width - 40, (root.popupData && root.popupData.width) ? root.popupData.width : 460)
        height: Math.min(parent.height - 40, (root.popupData && root.popupData.height) ? root.popupData.height : 320)
        anchors.centerIn: parent
        radius: (root.popupData && root.popupData.style && root.popupData.style.border_radius !== undefined) ? root.popupData.style.border_radius : 8
        color: (root.popupData && root.popupData.style && root.popupData.style.background) ? root.popupData.style.background : (theme ? theme.bgPopup : "#252526")
        border.color: (root.popupData && root.popupData.style && root.popupData.style.accent) ? root.popupData.style.accent : (theme ? theme.borderNormal : "#333333")
        border.width: 1
        scale: root.visible ? 1.0 : 0.98

        Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }

        MouseArea {
            anchors.fill: parent
            // Absorb click so backdrop isn't clicked
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Dialog Header Bar
            Rectangle {
                Layout.fillWidth: true
                height: 38
                color: theme ? theme.bgHeader : "#181818"
                radius: dialogCard.radius

                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: dialogCard.radius
                    color: parent.color
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 10
                    spacing: 8

                    Text {
                        text: (root.popupData && root.popupData.title) ? root.popupData.title : "Dialog"
                        font.pixelSize: 13
                        font.bold: true
                        color: theme ? theme.textBright : "#ffffff"
                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    Rectangle {
                        width: 24
                        height: 24
                        radius: 3
                        visible: !root.popupData || root.popupData.closable !== false
                        color: closeBtnMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "close"
                            size: 10
                            color: theme ? theme.textSecondary : "#858585"
                        }

                        MouseArea {
                            id: closeBtnMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.closeRequested()
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: theme ? theme.borderSubtle : "#282828"
            }

            // Dialog Content Area
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                padding: 16

                DynamicComponentRenderer {
                    width: parent ? parent.width : undefined
                    componentData: root.popupData ? root.popupData.content : null
                    onActionTriggered: {
                        if (typeof extensionManager !== "undefined" && extensionManager) {
                            extensionManager.triggerUiAction("popup", (root.popupData ? root.popupData.id : ""), componentId, actionName, payload);
                        }
                    }
                }
            }
        }
    }
}

