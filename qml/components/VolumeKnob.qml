import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property real value: 0.8 // 0.0 to 1.0
    property real minimumValue: 0.0
    property real maximumValue: 1.0
    property real size: 36
    property bool readOnly: false

    signal moved(real val)

    width: size
    height: size

    // Arc range in degrees: 135 deg to 405 deg (270 deg total sweep)
    readonly property real startAngle: 135
    readonly property real endAngle: 405
    readonly property real totalAngle: 270
    readonly property real currentAngle: startAngle + (value * totalAngle)

    Canvas {
        id: knobCanvas
        anchors.fill: parent
        renderTarget: Canvas.Image

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.clearRect(0, 0, width, height);

            var centerX = width / 2;
            var centerY = height / 2;
            var radius = (Math.min(width, height) / 2) - 4;

            // 1. Outer Track Background Arc
            ctx.beginPath();
            var startRad = (root.startAngle * Math.PI) / 180;
            var endRad = (root.endAngle * Math.PI) / 180;
            ctx.arc(centerX, centerY, radius, startRad, endRad, false);
            ctx.strokeStyle = theme ? theme.borderNormal : "#333333";
            ctx.lineWidth = 3;
            ctx.lineCap = "round";
            ctx.stroke();

            // 2. Active Volume Value Arc
            if (root.value > 0.01) {
                ctx.beginPath();
                var curRad = (root.currentAngle * Math.PI) / 180;
                ctx.arc(centerX, centerY, radius, startRad, curRad, false);
                ctx.strokeStyle = theme ? theme.accent : "#0078d4";
                ctx.lineWidth = 3;
                ctx.lineCap = "round";
                ctx.stroke();
            }

            // 3. Inner Dial Disc
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius - 3, 0, 2 * Math.PI, false);
            ctx.fillStyle = theme ? theme.bgSurface : "#252526";
            ctx.fill();
            ctx.strokeStyle = theme ? theme.borderSubtle : "#282828";
            ctx.lineWidth = 1;
            ctx.stroke();

            // 4. Indicator Needle / Dot
            var needleRad = (root.currentAngle * Math.PI) / 180;
            var needleDist = radius - 5;
            var needleX = centerX + Math.cos(needleRad) * needleDist;
            var needleY = centerY + Math.sin(needleRad) * needleDist;

            ctx.beginPath();
            ctx.arc(needleX, needleY, 2, 0, 2 * Math.PI, false);
            ctx.fillStyle = theme ? theme.textBright : "#ffffff";
            ctx.fill();
        }
    }

    onValueChanged: knobCanvas.requestPaint()
    Component.onCompleted: knobCanvas.requestPaint()

    MouseArea {
        id: knobMa
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor

        property real lastY: 0
        property bool isDragging: false

        onPressed: function(mouse) {
            lastY = mouse.y;
            isDragging = true;
            updateValueFromAngle(mouse.x, mouse.y);
        }

        onPositionChanged: function(mouse) {
            if (isDragging) {
                // Support both vertical dragging and radial positioning
                var dy = lastY - mouse.y;
                lastY = mouse.y;
                var delta = dy / 100.0;
                var newVal = Math.max(0.0, Math.min(1.0, root.value + delta));
                if (newVal !== root.value) {
                    root.value = newVal;
                    root.moved(newVal);
                }
            }
        }

        onReleased: {
            isDragging = false;
        }

        onWheel: function(wheel) {
            var step = wheel.angleDelta.y > 0 ? 0.05 : -0.05;
            var newVal = Math.max(0.0, Math.min(1.0, root.value + step));
            if (newVal !== root.value) {
                root.value = newVal;
                root.moved(newVal);
            }
            wheel.accepted = true;
        }

        ToolTip.visible: knobMa.containsMouse || isDragging
        ToolTip.text: "Volume: " + Math.round(root.value * 100) + "%"

        function updateValueFromAngle(mx, my) {
            var cx = width / 2;
            var cy = height / 2;
            var dx = mx - cx;
            var dy = my - cy;
            var angleDeg = (Math.atan2(dy, dx) * 180) / Math.PI;
            if (angleDeg < 0) angleDeg += 360;

            // Map angle to 135 -> 405 range
            var relAngle = angleDeg - 135;
            if (relAngle < 0) relAngle += 360;

            if (relAngle <= 270) {
                var v = relAngle / 270.0;
                root.value = Math.max(0.0, Math.min(1.0, v));
                root.moved(root.value);
            }
        }
    }
}
