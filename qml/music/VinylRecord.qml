import QtQuick 2.15
import Qt5Compat.GraphicalEffects

Item {
    id: root

    property bool isPlaying: false
    property string trackTitle: "No Track"
    property string trackArtist: "Ready"
    property string coverUrl: ""
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

        // Concentric High-Visibility Grooves & Yellow Ring
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
                var maxR = width / 2 - 2;
                var minR = width * 0.23;

                // 1. Outer rim lead-in track
                ctx.strokeStyle = "rgba(255, 255, 255, 0.24)";
                ctx.lineWidth = 1.0;
                ctx.beginPath();
                ctx.arc(cx, cy, maxR, 0, Math.PI * 2);
                ctx.stroke();

                // 2. High-contrast sound grooves
                var step = 2.4;
                var idx = 0;
                for (var r = minR + 4; r < maxR - 1; r += step) {
                    idx++;
                    var alpha = (idx % 3 === 0) ? 0.24 : ((idx % 2 === 0) ? 0.16 : 0.09);
                    ctx.strokeStyle = "rgba(255, 255, 255, " + alpha + ")";
                    ctx.lineWidth = (idx % 3 === 0) ? 0.8 : 0.5;
                    ctx.beginPath();
                    ctx.arc(cx, cy, r, 0, Math.PI * 2);
                    ctx.stroke();

                    // Dark groove cut right next to it for authentic depth
                    if (idx % 3 === 0) {
                        ctx.strokeStyle = "rgba(0, 0, 0, 0.70)";
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.arc(cx, cy, r + 0.6, 0, Math.PI * 2);
                        ctx.stroke();
                    }
                }

                // 3. Prominent Yellow / Golden circular line in disk
                var midR = minR + (maxR - minR) * 0.52;
                ctx.strokeStyle = "#eab308";
                ctx.lineWidth = 1.4;
                ctx.beginPath();
                ctx.arc(cx, cy, midR, 0, Math.PI * 2);
                ctx.stroke();

                // Inner golden accent ring near center label
                ctx.strokeStyle = "rgba(250, 204, 21, 0.85)";
                ctx.lineWidth = 1.0;
                ctx.beginPath();
                ctx.arc(cx, cy, minR + 2, 0, Math.PI * 2);
                ctx.stroke();

                // 4. Specular vinyl luster sheen (anisotropic reflections)
                var grad = ctx.createLinearGradient(cx - maxR, cy - maxR, cx + maxR, cy + maxR);
                grad.addColorStop(0.0, "rgba(255, 255, 255, 0.12)");
                grad.addColorStop(0.25, "rgba(255, 255, 255, 0.0)");
                grad.addColorStop(0.75, "rgba(255, 255, 255, 0.0)");
                grad.addColorStop(1.0, "rgba(255, 255, 255, 0.12)");
                ctx.fillStyle = grad;
                ctx.beginPath();
                ctx.arc(cx, cy, maxR, 0, Math.PI * 2);
                ctx.fill();

                var grad2 = ctx.createLinearGradient(cx + maxR, cy - maxR, cx - maxR, cy + maxR);
                grad2.addColorStop(0.0, "rgba(255, 255, 255, 0.08)");
                grad2.addColorStop(0.3, "rgba(255, 255, 255, 0.0)");
                grad2.addColorStop(0.7, "rgba(255, 255, 255, 0.0)");
                grad2.addColorStop(1.0, "rgba(255, 255, 255, 0.08)");
                ctx.fillStyle = grad2;
                ctx.beginPath();
                ctx.arc(cx, cy, maxR, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        // Center Label Hub
        Item {
            id: centerLabel
            anchors.centerIn: parent
            width: parent.width * 0.46
            height: width

            // Fallback Background Circle
            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: theme ? theme.accent : "#0078d4"
                border.color: "#ffffff30"
                border.width: 1
            }

            // Raw Image (Used as source for OpacityMask)
            Image {
                id: rawCoverImage
                anchors.fill: parent
                source: root.coverUrl
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                cache: true
                visible: false
            }

            // Circular Mask
            Rectangle {
                id: circularMask
                anchors.fill: parent
                radius: width / 2
                visible: false
            }

            // Circular Cropped Album Cover
            OpacityMask {
                id: albumCoverImg
                anchors.fill: parent
                source: rawCoverImage
                maskSource: circularMask
                visible: root.coverUrl !== "" && rawCoverImage.status === Image.Ready
            }

            Column {
                anchors.centerIn: parent
                width: parent.width - 6
                spacing: 1
                visible: !albumCoverImg.visible

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

            // Center Spindle Hole
            Rectangle {
                anchors.centerIn: parent
                width: parent.width * 0.22
                height: width
                radius: width / 2
                color: "#121212"
                border.color: "#333333"
                border.width: 1
                z: 10
            }

            // Crisp Golden Ring Framing the Album Center Hub
            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: "transparent"
                border.color: "#eab308"
                border.width: 1.5
                z: 15
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
