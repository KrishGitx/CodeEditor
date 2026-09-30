import QtQuick 2.15

Item {
    id: root

    property bool isPlaying: false
    property string trackTitle: "No Track"
    property string trackArtist: "Ready"
    property real size: 68

    width: size
    height: size

    property real currentAngle: 0.0

    // Vinyl Disc
    Rectangle {
        id: disc
        anchors.fill: parent
        radius: width / 2
        color: "#121212"
        border.color: "#252525"
        border.width: 1

        transform: Rotation {
            origin.x: disc.width / 2
            origin.y: disc.height / 2
            angle: root.currentAngle
        }

        // Concentric Micro-Grooves
        Canvas {
            id: groovesCanvas
            anchors.fill: parent
            renderTarget: Canvas.Image

            onPaint: {
                var ctx = getContext("2d");
                ctx.reset();
                ctx.clearRect(0, 0, width, height);

                var cx = width / 2;
                var cy = height / 2;
                var maxR = width / 2 - 3;
                var minR = width * 0.22;

                ctx.strokeStyle = "#1a1a1a";
                ctx.lineWidth = 0.6;

                for (var r = minR + 3; r < maxR; r += 2.8) {
                    ctx.beginPath();
                    ctx.arc(cx, cy, r, 0, Math.PI * 2);
                    ctx.stroke();
                }
            }
        }

        // Center Label
        Rectangle {
            id: centerLabel
            anchors.centerIn: parent
            width: parent.width * 0.44
            height: width
            radius: width / 2
            color: theme ? theme.accent : "#0078d4"
            border.color: "#ffffff25"
            border.width: 1

            Column {
                anchors.centerIn: parent
                width: parent.width - 6
                spacing: 1

                Text {
                    width: parent.width
                    text: root.trackTitle
                    color: "#ffffff"
                    font.pixelSize: Math.max(6, root.size * 0.08)
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
            }

            // Center Hole
            Rectangle {
                anchors.centerIn: parent
                width: parent.width * 0.22
                height: width
                radius: width / 2
                color: "#121212"
            }
        }
    }

    NumberAnimation {
        id: rotationAnim
        target: root
        property: "currentAngle"
        from: root.currentAngle
        to: root.currentAngle + 360
        duration: 3600
        loops: Animation.Infinite
        running: root.isPlaying && (theme ? (theme.enableVinylAnimation && theme.enableAnimations) : true)
    }

    onIsPlayingChanged: {
        if (!root.isPlaying) {
            rotationAnim.stop();
        } else if (theme ? (theme.enableVinylAnimation && theme.enableAnimations) : true) {
            rotationAnim.start();
        }
    }
}
