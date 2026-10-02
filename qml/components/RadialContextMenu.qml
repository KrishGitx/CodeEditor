import QtQuick 2.15
import "."

Item {
    id: root

    property bool active: false
    property real centerX: 0
    property real centerY: 0
    property int selectedIndex: -1
    property bool hasSelectedCode: false
    property string selectedCode: ""

    signal actionSelected(string actionId)
    signal closeRequested()

    width: 220
    height: 220

    readonly property real radiusDistance: 68
    property var actions: [{
            "id": "format",
            "label": "Format",
            "icon": "sparkles",
            "angle": -90
        }, {
            "id": "run",
            "label": "Run",
            "icon": "play",
            "angle": -38.5
        }, {
            "id": "copy",
            "label": "Copy",
            "icon": "copy",
            "angle": 12.8
        }, {
            "id": "cut",
            "label": "Cut",
            "icon": "close",
            "angle": 64.2
        }, {
            "id": "paste",
            "label": "Paste",
            "icon": "file",
            "angle": 115.7
        }, {
            "id": "undo",
            "label": "Undo",
            "icon": "undo",
            "angle": 167.1
        }, {
            "id": "find",
            "label": "Find",
            "icon": "search",
            "angle": 218.5
        }]



    // Semi-transparent center hub
    Rectangle {
        id: centerHub
        anchors.centerIn: parent
        width: 54
        height: 54
        radius: 27
        color: theme ? theme.bgPopup : "#252526"
        border.color: theme ? theme.borderNormal : "#333333"
        border.width: 1

        Column {
            anchors.centerIn: parent
            spacing: 1

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.selectedIndex >= 0 ? ((root.actions[root.selectedIndex].id === "run" && root.hasSelectedCode) ? "Ask AI" : root.actions[root.selectedIndex].label) : "DGX"
                color: root.selectedIndex >= 0 ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                font.pixelSize: 10
                font.bold: true
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
            }
        }
    }

    // Radial Action Nodes
    Repeater {
        model: root.actions

        delegate: Item {
            id: actionNode

            readonly property real rad: (modelData.angle * Math.PI) / 180
            readonly property real nodeX: (root.width / 2) + Math.cos(
                rad) * root.radiusDistance - 18
            readonly property real nodeY: (root.height / 2) + Math.sin(
                rad) * root.radiusDistance - 18
            readonly property bool isHovered: index === root.selectedIndex
            readonly property bool isAskAiNode: (modelData.id === "run" && root.hasSelectedCode)

            x: nodeX
            y: nodeY
            width: 36
            height: 36

            Rectangle {
                anchors.fill: parent
                radius: 18
                color: isHovered ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgSurface : "#252526")
                border.color: isHovered ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.borderNormal : "#333333")
                border.width: 1

                scale: isHovered ? 1.15 : 1.0
                Behavior on scale {
                    NumberAnimation {
                        duration: 60
                    }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 1

                    VectorIcon {
                        anchors.horizontalCenter: parent.horizontalCenter
                        name: actionNode.isAskAiNode ? "sparkles" : modelData.icon
                        size: 11
                        color: isHovered ? "#ffffff" : (theme ? theme.textPrimary : "#cccccc")
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: actionNode.isAskAiNode ? "Ask AI" : modelData.label
                        color: isHovered ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                        font.pixelSize: 8
                        font.bold: isHovered
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onEntered: root.selectedIndex = index
                    onClicked: {
                        var actId = actionNode.isAskAiNode ? "ask_ai" : modelData.id;
                        root.actionSelected(actId);
                        root.closeRequested();
                    }
                }
            }
        }
    }

    function handleDrag(mouseX, mouseY) {
        var dx = mouseX - (root.width / 2)
        var dy = mouseY - (root.height / 2)
        var dist = Math.sqrt(dx * dx + dy * dy)

        if (dist < 18) {
            root.selectedIndex = -1
            return
        }

        var angleDeg = (Math.atan2(dy, dx) * 180) / Math.PI

        var bestIdx = 0
        var minDiff = 999

        for (var i = 0; i < root.actions.length; i++) {
            var diff = Math.abs(angleDeg - root.actions[i].angle)
            if (diff > 180)
            diff = 360 - diff
            if (diff < minDiff) {
                minDiff = diff
                bestIdx = i
            }
        }

        root.selectedIndex = bestIdx
    }

    function handleRelease(mouseX, mouseY) {
        var dx = mouseX - (root.width / 2)
        var dy = mouseY - (root.height / 2)
        var dist = Math.sqrt(dx * dx + dy * dy)

        if (dist > 22 && root.selectedIndex >= 0) {
            var selectedNode = root.actions[root.selectedIndex];
            var actId = (selectedNode.id === "run" && root.hasSelectedCode) ? "ask_ai" : selectedNode.id;
            root.actionSelected(actId);
            root.closeRequested();
            return true;
        }
        return false;
    }
}
