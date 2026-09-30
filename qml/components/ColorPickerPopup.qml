import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property color selectedColor: "#0078d4"
    property real hueVal: 0.58
    property real satVal: 1.0
    property real valVal: 0.83
    property int targetStart: -1
    property int targetEnd: -1

    signal colorChosen(string hexColor)
    signal closeRequested()

    width: 250
    height: 290
    radius: theme ? theme.radiusMd : 6
    color: theme ? theme.bgPopup : "#252526"
    border.color: theme ? theme.borderNormal : "#333333"
    border.width: 1
    clip: true

    function openAtColor(hex) {
        if (hex) {
            root.selectedColor = hex;
            hexField.text = hex.toUpperCase();
        }
    }

    function hsvToRgb(h, s, v) {
        var r, g, b;
        var i = Math.floor(h * 6);
        var f = h * 6 - i;
        var p = v * (1 - s);
        var q = v * (1 - f * s);
        var t = v * (1 - (1 - f) * s);
        switch (i % 6) {
            case 0: r = v; g = t; b = p; break;
            case 1: r = q; g = v; b = p; break;
            case 2: r = p; g = v; b = t; break;
            case 3: r = p; g = q; b = v; break;
            case 4: r = t; g = p; b = v; break;
            case 5: r = v; g = p; b = q; break;
        }
        var toHex = function(c) {
            var hex = Math.round(c * 255).toString(16);
            return hex.length === 1 ? "0" + hex : hex;
        };
        return "#" + toHex(r) + toHex(g) + toHex(b);
    }

    function updateFromHsv() {
        var hex = hsvToRgb(root.hueVal, root.satVal, root.valVal);
        root.selectedColor = hex;
        hexField.text = hex.toUpperCase();
        root.colorChosen(hex);
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        // Header Title & Close
        RowLayout {
            Layout.fillWidth: true

            VectorIcon {
                name: "sparkles"
                size: 12
                color: root.selectedColor
            }

            Text {
                text: "Color Picker"
                color: theme ? theme.textBright : "#ffffff"
                font.pixelSize: 11
                font.bold: true
                Layout.fillWidth: true
            }

            Rectangle {
                width: 18
                height: 18
                radius: 2
                color: closeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#37373d") : "transparent"

                VectorIcon {
                    anchors.centerIn: parent
                    name: "close"
                    size: 8
                    color: theme ? theme.textSecondary : "#858585"
                }

                MouseArea {
                    id: closeMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.closeRequested()
                }
            }
        }

        // Saturation / Value 2D Gradient Box
        Rectangle {
            id: satBox
            Layout.fillWidth: true
            height: 110
            radius: 4
            clip: true

            Canvas {
                id: satCanvas
                anchors.fill: parent

                onPaint: {
                    var ctx = getContext("2d");
                    ctx.reset();
                    ctx.clearRect(0, 0, width, height);

                    // Base pure hue color
                    var baseHueRgb = root.hsvToRgb(root.hueVal, 1.0, 1.0);
                    ctx.fillStyle = baseHueRgb;
                    ctx.fillRect(0, 0, width, height);

                    // Horizontal white gradient (saturation)
                    var whiteGrad = ctx.createLinearGradient(0, 0, width, 0);
                    whiteGrad.addColorStop(0.0, "rgba(255,255,255,1)");
                    whiteGrad.addColorStop(1.0, "rgba(255,255,255,0)");
                    ctx.fillStyle = whiteGrad;
                    ctx.fillRect(0, 0, width, height);

                    // Vertical black gradient (value/brightness)
                    var blackGrad = ctx.createLinearGradient(0, 0, 0, height);
                    blackGrad.addColorStop(0.0, "rgba(0,0,0,0)");
                    blackGrad.addColorStop(1.0, "rgba(0,0,0,1)");
                    ctx.fillStyle = blackGrad;
                    ctx.fillRect(0, 0, width, height);
                }
            }

            // Picker reticle indicator
            Rectangle {
                width: 12
                height: 12
                radius: 6
                x: Math.max(0, Math.min(satBox.width - 12, root.satVal * satBox.width - 6))
                y: Math.max(0, Math.min(satBox.height - 12, (1.0 - root.valVal) * satBox.height - 6))
                color: root.selectedColor
                border.color: "#ffffff"
                border.width: 2
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.CrossCursor

                function updateSatVal(mouse) {
                    root.satVal = Math.max(0.0, Math.min(1.0, mouse.x / satBox.width));
                    root.valVal = Math.max(0.0, Math.min(1.0, 1.0 - (mouse.y / satBox.height)));
                    root.updateFromHsv();
                }

                onPressed: function(mouse) { updateSatVal(mouse); }
                onPositionChanged: function(mouse) { if (pressed) updateSatVal(mouse); }
            }
        }

        // 1D Rainbow Hue Slider
        Rectangle {
            id: hueSlider
            Layout.fillWidth: true
            height: 14
            radius: 7
            clip: true

            Canvas {
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d");
                    var grad = ctx.createLinearGradient(0, 0, width, 0);
                    grad.addColorStop(0.0, "#ff0000");
                    grad.addColorStop(0.17, "#ffff00");
                    grad.addColorStop(0.33, "#00ff00");
                    grad.addColorStop(0.50, "#00ffff");
                    grad.addColorStop(0.67, "#0000ff");
                    grad.addColorStop(0.83, "#ff00ff");
                    grad.addColorStop(1.0, "#ff0000");
                    ctx.fillStyle = grad;
                    ctx.fillRect(0, 0, width, height);
                }
            }

            Rectangle {
                width: 12
                height: 14
                radius: 3
                x: Math.max(0, Math.min(hueSlider.width - 12, root.hueVal * hueSlider.width - 6))
                color: "#ffffff"
                border.color: "#333333"
                border.width: 1
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor

                function updateHue(mouse) {
                    root.hueVal = Math.max(0.0, Math.min(1.0, mouse.x / hueSlider.width));
                    satCanvas.requestPaint();
                    root.updateFromHsv();
                }

                onPressed: function(mouse) { updateHue(mouse); }
                onPositionChanged: function(mouse) { if (pressed) updateHue(mouse); }
            }
        }

        // Preview Swatch + Hex Input
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Rectangle {
                width: 28
                height: 24
                radius: 4
                color: root.selectedColor
                border.color: "#ffffff30"
                border.width: 1
            }

            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 3
                color: theme ? theme.bgInput : "#181818"
                border.color: theme ? theme.borderSubtle : "#333333"

                TextInput {
                    id: hexField
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    verticalAlignment: TextInput.AlignVCenter
                    text: root.selectedColor.toString().toUpperCase()
                    color: theme ? theme.textBright : "#ffffff"
                    font.pixelSize: 11
                    font.family: theme ? theme.fontFamilyMono : "monospace"
                    selectByMouse: true

                    onAccepted: {
                        if (text.startsWith("#") && (text.length === 7 || text.length === 4)) {
                            root.selectedColor = text;
                            root.colorChosen(text);
                        }
                    }
                }
            }
        }

        // Quick Swatches Palette
        Row {
            Layout.alignment: Qt.AlignHCenter
            spacing: 5

            Repeater {
                model: ["#0078d4", "#4ec9b0", "#cca700", "#f14c4c", "#a855f7", "#22c55e", "#ec4899", "#ffffff", "#1e1e1e"]
                delegate: Rectangle {
                    width: 16
                    height: 16
                    radius: 8
                    color: modelData
                    border.color: root.selectedColor.toString().toLowerCase() === modelData.toLowerCase() ? "#ffffff" : "#00000040"
                    border.width: root.selectedColor.toString().toLowerCase() === modelData.toLowerCase() ? 2 : 1

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.selectedColor = modelData;
                            hexField.text = modelData.toUpperCase();
                            root.colorChosen(modelData);
                        }
                    }
                }
            }
        }
    }
}
