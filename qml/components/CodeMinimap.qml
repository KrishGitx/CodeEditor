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
        renderTarget: Canvas.Image

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.clearRect(0, 0, width, height);

            if (!root.documentText || root.documentText.length === 0) return;

            var lines = root.documentText.split("\n");
            var lineCount = Math.max(1, lines.length);
            var lineHeight = Math.max(1.5, Math.min(6.0, height / lineCount));
            var maxDraw = Math.min(lineCount, Math.floor(height / lineHeight));

            for (var i = 0; i < maxDraw; i++) {
                var lineStr = lines[i] || "";
                var trimmed = lineStr.trim();
                if (trimmed.length > 0) {
                    var indent = lineStr.search(/\S/);
                    if (indent < 0) indent = 0;

                    var startX = Math.min(width * 0.6, Math.max(3, indent * 2));
                    var barWidth = Math.min(width - startX - 4, Math.max(4, trimmed.length * 0.85));
                    var y = i * lineHeight;

                    // Syntax-like color encoding
                    if (/^(def |class |function |const |let |var |import |from |package |public |private )/.test(trimmed)) {
                        ctx.fillStyle = theme ? theme.synKeyword : "#569cd6";
                    } else if (/\(.*\)/.test(trimmed)) {
                        ctx.fillStyle = theme ? theme.synFunction : "#dcdcaa";
                    } else if (/^(\/\/|#|\/\*|\*)/.test(trimmed)) {
                        ctx.fillStyle = theme ? theme.synComment : "#6a9955";
                    } else if (/^(\{|\}|\(|\)|\[|\])/.test(trimmed)) {
                        ctx.fillStyle = theme ? theme.synType : "#4ec9b0";
                    } else {
                        ctx.fillStyle = theme ? theme.textDisabled : "#4d4d4d";
                    }

                    ctx.fillRect(startX, y, barWidth, Math.max(1, lineHeight - 0.5));
                }
            }
        }
    }

    onDocumentTextChanged: minimapCanvas.requestPaint()
    onWidthChanged: minimapCanvas.requestPaint()
    onHeightChanged: minimapCanvas.requestPaint()
    Component.onCompleted: minimapCanvas.requestPaint()

    // Highlighted Viewport Box Indicator
    Rectangle {
        id: viewportBox
        x: 0
        y: Math.max(0, Math.min(root.height - height, root.scrollRatio * (root.height - height)))
        width: parent.width
        height: Math.max(24, Math.min(root.height, root.visibleRatio * root.height))
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
