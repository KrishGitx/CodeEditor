import QtQuick 2.15

Item {
    id: root
    anchors.fill: parent
    z: 250
    clip: true

    Connections {
        target: (typeof extensionManager !== "undefined" && extensionManager) ? extensionManager : null
        function onParticleEmitRequested(typeStr, startX, startY, count, durationMs) {
            spawnParticles(typeStr, startX, startY, count, durationMs);
        }
    }

    function spawnParticles(typeStr, startX, startY, count, durationMs) {
        var num = Math.min(25, count || 20);
        var dur = durationMs || 1500;
        var palette = ["#ff595e", "#ffca3a", "#8ac926", "#1982c4", "#6a4c93", "#f72585", "#4cc9f0"];

        for (var i = 0; i < num; i++) {
            var p = particleComponent.createObject(root, {
                particleType: typeStr,
                startX: startX,
                startY: startY,
                pColor: palette[Math.floor(Math.random() * palette.length)],
                dx: (Math.random() - 0.5) * 360,
                dy: (typeStr === "snow" || typeStr === "bubbles") ? -(Math.random() * 200 + 100) : (Math.random() * 300 - 150),
                duration: dur * (0.8 + Math.random() * 0.4),
                rot: (Math.random() - 0.5) * 720
            });
            if (p) p.start();
        }
    }

    Component {
        id: particleComponent
        Item {
            id: pItem
            property string particleType: "confetti"
            property real startX: 0
            property real startY: 0
            property color pColor: "#ffca3a"
            property real dx: 0
            property real dy: 0
            property real duration: 1500
            property real rot: 360

            x: startX
            y: startY
            opacity: 1.0

            Rectangle {
                anchors.centerIn: parent
                width: (pItem.particleType === "confetti") ? 8 : ((pItem.particleType === "stars") ? 10 : 7)
                height: (pItem.particleType === "confetti") ? 12 : width
                radius: (pItem.particleType === "bubbles" || pItem.particleType === "snow") ? (width / 2) : 1
                color: pItem.pColor
                rotation: pItem.rot
            }

            function start() {
                anim.start();
            }

            ParallelAnimation {
                id: anim
                NumberAnimation { target: pItem; property: "x"; to: pItem.startX + pItem.dx; duration: pItem.duration; easing.type: Easing.OutQuad }
                NumberAnimation { target: pItem; property: "y"; to: pItem.startY + pItem.dy; duration: pItem.duration; easing.type: Easing.OutQuad }
                NumberAnimation { target: pItem; property: "opacity"; to: 0.0; duration: pItem.duration; easing.type: Easing.InQuad }
                onFinished: pItem.destroy()
            }
        }
    }
}

