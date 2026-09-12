import QtQuick 2.15

Item {
    id: radialRoot
    width: 280
    height: 280
    visible: opacity > 0
    opacity: 0
    scale: opacity

    signal actionTriggered(string action)

    property var items: [
        { id: "save",     label: "Save",     icon: "💾", angle: -90, shortcut: "1" },
        { id: "find",     label: "Find",     icon: "🔍", angle: -45, shortcut: "2" },
        { id: "run",      label: "Run",      icon: "⚡", angle: 0,   shortcut: "3" },
        { id: "ai",       label: "AI Chat",  icon: "🤖", angle: 45,  shortcut: "4" },
        { id: "music",    label: "Music",    icon: "🎵", angle: 90,  shortcut: "5" },
        { id: "zen",      label: "Zen Mode", icon: "🧘", angle: 135, shortcut: "6" },
        { id: "settings", label: "Settings", icon: "⚙️", angle: 180, shortcut: "7" },
        { id: "undo",     label: "Undo",     icon: "↩️", angle: -135, shortcut: "8" }
    ]

    Behavior on opacity {
        NumberAnimation { duration: theme.animFast; easing.type: Easing.OutCubic }
    }
    Behavior on scale {
        NumberAnimation { duration: theme.animFast; easing.type: Easing.OutBack }
    }

    // Backdrop click dismisser
    MouseArea {
        anchors.fill: parent
        anchors.margins: -1200
        onClicked: radialRoot.close()
    }

    // Radial Menu Background Circle
    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: theme.bgCard
        border.color: theme.borderSubtle
        border.width: 1

        // Center hub
        Rectangle {
            width: 56
            height: 56
            radius: 28
            anchors.centerIn: parent
            color: theme.bgActive
            border.color: theme.accentColor
            border.width: 1.5

            Column {
                anchors.centerIn: parent
                spacing: 1

                Text {
                    text: "DGX"
                    color: theme.accentColor
                    font.pixelSize: 11
                    font.bold: true
                    font.family: theme.uiFont
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Text {
                    text: "MENU"
                    color: theme.textMuted
                    font.pixelSize: 8
                    font.bold: true
                    font.family: theme.uiFont
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }

        // Radial items repeater
        Repeater {
            model: radialRoot.items

            delegate: Item {
                id: itemNode
                width: 48
                height: 48

                // Calculate radial coordinate (radius = 95)
                readonly property real rad: (modelData.angle * Math.PI) / 180
                readonly property real cx: radialRoot.width / 2
                readonly property real cy: radialRoot.height / 2
                readonly property real r: 95

                x: cx + r * Math.cos(rad) - (width / 2)
                y: cy + r * Math.sin(rad) - (height / 2)

                Rectangle {
                    anchors.fill: parent
                    radius: width / 2
                    color: nodeMouse.containsMouse ? theme.accentColor : theme.bgHover
                    border.color: theme.borderSubtle
                    border.width: 1

                    Behavior on color { ColorAnimation { duration: theme.animFast } }

                    Column {
                        anchors.centerIn: parent
                        spacing: 2

                        Text {
                            text: modelData.icon
                            font.pixelSize: 13
                            anchors.horizontalCenter: parent.horizontalCenter
                        }

                        Text {
                            text: modelData.label
                            color: nodeMouse.containsMouse ? "#ffffff" : theme.textPrimary
                            font.pixelSize: 8
                            font.bold: true
                            font.family: theme.uiFont
                            anchors.horizontalCenter: parent.horizontalCenter
                        }
                    }

                    MouseArea {
                        id: nodeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            radialRoot.actionTriggered(modelData.id)
                            radialRoot.close()
                        }
                    }
                }
            }
        }
    }

    // Keyboard Shortcuts (1-8, Esc)
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Escape) {
            radialRoot.close()
            event.accepted = true
            return
        }
        var num = parseInt(event.text)
        if (num >= 1 && num <= radialRoot.items.length) {
            var actionId = radialRoot.items[num - 1].id
            radialRoot.actionTriggered(actionId)
            radialRoot.close()
            event.accepted = true
        }
    }

    function openAt(posX, posY) {
        x = Math.max(20, Math.min(posX - (width / 2), mainWindow.width - width - 20))
        y = Math.max(50, Math.min(posY - (height / 2), mainWindow.height - height - 50))
        opacity = 1
        forceActiveFocus()
    }

    function close() {
        opacity = 0
    }
}
