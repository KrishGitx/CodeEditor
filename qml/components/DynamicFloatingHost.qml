import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    clip: true

    Repeater {
        model: (typeof extensionManager !== "undefined" && extensionManager && extensionManager.floatingWidgets) ? extensionManager.floatingWidgets : []

        delegate: Item {
            id: widgetContainer
            x: modelData.x || 600
            y: modelData.y || 300
            width: Math.max(40, (modelData.width || 120))
            height: Math.max(40, (modelData.height || 120))
            visible: modelData.visible !== false
            opacity: modelData.opacity !== undefined ? modelData.opacity : 1.0
            z: modelData.keep_on_top ? 50 : 20

            // Animated Speech Bubble (e.g. for cat mascot / speech tips)
            Rectangle {
                id: speechBubble
                anchors.bottom: widgetContent.top
                anchors.bottomMargin: 8
                anchors.horizontalCenter: widgetContent.horizontalCenter
                width: Math.min(240, Math.max(60, bubbleText.implicitWidth + 20))
                height: bubbleText.implicitHeight + 14
                radius: 8
                color: theme ? theme.bgPopup : "#252526"
                border.color: theme ? theme.accent : "#0078d4"
                border.width: 1
                visible: Boolean(modelData.bubble_visible && modelData.bubble_text && modelData.bubble_text.length > 0)
                opacity: visible ? 1.0 : 0.0

                Behavior on opacity { NumberAnimation { duration: 180 } }

                Text {
                    id: bubbleText
                    anchors.centerIn: parent
                    width: parent.width - 16
                    text: modelData.bubble_text || ""
                    font.pixelSize: 11
                    color: theme ? theme.textBright : "#ffffff"
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                // Bubble Tail pointing down
                Rectangle {
                    anchors.top: parent.bottom
                    anchors.topMargin: -4
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 8
                    height: 8
                    rotation: 45
                    color: parent.color
                    border.color: parent.border.color
                    border.width: 1
                    z: -1
                }
            }

            // Main Widget Body / Content
            Item {
                id: widgetContent
                anchors.fill: parent

                DynamicComponentRenderer {
                    anchors.fill: parent
                    componentData: modelData.content
                    onActionTriggered: {
                        if (typeof extensionManager !== "undefined" && extensionManager) {
                            extensionManager.triggerUiAction("floating", modelData.id, componentId, actionName, payload);
                        }
                    }
                }

                MouseArea {
                    id: dragArea
                    anchors.fill: parent
                    enabled: modelData.draggable !== false
                    cursorShape: enabled ? Qt.SizeAllCursor : Qt.PointingHandCursor
                    drag.target: widgetContainer
                    drag.minimumX: 0
                    drag.maximumX: Math.max(0, root.width - widgetContainer.width)
                    drag.minimumY: 0
                    drag.maximumY: Math.max(0, root.height - widgetContainer.height)

                    onReleased: {
                        if (typeof extensionManager !== "undefined" && extensionManager) {
                            extensionManager.updateFloatingPosition(modelData.id, widgetContainer.x, widgetContainer.y);
                            extensionManager.triggerUiAction("floating", modelData.id, "", "drag_end", { x: widgetContainer.x, y: widgetContainer.y });
                        }
                    }

                    onClicked: {
                        if (typeof extensionManager !== "undefined" && extensionManager) {
                            extensionManager.triggerUiAction("floating", modelData.id, "", "click", null);
                        }
                    }
                }
            }

            // Connection to animate widget dynamically
            Connections {
                target: (typeof extensionManager !== "undefined" && extensionManager) ? extensionManager : null
                function onWidgetAnimationRequested(targetId, propsJson, durationMs, easingStr) {
                    if (targetId === modelData.id) {
                        try {
                            var p = JSON.parse(propsJson);
                            if (p.x !== undefined) widgetContainer.x = p.x;
                            if (p.y !== undefined) widgetContainer.y = p.y;
                            if (p.opacity !== undefined) widgetContainer.opacity = p.opacity;
                        } catch(e) {}
                    }
                }
            }

            Behavior on x { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
            Behavior on y { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
        }
    }
}

