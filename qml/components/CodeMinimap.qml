import QtQuick 2.15

Rectangle {
    id: root

    property string documentText: ""
    property real visibleRatio: 0.2
    property real scrollRatio: 0.0

    signal scrollRequested(real ratio)

    width: 64
    color: theme ? theme.bgSidebar : "#181818"

    Canvas {
        id: minimapCanvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            var text = root.documentText;
            if (!text || text.length === 0) return;

            var lines = text.split("\n");
            var lineCount = Math.max(1, lines.length);

            // Cap max bars rendered on canvas to at most 300 for instant 60fps rendering
            var maxBars = Math.min(300, Math.max(1, Math.floor(height / 2.2)));
            var step = lineCount / maxBars;
            var barHeight = Math.max(1.2, Math.min(3.5, height / maxBars));

            var kwColor = theme ? theme.synKeyword : "#569cd6";
            var fnColor = theme ? theme.synFunction : "#dcdcaa";
            var comColor = theme ? theme.synComment : "#6a9955";
            var strColor = theme ? theme.synString : "#ce9178";
            var typeColor = theme ? theme.synType : "#4ec9b0";
            var defaultColor = theme ? theme.textDisabled : "#4d4d4d";

            for (var b = 0; b < maxBars; b++) {
                var lineIdx = Math.floor(b * step);
                if (lineIdx >= lineCount) break;

                var lineStr = lines[lineIdx] || "";
                var trimmed = lineStr.trim();
                if (trimmed.length > 0) {
                    var indent = 0;
                    while (indent < lineStr.length && (lineStr.charAt(indent) === ' ' || lineStr.charAt(indent) === '\t')) {
                        indent++;
                    }

                    var startX = Math.min(width * 0.55, Math.max(3, indent * 1.8));
                    var barWidth = Math.min(width - startX - 4, Math.max(3, trimmed.length * 0.7));
                    var y = b * (height / maxBars);

                    var firstChar = trimmed.charAt(0);
                    if (firstChar === '#' || (firstChar === '/' && trimmed.length > 1 && trimmed.charAt(1) === '/')) {
                        ctx.fillStyle = comColor;
                    } else if (firstChar === '"' || firstChar === "'" || firstChar === '`') {
                        ctx.fillStyle = strColor;
                    } else if (trimmed.startsWith("def ") || trimmed.startsWith("class ") || trimmed.startsWith("function ") ||
                               trimmed.startsWith("const ") || trimmed.startsWith("import ") || trimmed.startsWith("from ") ||
                               trimmed.startsWith("return ") || trimmed.startsWith("var ") || trimmed.startsWith("let ") ||
                               trimmed.startsWith("property ") || trimmed.startsWith("if ") || trimmed.startsWith("for ")) {
                        ctx.fillStyle = kwColor;
                    } else if (trimmed.indexOf("(") !== -1) {
                        ctx.fillStyle = fnColor;
                    } else if (firstChar === '{' || firstChar === '}' || firstChar === '[' || firstChar === ']') {
                        ctx.fillStyle = typeColor;
                    } else {
                        ctx.fillStyle = defaultColor;
                    }

                    ctx.fillRect(startX, y, barWidth, Math.max(1.0, barHeight - 0.4));
                }
            }
        }
    }

    Timer {
        id: paintDebounceTimer
        interval: 100
        repeat: false
        onTriggered: minimapCanvas.requestPaint()
    }

    onDocumentTextChanged: paintDebounceTimer.restart()
    onWidthChanged: minimapCanvas.requestPaint()
    onHeightChanged: minimapCanvas.requestPaint()
    Component.onCompleted: paintDebounceTimer.restart()

    // Highlighted Viewport Box Indicator
    Rectangle {
        id: viewportBox
        x: 0
        y: Math.max(0, Math.min(root.height - height, root.scrollRatio * (root.height - height)))
        width: parent.width
        height: Math.max(20, Math.min(root.height, root.visibleRatio * root.height))
        color: theme ? theme.accentMuted : "#0078d420"
        border.color: theme ? theme.borderNormal : "#333333"
        border.width: 1
        opacity: mapArea.containsMouse || mapArea.pressed ? 0.9 : 0.55

        Behavior on opacity {
            NumberAnimation { duration: 100 }
        }
    }

    MouseArea {
        id: mapArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor

        onPressed: function(mouse) {
            updateScroll(mouse.y);
        }

        onPositionChanged: function(mouse) {
            if (pressed) {
                updateScroll(mouse.y);
            }
        }

        function updateScroll(mouseY) {
            var halfBox = viewportBox.height / 2;
            var availableH = root.height - viewportBox.height;
            if (availableH <= 0) return;

            var targetY = mouseY - halfBox;
            var ratio = Math.max(0.0, Math.min(1.0, targetY / availableH));
            root.scrollRequested(ratio);
        }
    }
}
