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

    signal actionSelected(string actionId, string customAction)
    signal closeRequested()

    width: 220
    height: 220

    readonly property real radiusDistance: 68
    property var actions: []

    function loadActions() {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_radial_menu_config) {
            var cfg = settingsBackend.get_radial_menu_config() || [];
            var enabledList = [];
            for (var i = 0; i < cfg.length; i++) {
                if (cfg[i].enabled !== false) {
                    enabledList.push(cfg[i]);
                }
            }
            if (enabledList.length > 0) {
                var total = enabledList.length;
                var res = [];
                for (var j = 0; j < total; j++) {
                    var item = enabledList[j];
                    var angle = (j / total) * 360.0 - 90.0;
                    res.push({
                        id: item.id,
                        label: item.label,
                        icon: item.icon || "file",
                        angle: angle,
                        action: item.action || "",
                        action_type: item.action_type || "",
                        custom: item.custom || false
                    });
                }
                root.actions = res;
                return;
            }
        }

        // Fallback default actions
        root.actions = [
            { "id": "format", "label": "Formatter", "icon": "sparkles", "angle": -90 },
            { "id": "run", "label": "Run", "icon": "play", "angle": -38.5 },
            { "id": "copy", "label": "Copy", "icon": "copy", "angle": 12.8 },
            { "id": "cut", "label": "Cut", "icon": "close", "angle": 64.2 },
            { "id": "paste", "label": "Paste", "icon": "file", "angle": 115.7 },
            { "id": "undo", "label": "Undo", "icon": "undo", "angle": 167.1 },
            { "id": "find", "label": "Find", "icon": "search", "angle": 218.5 }
        ];
    }

    Component.onCompleted: root.loadActions()
    onVisibleChanged: {
        if (visible) root.loadActions();
    }
    onActiveChanged: {
        if (active) root.loadActions();
    }

    Connections {
        target: (typeof settingsBackend !== "undefined" && settingsBackend) ? settingsBackend : null
        function onSettingChanged(key, value) {
            if (key === "radial_menu_items" || key === "radial_custom_actions") {
                root.loadActions();
            }
        }
    }

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
                text: (root.selectedIndex >= 0 && root.selectedIndex < root.actions.length) ? ((root.actions[root.selectedIndex].id === "run" && root.hasSelectedCode) ? "Ask AI" : root.actions[root.selectedIndex].label) : "DGX"
                color: root.selectedIndex >= 0 ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                font.pixelSize: 10
                font.bold: true
                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                elide: Text.ElideRight
                width: 46
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    // Radial Action Nodes
    Repeater {
        model: root.actions

        delegate: Item {
            id: actionNode

            readonly property real rad: (modelData.angle * Math.PI) / 180
            readonly property real nodeX: (root.width / 2) + Math.cos(rad) * root.radiusDistance - 19
            readonly property real nodeY: (root.height / 2) + Math.sin(rad) * root.radiusDistance - 19
            readonly property bool isHovered: index === root.selectedIndex
            readonly property bool isAskAiNode: (modelData.id === "run" && root.hasSelectedCode)

            x: nodeX
            y: nodeY
            width: 38
            height: 38

            Rectangle {
                anchors.fill: parent
                radius: 19
                color: isHovered ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgSurface : "#252526")
                border.color: isHovered ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.borderNormal : "#333333")
                border.width: 1

                scale: isHovered ? 1.12 : 1.0
                Behavior on scale {
                    NumberAnimation {
                        duration: 60
                    }
                }

                Column {
                    anchors.centerIn: parent
                    width: parent.width - 4
                    spacing: 1

                    VectorIcon {
                        anchors.horizontalCenter: parent.horizontalCenter
                        name: actionNode.isAskAiNode ? "sparkles" : (modelData.icon || "file")
                        size: 11
                        color: isHovered ? "#ffffff" : (theme ? theme.textPrimary : "#cccccc")
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: actionNode.isAskAiNode ? "Ask AI" : (modelData.label || "")
                        color: isHovered ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                        font.pixelSize: 8
                        font.bold: isHovered
                        elide: Text.ElideRight
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onEntered: root.selectedIndex = index
                    onClicked: {
                        var actId = actionNode.isAskAiNode ? "ask_ai" : modelData.id;
                        root.actionSelected(actId, modelData.action || "");
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

        if (dist > 22 && root.selectedIndex >= 0 && root.selectedIndex < root.actions.length) {
            var selectedNode = root.actions[root.selectedIndex];
            var actId = (selectedNode.id === "run" && root.hasSelectedCode) ? "ask_ai" : selectedNode.id;
            root.actionSelected(actId, selectedNode.action || "");
            root.closeRequested();
            return true;
        }
        return false;
    }
}
