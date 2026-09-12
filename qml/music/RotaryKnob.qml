import QtQuick 2.15

Item {
    id: knobRoot
    width: 44
    height: 44

    property real value: 0.8 // 0.0 to 1.0
    signal valueModified(real newValue)

    // Minimum and maximum rotation angles in degrees (-135° to +135°)
    readonly property real minAngle: -135
    readonly property real maxAngle: 135
    readonly property real currentAngle: minAngle + (value * (maxAngle - minAngle))

    Canvas {
        id: knobCanvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()

            var cx = width / 2
            var cy = height / 2
            var r = Math.min(cx, cy) - 3

            // Outer ring track
            ctx.beginPath()
            ctx.arc(cx, cy, r, (-135 - 90) * Math.PI / 180, (135 - 90) * Math.PI / 180)
            ctx.lineWidth = 2.5
            ctx.strokeStyle = "#272a34"
            ctx.stroke()

            // Active volume arc
            var activeEndAngle = (knobRoot.currentAngle - 90) * Math.PI / 180
            ctx.beginPath()
            ctx.arc(cx, cy, r, (-135 - 90) * Math.PI / 180, activeEndAngle)
            ctx.lineWidth = 2.5
            ctx.strokeStyle = theme.accentColor
            ctx.stroke()

            // Knob Body (Dark metallic gradient)
            var bodyR = r - 4
            var bodyGrad = ctx.createRadialGradient(cx, cy - 2, 1, cx, cy, bodyR)
            bodyGrad.addColorStop(0, "#2a2e3d")
            bodyGrad.addColorStop(0.7, "#1a1d26")
            bodyGrad.addColorStop(1, "#12141a")
            ctx.beginPath()
            ctx.arc(cx, cy, bodyR, 0, 2 * Math.PI)
            ctx.fillStyle = bodyGrad
            ctx.fill()

            ctx.lineWidth = 1.0
            ctx.strokeStyle = "#3e4456"
            ctx.stroke()

            // Indicator line on knob
            var rad = (knobRoot.currentAngle - 90) * Math.PI / 180
            var indInnerR = bodyR * 0.3
            var indOuterR = bodyR * 0.85
            var x1 = cx + indInnerR * Math.cos(rad)
            var y1 = cy + indInnerR * Math.sin(rad)
            var x2 = cx + indOuterR * Math.cos(rad)
            var y2 = cy + indOuterR * Math.sin(rad)

            ctx.beginPath()
            ctx.moveTo(x1, y1)
            ctx.lineTo(x2, y2)
            ctx.lineWidth = 2.0
            ctx.strokeStyle = "#ffffff"
            ctx.lineCap = "round"
            ctx.stroke()
        }
    }

    onValueChanged: knobCanvas.requestPaint()

    MouseArea {
        id: knobMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        property real startY: 0
        property real startVal: 0

        onPressed: mouse => {
            startY = mouse.y
            startVal = knobRoot.value
        }

        onPositionChanged: mouse => {
            if (pressed) {
                var deltaY = startY - mouse.y
                var newVal = Math.max(0.0, Math.min(1.0, startVal + (deltaY / 100.0)))
                knobRoot.value = newVal
                knobRoot.valueModified(newVal)
            }
        }

        onWheel: wheel => {
            var step = wheel.angleDelta.y > 0 ? 0.05 : -0.05
            var newVal = Math.max(0.0, Math.min(1.0, knobRoot.value + step))
            knobRoot.value = newVal
            knobRoot.valueModified(newVal)
        }
    }
}
