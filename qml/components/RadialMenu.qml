import QtQuick 2.15
import QtQuick.Controls 2.15
import "."

Item {
    id: root

    property bool isOpen: false

    signal actionTriggered(string action)
    signal closeRequested()

    width: 340
    height: 340

    readonly property real radiusDistance: 110

    property var menuItems: [
        { id: "save", label: "Save", icon: "save", shortcut: "Ctrl+S" },
        { id: "undo", label: "Undo", icon: "undo", shortcut: "Ctrl+Z" },
        { id: "redo", label: "Redo", icon: "redo", shortcut: "Ctrl+Y" },
        { id: "find", label: "Find", icon: "search", shortcut: "Ctrl+F" },
        { id: "run", label: "Run File", icon: "play", shortcut: "F5" },
        { id: "ai", label: "AI Copilot", icon: "sparkles", shortcut: "AI Panel" },
        { id: "music", label: "Music", icon: "music", shortcut: "Music Panel" },
        { id: "zen", label: "Zen Mode", icon: "zen", shortcut: "Ctrl+Shift+Z" },
        { id: "terminal", label: "Terminal", icon: "terminal", shortcut: "Ctrl+`" },
        { id: "settings", label: "Settings", icon: "settings", shortcut: "Ctrl+," }
    ]

    // Background Dimming & Backdrop
    Rectangle {
        id: centerDisc
        anchors.centerIn: parent
        width: 100
        height: 100
        radius: 50
        color: theme ? theme.bgPopup : "#151824"
        border.color: theme ? theme.borderNormal : "#2a3145"
        border.width: 2

        Column {
            anchors.centerIn: parent
            spacing: 2

            VectorIcon {
                anchors.horizontalCenter: parent.horizontalCenter
                name: "zen"
                size: 20
                color: theme ? theme.accent : "#3b82f6"
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "DGX"
                color: theme ? theme.textPrimary : "#f1f5f9"
                font.pixelSize: 11
                font.bold: true
                font.letterSpacing: 1
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.closeRequested()
        }
    }

    // Radial Menu Action Nodes
    Repeater {
        model: root.menuItems

        delegate: Item {
            id: radialItem

            // Angle calculation evenly spaced in circle
            readonly property real angle: (index / root.menuItems.length) * (2 * Math.PI) - (Math.PI / 2)
            readonly property real itemX: (root.width / 2) + Math.cos(angle) * root.radiusDistance - (itemBubble.width / 2)
            readonly property real itemY: (root.height / 2) + Math.sin(angle) * root.radiusDistance - (itemBubble.height / 2)

            x: itemX
            y: itemY
            width: itemBubble.width
            height: itemBubble.height

            Rectangle {
                id: itemBubble
                width: 52
                height: 52
                radius: 26
                color: itemMa.containsMouse ? (theme ? theme.accent : "#3b82f6") : (theme ? theme.bgSurface : "#181c28")
                border.color: itemMa.containsMouse ? (theme ? theme.borderGlow : "#60a5fa") : (theme ? theme.borderNormal : "#2a3145")
                border.width: 1

                scale: itemMa.containsMouse ? 1.12 : 1.0
                Behavior on scale {
                    NumberAnimation { duration: theme ? theme.animationDurationFast : 120 }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 2

                    VectorIcon {
                        anchors.horizontalCenter: parent.horizontalCenter
                        name: modelData.icon || "file"
                        size: 15
                        color: itemMa.containsMouse ? "#ffffff" : (theme ? theme.textPrimary : "#f1f5f9")
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: modelData.label || ""
                        color: itemMa.containsMouse ? "#ffffff" : (theme ? theme.textSecondary : "#94a3b8")
                        font.pixelSize: 9
                        font.bold: itemMa.containsMouse
                    }
                }

                ToolTip.visible: itemMa.containsMouse
                ToolTip.text: modelData.label + " (" + modelData.shortcut + ")"

                MouseArea {
                    id: itemMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.actionTriggered(modelData.id);
                        root.closeRequested();
                    }
                }
            }
        }
    }
}
