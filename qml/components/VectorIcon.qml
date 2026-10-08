import QtQuick 2.15

Item {
    id: root

    property string name: "file"
    property color color: "#94a3b8"
    property real size: 16

    width: size
    height: size

    Canvas {
        id: canvas
        anchors.fill: parent
        renderTarget: Canvas.Image
        renderStrategy: Canvas.Threaded

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.clearRect(0, 0, width, height);

            ctx.strokeStyle = root.color;
            ctx.fillStyle = root.color;
            ctx.lineWidth = Math.max(1.2, width / 11);
            ctx.lineCap = "round";
            ctx.lineJoin = "round";

            var w = width;
            var h = height;
            var pad = w * 0.12;
            var n = root.name;

            if (n === "file") {
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.1, pad);
                ctx.lineTo(w - pad - w * 0.25, pad);
                ctx.lineTo(w - pad, pad + h * 0.25);
                ctx.lineTo(w - pad, h - pad);
                ctx.lineTo(pad + w * 0.1, h - pad);
                ctx.closePath();
                ctx.stroke();

                ctx.beginPath();
                ctx.moveTo(w - pad - w * 0.25, pad);
                ctx.lineTo(w - pad - w * 0.25, pad + h * 0.25);
                ctx.lineTo(w - pad, pad + h * 0.25);
                ctx.stroke();
            }
            else if (n === "folder" || n === "folder-closed") {
                ctx.beginPath();
                ctx.moveTo(pad, pad + h * 0.2);
                ctx.lineTo(pad + w * 0.3, pad + h * 0.2);
                ctx.lineTo(pad + w * 0.45, pad + h * 0.35);
                ctx.lineTo(w - pad, pad + h * 0.35);
                ctx.lineTo(w - pad, h - pad);
                ctx.lineTo(pad, h - pad);
                ctx.closePath();
                ctx.stroke();
            }
            else if (n === "folder-open") {
                ctx.beginPath();
                ctx.moveTo(pad, pad + h * 0.2);
                ctx.lineTo(pad + w * 0.3, pad + h * 0.2);
                ctx.lineTo(pad + w * 0.42, pad + h * 0.35);
                ctx.lineTo(w - pad, pad + h * 0.35);
                ctx.lineTo(w - pad, h - pad);
                ctx.lineTo(pad, h - pad);
                ctx.closePath();
                ctx.stroke();

                ctx.beginPath();
                ctx.moveTo(pad * 0.8, h - pad);
                ctx.lineTo(pad * 1.6, pad + h * 0.45);
                ctx.lineTo(w - pad * 0.8, pad + h * 0.45);
                ctx.lineTo(w - pad * 1.6, h - pad);
                ctx.closePath();
                ctx.stroke();
            }
            else if (n === "new-file") {
                ctx.beginPath();
                ctx.moveTo(pad, pad);
                ctx.lineTo(w - pad - w * 0.25, pad);
                ctx.lineTo(w - pad, pad + h * 0.25);
                ctx.lineTo(w - pad, h * 0.6);
                ctx.moveTo(pad, pad);
                ctx.lineTo(pad, h - pad);
                ctx.lineTo(w * 0.55, h - pad);
                ctx.stroke();

                // Plus sign
                ctx.beginPath();
                ctx.moveTo(w * 0.75, h * 0.65);
                ctx.lineTo(w * 0.75, h * 0.95);
                ctx.moveTo(w * 0.6, h * 0.8);
                ctx.lineTo(w * 0.9, h * 0.8);
                ctx.stroke();
            }
            else if (n === "new-folder") {
                ctx.beginPath();
                ctx.moveTo(pad, pad + h * 0.2);
                ctx.lineTo(pad + w * 0.3, pad + h * 0.2);
                ctx.lineTo(pad + w * 0.45, pad + h * 0.35);
                ctx.lineTo(w - pad, pad + h * 0.35);
                ctx.lineTo(w - pad, h * 0.6);
                ctx.moveTo(pad, pad + h * 0.2);
                ctx.lineTo(pad, h - pad);
                ctx.lineTo(w * 0.55, h - pad);
                ctx.stroke();

                // Plus
                ctx.beginPath();
                ctx.moveTo(w * 0.75, h * 0.65);
                ctx.lineTo(w * 0.75, h * 0.95);
                ctx.moveTo(w * 0.6, h * 0.8);
                ctx.lineTo(w * 0.9, h * 0.8);
                ctx.stroke();
            }
            else if (n === "refresh") {
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.32, 0.2 * Math.PI, 1.75 * Math.PI, false);
                ctx.stroke();

                // Arrowhead
                ctx.beginPath();
                ctx.moveTo(w * 0.5, h * 0.15);
                ctx.lineTo(w * 0.65, h * 0.18);
                ctx.lineTo(w * 0.6, h * 0.33);
                ctx.stroke();
            }
            else if (n === "play") {
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.15, pad);
                ctx.lineTo(w - pad, h / 2);
                ctx.lineTo(pad + w * 0.15, h - pad);
                ctx.closePath();
                ctx.fill();
            }
            else if (n === "pause") {
                var barW = w * 0.18;
                var gap = w * 0.2;
                ctx.fillRect(w / 2 - gap / 2 - barW, pad, barW, h - pad * 2);
                ctx.fillRect(w / 2 + gap / 2, pad, barW, h - pad * 2);
            }
            else if (n === "stop") {
                ctx.fillRect(pad + w * 0.08, pad + h * 0.08, w - pad * 2 - w * 0.16, h - pad * 2 - h * 0.16);
            }
            else if (n === "next") {
                ctx.beginPath();
                ctx.moveTo(pad, pad);
                ctx.lineTo(w * 0.55, h / 2);
                ctx.lineTo(pad, h - pad);
                ctx.closePath();
                ctx.fill();

                ctx.fillRect(w * 0.68, pad, w * 0.14, h - pad * 2);
            }
            else if (n === "prev") {
                ctx.beginPath();
                ctx.moveTo(w - pad, pad);
                ctx.lineTo(w * 0.45, h / 2);
                ctx.lineTo(w - pad, h - pad);
                ctx.closePath();
                ctx.fill();

                ctx.fillRect(w * 0.18, pad, w * 0.14, h - pad * 2);
            }
            else if (n === "volume" || n === "volume-high") {
                ctx.beginPath();
                ctx.moveTo(pad, h * 0.35);
                ctx.lineTo(pad + w * 0.2, h * 0.35);
                ctx.lineTo(pad + w * 0.45, pad);
                ctx.lineTo(pad + w * 0.45, h - pad);
                ctx.lineTo(pad + w * 0.2, h * 0.65);
                ctx.lineTo(pad, h * 0.65);
                ctx.closePath();
                ctx.fill();

                ctx.beginPath();
                ctx.arc(pad + w * 0.45, h / 2, w * 0.25, -0.35 * Math.PI, 0.35 * Math.PI, false);
                ctx.stroke();

                ctx.beginPath();
                ctx.arc(pad + w * 0.45, h / 2, w * 0.4, -0.4 * Math.PI, 0.4 * Math.PI, false);
                ctx.stroke();
            }
            else if (n === "mute" || n === "volume-mute") {
                ctx.beginPath();
                ctx.moveTo(pad, h * 0.35);
                ctx.lineTo(pad + w * 0.2, h * 0.35);
                ctx.lineTo(pad + w * 0.45, pad);
                ctx.lineTo(pad + w * 0.45, h - pad);
                ctx.lineTo(pad + w * 0.2, h * 0.65);
                ctx.lineTo(pad, h * 0.65);
                ctx.closePath();
                ctx.fill();

                ctx.beginPath();
                ctx.moveTo(w * 0.65, h * 0.35);
                ctx.lineTo(w * 0.9, h * 0.65);
                ctx.moveTo(w * 0.9, h * 0.35);
                ctx.lineTo(w * 0.65, h * 0.65);
                ctx.stroke();
            }
            else if (n === "search") {
                var r = w * 0.28;
                ctx.beginPath();
                ctx.arc(pad + r, pad + r, r, 0, Math.PI * 2);
                ctx.stroke();

                ctx.beginPath();
                ctx.moveTo(pad + r + r * 0.7, pad + r + r * 0.7);
                ctx.lineTo(w - pad, h - pad);
                ctx.stroke();
            }
            else if (n === "settings" || n === "gear") {
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.16, 0, Math.PI * 2);
                ctx.stroke();

                for (var i = 0; i < 6; i++) {
                    var angle = (i * Math.PI) / 3;
                    var cos = Math.cos(angle);
                    var sin = Math.sin(angle);
                    ctx.beginPath();
                    ctx.moveTo(w / 2 + cos * w * 0.26, h / 2 + sin * h * 0.26);
                    ctx.lineTo(w / 2 + cos * w * 0.4, h / 2 + sin * h * 0.4);
                    ctx.stroke();
                }
            }
            else if (n === "sparkles" || n === "ai") {
                // 4-point star
                var cx = w / 2;
                var cy = h / 2;
                ctx.beginPath();
                ctx.moveTo(cx, pad);
                ctx.quadraticCurveTo(cx, cy, w - pad, cy);
                ctx.quadraticCurveTo(cx, cy, cx, h - pad);
                ctx.quadraticCurveTo(cx, cy, pad, cy);
                ctx.quadraticCurveTo(cx, cy, cx, pad);
                ctx.closePath();
                ctx.fill();

                // Small star
                var sx = w * 0.8;
                var sy = h * 0.25;
                var sr = w * 0.12;
                ctx.beginPath();
                ctx.moveTo(sx, sy - sr);
                ctx.quadraticCurveTo(sx, sy, sx + sr, sy);
                ctx.quadraticCurveTo(sx, sy, sx, sy + sr);
                ctx.quadraticCurveTo(sx, sy, sx - sr, sy);
                ctx.quadraticCurveTo(sx, sy, sx, sy - sr);
                ctx.closePath();
                ctx.fill();
            }
            else if (n === "puzzle" || n === "extension" || n === "plugin") {
                var pX = pad;
                var pY = pad;
                var pW = w - pad * 2;
                var pH = h - pad * 2;
                var r = pW * 0.16;

                ctx.beginPath();
                ctx.moveTo(pX, pY);
                ctx.lineTo(pX + pW * 0.35, pY);
                ctx.arc(pX + pW * 0.5, pY, r, Math.PI, 0, false);
                ctx.lineTo(pX + pW, pY);
                ctx.lineTo(pX + pW, pY + pH * 0.35);
                ctx.arc(pX + pW, pY + pH * 0.5, r, -Math.PI / 2, Math.PI / 2, true);
                ctx.lineTo(pX + pW, pY + pH);
                ctx.lineTo(pX + pW * 0.65, pY + pH);
                ctx.arc(pX + pW * 0.5, pY + pH, r, 0, Math.PI, true);
                ctx.lineTo(pX, pY + pH);
                ctx.lineTo(pX, pY + pH * 0.65);
                ctx.arc(pX, pY + pH * 0.5, r, Math.PI / 2, -Math.PI / 2, false);
                ctx.closePath();
                ctx.stroke();
            }
            else if (n === "bolt" || n === "lightning" || n === "flash") {
                ctx.beginPath();
                ctx.moveTo(w * 0.55, pad);
                ctx.lineTo(pad + w * 0.15, h * 0.52);
                ctx.lineTo(w * 0.48, h * 0.52);
                ctx.lineTo(w * 0.42, h - pad);
                ctx.lineTo(w - pad - w * 0.1, h * 0.44);
                ctx.lineTo(w * 0.55, h * 0.44);
                ctx.closePath();
                ctx.fill();
            }
            else if (n === "download") {
                ctx.beginPath();
                ctx.moveTo(w / 2, pad);
                ctx.lineTo(w / 2, h * 0.65);
                ctx.moveTo(w * 0.3, h * 0.45);
                ctx.lineTo(w / 2, h * 0.65);
                ctx.lineTo(w * 0.7, h * 0.45);
                ctx.moveTo(pad, h - pad);
                ctx.lineTo(w - pad, h - pad);
                ctx.stroke();
            }
            else if (n === "code" || n === "brackets" || n === "syntax") {
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.28, pad + h * 0.15);
                ctx.lineTo(pad + w * 0.06, h / 2);
                ctx.lineTo(pad + w * 0.28, h - pad - h * 0.15);
                ctx.moveTo(w * 0.62, pad + h * 0.1);
                ctx.lineTo(w * 0.38, h - pad - h * 0.1);
                ctx.moveTo(w - pad - w * 0.28, pad + h * 0.15);
                ctx.lineTo(w - pad - w * 0.06, h / 2);
                ctx.lineTo(w - pad - w * 0.28, h - pad - h * 0.15);
                ctx.stroke();
            }
            else if (n === "terminal") {
                ctx.beginPath();
                ctx.moveTo(pad, pad);
                ctx.lineTo(w - pad, pad);
                ctx.lineTo(w - pad, h - pad);
                ctx.lineTo(pad, h - pad);
                ctx.closePath();
                ctx.stroke();

                // Chevron prompt
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.15, pad + h * 0.25);
                ctx.lineTo(pad + w * 0.35, h / 2);
                ctx.lineTo(pad + w * 0.15, h - pad - h * 0.25);
                ctx.stroke();

                // Underscore cursor
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.45, h - pad - h * 0.25);
                ctx.lineTo(pad + w * 0.7, h - pad - h * 0.25);
                ctx.stroke();
            }
            else if (n === "close" || n === "x") {
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.1, pad + h * 0.1);
                ctx.lineTo(w - pad - w * 0.1, h - pad - h * 0.1);
                ctx.moveTo(w - pad - w * 0.1, pad + h * 0.1);
                ctx.lineTo(pad + w * 0.1, h - pad - h * 0.1);
                ctx.stroke();
            }
            else if (n === "minimize" || n === "minus") {
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.1, h / 2);
                ctx.lineTo(w - pad - w * 0.1, h / 2);
                ctx.stroke();
            }
            else if (n === "maximize") {
                ctx.beginPath();
                ctx.rect(pad + w * 0.1, pad + h * 0.1, w - pad * 2 - w * 0.2, h - pad * 2 - h * 0.2);
                ctx.stroke();
            }
            else if (n === "restore") {
                ctx.beginPath();
                ctx.rect(pad + w * 0.25, pad, w - pad * 2 - w * 0.25, h - pad * 2 - h * 0.25);
                ctx.stroke();
                ctx.beginPath();
                ctx.rect(pad, pad + h * 0.25, w - pad * 2 - w * 0.25, h - pad * 2 - h * 0.25);
                ctx.stroke();
            }
            else if (n === "chevron-right") {
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.2, pad);
                ctx.lineTo(w - pad - w * 0.2, h / 2);
                ctx.lineTo(pad + w * 0.2, h - pad);
                ctx.stroke();
            }
            else if (n === "chevron-down") {
                ctx.beginPath();
                ctx.moveTo(pad, pad + h * 0.2);
                ctx.lineTo(w / 2, h - pad - h * 0.2);
                ctx.lineTo(w - pad, pad + h * 0.2);
                ctx.stroke();
            }
            else if (n === "check") {
                ctx.beginPath();
                ctx.moveTo(pad, h * 0.55);
                ctx.lineTo(w * 0.4, h - pad);
                ctx.lineTo(w - pad, pad);
                ctx.stroke();
            }
            else if (n === "copy") {
                ctx.beginPath();
                ctx.rect(w * 0.3, pad, w * 0.55, h * 0.65);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(w * 0.25, pad + h * 0.2);
                ctx.lineTo(pad, pad + h * 0.2);
                ctx.lineTo(pad, h - pad);
                ctx.lineTo(w * 0.65, h - pad);
                ctx.lineTo(w * 0.65, pad + h * 0.7);
                ctx.stroke();
            }
            else if (n === "zen" || n === "focus") {
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.35, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.12, 0, Math.PI * 2);
                ctx.fill();
            }
            else if (n === "music" || n === "disc") {
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.38, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.15, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.05, 0, Math.PI * 2);
                ctx.fill();
            }
            else if (n === "undo") {
                ctx.beginPath();
                ctx.arc(w * 0.55, h * 0.55, w * 0.3, 0.8 * Math.PI, 1.8 * Math.PI, false);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(w * 0.15, h * 0.45);
                ctx.lineTo(w * 0.3, h * 0.2);
                ctx.lineTo(w * 0.42, h * 0.38);
                ctx.stroke();
            }
            else if (n === "redo") {
                ctx.beginPath();
                ctx.arc(w * 0.45, h * 0.55, w * 0.3, 1.2 * Math.PI, 0.2 * Math.PI, true);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(w * 0.85, h * 0.45);
                ctx.lineTo(w * 0.7, h * 0.2);
                ctx.lineTo(w * 0.58, h * 0.38);
                ctx.stroke();
            }
            else if (n === "save") {
                ctx.beginPath();
                ctx.moveTo(pad, pad);
                ctx.lineTo(w - pad - w * 0.2, pad);
                ctx.lineTo(w - pad, pad + h * 0.2);
                ctx.lineTo(w - pad, h - pad);
                ctx.lineTo(pad, h - pad);
                ctx.closePath();
                ctx.stroke();
                ctx.fillRect(pad + w * 0.15, pad, w * 0.4, h * 0.3);
            }
            else if (n === "keyboard") {
                ctx.beginPath();
                ctx.roundRect ? ctx.roundRect(pad, pad * 1.5, w - pad * 2, h - pad * 3, 2) : ctx.rect(pad, pad * 1.5, w - pad * 2, h - pad * 3);
                ctx.stroke();
                // Key dots
                var kw = (w - pad * 2) / 4;
                var kh = (h - pad * 3) / 3;
                for (var rk = 0; rk < 2; rk++) {
                    for (var ck = 0; ck < 3; ck++) {
                        ctx.fillRect(pad + (ck + 0.5) * kw, pad * 1.5 + (rk + 0.5) * kh, kw * 0.5, kh * 0.5);
                    }
                }
                // Space bar
                ctx.fillRect(pad + kw, pad * 1.5 + 2 * kh, kw * 2, kh * 0.4);
            }
            else if (n === "info") {
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.38, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(w / 2, h * 0.35, w * 0.04, 0, Math.PI * 2);
                ctx.fill();
                ctx.beginPath();
                ctx.moveTo(w / 2, h * 0.48);
                ctx.lineTo(w / 2, h * 0.72);
                ctx.stroke();
            }
            else if (n === "back" || n === "arrow-left") {
                ctx.beginPath();
                ctx.moveTo(w - pad - 2, h / 2);
                ctx.lineTo(pad + 2, h / 2);
                ctx.moveTo(pad + w * 0.35, pad + 2);
                ctx.lineTo(pad + 2, h / 2);
                ctx.lineTo(pad + w * 0.35, h - pad - 2);
                ctx.stroke();
            }
            else if (n === "board" || n === "whiteboard") {
                // Whiteboard frame & easel stand
                ctx.beginPath();
                ctx.rect(pad, pad, w - pad * 2, h * 0.58);
                ctx.stroke();
                // Marker tray
                ctx.beginPath();
                ctx.moveTo(pad * 0.7, pad + h * 0.58);
                ctx.lineTo(w - pad * 0.7, pad + h * 0.58);
                ctx.stroke();
                // Legs
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.15, pad + h * 0.58);
                ctx.lineTo(pad * 0.8, h - pad * 0.5);
                ctx.moveTo(w - pad - w * 0.15, pad + h * 0.58);
                ctx.lineTo(w - pad * 0.8, h - pad * 0.5);
                ctx.stroke();
            }
            else if (n === "hand" || n === "pan") {
                // Hand icon with fingers for pan/navigation
                ctx.beginPath();
                ctx.moveTo(w * 0.3, h * 0.75);
                ctx.lineTo(w * 0.3, h * 0.35);
                ctx.lineTo(w * 0.42, h * 0.35);
                ctx.lineTo(w * 0.42, h * 0.22);
                ctx.lineTo(w * 0.54, h * 0.22);
                ctx.lineTo(w * 0.54, h * 0.28);
                ctx.lineTo(w * 0.66, h * 0.28);
                ctx.lineTo(w * 0.66, h * 0.4);
                ctx.lineTo(w * 0.76, h * 0.48);
                ctx.lineTo(w * 0.76, h * 0.75);
                ctx.closePath();
                ctx.stroke();
            }
            else if (n === "eraser") {
                // Angled eraser block
                ctx.save();
                ctx.translate(w / 2, h / 2);
                ctx.rotate(-Math.PI / 4);
                ctx.beginPath();
                ctx.rect(-w * 0.35, -h * 0.2, w * 0.7, h * 0.4);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(0, -h * 0.2);
                ctx.lineTo(0, h * 0.2);
                ctx.stroke();
                ctx.restore();
            }
            else if (n === "focus" || n === "target" || n === "center") {
                // Center / Fit viewport crosshair
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.32, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(w / 2, pad * 0.6);
                ctx.lineTo(w / 2, pad * 1.6);
                ctx.moveTo(w / 2, h - pad * 1.6);
                ctx.lineTo(w / 2, h - pad * 0.6);
                ctx.moveTo(pad * 0.6, h / 2);
                ctx.lineTo(pad * 1.6, h / 2);
                ctx.moveTo(w - pad * 1.6, h / 2);
                ctx.lineTo(w - pad * 0.6, h / 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.08, 0, Math.PI * 2);
                ctx.fill();
            }
            else if (n === "heart" || n === "like") {
                // Outline Heart
                ctx.beginPath();
                var topCurveHeight = h * 0.3;
                ctx.moveTo(w / 2, h * 0.82);
                ctx.bezierCurveTo(w * 0.1, h * 0.55, w * 0.05, h * 0.2, w * 0.3, h * 0.2);
                ctx.bezierCurveTo(w * 0.42, h * 0.2, w * 0.48, h * 0.32, w / 2, h * 0.38);
                ctx.bezierCurveTo(w * 0.52, h * 0.32, w * 0.58, h * 0.2, w * 0.7, h * 0.2);
                ctx.bezierCurveTo(w * 0.95, h * 0.2, w * 0.9, h * 0.55, w / 2, h * 0.82);
                ctx.closePath();
                ctx.stroke();
            }
            else if (n === "heart-filled" || n === "liked") {
                // Filled Heart
                ctx.beginPath();
                ctx.moveTo(w / 2, h * 0.82);
                ctx.bezierCurveTo(w * 0.1, h * 0.55, w * 0.05, h * 0.2, w * 0.3, h * 0.2);
                ctx.bezierCurveTo(w * 0.42, h * 0.2, w * 0.48, h * 0.32, w / 2, h * 0.38);
                ctx.bezierCurveTo(w * 0.52, h * 0.32, w * 0.58, h * 0.2, w * 0.7, h * 0.2);
                ctx.bezierCurveTo(w * 0.95, h * 0.2, w * 0.9, h * 0.55, w / 2, h * 0.82);
                ctx.closePath();
                ctx.fill();
            }
            else if (n === "equalizer" || n === "waveform") {
                // Animated / Static Equalizer Bars
                var barW = Math.max(1.5, w * 0.14);
                var gap = w * 0.09;
                var b1H = h * 0.45;
                var b2H = h * 0.75;
                var b3H = h * 0.55;
                var b4H = h * 0.35;
                var xStart = pad;

                ctx.fillRect(xStart, h - pad - b1H, barW, b1H);
                ctx.fillRect(xStart + barW + gap, h - pad - b2H, barW, b2H);
                ctx.fillRect(xStart + (barW + gap) * 2, h - pad - b3H, barW, b3H);
                ctx.fillRect(xStart + (barW + gap) * 3, h - pad - b4H, barW, b4H);
            }
            else if (n === "file-code") {
                // Document with code brackets
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.1, pad);
                ctx.lineTo(w - pad - w * 0.25, pad);
                ctx.lineTo(w - pad, pad + h * 0.25);
                ctx.lineTo(w - pad, h - pad);
                ctx.lineTo(pad + w * 0.1, h - pad);
                ctx.closePath();
                ctx.stroke();

                // Bracket < >
                ctx.beginPath();
                ctx.moveTo(w * 0.44, h * 0.45);
                ctx.lineTo(w * 0.34, h * 0.58);
                ctx.lineTo(w * 0.44, h * 0.71);
                ctx.moveTo(w * 0.56, h * 0.45);
                ctx.lineTo(w * 0.66, h * 0.58);
                ctx.lineTo(w * 0.56, h * 0.71);
                ctx.stroke();
            }
            else if (n === "file-image") {
                // Document with mountain and sun
                ctx.beginPath();
                ctx.rect(pad, pad * 1.1, w - pad * 2, h - pad * 2.2);
                ctx.stroke();
                // Sun
                ctx.beginPath();
                ctx.arc(pad + (w - pad * 2) * 0.3, pad * 1.1 + (h - pad * 2.2) * 0.3, w * 0.1, 0, Math.PI * 2);
                ctx.fill();
                // Mountain
                ctx.beginPath();
                ctx.moveTo(pad, h - pad * 1.1);
                ctx.lineTo(pad + (w - pad * 2) * 0.45, pad * 1.1 + (h - pad * 2.2) * 0.45);
                ctx.lineTo(pad + (w - pad * 2) * 0.7, pad * 1.1 + (h - pad * 2.2) * 0.7);
                ctx.lineTo(pad + (w - pad * 2) * 0.85, pad * 1.1 + (h - pad * 2.2) * 0.55);
                ctx.lineTo(w - pad, h - pad * 1.1);
                ctx.stroke();
            }
            else if (n === "file-audio" || n === "file-music") {
                // Document with musical note
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.1, pad);
                ctx.lineTo(w - pad - w * 0.25, pad);
                ctx.lineTo(w - pad, pad + h * 0.25);
                ctx.lineTo(w - pad, h - pad);
                ctx.lineTo(pad + w * 0.1, h - pad);
                ctx.closePath();
                ctx.stroke();
                // Note
                ctx.beginPath();
                ctx.arc(w * 0.42, h * 0.68, w * 0.1, 0, Math.PI * 2);
                ctx.fill();
                ctx.beginPath();
                ctx.moveTo(w * 0.52, h * 0.68);
                ctx.lineTo(w * 0.52, h * 0.42);
                ctx.lineTo(w * 0.68, h * 0.36);
                ctx.lineTo(w * 0.68, h * 0.52);
                ctx.stroke();
            }
            else if (n === "file-binary" || n === "file-exe") {
                // Binary / Terminal file
                ctx.beginPath();
                ctx.rect(pad, pad * 1.1, w - pad * 2, h - pad * 2.2);
                ctx.stroke();
                // Prompt >_
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.15, pad * 1.1 + h * 0.25);
                ctx.lineTo(pad + w * 0.35, pad * 1.1 + h * 0.4);
                ctx.lineTo(pad + w * 0.15, pad * 1.1 + h * 0.55);
                ctx.moveTo(pad + w * 0.42, pad * 1.1 + h * 0.55);
                ctx.lineTo(pad + w * 0.65, pad * 1.1 + h * 0.55);
                ctx.stroke();
            }
            else if (n === "file-archive" || n === "file-zip") {
                // Zip file
                ctx.beginPath();
                ctx.moveTo(pad + w * 0.1, pad);
                ctx.lineTo(w - pad - w * 0.25, pad);
                ctx.lineTo(w - pad, pad + h * 0.25);
                ctx.lineTo(w - pad, h - pad);
                ctx.lineTo(pad + w * 0.1, h - pad);
                ctx.closePath();
                ctx.stroke();
                // Zipper teeth
                for (var zY = pad + h * 0.15; zY <= h - pad * 1.5; zY += h * 0.12) {
                    ctx.fillRect(w * 0.45, zY, w * 0.1, h * 0.05);
                }
            }
            else {
                // Default bullet/dot
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, w * 0.2, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }

    onColorChanged: canvas.requestPaint()
    onNameChanged: canvas.requestPaint()
    onSizeChanged: canvas.requestPaint()
}
