import QtQuick 2.15
import QtQuick.Layouts 1.3

Row {
    id: playbackControlsRoot
    spacing: 10

    property string playbackState: "stopped" // "playing", "paused", "stopped"

    signal playPauseClicked()
    signal stopClicked()
    signal prevClicked()
    signal nextClicked()

    // Previous Button
    Rectangle {
        width: 28
        height: 28
        radius: 14
        color: prevMouse.containsMouse ? theme.bgHover : "transparent"
        anchors.verticalCenter: parent.verticalCenter

        Text {
            text: "⏮"
            color: theme.textSecondary
            font.pixelSize: 11
            anchors.centerIn: parent
        }

        MouseArea {
            id: prevMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: playbackControlsRoot.prevClicked()
        }
    }

    // Play / Pause Toggle Button
    Rectangle {
        width: 36
        height: 36
        radius: 18
        color: playMouse.containsMouse ? theme.accentColor : theme.bgCard
        border.color: theme.accentColor
        border.width: 1
        anchors.verticalCenter: parent.verticalCenter

        Text {
            text: playbackControlsRoot.playbackState === "playing" ? "⏸" : "▶"
            color: playMouse.containsMouse ? "#ffffff" : theme.accentColor
            font.pixelSize: 13
            anchors.centerIn: parent
        }

        MouseArea {
            id: playMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: playbackControlsRoot.playPauseClicked()
        }
    }

    // Stop Button
    Rectangle {
        width: 28
        height: 28
        radius: 14
        color: stopMouse.containsMouse ? theme.bgHover : "transparent"
        anchors.verticalCenter: parent.verticalCenter

        Text {
            text: "⏹"
            color: theme.textSecondary
            font.pixelSize: 11
            anchors.centerIn: parent
        }

        MouseArea {
            id: stopMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: playbackControlsRoot.stopClicked()
        }
    }

    // Next Button
    Rectangle {
        width: 28
        height: 28
        radius: 14
        color: nextMouse.containsMouse ? theme.bgHover : "transparent"
        anchors.verticalCenter: parent.verticalCenter

        Text {
            text: "⏭"
            color: theme.textSecondary
            font.pixelSize: 11
            anchors.centerIn: parent
        }

        MouseArea {
            id: nextMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: playbackControlsRoot.nextClicked()
        }
    }
}
