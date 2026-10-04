import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "LanguageRegistry.js" as LanguageRegistry
import "SnippetManager.js" as SnippetManager
import "."

Item {
    id: root

    // Tab and Document Model
    ListModel {
        id: tabModel
    }

    property int activeTabIndex: -1
    property alias tabCount: tabModel.count
    readonly property var currentTab: (activeTabIndex >= 0 && tabModel.count > activeTabIndex) ? tabModel.get(activeTabIndex) : null
    property string activeFilePath: currentTab ? (currentTab.path || "") : ""
    property string activeFileName: currentTab ? (currentTab.title || "") : ""
    property bool isCurrentFileDirty: currentTab ? (currentTab.isDirty || false) : false
    property string currentLanguage: currentTab ? (currentTab.languageName || "Plain Text") : "Plain Text"
    property string currentLanguageId: currentTab ? (currentTab.languageId || "text") : "text"
    property var extraCursors: [] // Array of character indices for Multi-Cursor editing

    // Split Window / Dual Editor Properties
    property bool isSplitEditor: false
    property real splitRatio: 0.5
    property int secondaryTabIndex: -1
    readonly property var secondaryTab: (secondaryTabIndex >= 0 && tabModel.count > secondaryTabIndex) ? tabModel.get(secondaryTabIndex) : null
    property string secondaryLanguageId: secondaryTab ? (secondaryTab.languageId || "text") : "text"
    property int secondaryTotalLineCount: secondaryTab && secondaryTab.content ? Math.max(1, secondaryTab.content.split("\n").length) : 1

    Shortcut {
        sequence: "Ctrl+\\"
        onActivated: root.toggleSplitEditor()
    }

    // Cursor and Line Metrics
    // Active Tab Persistent Editor References
    readonly property var activeEditorPane: (tabEditorRepeater && activeTabIndex >= 0 && activeTabIndex < tabEditorRepeater.count) ? tabEditorRepeater.itemAt(activeTabIndex) : null
    readonly property var codeTextArea: activeEditorPane ? activeEditorPane.codeTextArea : null
    readonly property var editorFlickable: activeEditorPane ? activeEditorPane.editorFlickable : null
    readonly property var gutterFlickable: activeEditorPane ? activeEditorPane.gutterFlickable : null
    readonly property var indentGuidesCanvas: activeEditorPane ? activeEditorPane.indentGuidesCanvas : null

    property int cursorLine: 1
    property int cursorColumn: 1
    readonly property int totalLineCount: activeEditorPane ? activeEditorPane.paneTotalLineCount : (codeTextArea ? countLines(codeTextArea.text) : 1)
    property bool isFoldingOperation: false
    property bool isRestoringTab: false
    property bool isInitialTextLoading: false
    readonly property real editorLineHeight: fontMetrics.lineSpacing > 0 ? fontMetrics.lineSpacing : (fontMetrics.height > 0 ? fontMetrics.height : 18)
    readonly property real charWidth: fontMetrics.advanceWidth(" ") > 0 ? fontMetrics.advanceWidth(" ") : (fontMetrics.width(" ") > 0 ? fontMetrics.width(" ") : 8.0)
    readonly property var cachedIndentLevelWidths: {
        var tabSz = (typeof theme !== "undefined" && theme && theme.tabSize) ? theme.tabSize : 4;
        var arr = [0];
        for (var i = 1; i <= 32; i++) {
            arr.push(fontMetrics.advanceWidth(" ".repeat(i * tabSz)));
        }
        return arr;
    }
    property var foldableLinesMap: ({})
    property int scopeDocRevision: 0
    readonly property var activeScopeRanges: activeEditorPane ? activeEditorPane.paneScopeRanges : []

    function computeScopesForText(docText) {
        if (!docText) return [];
        var tabSize = (typeof theme !== "undefined" && theme && theme.tabSize) ? theme.tabSize : 4;
        var lines = docText.split("\n");
        var stack = [];
        var scopes = [];
        var total = lines.length;

        for (var l = 0; l < total; l++) {
            var line = lines[l];
            var trimmed = line.trim();
            var cols = 0;
            for (var i = 0; i < line.length; i++) {
                var ch = line.charAt(i);
                if (ch === ' ') {
                    cols += 1;
                } else if (ch === '\t') {
                    cols += tabSize - (cols % tabSize);
                } else {
                    break;
                }
            }
            var rawIndent = trimmed.length > 0 ? Math.floor(cols / tabSize) : -1;

            var inStr = false;
            var strQuote = '';
            for (var c = 0; c < line.length; c++) {
                var char = line.charAt(c);
                if (char === '/' && c + 1 < line.length && line.charAt(c + 1) === '/' && !inStr) {
                    break;
                }
                if (char === '"' || char === '\'' || char === '`') {
                    if (!inStr) { inStr = true; strQuote = char; }
                    else if (strQuote === char && (c === 0 || line.charAt(c - 1) !== '\\')) { inStr = false; }
                    continue;
                }
                if (inStr) continue;

                if (char === '{') {
                    var blockIndent = Math.max(0, rawIndent >= 0 ? rawIndent : 0);
                    stack.push({ startLine: l, level: blockIndent });
                } else if (char === '}') {
                    if (stack.length > 0) {
                        var top = stack.pop();
                        if (l > top.startLine) {
                            scopes.push({
                                startLine: top.startLine,
                                endLine: l,
                                level: top.level
                            });
                        }
                    }
                }
            }
        }
        return scopes;
    }

    function recomputeScopes(docText) {
        root.scopeDocRevision++;
        var scopes = computeScopesForText(docText || (root.codeTextArea ? root.codeTextArea.text : ""));
        if (root.activeEditorPane) {
            root.activeEditorPane.paneScopeRanges = scopes;
            if (root.activeEditorPane.indentGuidesCanvas) {
                root.activeEditorPane.indentGuidesCanvas.requestPaint();
            }
        }
    }

    Timer {
        id: foldAnalysisTimer
        interval: 800
        repeat: false
        onTriggered: {
            root.recalculateFoldableLines();
        }
    }

    // Signals for parent / status bar
    signal fileSaved(string path, bool success)
    signal activeFileChanged(string path, string name, string lang, bool dirty)
    signal cursorPositionChanged(int line, int col)
    signal requestOpenFile()
    signal requestOpenFolder()
    signal requestRunFile()

    signal askAi(string code)

    FontMetrics {
        id: fontMetrics
        font.family: (theme && theme.fontFamilyMono) ? theme.fontFamilyMono : "Consolas"
        font.pixelSize: theme ? theme.editorFontSize : 13
    }

    Component.onCompleted: {
        if (typeof backend !== "undefined" && backend && backend.register_text_area) {
            backend.register_text_area(codeTextArea);
        }
        updateCursorPosition();
    }

    // 1. Welcome Page (Visible when no tabs are open)
    WelcomePage {
        anchors.fill: parent
        visible: tabModel.count === 0
        z: 10

        onNewFileRequested: root.createNewFile()
        onOpenFileRequested: root.requestOpenFile()
        onOpenFolderRequested: root.requestOpenFolder()
    }

    // 2. Main Editor Workspace (Visible when at least 1 tab is open)
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        visible: tabModel.count > 0

        // Editor Tab Bar
        EditorTabBar {
            id: tabBar
            Layout.fillWidth: true
            tabModel: tabModel
            activeIndex: root.activeTabIndex
            isSplit: root.isSplitEditor

            onTabSelected: function(index) {
                root.switchToTab(index);
            }

            onTabClosed: function(index) {
                root.closeTab(index);
            }

            onNewTabRequested: function() {
                root.createNewFile();
            }

            onSplitEditorRequested: function() {
                root.toggleSplitEditor();
            }
        }

        // Editor Surface (Code Editor OR Whiteboard Canvas Tab, with optional Split Pane)
        Item {
            id: mainEditorSurface
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            RowLayout {
                anchors.fill: parent
                spacing: 0

                // 1. Primary Left Editor Container
                Item {
                    id: primaryEditorContainer
                    Layout.fillHeight: true
                    Layout.fillWidth: !root.isSplitEditor
                    Layout.preferredWidth: root.isSplitEditor ? Math.max(160, (mainEditorSurface.width - 2) * root.splitRatio) : -1
                    clip: true

                    // 1.1 Code Editor Surface (Visible for code files)
                    Item {
                        id: codeEditorContainer
                        anchors.fill: parent
                        visible: !root.currentTab || (!root.currentTab.isWhiteboard && !root.currentTab.isWebPreview && root.currentTab.languageId !== "webpreview")

                        Rectangle {
                            anchors.fill: parent
                            color: theme ? theme.bgEditor : "#1e1e1e"
                        }

                        RowLayout {
                            anchors.fill: parent
                            spacing: 0

                            StackLayout {
                                id: tabEditorStack
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                currentIndex: (root.activeTabIndex >= 0 && root.activeTabIndex < tabModel.count) ? root.activeTabIndex : 0

                                Repeater {
                                    id: tabEditorRepeater
                                    model: tabModel

                                    delegate: Item {
                                        id: tabPane
                                        property alias gutter: gutter
                                        property alias gutterFlickable: gutterFlickable
                                        property alias textAreaContainer: textAreaContainer
                                        property alias indentGuidesCanvas: indentGuidesCanvas
                                        property alias editorFlickable: editorFlickable
                                        property alias codeTextArea: codeTextArea
                                        property alias currentLineHighlight: currentLineHighlight
                                        property int paneTotalLineCount: countLines(codeTextArea.text)
                                        property var paneScopeRanges: []

                                        function updatePaneScopes() {
                                            paneScopeRanges = root.computeScopesForText(codeTextArea.text);
                                            indentGuidesCanvas.requestPaint();
                                        }

                                        RowLayout {
                                            anchors.fill: parent
                                            spacing: 0

                                            // Line Numbers Gutter (Virtualized for high performance on large files)
                                            Rectangle {
                                                id: gutter
                                                Layout.preferredWidth: Math.max(48, (tabPane.paneTotalLineCount.toString().length * 8 + 30))
                                                Layout.fillHeight: true
                                                color: theme ? theme.bgPanel : "#181818"
                                                visible: theme ? theme.enableLineNumbers : true
                                                clip: true

                                                readonly property int visibleStartLine: Math.max(0, Math.floor(gutterFlickable.contentY / root.editorLineHeight))
                                                readonly property int visibleLineCount: Math.min(tabPane.paneTotalLineCount - visibleStartLine, Math.ceil(gutter.height / root.editorLineHeight) + 12)

                                                Flickable {
                                                    id: gutterFlickable
                                                    anchors.fill: parent
                                                    contentHeight: editorFlickable.contentHeight
                                                    contentY: editorFlickable.contentY
                                                    interactive: false
                                                    boundsBehavior: Flickable.StopAtBounds

                                                    Item {
                                                        width: gutter.width
                                                        height: Math.max(gutterFlickable.height, tabPane.paneTotalLineCount * root.editorLineHeight + codeTextArea.topPadding + codeTextArea.bottomPadding)

                                                        Repeater {
                                                            model: gutter.visibleLineCount > 0 ? gutter.visibleLineCount : 0

                                                            delegate: Item {
                                                                readonly property int lineNum: gutter.visibleStartLine + index + 1
                                                                width: gutter.width
                                                                height: root.editorLineHeight
                                                                y: (lineNum - 1) * root.editorLineHeight + codeTextArea.topPadding

                                                                // Code fold chevron
                                                                Text {
                                                                    anchors.left: parent.left
                                                                    anchors.leftMargin: 6
                                                                    anchors.verticalCenter: parent.verticalCenter
                                                                    text: root.getFoldChevron(lineNum)
                                                                    font.pixelSize: 10
                                                                    font.family: "Consolas, monospace"
                                                                    color: foldMa.containsMouse ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                                                                    visible: root.isFoldableLine(lineNum)
                                                                    opacity: foldMa.containsMouse || root.isLineFolded(lineNum) ? 1.0 : 0.6

                                                                    MouseArea {
                                                                        id: foldMa
                                                                        anchors.fill: parent
                                                                        anchors.margins: -4
                                                                        hoverEnabled: true
                                                                        cursorShape: Qt.PointingHandCursor
                                                                        onClicked: {
                                                                            root.toggleFoldAtLine(lineNum);
                                                                        }
                                                                    }
                                                                }

                                                                // Line number
                                                                Text {
                                                                    anchors.right: parent.right
                                                                    anchors.rightMargin: 10
                                                                    anchors.verticalCenter: parent.verticalCenter
                                                                    text: lineNum.toString()
                                                                    font.pixelSize: codeTextArea.font.pixelSize
                                                                    font.family: codeTextArea.font.family
                                                                    color: (lineNum === root.cursorLine && tabPane.index === root.activeTabIndex) ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }

                                            // Code Text Area Container
                                            Item {
                                                id: textAreaContainer
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                clip: true

                                                // Indentation Guide Lines Canvas (Inside textAreaContainer, aligned with viewport)
                                                Canvas {
                                                    id: indentGuidesCanvas
                                                    anchors.fill: parent
                                                    z: 0
                                                    antialiasing: false

                                                    Timer {
                                                        id: canvasScrollTimer
                                                        interval: 16
                                                        repeat: false
                                                        onTriggered: indentGuidesCanvas.requestPaint()
                                                    }

                                                    Connections {
                                                        target: editorFlickable
                                                        function onContentXChanged() { canvasScrollTimer.restart(); }
                                                        function onContentYChanged() { canvasScrollTimer.restart(); }
                                                    }

                                                    Timer {
                                                        id: canvasDebounceTimer
                                                        interval: 60
                                                        repeat: false
                                                        onTriggered: indentGuidesCanvas.requestPaint()
                                                    }

                                                    Connections {
                                                        target: codeTextArea
                                                        function onTextChanged() { canvasDebounceTimer.restart(); }
                                                    }

                                                    Connections {
                                                        target: root
                                                        function onActiveTabIndexChanged() { indentGuidesCanvas.requestPaint(); }
                                                        function onCharWidthChanged() { indentGuidesCanvas.requestPaint(); }
                                                        function onEditorLineHeightChanged() { indentGuidesCanvas.requestPaint(); }
                                                        function onCachedIndentLevelWidthsChanged() { indentGuidesCanvas.requestPaint(); }
                                                    }

                                                    onPaint: {
                                                        var ctx = getContext("2d");
                                                        ctx.clearRect(0, 0, width, height);
                                                        var doc = codeTextArea.text;
                                                        if (!doc) return;

                                                        var tabSize = (typeof theme !== "undefined" && theme && theme.tabSize) ? theme.tabSize : 4;
                                                        var leftPadding = codeTextArea.leftPadding - editorFlickable.contentX;
                                                        var topPadding = codeTextArea.topPadding;
                                                        var lineH = root.editorLineHeight;
                                                        var cachedWidths = root.cachedIndentLevelWidths;

                                                        var viewTop = editorFlickable.contentY;
                                                        var startLine = Math.max(0, Math.floor(viewTop / lineH) - 1);
                                                        var endLine = startLine + Math.ceil(height / lineH) + 4;

                                                        var currentLineIdx = 0;
                                                        var charIdx = 0;
                                                        var docLen = doc.length;
                                                        while (currentLineIdx < startLine && charIdx < docLen) {
                                                            var nl = doc.indexOf("\n", charIdx);
                                                            if (nl === -1) { charIdx = docLen; break; }
                                                            charIdx = nl + 1;
                                                            currentLineIdx++;
                                                        }

                                                        ctx.lineWidth = 1;
                                                        ctx.strokeStyle = theme ? "#35383d" : "#303030";
                                                        ctx.globalAlpha = 0.35;

                                                        // 1. Regular indentation guides for indented code lines
                                                        for (var l = startLine; l < endLine && charIdx < docLen; l++) {
                                                            var lineEnd = doc.indexOf("\n", charIdx);
                                                            if (lineEnd === -1) lineEnd = docLen;
                                                            var lineText = doc.substring(charIdx, lineEnd);
                                                            charIdx = lineEnd + 1;

                                                            var trimmed = lineText.trim();
                                                            if (trimmed.length > 0) {
                                                                var cols = 0;
                                                                for (var c = 0; c < lineText.length; c++) {
                                                                    var ch = lineText.charAt(c);
                                                                    if (ch === ' ') {
                                                                        cols += 1;
                                                                    } else if (ch === '\t') {
                                                                        cols += tabSize - (cols % tabSize);
                                                                    } else {
                                                                        break;
                                                                    }
                                                                }
                                                                var indentCount = Math.floor(cols / tabSize);
                                                                var y = topPadding + (l * lineH) - viewTop;

                                                                for (var lvl = 1; lvl < indentCount; lvl++) {
                                                                    var lvlWidth = (lvl < cachedWidths.length) ? cachedWidths[lvl] : (lvl * cachedWidths[1]);
                                                                    var x = Math.round(leftPadding + lvlWidth) + 0.5;
                                                                    if (x >= 0 && x <= width) {
                                                                        ctx.beginPath();
                                                                        ctx.moveTo(x, y);
                                                                        ctx.lineTo(x, y + lineH);
                                                                        ctx.stroke();
                                                                    }
                                                                }
                                                            }
                                                        }

                                                        // 2. Structural Scope Guides (handles outermost { at level 0, nested {, and blank lines)
                                                        var scopes = tabPane.paneScopeRanges || [];
                                                        for (var s = 0; s < scopes.length; s++) {
                                                            var sc = scopes[s];
                                                            if (sc.startLine < endLine && sc.endLine >= startLine) {
                                                                var sLvl = sc.level;
                                                                var sLvlWidth = (sLvl < cachedWidths.length) ? cachedWidths[sLvl] : (sLvl * cachedWidths[1]);
                                                                var sx = Math.round(leftPadding + sLvlWidth) + 0.5;
                                                                if (sx >= 0 && sx <= width) {
                                                                    var lineStart = Math.max(startLine, sc.startLine + 1);
                                                                    var lineEnd = Math.min(endLine - 1, sc.endLine);
                                                                    for (var sl = lineStart; sl <= lineEnd; sl++) {
                                                                        var sy = topPadding + (sl * lineH) - viewTop;
                                                                        ctx.beginPath();
                                                                        ctx.moveTo(sx, sy);
                                                                        ctx.lineTo(sx, sy + lineH);
                                                                        ctx.stroke();

                                                                        if (sl === sc.endLine) {
                                                                            ctx.beginPath();
                                                                            ctx.moveTo(sx, sy + lineH * 0.5);
                                                                            ctx.lineTo(sx + root.charWidth * 0.75, sy + lineH * 0.5);
                                                                            ctx.stroke();
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                                                        ctx.globalAlpha = 1.0;
                                                    }
                                                }

                                                Flickable {
                                                    id: editorFlickable
                                                    anchors.fill: parent
                                                    interactive: false
                                                    clip: true
                                                    boundsBehavior: Flickable.StopAtBounds
                                                    contentWidth: Math.max(width, codeTextArea.contentWidth + codeTextArea.leftPadding + codeTextArea.rightPadding + 80)
                                                    contentHeight: Math.max(height, tabPane.paneTotalLineCount * root.editorLineHeight + 220)

                                                    WheelHandler {
                                                        target: editorFlickable
                                                        orientation: Qt.Vertical
                                                        onWheel: function(event) {
                                                            var delta = event.angleDelta.y;
                                                            if (delta === 0) return;
                                                            var lines = delta / 120.0;
                                                            var step = lines * root.editorLineHeight * 3.0;
                                                            var maxY = Math.max(0, editorFlickable.contentHeight - editorFlickable.height);
                                                            editorFlickable.contentY = Math.max(0, Math.min(maxY, editorFlickable.contentY - step));
                                                        }
                                                    }

                                                    WheelHandler {
                                                        target: null
                                                        acceptedModifiers: Qt.ControlModifier
                                                        orientation: Qt.Vertical
                                                        onWheel: function(event) {
                                                            if (typeof theme !== "undefined" && theme && theme.enableMouseWheelZoom === false) return;
                                                            var delta = event.angleDelta.y;
                                                            if (delta === 0) return;
                                                            var change = delta > 0 ? 1 : -1;
                                                            if (typeof theme !== "undefined" && theme) {
                                                                var oldLineH = root.editorLineHeight > 0 ? root.editorLineHeight : 18;
                                                                var topVisibleLine = editorFlickable.contentY / oldLineH;
                                                                var newSize = Math.max(8, Math.min(48, theme.editorFontSize + change));
                                                                if (newSize !== theme.editorFontSize) {
                                                                    theme.editorFontSize = newSize;
                                                                    theme.saveSettings();
                                                                    Qt.callLater(function() {
                                                                        if (editorFlickable && root.editorLineHeight > 0) {
                                                                            var maxY = Math.max(0, editorFlickable.contentHeight - editorFlickable.height);
                                                                            editorFlickable.contentY = Math.max(0, Math.min(maxY, topVisibleLine * root.editorLineHeight));
                                                                        }
                                                                    });
                                                                }
                                                            }
                                                        }
                                                    }

                                                    WheelHandler {
                                                        target: editorFlickable
                                                        acceptedModifiers: Qt.ShiftModifier
                                                        orientation: Qt.Horizontal
                                                        onWheel: function(event) {
                                                            var delta = event.angleDelta.y !== 0 ? event.angleDelta.y : event.angleDelta.x;
                                                            if (delta === 0) return;
                                                            var step = (delta / 120.0) * 80.0;
                                                            var maxX = Math.max(0, editorFlickable.contentWidth - editorFlickable.width);
                                                            editorFlickable.contentX = Math.max(0, Math.min(maxX, editorFlickable.contentX - step));
                                                        }
                                                    }

                                                    ScrollBar.vertical: ScrollBar {
                                                        id: vScrollBar
                                                        policy: ScrollBar.AsNeeded
                                                        width: 10
                                                        active: true
                                                    }

                                                    ScrollBar.horizontal: ScrollBar {
                                                        id: hScrollBar
                                                        policy: ScrollBar.AsNeeded
                                                        height: 10
                                                        active: true
                                                    }

                                                    // Current Line Highlight Band
                                                    Rectangle {
                                                        id: currentLineHighlight
                                                        x: 0
                                                        y: (root.cursorLine - 1) * root.editorLineHeight + codeTextArea.topPadding
                                                        width: Math.max(editorFlickable.contentWidth, editorFlickable.width)
                                                        height: root.editorLineHeight
                                                        color: (theme && theme.synCurrentLine) ? theme.synCurrentLine : "#282828"
                                                        opacity: 0.35
                                                        z: 0
                                                        visible: codeTextArea.cursorRectangle.height > 0 && tabPane.index === root.activeTabIndex
                                                    }

                                                    TextArea {
                                                        id: codeTextArea
                                                        objectName: "codeTextArea"
                                                        z: 1
                                                        width: editorFlickable.contentWidth
                                                        height: editorFlickable.contentHeight
                                                        topPadding: 6
                                                        bottomPadding: 16
                                                        leftPadding: 10
                                                        rightPadding: 24
                                                        wrapMode: (theme && theme.enableWordWrap) ? TextArea.Wrap : TextArea.NoWrap
                                                        tabStopDistance: (theme ? theme.tabSize : 4) * root.charWidth
                                                        color: theme ? theme.textPrimary : "#cccccc"
                                                        selectionColor: theme ? theme.synSelection : "#264f78"
                                                        selectedTextColor: theme ? theme.textBright : "#ffffff"
                                                        font.pixelSize: (typeof theme !== "undefined" && theme) ? theme.editorFontSize : 13
                                                        font.family: (theme && theme.fontFamilyMono) ? theme.fontFamilyMono : "Consolas"
                                                        selectByMouse: true
                                                        focus: tabPane.index === root.activeTabIndex
                                                        cursorVisible: true
                                                        textFormat: TextArea.PlainText
                                                        background: null
                                                        text: ""

                                                        Component.onCompleted: {
                                                            if (tabPane.index === root.activeTabIndex && typeof backend !== "undefined" && backend && backend.register_text_area) {
                                                                backend.register_text_area(codeTextArea, model.path || "", model.languageId || "text");
                                                            }
                                                            Qt.callLater(function() {
                                                                if (tabPane) {
                                                                    tabPane.paneScopeRanges = root.computeScopesForText(codeTextArea.text);
                                                                    indentGuidesCanvas.requestPaint();
                                                                }
                                                            });
                                                        }

                                                        signal selection(string code)

                                                        onSelectedTextChanged: {
                                                            selection(codeTextArea.selectedText);
                                                        }

                                                        // Multi-Cursor Caret Overlays
                                                        Repeater {
                                                            model: (tabPane.index === root.activeTabIndex) ? root.extraCursors : []
                                                            delegate: Rectangle {
                                                                property var curRect: codeTextArea.positionToRectangle(modelData)
                                                                x: curRect.x
                                                                y: curRect.y
                                                                width: 2
                                                                height: curRect.height > 0 ? curRect.height : root.editorLineHeight
                                                                color: theme ? theme.accent : "#0078d4"
                                                                visible: extraCursorBlinkTimer.blinkOn
                                                                z: 15
                                                            }
                                                        }

                                                        Timer {
                                                            id: extraCursorBlinkTimer
                                                            interval: 500
                                                            running: root.extraCursors.length > 0 && tabPane.index === root.activeTabIndex
                                                            repeat: true
                                                            property bool blinkOn: true
                                                            onTriggered: blinkOn = !blinkOn
                                                        }

                                                        // Alt+Click Multi-Cursor TapHandler (does not block mouse selection)
                                                        TapHandler {
                                                            acceptedButtons: Qt.LeftButton
                                                            acceptedModifiers: Qt.AltModifier
                                                            onTapped: function(event, point) {
                                                                var charPos = codeTextArea.positionAt(point.position.x, point.position.y);
                                                                root.toggleExtraCursor(charPos);
                                                            }
                                                        }

                                                        // Normal Left-Click TapHandler - clears autocomplete and extra cursors & ensures focus
                                                        TapHandler {
                                                            acceptedButtons: Qt.LeftButton
                                                            acceptedModifiers: Qt.NoModifier
                                                            onTapped: {
                                                                codeTextArea.forceActiveFocus();
                                                                if (root.extraCursors.length > 0) {
                                                                    root.extraCursors = [];
                                                                }
                                                                if (suggestionModel.count > 0) {
                                                                    suggestionModel.clear();
                                                                }
                                                            }
                                                        }

                                                        // Child right-click interceptor - intercepts right-clicks before TextArea C++ handles them
                                                        MouseArea {
                                                            anchors.fill: parent
                                                            acceptedButtons: Qt.RightButton
                                                            hoverEnabled: false
                                                            z: 10
                                                            cursorShape: Qt.IBeamCursor

                                                            onPressed: function(mouse) {
                                                                mouse.accepted = true;
                                                                var containerPos = mapToItem(codeEditorContainer, mouse.x, mouse.y);
                                                                rightClickOverlay.handleRightClickPress(containerPos.x, containerPos.y);
                                                            }

                                                            onPositionChanged: function(mouse) {
                                                                mouse.accepted = true;
                                                                var containerPos = mapToItem(codeEditorContainer, mouse.x, mouse.y);
                                                                rightClickOverlay.handleRightClickMove(containerPos.x, containerPos.y);
                                                            }

                                                            onReleased: function(mouse) {
                                                                mouse.accepted = true;
                                                                var containerPos = mapToItem(codeEditorContainer, mouse.x, mouse.y);
                                                                rightClickOverlay.handleRightClickRelease(containerPos.x, containerPos.y);
                                                            }

                                                            onCanceled: {
                                                                rightClickOverlay.handleRightClickCancel();
                                                            }
                                                        }

                                                        onCursorPositionChanged: {
                                                            if (tabPane.index === root.activeTabIndex) {
                                                                root.updateCursorPosition();
                                                                if (suggestionModel.count > 0 && !autocompleteTimer.running) {
                                                                    suggestionModel.clear();
                                                                }
                                                            }
                                                        }

                                                        onTextChanged: {
                                                            if (root.isInitialTextLoading || root.isRestoringTab || root.isFoldingOperation) return;
                                                            tabPane.paneTotalLineCount = countLines(codeTextArea.text);
                                                            tabPane.paneScopeRanges = root.computeScopesForText(codeTextArea.text);
                                                            if (index >= 0 && index < tabModel.count) {
                                                                tabModel.setProperty(index, "isDirty", true);
                                                                var curTab = tabModel.get(index);
                                                                root.activeFileChanged(curTab ? (curTab.path || "") : "", curTab ? (curTab.title || "") : "", root.currentLanguage, true);
                                                            }
                                                            canvasDebounceTimer.restart();
                                                            textChangeDebounceTimer.restart();
                                                            foldAnalysisTimer.restart();
                                                            diagnosticsTimer.restart();
                                                        }

                                                        Keys.onPressed: function(event) {
                                                            // 0. Multi-Cursor Next Occurrence: Ctrl+D
                                                            if ((event.modifiers & Qt.ControlModifier) && (event.key === Qt.Key_D)) {
                                                                root.addNextOccurrenceCursor();
                                                                event.accepted = true;
                                                                return;
                                                            }

                                                            // 0.05 Find & Replace shortcuts
                                                            if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_F) {
                                                                root.showFind(false);
                                                                event.accepted = true;
                                                                return;
                                                            }
                                                            if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_H) {
                                                                root.showFind(true);
                                                                event.accepted = true;
                                                                return;
                                                            }
                                                            if (event.key === Qt.Key_F3) {
                                                                if (event.modifiers & Qt.ShiftModifier) {
                                                                    root.findPrev(findReplaceBar.findText, findReplaceBar.matchCase);
                                                                } else {
                                                                    root.findNext(findReplaceBar.findText, findReplaceBar.matchCase);
                                                                }
                                                                event.accepted = true;
                                                                return;
                                                            }

                                                            // 0.1 Inline Color Picker: Ctrl+Shift+C
                                                            if ((event.modifiers & Qt.ControlModifier) && (event.modifiers & Qt.ShiftModifier) && (event.key === Qt.Key_C)) {
                                                                root.openColorPickerAtCursor();
                                                                event.accepted = true;
                                                                return;
                                                            }

                                                            // 0.2 Live Web / Markdown Preview: Ctrl+Shift+V
                                                            if ((event.modifiers & Qt.ControlModifier) && (event.modifiers & Qt.ShiftModifier) && (event.key === Qt.Key_V)) {
                                                                root.openWebPreviewTab();
                                                                event.accepted = true;
                                                                return;
                                                            }

                                                            // 0.3 Escape: Clear multi-cursors and suggestions
                                                            if (event.key === Qt.Key_Escape) {
                                                                var handledEsc = false;
                                                                if (root.extraCursors.length > 0) {
                                                                    root.extraCursors = [];
                                                                    handledEsc = true;
                                                                }
                                                                if (suggestionModel.count > 0) {
                                                                    suggestionModel.clear();
                                                                    handledEsc = true;
                                                                }
                                                                if (colorPickerPopup.visible) {
                                                                    colorPickerPopup.visible = false;
                                                                    handledEsc = true;
                                                                }
                                                                if (handledEsc) {
                                                                    event.accepted = true;
                                                                    return;
                                                                }
                                                            }

                                                            // 0.4 Multi-Cursor Typing & Backspacing
                                                            if (root.extraCursors.length > 0) {
                                                                if (event.key === Qt.Key_Backspace) {
                                                                    var allPos = root.extraCursors.concat([codeTextArea.cursorPosition]);
                                                                    allPos.sort(function(a, b) { return b - a; });
                                                                    allPos = allPos.filter(function(item, pos, self) { return self.indexOf(item) === pos; });

                                                                    var newText = codeTextArea.text;
                                                                    for (var bi = 0; bi < allPos.length; bi++) {
                                                                        var bp = allPos[bi];
                                                                        if (bp > 0) {
                                                                            newText = newText.substring(0, bp - 1) + newText.substring(bp);
                                                                        }
                                                                    }

                                                                    var sortedAsc = allPos.slice().sort(function(a, b) { return a - b; });
                                                                    var finalExtras = [];
                                                                    var mainNewPos = codeTextArea.cursorPosition;
                                                                    for (var s = 0; s < sortedAsc.length; s++) {
                                                                        var origP = sortedAsc[s];
                                                                        var shiftedP = Math.max(0, origP - 1 - s);
                                                                        if (origP === codeTextArea.cursorPosition) {
                                                                            mainNewPos = shiftedP;
                                                                        } else {
                                                                            finalExtras.push(shiftedP);
                                                                        }
                                                                    }
                                                                    codeTextArea.text = newText;
                                                                    codeTextArea.cursorPosition = mainNewPos;
                                                                    root.extraCursors = finalExtras;
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.text && event.text.length === 1 && !event.modifiers && event.key !== Qt.Key_Tab && event.key !== Qt.Key_Return && event.key !== Qt.Key_Enter) {
                                                                    var charTyped = event.text;
                                                                    var allCur = root.extraCursors.concat([codeTextArea.cursorPosition]);
                                                                    allCur.sort(function(a, b) { return b - a; });
                                                                    allCur = allCur.filter(function(item, pos, self) { return self.indexOf(item) === pos; });

                                                                    var docT = codeTextArea.text;
                                                                    for (var ci = 0; ci < allCur.length; ci++) {
                                                                        var cp = allCur[ci];
                                                                        docT = docT.substring(0, cp) + charTyped + docT.substring(cp);
                                                                    }

                                                                    var sortedCurAsc = allCur.slice().sort(function(a, b) { return a - b; });
                                                                    var finalCurExtras = [];
                                                                    var mainCurPos = codeTextArea.cursorPosition;
                                                                    for (var sc = 0; sc < sortedCurAsc.length; sc++) {
                                                                        var oP = sortedCurAsc[sc];
                                                                        var sP = oP + sc + 1;
                                                                        if (oP === codeTextArea.cursorPosition) {
                                                                            mainCurPos = sP;
                                                                        } else {
                                                                            finalCurExtras.push(sP);
                                                                        }
                                                                    }
                                                                    codeTextArea.text = docT;
                                                                    codeTextArea.cursorPosition = mainCurPos;
                                                                    root.extraCursors = finalCurExtras;
                                                                    event.accepted = true;
                                                                    return;
                                                                }
                                                            }

                                                            // 0.5 Ctrl+Space: Manually Trigger Autocomplete
                                                            if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_Space) {
                                                                root.triggerCompletionRequest();
                                                                event.accepted = true;
                                                                return;
                                                            }

                                                            // 1. Autocomplete navigation when popup is visible
                                                            if (autocompletePopup.visible && suggestionModel.count > 0) {
                                                                if (event.key === Qt.Key_Down) {
                                                                    autocompletePopup.selectedSuggestionIndex = (autocompletePopup.selectedSuggestionIndex + 1) % suggestionModel.count;
                                                                    suggestionListView.positionViewAtIndex(autocompletePopup.selectedSuggestionIndex, ListView.Contain);
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.key === Qt.Key_Up) {
                                                                    autocompletePopup.selectedSuggestionIndex = (autocompletePopup.selectedSuggestionIndex - 1 + suggestionModel.count) % suggestionModel.count;
                                                                    suggestionListView.positionViewAtIndex(autocompletePopup.selectedSuggestionIndex, ListView.Contain);
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.key === Qt.Key_Tab || event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                                                    var selected = suggestionModel.get(autocompletePopup.selectedSuggestionIndex);
                                                                    if (selected) {
                                                                        root.applySuggestion(selected.insertText || selected.label, selected.kind);
                                                                        event.accepted = true;
                                                                        return;
                                                                    }
                                                                } else if (event.key === Qt.Key_Escape) {
                                                                    suggestionModel.clear();
                                                                    event.accepted = true;
                                                                    return;
                                                                }
                                                            }

                                                            // 2. Tab and Shift+Tab Indentation / Unindentation
                                                            if (event.key === Qt.Key_Backtab || ((event.modifiers & Qt.ShiftModifier) && event.key === Qt.Key_Tab)) {
                                                                root.unindentSelectedText();
                                                                event.accepted = true;
                                                                return;
                                                            } else if (event.key === Qt.Key_Tab) {
                                                                root.indentSelectedText();
                                                                event.accepted = true;
                                                                return;
                                                            }

                                                            // 3. Ctrl+/ : Toggle Line Comment
                                                            if ((event.modifiers & Qt.ControlModifier) && (event.key === Qt.Key_Slash || event.key === Qt.Key_Question)) {
                                                                root.toggleComment();
                                                                event.accepted = true;
                                                                return;
                                                            }

                                                            // 4. Shift+Alt+F: Format Document
                                                            if ((event.modifiers & Qt.ShiftModifier) && (event.modifiers & Qt.AltModifier) && event.key === Qt.Key_F) {
                                                                root.formatDocument();
                                                                event.accepted = true;
                                                                return;
                                                            }

                                                            // 4. Wrap Selected Text in Quotes / Brackets
                                                            var selStart = codeTextArea.selectionStart;
                                                            var selEnd = codeTextArea.selectionEnd;
                                                            var hasSelection = (selStart !== undefined && selEnd !== undefined && selStart !== selEnd);

                                                            if (hasSelection && event.text && event.text.length === 1 && !event.modifiers) {
                                                                var wrapPairs = {
                                                                    "\"": ["\"", "\""],
                                                                    "'": ["'", "'"],
                                                                    "`": ["`", "`"],
                                                                    "(": ["(", ")"],
                                                                    "[": ["[", "]"],
                                                                    "{": ["{", "}"],
                                                                    "<": ["<", ">"]
                                                                };
                                                                if (wrapPairs[event.text]) {
                                                                    var pair = wrapPairs[event.text];
                                                                    var minP = Math.min(selStart, selEnd);
                                                                    var maxP = Math.max(selStart, selEnd);
                                                                    var selected = codeTextArea.text.substring(minP, maxP);
                                                                    var wrapped = pair[0] + selected + pair[1];
                                                                    codeTextArea.remove(minP, maxP);
                                                                    codeTextArea.insert(minP, wrapped);
                                                                    codeTextArea.select(minP + 1, minP + 1 + selected.length);
                                                                    event.accepted = true;
                                                                    return;
                                                                }
                                                            }

                                                            // 4.1 Auto Bracket Matching & Closing
                                                            if (theme && theme.enableBracketMatching && !hasSelection) {
                                                                var pos = codeTextArea.cursorPosition;
                                                                var charMap = {
                                                                    "(": ")",
                                                                    "[": "]",
                                                                    "{": "}",
                                                                    "\"": "\"",
                                                                    "'": "'",
                                                                    "`": "`"
                                                                };

                                                                if (charMap[event.text]) {
                                                                    codeTextArea.insert(pos, event.text + charMap[event.text]);
                                                                    codeTextArea.cursorPosition = pos + 1;
                                                                    event.accepted = true;
                                                                    return;
                                                                }
                                                            }

                                                            // 4.2 HTML / XML Auto Close Tag on '>'
                                                            if (event.text === ">") {
                                                                var curPosTag = codeTextArea.cursorPosition;
                                                                var fullDocTag = codeTextArea.text;
                                                                var lineStartTag = fullDocTag.lastIndexOf("\n", curPosTag - 1) + 1;
                                                                var textBeforeTag = fullDocTag.substring(lineStartTag, curPosTag);
                                                                var tagMatch = textBeforeTag.match(/<([a-zA-Z0-9_\-]+)(?:\s+[^<>]*)?$/);
                                                                if (tagMatch && !textBeforeTag.endsWith("/")) {
                                                                    var tagName = tagMatch[1].toLowerCase();
                                                                    var voidTags = ["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr", "!doctype"];
                                                                    if (voidTags.indexOf(tagName) === -1 && !tagName.startsWith("!")) {
                                                                        var closeTag = ">" + "</" + tagMatch[1] + ">";
                                                                        codeTextArea.insert(curPosTag, closeTag);
                                                                        codeTextArea.cursorPosition = curPosTag + 1;
                                                                        event.accepted = true;
                                                                        return;
                                                                    }
                                                                }
                                                            }

                                                            // 5. Smart Auto Indentation & Bracket Formatting on Enter
                                                            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                                                var curPos = codeTextArea.cursorPosition;
                                                                var docText = codeTextArea.text;
                                                                var lineStart = docText.lastIndexOf("\n", curPos - 1) + 1;
                                                                var currentLineContent = docText.substring(lineStart, curPos);

                                                                var match = currentLineContent.match(/^(\s*)/);
                                                                var baseIndent = match ? match[1] : "";
                                                                var tabSize = (theme && theme.tabSize) ? theme.tabSize : 4;
                                                                var tabSpaces = " ".repeat(tabSize);

                                                                var charBefore = curPos > 0 ? docText.charAt(curPos - 1) : "";
                                                                var charAfter = curPos < docText.length ? docText.charAt(curPos) : "";

                                                                if ((charBefore === "{" && charAfter === "}") ||
                                                                    (charBefore === "(" && charAfter === ")") ||
                                                                    (charBefore === "[" && charAfter === "]")) {
                                                                    var insertBlock = "\n" + baseIndent + tabSpaces + "\n" + baseIndent;
                                                                    codeTextArea.insert(curPos, insertBlock);
                                                                    codeTextArea.cursorPosition = curPos + 1 + baseIndent.length + tabSpaces.length;
                                                                    event.accepted = true;
                                                                    return;
                                                                }

                                                                var trimmed = currentLineContent.trim();
                                                                var indent = baseIndent;
                                                                if (trimmed.endsWith(":") || trimmed.endsWith("{") || trimmed.endsWith("(") || trimmed.endsWith("[")) {
                                                                    indent += tabSpaces;
                                                                }

                                                                codeTextArea.insert(curPos, "\n" + indent);
                                                                codeTextArea.cursorPosition = curPos + 1 + indent.length;
                                                                event.accepted = true;
                                                                return;
                                                            }

                                                            // 6. Trigger Autocomplete on typing word characters or backspacing
                                                            if (theme && theme.enableAutocomplete) {
                                                                if (event.key === Qt.Key_Backspace || event.key === Qt.Key_Delete || (event.text && event.text.length === 1 && /[a-zA-Z0-9_\.]/.test(event.text))) {
                                                                    autocompleteTimer.restart();
                                                                }
                                                            }
                                                        }

                                                        Keys.onReleased: function(event) {
                                                            if (event.key === Qt.Key_Up || event.key === Qt.Key_Down ||
                                                                event.key === Qt.Key_Left || event.key === Qt.Key_Right ||
                                                                event.key === Qt.Key_PageUp || event.key === Qt.Key_PageDown ||
                                                                event.key === Qt.Key_Home || event.key === Qt.Key_End ||
                                                                event.key === Qt.Key_Return || event.key === Qt.Key_Enter ||
                                                                event.key === Qt.Key_Backspace || event.key === Qt.Key_Tab) {
                                                                root.ensureCursorVisible();
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Minimap on right edge
                            CodeMinimap {
                                id: codeMinimap
                                Layout.fillHeight: true
                                visible: theme ? theme.enableMinimap : true
                                documentText: root.codeTextArea ? root.codeTextArea.text : ""
                                visibleRatio: root.editorFlickable ? (root.editorFlickable.height / Math.max(1, root.editorFlickable.contentHeight)) : 1.0
                                scrollRatio: root.editorFlickable ? (root.editorFlickable.contentY / Math.max(1, (root.editorFlickable.contentHeight - root.editorFlickable.height))) : 0.0

                                onScrollRequested: function(ratio) {
                                    if (root.editorFlickable) {
                                        root.editorFlickable.contentY = ratio * Math.max(0, root.editorFlickable.contentHeight - root.editorFlickable.height);
                                    }
                                }
                            }
                        }

                        // Top-Level Right-Click Interceptor Overlay (Blocks Native Qt Context Menu 100%)
                        MouseArea {
                            id: rightClickOverlay
                            anchors.fill: parent
                            acceptedButtons: Qt.RightButton
                            hoverEnabled: false
                            z: 50

                            property real pressX: 0
                            property real pressY: 0
                            property bool isHolding: false

                            function handleRightClickPress(posX, posY) {
                                pressX = posX;
                                pressY = posY;
                                var useRadial = !theme || theme.contextMenuStyle !== "standard";
                                var selText = (root.codeTextArea && root.codeTextArea.selectedText) ? root.codeTextArea.selectedText : "";
                                radialContextMenu.hasSelectedCode = (selText.trim().length > 0);
                                radialContextMenu.selectedCode = selText;

                                if (useRadial) {
                                    isHolding = true;
                                    radialContextMenu.x = Math.max(10, Math.min(codeEditorContainer.width - radialContextMenu.width - 10, posX - (radialContextMenu.width / 2)));
                                    radialContextMenu.y = Math.max(10, Math.min(codeEditorContainer.height - radialContextMenu.height - 10, posY - (radialContextMenu.height / 2)));
                                    radialContextMenu.selectedIndex = -1;
                                    radialContextMenu.visible = true;
                                } else {
                                    isHolding = false;
                                    radialContextMenu.visible = false;
                                    standardContextMenu.popup(posX, posY);
                                }
                            }

                            function handleRightClickMove(posX, posY) {
                                if (isHolding && radialContextMenu.visible) {
                                    var localX = posX - radialContextMenu.x;
                                    var localY = posY - radialContextMenu.y;
                                    radialContextMenu.handleDrag(localX, localY);
                                }
                            }

                            function handleRightClickRelease(posX, posY) {
                                if (isHolding && radialContextMenu.visible) {
                                    isHolding = false;
                                    var localX = posX - radialContextMenu.x;
                                    var localY = posY - radialContextMenu.y;
                                    var handled = radialContextMenu.handleRelease(localX, localY);
                                    if (!handled) {
                                        radialContextMenu.visible = false;
                                    }
                                }
                            }

                            function handleRightClickCancel() {
                                isHolding = false;
                                radialContextMenu.visible = false;
                            }

                            onPressed: function(mouse) {
                                mouse.accepted = true;
                                handleRightClickPress(mouse.x, mouse.y);
                            }

                            onPositionChanged: function(mouse) {
                                mouse.accepted = true;
                                handleRightClickMove(mouse.x, mouse.y);
                            }

                            onReleased: function(mouse) {
                                mouse.accepted = true;
                                handleRightClickRelease(mouse.x, mouse.y);
                            }

                            onCanceled: {
                                handleRightClickCancel();
                            }
                        }

                        // Radial Context Menu (Shown only while holding right-click)
                        RadialContextMenu {
                            id: radialContextMenu
                            visible: false
                            z: 110

                            onActionSelected: function(actionId) {
                                radialContextMenu.visible = false;
                                root.executeEditorAction(actionId);
                            }

                            onCloseRequested: radialContextMenu.visible = false
                        }

                        // Standard VS Code Styled Context Menu
                        Menu {
                            id: standardContextMenu
                            z: 115

                            background: Rectangle {
                                implicitWidth: 180
                                color: theme ? theme.bgPopup : "#252526"
                                border.color: theme ? theme.borderNormal : "#333333"
                                radius: theme ? theme.radiusSm : 3
                            }

                            Action {
                                text: "Format Document\tShift+Alt+F"
                                onTriggered: root.formatDocument()
                            }
                            Action {
                                text: (root.codeTextArea && root.codeTextArea.selectedText) ? "Ask AI": "Run File\tF5"
                                onTriggered: (root.codeTextArea && root.codeTextArea.selectedText) ? root.askAi(root.codeTextArea.selectedText) : root.requestRunFile()
                            }

                            MenuSeparator {
                                contentItem: Rectangle {
                                    implicitHeight: 1
                                    color: theme ? theme.borderSubtle : "#282828"
                                }
                            }
                            Action {
                                text: "Cut\tCtrl+X"
                                onTriggered: if (root.codeTextArea) root.codeTextArea.cut()
                            }
                            Action {
                                text: "Copy\tCtrl+C"
                                onTriggered: if (root.codeTextArea) root.codeTextArea.copy()
                            }
                            Action {
                                text: "Paste\tCtrl+V"
                                onTriggered: if (root.codeTextArea) root.codeTextArea.paste()
                            }
                            MenuSeparator {
                                contentItem: Rectangle {
                                    implicitHeight: 1
                                    color: theme ? theme.borderSubtle : "#282828"
                                }
                            }
                            Action {
                                text: "Find\tCtrl+F"
                                onTriggered: root.showFind(false)
                            }
                            Action {
                                text: "Replace\tCtrl+H"
                                onTriggered: root.showFind(true)
                            }

                            delegate: MenuItem {
                                id: stdItm
                                implicitHeight: 26
                                contentItem: Text {
                                    text: stdItm.text
                                    color: stdItm.highlighted ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                    font.pixelSize: 12
                                    verticalAlignment: Text.AlignVCenter
                                    leftPadding: 8
                                    rightPadding: 8
                                }
                                background: Rectangle {
                                    color: stdItm.highlighted ? (theme ? theme.bgSelected : "#04395e") : "transparent"
                                }
                            }
                        }

                        // Autocomplete Popup Menu (Positioned exactly below typing cursor)
                        Rectangle {
                            id: autocompletePopup
                            width: 220
                            height: Math.min(180, suggestionModel.count * 24 + 8)
                            visible: suggestionModel.count > 0
                            radius: theme ? theme.radiusSm : 3
                            color: theme ? theme.bgPopup : "#252526"
                            border.color: theme ? theme.borderNormal : "#333333"
                            border.width: 1
                            z: 100

                            property int selectedSuggestionIndex: 0

                            readonly property point cursorPt: {
                                if (!root.codeTextArea) return Qt.point(0, 0);
                                var r = root.codeTextArea.cursorRectangle;
                                return root.codeTextArea.mapToItem(codeEditorContainer, r.x, r.y + r.height + 2);
                            }

                            x: Math.min(codeEditorContainer.width - width - 10, Math.max(10, cursorPt.x))
                            y: (cursorPt.y + height > codeEditorContainer.height - 10) ? Math.max(10, cursorPt.y - height - (root.codeTextArea ? root.codeTextArea.cursorRectangle.height : 18) - 4) : Math.max(10, cursorPt.y)

                            ListModel { id: suggestionModel }

                            ListView {
                                id: suggestionListView
                                anchors.fill: parent
                                anchors.margins: 4
                                model: suggestionModel
                                clip: true
                                currentIndex: autocompletePopup.selectedSuggestionIndex

                                delegate: Rectangle {
                                    width: suggestionListView.width
                                    height: 22
                                    radius: 2
                                    color: index === autocompletePopup.selectedSuggestionIndex ? (theme ? theme.bgSelected : "#04395e") : (sugMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 6
                                        anchors.rightMargin: 6
                                        spacing: 6

                                        VectorIcon {
                                            name: (model.kind === "keyword") ? "sparkles" : ((model.kind === "method" || model.kind === "function") ? "play" : "file")
                                            size: 10
                                            color: index === autocompletePopup.selectedSuggestionIndex ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: model.label || ""
                                            color: index === autocompletePopup.selectedSuggestionIndex ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                            font.pixelSize: 11
                                            font.family: theme ? theme.fontFamilyMono : "monospace"
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            text: model.kind || ""
                                            color: theme ? theme.textMuted : "#656565"
                                            font.pixelSize: 9
                                            visible: model.kind ? true : false
                                        }
                                    }

                                    MouseArea {
                                        id: sugMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.applySuggestion(model.insertText || model.label);
                                        }
                                    }
                                }
                            }
                        }

                        // Floating Find & Replace Bar
                        FindReplaceBar {
                            id: findReplaceBar
                            anchors.top: parent.top
                            anchors.right: parent.right
                            anchors.topMargin: 6
                            anchors.rightMargin: 16
                            visible: false
                            z: 90

                            onFindNextRequested: root.findNext(findReplaceBar.findText, findReplaceBar.matchCase)
                            onFindPrevRequested: root.findPrev(findReplaceBar.findText, findReplaceBar.matchCase)
                            onReplaceRequested: root.replaceNext(findReplaceBar.findText, findReplaceBar.replaceText, findReplaceBar.matchCase)
                            onReplaceAllRequested: root.replaceAll(findReplaceBar.findText, findReplaceBar.replaceText, findReplaceBar.matchCase)
                            onCloseRequested: {
                                findReplaceBar.visible = false;
                                if (root.codeTextArea) root.codeTextArea.forceActiveFocus();
                            }
                        }

                        // Floating Color Picker Popup
                        ColorPickerPopup {
                            id: colorPickerPopup
                            visible: false
                            z: 120
                            onColorChosen: function(hex) {
                                if (colorPickerPopup.targetStart >= 0 && colorPickerPopup.targetEnd > colorPickerPopup.targetStart && root.codeTextArea) {
                                    root.codeTextArea.remove(colorPickerPopup.targetStart, colorPickerPopup.targetEnd);
                                    root.codeTextArea.insert(colorPickerPopup.targetStart, hex);
                                    colorPickerPopup.targetEnd = colorPickerPopup.targetStart + hex.length;
                                }
                            }
                            onCloseRequested: {
                                colorPickerPopup.visible = false;
                                if (root.codeTextArea) root.codeTextArea.forceActiveFocus();
                            }
                        }
                    }

                    // 1.2 Whiteboard Canvas Tab View (Embedded as a full tab)
                    WhiteboardView {
                        id: whiteboardCanvasTab
                        anchors.fill: parent
                        visible: root.currentTab && root.currentTab.isWhiteboard
                        onCloseRequested: {
                            if (root.activeTabIndex >= 0) {
                                root.closeTab(root.activeTabIndex);
                            }
                        }
                    }

                    // 1.3 Web & Markdown Live Preview Tab View
                    WebPreviewView {
                        id: webPreviewTab
                        anchors.fill: parent
                        visible: root.currentTab && (root.currentTab.isWebPreview || root.currentTab.languageId === "webpreview")
                        htmlContent: root.currentTab ? (root.currentTab.content || "") : ""
                        sourcePath: root.currentTab ? (root.currentTab.sourcePath || root.currentTab.path || "") : ""
                        isMarkdown: root.currentTab ? (root.currentTab.isMarkdown || false) : false
                        onCloseRequested: {
                            if (root.activeTabIndex >= 0) {
                                root.closeTab(root.activeTabIndex);
                            }
                        }
                    }
                }

                // 2. SplitHandle (1px movable horizontal splitter between Left & Right panes)
                SplitHandle {
                    id: editorSplitDivider
                    orientation: Qt.Horizontal
                    visible: root.isSplitEditor
                    enabled: root.isSplitEditor
                    onMoved: function(delta) {
                        var newW = ((mainEditorSurface.width - 2) * root.splitRatio) + delta;
                        root.splitRatio = Math.max(0.18, Math.min(0.82, newW / Math.max(1, mainEditorSurface.width - 2)));
                    }
                }

                // 3. Secondary Right Editor Container
                Item {
                    id: secondaryEditorContainer
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    visible: root.isSplitEditor
                    clip: true

                    Rectangle {
                        anchors.fill: parent
                        color: theme ? theme.bgEditor : "#1e1e1e"
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        // Secondary Pane Header Bar (VS Code style Tab Bar + Close Split Pane)
                        Rectangle {
                            Layout.fillWidth: true
                            height: 30
                            color: theme ? theme.bgHeader : "#181818"

                            Rectangle {
                                anchors.bottom: parent.bottom
                                anchors.left: parent.left
                                anchors.right: parent.right
                                height: 1
                                color: theme ? theme.borderSubtle : "#282828"
                            }

                            RowLayout {
                                anchors.fill: parent
                                spacing: 0

                                // Secondary Tabs Scrollable Row
                                ScrollView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                                    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
                                    clip: true

                                    Row {
                                        height: parent.height
                                        spacing: 1

                                        Repeater {
                                            model: root.tabModel

                                            delegate: Rectangle {
                                                id: secTabItem
                                                height: 29
                                                width: Math.min(170, Math.max(90, secTabTitleText.contentWidth + 48))
                                                color: index === root.secondaryTabIndex ? (theme ? theme.bgEditor : "#1e1e1e") : (secTabMa.containsMouse ? (theme ? theme.bgSurface : "#252526") : (theme ? theme.bgHeader : "#181818"))

                                                Rectangle {
                                                    anchors.right: parent.right
                                                    anchors.top: parent.top
                                                    anchors.bottom: parent.bottom
                                                    width: 1
                                                    color: theme ? theme.borderSubtle : "#282828"
                                                }

                                                Rectangle {
                                                    anchors.top: parent.top
                                                    anchors.left: parent.left
                                                    anchors.right: parent.right
                                                    height: 2
                                                    color: theme ? theme.accent : "#0078d4"
                                                    visible: index === root.secondaryTabIndex
                                                }

                                                RowLayout {
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 8
                                                    anchors.rightMargin: 4
                                                    spacing: 4

                                                    VectorIcon {
                                                        name: (model.isWhiteboard || model.languageId === "whiteboard") ? "board" : ((model.isWebPreview || model.languageId === "webpreview") ? "sparkles" : "file")
                                                        size: 10
                                                        color: index === root.secondaryTabIndex ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                                                    }

                                                    Text {
                                                        id: secTabTitleText
                                                        text: model.title || "Untitled"
                                                        color: index === root.secondaryTabIndex ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                                        font.pixelSize: 11
                                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                                        elide: Text.ElideRight
                                                        Layout.fillWidth: true
                                                    }

                                                    // Close tab button
                                                    Rectangle {
                                                        Layout.preferredWidth: 16
                                                        Layout.preferredHeight: 16
                                                        radius: 2
                                                        color: secCloseMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#333333") : "transparent"
                                                        visible: secTabMa.containsMouse || index === root.secondaryTabIndex

                                                        VectorIcon {
                                                            anchors.centerIn: parent
                                                            name: "close"
                                                            size: 8
                                                            color: secCloseMa.containsMouse ? (theme ? theme.error : "#ef4444") : (theme ? theme.textMuted : "#656565")
                                                        }

                                                        MouseArea {
                                                            id: secCloseMa
                                                            anchors.fill: parent
                                                            hoverEnabled: true
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: {
                                                                root.closeTab(index);
                                                            }
                                                        }
                                                    }
                                                }

                                                MouseArea {
                                                    id: secTabMa
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    z: -1
                                                    onClicked: {
                                                        root.secondaryTabIndex = index;
                                                        root.syncSecondaryEditor();
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                // Secondary Active File Indicator / Breadcrumb
                                RowLayout {
                                    Layout.alignment: Qt.AlignVCenter
                                    Layout.rightMargin: 8
                                    spacing: 6
                                    visible: root.secondaryTab !== null

                                    VectorIcon {
                                        name: (root.secondaryTab && (root.secondaryTab.isWhiteboard || root.secondaryTab.languageId === "whiteboard")) ? "board" : ((root.secondaryTab && (root.secondaryTab.isWebPreview || root.secondaryTab.languageId === "webpreview")) ? "sparkles" : "file")
                                        size: 11
                                        color: theme ? theme.accent : "#0078d4"
                                    }

                                    Text {
                                        text: root.secondaryTab ? (root.secondaryTab.title || (root.secondaryTab.path ? root.secondaryTab.path.split("/").pop().split("\\").pop() : "Untitled")) : ""
                                        color: theme ? theme.textBright : "#ffffff"
                                        font.pixelSize: 11
                                        font.bold: true
                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                    }
                                }

                                // Close Split Editor Pane Button (X)
                                Rectangle {
                                    Layout.preferredWidth: 28
                                    Layout.preferredHeight: 28
                                    Layout.alignment: Qt.AlignVCenter
                                    Layout.rightMargin: 4
                                    radius: 2
                                    color: closeSplitMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                                    VectorIcon {
                                        anchors.centerIn: parent
                                        name: "close"
                                        size: 10
                                        color: closeSplitMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                                    }

                                    ToolTip.visible: closeSplitMa.containsMouse
                                    ToolTip.text: "Close Split Pane (Ctrl+\\)"

                                    MouseArea {
                                        id: closeSplitMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.isSplitEditor = false;
                                        }
                                    }
                                }
                            }
                        }

                        // Secondary Content Surface
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            // Secondary Code Editor Surface
                            Item {
                                anchors.fill: parent
                                visible: !root.secondaryTab || (!root.secondaryTab.isWhiteboard && !root.secondaryTab.isWebPreview && root.secondaryTab.languageId !== "webpreview")

                                RowLayout {
                                    anchors.fill: parent
                                    spacing: 0

                                    // Secondary Gutter (Virtualized)
                                    Rectangle {
                                        id: secGutter
                                        Layout.preferredWidth: Math.max(38, (root.secondaryTotalLineCount.toString().length * 8 + 22))
                                        Layout.fillHeight: true
                                        color: theme ? theme.bgPanel : "#181818"
                                        visible: theme ? theme.enableLineNumbers : true
                                        clip: true

                                        readonly property int visibleStartLine: Math.max(0, Math.floor(secGutterFlickable.contentY / root.editorLineHeight))
                                        readonly property int visibleLineCount: Math.min(root.secondaryTotalLineCount - visibleStartLine, Math.ceil(secGutter.height / root.editorLineHeight) + 12)

                                        Flickable {
                                            id: secGutterFlickable
                                            anchors.fill: parent
                                            contentHeight: secEditorFlickable.contentHeight
                                            contentY: secEditorFlickable.contentY
                                            interactive: false
                                            boundsBehavior: Flickable.StopAtBounds

                                            Item {
                                                width: secGutter.width
                                                height: Math.max(secGutterFlickable.height, root.secondaryTotalLineCount * root.editorLineHeight + secCodeTextArea.topPadding + secCodeTextArea.bottomPadding)

                                                Repeater {
                                                    model: secGutter.visibleLineCount > 0 ? secGutter.visibleLineCount : 0

                                                    delegate: Item {
                                                        readonly property int lineNum: secGutter.visibleStartLine + index + 1
                                                        width: secGutter.width
                                                        height: root.editorLineHeight
                                                        y: (lineNum - 1) * root.editorLineHeight + secCodeTextArea.topPadding

                                                        Text {
                                                            anchors.right: parent.right
                                                            anchors.rightMargin: 8
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            text: lineNum.toString()
                                                            font.pixelSize: secCodeTextArea.font.pixelSize
                                                            font.family: secCodeTextArea.font.family
                                                            color: theme ? theme.textMuted : "#656565"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // Secondary Text Area Container
                                    Item {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        clip: true

                                        // Indentation Guide Lines Canvas (Secondary Editor)
                                        Canvas {
                                            id: secIndentGuidesCanvas
                                            anchors.fill: parent
                                            z: 0
                                            antialiasing: false

                                            Timer {
                                                id: secCanvasScrollTimer
                                                interval: 16
                                                repeat: false
                                                onTriggered: secIndentGuidesCanvas.requestPaint()
                                            }

                                            Connections {
                                                target: secEditorFlickable
                                                function onContentXChanged() { secCanvasScrollTimer.restart(); }
                                                function onContentYChanged() { secCanvasScrollTimer.restart(); }
                                            }

                                            Timer {
                                                id: secCanvasDebounceTimer
                                                interval: 60
                                                repeat: false
                                                onTriggered: secIndentGuidesCanvas.requestPaint()
                                            }

                                            Connections {
                                                target: secCodeTextArea
                                                function onTextChanged() { secCanvasDebounceTimer.restart(); }
                                            }

                                            Connections {
                                                target: root
                                                function onActiveTabIndexChanged() { secIndentGuidesCanvas.requestPaint(); }
                                                function onSecondaryTabIndexChanged() { secIndentGuidesCanvas.requestPaint(); }
                                                function onCharWidthChanged() { secIndentGuidesCanvas.requestPaint(); }
                                                function onEditorLineHeightChanged() { secIndentGuidesCanvas.requestPaint(); }
                                                function onCachedIndentLevelWidthsChanged() { secIndentGuidesCanvas.requestPaint(); }
                                            }

                                            onPaint: {
                                                var ctx = getContext("2d");
                                                ctx.clearRect(0, 0, width, height);
                                                var doc = secCodeTextArea.text;
                                                if (!doc) return;

                                                var tabSize = (theme && theme.tabSize) ? theme.tabSize : 4;
                                                var leftPadding = secCodeTextArea.leftPadding - secEditorFlickable.contentX;
                                                var topPadding = secCodeTextArea.topPadding;
                                                var lineH = root.editorLineHeight;
                                                var cachedWidths = root.cachedIndentLevelWidths;

                                                var viewTop = secEditorFlickable.contentY;
                                                var startLine = Math.max(0, Math.floor(viewTop / lineH) - 1);
                                                var endLine = startLine + Math.ceil(height / lineH) + 4;

                                                var currentLineIdx = 0;
                                                var charIdx = 0;
                                                var docLen = doc.length;
                                                while (currentLineIdx < startLine && charIdx < docLen) {
                                                    var nl = doc.indexOf("\n", charIdx);
                                                    if (nl === -1) { charIdx = docLen; break; }
                                                    charIdx = nl + 1;
                                                    currentLineIdx++;
                                                }

                                                ctx.lineWidth = 1;
                                                ctx.strokeStyle = theme ? "#35383d" : "#303030";
                                                ctx.globalAlpha = 0.35;

                                                // 1. Regular indentation guides for indented code lines
                                                for (var l = startLine; l < endLine && charIdx < docLen; l++) {
                                                    var lineEnd = doc.indexOf("\n", charIdx);
                                                    if (lineEnd === -1) lineEnd = docLen;
                                                    var lineText = doc.substring(charIdx, lineEnd);
                                                    charIdx = lineEnd + 1;

                                                    var trimmed = lineText.trim();
                                                    if (trimmed.length > 0) {
                                                        var cols = 0;
                                                        for (var c = 0; c < lineText.length; c++) {
                                                            var ch = lineText.charAt(c);
                                                            if (ch === ' ') {
                                                                cols += 1;
                                                            } else if (ch === '\t') {
                                                                cols += tabSize - (cols % tabSize);
                                                            } else {
                                                                break;
                                                            }
                                                        }
                                                        var indentCount = Math.floor(cols / tabSize);
                                                        var y = topPadding + (l * lineH) - viewTop;

                                                        for (var lvl = 1; lvl < indentCount; lvl++) {
                                                            var lvlWidth = (lvl < cachedWidths.length) ? cachedWidths[lvl] : (lvl * cachedWidths[1]);
                                                            var x = Math.round(leftPadding + lvlWidth) + 0.5;
                                                            if (x >= 0 && x <= width) {
                                                                ctx.beginPath();
                                                                ctx.moveTo(x, y);
                                                                ctx.lineTo(x, y + lineH);
                                                                ctx.stroke();
                                                            }
                                                        }
                                                    }
                                                }

                                                // 2. Structural Scope Guides (handles outermost { at level 0, nested {, and blank lines)
                                                var scopes = root.activeScopeRanges || [];
                                                for (var s = 0; s < scopes.length; s++) {
                                                    var sc = scopes[s];
                                                    if (sc.startLine < endLine && sc.endLine >= startLine) {
                                                        var sLvl = sc.level;
                                                        var sLvlWidth = (sLvl < cachedWidths.length) ? cachedWidths[sLvl] : (sLvl * cachedWidths[1]);
                                                        var sx = Math.round(leftPadding + sLvlWidth) + 0.5;
                                                        if (sx >= 0 && sx <= width) {
                                                            var lineStart = Math.max(startLine, sc.startLine + 1);
                                                            var lineEnd = Math.min(endLine - 1, sc.endLine);
                                                            for (var sl = lineStart; sl <= lineEnd; sl++) {
                                                                var sy = topPadding + (sl * lineH) - viewTop;
                                                                ctx.beginPath();
                                                                ctx.moveTo(sx, sy);
                                                                ctx.lineTo(sx, sy + lineH);
                                                                ctx.stroke();

                                                                if (sl === sc.endLine) {
                                                                    ctx.beginPath();
                                                                    ctx.moveTo(sx, sy + lineH * 0.5);
                                                                    ctx.lineTo(sx + root.charWidth * 0.75, sy + lineH * 0.5);
                                                                    ctx.stroke();
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                                ctx.globalAlpha = 1.0;
                                            }
                                        }

                                        Flickable {
                                            id: secEditorFlickable
                                            anchors.fill: parent
                                            interactive: false
                                            clip: true
                                            boundsBehavior: Flickable.StopAtBounds
                                            contentWidth: Math.max(width, secCodeTextArea.contentWidth + secCodeTextArea.leftPadding + secCodeTextArea.rightPadding + 60)
                                            contentHeight: Math.max(height, secCodeTextArea.height + Math.max(250, height * 0.5))

                                            WheelHandler {
                                                target: secEditorFlickable
                                                orientation: Qt.Vertical
                                                onWheel: function(event) {
                                                    var delta = event.angleDelta.y;
                                                    if (delta === 0) return;
                                                    var lines = delta / 120.0;
                                                    var step = lines * root.editorLineHeight * 3.0;
                                                    var maxY = Math.max(0, secEditorFlickable.contentHeight - secEditorFlickable.height);
                                                    secEditorFlickable.contentY = Math.max(0, Math.min(maxY, secEditorFlickable.contentY - step));
                                                }
                                            }

                                            WheelHandler {
                                                target: secEditorFlickable
                                                acceptedModifiers: Qt.ShiftModifier
                                                orientation: Qt.Horizontal
                                                onWheel: function(event) {
                                                    var delta = event.angleDelta.y !== 0 ? event.angleDelta.y : event.angleDelta.x;
                                                    if (delta === 0) return;
                                                    var step = (delta / 120.0) * 80.0;
                                                    var maxX = Math.max(0, secEditorFlickable.contentWidth - secEditorFlickable.width);
                                                    secEditorFlickable.contentX = Math.max(0, Math.min(maxX, secEditorFlickable.contentX - step));
                                                }
                                            }

                                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; width: 8; active: true }
                                            ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded; height: 8; active: true }

                                            TextArea {
                                                id: secCodeTextArea
                                                z: 1
                                                cursorVisible: true
                                                tabStopDistance: (theme ? theme.tabSize : 4) * root.charWidth
                                                width: Math.max(secEditorFlickable.width, secEditorFlickable.contentWidth)
                                                height: Math.max(secEditorFlickable.height, contentHeight + topPadding + bottomPadding + 10)
                                                topPadding: 6
                                                bottomPadding: 16
                                                leftPadding: 8
                                                rightPadding: 16
                                                wrapMode: (theme && theme.enableWordWrap) ? TextArea.Wrap : TextArea.NoWrap
                                                color: theme ? theme.textPrimary : "#cccccc"
                                                selectionColor: theme ? theme.synSelection : "#264f78"
                                                selectedTextColor: theme ? theme.textBright : "#ffffff"
                                                font.pixelSize: theme ? theme.editorFontSize : 13
                                                font.family: (theme && theme.fontFamilyMono) ? theme.fontFamilyMono : "Consolas"
                                                selectByMouse: true
                                                textFormat: TextArea.PlainText
                                                background: null

                                                Component.onCompleted: {
                                                    if (typeof backend !== "undefined" && backend && backend.register_secondary_text_area) {
                                                        backend.register_secondary_text_area(secCodeTextArea);
                                                    }
                                                    root.syncSecondaryEditor();
                                                }

                                                onTextChanged: {
                                                    if (root.secondaryTab && root.secondaryTabIndex >= 0) {
                                                        tabModel.setProperty(root.secondaryTabIndex, "content", secCodeTextArea.text);
                                                        tabModel.setProperty(root.secondaryTabIndex, "isDirty", true);
                                                        if (root.secondaryTabIndex === root.activeTabIndex && codeTextArea.text !== secCodeTextArea.text) {
                                                            codeTextArea.text = secCodeTextArea.text;
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Secondary Whiteboard Surface
                            WhiteboardView {
                                anchors.fill: parent
                                visible: root.secondaryTab && root.secondaryTab.isWhiteboard
                            }

                            // Secondary Web Preview Surface
                            WebPreviewView {
                                anchors.fill: parent
                                visible: root.secondaryTab && (root.secondaryTab.isWebPreview || root.secondaryTab.languageId === "webpreview")
                                htmlContent: root.secondaryTab ? (root.secondaryTab.content || "") : ""
                                sourcePath: root.secondaryTab ? (root.secondaryTab.sourcePath || root.secondaryTab.path || "") : ""
                                isMarkdown: root.secondaryTab ? (root.secondaryTab.isMarkdown || false) : false
                            }
                        }
                    }
                }
            }
        }
    }

    Timer {
        id: autocompleteTimer
        interval: 180
        repeat: false
        onTriggered: {
            root.triggerCompletionRequest();
        }
    }

    function executeEditorAction(actionId) {
        if (actionId === "format") {
            root.formatDocument();
        } else if (actionId === "ask_ai") {
            var code = codeTextArea.selectedText || "";
            if (code.length > 0) {
                root.askAi(code);
            }
        } else if (actionId === "run") {
            if (codeTextArea.selectedText && codeTextArea.selectedText.trim().length > 0) {
                root.askAi(codeTextArea.selectedText);
                return;
            }
            var ext = root.activeFileName ? root.activeFileName.split(".").pop().toLowerCase() : "";
            if (ext === "html" || ext === "htm") {
                var target = (theme && theme.htmlRunTarget) ? theme.htmlRunTarget : "built_in";
                if (target === "built_in") {
                    root.openWebPreviewTab();
                    return;
                }
            }
            root.requestRunFile();
        } else if (actionId === "copy") {
            codeTextArea.copy();
        } else if (actionId === "cut") {
            codeTextArea.cut();
        } else if (actionId === "paste") {
            codeTextArea.paste();
        } else if (actionId === "undo") {
            codeTextArea.undo();
        } else if (actionId === "find") {
            root.showFind(false);
        }
    }

    // =========================================================================
    // ACCURATE MULTI-LANGUAGE CODE FORMATTER (Preserves Viewport & Cursor Position)
    // =========================================================================
    function formatDocument() {
        var text = codeTextArea.text;
        if (!text || text.trim().length === 0) return;

        var lang = root.currentLanguageId;
        var ext = root.activeFileName ? root.activeFileName.split(".").pop().toLowerCase() : "";
        var tabSize = theme ? theme.tabSize : 4;
        var tabSpaces = " ".repeat(tabSize);
        var formattedText = text;

        if (typeof backend !== "undefined" && backend && backend.format_code) {
            try {
                formattedText = backend.format_code(lang, root.activeFilePath || root.activeFileName || "", text, tabSize);
            } catch (e) {
                console.log("[EditorArea] Backend format notice:", e);
            }
        }

        // Fallback local formatter if backend produced no change or is unavailable
        if (!formattedText || formattedText === text) {
            if (lang === "json" || ext === "json") {
                try {
                    var parsed = JSON.parse(text);
                    formattedText = JSON.stringify(parsed, null, tabSize);
                } catch (e) {}
            }
        }

        if (!formattedText || formattedText === text) return;

        var curLine = root.cursorLine;
        var curCol = root.cursorColumn;
        var oldScrollX = editorFlickable.contentX;
        var oldScrollY = editorFlickable.contentY;

        codeTextArea.text = formattedText;

        // Restore cursor position by line and column in formatted text
        var newLines = formattedText.split("\n");
        var targetLine = Math.min(curLine, newLines.length);
        var newCharPos = 0;
        for (var l = 0; l < targetLine - 1; l++) {
            newCharPos += newLines[l].length + 1;
        }
        if (targetLine - 1 < newLines.length) {
            newCharPos += Math.min(curCol - 1, newLines[targetLine - 1].length);
        }
        codeTextArea.cursorPosition = Math.min(newCharPos, formattedText.length);

        // Keep viewport steady so code is never scrolled away or hidden
        editorFlickable.contentX = Math.max(0, oldScrollX);
        editorFlickable.contentY = Math.max(0, oldScrollY);
        root.updateCursorPosition();
    }

    // =========================================================================
    // SMART TAB & INDENTATION ENGINE
    // =========================================================================
    function indentSelectedText() {
        var tabSize = (theme && theme.tabSize) ? theme.tabSize : 4;
        var tabSpaces = " ".repeat(tabSize);
        var fullText = codeTextArea.text;
        var start = codeTextArea.selectionStart;
        var end = codeTextArea.selectionEnd;

        // 1. Multi-line selection: indent each selected line by tabSpaces
        if (start !== end) {
            var minPos = Math.min(start, end);
            var maxPos = Math.max(start, end);

            var firstLineStart = fullText.lastIndexOf("\n", minPos - 1) + 1;
            var lastLineEnd = fullText.indexOf("\n", maxPos);
            if (lastLineEnd === -1) lastLineEnd = fullText.length;

            var targetBlock = fullText.substring(firstLineStart, lastLineEnd);
            var lines = targetBlock.split("\n");
            var modifiedLines = [];
            var addedChars = 0;

            for (var i = 0; i < lines.length; i++) {
                modifiedLines.push(tabSpaces + lines[i]);
                addedChars += tabSpaces.length;
            }

            var newBlock = modifiedLines.join("\n");
            codeTextArea.text = fullText.substring(0, firstLineStart) + newBlock + fullText.substring(lastLineEnd);
            codeTextArea.select(minPos + tabSpaces.length, maxPos + addedChars);
            return;
        }

        // 2. Single cursor position (Smart Tab)
        var cur = codeTextArea.cursorPosition;
        var lineStart = fullText.lastIndexOf("\n", cur - 1) + 1;
        var textBeforeCursor = fullText.substring(lineStart, cur);
        var isLeadingWhitespace = /^\s*$/.test(textBeforeCursor);

        if (isLeadingWhitespace) {
            // Find previous non-empty line to determine context-aware smart indent
            var prevText = fullText.substring(0, lineStart > 0 ? lineStart - 1 : 0);
            var prevLines = prevText.split("\n");
            var prevNonEmpty = "";
            for (var p = prevLines.length - 1; p >= 0; p--) {
                if (prevLines[p].trim().length > 0) {
                    prevNonEmpty = prevLines[p];
                    break;
                }
            }

            var expectedIndent = "";
            if (prevNonEmpty.length > 0) {
                var prevIndentMatch = prevNonEmpty.match(/^(\s*)/);
                var prevIndent = prevIndentMatch ? prevIndentMatch[1] : "";
                var prevTrimmed = prevNonEmpty.trim();

                if (prevTrimmed.endsWith(":") || prevTrimmed.endsWith("{") || prevTrimmed.endsWith("(") || prevTrimmed.endsWith("[")) {
                    expectedIndent = prevIndent + tabSpaces;
                } else if (/^(case\b|default:)/.test(prevTrimmed) && !prevTrimmed.endsWith(";")) {
                    expectedIndent = prevIndent + tabSpaces;
                } else {
                    expectedIndent = prevIndent;
                }
            }

            // If current line indent is less than expected indent, jump directly to expected indent
            if (expectedIndent.length > textBeforeCursor.length && expectedIndent.startsWith(textBeforeCursor)) {
                var missingSpaces = expectedIndent.substring(textBeforeCursor.length);
                codeTextArea.insert(cur, missingSpaces);
                codeTextArea.cursorPosition = cur + missingSpaces.length;
            } else {
                // Otherwise add standard tabSpaces or align to next tab stop
                var col = textBeforeCursor.length;
                var count = tabSize - (col % tabSize);
                if (count === 0) count = tabSize;
                var insertStr = " ".repeat(count);
                codeTextArea.insert(cur, insertStr);
                codeTextArea.cursorPosition = cur + insertStr.length;
            }
        } else {
            // Cursor is after code on the line: align to next tab stop multiple of tabSize
            var colAfter = textBeforeCursor.length;
            var spacesNeeded = tabSize - (colAfter % tabSize);
            if (spacesNeeded === 0) spacesNeeded = tabSize;
            var addSpaces = " ".repeat(spacesNeeded);
            codeTextArea.insert(cur, addSpaces);
            codeTextArea.cursorPosition = cur + addSpaces.length;
        }

        root.updateCursorPosition();
    }

    function unindentSelectedText() {
        var tabSize = (theme && theme.tabSize) ? theme.tabSize : 4;
        var fullText = codeTextArea.text;
        var start = codeTextArea.selectionStart;
        var end = codeTextArea.selectionEnd;

        if (start === end) {
            var cur = codeTextArea.cursorPosition;
            var lineStart = fullText.lastIndexOf("\n", cur - 1) + 1;
            var lineEnd = fullText.indexOf("\n", cur);
            if (lineEnd === -1) lineEnd = fullText.length;
            var lineContent = fullText.substring(lineStart, lineEnd);
            var textBeforeCursor = fullText.substring(lineStart, cur);

            // If cursor is in leading whitespace or at start of line
            if (/^\s*$/.test(textBeforeCursor)) {
                var matchLeading = lineContent.match(/^ +/);
                if (matchLeading) {
                    var spacesToRemove = Math.min(tabSize, matchLeading[0].length);
                    codeTextArea.remove(lineStart, lineStart + spacesToRemove);
                    codeTextArea.cursorPosition = Math.max(lineStart, cur - spacesToRemove);
                }
            } else {
                // If cursor is after spaces
                var matchTrail = textBeforeCursor.match(/ +$/);
                if (matchTrail) {
                    var removeCount = Math.min(tabSize, matchTrail[0].length);
                    codeTextArea.remove(cur - removeCount, cur);
                    codeTextArea.cursorPosition = cur - removeCount;
                }
            }
            root.updateCursorPosition();
            return;
        }

        var minPos = Math.min(start, end);
        var maxPos = Math.max(start, end);

        var firstLineStart = fullText.lastIndexOf("\n", minPos - 1) + 1;
        var lastLineEnd = fullText.indexOf("\n", maxPos);
        if (lastLineEnd === -1) lastLineEnd = fullText.length;

        var targetBlock = fullText.substring(firstLineStart, lastLineEnd);
        var lines = targetBlock.split("\n");
        var modifiedLines = [];
        var removedChars = 0;

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];
            var spacesToRemove = 0;
            if (line.startsWith("\t")) {
                spacesToRemove = 1;
            } else {
                while (spacesToRemove < tabSize && line.charAt(spacesToRemove) === ' ') {
                    spacesToRemove++;
                }
            }
            modifiedLines.push(line.substring(spacesToRemove));
            removedChars += spacesToRemove;
        }

        var newBlock = modifiedLines.join("\n");
        codeTextArea.text = fullText.substring(0, firstLineStart) + newBlock + fullText.substring(lastLineEnd);
        codeTextArea.select(firstLineStart, Math.max(firstLineStart, maxPos - removedChars));
        root.updateCursorPosition();
    }

    function toggleComment() {
        var ext = root.activeFileName ? root.activeFileName.split(".").pop().toLowerCase() : "";
        var delimiter = "// ";
        if (ext === "py" || ext === "pyw" || ext === "sh" || ext === "bash" || ext === "ps1" || ext === "yaml" || ext === "yml" || ext === "toml" || ext === "rb") {
            delimiter = "# ";
        } else if (ext === "sql" || ext === "lua") {
            delimiter = "-- ";
        } else if (ext === "html" || ext === "htm" || ext === "xml") {
            delimiter = "<!-- ";
        }

        var fullText = codeTextArea.text;
        var start = codeTextArea.selectionStart;
        var end = codeTextArea.selectionEnd;
        var minPos = Math.min(start, end);
        var maxPos = Math.max(start, end);

        var firstLineStart = fullText.lastIndexOf("\n", minPos - 1) + 1;
        var lastLineEnd = fullText.indexOf("\n", maxPos);
        if (lastLineEnd === -1) lastLineEnd = fullText.length;

        var targetBlock = fullText.substring(firstLineStart, lastLineEnd);
        var lines = targetBlock.split("\n");
        var rawDelim = delimiter.trim();

        // Check if all non-empty lines already have comment
        var allCommented = true;
        for (var i = 0; i < lines.length; i++) {
            var trimmed = lines[i].trim();
            if (trimmed.length > 0 && !trimmed.startsWith(rawDelim)) {
                allCommented = false;
                break;
            }
        }

        var modifiedLines = [];
        for (var j = 0; j < lines.length; j++) {
            var line = lines[j];
            if (allCommented) {
                var idx = line.indexOf(rawDelim);
                if (idx !== -1) {
                    var before = line.substring(0, idx);
                    var after = line.substring(idx + rawDelim.length);
                    if (after.startsWith(" ")) after = after.substring(1);
                    modifiedLines.push(before + after);
                } else {
                    modifiedLines.push(line);
                }
            } else {
                var matchIndent = line.match(/^(\s*)/);
                var leadSpaces = matchIndent ? matchIndent[1] : "";
                var rest = line.substring(leadSpaces.length);
                modifiedLines.push(leadSpaces + delimiter + rest);
            }
        }

        var newBlock = modifiedLines.join("\n");
        codeTextArea.text = fullText.substring(0, firstLineStart) + newBlock + fullText.substring(lastLineEnd);
        codeTextArea.select(firstLineStart, firstLineStart + newBlock.length);
    }

    function ensureCursorVisible() {
        if (!codeTextArea || codeTextArea.cursorRectangle.height <= 0) return;
        var curY = codeTextArea.cursorRectangle.y;
        var curH = codeTextArea.cursorRectangle.height;
        var curX = codeTextArea.cursorRectangle.x;
        var viewTop = editorFlickable.contentY;
        var viewLeft = editorFlickable.contentX;
        var viewHeight = editorFlickable.height;
        var viewWidth = editorFlickable.width;
        if (viewHeight <= 0 || viewWidth <= 0) return;

        var paddingY = 24;
        var paddingX = 40;

        if (curY < viewTop + paddingY) {
            editorFlickable.contentY = Math.max(0, curY - paddingY);
        } else if (curY + curH > viewTop + viewHeight - paddingY) {
            var maxY = Math.max(0, editorFlickable.contentHeight - editorFlickable.height);
            editorFlickable.contentY = Math.min(maxY, curY + curH + paddingY - viewHeight);
        }

        if (curX < viewLeft + paddingX) {
            editorFlickable.contentX = Math.max(0, curX - paddingX);
        } else if (curX > viewLeft + viewWidth - paddingX) {
            var maxX = Math.max(0, editorFlickable.contentWidth - editorFlickable.width);
            editorFlickable.contentX = Math.min(maxX, curX + paddingX - viewWidth);
        }
    }

    function countLines(str) {
        if (!str) return 1;
        var cnt = 1;
        var len = str.length;
        for (var i = 0; i < len; i++) {
            if (str.charCodeAt(i) === 10) cnt++;
        }
        return cnt;
    }

    function updateCursorPosition() {
        if (!codeTextArea) return;
        var r = codeTextArea.cursorRectangle;
        var line = Math.max(1, Math.floor((r.y - codeTextArea.topPadding) / root.editorLineHeight) + 1);
        var col = Math.max(1, Math.floor((r.x - codeTextArea.leftPadding) / root.charWidth) + 1);
        root.cursorLine = line;
        root.cursorColumn = col;
        root.cursorPositionChanged(line, col);
    }

    Timer {
        id: diagnosticsTimer
        interval: 1000
        repeat: false
        onTriggered: {
            if (typeof backend !== "undefined" && backend && backend.check_diagnostics) {
                backend.check_diagnostics(root.activeFilePath || root.activeFileName || "", root.getCanonicalText(), root.currentLanguageId);
            }
        }
    }

    function jumpToLineAndCol(line, col) {
        if (!codeTextArea) return;
        var text = codeTextArea.text;
        var lines = text.split("\n");
        var targetLine = Math.max(1, Math.min(line, lines.length));
        var charPos = 0;
        for (var i = 0; i < targetLine - 1; i++) {
            charPos += lines[i].length + 1;
        }
        var targetCol = Math.max(1, Math.min(col || 1, lines[targetLine - 1].length + 1));
        charPos += (targetCol - 1);
        codeTextArea.cursorPosition = Math.min(charPos, text.length);
        codeTextArea.forceActiveFocus();
        root.updateCursorPosition();
        root.ensureCursorVisible();
    }

    Timer {
        id: textChangeDebounceTimer
        interval: 300
        repeat: false
        onTriggered: {
            root.totalLineCount = codeTextArea.lineCount > 0 ? codeTextArea.lineCount : countLines(codeTextArea.text);
            var canonical = root.getCanonicalText();
            if (root.currentTab) {
                root.currentTab.content = canonical;
            }
            if (codeMinimap) {
                codeMinimap.documentText = codeTextArea.text;
            }
            for (var t = 0; t < tabModel.count; t++) {
                var tab = tabModel.get(t);
                if (tab && (tab.isWebPreview || tab.languageId === "webpreview")) {
                    tabModel.setProperty(t, "content", canonical);
                }
            }
            if (typeof backend !== "undefined" && backend && backend.notify_change) {
                backend.notify_change(root.activeFilePath || "untitled.txt", canonical);
            }
        }
    }

    function handleEditorContentChanged() {
        if (root.isRestoringTab || root.isFoldingOperation) return;
        if (root.currentTab) {
            if (!root.currentTab.isDirty) {
                root.currentTab.isDirty = true;
                root.activeFileChanged(root.activeFilePath, root.activeFileName, root.currentLanguage, true);
            }
        }
        if (root.activeEditorPane && root.activeEditorPane.updatePaneScopes) {
            root.activeEditorPane.updatePaneScopes();
        }
        if (typeof textChangeDebounceTimer !== "undefined" && textChangeDebounceTimer) textChangeDebounceTimer.restart();
        if (typeof diagnosticsTimer !== "undefined" && diagnosticsTimer) diagnosticsTimer.restart();
    }

    function createNewFile() {
        var newNum = tabModel.count + 1;
        var title = "Untitled-" + newNum;
        var newIdx = tabModel.count;

        tabModel.append({
                fileId: "tab_" + Date.now() + "_" + newNum,
                title: title,
                path: "",
                content: "",
                isDirty: true,
                languageName: "Plain Text",
                languageId: "text",
                cursorPos: 0,
                scrollX: 0,
                scrollY: 0
            });

        switchToTab(newIdx);
    }

    function loadFile(path, content) {
        console.time("[Timing] loadFile total");
        for (var i = 0; i < tabModel.count; i++) {
            if (tabModel.get(i).path === path) {
                switchToTab(i);
                console.timeEnd("[Timing] loadFile total");
                return;
            }
        }

        var fileName = path.split("/").pop().split("\\").pop();
        var langObj = LanguageRegistry.detectLanguage(fileName);
        var newIdx = tabModel.count;

        root.isInitialTextLoading = true;
        console.time("[Timing] tabModel.append");
        tabModel.append({
                fileId: "file_" + Date.now(),
                title: fileName,
                path: path,
                content: "",
                isDirty: false,
                languageName: langObj.name,
                languageId: langObj.id,
                cursorPos: 0,
                scrollX: 0,
                scrollY: 0
            });
        console.timeEnd("[Timing] tabModel.append");

        console.time("[Timing] switchToTab");
        switchToTab(newIdx);
        console.timeEnd("[Timing] switchToTab");

        if (root.activeEditorPane && root.activeEditorPane.codeTextArea) {
            root.activeEditorPane.codeTextArea.text = content;
            root.activeEditorPane.paneTotalLineCount = root.countLines(content);
            root.activeEditorPane.updatePaneScopes();
        }
        root.isInitialTextLoading = false;

        console.timeEnd("[Timing] loadFile total");
    }

    function openWhiteboardTab() {
        for (var i = 0; i < tabModel.count; i++) {
            if (tabModel.get(i).isWhiteboard) {
                switchToTab(i);
                return;
            }
        }

        var newIdx = tabModel.count;
        tabModel.append({
                fileId: "whiteboard_" + Date.now(),
                title: "Architecture Plan",
                path: "whiteboard://plan",
                content: "",
                isDirty: false,
                languageName: "Whiteboard Canvas",
                languageId: "whiteboard",
                isWhiteboard: true,
                cursorPos: 0
            });

        switchToTab(newIdx);
    }

    function openWebPreviewTab() {
        var currentContent = codeTextArea ? (codeTextArea.text || "") : "";
        var currentExt = root.activeFileName ? root.activeFileName.split(".").pop().toLowerCase() : "";
        var isMd = (root.currentLanguageId === "markdown" || currentExt === "md");
        var activePath = root.activeFilePath || "";

        for (var i = 0; i < tabModel.count; i++) {
            var t = tabModel.get(i);
            if (t && (t.isWebPreview || t.languageId === "webpreview")) {
                t.content = currentContent;
                t.isMarkdown = isMd;
                t.sourcePath = activePath;
                switchToTab(i);
                return;
            }
        }

        var newIdx = tabModel.count;
        tabModel.append({
                fileId: "webpreview_" + Date.now(),
                title: isMd ? "Markdown Preview" : "Live HTML Preview",
                path: activePath ? activePath : "preview://live",
                sourcePath: activePath,
                content: currentContent,
                isDirty: false,
                languageName: isMd ? "Markdown Preview" : "Live HTML Preview",
                languageId: "webpreview",
                isWebPreview: true,
                isMarkdown: isMd,
                cursorPos: 0
            });

        switchToTab(newIdx);
    }

    // =========================================================================
    // CODE FOLDING / WARP FUNCTIONS (VS CODE STYLE - HIGH PERFORMANCE)
    // =========================================================================
    property var foldedMap: ({})
    property int foldVersion: 0

    function isLineFolded(lineNum) {
        return foldedMap[lineNum] !== undefined;
    }

    function isFoldableLine(lineNum) {
        return (root.foldableLinesMap && root.foldableLinesMap[lineNum] === true) || (foldedMap && foldedMap[lineNum] !== undefined);
    }

    function getCanonicalText() {
        if (!codeTextArea) return "";
        var keys = Object.keys(root.foldedMap);
        if (keys.length === 0) {
            return codeTextArea.text;
        }
        var lines = codeTextArea.text.split("\n");
        var reconstructed = [];
        for (var i = 0; i < lines.length; i++) {
            var curLine = lines[i];
            var lineNum = i + 1;
            if (curLine.endsWith(" /* ... */") || curLine.endsWith(" ...")) {
                var cleanLine = curLine.replace(/ \/\* \.\.\. \*\/$/, "").replace(/ \.\.\.$/, "");
                reconstructed.push(cleanLine);
                var fold = root.foldedMap[lineNum];
                if (fold && fold.hiddenLines) {
                    for (var h = 0; h < fold.hiddenLines.length; h++) {
                        reconstructed.push(fold.hiddenLines[h]);
                    }
                }
            } else {
                reconstructed.push(curLine);
            }
        }
        return reconstructed.join("\n");
    }

    function recalculateFoldableLines() {
        var text = codeTextArea.text;
        if (!text) {
            root.foldableLinesMap = {};
            return;
        }
        var map = {};
        var tabSize = (theme && theme.tabSize) ? theme.tabSize : 4;
        var lines = text.split("\n");
        var total = Math.min(lines.length, 3000);

        for (var i = 0; i < total - 1; i++) {
            var curL = lines[i];
            var trimmed = curL.trim();
            if (trimmed.length === 0) continue;

            if (trimmed.endsWith("{") || trimmed.endsWith("(") || trimmed.endsWith("[") || trimmed.endsWith(":")) {
                map[i + 1] = true;
                continue;
            }

            var matchLead = curL.match(/^(\s*)/);
            var curLead = matchLead ? matchLead[1].replace(/\t/g, " ".repeat(tabSize)).length : 0;
            for (var n = i + 1; n < Math.min(total, i + 6); n++) {
                var nextL = lines[n];
                if (nextL.trim().length > 0) {
                    var nextMatch = nextL.match(/^(\s*)/);
                    var nextLead = nextMatch ? nextMatch[1].replace(/\t/g, " ".repeat(tabSize)).length : 0;
                    if (nextLead > curLead) {
                        map[i + 1] = true;
                    }
                    break;
                }
            }
        }
        root.foldableLinesMap = map;
    }

    function getFoldChevron(lineNum) {
        if (isLineFolded(lineNum)) return "▶";
        if (isFoldableLine(lineNum)) return "▼";
        return "";
    }

    function toggleFoldAtLine(lineNum) {
        if (lineNum < 1 || !codeTextArea) return;
        var text = codeTextArea.text;
        if (!text) return;
        var lines = text.split("\n");
        if (lineNum > lines.length) return;

        var startIdx = lineNum - 1;
        var curLine = lines[startIdx];

        root.isFoldingOperation = true;

        if (root.isLineFolded(lineNum)) {
            // UNFOLD: Restore hidden lines
            var foldInfo = root.foldedMap[lineNum];
            var restoredCount = 0;
            if (foldInfo && foldInfo.hiddenLines) {
                restoredCount = foldInfo.hiddenLines.length;
                var cleanHeader = curLine.replace(/ \/\* \.\.\. \*\/$/, "").replace(/ \.\.\.$/, "");
                lines[startIdx] = cleanHeader;
                var before = lines.slice(0, startIdx + 1);
                var after = lines.slice(startIdx + 1);
                lines = before.concat(foldInfo.hiddenLines).concat(after);
            }
            var newMap = {};
            for (var k in root.foldedMap) {
                var kn = parseInt(k);
                if (kn === lineNum) continue;
                if (kn > lineNum) {
                    newMap[kn + restoredCount] = root.foldedMap[k];
                } else {
                    newMap[kn] = root.foldedMap[k];
                }
            }
            root.foldedMap = newMap;
            codeTextArea.text = lines.join("\n");
        } else {
            // FOLD: Find block boundary and visually collapse
            var tabSize = (theme && theme.tabSize) ? theme.tabSize : 4;
            var curLeadMatch = curLine.match(/^(\s*)/);
            var baseLead = curLeadMatch ? curLeadMatch[1].replace(/\t/g, " ".repeat(tabSize)).length : 0;
            var endIdx = startIdx + 1;

            while (endIdx < lines.length) {
                var nextL = lines[endIdx];
                if (nextL.trim().length > 0) {
                    var nextLeadMatch = nextL.match(/^(\s*)/);
                    var nextLead = nextLeadMatch ? nextLeadMatch[1].replace(/\t/g, " ".repeat(tabSize)).length : 0;
                    var trimmedNext = nextL.trim();
                    if (nextLead <= baseLead && !trimmedNext.startsWith("}") && !trimmedNext.startsWith(")") && !trimmedNext.startsWith("]")) {
                        break;
                    }
                    if (nextLead <= baseLead && (trimmedNext.startsWith("}") || trimmedNext.startsWith(")") || trimmedNext.startsWith("]"))) {
                        endIdx++;
                        break;
                    }
                }
                endIdx++;
            }

            while (endIdx > startIdx + 1 && lines[endIdx - 1].trim().length === 0) {
                endIdx--;
            }

            if (endIdx > startIdx + 1) {
                var hidden = lines.slice(startIdx + 1, endIdx);
                var foldObj = {
                    startLine: lineNum,
                    endLine: endIdx,
                    lineCount: endIdx - lineNum,
                    hiddenLines: hidden
                };
                var hiddenCount = hidden.length;
                var newFoldMap = {};
                for (var fKey in root.foldedMap) {
                    var fkn = parseInt(fKey);
                    if (fkn > lineNum) {
                        newFoldMap[fkn - hiddenCount] = root.foldedMap[fKey];
                    } else {
                        newFoldMap[fkn] = root.foldedMap[fKey];
                    }
                }
                newFoldMap[lineNum] = foldObj;
                root.foldedMap = newFoldMap;

                lines[startIdx] = curLine + " /* ... */";
                lines.splice(startIdx + 1, hidden.length);
                codeTextArea.text = lines.join("\n");
            }
        }

        root.isFoldingOperation = false;
        root.totalLineCount = lines.length;
        root.foldVersion++;
    }

    function switchToTab(index) {
        if (index < 0 || index >= tabModel.count) {
            return;
        }

        if (typeof autocompleteTimer !== "undefined" && autocompleteTimer) autocompleteTimer.stop();
        if (typeof textChangeDebounceTimer !== "undefined" && textChangeDebounceTimer) textChangeDebounceTimer.stop();
        if (typeof diagnosticsTimer !== "undefined" && diagnosticsTimer) diagnosticsTimer.stop();
        if (typeof suggestionModel !== "undefined" && suggestionModel) suggestionModel.clear();

        root.activeTabIndex = index;
        if (tabEditorStack) {
            tabEditorStack.currentIndex = index;
        }

        var newTab = tabModel.get(index);
        if (!newTab) return;

        root.currentLanguage = newTab.languageName || "Plain Text";
        root.currentLanguageId = newTab.languageId || "text";

        if (typeof backend !== "undefined" && backend && backend.set_active_file) {
            backend.set_active_file(newTab.path || newTab.title || "", newTab.languageId || "text");
        }

        if (!newTab.isWhiteboard && !newTab.isWebPreview) {
            if (root.codeTextArea) {
                if (typeof backend !== "undefined" && backend && backend.register_text_area) {
                    backend.register_text_area(root.codeTextArea, newTab.path || "", newTab.languageId || "text");
                }
                root.codeTextArea.forceActiveFocus();
                root.updateCursorPosition();
                root.ensureCursorVisible();
            }
            if (root.indentGuidesCanvas) {
                root.indentGuidesCanvas.requestPaint();
            }
            if (codeMinimap && root.codeTextArea) {
                codeMinimap.documentText = root.codeTextArea.text;
            }
        }

        root.activeFileChanged(newTab.path || "", newTab.title || "", root.currentLanguage, newTab.isDirty || false);
        diagnosticsTimer.restart();
    }

    function syncSecondaryEditor() {
        if (root.secondaryTab && typeof secCodeTextArea !== "undefined" && secCodeTextArea) {
            secCodeTextArea.text = root.secondaryTab.content || "";
            if (typeof backend !== "undefined" && backend) {
                if (backend.register_secondary_text_area) {
                    backend.register_secondary_text_area(secCodeTextArea);
                }
                if (backend.set_secondary_file) {
                    backend.set_secondary_file(root.secondaryTab.path || root.secondaryTab.title || "main.py");
                }
            }
        }
    }

    function toggleSplitEditor() {
        if (root.isSplitEditor) {
            root.isSplitEditor = false;
        } else {
            if (tabModel.count > 1) {
                root.secondaryTabIndex = (root.activeTabIndex === 0 ? 1 : 0);
            } else {
                root.secondaryTabIndex = Math.max(0, root.activeTabIndex);
            }
            root.isSplitEditor = true;
            syncSecondaryEditor();
        }
    }

    function closeTab(index) {
        if (index < 0 || index >= tabModel.count) return;

        var wasActive = (index === root.activeTabIndex);
        var wasSecondary = (index === root.secondaryTabIndex);

        tabModel.remove(index);

        if (tabModel.count === 0) {
            root.isSplitEditor = false;
            root.activeTabIndex = -1;
            root.secondaryTabIndex = -1;
            root.isRestoringTab = true;
            try {
                if (codeTextArea) {
                    codeTextArea.text = "";
                }
                root.totalLineCount = 0;
                if (codeMinimap) {
                    codeMinimap.documentText = "";
                }
                root.currentLanguage = "Plain Text";
                root.currentLanguageId = "text";
                root.activeFileChanged("", "", "Plain Text", false);
                if (typeof backend !== "undefined" && backend && backend.set_active_file) {
                    backend.set_active_file("", "text");
                }
                indentGuidesCanvas.requestPaint();
            } finally {
                root.isRestoringTab = false;
            }
            return;
        }

        // Adjust activeTabIndex for primary pane
        if (wasActive) {
            var newActive = Math.min(index, tabModel.count - 1);
            switchToTab(newActive);
        } else if (root.activeTabIndex > index) {
            root.activeTabIndex--;
        }

        // Adjust secondaryTabIndex for secondary split pane
        if (root.isSplitEditor) {
            if (wasSecondary) {
                root.secondaryTabIndex = Math.min(index, tabModel.count - 1);
                syncSecondaryEditor();
            } else if (root.secondaryTabIndex > index) {
                root.secondaryTabIndex--;
            }
        }
    }

    function saveCurrentFile() {
        if (!root.currentTab) return false;

        if (!root.currentTab.path) {
            return false;
        }

        if (typeof backend !== "undefined" && backend) {
            backend.save_file(root.currentTab.path, root.getCanonicalText());
            tabModel.setProperty(root.activeTabIndex, "isDirty", false);
            root.activeFileChanged(root.activeFilePath, root.activeFileName, root.currentLanguage, false);
            return true;
        }
        return false;
    }

    function saveAsCurrentFile(newPath) {
        if (!newPath) return;

        var cleanPath = newPath;
        if (cleanPath.startsWith("file:///")) {
            cleanPath = cleanPath.replace("file:///", "");
        }

        var fileName = cleanPath.split("/").pop().split("\\").pop();
        var langObj = LanguageRegistry.detectLanguage(fileName);

        if (root.currentTab) {
            root.currentTab.path = cleanPath;
            root.currentTab.title = fileName;
            root.currentTab.languageName = langObj.name;
            root.currentTab.languageId = langObj.id;
            tabModel.setProperty(root.activeTabIndex, "isDirty", false);
            root.currentLanguage = langObj.name;
            root.currentLanguageId = langObj.id;
        }

        if (typeof backend !== "undefined" && backend) {
            backend.save_file(cleanPath, root.getCanonicalText());
            if (backend.register_text_area) {
                backend.register_text_area(codeTextArea);
            }
            root.activeFileChanged(cleanPath, fileName, root.currentLanguage, false);
        }
    }

    function undo() { codeTextArea.undo(); }
    function redo() { codeTextArea.redo(); }

    function insertSnippet(code) {
        var pos = codeTextArea.cursorPosition;
        codeTextArea.insert(pos, code);
        codeTextArea.cursorPosition = pos + code.length;
        codeTextArea.forceActiveFocus();
    }

    function showFind(showReplace) {
        findReplaceBar.isReplaceMode = showReplace;
        if (codeTextArea && codeTextArea.selectedText && codeTextArea.selectedText.indexOf("\n") === -1) {
            findReplaceBar.setFindText(codeTextArea.selectedText);
        }
        findReplaceBar.visible = true;
        findReplaceBar.focusInput();
        updateFindMatches(findReplaceBar.findText, findReplaceBar.matchCase);
    }

    function updateFindMatches(pattern, matchCase) {
        if (!pattern || !codeTextArea) {
            findReplaceBar.totalMatches = 0;
            findReplaceBar.currentMatchIndex = 0;
            return [];
        }
        var text = codeTextArea.text;
        var searchPattern = matchCase ? pattern : pattern.toLowerCase();
        var searchText = matchCase ? text : text.toLowerCase();
        var matches = [];
        var pos = 0;
        while ((pos = searchText.indexOf(searchPattern, pos)) !== -1) {
            matches.push(pos);
            pos += searchPattern.length;
        }
        findReplaceBar.totalMatches = matches.length;
        return matches;
    }

    function findNext(pattern, matchCase) {
        if (!pattern || !codeTextArea) return;
        var text = codeTextArea.text;
        var startPos = codeTextArea.selectionEnd || codeTextArea.cursorPosition;
        var matches = updateFindMatches(pattern, matchCase);
        if (matches.length === 0) return;

        var nextIdx = -1;
        var matchIndex = 0;
        for (var i = 0; i < matches.length; i++) {
            if (matches[i] >= startPos) {
                nextIdx = matches[i];
                matchIndex = i;
                break;
            }
        }
        if (nextIdx === -1) {
            nextIdx = matches[0];
            matchIndex = 0;
        }

        findReplaceBar.currentMatchIndex = matchIndex;
        codeTextArea.select(nextIdx, nextIdx + pattern.length);
        root.updateCursorPosition();
        root.ensureCursorVisible();
    }

    function findPrev(pattern, matchCase) {
        if (!pattern || !codeTextArea) return;
        var text = codeTextArea.text;
        var startPos = codeTextArea.selectionStart !== undefined ? codeTextArea.selectionStart : codeTextArea.cursorPosition;
        var matches = updateFindMatches(pattern, matchCase);
        if (matches.length === 0) return;

        var prevIdx = -1;
        var matchIndex = 0;
        for (var i = matches.length - 1; i >= 0; i--) {
            if (matches[i] < startPos) {
                prevIdx = matches[i];
                matchIndex = i;
                break;
            }
        }
        if (prevIdx === -1) {
            prevIdx = matches[matches.length - 1];
            matchIndex = matches.length - 1;
        }

        findReplaceBar.currentMatchIndex = matchIndex;
        codeTextArea.select(prevIdx, prevIdx + pattern.length);
        root.updateCursorPosition();
        root.ensureCursorVisible();
    }

    function replaceNext(pattern, replacement, matchCase) {
        if (!pattern || !codeTextArea) return;
        if (codeTextArea.selectedText && (matchCase ? codeTextArea.selectedText === pattern : codeTextArea.selectedText.toLowerCase() === pattern.toLowerCase())) {
            var start = codeTextArea.selectionStart;
            codeTextArea.remove(start, codeTextArea.selectionEnd);
            codeTextArea.insert(start, replacement || "");
            codeTextArea.select(start, start + (replacement ? replacement.length : 0));
        }
        findNext(pattern, matchCase);
    }

    function replaceAll(pattern, replacement, matchCase) {
        if (!pattern || !codeTextArea) return;
        var text = codeTextArea.text;
        var regex = new RegExp(escapeRegExp(pattern), matchCase ? "g" : "gi");
        codeTextArea.text = text.replace(regex, replacement || "");
        updateFindMatches(pattern, matchCase);
    }

    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // =========================================================================
    // INTELLIGENT LANGUAGE-AWARE AUTOCOMPLETE
    // =========================================================================
    function triggerCompletionRequest() {
        var pos = codeTextArea.cursorPosition;
        if (pos <= 0) {
            suggestionModel.clear();
            return;
        }

        // Fast O(1) local substring extraction
        var chunk = codeTextArea.getText(Math.max(0, pos - 50), pos);
        var match = chunk.match(/[a-zA-Z0-9_]+$/);
        var prefix = match ? match[0] : "";

        if (!prefix || prefix.length < 1) {
            suggestionModel.clear();
            return;
        }

        var prefixLower = prefix.toLowerCase();
        var matches = [];
        var seen = {};

        // 0. Match Snippets for active programming language
        var snippets = SnippetManager.getSnippetsForLanguage(root.currentLanguageId) || [];
        for (var s = 0; s < snippets.length; s++) {
            var snip = snippets[s];
            if (snip.label.toLowerCase().startsWith(prefixLower) && snip.label !== prefix) {
                matches.push({ label: snip.label, insertText: snip.insertText, kind: "snippet", priority: 25 });
                seen[snip.label] = true;
            }
        }

        // 1. Match Keywords for active programming language
        var langKeywords = LanguageRegistry.getKeywords(root.currentLanguageId);
        for (var k = 0; k < langKeywords.length; k++) {
            var kw = langKeywords[k];
            var kwLower = kw.toLowerCase();
            if (kwLower.startsWith(prefixLower) && kw !== prefix && !seen[kw]) {
                matches.push({ label: kw, insertText: kw, kind: "keyword", priority: 10 });
                seen[kw] = true;
            }
        }

        // 2. Fast local neighborhood symbol extraction (+/- 1000 chars)
        var nearbyText = codeTextArea.getText(Math.max(0, pos - 1000), Math.min(codeTextArea.length, pos + 1000));
        var docWords = nearbyText.match(/[a-zA-Z_][a-zA-Z0-9_]{2,}/g) || [];
        for (var w = 0; w < docWords.length; w++) {
            var word = docWords[w];
            if (!seen[word] && word.toLowerCase().startsWith(prefixLower) && word !== prefix) {
                matches.push({ label: word, insertText: word, kind: "identifier", priority: 5 });
                seen[word] = true;
            }
        }

        // Sort: exact prefix starts first, then shorter lengths
        matches.sort(function(a, b) {
                if (b.priority !== a.priority) return b.priority - a.priority;
                return a.label.length - b.label.length;
            });

        suggestionModel.clear();
        var maxSuggestions = Math.min(12, matches.length);
        for (var m = 0; m < maxSuggestions; m++) {
            suggestionModel.append(matches[m]);
        }
        autocompletePopup.selectedSuggestionIndex = 0;

        // Query Backend LSP asynchronously with canonical text synchronization
        if (typeof backend !== "undefined" && backend && backend.request_completion) {
            backend.request_completion(root.activeFilePath || "untitled.txt", root.cursorLine - 1, root.cursorColumn - 1, root.getCanonicalText());
        }
    }

    function showCompletions(suggestions) {
        if (!suggestions || suggestions.length === 0) return;
        var pos = codeTextArea.cursorPosition;
        if (pos <= 0) return;

        var chunk = codeTextArea.getText(Math.max(0, pos - 50), pos);
        var match = chunk.match(/[a-zA-Z0-9_]+$/);
        var prefix = match ? match[0] : "";
        if (!prefix || prefix.length < 1) return;
        var prefixLower = prefix.toLowerCase();

        // O(1) seen set for fast duplicate filtering
        var seen = {};
        for (var s = 0; s < suggestionModel.count; s++) {
            seen[suggestionModel.get(s).label] = true;
        }

        var toAppend = [];
        for (var i = 0; i < suggestions.length && (suggestionModel.count + toAppend.length) < 14; i++) {
            var item = suggestions[i];
            var label = item.label || item;
            var ins = item.insertText || label;

            if (!seen[label] && label.toLowerCase().startsWith(prefixLower) && label !== prefix) {
                seen[label] = true;
                toAppend.push({ label: label, insertText: ins, kind: item.type || "lsp" });
            }
        }

        for (var a = 0; a < toAppend.length; a++) {
            suggestionModel.append(toAppend[a]);
        }
    }

    function applySuggestion(word, kind) {
        if (!word) return;
        var pos = codeTextArea.cursorPosition;
        var text = codeTextArea.text;
        var prefixStart = pos;
        while (prefixStart > 0 && /[a-zA-Z0-9_]/.test(text[prefixStart - 1])) {
            prefixStart--;
        }

        var isSnippet = kind === "snippet" || word.indexOf("${") !== -1;
        var expanded = isSnippet ? SnippetManager.expandSnippetTemplate(word) : { text: word, cursorOffset: word.length };
        var insertStr = expanded.text;
        var targetOffset = expanded.cursorOffset;

        var removeStart = prefixStart;
        var removeEnd = pos;

        // Check if there is a leading '<' right before prefixStart
        var hasLeadingAngle = (prefixStart > 0 && text[prefixStart - 1] === "<");
        // Check if there is a trailing '>' right after current pos
        var hasTrailingAngle = (pos < text.length && text[pos] === ">");

        if (hasLeadingAngle && insertStr.startsWith("<")) {
            removeStart = prefixStart - 1;
        } else if (hasLeadingAngle && !insertStr.startsWith("<")) {
            var isHtmlContext = (root.currentLanguageId === "html" || root.currentLanguageId === "xml" || root.currentLanguageId === "qml" || (root.activeFileName && (root.activeFileName.endsWith(".html") || root.activeFileName.endsWith(".htm") || root.activeFileName.endsWith(".jsx") || root.activeFileName.endsWith(".tsx"))));
            if (isHtmlContext) {
                removeStart = prefixStart - 1;
                insertStr = "<" + insertStr + ">\n    \n</" + insertStr + ">";
                targetOffset = insertStr.indexOf("\n    ") + 5;
            }
        }

        if (hasTrailingAngle && (insertStr.startsWith("<") || hasLeadingAngle)) {
            removeEnd = pos + 1;
        }

        codeTextArea.remove(removeStart, removeEnd);
        codeTextArea.insert(removeStart, insertStr);
        codeTextArea.cursorPosition = removeStart + targetOffset;
        suggestionModel.clear();
        codeTextArea.forceActiveFocus();
    }

    function toggleExtraCursor(charPos) {
        if (charPos < 0 || charPos > codeTextArea.text.length) return;
        var arr = root.extraCursors.slice();
        var idx = arr.indexOf(charPos);
        if (idx !== -1) {
            arr.splice(idx, 1);
        } else {
            arr.push(charPos);
        }
        root.extraCursors = arr;
    }

    function addNextOccurrenceCursor() {
        var text = codeTextArea.text;
        var selText = codeTextArea.selectedText;
        var curPos = codeTextArea.cursorPosition;

        if (!selText || selText.length === 0) {
            var wordStart = curPos;
            while (wordStart > 0 && /[a-zA-Z0-9_]/.test(text[wordStart - 1])) wordStart--;
            var wordEnd = curPos;
            while (wordEnd < text.length && /[a-zA-Z0-9_]/.test(text[wordEnd])) wordEnd++;
            if (wordEnd > wordStart) {
                codeTextArea.select(wordStart, wordEnd);
                selText = text.substring(wordStart, wordEnd);
            } else {
                return;
            }
        }

        var searchStart = codeTextArea.selectionEnd;
        var arr = root.extraCursors.slice();
        if (arr.length > 0) {
            for (var i = 0; i < arr.length; i++) {
                searchStart = Math.max(searchStart, arr[i] + selText.length);
            }
        }

        var nextIdx = text.indexOf(selText, searchStart);
        if (nextIdx === -1) {
            nextIdx = text.indexOf(selText, 0);
        }

        if (nextIdx !== -1 && nextIdx !== codeTextArea.selectionStart && arr.indexOf(nextIdx) === -1) {
            arr.push(nextIdx);
            root.extraCursors = arr;
        }
    }

    function openColorPickerAtCursor() {
        var pos = codeTextArea.cursorPosition;
        var text = codeTextArea.text;
        var lineStart = text.lastIndexOf("\n", pos - 1) + 1;
        var lineEnd = text.indexOf("\n", pos);
        if (lineEnd === -1) lineEnd = text.length;
        var lineText = text.substring(lineStart, lineEnd);

        var hexMatch = lineText.match(/#([0-9a-fA-F]{3,8})/);
        var initialHex = "#0078d4";
        var colorStart = -1;
        var colorEnd = -1;

        if (hexMatch) {
            var idx = lineText.indexOf(hexMatch[0]);
            colorStart = lineStart + idx;
            colorEnd = colorStart + hexMatch[0].length;
            initialHex = hexMatch[0];
        }

        colorPickerPopup.targetStart = colorStart;
        colorPickerPopup.targetEnd = colorEnd;
        colorPickerPopup.openAtColor(initialHex);

        var r = codeTextArea.cursorRectangle;
        var pt = codeTextArea.mapToItem(textAreaContainer, r.x, r.y + r.height + 4);
        colorPickerPopup.x = Math.min(textAreaContainer.width - colorPickerPopup.width - 10, Math.max(10, pt.x));
        colorPickerPopup.y = (pt.y + colorPickerPopup.height > textAreaContainer.height - 10) ? Math.max(10, pt.y - colorPickerPopup.height - codeTextArea.cursorRectangle.height - 8) : Math.max(10, pt.y);
        colorPickerPopup.visible = true;
    }
}
