import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property bool explorerActive: true
    property bool extensionsActive: false
    property bool settingsActive: false
    property bool musicActive: false
    property bool aiActive: false
    property bool terminalActive: false

    signal toggleExplorerRequested()
    signal searchRequested()
    signal sourceControlRequested()
    signal extensionsRequested()
    signal musicRequested()
    signal aiRequested()
    signal terminalRequested()
    signal settingsRequested()

    width: 48
    color: (typeof theme !== "undefined" && theme) ? theme.bgSurface : "#181818"

    // 1px right border divider
    Rectangle {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        width: 1
        color: (typeof theme !== "undefined" && theme) ? theme.borderSubtle : "#2b2b2b"
    }

    // Top Action Icons
    Column {
        id: topGroup
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 0

        // 1. Explorer
        Rectangle {
            width: 48
            height: 48
            color: expMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

            Rectangle {
                width: 2
                height: 24
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                color: theme ? theme.accent : "#0078d4"
                visible: root.explorerActive
            }

            VectorIcon {
                anchors.centerIn: parent
                name: "files"
                size: 20
                strokeWidth: 1.1
                color: root.explorerActive ? (theme ? theme.textBright : "#ffffff") : (expMa.containsMouse ? (theme ? theme.textPrimary : "#e0e0e0") : (theme ? theme.textSecondary : "#858585"))
            }

            ToolTip.visible: expMa.containsMouse
            ToolTip.text: "Explorer (Ctrl+Shift+E / Ctrl+B)"
            ToolTip.delay: 350

            MouseArea {
                id: expMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.toggleExplorerRequested()
            }
        }

        // 2. Extensions
        Rectangle {
            width: 48
            height: 48
            color: extMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

            Rectangle {
                width: 2
                height: 24
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                color: theme ? theme.accent : "#0078d4"
                visible: root.extensionsActive
            }

            VectorIcon {
                anchors.centerIn: parent
                name: "puzzle"
                size: 20
                strokeWidth: 1.1
                color: root.extensionsActive ? (theme ? theme.textBright : "#ffffff") : (extMa.containsMouse ? (theme ? theme.textPrimary : "#e0e0e0") : (theme ? theme.textSecondary : "#858585"))
            }

            ToolTip.visible: extMa.containsMouse
            ToolTip.text: "Extensions (Ctrl+Shift+X)"
            ToolTip.delay: 350

            MouseArea {
                id: extMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.extensionsRequested()
            }
        }

        // 5. AI Workspace
        Rectangle {
            width: 48
            height: 48
            color: aiMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

            Rectangle {
                width: 2
                height: 24
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                color: theme ? theme.accent : "#0078d4"
                visible: root.aiActive
            }

            VectorIcon {
                anchors.centerIn: parent
                name: "sparkles"
                size: 20
                strokeWidth: 1.1
                color: root.aiActive ? (theme ? theme.textBright : "#ffffff") : (aiMa.containsMouse ? (theme ? theme.textPrimary : "#e0e0e0") : (theme ? theme.textSecondary : "#858585"))
            }

            ToolTip.visible: aiMa.containsMouse
            ToolTip.text: "Pod AI Workspace"
            ToolTip.delay: 350

            MouseArea {
                id: aiMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.aiRequested()
            }
        }

        // 6. Music Studio
        Rectangle {
            width: 48
            height: 48
            color: musicMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

            Rectangle {
                width: 2
                height: 24
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                color: theme ? theme.accent : "#0078d4"
                visible: root.musicActive
            }

            VectorIcon {
                anchors.centerIn: parent
                name: "vinyl"
                size: 20
                strokeWidth: 1.1
                color: root.musicActive ? (theme ? theme.textBright : "#ffffff") : (musicMa.containsMouse ? (theme ? theme.textPrimary : "#e0e0e0") : (theme ? theme.textSecondary : "#858585"))
            }

            ToolTip.visible: musicMa.containsMouse
            ToolTip.text: "Pod Music Player"
            ToolTip.delay: 350

            MouseArea {
                id: musicMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.musicRequested()
            }
        }
    }

    // Bottom Pinned Action Icons
    Column {
        id: bottomGroup
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 0

        // Settings
        Rectangle {
            width: 48
            height: 48
            color: setMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

            Rectangle {
                width: 2
                height: 24
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                color: theme ? theme.accent : "#0078d4"
                visible: root.settingsActive
            }

            VectorIcon {
                anchors.centerIn: parent
                name: "settings"
                size: 20
                strokeWidth: 1.1
                color: root.settingsActive ? (theme ? theme.textBright : "#ffffff") : (setMa.containsMouse ? (theme ? theme.textPrimary : "#e0e0e0") : (theme ? theme.textSecondary : "#858585"))
            }

            ToolTip.visible: setMa.containsMouse
            ToolTip.text: "Settings (Ctrl+,)"
            ToolTip.delay: 350

            MouseArea {
                id: setMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.settingsRequested()
            }
        }
    }
}

