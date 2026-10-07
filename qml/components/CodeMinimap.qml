import QtQuick 2.15

Rectangle {
    id: root

    property string documentText: ""
    property string activeTabKey: ""
    property real visibleRatio: 0.2
    property real scrollRatio: 0.0

    signal scrollRequested(real ratio)

    width: 90
    color: (typeof theme !== "undefined" && theme && theme.bgSidebar) ? theme.bgSidebar : "#18181b"
    clip: true

    readonly property real lineSpacing: 4.8
    readonly property real charScale: 2.7
    readonly property real topOffset: 6.0

    property int totalLineCount: 1
    readonly property real totalMinimapDocHeight: topOffset + (totalLineCount * lineSpacing) + 20
    readonly property bool needsMinimapScroll: totalMinimapDocHeight > height
    readonly property real maxMinimapScrollY: Math.max(0, totalMinimapDocHeight - height)
    readonly property real currentMinimapScrollY: needsMinimapScroll ? (root.scrollRatio * maxMinimapScrollY) : 0

    // Per-tab cache mapping tab key -> { lines: [], totalLineCount: int }
    property var tabCache: ({})
    property var currentLines: []

    function setTabAndText(tabKey, text) {
        activeTabKey = tabKey || "default";
        if (text && text.length > 0) {
            documentText = text;
        }
        if (tabCache[activeTabKey]) {
            var cached = tabCache[activeTabKey];
            currentLines = cached.lines;
            if (cached.totalLineCount > 1) {
                totalLineCount = cached.totalLineCount;
            }
            minimapCanvas.requestPaint();
        } else if (text && text.length > 0) {
            parseDebounceTimer.restart();
        }
    }

    function rebuildCache() {
        console.log("[Timing] Minimap generation start");
        var text = root.documentText;
        var key = root.activeTabKey || "default";

        if (!text || text.length === 0) {
            if (!tabCache[key] || tabCache[key].lines.length === 0) {
                currentLines = [];
                totalLineCount = Math.max(1, root.totalLineCount);
                tabCache[key] = { lines: [], totalLineCount: totalLineCount };
                minimapCanvas.requestPaint();
            }
            console.log("[Timing] Minimap generation complete");
            return;
        }

        var rawLines = text.split("\n");
        var docLines = rawLines.length;
        totalLineCount = Math.max(root.totalLineCount, docLines);

        var linesData = [];
        var maxCharsPerLine = 45;

        for (var i = 0; i < docLines; i++) {
            var line = rawLines[i];
            if (!line || line.length === 0) {
                linesData.push(null);
                continue;
            }

            var indent = 0;
            var len = line.length;
            while (indent < len && (line.charCodeAt(indent) === 32 || line.charCodeAt(indent) === 9)) {
                indent += (line.charCodeAt(indent) === 9 ? 4 : 1);
            }

            var trimmed = line.substring(indent, Math.min(len, indent + maxCharsPerLine));
            if (trimmed.length === 0) {
                linesData.push(null);
                continue;
            }

            // Syntax color classification for accurate miniature code text
            var colorType = 0;
            var firstChar = trimmed.charAt(0);
            if (firstChar === '#' || trimmed.startsWith("//") || trimmed.startsWith("/*") || trimmed.startsWith("*")) {
                colorType = 1; // comment
            } else if (firstChar === '"' || firstChar === "'" || firstChar === '`') {
                colorType = 2; // string
            } else if (firstChar === '<' || firstChar === '@') {
                colorType = 3; // keyword / tag
            } else {
                var spaceIdx = trimmed.indexOf(" ");
                var token = (spaceIdx !== -1) ? trimmed.substring(0, spaceIdx) : trimmed;
                if (token === "def" || token === "class" || token === "function" ||
                    token === "const" || token === "let" || token === "var" ||
                    token === "if" || token === "for" || token === "while" ||
                    token === "return" || token === "import" || token === "export" ||
                    token === "public" || token === "private" || token === "int" ||
                    token === "void" || token === "bool" || token === "struct") {
                    colorType = 3;
                }
            }

            linesData.push({
                indent: Math.min(24, indent),
                text: trimmed,
                colorType: colorType
            });
        }

        currentLines = linesData;
        tabCache[key] = { lines: linesData, totalLineCount: totalLineCount };
        minimapCanvas.requestPaint();
        console.log("[Timing] Minimap generation complete");
    }

    Timer {
        id: parseDebounceTimer
        interval: 100
        repeat: false
        onTriggered: root.rebuildCache()
    }

    onDocumentTextChanged: parseDebounceTimer.restart()

    Canvas {
        id: minimapCanvas
        anchors.fill: parent

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            var lines = root.currentLines;
            var count = lines ? lines.length : 0;
            if (count === 0) return;

            var kwColor = (typeof theme !== "undefined" && theme && theme.synKeyword) ? theme.synKeyword : "#c678dd";
            var comColor = (typeof theme !== "undefined" && theme && theme.synComment) ? theme.synComment : "#5c6478";
            var strColor = (typeof theme !== "undefined" && theme && theme.synString) ? theme.synString : "#98c379";
            var defColor = (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#8b949e";

            var colors = [defColor, comColor, strColor, kwColor];

            ctx.font = "4.5px 'Consolas', 'Courier New', monospace";
            ctx.textBaseline = "top";

            var scrollOffY = root.currentMinimapScrollY;
            var startIdx = Math.max(0, Math.floor((scrollOffY - 10) / root.lineSpacing));
            var endIdx = Math.min(count - 1, Math.ceil((scrollOffY + height + 10) / root.lineSpacing));

            var maxDrawX = width - 4;

            for (var i = startIdx; i <= endIdx; i++) {
                var lData = lines[i];
                if (!lData) continue;

                var y = root.topOffset + (i * root.lineSpacing) - scrollOffY;
                if (y < -6 || y > height + 6) continue;

                var startX = Math.max(2, Math.min(maxDrawX - 10, lData.indent * root.charScale));
                ctx.fillStyle = colors[lData.colorType] || defColor;
                ctx.fillText(lData.text, startX, y);
            }
        }
    }

    Timer {
        id: paintDebounceTimer
        interval: 16
        repeat: false
        onTriggered: minimapCanvas.requestPaint()
    }

    onScrollRatioChanged: paintDebounceTimer.restart()
    onVisibleRatioChanged: paintDebounceTimer.restart()
    onWidthChanged: minimapCanvas.requestPaint()
    onHeightChanged: minimapCanvas.requestPaint()

    // Viewport Range Indicator Box
    Rectangle {
        id: viewportBox
        x: 0
        y: {
            if (root.needsMinimapScroll) {
                var availH = root.height - height;
                return Math.max(0, Math.min(availH, root.scrollRatio * availH));
            } else {
                var docH = Math.min(root.height, root.totalMinimapDocHeight);
                var availDocH = docH - height;
                if (availDocH <= 0) return root.topOffset;
                return root.topOffset + Math.max(0, Math.min(availDocH, root.scrollRatio * availDocH));
            }
        }
        width: parent.width
        height: {
            var totalH = root.needsMinimapScroll ? root.height : Math.min(root.height, root.totalMinimapDocHeight);
            return Math.max(18, Math.min(totalH, root.visibleRatio * totalH));
        }
        color: (typeof theme !== "undefined" && theme && theme.accentMuted) ? theme.accentMuted : "#38bdf818"
        border.color: (typeof theme !== "undefined" && theme && theme.accent) ? theme.accent : "#38bdf8"
        border.width: 1
        opacity: mapArea.containsMouse || mapArea.pressed ? 0.9 : 0.55

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
            var availH = root.height - viewportBox.height;
            if (availH <= 0) return;

            var halfBox = viewportBox.height / 2;
            var targetY = mouseY - halfBox;
            var ratio = Math.max(0.0, Math.min(1.0, targetY / availH));
            root.scrollRequested(ratio);
        }
    }
}
