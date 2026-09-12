import QtQuick 2.15

Item {
    id: vinylRoot

    width: 130
    height: 130

    // Keep the existing public property.
    property string playbackState: "stopped"

    property bool isPlaying: playbackState === "playing"

    // Persistent rotation angle.
    property real spinAngle: 0

    // ============================================================
    // VINYL ROTATION
    // ============================================================

    NumberAnimation {
        id: spinAnimation

        target: vinylRoot
        property: "spinAngle"

        from: vinylRoot.spinAngle
        to: vinylRoot.spinAngle + 360

        duration: 2600
        loops: Animation.Infinite

        running: vinylRoot.isPlaying && theme.animationsEnabled

        onStopped: {
            // Intentionally do not reset spinAngle.
            // Pausing should freeze the record where it is.
        }
    }

    onPlaybackStateChanged: {
        if (playbackState === "playing") {
            if (theme.animationsEnabled) {
                spinAnimation.stop()
                spinAnimation.from = spinAngle
                spinAnimation.to = spinAngle + 360
                spinAnimation.start()
            }
        } else {
            spinAnimation.stop()
        }
    }

    Connections {
        target: theme

        function onAnimationsEnabledChanged() {
            spinAnimation.stop()

            if (vinylRoot.isPlaying && theme.animationsEnabled) {
                spinAnimation.from = vinylRoot.spinAngle
                spinAnimation.to = vinylRoot.spinAngle + 360
                spinAnimation.start()
            }
        }
    }

    // ============================================================
    // ROTATING RECORD
    // ============================================================

    Item {
        id: rotatingDisc

        anchors.fill: parent

        rotation: vinylRoot.spinAngle

        // --------------------------------------------------------
        // Vinyl body
        // --------------------------------------------------------

        Rectangle {
            id: record

            anchors.fill: parent

            radius: width / 2

            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: "#292a30"
                }

                GradientStop {
                    position: 0.35
                    color: "#17181c"
                }

                GradientStop {
                    position: 0.75
                    color: "#0d0e11"
                }

                GradientStop {
                    position: 1.0
                    color: "#050506"
                }
            }

            border.width: 1
            border.color: "#383b43"

            // ----------------------------------------------------
            // Grooves
            // ----------------------------------------------------

            Repeater {
                model: 19

                Rectangle {
                    property real grooveRadius:
                        record.width * (0.43 + index * 0.027)

                    width: grooveRadius * 2
                    height: grooveRadius * 2

                    x: record.width / 2 - width / 2
                    y: record.height / 2 - height / 2

                    radius: width / 2

                    color: "transparent"

                    border.width: 1

                    border.color:
                        index % 2 === 0
                        ? "#24252a"
                        : "#101114"
                }
            }

            // ----------------------------------------------------
            // Inner groove
            // ----------------------------------------------------

            Rectangle {
                width: parent.width * 0.84
                height: width

                anchors.centerIn: parent

                radius: width / 2

                color: "transparent"

                border.width: 1
                border.color: "#303239"
            }

            // ----------------------------------------------------
            // Center label
            // ----------------------------------------------------

            Rectangle {
                id: label

                width: parent.width * 0.36
                height: width

                anchors.centerIn: parent

                radius: width / 2

                gradient: Gradient {
                    GradientStop {
                        position: 0.0
                        color: "#1593cc"
                    }

                    GradientStop {
                        position: 0.65
                        color: "#0876aa"
                    }

                    GradientStop {
                        position: 1.0
                        color: "#075985"
                    }
                }

                border.width: 1
                border.color: "#5fb8df"
            }

            // ----------------------------------------------------
            // Center hole
            // ----------------------------------------------------

            Rectangle {
                width: parent.width * 0.075
                height: width

                anchors.centerIn: parent

                radius: width / 2

                color: "#050506"

                border.width: 1
                border.color: "#8a8d94"
            }
        }

        // ========================================================
        // RECORD SHEEN
        // ========================================================

        Canvas {
            id: sheen

            anchors.fill: parent

            opacity: 0.30

            onPaint: {
                var ctx = getContext("2d")

                ctx.reset()

                var cx = width / 2
                var cy = height / 2
                var r = Math.min(width, height) / 2 - 2

                var gradient = ctx.createRadialGradient(
                    cx,
                    cy,
                    r * 0.10,
                    cx,
                    cy,
                    r
                )

                gradient.addColorStop(
                    0,
                    "rgba(255,255,255,0.16)"
                )

                gradient.addColorStop(
                    0.55,
                    "rgba(255,255,255,0.06)"
                )

                gradient.addColorStop(
                    1,
                    "rgba(255,255,255,0.0)"
                )

                // First reflective sweep.
                ctx.beginPath()

                ctx.moveTo(cx, cy)

                ctx.arc(
                    cx,
                    cy,
                    r,
                    -Math.PI / 3.5,
                    Math.PI / 18
                )

                ctx.closePath()

                ctx.fillStyle = gradient
                ctx.fill()

                // Second subtle reflection.
                ctx.beginPath()

                ctx.moveTo(cx, cy)

                ctx.arc(
                    cx,
                    cy,
                    r,
                    2.55,
                    3.15
                )

                ctx.closePath()

                ctx.fillStyle = gradient
                ctx.fill()
            }
        }

        // Outer highlight.
        Rectangle {
            anchors.fill: parent

            radius: width / 2

            color: "transparent"

            border.width: 1
            border.color: "#ffffff18"
        }
    }

    // ============================================================
    // STARTUP
    // ============================================================

    Component.onCompleted: {
        if (vinylRoot.isPlaying && theme.animationsEnabled) {
            spinAnimation.from = vinylRoot.spinAngle
            spinAnimation.to = vinylRoot.spinAngle + 360
            spinAnimation.start()
        }
    }
}
