import QtQuick 2.15

Rectangle {
    id: root

    property string documentText: ""
    property real visibleRatio: 0.2
    property real scrollRatio: 0.0

    signal scrollRequested(real ratio)

    width: 64
    color: (typeof theme !== "undefined" && theme && theme.bgSidebar) ? theme.bgSidebar : "#18181b"

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

            var kwColor = (typeof theme !== "undefined" && theme && theme.synKeyword) ? theme.synKeyword : "#569cd6";
            var fnColor = (typeof theme !== "undefined" && theme && theme.synFunction) ? theme.synFunction : "#dcdcaa";
            var comColor = (typeof theme !== "undefined" && theme && theme.synComment) ? theme.synComment : "#6a9955";
            var strColor = (typeof theme !== "undefined" && theme && theme.synString) ? theme.synString : "#ce9178";
            var defaultColor = (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#52525b";

            var totalH = height;
            var numLinesToRender = Math.min(lineCount, Math.floor(totalH / 2.0));
            var step = lineCount / numLinesToRender;
            var lineH = Math.max(1.2, Math.min(2.8, totalH / numLinesToRender));

            for (var i = 0; i < numLinesToRender; i++) {
                var lIdx = Math.floor(i * step);
                if (lIdx >= lineCount) break;

                var lineStr = lines[lIdx] || "";
                if (lineStr.trim().length === 0) continue;

                var indent = 0;
                while (indent < lineStr.length && (lineStr.charAt(indent) === ' ' || lineStr.charAt(indent) === '\t')) {
                    indent += (lineStr.charAt(indent) === '\t' ? 4 : 1);
                }

                var startX = Math.min(width * 0.5, Math.max(2, indent * 1.5));
                var y = i * (totalH / numLinesToRender);

                var trimmed = lineStr.trim();
                var firstChar = trimmed.charAt(0);

                if (firstChar === '#' || (firstChar === '/' && trimmed.length > 1 && trimmed.charAt(1) === '/')) {
                    ctx.fillStyle = comColor;
                    var barW = Math.min(width - startX - 2, Math.max(4, trimmed.length * 0.7));
                    ctx.fillRect(startX, y, barW, lineH);
                } else if (firstChar === '"' || firstChar === "'" || firstChar === '`') {
                    ctx.fillStyle = strColor;
                    var barW = Math.min(width - startX - 2, Math.max(4, trimmed.length * 0.7));
                    ctx.fillRect(startX, y, barW, lineH);
                } else {
                    // Render multi-word token chunks for realistic code appearance
                    var tokens = trimmed.split(/(\s+|[(),.:;={}[\]<>]+)/).filter(function(t) { return t.length > 0; });
                    var curX = startX;

                    for (var t = 0; t < tokens.length; t++) {
                        var tok = tokens[t];
                        if (tok.trim().length === 0) {
                            curX += Math.max(2, tok.length * 1.2);
                            continue;
                        }

                        if (tok === "def" || tok === "class" || tok === "function" || tok === "const" ||
                            tok === "let" || tok === "var" || tok === "if" || tok === "else" ||
                            tok === "for" || tok === "while" || tok === "return" || tok === "import" ||
                            tok === "from" || tok === "export" || tok === "property" || tok === "Item" ||
                            tok === "Rectangle") {
                            ctx.fillStyle = kwColor;
                        } else if (tok.startsWith('"') || tok.startsWith("'") || tok.startsWith('`')) {
                            ctx.fillStyle = strColor;
                        } else if (t + 1 < tokens.length && (tokens[t + 1] === "(" || tokens[t + 1] === ":")) {
                            ctx.fillStyle = fnColor;
                        } else {
                            ctx.fillStyle = defaultColor;
                        }

                        var tokW = Math.min(width - curX - 2, Math.max(2, tok.length * 0.75));
                        if (tokW > 0 && curX < width - 2) {
                            ctx.fillRect(curX, y, tokW, lineH);
                        }
                        curX += tokW + 1.5;
                        if (curX >= width - 2) break;
                    }
                }
            }
        }
    }

    Timer {
        id: paintDebounceTimer
        interval: 60
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
        height: Math.max(16, Math.min(root.height, root.visibleRatio * root.height))
        color: (typeof theme !== "undefined" && theme && theme.accentMuted) ? theme.accentMuted : "#3b82f615"
        border.color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#3f3f46"
        border.width: 1
        opacity: mapArea.containsMouse || mapArea.pressed ? 0.85 : 0.45

        Behavior on opacity {
            NumberAnimation { duration: 80 }
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
