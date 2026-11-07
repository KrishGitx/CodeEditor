import QtQuick 2.15

Rectangle {
    id: root

    property string documentText: ""
    property string activeTabKey: ""
    property real visibleRatio: 0.2
    property real scrollRatio: 0.0

    signal scrollRequested(real ratio)
    signal scrollFinished()
    property bool isDragging: false

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
        var hasValidText = (text !== undefined && text !== null && typeof text === "string" && text.length > 0);
        if (hasValidText) {
            documentText = text;
        }

        // Only use cache if it actually contains populated lines
        if (tabCache[activeTabKey] && tabCache[activeTabKey].lines && tabCache[activeTabKey].lines.length > 0) {
            var cached = tabCache[activeTabKey];
            currentLines = cached.lines;
            if (cached.totalLineCount > 1) {
                totalLineCount = cached.totalLineCount;
            }
            minimapCanvas.requestPaint();
        } else if (hasValidText) {
            // Build cache immediately so the minimap code text appears with zero perceptible delay
            rebuildCache();
        }
    }

    function rebuildCache() {
        console.log("[Timing] Minimap generation start");
        var text = root.documentText;
        var key = root.activeTabKey || "default";

        if (!text || text.length === 0) {
            // If we already have valid lines for this key, preserve them instead of clobbering with empty array
            if (tabCache[key] && tabCache[key].lines && tabCache[key].lines.length > 0) {
                currentLines = tabCache[key].lines;
                totalLineCount = Math.max(root.totalLineCount, tabCache[key].totalLineCount);
                minimapCanvas.requestPaint();
                return;
            }
            currentLines = [];
            totalLineCount = Math.max(1, root.totalLineCount);
            minimapCanvas.requestPaint();
            console.log("[Timing] Minimap generation complete");
            return;
        }

        var rawLines = text.split("\n");
        var docLines = rawLines.length;
        totalLineCount = Math.max(1, docLines);

        var linesData = new Array(docLines);
        var maxCharsPerLine = 45;

        for (var i = 0; i < docLines; i++) {
            var line = rawLines[i];
            if (!line || line.length === 0) {
                linesData[i] = null;
                continue;
            }

            var indent = 0;
            var len = line.length;
            while (indent < len && (line.charCodeAt(indent) === 32 || line.charCodeAt(indent) === 9)) {
                indent += (line.charCodeAt(indent) === 9 ? 4 : 1);
            }

            var trimmed = line.substring(indent, Math.min(len, indent + maxCharsPerLine));
            if (trimmed.length === 0) {
                linesData[i] = null;
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

            linesData[i] = {
                indent: Math.min(24, indent),
                text: trimmed,
                colorType: colorType
            };
        }

        currentLines = linesData;
        tabCache[key] = { lines: linesData, totalLineCount: totalLineCount };
        if (minimapCanvas.available) {
            minimapCanvas.requestPaint();
        }
        console.log("[Timing] Minimap generation complete");
    }

    Timer {
        id: parseDebounceTimer
        interval: 80
        repeat: false
        onTriggered: root.rebuildCache()
    }

    onDocumentTextChanged: {
        if (!currentLines || currentLines.length === 0) {
            root.rebuildCache();
        } else {
            parseDebounceTimer.restart();
        }
    }

    Canvas {
        id: minimapCanvas
        anchors.fill: parent

        onAvailableChanged: {
            if (available) requestPaint();
        }

        Connections {
            target: root
            function onCurrentLinesChanged() {
                if (minimapCanvas.available) minimapCanvas.requestPaint();
            }
        }

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
    onWidthChanged: {
        if (width > 0 && height > 0) {
            if ((!currentLines || currentLines.length === 0) && documentText && documentText.length > 0) {
                rebuildCache();
            } else {
                minimapCanvas.requestPaint();
            }
        }
    }
    onHeightChanged: {
        if (width > 0 && height > 0) {
            if ((!currentLines || currentLines.length === 0) && documentText && documentText.length > 0) {
                rebuildCache();
            } else {
                minimapCanvas.requestPaint();
            }
        }
    }

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
        color: mapArea.containsMouse || mapArea.pressed ? Qt.rgba(1.0, 1.0, 1.0, 0.16) : Qt.rgba(1.0, 1.0, 1.0, 0.08)
        border.color: mapArea.containsMouse || mapArea.pressed ? Qt.rgba(1.0, 1.0, 1.0, 0.35) : Qt.rgba(1.0, 1.0, 1.0, 0.18)
        border.width: 1
    }

    MouseArea {
        id: mapArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor

        onPressed: function(mouse) {
            root.isDragging = true;
            updateScroll(mouse.y);
        }

        onPositionChanged: function(mouse) {
            if (pressed) {
                root.isDragging = true;
                updateScroll(mouse.y);
            }
        }

        onReleased: function(mouse) {
            root.isDragging = false;
            updateScroll(mouse.y);
            root.scrollFinished();
        }

        onCanceled: function() {
            root.isDragging = false;
            root.scrollFinished();
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
