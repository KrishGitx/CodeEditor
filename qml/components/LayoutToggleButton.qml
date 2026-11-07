import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    property string panel: "left" // "left" | "bottom" | "right"
    property bool active: false
    property string toolTipText: ""
    signal clicked()

    width: 28
    height: 24
    radius: (typeof theme !== "undefined" && theme) ? theme.radiusSm : 3
    color: ma.containsMouse ? ((typeof theme !== "undefined" && theme) ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

    Canvas {
        id: iconCanvas
        anchors.centerIn: parent
        width: 16
        height: 13
        renderTarget: Canvas.Image

        Connections {
            target: root
            function onActiveChanged() { iconCanvas.requestPaint(); }
        }

        Connections {
            target: ma
            function onContainsMouseChanged() { iconCanvas.requestPaint(); }
        }

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.clearRect(0, 0, width, height);

            var w = width;
            var h = height;
            var r = 1.8;
            var strokeCol = ma.containsMouse ? (theme ? theme.textBright : "#ffffff") : (root.active ? (theme ? theme.textPrimary : "#cccccc") : (theme ? theme.textMuted : "#858585"));
            var fillCol = ma.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#e0e0e0");

            ctx.lineWidth = 0.9;
            ctx.strokeStyle = strokeCol;
            ctx.fillStyle = fillCol;

            // 1. Draw outer rounded rectangle with crisp thin stroke
            ctx.beginPath();
            ctx.moveTo(r, 0.5);
            ctx.lineTo(w - r, 0.5);
            ctx.arcTo(w - 0.5, 0.5, w - 0.5, r, r);
            ctx.lineTo(w - 0.5, h - r);
            ctx.arcTo(w - 0.5, h - 0.5, w - r, h - 0.5, r);
            ctx.lineTo(r, h - 0.5);
            ctx.arcTo(0.5, h - 0.5, 0.5, h - r, r);
            ctx.lineTo(0.5, r);
            ctx.arcTo(0.5, 0.5, r, 0.5, r);
            ctx.closePath();
            ctx.stroke();

            // 2. Draw partition line and optional filled region
            if (root.panel === "left") {
                var divX = 4.8;
                if (root.active) {
                    ctx.beginPath();
                    ctx.moveTo(divX, 0.5);
                    ctx.lineTo(r, 0.5);
                    ctx.arcTo(0.5, 0.5, 0.5, r, r);
                    ctx.lineTo(0.5, h - r);
                    ctx.arcTo(0.5, h - 0.5, r, h - 0.5, r);
                    ctx.lineTo(divX, h - 0.5);
                    ctx.closePath();
                    ctx.fill();
                }
                ctx.beginPath();
                ctx.moveTo(divX, 0.5);
                ctx.lineTo(divX, h - 0.5);
                ctx.stroke();
            } else if (root.panel === "bottom") {
                var divY = 8.5;
                if (root.active) {
                    ctx.beginPath();
                    ctx.moveTo(0.5, divY);
                    ctx.lineTo(0.5, h - r);
                    ctx.arcTo(0.5, h - 0.5, r, h - 0.5, r);
                    ctx.lineTo(w - r, h - 0.5);
                    ctx.arcTo(w - 0.5, h - 0.5, w - 0.5, h - r, r);
                    ctx.lineTo(w - 0.5, divY);
                    ctx.closePath();
                    ctx.fill();
                }
                ctx.beginPath();
                ctx.moveTo(0.5, divY);
                ctx.lineTo(w - 0.5, divY);
                ctx.stroke();
            } else if (root.panel === "right") {
                var divX2 = w - 4.8;
                if (root.active) {
                    ctx.beginPath();
                    ctx.moveTo(divX2, 0.5);
                    ctx.lineTo(w - r, 0.5);
                    ctx.arcTo(w - 0.5, 0.5, w - 0.5, r, r);
                    ctx.lineTo(w - 0.5, h - r);
                    ctx.arcTo(w - 0.5, h - 0.5, w - r, h - 0.5, r);
                    ctx.lineTo(divX2, h - 0.5);
                    ctx.closePath();
                    ctx.fill();
                }
                ctx.beginPath();
                ctx.moveTo(divX2, 0.5);
                ctx.lineTo(divX2, h - 0.5);
                ctx.stroke();
            }
        }
    }

    ToolTip.visible: ma.containsMouse && root.toolTipText.length > 0
    ToolTip.text: root.toolTipText
    ToolTip.delay: 350

    MouseArea {
        id: ma
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}

