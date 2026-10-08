import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: toastRoot

    property string messageText: ""
    property string messageType: "info" // "info", "warning", "error", "success"
    property string sourceTitle: ""
    property int autoDismissDuration: 5000

    property string actionButtonText: ""
    property var actionButtonCallback: null
    property string secondaryActionText: ""
    property var secondaryActionCallback: null

    visible: opacity > 0.01
    opacity: 0.0
    width: 360
    implicitHeight: mainLayout.implicitHeight + 20
    radius: 4
    color: (typeof theme !== "undefined" && theme) ? theme.bgPanel : "#252526"
    border.color: (typeof theme !== "undefined" && theme) ? theme.borderSubtle : "#3c3c3c"
    border.width: 1

    Behavior on opacity {
        NumberAnimation { duration: 180; easing.type: Easing.OutQuad }
    }
    Behavior on y {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    // Left accent strip
    Rectangle {
        id: accentStrip
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 3
        radius: 2
        color: {
            if (toastRoot.messageType === "error") return "#f14c4c";
            if (toastRoot.messageType === "warning") return "#cca700";
            if (toastRoot.messageType === "success") return "#73c991";
            return (typeof theme !== "undefined" && theme) ? theme.accent : "#0078d4";
        }
    }

    Timer {
        id: dismissTimer
        interval: toastRoot.autoDismissDuration
        repeat: false
        onTriggered: {
            toastRoot.hide();
        }
    }

    MouseArea {
        id: hoverArea
        anchors.fill: parent
        hoverEnabled: true
        onEntered: {
            if (dismissTimer.running) {
                dismissTimer.stop();
            }
        }
        onExited: {
            if (toastRoot.opacity > 0) {
                dismissTimer.interval = toastRoot.actionButtonText !== "" ? 6000 : 2500;
                dismissTimer.restart();
            }
        }
    }

    ColumnLayout {
        id: mainLayout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 14
        anchors.rightMargin: 10
        anchors.topMargin: 10
        spacing: 6

        // Header: Icon + Title + Close Button
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // Status indicator icon
            Rectangle {
                width: 14
                height: 14
                radius: 7
                color: accentStrip.color
                Layout.alignment: Qt.AlignVCenter

                Text {
                    anchors.centerIn: parent
                    text: {
                        if (toastRoot.messageType === "error") return "✕";
                        if (toastRoot.messageType === "warning") return "!";
                        if (toastRoot.messageType === "success") return "✓";
                        return "i";
                    }
                    font.pixelSize: 9
                    font.bold: true
                    color: "#ffffff"
                }
            }

            Text {
                text: toastRoot.sourceTitle || (toastRoot.messageType.toUpperCase())
                color: (typeof theme !== "undefined" && theme) ? theme.textSecondary : "#a0a0a0"
                font.pixelSize: 11
                font.bold: true
                font.letterSpacing: 0.5
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            // Close button
            Rectangle {
                width: 18
                height: 18
                radius: 3
                color: closeMa.containsMouse ? (typeof theme !== "undefined" && theme ? theme.bgHover : "#383838") : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    font.pixelSize: 10
                    color: closeMa.containsMouse ? "#ffffff" : ((typeof theme !== "undefined" && theme) ? theme.textMuted : "#858585")
                }

                MouseArea {
                    id: closeMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: toastRoot.hide()
                }
            }
        }

        // Message Body
        Text {
            id: bodyText
            Layout.fillWidth: true
            text: toastRoot.messageText
            color: (typeof theme !== "undefined" && theme) ? theme.textBright : "#e0e0e0"
            font.pixelSize: 12
            wrapMode: Text.Wrap
            lineHeight: 1.2
            maximumLineCount: 6
            elide: Text.ElideRight
        }

        // Action Buttons Row (e.g. [ Smart Install ] [ Close ])
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 4
            Layout.bottomMargin: 2
            spacing: 8
            visible: toastRoot.actionButtonText !== "" || toastRoot.secondaryActionText !== ""

            Item { Layout.fillWidth: true }

            // Secondary Action (e.g. Close)
            Rectangle {
                visible: toastRoot.secondaryActionText !== ""
                width: secText.implicitWidth + 16
                height: 24
                radius: 3
                color: secMa.containsMouse ? (typeof theme !== "undefined" && theme ? theme.bgHover : "#3c3c3c") : (typeof theme !== "undefined" && theme ? theme.bgSurface : "#2d2d2d")
                border.color: typeof theme !== "undefined" && theme ? theme.borderSubtle : "#444444"
                border.width: 1

                Text {
                    id: secText
                    anchors.centerIn: parent
                    text: toastRoot.secondaryActionText
                    color: typeof theme !== "undefined" && theme ? theme.textSecondary : "#cccccc"
                    font.pixelSize: 11
                }

                MouseArea {
                    id: secMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (toastRoot.secondaryActionCallback) {
                            try { toastRoot.secondaryActionCallback(); } catch (e) {}
                        }
                        toastRoot.hide();
                    }
                }
            }

            // Primary Action (e.g. Smart Install)
            Rectangle {
                visible: toastRoot.actionButtonText !== ""
                width: actRow.implicitWidth + 18
                height: 24
                radius: 3
                color: actMa.containsMouse ? (typeof theme !== "undefined" && theme ? theme.accentHover : "#006cbd") : (typeof theme !== "undefined" && theme ? theme.accent : "#0078d4")

                Row {
                    id: actRow
                    anchors.centerIn: parent
                    spacing: 4

                    VectorIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: "download"
                        size: 10
                        color: "#ffffff"
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: toastRoot.actionButtonText
                        color: "#ffffff"
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                MouseArea {
                    id: actMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        var cb = toastRoot.actionButtonCallback;
                        toastRoot.hide();
                        if (cb) {
                            try { cb(); } catch (e) { console.log("[NotificationToast] Action error:", e); }
                        }
                    }
                }
            }
        }
    }

    function show(msg, type, title, duration, actionText, actionCb, secActionText, secActionCb) {
        toastRoot.messageText = msg || "";
        toastRoot.messageType = type || "info";
        toastRoot.sourceTitle = title || "";
        toastRoot.actionButtonText = actionText || "";
        toastRoot.actionButtonCallback = (typeof actionCb === "function") ? actionCb : null;
        toastRoot.secondaryActionText = secActionText || "";
        toastRoot.secondaryActionCallback = (typeof secActionCb === "function") ? secActionCb : null;

        toastRoot.autoDismissDuration = duration > 0 ? duration : (actionText ? 10000 : (type === "error" ? 7000 : 5000));
        toastRoot.opacity = 1.0;
        dismissTimer.interval = toastRoot.autoDismissDuration;
        dismissTimer.restart();
    }

    function hide() {
        dismissTimer.stop();
        toastRoot.opacity = 0.0;
        toastRoot.actionButtonText = "";
        toastRoot.actionButtonCallback = null;
        toastRoot.secondaryActionText = "";
        toastRoot.secondaryActionCallback = null;
    }
}

