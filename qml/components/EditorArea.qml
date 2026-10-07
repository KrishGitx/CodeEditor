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
    property alias tabModel: tabModel

    property int activeTabIndex: -1
    property alias tabCount: tabModel.count
    property int dirtyVersion: 0
    readonly property var currentTab: {
        var _ = dirtyVersion;
        return (activeTabIndex >= 0 && tabModel.count > activeTabIndex) ? tabModel.get(activeTabIndex) : null;
    }
    property string activeFilePath: currentTab ? (currentTab.path || "") : ""
    property string activeFileName: currentTab ? (currentTab.title || "") : ""
    readonly property bool isCurrentFileDirty: {
        var _ = dirtyVersion;
        return (currentTab && currentTab.isDirty === true);
    }
    property string currentLanguage: currentTab ? (currentTab.languageName || "Plain Text") : "Plain Text"
    property string currentLanguageId: currentTab ? (currentTab.languageId || "text") : "text"
    property var extraCursors: [] // Array of character indices for Multi-Cursor editing
    property var multiCursorUndoStack: []
    property var multiCursorRedoStack: []
    property bool copiedWholeLine: false
    property string clipboardWholeLineText: ""
    property var activeSnippetStops: []
    property int activeSnippetStopIndex: -1
            property var selectionOccurrences: []

    Shortcut {
        sequence: "Ctrl+P"
        onActivated: quickOpenPalette.openQuickOpen()
    }

    Shortcut {
        sequence: "Ctrl+G"
        onActivated: quickOpenPalette.openGotoLine(root.cursorLine)
    }
    

    Shortcut {
        sequence: "F2"
        onActivated: root.triggerRenameSymbol()
    }


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

    function getActiveEditorContent() {
        if (root.activeEditorPane && root.activeEditorPane.codeTextArea) {
            return root.activeEditorPane.codeTextArea.text;
        }
        if (root.currentTab) {
            return root.currentTab.content || "";
        }
        return "";
    }
    function setActiveEditorContent(val) {
        if (root.currentTab) {
            root.currentTab.content = val;
            tabModel.setProperty(root.activeTabIndex, "content", val);
        }
        if (root.activeEditorPane && root.activeEditorPane.codeTextArea) {
            root.activeEditorPane.codeTextArea.text = val;
        }
    }
    function dispatchEditorKey(key, modifiers, text) {
        if (root.activeEditorPane && root.activeEditorPane.handleEditorKey) {
            var ev = {
                key: key,
                modifiers: modifiers !== undefined ? modifiers : Qt.NoModifier,
                text: text || "",
                accepted: false
            };
            root.activeEditorPane.handleEditorKey(ev);
            return ev.accepted;
        }
        return false;
    }

    function setActiveEditorCursorPosition(pos) {
        if (root.activeEditorPane && root.activeEditorPane.codeTextArea) {
            root.activeEditorPane.codeTextArea.cursorPosition = pos;
        }
    }

    function setEditorZoom(newSize) {
        if (typeof theme !== "undefined" && theme) {
            theme.editorFontSize = newSize;
        }
    }

    property bool isSyncingSecondary: false
    property bool isFormatting: false
    property int formatRequestSeq: 0
    property string activeFormatReqId: ""

    Connections {
        target: (typeof backend !== "undefined" && backend) ? backend : null
        function onFormattingCompleted(reqId, filePath, success, formattedCode, message, available, extensionId) {
            if (root.activeFormatReqId !== "" && reqId !== root.activeFormatReqId) {
                return;
            }
            root.isFormatting = false;
            root.activeFormatReqId = "";

            if (!codeTextArea) return;
            var currentText = codeTextArea.text;

            if (available === false) {
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification(message || "No formatter available for this language.", "warning", "Formatter");
                }
                return;
            }

            if (!success) {
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification(message || "Formatting failed.", "error", "Formatter");
                }
                return;
            }

            var formattedText = formattedCode || currentText;
            if (formattedText === currentText) {
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification(message || "Document is already formatted.", "info", "Formatter", 2500);
                }
                return;
            }

            var curLine = root.cursorLine;
            var curCol = root.cursorColumn;
            var oldScrollX = editorFlickable ? editorFlickable.contentX : 0;
            var oldScrollY = editorFlickable ? editorFlickable.contentY : 0;

            var applied = false;
            if (typeof backend !== "undefined" && backend && backend.apply_formatted_text) {
                applied = backend.apply_formatted_text(codeTextArea, formattedText);
            }
            if (!applied) {
                codeTextArea.text = formattedText;
            }

            // Mark document dirty
            if (root.activeTabIndex >= 0 && root.activeTabIndex < tabModel.count) {
                tabModel.setProperty(root.activeTabIndex, "isDirty", true);
            }
            root.isCurrentFileDirty = true;

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

            // Keep viewport steady
            if (editorFlickable) {
                editorFlickable.contentX = Math.max(0, oldScrollX);
                editorFlickable.contentY = Math.max(0, oldScrollY);
            }
            root.updateCursorPosition();

            // Refresh scopes and folding after format
            if (root.activeEditorPane) {
                root.activeEditorPane.updatePaneScopes();
            }
            root.recalculateFoldableLines();

            if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                mainWindow.showNotification(message || "Formatted successfully.", "success", "Formatter", 2500);
            }
        }
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
        var _dep = (fontMetrics.font.pixelSize || 13) + (fontMetrics.height || 0) + (typeof theme !== "undefined" && theme ? (theme.editorFontSize || 13) : 0);
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
        var total = lines.length;
        if (total === 0) return [];

        function getRawLineIndent(line) {
            var trimmed = line.trim();
            if (trimmed.length === 0) return -1;
            var cols = 0;
            for (var i = 0; i < line.length; i++) {
                var ch = line.charAt(i);
                if (ch === ' ') cols += 1;
                else if (ch === '\t') cols += tabSize - (cols % tabSize);
                else break;
            }
            return Math.floor(cols / tabSize);
        }

        var stack = [];
        var scopes = [];
        var inBlockComment = false;
        var inTripleQuote = false;
        var tripleQuoteChar = '';

        for (var l = 0; l < total; l++) {
            var line = lines[l];
            var rawIndent = getRawLineIndent(line);
            var inStr = false;
            var strQuote = '';

            for (var c = 0; c < line.length; c++) {
                var char = line.charAt(c);
                var nextChar = c + 1 < line.length ? line.charAt(c + 1) : '';

                if (inBlockComment) {
                    if (char === '*' && nextChar === '/') {
                        inBlockComment = false;
                        c++;
                    }
                    continue;
                }

                if (inTripleQuote) {
                    if (char === tripleQuoteChar && nextChar === tripleQuoteChar && c + 2 < line.length && line.charAt(c + 2) === tripleQuoteChar) {
                        inTripleQuote = false;
                        c += 2;
                    }
                    continue;
                }

                if (inStr) {
                    if (char === '\\') {
                        c++;
                    } else if (char === strQuote) {
                        inStr = false;
                    }
                    continue;
                }

                if (char === '/' && nextChar === '*') {
                    inBlockComment = true;
                    c++;
                    continue;
                }
                if (char === '/' && nextChar === '/') break;
                if (char === '#') break;

                if ((char === '"' || char === '\'') && nextChar === char && c + 2 < line.length && line.charAt(c + 2) === char) {
                    inTripleQuote = true;
                    tripleQuoteChar = char;
                    c += 2;
                    continue;
                }

                if (char === '"' || char === '\'' || char === '`') {
                    inStr = true;
                    strQuote = char;
                    continue;
                }

                if (char === '{') {
                    var blockIndent = Math.max(0, rawIndent >= 0 ? rawIndent : 0);
                    stack.push({ startLine: l, level: blockIndent });
                } else if (char === '}') {
                    if (stack.length > 0) {
                        var top = stack.pop();
                        if (l >= top.startLine) {
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

    function computeGuideSegmentsForText(docText) {
        if (!docText) return [];
        var tabSize = (typeof theme !== "undefined" && theme && theme.tabSize) ? theme.tabSize : 4;
        var lines = docText.split("\n");
        var total = lines.length;
        if (total === 0) return [];

        function getRawLineIndent(line) {
            var trimmed = line.trim();
            if (trimmed.length === 0) return -1;
            var cols = 0;
            for (var i = 0; i < line.length; i++) {
                var ch = line.charAt(i);
                if (ch === ' ') cols += 1;
                else if (ch === '\t') cols += tabSize - (cols % tabSize);
                else break;
            }
            return Math.floor(cols / tabSize);
        }

        function isCommentOnlyLine(line) {
            var trimmed = line.trim();
            return trimmed.startsWith("//") || trimmed.startsWith("#") || trimmed.startsWith("/*") || trimmed.startsWith("*");
        }

        var lineIndents = new Array(total);
        var lineHasClosingBrace = new Array(total);
        var lineHasOpeningBrace = new Array(total);
        var lineEndsWithColon = new Array(total);

        var inBlockComment = false;
        var inTripleQuote = false;
        var tripleQuoteChar = '';

        for (var l = 0; l < total; l++) {
            var line = lines[l];
            lineIndents[l] = getRawLineIndent(line);
            lineHasClosingBrace[l] = false;
            lineHasOpeningBrace[l] = false;
            var trimmed = line.trim();
            lineEndsWithColon[l] = trimmed.endsWith(":");

            var inStr = false;
            var strQuote = '';

            for (var c = 0; c < line.length; c++) {
                var char = line.charAt(c);
                var nextChar = c + 1 < line.length ? line.charAt(c + 1) : '';

                if (inBlockComment) {
                    if (char === '*' && nextChar === '/') {
                        inBlockComment = false;
                        c++;
                    }
                    continue;
                }

                if (inTripleQuote) {
                    if (char === tripleQuoteChar && nextChar === tripleQuoteChar && c + 2 < line.length && line.charAt(c + 2) === tripleQuoteChar) {
                        inTripleQuote = false;
                        c += 2;
                    }
                    continue;
                }

                if (inStr) {
                    if (char === '\\') {
                        c++;
                    } else if (char === strQuote) {
                        inStr = false;
                    }
                    continue;
                }

                if (char === '/' && nextChar === '*') {
                    inBlockComment = true;
                    c++;
                    continue;
                }
                if (char === '/' && nextChar === '/') break;
                if (char === '#') break;

                if ((char === '"' || char === '\'') && nextChar === char && c + 2 < line.length && line.charAt(c + 2) === char) {
                    inTripleQuote = true;
                    tripleQuoteChar = char;
                    c += 2;
                    continue;
                }

                if (char === '"' || char === '\'' || char === '`') {
                    inStr = true;
                    strQuote = char;
                    continue;
                }

                if (char === '{') {
                    lineHasOpeningBrace[l] = true;
                } else if (char === '}') {
                    lineHasClosingBrace[l] = true;
                }
            }
        }

        // 2. Resolve effective indentation for blank and comment-only lines
        var effectiveIndents = new Array(total);

        for (var l = 0; l < total; l++) {
            var ind = lineIndents[l];
            if (ind >= 0 && !isCommentOnlyLine(lines[l])) {
                effectiveIndents[l] = ind;
            } else {
                var prevValidIndent = -1;
                var prevValidLine = -1;
                for (var pl = l - 1; pl >= 0; pl--) {
                    if (lineIndents[pl] >= 0 && !isCommentOnlyLine(lines[pl])) {
                        prevValidIndent = lineIndents[pl];
                        prevValidLine = pl;
                        break;
                    }
                }

                var nextValidIndent = -1;
                var nextValidLine = -1;
                for (var nl = l + 1; nl < total; nl++) {
                    if (lineIndents[nl] >= 0 && !isCommentOnlyLine(lines[nl])) {
                        nextValidIndent = lineIndents[nl];
                        nextValidLine = nl;
                        break;
                    }
                }

                if (prevValidIndent === -1 && nextValidIndent === -1) {
                    effectiveIndents[l] = 0;
                } else if (prevValidIndent === -1) {
                    effectiveIndents[l] = 0;
                } else if (nextValidIndent === -1) {
                    effectiveIndents[l] = 0;
                } else if (prevValidIndent === nextValidIndent) {
                    effectiveIndents[l] = prevValidIndent;
                } else if (nextValidIndent > prevValidIndent) {
                    if (lineHasOpeningBrace[prevValidLine] || lineEndsWithColon[prevValidLine]) {
                        effectiveIndents[l] = nextValidIndent;
                    } else {
                        effectiveIndents[l] = prevValidIndent;
                    }
                } else {
                    if (lineHasClosingBrace[nextValidLine]) {
                        effectiveIndents[l] = prevValidIndent;
                    } else {
                        effectiveIndents[l] = nextValidIndent;
                    }
                }
            }
        }
        
     
        // 3. Build Continuous Logical Guide Segments
        var segments = [];
        var maxIndentObserved = 0;
        for (var l = 0; l < total; l++) {
            if (effectiveIndents[l] > maxIndentObserved) {
                maxIndentObserved = effectiveIndents[l];
            }
        }
        maxIndentObserved = Math.min(maxIndentObserved, 32);

        var activeSegments = new Array(maxIndentObserved + 1);
        for (var k = 0; k <= maxIndentObserved; k++) activeSegments[k] = null;

        for (var l = 0; l < total; l++) {
            var curEff = effectiveIndents[l];
            var isClosingLine = lineHasClosingBrace[l];
            var isOpeningLine = lineHasOpeningBrace[l];
            var rawInd = lineIndents[l];

            for (var k = 0; k <= maxIndentObserved; k++) {
                var isLevelActiveOnLine = (curEff > k);
                var isOpeningThisLevel = (isOpeningLine && rawInd === k);
                var isColonOpeningThisLevel = (lineEndsWithColon[l] && rawInd === k && (l + 1 < total && effectiveIndents[l + 1] > k));
                var isClosingThisLevel = (isClosingLine && rawInd === k);

                if (isOpeningThisLevel || isColonOpeningThisLevel) {
                    if (!activeSegments[k]) {
                        activeSegments[k] = {
                            startLine: l,
                            endLine: l,
                            level: k,
                            hasClosingBrace: false
                        };
                    }
                }

                if (isLevelActiveOnLine) {
                    if (!activeSegments[k]) {
                        var sLine = l;
                        for (var pl = l - 1; pl >= 0; pl--) {
                            if (lineIndents[pl] === k && (lineHasOpeningBrace[pl] || lineEndsWithColon[pl])) {
                                sLine = pl;
                                break;
                            }
                        }
                        activeSegments[k] = {
                            startLine: sLine,
                            endLine: l,
                            level: k,
                            hasClosingBrace: false
                        };
                    } else {
                        activeSegments[k].endLine = l;
                    }
                } else if (isClosingThisLevel) {
                    if (activeSegments[k]) {
                        activeSegments[k].endLine = l;
                        activeSegments[k].hasClosingBrace = true;
                        segments.push(activeSegments[k]);
                        activeSegments[k] = null;
                    }
                } else if (!isOpeningThisLevel && !isColonOpeningThisLevel) {
                    if (activeSegments[k]) {
                        segments.push(activeSegments[k]);
                        activeSegments[k] = null;
                    }
                }
            }
        }

        for (var k = 0; k <= maxIndentObserved; k++) {
            if (activeSegments[k]) {
                segments.push(activeSegments[k]);
                activeSegments[k] = null;
            }
        }

        return segments;
    }

    function recomputeScopes(docText) {
        root.scopeDocRevision++;
        var text = docText || (root.codeTextArea ? root.codeTextArea.text : "");
        var scopes = computeScopesForText(text);
        var segments = computeGuideSegmentsForText(text);
        if (root.activeEditorPane) {
            root.activeEditorPane.paneScopeRanges = scopes;
            root.activeEditorPane.paneGuideSegments = segments;
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

    signal askAi(string code, int selectionStart, int selectionEnd, string languageId)
    signal sendAiPrompt(string prompt)

    property string pendingAiCode: ""
    property int pendingAiStart: -1
    property int pendingAiEnd: -1
    property string pendingAiOriginalText: ""
    property bool isAiReplacementGenerating: false
    property bool hasPendingAiReplacement: pendingAiStart >= 0 && (isAiReplacementGenerating || pendingAiCode.length > 0)

    function startPendingAiReplacement(startPos, endPos, originalText) {
        pendingAiStart = startPos;
        pendingAiEnd = endPos;
        pendingAiOriginalText = originalText || "";
        pendingAiCode = "";
        isAiReplacementGenerating = true;
    }

    function setPendingAiReplacement(startPos, endPos, code, originalText) {
        pendingAiStart = startPos;
        pendingAiEnd = endPos;
        pendingAiCode = code;
        pendingAiOriginalText = originalText || "";
        isAiReplacementGenerating = false;
    }

    function clearPendingAiReplacement() {
        pendingAiCode = "";
        pendingAiStart = -1;
        pendingAiEnd = -1;
        pendingAiOriginalText = "";
        isAiReplacementGenerating = false;
    }

    FontMetrics {
        id: fontMetrics
        font.family: (typeof theme !== "undefined" && theme && (theme.editorFontFamily || theme.fontFamilyMono)) ? (theme.editorFontFamily || theme.fontFamilyMono) : "Consolas"
        font.pixelSize: (typeof theme !== "undefined" && theme && theme.editorFontSize) ? theme.editorFontSize : 13
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

            onCloseOtherTabsRequested: function(index) {
                root.closeOtherTabs(index);
            }

            onCloseTabsToTheRightRequested: function(index) {
                root.closeTabsToTheRight(index);
            }

            onCloseAllTabsRequested: function() {
                root.closeAllTabs();
            }

            onCloseSavedTabsRequested: function() {
                root.closeSavedTabs();
            }

            onCopyTabPathRequested: function(index) {
                root.copyTabPath(index);
            }

            onRevealTabInExplorerRequested: function(index) {
                root.revealTabInExplorer(index);
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

                        // Breadcrumbs Hierarchy & Symbol Bar
                        BreadcrumbsBar {
                            id: breadcrumbsBar
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            filePath: root.activeFilePath
                            z: 20
                            onNavigateToLine: function(line) {
                                root.jumpToLine(line);
                            }
                        }

                        RowLayout {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.top: breadcrumbsBar.bottom
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
                                        property int index: (typeof model !== "undefined" && typeof model.index !== "undefined") ? model.index : (typeof index !== "undefined" ? index : 0)
                                        property string savedContent: (typeof model !== "undefined" && model && model.path) ? (model.content || "") : ""
                                        property bool isUntitled: (typeof model !== "undefined" && model) ? (!model.path || model.path === "") : true
                                        property string tabKey: (typeof model !== "undefined" && model) ? (model.path || model.fileId || ("tab_" + index)) : ("tab_" + index)
                                        property int windowStartLine: 0
                                        property int windowEndLine: 0
                                        property bool isVirtualized: paneTotalLineCount > 800
                                        property int paneTotalLineCount: (typeof backend !== "undefined" && backend && backend.get_backing_total_lines) ? backend.get_backing_total_lines(tabPane.tabKey) : (codeTextArea ? Math.max(1, codeTextArea.lineCount) : 1)
                                        property bool isShifting: false
                                        property int pendingScrollbarTargetLine: -1
                                        property alias gutter: gutter
                                        property alias gutterFlickable: gutterFlickable
                                        property alias textAreaContainer: textAreaContainer
                                        property alias indentGuidesCanvas: indentGuidesCanvas
                                        property alias editorFlickable: editorFlickable
                                        property alias codeTextArea: codeTextArea
                                        property alias currentLineHighlight: currentLineHighlight
                                        property var paneScopeRanges: []
                                        property var paneGuideSegments: []
                                        property int paneFontSize: 13
                                        property real paneCharWidth: 7.8
                                        property real paneLineHeight: 18.0
                                        property real lastKnownLineHeight: 18.0

                                        Component.onCompleted: {
                                            if (typeof theme !== "undefined" && theme && theme.editorFontSize) {
                                                paneFontSize = theme.editorFontSize;
                                            }
                                            paneCharWidth = root.charWidth > 0 ? root.charWidth : 7.8;
                                            paneLineHeight = root.editorLineHeight > 0 ? root.editorLineHeight : 18.0;
                                            lastKnownLineHeight = paneLineHeight;
                                            if (typeof backend !== "undefined" && backend && backend.get_backing_total_lines) {
                                                paneTotalLineCount = backend.get_backing_total_lines(tabKey);
                                                if (paneTotalLineCount > 800) {
                                                    checkAndShiftWindow(true, "init");
                                                }
                                            }
                                        }

                                        function checkAndShiftWindow(force, reason) {
                                            if (!isVirtualized || isShifting || typeof backend === "undefined" || !backend || !backend.get_backing_slice) return;
                                            
                                            var viewTop = editorFlickable.contentY;
                                            var lineH = paneLineHeight > 0 ? paneLineHeight : 18.0;
                                            var viewCenterLine = (pendingScrollbarTargetLine >= 0) ? pendingScrollbarTargetLine : Math.max(0, Math.floor((viewTop + editorFlickable.height * 0.5) / lineH));
                                            
                                            var bufferThreshold = 180;
                                            var needsShift = (force === true) || (viewCenterLine < windowStartLine + bufferThreshold) || (viewCenterLine > windowEndLine - bufferThreshold);
                                            
                                            if (needsShift) {
                                                var halfWindow = 400;
                                                var newStart = Math.max(0, viewCenterLine - halfWindow);
                                                var newEnd = Math.min(paneTotalLineCount - 1, newStart + 800);
                                                newStart = Math.max(0, newEnd - 800);
                                                
                                                if (newStart === windowStartLine && newEnd === windowEndLine && !force) return;
                                                
                                                var sliceObj = backend.get_backing_slice(tabKey, newStart, newEnd);
                                                if (sliceObj && sliceObj.text !== undefined) {
                                                    isShifting = true;
                                                    var viewStart = Math.max(0, Math.floor(viewTop / lineH));
                                                    var viewEnd = viewStart + Math.ceil(editorFlickable.height / lineH);
                                                    console.log("[Virtualization Shift]", "reason:", reason || "wheel",
                                                        "globalTotalLines:", paneTotalLineCount,
                                                        "window:", (windowStartLine + 1) + ".." + (windowEndLine + 1), "->", (sliceObj.startLine + 1) + ".." + (sliceObj.endLine + 1),
                                                        "viewport:", viewStart + ".." + viewEnd,
                                                        "contentY:", Math.round(viewTop), "contentHeight:", Math.round(editorFlickable.contentHeight),
                                                        "flickWidth:", editorFlickable.width,
                                                        "matX:", materializedEditorContainer.x, "matW:", materializedEditorContainer.width,
                                                        "codeX:", codeTextArea.x, "codeW:", codeTextArea.width,
                                                        "gutterW:", gutter.width);
                                                    
                                                    var oldScrollY = editorFlickable.contentY;
                                                    var oldScrollX = editorFlickable.contentX;
                                                    var globalLine = root.cursorLine;
                                                    var globalCol = root.cursorColumn;
                                                    
                                                    root.isRestoringTab = true;
                                                    try {
                                                        windowStartLine = sliceObj.startLine;
                                                        windowEndLine = sliceObj.endLine;
                                                        codeTextArea.text = sliceObj.text;
                                                        
                                                        if (globalLine >= windowStartLine + 1 && globalLine <= windowEndLine + 1) {
                                                            var localLine = globalLine - windowStartLine;
                                                            var localLines = sliceObj.text.split("\n");
                                                            var targetLine = Math.min(localLine, localLines.length);
                                                            var charPos = 0;
                                                            for (var l = 0; l < targetLine - 1; l++) {
                                                                charPos += localLines[l].length + 1;
                                                            }
                                                            if (targetLine - 1 < localLines.length) {
                                                                charPos += Math.min(globalCol - 1, localLines[targetLine - 1].length);
                                                            }
                                                            codeTextArea.cursorPosition = Math.min(charPos, sliceObj.text.length);
                                                        }

                                                        tabPane.paneScopeRanges = root.computeScopesForText(codeTextArea.text);
                                                        tabPane.paneGuideSegments = root.computeGuideSegmentsForText(codeTextArea.text);
                                                        if (tabPane.index === root.activeTabIndex) {
                                                            indentGuidesCanvas.requestPaint();
                                                        }
                                                    } finally {
                                                        root.isRestoringTab = false;
                                                    }
                                                    
                                                    editorFlickable.contentY = oldScrollY;
                                                    editorFlickable.contentX = oldScrollX;
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                            }
                                                var newStart = Math.max(0, viewCenterLine - halfWindow);
                                                var newEnd = Math.min(paneTotalLineCount - 1, newStart + 800);
                                                newStart = Math.max(0, newEnd - 800);
                                                
                                                if (newStart === windowStartLine && newEnd === windowEndLine && !force) return;
                                                
                                                var sliceObj = backend.get_backing_slice(tabKey, newStart, newEnd);
                                                if (sliceObj && sliceObj.text !== undefined) {
                                                    isShifting = true;
                                                    var viewStart = Math.max(0, Math.floor(viewTop / lineH));
                                                    var viewEnd = viewStart + Math.ceil(editorFlickable.height / lineH);
                                                    console.log("[Virtualization Shift]", "reason:", reason || "wheel",
                                                        "globalTotalLines:", paneTotalLineCount,
                                                        "window:", (windowStartLine + 1) + ".." + (windowEndLine + 1), "->", (sliceObj.startLine + 1) + ".." + (sliceObj.endLine + 1),
                                                        "viewport:", viewStart + ".." + viewEnd,
                                                        "contentY:", Math.round(viewTop), "contentHeight:", Math.round(editorFlickable.contentHeight),
                                                        "flickWidth:", editorFlickable.width,
                                                        "matX:", materializedEditorContainer.x, "matW:", materializedEditorContainer.width,
                                                        "codeX:", codeTextArea.x, "codeW:", codeTextArea.width,
                                                        "gutterW:", gutter.width);
                                                    
                                                    var oldScrollY = editorFlickable.contentY;
                                                    var oldScrollX = editorFlickable.contentX;
                                                    var globalLine = root.cursorLine;
                                                    var globalCol = root.cursorColumn;
                                                    
                                                    root.isRestoringTab = true;
                                                    try {
                                                        windowStartLine = sliceObj.startLine;
                                                        windowEndLine = sliceObj.endLine;
                                                        codeTextArea.text = sliceObj.text;
                                                        
                                                        if (globalLine >= windowStartLine + 1 && globalLine <= windowEndLine + 1) {
                                                            var localLine = globalLine - windowStartLine;
                                                            var localLines = sliceObj.text.split("\n");
                                                            var targetLine = Math.min(localLine, localLines.length);
                                                            var charPos = 0;
                                                            for (var l = 0; l < targetLine - 1; l++) {
                                                                charPos += localLines[l].length + 1;
                                                            }
                                                            if (targetLine - 1 < localLines.length) {
                                                                charPos += Math.min(globalCol - 1, localLines[targetLine - 1].length);
                                                            }
                                                            codeTextArea.cursorPosition = Math.min(charPos, sliceObj.text.length);
                                                        }

                                                        tabPane.paneScopeRanges = root.computeScopesForText(codeTextArea.text);
                                                        tabPane.paneGuideSegments = root.computeGuideSegmentsForText(codeTextArea.text);
                                                        if (tabPane.index === root.activeTabIndex) {
                                                            indentGuidesCanvas.requestPaint();
                                                        }
                                                    } finally {
                                                        root.isRestoringTab = false;
                                                    }
                                                    
                                                    editorFlickable.contentY = oldScrollY;
                                                    editorFlickable.contentX = oldScrollX;
                                                    isShifting = false;
                                                }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                                    isShifting = false;
                                                }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                            }
                                        }

                                        function syncFontMetricsAndGeometry() {
                                            var oldLineH = lastKnownLineHeight > 0 ? lastKnownLineHeight : (paneLineHeight > 0 ? paneLineHeight : 18.0);
                                            var newLineH = root.editorLineHeight > 0 ? root.editorLineHeight : 18.0;
                                            var newCharW = root.charWidth > 0 ? root.charWidth : 7.8;
                                            var newFontSize = (typeof theme !== "undefined" && theme && theme.editorFontSize) ? theme.editorFontSize : 13;

                                            tabPane.paneFontSize = newFontSize;
                                            tabPane.paneCharWidth = newCharW;
                                            tabPane.paneLineHeight = newLineH;
                                            lastKnownLineHeight = newLineH;

                                            if (editorFlickable && oldLineH > 0 && newLineH > 0 && Math.abs(newLineH - oldLineH) > 0.01) {
                                                var ratio = newLineH / oldLineH;
                                                var newY = editorFlickable.contentY * ratio;
                                                var maxY = Math.max(0, editorFlickable.contentHeight - editorFlickable.height);
                                                editorFlickable.contentY = Math.max(0, Math.min(maxY, newY));
                                            }

                                            if (tabPane.isVirtualized) {
                                                tabPane.checkAndShiftWindow(true, "zoom");
                                            }
                                            if (indentGuidesCanvas) {
                                                indentGuidesCanvas.requestPaint();
                                            }
                                        }

                                        Connections {
                                            target: (typeof theme !== "undefined" && theme) ? theme : null
                                            function onEditorFontSizeChanged() {
                                                if (tabPane.index === root.activeTabIndex) {
                                                    tabPane.syncFontMetricsAndGeometry();
                                                }
                                            }
                                        }

                                        Connections {
                                            target: root
                                            function onCharWidthChanged() {
                                                if (tabPane.index === root.activeTabIndex) {
                                                    tabPane.paneCharWidth = root.charWidth;
                                                }
                                            }
                                            function onEditorLineHeightChanged() {
                                                if (tabPane.index === root.activeTabIndex) {
                                                    tabPane.syncFontMetricsAndGeometry();
                                                }
                                            }
                                            function onActiveTabIndexChanged() {
                                                if (tabPane.index === root.activeTabIndex) {
                                                    tabPane.syncFontMetricsAndGeometry();
                                                }
                                            }
                                        }

                                        function handleEditorKey(event) {
                                            if (codeTextArea && codeTextArea.handleKeyPressInternal) {
                                                return codeTextArea.handleKeyPressInternal(event);
                                            }
                                        }

                                        function updatePaneScopes() {
                                            paneScopeRanges = root.computeScopesForText(codeTextArea.text);
                                            paneGuideSegments = root.computeGuideSegmentsForText(codeTextArea.text);
                                            if (tabPane.index === root.activeTabIndex) {
                                                indentGuidesCanvas.requestPaint();
                                            }
                                        }

                                        RowLayout {
                                            anchors.fill: parent
                                            spacing: 0

                                            // Line Numbers Gutter (Virtualized for high performance on large files)
                                            Rectangle {
                                                id: gutter
                                                Layout.fillWidth: false
                                                Layout.preferredWidth: Math.max(48, (tabPane.paneTotalLineCount.toString().length * 8 + 30))
                                                Layout.minimumWidth: Layout.preferredWidth
                                                Layout.maximumWidth: Layout.preferredWidth
                                                Layout.fillHeight: true
                                                color: theme ? theme.bgPanel : "#181818"
                                                visible: theme ? theme.enableLineNumbers : true
                                                clip: true

                                                readonly property int visibleStartLine: Math.max(0, Math.floor(gutterFlickable.contentY / tabPane.paneLineHeight))
                                                readonly property int visibleLineCount: Math.min(tabPane.paneTotalLineCount - visibleStartLine, Math.ceil(gutter.height / tabPane.paneLineHeight) + 12)

                                                Flickable {
                                                    id: gutterFlickable
                                                    anchors.fill: parent
                                                    contentHeight: editorFlickable.contentHeight
                                                    contentY: editorFlickable.contentY
                                                    interactive: false
                                                    boundsBehavior: Flickable.StopAtBounds

                                                    Item {
                                                        width: gutter.width
                                                        height: Math.max(gutterFlickable.height, tabPane.paneTotalLineCount * tabPane.paneLineHeight + codeTextArea.topPadding + codeTextArea.bottomPadding)

                                                        Repeater {
                                                            model: gutter.visibleLineCount > 0 ? gutter.visibleLineCount : 0

                                                            delegate: Item {
                                                                readonly property int lineNum: gutter.visibleStartLine + index + 1
                                                                width: gutter.width
                                                                height: tabPane.paneLineHeight
                                                                y: (lineNum - 1) * tabPane.paneLineHeight + codeTextArea.topPadding

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
                                                                    font.pixelSize: tabPane.paneFontSize
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
                                                        onTriggered: {
                                                            if (tabPane.index === root.activeTabIndex) {
                                                                indentGuidesCanvas.requestPaint();
                                                            }
                                                        }
                                                    }

                                                    Connections {
                                                        target: editorFlickable
                                                        function onContentXChanged() { canvasScrollTimer.restart(); }
                                                        function onContentYChanged() { canvasScrollTimer.restart(); }
                                                    }

                                                    Timer {
                                                        id: canvasDebounceTimer
                                                        interval: 350
                                                        repeat: false
                                                        onTriggered: {
                                                            if (codeTextArea) {
                                                                if (!tabPane.isVirtualized) {
                                                                    tabPane.paneTotalLineCount = Math.max(1, codeTextArea.lineCount);
                                                                }
                                                                tabPane.paneScopeRanges = root.computeScopesForText(codeTextArea.text);
                                                                tabPane.paneGuideSegments = root.computeGuideSegmentsForText(codeTextArea.text);
                                                            }
                                                            if (tabPane.index === root.activeTabIndex) {
                                                                canvasScrollTimer.restart();
                                                            }
                                                        }
                                                    }

                                                    Connections {
                                                        target: codeTextArea
                                                        function onTextChanged() { canvasDebounceTimer.restart(); }
                                                    }

                                                    Connections {
                                                        target: root
                                                        function onActiveTabIndexChanged() {
                                                            if (tabPane.index === root.activeTabIndex) canvasScrollTimer.restart();
                                                        }
                                                        function onCharWidthChanged() {
                                                            if (tabPane.index === root.activeTabIndex) canvasScrollTimer.restart();
                                                        }
                                                        function onEditorLineHeightChanged() {
                                                            if (tabPane.index === root.activeTabIndex) canvasScrollTimer.restart();
                                                        }
                                                        function onCachedIndentLevelWidthsChanged() {
                                                            if (tabPane.index === root.activeTabIndex) canvasScrollTimer.restart();
                                                        }
                                                    }

                                                    onPaint: {
                                                        if (tabPane.index !== root.activeTabIndex) return;
                                                        var ctx = getContext("2d");
                                                        ctx.clearRect(0, 0, width, height);

                                                        var segments = tabPane.paneGuideSegments;
                                                        if (!segments || segments.length === 0) return;

                                                        var leftPadding = codeTextArea.leftPadding - editorFlickable.contentX;
                                                        var topPadding = codeTextArea.topPadding;
                                                        var lineH = root.editorLineHeight;
                                                        var charW = root.charWidth;
                                                        var cachedWidths = root.cachedIndentLevelWidths;

                                                        var viewTop = editorFlickable.contentY;
                                                        var visibleStartLine = Math.max(0, Math.floor(viewTop / lineH) - 1);
                                                        var visibleEndLine = visibleStartLine + Math.ceil(height / lineH) + 4;

                                                        ctx.lineWidth = 1;
                                                        ctx.strokeStyle = (typeof theme !== "undefined" && theme && theme.borderSubtle) ? theme.borderSubtle : "#35383d";
                                                        ctx.globalAlpha = 0.35;

                                                        for (var i = 0; i < segments.length; i++) {
                                                            var seg = segments[i];
                                                            var globalStart = tabPane.isVirtualized ? (tabPane.windowStartLine + seg.startLine) : seg.startLine;
                                                            var globalEnd = tabPane.isVirtualized ? (tabPane.windowStartLine + seg.endLine) : seg.endLine;

                                                            if (globalEnd < visibleStartLine || globalStart > visibleEndLine) continue;

                                                            var lvl = seg.level;
                                                            var lvlWidth = (lvl < cachedWidths.length) ? cachedWidths[lvl] : (lvl * cachedWidths[1]);
                                                            var x = leftPadding + lvlWidth;
                                                            var drawX = Math.round(x) + 0.5;

                                                            if (drawX < -20 || drawX > width + 20) continue;

                                                            var yStart = topPadding + (globalStart * lineH) - viewTop;
                                                            var yEnd = seg.hasClosingBrace ? (topPadding + (globalEnd * lineH) + (lineH * 0.5) - viewTop) : (topPadding + ((globalEnd + 1) * lineH) - viewTop);

                                                            ctx.beginPath();
                                                            ctx.moveTo(drawX, yStart);
                                                            ctx.lineTo(drawX, yEnd);
                                                            if (seg.hasClosingBrace) {
                                                                ctx.lineTo(drawX + Math.round(charW * 0.45), yEnd);
                                                            }
                                                            ctx.stroke();
                                                        }
                                                        ctx.globalAlpha = 1.0;
                                                    }
                                                }

                                                Flickable {
                                                    id: editorFlickable
                                                    objectName: "editorFlickable"
                                                    anchors.fill: parent
                                                    interactive: false
                                                    clip: true
                                                    boundsBehavior: Flickable.StopAtBounds
                                                    contentWidth: (theme && theme.enableWordWrap) ? width : Math.max(width, codeTextArea.contentWidth + codeTextArea.leftPadding + codeTextArea.rightPadding + 80)
                                                    contentHeight: (theme && theme.enableWordWrap) ? Math.max(height, codeTextArea.contentHeight + codeTextArea.topPadding + codeTextArea.bottomPadding + 220) : Math.max(height, tabPane.paneTotalLineCount * tabPane.paneLineHeight + 220)

                                                    Timer {
                                                        id: windowShiftDebounceTimer
                                                        interval: 25
                                                        repeat: false
                                                        onTriggered: {
                                                            if (tabPane.isVirtualized) {
                                                                tabPane.checkAndShiftWindow(false, "wheel");
                                                            }
                                                        }
                                                    }

                                                    Timer {
                                                        id: scrollbarDragEndTimer
                                                        interval: 35
                                                        repeat: false
                                                        onTriggered: {
                                                            if (tabPane.isVirtualized) {
                                                                tabPane.checkAndShiftWindow(true, "scrollbar");
                                                            }
                                                        }
                                                    }

                                                    Timer {
                                                        id: visibleRangeDebounceTimer
                                                        interval: 100
                                                        repeat: false
                                                        onTriggered: {
                                                            if (tabPane.index === root.activeTabIndex && typeof backend !== "undefined" && backend && backend.update_visible_range) {
                                                                var lineH = tabPane.paneLineHeight > 0 ? tabPane.paneLineHeight : 18;
                                                                var sLine = Math.max(0, Math.floor(editorFlickable.contentY / lineH));
                                                                var eLine = sLine + Math.ceil(editorFlickable.height / lineH) + 4;
                                                                backend.update_visible_range(sLine, eLine);
                                                            }
                                                        }
                                                    }

                                                    onContentYChanged: {
                                                        visibleRangeDebounceTimer.restart();
                                                        if (tabPane.isVirtualized) {
                                                            if (vScrollBar && vScrollBar.pressed) {
                                                                scrollbarDragEndTimer.restart();
                                                            } else {
                                                                var lineH = paneLineHeight > 0 ? paneLineHeight : 18.0;
                                                                var vCenter = Math.floor((editorFlickable.contentY + editorFlickable.height * 0.5) / lineH);
                                                                if (vCenter < tabPane.windowStartLine + 100 || vCenter > tabPane.windowEndLine - 100) {
                                                                    tabPane.checkAndShiftWindow(false, "wheel_fast");
                                                                } else {
                                                                    windowShiftDebounceTimer.restart();
                                                                }
                                                            }
                                                        }
                                                    }

                                                    WheelHandler {
                                                        target: editorFlickable
                                                        acceptedModifiers: Qt.NoModifier
                                                        orientation: Qt.Vertical
                                                        onWheel: function(event) {
                                                            var delta = event.angleDelta.y;
                                                            if (delta === 0) return;
                                                            var lines = delta / 120.0;
                                                            var step = lines * tabPane.paneLineHeight * 3.0;
                                                            var maxY = Math.max(0, editorFlickable.contentHeight - editorFlickable.height);
                                                            editorFlickable.contentY = Math.max(0, Math.min(maxY, editorFlickable.contentY - step));
                                                        }
                                                    }

                                                    Timer {
                                                        id: saveZoomTimer
                                                        interval: 400
                                                        repeat: false
                                                        onTriggered: {
                                                            if (typeof theme !== "undefined" && theme) {
                                                                theme.saveSettings();
                                                            }
                                                        }
                                                    }

                                                    Timer {
                                                        id: zoomCoalesceTimer
                                                        interval: 35
                                                        repeat: false
                                                        onTriggered: {
                                                            if (typeof theme === "undefined" || !theme || theme.enableMouseWheelZoom === false) return;
                                                            if (Math.abs(zoomWheelHandler.deltaAccumulator) >= 60) {
                                                                var steps = Math.round(zoomWheelHandler.deltaAccumulator / 120.0);
                                                                if (steps === 0) steps = (zoomWheelHandler.deltaAccumulator > 0) ? 1 : -1;
                                                                zoomWheelHandler.deltaAccumulator = 0.0;
                                                                var currentSize = theme.editorFontSize;
                                                                var newSize = Math.max(8, Math.min(48, currentSize + steps));
                                                                if (newSize !== currentSize) {
                                                                    theme.editorFontSize = newSize;
                                                                    saveZoomTimer.restart();
                                                                }
                                                            } else {
                                                                zoomWheelHandler.deltaAccumulator = 0.0;
                                                            }
                                                        }
                                                    }

                                                    WheelHandler {
                                                        id: zoomWheelHandler
                                                        target: null
                                                        acceptedModifiers: Qt.ControlModifier
                                                        orientation: Qt.Vertical

                                                        property real deltaAccumulator: 0.0

                                                        onWheel: function(event) {
                                                            if (typeof theme === "undefined" || !theme || theme.enableMouseWheelZoom === false) return;
                                                            var delta = event.angleDelta.y;
                                                            if (delta === 0) return;

                                                             deltaAccumulator += delta;
                                                             zoomCoalesceTimer.restart();
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

                                                        onPressedChanged: {
                                                            if (!pressed && tabPane.isVirtualized) {
                                                                scrollbarDragEndTimer.stop();
                                                                tabPane.checkAndShiftWindow(true, "scrollbar_release");
                                                            }
                                                        }
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
                                                        y: (root.cursorLine - 1) * tabPane.paneLineHeight + codeTextArea.topPadding
                                                        width: Math.max(editorFlickable.contentWidth, editorFlickable.width)
                                                        height: tabPane.paneLineHeight
                                                        color: (theme && theme.synCurrentLine) ? theme.synCurrentLine : "#282828"
                                                        opacity: 0.35
                                                        z: 0
                                                        visible: codeTextArea.cursorRectangle.height > 0 && tabPane.index === root.activeTabIndex
                                                    }

                                                    Item {
                                                        id: materializedEditorContainer
                                                        x: 0
                                                        y: tabPane.isVirtualized ? (tabPane.windowStartLine * tabPane.paneLineHeight) : 0
                                                        width: (theme && theme.enableWordWrap) ? editorFlickable.width : editorFlickable.contentWidth
                                                        height: tabPane.isVirtualized ? ((tabPane.windowEndLine - tabPane.windowStartLine + 1) * tabPane.paneLineHeight + codeTextArea.topPadding + codeTextArea.bottomPadding) : editorFlickable.contentHeight
                                                        z: 1

                                                        TextArea {
                                                            id: codeTextArea
                                                            objectName: "codeTextArea"
                                                            anchors.fill: parent
                                                            topPadding: 6
                                                            bottomPadding: 16
                                                            leftPadding: 10
                                                            rightPadding: 24
                                                            wrapMode: (theme && theme.enableWordWrap) ? TextArea.WrapAtWordBoundaryOrAnywhere : TextArea.NoWrap
                                                            tabStopDistance: (theme ? theme.tabSize : 4) * tabPane.paneCharWidth
                                                            color: theme ? theme.textPrimary : "#cccccc"
                                                            selectionColor: theme ? theme.synSelection : "#264f78"
                                                            selectedTextColor: theme ? theme.textBright : "#ffffff"
                                                            font.pixelSize: tabPane.paneFontSize
                                                            font.family: (typeof theme !== "undefined" && theme && (theme.editorFontFamily || theme.fontFamilyMono)) ? (theme.editorFontFamily || theme.fontFamilyMono) : "Consolas"
                                                            selectByMouse: true
                                                            focus: tabPane.index === root.activeTabIndex
                                                            cursorVisible: true
                                                            textFormat: TextArea.PlainText
                                                            background: null
                                                            text: (typeof model !== "undefined" && model && model.content) ? model.content : ""

                                                            Component.onCompleted: {
                                                                Qt.callLater(function() {
                                                                    if (tabPane && tabPane.index === root.activeTabIndex && typeof backend !== "undefined" && backend && backend.register_text_area) {
                                                                        backend.register_text_area(codeTextArea, (model && model.path) ? model.path : "", (model && model.languageId) ? model.languageId : "text");
                                                                    }
                                                                    if (tabPane) {
                                                                        if (tabPane.isVirtualized) {
                                                                            tabPane.checkAndShiftWindow(true);
                                                                        }
                                                                        tabPane.paneScopeRanges = root.computeScopesForText(codeTextArea.text);
                                                                        tabPane.paneGuideSegments = root.computeGuideSegmentsForText(codeTextArea.text);
                                                                        indentGuidesCanvas.requestPaint();
                                                                    }
                                                                });
                                                            }

                                                        signal selection(string code)

                                                        onSelectedTextChanged: {
                                                            selection(codeTextArea.selectedText);
                                                        }

                                                                                                                 // Selection Occurrences Highlight Overlays
                                                         Repeater {
                                                             model: (tabPane.index === root.activeTabIndex) ? root.selectionOccurrences : []
                                                             delegate: Rectangle {
                                                                 property var occRect: codeTextArea.positionToRectangle(modelData.start)
                                                                 property var occEndRect: codeTextArea.positionToRectangle(modelData.end)
                                                                 x: occRect.x
                                                                 y: occRect.y
                                                                 width: Math.max(8, occEndRect.x - occRect.x)
                                                                 height: occRect.height > 0 ? occRect.height : root.editorLineHeight
                                                                 color: "#38bdf8"
                                                                 opacity: 0.28
                                                                 border.color: "#38bdf888"
                                                                 border.width: 1
                                                                 radius: 2
                                                                 z: 5
                                                             }
                                                         }

                                                         // Multi-Cursor Extra Selection Highlights
                                                        Repeater {
                                                            model: (tabPane.index === root.activeTabIndex) ? root.extraCursors : []
                                                            delegate: Rectangle {
                                                                property int sPos: typeof modelData === "object" ? Math.min(modelData.start, modelData.end) : modelData
                                                                property int ePos: typeof modelData === "object" ? Math.max(modelData.start, modelData.end) : modelData
                                                                visible: sPos !== ePos
                                                                property var r1: codeTextArea.positionToRectangle(sPos)
                                                                property var r2: codeTextArea.positionToRectangle(ePos)
                                                                x: r1.x
                                                                y: r1.y
                                                                width: Math.max(4, r2.x - r1.x)
                                                                height: r1.height > 0 ? r1.height : root.editorLineHeight
                                                                color: theme ? theme.synSelection : "#264f78"
                                                                opacity: 0.65
                                                                radius: 2
                                                                z: 4
                                                            }
                                                        }

                                                        // Multi-Cursor Caret Overlays
                                                        Repeater {
                                                            model: (tabPane.index === root.activeTabIndex) ? root.extraCursors : []
                                                            delegate: Rectangle {
                                                                property int cPos: typeof modelData === "object" ? modelData.cursor : modelData
                                                                property var curRect: codeTextArea.positionToRectangle(cPos)
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

                                                        // Floating AI Replace Pill on top of original saved selection
                                                        Rectangle {
                                                            id: floatingAiSelectionPill
                                                            z: 90

                                                            readonly property bool hasActiveSelection: codeTextArea.selectionStart !== codeTextArea.selectionEnd
                                                            readonly property int curSelStart: Math.min(codeTextArea.selectionStart, codeTextArea.selectionEnd)
                                                            readonly property int curSelEnd: Math.max(codeTextArea.selectionStart, codeTextArea.selectionEnd)
                                                            readonly property bool matchesPendingSelection: (curSelStart === root.pendingAiStart && curSelEnd === root.pendingAiEnd)

                                                            visible: root.hasPendingAiReplacement && (tabPane.index === root.activeTabIndex) && !findReplaceBar.visible && hasActiveSelection && matchesPendingSelection

                                                            readonly property bool isReady: !root.isAiReplacementGenerating && root.pendingAiCode.length > 0
                                                            enabled: isReady
                                                            opacity: isReady ? 1.0 : 0.55

                                                            property var origSelRect: (root.hasPendingAiReplacement && hasActiveSelection && matchesPendingSelection) ? codeTextArea.positionToRectangle(root.pendingAiStart) : null
                                                            x: origSelRect ? Math.max(codeTextArea.leftPadding, Math.min(codeTextArea.width - width - 12, origSelRect.x)) : 0
                                                            y: origSelRect ? (origSelRect.y - height - 6 < 0 ? (origSelRect.y + (origSelRect.height > 0 ? origSelRect.height : root.editorLineHeight) + 4) : (origSelRect.y - height - 6)) : 0

                                                            width: pillRow.implicitWidth + 18
                                                            height: 24
                                                            radius: 4
                                                            color: !isReady ? (theme ? theme.bgSurfaceHover : "#333333") : (pillMa.containsMouse ? (theme ? theme.accentHover : "#1084d8") : (theme ? theme.accent : "#0078d4"))
                                                            border.color: !isReady ? (theme ? theme.borderSubtle : "#444444") : (theme ? theme.borderFocus : "#60a5fa")
                                                            border.width: 1

                                                            RowLayout {
                                                                id: pillRow
                                                                anchors.centerIn: parent
                                                                spacing: 5

                                                                VectorIcon {
                                                                    name: "sparkles"
                                                                    size: 11
                                                                    color: floatingAiSelectionPill.isReady ? "#ffffff" : (theme ? theme.textMuted : "#888888")
                                                                }

                                                                Text {
                                                                    text: "Replace with AI"
                                                                    color: floatingAiSelectionPill.isReady ? "#ffffff" : (theme ? theme.textMuted : "#888888")
                                                                    font.pixelSize: 11
                                                                    font.bold: true
                                                                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                                                }
                                                            }

                                                            MouseArea {
                                                                id: pillMa
                                                                anchors.fill: parent
                                                                hoverEnabled: floatingAiSelectionPill.enabled
                                                                cursorShape: floatingAiSelectionPill.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                                                onClicked: {
                                                                    if (!floatingAiSelectionPill.enabled) return;
                                                                    root.replaceSelection(root.pendingAiStart, root.pendingAiEnd, root.pendingAiCode, root.pendingAiOriginalText);
                                                                    root.clearPendingAiReplacement();
                                                                }
                                                            }
                                                        }

                                                                                                                

                                                         // Alt+Click Multi-Cursor Interceptor (Left Button with Alt Modifier)
                                                        MouseArea {
                                                            anchors.fill: parent
                                                            acceptedButtons: Qt.LeftButton
                                                            hoverEnabled: false
                                                            z: 20
                                                            cursorShape: Qt.IBeamCursor

                                                            onPressed: function(mouse) {
                                                                if (mouse.modifiers & Qt.AltModifier) {
                                                                    mouse.accepted = true;
                                                                    var charPos = codeTextArea.positionAt(mouse.x, mouse.y);
                                                                    root.toggleExtraCursor(charPos);
                                                                } else {
                                                                    mouse.accepted = false;
                                                                }
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
                                                                    root.multiCursorUndoStack = [];
                                                                    root.multiCursorRedoStack = [];
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
                                                                
                                                                if (codeTextArea.selectedText && codeTextArea.selectedText.length >= 2) {
                                                                    root.updateSelectionOccurrences();
                                                                } else if (root.selectionOccurrences && root.selectionOccurrences.length > 0) {
                                                                    root.selectionOccurrences = [];
                                                                }
                                                                if (breadcrumbsBar && typeof breadcrumbsBar.updateActiveSymbolForLine === "function") {
                                                                    breadcrumbsBar.updateActiveSymbolForLine(root.cursorLine);
                                                                }
                                                                sessionSaveDebounceTimer.restart();
                                                                if (suggestionModel.count > 0 && !autocompleteTimer.running) {
                                                                    suggestionModel.clear();
                                                                }
                                                            }
                                                        }

                                                        onLineCountChanged: {
                                                            if (!tabPane.isVirtualized) {
                                                                tabPane.paneTotalLineCount = Math.max(1, codeTextArea.lineCount);
                                                            }
                                                        }

                                                        onTextChanged: {
                                                            if (root.isInitialTextLoading || root.isRestoringTab || root.isFoldingOperation) return;
                                                            if (index >= 0 && index < tabModel.count) {
                                                                var curTab = tabModel.get(index);
                                                                if (curTab) {
                                                                    if (tabPane.isVirtualized && typeof backend !== "undefined" && backend && backend.update_backing_slice) {
                                                                        backend.update_backing_slice(tabPane.tabKey, tabPane.windowStartLine, tabPane.windowEndLine, codeTextArea.text);
                                                                        tabPane.paneTotalLineCount = backend.get_backing_total_lines(tabPane.tabKey);
                                                                    } else if (typeof backend !== "undefined" && backend && backend.update_backing_text) {
                                                                        backend.update_backing_text(tabPane.tabKey, codeTextArea.text);
                                                                        tabPane.paneTotalLineCount = Math.max(1, codeTextArea.lineCount);
                                                                    }
                                                                    var isDirtyNow = false;
                                                                    if (tabPane.isUntitled || !curTab.path || curTab.path === "") {
                                                                        isDirtyNow = true;
                                                                    } else {
                                                                        if (typeof backend !== "undefined" && backend && backend.is_backing_document_modified) {
                                                                            isDirtyNow = backend.is_backing_document_modified(tabPane.tabKey);
                                                                        } else if (typeof backend !== "undefined" && backend && backend.is_document_modified) {
                                                                            isDirtyNow = backend.is_document_modified(codeTextArea);
                                                                        } else {
                                                                            isDirtyNow = (codeTextArea.text !== (tabPane.savedContent || ""));
                                                                        }
                                                                    }
                                                                    if (curTab.isDirty !== isDirtyNow) {
                                                                        tabModel.setProperty(index, "isDirty", isDirtyNow);
                                                                        root.dirtyVersion++;
                                                                        if (index === root.activeTabIndex) {
                                                                            root.activeFileChanged(curTab.path || "", curTab.title || "", root.currentLanguage, isDirtyNow);
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                            canvasDebounceTimer.restart();
                                                            textChangeDebounceTimer.restart();
                                                            foldAnalysisTimer.restart();
                                                            diagnosticsTimer.restart();
                                                            minimapDeferredUpdateTimer.restart();
                                                        }

                                                        Keys.onPressed: function(event) { handleKeyPressInternal(event); }

                                                        function handleKeyPressInternal(event) {
                                                            // Whole-line copy / paste behavior
                                                            if ((event.modifiers & Qt.ControlModifier) && (event.key === Qt.Key_C)) {
                                                                var sStart = codeTextArea.selectionStart;
                                                                var sEnd = codeTextArea.selectionEnd;
                                                                if (sStart === undefined || sEnd === undefined || sStart === sEnd) {
                                                                    var docT = codeTextArea.text;
                                                                    var cPos = codeTextArea.cursorPosition;
                                                                    var lStart = docT.lastIndexOf("\n", cPos - 1) + 1;
                                                                    var lEnd = docT.indexOf("\n", cPos);
                                                                    if (lEnd === -1) lEnd = docT.length;
                                                                    var lineCopy = docT.substring(lStart, lEnd) + "\n";
                                                                    root.copiedWholeLine = true;
                                                                    root.clipboardWholeLineText = lineCopy;
                                                                    codeTextArea.select(lStart, lEnd < docT.length ? lEnd + 1 : lEnd);
                                                                    codeTextArea.copy();
                                                                    codeTextArea.deselect();
                                                                    codeTextArea.cursorPosition = cPos;
                                                                    event.accepted = true;
                                                                    return;
                                                                }
                                                            }

                                                            if ((event.modifiers & Qt.ControlModifier) && (event.key === Qt.Key_V)) {
                                                                var selS = codeTextArea.selectionStart;
                                                                var selE = codeTextArea.selectionEnd;
                                                                var hasSel = (selS !== undefined && selE !== undefined && selS !== selE);
                                                                if (!hasSel && root.copiedWholeLine && root.clipboardWholeLineText) {
                                                                    var dText = codeTextArea.text;
                                                                    var curP = codeTextArea.cursorPosition;
                                                                    var lineSt = dText.lastIndexOf("\n", curP - 1) + 1;
                                                                    codeTextArea.insert(lineSt, root.clipboardWholeLineText);
                                                                    codeTextArea.cursorPosition = lineSt;
                                                                    event.accepted = true;
                                                                    return;
                                                                }
                                                            }

                                                            // Snippet Placeholders Tab Navigation
                                                            if (root.activeSnippetStops && root.activeSnippetStops.length > 0) {
                                                                if (event.key === Qt.Key_Tab && !(event.modifiers & Qt.ShiftModifier)) {
                                                                    root.activeSnippetStopIndex += 1;
                                                                    if (root.activeSnippetStopIndex < root.activeSnippetStops.length) {
                                                                        var nStop = root.activeSnippetStops[root.activeSnippetStopIndex];
                                                                        codeTextArea.select(nStop.start, nStop.end);
                                                                        event.accepted = true;
                                                                        return;
                                                                    } else {
                                                                        root.activeSnippetStops = [];
                                                                        root.activeSnippetStopIndex = -1;
                                                                    }
                                                                } else if (event.key === Qt.Key_Backtab || ((event.modifiers & Qt.ShiftModifier) && event.key === Qt.Key_Tab)) {
                                                                    if (root.activeSnippetStopIndex > 0) {
                                                                        root.activeSnippetStopIndex -= 1;
                                                                        var pStop = root.activeSnippetStops[root.activeSnippetStopIndex];
                                                                        codeTextArea.select(pStop.start, pStop.end);
                                                                        event.accepted = true;
                                                                        return;
                                                                    }
                                                                } else if (event.key === Qt.Key_Escape) {
                                                                    root.activeSnippetStops = [];
                                                                    root.activeSnippetStopIndex = -1;
                                                                }
                                                            }

                                                            // F2 Rename Symbol shortcut
                                                            if (event.key === Qt.Key_F2) {
                                                                root.triggerRenameSymbol();
                                                                event.accepted = true;
                                                                return;
                                                            }

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

                                                            // 0.4 Multi-Cursor Copy & Paste & Undo/Redo Handling
                                                            if (root.extraCursors.length > 0 && (event.modifiers & Qt.ControlModifier)) {
                                                                if (event.key === Qt.Key_C) {
                                                                    var textDoc = codeTextArea.text;
                                                                    var selPieces = [];
                                                                    for (var ci = 0; ci < root.extraCursors.length; ci++) {
                                                                        var curObj = root.extraCursors[ci];
                                                                        var cStart = typeof curObj === "object" ? Math.min(curObj.start, curObj.end) : curObj;
                                                                        var cEnd = typeof curObj === "object" ? Math.max(curObj.start, curObj.end) : curObj;
                                                                        if (cStart !== cEnd) {
                                                                            selPieces.push(textDoc.substring(cStart, cEnd));
                                                                        }
                                                                    }
                                                                    if (selPieces.length > 0 && typeof backend !== "undefined" && backend && backend.set_clipboard_text) {
                                                                        backend.set_clipboard_text(selPieces.join("\n"));
                                                                        event.accepted = true;
                                                                        return;
                                                                    }
                                                                } else if (event.key === Qt.Key_V) {
                                                                    var pasteText = "";
                                                                    if (typeof backend !== "undefined" && backend && backend.get_clipboard_text) {
                                                                        pasteText = backend.get_clipboard_text() || "";
                                                                    }
                                                                    if (pasteText.length > 0) {
                                                                        var snapUndo = root.multiCursorUndoStack.slice();
                                                                        snapUndo.push({ text: codeTextArea.text, cursors: JSON.parse(JSON.stringify(root.extraCursors)) });
                                                                        if (snapUndo.length > 50) snapUndo.shift();
                                                                        root.multiCursorUndoStack = snapUndo;
                                                                        root.multiCursorRedoStack = [];

                                                                        var pasteLines = pasteText.split("\n");
                                                                        var cursors = getNormalizedCursors();
                                                                        var isLineMatch = (pasteLines.length === cursors.length);
                                                                        var deltas = [];
                                                                        var localPos = [];

                                                                        for (var i = 0; i < cursors.length; i++) {
                                                                            var cur = cursors[i];
                                                                            var minP = Math.min(cur.start, cur.end);
                                                                            var maxP = Math.max(cur.start, cur.end);
                                                                            var curPaste = isLineMatch ? pasteLines[i] : pasteText;
                                                                            deltas.push(curPaste.length - (maxP - minP));
                                                                            localPos.push(minP + curPaste.length);
                                                                        }

                                                                        for (var pi = cursors.length - 1; pi >= 0; pi--) {
                                                                            var cur = cursors[pi];
                                                                            var minP = Math.min(cur.start, cur.end);
                                                                            var maxP = Math.max(cur.start, cur.end);
                                                                            var curPaste = isLineMatch ? pasteLines[pi] : pasteText;
                                                                            if (minP !== maxP) {
                                                                                codeTextArea.remove(minP, maxP);
                                                                            }
                                                                            codeTextArea.insert(minP, curPaste);
                                                                        }

                                                                        var newCursors = [];
                                                                        var cumShift = 0;
                                                                        for (var k = 0; k < cursors.length; k++) {
                                                                            var finalPos = localPos[k] + cumShift;
                                                                            newCursors.push({ start: finalPos, end: finalPos, cursor: finalPos });
                                                                            cumShift += deltas[k];
                                                                        }

                                                                        root.extraCursors = newCursors;
                                                                        if (newCursors.length > 0) {
                                                                            codeTextArea.cursorPosition = newCursors[newCursors.length - 1].cursor;
                                                                        }
                                                                        event.accepted = true;
                                                                        return;
                                                                    }
                                                                } else if (event.key === Qt.Key_Z && !(event.modifiers & Qt.ShiftModifier)) {
                                                                    if (root.multiCursorUndoStack.length > 0) {
                                                                        var undoArr = root.multiCursorUndoStack.slice();
                                                                        var prevSnap = undoArr.pop();
                                                                        root.multiCursorUndoStack = undoArr;

                                                                        var redoArr = root.multiCursorRedoStack.slice();
                                                                        redoArr.push({ text: codeTextArea.text, cursors: JSON.parse(JSON.stringify(root.extraCursors)) });
                                                                        root.multiCursorRedoStack = redoArr;

                                                                        codeTextArea.text = prevSnap.text;
                                                                        root.extraCursors = prevSnap.cursors;
                                                                        if (prevSnap.cursors && prevSnap.cursors.length > 0) {
                                                                            var lastC = prevSnap.cursors[prevSnap.cursors.length - 1];
                                                                            codeTextArea.cursorPosition = (typeof lastC === "object") ? lastC.cursor : lastC;
                                                                        }
                                                                        event.accepted = true;
                                                                        return;
                                                                    }
                                                                } else if (event.key === Qt.Key_Y || ((event.modifiers & Qt.ShiftModifier) && event.key === Qt.Key_Z)) {
                                                                    if (root.multiCursorRedoStack.length > 0) {
                                                                        var redoArr2 = root.multiCursorRedoStack.slice();
                                                                        var nextSnap = redoArr2.pop();
                                                                        root.multiCursorRedoStack = redoArr2;

                                                                        var undoArr2 = root.multiCursorUndoStack.slice();
                                                                        undoArr2.push({ text: codeTextArea.text, cursors: JSON.parse(JSON.stringify(root.extraCursors)) });
                                                                        root.multiCursorUndoStack = undoArr2;

                                                                        codeTextArea.text = nextSnap.text;
                                                                        root.extraCursors = nextSnap.cursors;
                                                                        if (nextSnap.cursors && nextSnap.cursors.length > 0) {
                                                                            var lastC2 = nextSnap.cursors[nextSnap.cursors.length - 1];
                                                                            codeTextArea.cursorPosition = (typeof lastC2 === "object") ? lastC2.cursor : lastC2;
                                                                        }
                                                                        event.accepted = true;
                                                                        return;
                                                                    }
                                                                }
                                                            }

                                                            // 0.42 Multi-Cursor Escape key cancels multi-cursor mode
                                                            if (event.key === Qt.Key_Escape && root.extraCursors.length > 0) {
                                                                root.extraCursors = [];
                                                                root.multiCursorUndoStack = [];
                                                                root.multiCursorRedoStack = [];
                                                                event.accepted = true;
                                                                return;
                                                            }

                                                            // 0.45 Multi-Cursor Typing, Backspacing, Deleting & Enter
                                                            if (root.extraCursors.length > 0) {
                                                                // Normalize all cursor positions/ranges
                                                                function getNormalizedCursors() {
                                                                    var list = [];
                                                                    for (var i = 0; i < root.extraCursors.length; i++) {
                                                                        var item = root.extraCursors[i];
                                                                        if (typeof item === "object") {
                                                                            list.push({ start: item.start, end: item.end, cursor: item.cursor });
                                                                        } else {
                                                                            list.push({ start: item, end: item, cursor: item });
                                                                        }
                                                                    }
                                                                    var unique = [];
                                                                    for (var u = 0; u < list.length; u++) {
                                                                        var it = list[u];
                                                                        var dup = false;
                                                                        for (var k = 0; k < unique.length; k++) {
                                                                            if (unique[k].start === it.start && unique[k].end === it.end) {
                                                                                dup = true;
                                                                                break;
                                                                            }
                                                                        }
                                                                        if (!dup) unique.push(it);
                                                                    }
                                                                    return unique;
                                                                }

                                                                function recordMultiCursorEditSnapshot() {
                                                                    var stack = root.multiCursorUndoStack.slice();
                                                                    stack.push({ text: codeTextArea.text, cursors: JSON.parse(JSON.stringify(root.extraCursors)) });
                                                                    if (stack.length > 50) stack.shift();
                                                                    root.multiCursorUndoStack = stack;
                                                                    root.multiCursorRedoStack = [];
                                                                }

                                                                if (event.key === Qt.Key_Backspace) {
                                                                    recordMultiCursorEditSnapshot();
                                                                    var cursors = getNormalizedCursors();
                                                                    var deltas = [];
                                                                    var localPos = [];

                                                                    for (var i = 0; i < cursors.length; i++) {
                                                                        var cur = cursors[i];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            deltas.push(-(maxP - minP));
                                                                            localPos.push(minP);
                                                                        } else if (minP > 0) {
                                                                            deltas.push(-1);
                                                                            localPos.push(minP - 1);
                                                                        } else {
                                                                            deltas.push(0);
                                                                            localPos.push(0);
                                                                        }
                                                                    }

                                                                    for (var bi = cursors.length - 1; bi >= 0; bi--) {
                                                                        var cur = cursors[bi];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            codeTextArea.remove(minP, maxP);
                                                                        } else if (minP > 0) {
                                                                            codeTextArea.remove(minP - 1, minP);
                                                                        }
                                                                    }

                                                                    var newCursors = [];
                                                                    var cumShift = 0;
                                                                    for (var k = 0; k < cursors.length; k++) {
                                                                        var finalPos = localPos[k] + cumShift;
                                                                        newCursors.push({ start: finalPos, end: finalPos, cursor: finalPos });
                                                                        cumShift += deltas[k];
                                                                    }

                                                                    root.extraCursors = newCursors;
                                                                    if (newCursors.length > 0) {
                                                                        codeTextArea.cursorPosition = newCursors[newCursors.length - 1].cursor;
                                                                    }
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.key === Qt.Key_Delete) {
                                                                    recordMultiCursorEditSnapshot();
                                                                    var cursors = getNormalizedCursors();
                                                                    var deltas = [];
                                                                    var localPos = [];
                                                                    var docLen = codeTextArea.text.length;

                                                                    for (var i = 0; i < cursors.length; i++) {
                                                                        var cur = cursors[i];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            deltas.push(-(maxP - minP));
                                                                            localPos.push(minP);
                                                                        } else if (minP < docLen) {
                                                                            deltas.push(-1);
                                                                            localPos.push(minP);
                                                                        } else {
                                                                            deltas.push(0);
                                                                            localPos.push(minP);
                                                                        }
                                                                    }

                                                                    for (var di = cursors.length - 1; di >= 0; di--) {
                                                                        var cur = cursors[di];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            codeTextArea.remove(minP, maxP);
                                                                        } else if (minP < codeTextArea.text.length) {
                                                                            codeTextArea.remove(minP, minP + 1);
                                                                        }
                                                                    }

                                                                    var newCursors = [];
                                                                    var cumShift = 0;
                                                                    for (var k = 0; k < cursors.length; k++) {
                                                                        var finalPos = localPos[k] + cumShift;
                                                                        newCursors.push({ start: finalPos, end: finalPos, cursor: finalPos });
                                                                        cumShift += deltas[k];
                                                                    }

                                                                    root.extraCursors = newCursors;
                                                                    if (newCursors.length > 0) {
                                                                        codeTextArea.cursorPosition = newCursors[newCursors.length - 1].cursor;
                                                                    }
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                                                    recordMultiCursorEditSnapshot();
                                                                    var cursors = getNormalizedCursors();
                                                                    var deltas = [];
                                                                    var localPos = [];

                                                                    for (var i = 0; i < cursors.length; i++) {
                                                                        var cur = cursors[i];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        deltas.push(1 - (maxP - minP));
                                                                        localPos.push(minP + 1);
                                                                    }

                                                                    for (var ei = cursors.length - 1; ei >= 0; ei--) {
                                                                        var cur = cursors[ei];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            codeTextArea.remove(minP, maxP);
                                                                        }
                                                                        codeTextArea.insert(minP, "\n");
                                                                    }

                                                                    var newCursors = [];
                                                                    var cumShift = 0;
                                                                    for (var k = 0; k < cursors.length; k++) {
                                                                        var finalPos = localPos[k] + cumShift;
                                                                        newCursors.push({ start: finalPos, end: finalPos, cursor: finalPos });
                                                                        cumShift += deltas[k];
                                                                    }

                                                                    root.extraCursors = newCursors;
                                                                    if (newCursors.length > 0) {
                                                                        codeTextArea.cursorPosition = newCursors[newCursors.length - 1].cursor;
                                                                    }
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.text && event.text.length === 1 && !(event.modifiers & Qt.ControlModifier) && !(event.modifiers & Qt.AltModifier) && event.key !== Qt.Key_Tab) {
                                                                    recordMultiCursorEditSnapshot();
                                                                    var charTyped = event.text;
                                                                    var cursors = getNormalizedCursors();
                                                                    var deltas = [];
                                                                    var localPos = [];

                                                                    for (var i = 0; i < cursors.length; i++) {
                                                                        var cur = cursors[i];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        deltas.push(charTyped.length - (maxP - minP));
                                                                        localPos.push(minP + charTyped.length);
                                                                    }

                                                                    for (var ci = cursors.length - 1; ci >= 0; ci--) {
                                                                        var cur = cursors[ci];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            codeTextArea.remove(minP, maxP);
                                                                        }
                                                                        codeTextArea.insert(minP, charTyped);
                                                                    }

                                                                    var newCursors = [];
                                                                    var cumShift = 0;
                                                                    for (var k = 0; k < cursors.length; k++) {
                                                                        var finalPos = localPos[k] + cumShift;
                                                                        newCursors.push({ start: finalPos, end: finalPos, cursor: finalPos });
                                                                        cumShift += deltas[k];
                                                                    }

                                                                    root.extraCursors = newCursors;
                                                                    if (newCursors.length > 0) {
                                                                        codeTextArea.cursorPosition = newCursors[newCursors.length - 1].cursor;
                                                                    }
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

                                                            // 4.1 Auto Bracket & Quote Closing
                                                            if (theme && theme.autoCloseBracketsQuotes && !hasSelection) {
                                                                var pos = codeTextArea.cursorPosition;
                                                                var docT = codeTextArea.text;
                                                                var charMap = {
                                                                    "(": ")",
                                                                    "[": "]",
                                                                    "{": "}",
                                                                    "\"": "\"",
                                                                    "'": "'",
                                                                    "`": "`"
                                                                };
                                                                var closingChars = [")", "]", "}", "\"", "'", "`"];

                                                                // Over-type existing closing character
                                                                if (closingChars.indexOf(event.text) !== -1 && pos < docT.length && docT.charAt(pos) === event.text) {
                                                                    codeTextArea.cursorPosition = pos + 1;
                                                                    event.accepted = true;
                                                                    return;
                                                                }

                                                                // Auto insert pair
                                                                if (charMap[event.text]) {
                                                                    var nextCh = pos < docT.length ? docT.charAt(pos) : "";
                                                                    if (!nextCh || /\s|[)\]};:,]/.test(nextCh)) {
                                                                        codeTextArea.insert(pos, event.text + charMap[event.text]);
                                                                        codeTextArea.cursorPosition = pos + 1;
                                                                        event.accepted = true;
                                                                        return;
                                                                    }
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
                            }

                            // Minimap on right edge
                            CodeMinimap {
                                id: codeMinimap
                                objectName: "codeMinimap"
                                Layout.fillHeight: true
                                visible: theme ? theme.enableMinimap : true
                                documentText: ""
                                totalLineCount: root.activeEditorPane ? root.activeEditorPane.paneTotalLineCount : 1
                                visibleRatio: root.editorFlickable ? (root.editorFlickable.height / Math.max(1, root.editorFlickable.contentHeight)) : 1.0
                                scrollRatio: root.editorFlickable ? (root.editorFlickable.contentY / Math.max(1, (root.editorFlickable.contentHeight - root.editorFlickable.height))) : 0.0

                                onScrollRequested: function(ratio) {
                                    if (root.editorFlickable) {
                                        root.editorFlickable.contentY = ratio * Math.max(0, root.editorFlickable.contentHeight - root.editorFlickable.height);
                                    }
                                }
                            }

                            Timer {
                                id: minimapDeferredUpdateTimer
                                interval: 100
                                repeat: false
                                onTriggered: {
                                    if (codeMinimap && root.currentTab) {
                                        var tabKey = root.currentTab.fileId || root.currentTab.path || root.currentTab.title || "tab";
                                        codeMinimap.setTabAndText(tabKey, root.getCanonicalText());
                                    }
                                }
                            }

                            Connections {
                                target: root
                                function onActiveTabIndexChanged() {
                                    if (codeMinimap && root.currentTab) {
                                        var tabKey = root.currentTab.fileId || root.currentTab.path || root.currentTab.title || "tab";
                                        codeMinimap.setTabAndText(tabKey, root.getCanonicalText());
                                    } else {
                                        minimapDeferredUpdateTimer.restart();
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

                            onActionSelected: function(actionId, customAction) {
                                radialContextMenu.visible = false;
                                root.executeEditorAction(actionId, customAction);
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
                                onTriggered: (root.codeTextArea && root.codeTextArea.selectedText) ? root.askAi(root.codeTextArea.selectedText, root.codeTextArea.selectionStart, root.codeTextArea.selectionEnd, root.currentLanguageId) : root.requestRunFile()
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
                            objectName: "findReplaceBar"
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
                        visible: Boolean(root.currentTab && root.currentTab.isWhiteboard)
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
                        visible: Boolean(root.currentTab && (root.currentTab.isWebPreview || root.currentTab.languageId === "webpreview"))
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
                                visible: Boolean(!root.secondaryTab || (!root.secondaryTab.isWhiteboard && !root.secondaryTab.isWebPreview && root.secondaryTab.languageId !== "webpreview"))

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
                                            property var secGuideSegments: []

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
                                                interval: 200
                                                repeat: false
                                                onTriggered: {
                                                    if (secCodeTextArea) {
                                                        secIndentGuidesCanvas.secGuideSegments = root.computeGuideSegmentsForText(secCodeTextArea.text);
                                                    }
                                                    secIndentGuidesCanvas.requestPaint();
                                                }
                                            }

                                            Connections {
                                                target: secCodeTextArea
                                                function onTextChanged() { secCanvasDebounceTimer.restart(); }
                                            }

                                            Connections {
                                                target: root
                                                function onActiveTabIndexChanged() { secCanvasDebounceTimer.restart(); }
                                                function onSecondaryTabIndexChanged() { secCanvasDebounceTimer.restart(); }
                                                function onCharWidthChanged() { secIndentGuidesCanvas.requestPaint(); }
                                                function onEditorLineHeightChanged() { secIndentGuidesCanvas.requestPaint(); }
                                                function onCachedIndentLevelWidthsChanged() { secIndentGuidesCanvas.requestPaint(); }
                                            }

                                            onPaint: {
                                                var ctx = getContext("2d");
                                                ctx.clearRect(0, 0, width, height);

                                                var segments = secIndentGuidesCanvas.secGuideSegments;
                                                if (!segments || segments.length === 0) return;

                                                var leftPadding = secCodeTextArea.leftPadding - secEditorFlickable.contentX;
                                                var topPadding = secCodeTextArea.topPadding;
                                                var lineH = root.editorLineHeight;
                                                var charW = root.charWidth;
                                                var cachedWidths = root.cachedIndentLevelWidths;

                                                var viewTop = secEditorFlickable.contentY;
                                                var visibleStartLine = Math.max(0, Math.floor(viewTop / lineH) - 1);
                                                var visibleEndLine = visibleStartLine + Math.ceil(height / lineH) + 4;
                                                ctx.lineWidth = 1;

                                                for (var i = 0; i < segments.length; i++) {
                                                    var seg = segments[i];
                                                    if (seg.endLine < visibleStartLine || seg.startLine > visibleEndLine) continue;

                                                    var lvl = seg.level;
                                                    var lvlWidth = (lvl < cachedWidths.length) ? cachedWidths[lvl] : (lvl * cachedWidths[1]);
                                                    var x = leftPadding + lvlWidth;
                                                    var drawX = Math.round(x) + 0.5;

                                                    if (drawX < -20 || drawX > width + 20) continue;

                                                    var yStart = topPadding + (seg.startLine * lineH) - viewTop;
                                                    var yEnd = seg.hasClosingBrace ? (topPadding + (seg.endLine * lineH) + (lineH * 0.5) - viewTop) : (topPadding + ((seg.endLine + 1) * lineH) - viewTop);

                                                    ctx.strokeStyle = (typeof theme !== "undefined" && theme && theme.borderSubtle) ? theme.borderSubtle : "#35383d";
                                                    ctx.globalAlpha = 0.35;

                                                    ctx.beginPath();
                                                    ctx.moveTo(drawX, yStart);
                                                    ctx.lineTo(drawX, yEnd);
                                                    if (seg.hasClosingBrace) {
                                                        ctx.lineTo(drawX + Math.round(charW * 0.45), yEnd);
                                                    }
                                                    ctx.stroke();
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
                                            contentWidth: (theme && theme.enableWordWrap) ? width : Math.max(width, secCodeTextArea.contentWidth + secCodeTextArea.leftPadding + secCodeTextArea.rightPadding + 60)
                                            contentHeight: (theme && theme.enableWordWrap) ? Math.max(height, secCodeTextArea.contentHeight + secCodeTextArea.topPadding + secCodeTextArea.bottomPadding + 220) : Math.max(height, secCodeTextArea.height + Math.max(250, height * 0.5))

                                            WheelHandler {
                                                target: secEditorFlickable
                                                acceptedModifiers: Qt.NoModifier
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
                                                width: (theme && theme.enableWordWrap) ? secEditorFlickable.width : Math.max(secEditorFlickable.width, secEditorFlickable.contentWidth)
                                                height: secEditorFlickable.contentHeight
                                                topPadding: 6
                                                bottomPadding: 16
                                                leftPadding: 10
                                                rightPadding: 16
                                                wrapMode: (theme && theme.enableWordWrap) ? TextArea.WrapAtWordBoundaryOrAnywhere : TextArea.NoWrap
                                                color: theme ? theme.textPrimary : "#cccccc"
                                                selectionColor: theme ? theme.synSelection : "#264f78"
                                                selectedTextColor: theme ? theme.textBright : "#ffffff"
                                                font.pixelSize: (typeof theme !== "undefined" && theme && theme.editorFontSize) ? theme.editorFontSize : 13
                                                font.family: (typeof theme !== "undefined" && theme && (theme.editorFontFamily || theme.fontFamilyMono)) ? (theme.editorFontFamily || theme.fontFamilyMono) : "Consolas"
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
                                                    if (root.isSyncingSecondary || root.isInitialTextLoading || root.isRestoringTab || root.isFoldingOperation) return;
                                                    if (root.secondaryTab && root.secondaryTabIndex >= 0 && root.secondaryTabIndex < tabModel.count) {
                                                        tabModel.setProperty(root.secondaryTabIndex, "content", secCodeTextArea.text);
                                                        var curTab = tabModel.get(root.secondaryTabIndex);
                                                        if (curTab && !curTab.isDirty) {
                                                            tabModel.setProperty(root.secondaryTabIndex, "isDirty", true);
                                                        }
                                                        if (root.secondaryTabIndex === root.activeTabIndex && codeTextArea && codeTextArea.text !== secCodeTextArea.text) {
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
                                visible: Boolean(root.secondaryTab && root.secondaryTab.isWhiteboard)
                            }

                            // Secondary Web Preview Surface
                            WebPreviewView {
                                anchors.fill: parent
                                visible: Boolean(root.secondaryTab && (root.secondaryTab.isWebPreview || root.secondaryTab.languageId === "webpreview"))
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

    function executeEditorAction(actionId, customAction) {
        if (actionId === "format") {
            root.formatDocument();
        } else if (actionId === "ask_ai") {
            // 1. Selected Code -> Ask AI: Direct selection-based workflow (Never opens prompt popup)
            if (typeof mainWindow !== "undefined" && mainWindow) {
                if (!mainWindow.rightPanelVisible) mainWindow.rightPanelVisible = true;
                mainWindow.aiVisible = true;
            }
            var code = (codeTextArea && codeTextArea.selectedText) ? codeTextArea.selectedText : "";
            if (code.length > 0) {
                root.askAi(code, codeTextArea.selectionStart, codeTextArea.selectionEnd, root.currentLanguageId);
            }
        } else if (actionId === "ai" || actionId === "radial_ai") {
            // 2. Radial Menu -> AI: ONLY this action opens the compact Ctrl+P prompt popup
            if (typeof aiQuickPromptPopup !== "undefined" && aiQuickPromptPopup) {
                aiQuickPromptPopup.open();
            }
        } else if (actionId === "comment") {
            root.toggleComment();
        } else if (actionId === "music") {
            if (typeof mainWindow !== "undefined" && mainWindow) {
                if (!mainWindow.rightPanelVisible) mainWindow.rightPanelVisible = true;
                mainWindow.musicVisible = !mainWindow.musicVisible;
            }
        } else if (actionId === "zen") {
            if (typeof mainWindow !== "undefined" && mainWindow) {
                mainWindow.zenMode = !mainWindow.zenMode;
            }
        } else if (actionId === "terminal") {
            if (typeof mainWindow !== "undefined" && mainWindow) {
                mainWindow.terminalVisible = !mainWindow.terminalVisible;
            }
        } else if (actionId === "settings") {
            if (typeof settingsOverlay !== "undefined" && settingsOverlay) {
                settingsOverlay.visible = true;
            }
        } else if (actionId === "rename") {
            root.triggerRenameSymbol();
        } else if (actionId === "quickopen") {
            if (typeof quickOpenPalette !== "undefined" && quickOpenPalette) {
                quickOpenPalette.open();
            }
        } else if (actionId === "run") {
            if (codeTextArea && codeTextArea.selectedText && codeTextArea.selectedText.trim().length > 0) {
                root.askAi(codeTextArea.selectedText, codeTextArea.selectionStart, codeTextArea.selectionEnd, root.currentLanguageId);
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
        } else if (actionId === "save") {
            root.saveActiveFile();
        } else if (actionId === "copy") {
            if (codeTextArea) codeTextArea.copy();
        } else if (actionId === "cut") {
            if (codeTextArea) codeTextArea.cut();
        } else if (actionId === "paste") {
            if (codeTextArea) codeTextArea.paste();
        } else if (actionId === "undo") {
            if (codeTextArea) codeTextArea.undo();
        } else if (actionId === "redo") {
            if (codeTextArea) codeTextArea.redo();
        } else if (actionId === "find") {
            root.showFind(false);
        } else if (customAction && customAction.length > 0) {
            if (typeof terminalPanel !== "undefined" && terminalPanel && terminalPanel.executeCommand) {
                terminalPanel.activeTab = "TERMINAL";
                if (typeof mainWindow !== "undefined" && mainWindow) mainWindow.terminalVisible = true;
                terminalPanel.executeCommand(customAction);
            }
        }
    }

    // =========================================================================
    // ACCURATE MULTI-LANGUAGE CODE FORMATTER (Non-blocking & Asynchronous)
    // =========================================================================
    function formatDocument() {
        if (!codeTextArea) return;
        var text = codeTextArea.text;
        if (!text || text.trim().length === 0) return;
        if (root.isFormatting) return;

        var lang = root.currentLanguageId;
        var ext = root.activeFileName ? root.activeFileName.split(".").pop().toLowerCase() : "";
        var tabSize = theme ? theme.tabSize : 4;
        var effectivePath = root.activeFilePath || root.activeFileName || "";

        // Dispatch asynchronously to prevent freezing or locking the Qt UI thread
        if (typeof backend !== "undefined" && backend && backend.request_format_code) {
            root.formatRequestSeq++;
            root.activeFormatReqId = "fmt_" + Date.now() + "_" + root.formatRequestSeq;
            root.isFormatting = true;
            try {
                backend.request_format_code(root.activeFormatReqId, lang, effectivePath, text, tabSize);
                return;
            } catch (e) {
                console.log("[EditorArea] Backend async format notice:", e);
                root.isFormatting = false;
                root.activeFormatReqId = "";
            }
        }

        // Local JSON fallback if backend is unavailable
        if (lang === "json" || ext === "json") {
            try {
                var parsed = JSON.parse(text);
                var formattedText = JSON.stringify(parsed, null, tabSize);
                if (formattedText === text) {
                    if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                        mainWindow.showNotification("Document is already formatted.", "info", "Formatter", 2500);
                    }
                    return;
                }
                codeTextArea.text = formattedText;
                if (root.activeTabIndex >= 0 && root.activeTabIndex < tabModel.count) {
                    tabModel.setProperty(root.activeTabIndex, "isDirty", true);
                }
                root.isCurrentFileDirty = true;
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification("JSON formatted successfully", "success", "Formatter", 2500);
                }
                return;
            } catch (e) {
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification("JSON syntax error: " + e.message, "error", "Formatter");
                }
                return;
            }
        }

        // Synchronous fallback if backend only supports format_code
        if (typeof backend !== "undefined" && backend && backend.format_code) {
            var formatResult = null;
            try {
                formatResult = backend.format_code(lang, effectivePath, text, tabSize);
            } catch (e) {
                console.log("[EditorArea] Backend format fallback error:", e);
            }
            if (formatResult) {
                if (formatResult.available === false) {
                    if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                        mainWindow.showNotification(formatResult.message || "No formatter available for this language.", "warning", "Formatter");
                    }
                    return;
                }
                if (!formatResult.success) {
                    if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                        mainWindow.showNotification(formatResult.message || "Formatting failed.", "error", "Formatter");
                    }
                    return;
                }
                var resFormatted = formatResult.formatted || text;
                if (resFormatted === text) {
                    if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                        mainWindow.showNotification(formatResult.message || "Document is already formatted.", "info", "Formatter", 2500);
                    }
                    return;
                }
                codeTextArea.text = resFormatted;
                if (root.activeTabIndex >= 0 && root.activeTabIndex < tabModel.count) {
                    tabModel.setProperty(root.activeTabIndex, "isDirty", true);
                }
                root.isCurrentFileDirty = true;
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification(formatResult.message || "Formatted successfully.", "success", "Formatter", 2500);
                }
                return;
            }
        }

        var warnMsg = "No formatter is currently installed for '" + (lang || ext || "this file") + "'.";
        if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
            mainWindow.showNotification(warnMsg, "warning", "Formatter");
        }
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
        if (!codeTextArea) return;
        var r = codeTextArea.positionToRectangle(codeTextArea.cursorPosition);
        if (!r || r.height <= 0) {
            r = codeTextArea.cursorRectangle;
        }
        if (!r || r.height <= 0) return;

        var pane = root.activeEditorPane;
        var containerY = (pane && pane.isVirtualized) ? (pane.windowStartLine * pane.paneLineHeight) : 0;
        var curY = containerY + r.y;
        var curH = r.height > 0 ? r.height : (pane ? pane.paneLineHeight : 18.0);
        var curX = r.x;
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
        var r = codeTextArea.positionToRectangle(codeTextArea.cursorPosition);
        if (!r || r.height <= 0) {
            r = codeTextArea.cursorRectangle;
        }
        var pane = root.activeEditorPane;
        var lineH = (pane && pane.paneLineHeight > 0) ? pane.paneLineHeight : (root.editorLineHeight > 0 ? root.editorLineHeight : 18.0);
        var charW = (pane && pane.paneCharWidth > 0) ? pane.paneCharWidth : (root.charWidth > 0 ? root.charWidth : 7.8);
        var localLine = Math.max(1, Math.floor((r.y - codeTextArea.topPadding) / lineH) + 1);
        var globalLine = (pane && pane.isVirtualized) ? (pane.windowStartLine + localLine) : localLine;
        var col = Math.max(1, Math.floor((r.x - codeTextArea.leftPadding) / charW) + 1);
        root.cursorLine = globalLine;
        root.cursorColumn = col;
        root.cursorPositionChanged(globalLine, col);
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

    Timer {
        id: sessionSaveDebounceTimer
        interval: 1000
        repeat: false
        onTriggered: {
            root.saveWorkspaceSession();
        }
    }

    function jumpToLineAndCol(line, col) {
        root.jumpToLine(line, col);
    }

    Timer {
        id: textChangeDebounceTimer
        interval: 300
        repeat: false
        onTriggered: {
            if (root.activeEditorPane && codeTextArea) {
                if (!root.activeEditorPane.isVirtualized) {
                    root.activeEditorPane.paneTotalLineCount = codeTextArea.lineCount > 0 ? codeTextArea.lineCount : countLines(codeTextArea.text);
                }
            }
            var canonical = root.getCanonicalText();
            if (root.currentTab) {
                root.currentTab.content = canonical;
            }
            if (codeMinimap) {
                var tabKeyVal = (root.currentTab && (root.currentTab.fileId || root.currentTab.path || root.currentTab.title)) || "tab";
                codeMinimap.setTabAndText(tabKeyVal, canonical);
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
        var fileId = "tab_" + Date.now() + "_" + newNum;

        if (typeof backend !== "undefined" && backend && backend.init_backing_document) {
            backend.init_backing_document(fileId, "");
        }

        tabModel.append({
                fileId: fileId,
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
        if (root.activeEditorPane) {
            root.activeEditorPane.savedContent = "";
            root.activeEditorPane.isUntitled = true;
        }
        tabModel.setProperty(newIdx, "isDirty", true);
        root.dirtyVersion++;
        root.activeFileChanged("", title, "Plain Text", true);
    }

    function loadFile(path, content) {
        for (var i = 0; i < tabModel.count; i++) {
            if (tabModel.get(i).path === path) {
                switchToTab(i);
                return;
            }
        }

        var fileName = path.split("/").pop().split("\\").pop();
        var langObj = LanguageRegistry.detectLanguage(fileName);
        var newIdx = tabModel.count;
        var fileId = "file_" + Date.now();

        if (typeof backend !== "undefined" && backend && backend.init_backing_document) {
            backend.init_backing_document(path, content || "");
        }

        root.isInitialTextLoading = true;
        try {
            tabModel.append({
                    fileId: fileId,
                    title: fileName,
                    path: path,
                    content: content || "",
                    isDirty: false,
                    languageName: langObj.name,
                    languageId: langObj.id,
                    cursorPos: 0,
                    scrollX: 0,
                    scrollY: 0
                });

            switchToTab(newIdx);

            if (root.activeEditorPane) {
                root.activeEditorPane.savedContent = content || "";
                root.activeEditorPane.isUntitled = false;
            }
            tabModel.setProperty(newIdx, "isDirty", false);
            root.dirtyVersion++;
            root.activeFileChanged(path, fileName, langObj.name, false);
            console.log("[Timing] File visible");
        } finally {
            Qt.callLater(function() {
                root.isInitialTextLoading = false;
                if (root.activeEditorPane) {
                    root.activeEditorPane.savedContent = content || "";
                    root.activeEditorPane.isUntitled = false;
                    if (root.activeEditorPane.updatePaneScopes) {
                        root.activeEditorPane.updatePaneScopes();
                    }
                }
                if (newIdx >= 0 && newIdx < tabModel.count) {
                    tabModel.setProperty(newIdx, "isDirty", false);
                    if (newIdx === root.activeTabIndex) {
                        root.dirtyVersion++;
                    }
                }
                minimapDeferredUpdateTimer.restart();
                console.log("[Timing] Editor fully responsive");
            });
        }
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
        return (root.foldableLinesMap && root.foldableLinesMap[lineNum] !== undefined) || (foldedMap && foldedMap[lineNum] !== undefined);
    }

    function getCanonicalText() {
        var pane = root.activeEditorPane;
        if (pane && pane.isVirtualized && typeof backend !== "undefined" && backend && backend.get_backing_text) {
            var fullDoc = backend.get_backing_text(pane.tabKey);
            if (fullDoc !== undefined && fullDoc !== null && fullDoc.length > 0) return fullDoc;
        }
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
        var text = codeTextArea ? codeTextArea.text : "";
        if (!text) {
            root.foldableLinesMap = {};
            return;
        }
        var map = {};
        var tabSize = (typeof theme !== "undefined" && theme && theme.tabSize) ? theme.tabSize : 4;
        var lines = text.split("\n");
        var total = Math.min(lines.length, 5000);

        // 1. Structural brace-based blocks ({ ... }) across multiple lines
        var stack = [];
        var inBlockComment = false;
        var inTripleQuote = false;
        var tripleQuoteChar = '';

        for (var l = 0; l < total; l++) {
            var line = lines[l];
            var inStr = false;
            var strQuote = '';

            for (var c = 0; c < line.length; c++) {
                var char = line.charAt(c);
                var nextChar = c + 1 < line.length ? line.charAt(c + 1) : '';

                if (inBlockComment) {
                    if (char === '*' && nextChar === '/') {
                        inBlockComment = false;
                        c++;
                    }
                    continue;
                }

                if (inTripleQuote) {
                    if (char === tripleQuoteChar && nextChar === tripleQuoteChar && c + 2 < line.length && line.charAt(c + 2) === tripleQuoteChar) {
                        inTripleQuote = false;
                        c += 2;
                    }
                    continue;
                }

                if (inStr) {
                    if (char === '\\') {
                        c++;
                    } else if (char === strQuote) {
                        inStr = false;
                    }
                    continue;
                }

                if (char === '/' && nextChar === '*') {
                    inBlockComment = true;
                    c++;
                    continue;
                }
                if (char === '/' && nextChar === '/') {
                    break;
                }
                if (char === '#') {
                    break;
                }

                if ((char === '"' || char === '\'') && nextChar === char && c + 2 < line.length && line.charAt(c + 2) === char) {
                    inTripleQuote = true;
                    tripleQuoteChar = char;
                    c += 2;
                    continue;
                }

                if (char === '"' || char === '\'' || char === '`') {
                    inStr = true;
                    strQuote = char;
                    continue;
                }

                if (char === '{') {
                    stack.push({ startLine: l });
                } else if (char === '}') {
                    if (stack.length > 0) {
                        var top = stack.pop();
                        if (l > top.startLine) {
                            var foldLine = top.startLine + 1; // 1-indexed
                            map[foldLine] = { endLine: l + 1, type: "brace" };

                            // If opening brace was alone on its line (Allman style),
                            // also allow folding from the preceding declaration line
                            if (top.startLine > 0 && lines[top.startLine].trim() === "{") {
                                var prevNonEmpty = top.startLine - 1;
                                while (prevNonEmpty >= 0 && lines[prevNonEmpty].trim().length === 0) {
                                    prevNonEmpty--;
                                }
                                if (prevNonEmpty >= 0 && lines[prevNonEmpty].trim().length > 0) {
                                    map[prevNonEmpty + 1] = { endLine: l + 1, type: "brace" };
                                }
                            }
                        }
                    }
                }
            }
        }

        // 2. Indentation-based blocks (Python, YAML, Markdown, general block indentations)
        for (var i = 0; i < total - 1; i++) {
            var curL = lines[i];
            var trimmed = curL.trim();
            if (trimmed.length === 0 || trimmed.startsWith("#") || trimmed.startsWith("//")) continue;

            var curCols = 0;
            for (var ci = 0; ci < curL.length; ci++) {
                var cch = curL.charAt(ci);
                if (cch === ' ') curCols += 1;
                else if (cch === '\t') curCols += tabSize - (curCols % tabSize);
                else break;
            }

            var blockEnd = -1;
            var foundDeeper = false;
            for (var n = i + 1; n < total; n++) {
                var nextL = lines[n];
                var nextTrimmed = nextL.trim();
                if (nextTrimmed.length === 0 || nextTrimmed.startsWith("#") || nextTrimmed.startsWith("//")) {
                    continue;
                }

                var nextCols = 0;
                for (var nci = 0; nci < nextL.length; nci++) {
                    var nch = nextL.charAt(nci);
                    if (nch === ' ') nextCols += 1;
                    else if (nch === '\t') nextCols += tabSize - (nextCols % tabSize);
                    else break;
                }

                if (nextCols > curCols) {
                    foundDeeper = true;
                    blockEnd = n;
                } else {
                    break;
                }
            }

            if (foundDeeper && blockEnd > i) {
                if (!map[i + 1]) {
                    map[i + 1] = { endLine: blockEnd + 1, type: "indent" };
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
            // FOLD: Find block boundary from foldableLinesMap or compute boundary
            var foldData = root.foldableLinesMap ? root.foldableLinesMap[lineNum] : null;
            var endIdx = -1;

            if (foldData && foldData.endLine && foldData.endLine > lineNum) {
                endIdx = Math.min(foldData.endLine, lines.length);
                if (foldData.type === "brace" && endIdx > startIdx + 1 && lines[endIdx - 1].trim().startsWith("}")) {
                    // Keep closing brace line visible: collapse up to endIdx - 1
                    endIdx = endIdx - 1;
                }
            } else {
                // Fallback boundary scanner
                var tabSize = (theme && theme.tabSize) ? theme.tabSize : 4;
                var curLeadMatch = curLine.match(/^(\s*)/);
                var baseLead = curLeadMatch ? curLeadMatch[1].replace(/\t/g, " ".repeat(tabSize)).length : 0;
                endIdx = startIdx + 1;

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
                            break;
                        }
                    }
                    endIdx++;
                }
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
        if (root.activeEditorPane && !root.activeEditorPane.isVirtualized) {
            root.activeEditorPane.paneTotalLineCount = lines.length;
        }
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
                if (!(typeof explorerPanel !== "undefined" && explorerPanel && explorerPanel.editingFilePath !== "")) {
                    root.codeTextArea.forceActiveFocus();
                }
                root.updateCursorPosition();
                root.ensureCursorVisible();
            }
            if (root.indentGuidesCanvas) {
                root.indentGuidesCanvas.requestPaint();
            }
            if (codeMinimap) {
                var tabKey = newTab.fileId || newTab.path || newTab.title || ("tab_" + index);
                codeMinimap.setTabAndText(tabKey, root.getCanonicalText());
            }
        }

        root.dirtyVersion++;
        root.activeFileChanged(newTab.path || "", newTab.title || "", root.currentLanguage, newTab.isDirty || false);
        diagnosticsTimer.restart();
    }

    function syncSecondaryEditor() {
        if (root.secondaryTab && typeof secCodeTextArea !== "undefined" && secCodeTextArea) {
            root.isSyncingSecondary = true;
            try {
                var targetContent = root.secondaryTab.content || "";
                if (secCodeTextArea.text !== targetContent) {
                    secCodeTextArea.text = targetContent;
                }
                if (typeof backend !== "undefined" && backend) {
                    if (backend.register_secondary_text_area) {
                        backend.register_secondary_text_area(secCodeTextArea);
                    }
                    if (backend.set_secondary_file) {
                        backend.set_secondary_file(root.secondaryTab.path || root.secondaryTab.title || "main.py");
                    }
                }
            } finally {
                root.isSyncingSecondary = false;
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

        root.isRestoringTab = true;
        try {
            tabModel.remove(index);

            if (tabModel.count === 0) {
                root.isSplitEditor = false;
                root.activeTabIndex = -1;
                root.secondaryTabIndex = -1;
                if (codeTextArea) {
                    codeTextArea.text = "";
                }
                if (root.activeEditorPane) {
                    root.activeEditorPane.paneTotalLineCount = 0;
                }
                if (codeMinimap) {
                    codeMinimap.documentText = "";
                }
                root.currentLanguage = "Plain Text";
                root.currentLanguageId = "text";
                if (typeof backend !== "undefined" && backend && backend.set_active_file) {
                    backend.set_active_file("", "text");
                }
                if (typeof indentGuidesCanvas !== "undefined" && indentGuidesCanvas) {
                    indentGuidesCanvas.requestPaint();
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
        } finally {
            root.isRestoringTab = false;
        }
    }

    function closeOtherTabs(targetIndex) {
        if (targetIndex < 0 || targetIndex >= tabModel.count) return;
        for (var i = tabModel.count - 1; i > targetIndex; i--) {
            closeTab(i);
        }
        for (var j = targetIndex - 1; j >= 0; j--) {
            closeTab(j);
        }
    }

    function closeTabsToTheRight(targetIndex) {
        if (targetIndex < 0 || targetIndex >= tabModel.count) return;
        for (var i = tabModel.count - 1; i > targetIndex; i--) {
            closeTab(i);
        }
    }

    function closeAllTabs() {
        for (var i = tabModel.count - 1; i >= 0; i--) {
            closeTab(i);
        }
    }

    function closeSavedTabs() {
        for (var i = tabModel.count - 1; i >= 0; i--) {
            var t = tabModel.get(i);
            if (t && !t.isDirty) {
                closeTab(i);
            }
        }
    }

    function copyTabPath(index) {
        if (index < 0 || index >= tabModel.count) return;
        var t = tabModel.get(index);
        if (t && t.path && typeof backend !== "undefined" && backend && backend.copy_path_to_clipboard) {
            backend.copy_path_to_clipboard(t.path);
        }
    }

    function revealTabInExplorer(index) {
        if (index < 0 || index >= tabModel.count) return;
        var t = tabModel.get(index);
        if (t && t.path && typeof backend !== "undefined" && backend && backend.reveal_in_explorer) {
            backend.reveal_in_explorer(t.path);
        }
    }

    function isTabDirty(index) {
        return (index >= 0 && index < tabModel.count && tabModel.get(index)) ? (tabModel.get(index).isDirty === true) : false;
    }

    function setTabDirty(index, dirty) {
        if (index >= 0 && index < tabModel.count) {
            tabModel.setProperty(index, "isDirty", dirty);
            root.dirtyVersion++;
        }
    }

    function getTabPath(index) {
        return (index >= 0 && index < tabModel.count && tabModel.get(index)) ? (tabModel.get(index).path || "") : "";
    }

    function closeTabByPath(targetPath) {
        if (!targetPath) return;
        var normTarget = targetPath.replace(/\\/g, "/");
        for (var i = 0; i < tabModel.count; i++) {
            var t = tabModel.get(i);
            if (t && t.path && t.path.replace(/\\/g, "/") === normTarget) {
                closeTab(i);
                return;
            }
        }
    }

    function renameTabByPath(oldPath, newPath) {
        if (!oldPath || !newPath) return;
        var normOld = oldPath.replace(/\\/g, "/");
        var normNew = newPath.replace(/\\/g, "/");
        for (var i = 0; i < tabModel.count; i++) {
            var t = tabModel.get(i);
            if (t && t.path && t.path.replace(/\\/g, "/") === normOld) {
                var newFileName = normNew.split("/").pop();
                var langObj = LanguageRegistry.detectLanguage(newFileName);
                tabModel.setProperty(i, "path", normNew);
                tabModel.setProperty(i, "title", newFileName);
                tabModel.setProperty(i, "languageName", langObj.name);
                tabModel.setProperty(i, "languageId", langObj.id);
                if (i === root.activeTabIndex) {
                    root.currentLanguage = langObj.name;
                    root.currentLanguageId = langObj.id;
                    if (typeof backend !== "undefined" && backend && backend.set_active_file) {
                        backend.set_active_file(normNew, langObj.id);
                    }
                    root.activeFileChanged(normNew, newFileName, langObj.name, t.isDirty || false);
                }
                return;
            }
        }
    }

    function saveCurrentFile() {
        if (!root.currentTab) return false;

        if (!root.currentTab.path) {
            return false;
        }

        if (typeof backend !== "undefined" && backend) {
            var pane = root.activeEditorPane;
            var tabKey = (pane && pane.tabKey) ? pane.tabKey : (root.currentTab.path || root.currentTab.fileId || "");
            var canonical = (pane && pane.isVirtualized && backend.get_backing_text) ? backend.get_backing_text(tabKey) : root.getCanonicalText();
            backend.save_file(root.currentTab.path, canonical);
            if (backend.mark_backing_document_saved) {
                backend.mark_backing_document_saved(tabKey);
            }
            if (backend.mark_document_saved && codeTextArea) {
                backend.mark_document_saved(codeTextArea);
            }
            if (root.activeEditorPane) {
                root.activeEditorPane.savedContent = canonical;
                root.activeEditorPane.isUntitled = false;
            }
            tabModel.setProperty(root.activeTabIndex, "isDirty", false);
            root.dirtyVersion++;
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
        var pane = root.activeEditorPane;
        var tabKey = (pane && pane.tabKey) ? pane.tabKey : (root.currentTab ? (root.currentTab.path || root.currentTab.fileId || "") : "");
        var canonical = (pane && pane.isVirtualized && backend.get_backing_text) ? backend.get_backing_text(tabKey) : root.getCanonicalText();

        if (root.currentTab) {
            root.currentTab.path = cleanPath;
            root.currentTab.title = fileName;
            root.currentTab.languageName = langObj.name;
            root.currentTab.languageId = langObj.id;
            if (typeof backend !== "undefined" && backend) {
                if (backend.init_backing_document) {
                    backend.init_backing_document(cleanPath, canonical);
                }
                if (backend.mark_backing_document_saved) {
                    backend.mark_backing_document_saved(cleanPath);
                }
                if (backend.mark_document_saved && codeTextArea) {
                    backend.mark_document_saved(codeTextArea);
                }
            }
            if (root.activeEditorPane) {
                root.activeEditorPane.savedContent = canonical;
                root.activeEditorPane.isUntitled = false;
            }
            tabModel.setProperty(root.activeTabIndex, "isDirty", false);
            root.dirtyVersion++;
            root.currentLanguage = langObj.name;
            root.currentLanguageId = langObj.id;
        }
        if (root.activeEditorPane) {
            root.activeEditorPane.savedContent = canonical;
            root.activeEditorPane.isUntitled = false;
        }

        if (typeof backend !== "undefined" && backend) {
            backend.save_file(cleanPath, canonical);
            if (backend.register_text_area && root.codeTextArea) {
                backend.register_text_area(root.codeTextArea, cleanPath, langObj.id);
            }
            root.activeFileChanged(cleanPath, fileName, root.currentLanguage, false);
        }
    }

    function undo() {
        if (root.activeEditorPane && root.activeEditorPane.codeTextArea) {
            var ta = root.activeEditorPane.codeTextArea;
            if (ta.canUndo) {
                ta.undo();
                root.updateCursorPosition();
                root.ensureCursorVisible();
                if (root.activeEditorPane.updatePaneScopes) {
                    root.activeEditorPane.updatePaneScopes();
                }
            }
        }
    }

    function redo() {
        if (root.activeEditorPane && root.activeEditorPane.codeTextArea) {
            var ta = root.activeEditorPane.codeTextArea;
            if (ta.canRedo) {
                ta.redo();
                root.updateCursorPosition();
                root.ensureCursorVisible();
                if (root.activeEditorPane.updatePaneScopes) {
                    root.activeEditorPane.updatePaneScopes();
                }
            }
        }
    }

    function insertSnippet(code) {
        if (!codeTextArea) return;
        var cleanCode = code || "";
        var start = codeTextArea.selectionStart;
        var end = codeTextArea.selectionEnd;
        if (start !== end) {
            var minPos = Math.min(start, end);
            var maxPos = Math.max(start, end);
            codeTextArea.remove(minPos, maxPos);
            codeTextArea.insert(minPos, cleanCode);
            codeTextArea.cursorPosition = minPos + cleanCode.length;
        } else {
            var cur = codeTextArea.cursorPosition;
            codeTextArea.insert(cur, cleanCode);
            codeTextArea.cursorPosition = cur + cleanCode.length;
        }
        codeTextArea.forceActiveFocus();
        root.updateCursorPosition();
        root.ensureCursorVisible();
        if (root.activeEditorPane && root.activeEditorPane.updatePaneScopes) {
            root.activeEditorPane.updatePaneScopes();
        }
    }

    function insertCode(code) {
        insertSnippet(code);
    }

    function replaceSelection(startPos, endPos, newCode, originalText) {
        if (!codeTextArea) return false;
        var docText = codeTextArea.text;
        var textLen = docText.length;
        if (startPos === undefined || startPos < 0 || endPos === undefined || endPos < startPos) {
            return false;
        }
        var s = Math.min(startPos, textLen);
        var e = Math.min(endPos, textLen);

        // Safety check: if originalText was provided, verify if the range or nearby text matches
        if (originalText && originalText.length > 0) {
            var currentRangeText = codeTextArea.getText(s, e);
            if (currentRangeText !== originalText) {
                var foundIndex = docText.indexOf(originalText, Math.max(0, s - 500));
                if (foundIndex !== -1 && Math.abs(foundIndex - s) < 1000) {
                    s = foundIndex;
                    e = foundIndex + originalText.length;
                } else {
                    console.warn("[EditorArea] Selection text mismatch, skipping replace to avoid altering wrong code.");
                    return false;
                }
            }
        }

        // Replace ONLY the saved selection range using native remove & insert to preserve undo/redo history
        codeTextArea.remove(s, e);
        codeTextArea.insert(s, newCode || "");
        codeTextArea.select(s, s + (newCode ? newCode.length : 0));
        codeTextArea.cursorPosition = s + (newCode ? newCode.length : 0);
        codeTextArea.forceActiveFocus();
        root.clearPendingAiReplacement();
        root.updateCursorPosition();
        root.ensureCursorVisible();
        return true;
    }

    function showFind(showReplace) {
        findReplaceBar.isReplaceMode = showReplace;
        // Strictly search ONLY the actual editor document (codeTextArea)
        if (root.codeTextArea && root.codeTextArea.selectedText && root.codeTextArea.selectedText.indexOf("\n") === -1) {
            findReplaceBar.setFindText(root.codeTextArea.selectedText);
        }
        findReplaceBar.visible = true;
        findReplaceBar.focusInput();
        updateFindMatches(findReplaceBar.findText, findReplaceBar.matchCase);
    }

    property var globalFindMatches: []

    function updateFindMatches(pattern, matchCase) {
        var pane = root.activeEditorPane;
        if (!pattern || !codeTextArea) {
            findReplaceBar.totalMatches = 0;
            findReplaceBar.currentMatchIndex = 0;
            root.globalFindMatches = [];
            return [];
        }

        if (pane && pane.isVirtualized && typeof backend !== "undefined" && backend && backend.search_backing_document) {
            var matches = backend.search_backing_document(pane.tabKey, pattern, matchCase, false);
            root.globalFindMatches = matches || [];
            findReplaceBar.totalMatches = root.globalFindMatches.length;
            return root.globalFindMatches;
        }

        var text = codeTextArea.text;
        var searchPattern = matchCase ? pattern : pattern.toLowerCase();
        var searchText = matchCase ? text : text.toLowerCase();
        var localMatches = [];
        var pos = 0;
        while ((pos = searchText.indexOf(searchPattern, pos)) !== -1) {
            localMatches.push(pos);
            pos += searchPattern.length;
        }
        findReplaceBar.totalMatches = localMatches.length;
        return localMatches;
    }

    function findNext(pattern, matchCase) {
        if (!pattern || !codeTextArea) return;
        var pane = root.activeEditorPane;

        if (pane && pane.isVirtualized && typeof backend !== "undefined" && backend && backend.search_backing_document) {
            var gMatches = updateFindMatches(pattern, matchCase);
            console.log("[FindNext Debug] query:", pattern, "matchCase:", matchCase, "count:", gMatches ? gMatches.length : 0);
            if (!gMatches || gMatches.length === 0) return;

            var curLine = root.cursorLine;
            var curCol = root.cursorColumn;
            var nextMatch = null;
            var matchIdx = 0;

            for (var i = 0; i < gMatches.length; i++) {
                var m = gMatches[i];
                if (m.startLine > curLine || (m.startLine === curLine && m.startCol > curCol)) {
                    nextMatch = m;
                    matchIdx = i;
                    break;
                }
            }
            if (!nextMatch) {
                nextMatch = gMatches[0];
                matchIdx = 0;
            }

            console.log("[FindNext Match]", "matchIdx:", matchIdx, "startLine:", nextMatch.startLine, "startCol:", nextMatch.startCol);
            findReplaceBar.currentMatchIndex = matchIdx;
            root.jumpToLine(nextMatch.startLine, nextMatch.startCol);
            var localPos = codeTextArea.cursorPosition;
            codeTextArea.select(localPos, localPos + pattern.length);
            root.updateCursorPosition();
            root.ensureCursorVisible();
            return;
        }

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
        var pane = root.activeEditorPane;

        if (pane && pane.isVirtualized && typeof backend !== "undefined" && backend && backend.search_backing_document) {
            var gMatches = updateFindMatches(pattern, matchCase);
            if (!gMatches || gMatches.length === 0) return;

            var curLine = root.cursorLine;
            var curCol = root.cursorColumn;
            var prevMatch = null;
            var matchIdx = 0;

            for (var i = gMatches.length - 1; i >= 0; i--) {
                var m = gMatches[i];
                if (m.startLine < curLine || (m.startLine === curLine && m.startCol < curCol)) {
                    prevMatch = m;
                    matchIdx = i;
                    break;
                }
            }
            if (!prevMatch) {
                prevMatch = gMatches[gMatches.length - 1];
                matchIdx = gMatches.length - 1;
            }

            findReplaceBar.currentMatchIndex = matchIdx;
            root.jumpToLine(prevMatch.startLine, prevMatch.startCol);
            var localPos = codeTextArea.cursorPosition;
            codeTextArea.select(localPos, localPos + pattern.length);
            root.updateCursorPosition();
            root.ensureCursorVisible();
            return;
        }

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
        var pane = root.activeEditorPane;
        if (pane && pane.isVirtualized && typeof backend !== "undefined" && backend && backend.get_backing_text && backend.update_backing_text) {
            var fullText = backend.get_backing_text(pane.tabKey);
            var regex = new RegExp(escapeRegExp(pattern), matchCase ? "g" : "gi");
            var newFullText = fullText.replace(regex, replacement || "");
            backend.update_backing_text(pane.tabKey, newFullText);
            pane.paneTotalLineCount = backend.get_backing_total_lines(pane.tabKey);
            pane.checkAndShiftWindow(true);
            tabModel.setProperty(root.activeTabIndex, "isDirty", true);
            root.dirtyVersion++;
            updateFindMatches(pattern, matchCase);
            return;
        }
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

        // Query Backend LSP asynchronously if method is implemented
        if (typeof backend !== "undefined" && backend && typeof backend.request_completion === "function") {
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

        var lineStart = text.lastIndexOf("\n", prefixStart - 1) + 1;
        var currentLine = text.substring(lineStart, prefixStart);
        var indentMatch = currentLine.match(/^(\s*)/);
        var baseIndent = indentMatch ? indentMatch[1] : "";

        var isSnippet = kind === "snippet" || word.indexOf("${") !== -1 || word.indexOf("$0") !== -1 || word.indexOf("$1") !== -1;
        var expanded = isSnippet ? SnippetManager.expandSnippetTemplate(word, baseIndent) : { text: word, cursorOffset: word.length, tabstops: [] };
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
                insertStr = "<" + insertStr + ">\n" + baseIndent + "    \n" + baseIndent + "</" + insertStr + ">";
                targetOffset = insertStr.indexOf("\n" + baseIndent + "    ") + (baseIndent.length + 5);
            }
        }

        if (hasTrailingAngle && (insertStr.startsWith("<") || hasLeadingAngle)) {
            removeEnd = pos + 1;
        }

        codeTextArea.remove(removeStart, removeEnd);
        codeTextArea.insert(removeStart, insertStr);

        if (isSnippet && expanded.tabstops && expanded.tabstops.length > 0) {
            root.activeSnippetStops = expanded.tabstops.map(function(s) {
                return {
                    tabstop: s.tabstop,
                    start: removeStart + s.start,
                    end: removeStart + s.end,
                    placeholder: s.placeholder
                };
            });
            root.activeSnippetStopIndex = 0;
            var firstStop = root.activeSnippetStops[0];
            codeTextArea.cursorPosition = firstStop.start;
            if (firstStop.end > firstStop.start) {
                codeTextArea.select(firstStop.start, firstStop.end);
            }
        } else {
            root.activeSnippetStops = [];
            root.activeSnippetStopIndex = -1;
            codeTextArea.cursorPosition = removeStart + targetOffset;
        }

        suggestionModel.clear();
        codeTextArea.forceActiveFocus();
    }

    function toggleExtraCursor(charPos) {
        if (!codeTextArea || charPos < 0 || charPos > codeTextArea.text.length) return;
        var arr = root.extraCursors.slice();
        var existingIdx = -1;
        for (var i = 0; i < arr.length; i++) {
            var c = arr[i];
            var cPos = (typeof c === "object") ? c.cursor : c;
            if (Math.abs(cPos - charPos) <= 1) {
                existingIdx = i;
                break;
            }
        }
        if (existingIdx !== -1) {
            arr.splice(existingIdx, 1);
            if (arr.length === 1) {
                var single = arr[0];
                codeTextArea.cursorPosition = (typeof single === "object") ? single.cursor : single;
                arr = [];
            }
        } else {
            if (arr.length === 0) {
                var mainPos = codeTextArea.cursorPosition;
                arr.push({ start: mainPos, end: mainPos, cursor: mainPos });
            }
            arr.push({ start: charPos, end: charPos, cursor: charPos });
            arr.sort(function(a, b) {
                var aP = (typeof a === "object") ? a.start : a;
                var bP = (typeof b === "object") ? b.start : b;
                return aP - bP;
            });
        }
        root.extraCursors = arr;
    }

    function addNextOccurrenceCursor() {
        if (!codeTextArea) return;
        var text = codeTextArea.text;
        var sStart = codeTextArea.selectionStart;
        var sEnd = codeTextArea.selectionEnd;
        var curPos = codeTextArea.cursorPosition;
        var arr = root.extraCursors.slice();

        var selText = "";
        if (arr.length > 0 && arr[0].start !== undefined && arr[0].end !== undefined && arr[0].start !== arr[0].end) {
            selText = text.substring(arr[0].start, arr[0].end);
        } else if (sStart !== undefined && sEnd !== undefined && sStart !== sEnd) {
            selText = text.substring(Math.min(sStart, sEnd), Math.max(sStart, sEnd));
        }

        if (!selText || selText.length === 0) {
            var wordStart = curPos;
            while (wordStart > 0 && /[a-zA-Z0-9_]/.test(text.charAt(wordStart - 1))) wordStart--;
            var wordEnd = curPos;
            while (wordEnd < text.length && /[a-zA-Z0-9_]/.test(text.charAt(wordEnd))) wordEnd++;
            if (wordEnd > wordStart) {
                codeTextArea.select(wordStart, wordEnd);
                selText = text.substring(wordStart, wordEnd);
                root.extraCursors = [{ start: wordStart, end: wordEnd, cursor: wordEnd }];
                return;
            } else {
                return;
            }
        }

        if (arr.length === 0) {
            var minS = (sStart !== undefined && sEnd !== undefined) ? Math.min(sStart, sEnd) : curPos;
            var maxS = (sStart !== undefined && sEnd !== undefined) ? Math.max(sStart, sEnd) : curPos;
            arr.push({ start: minS, end: maxS, cursor: maxS });
        }

        var searchStart = 0;
        for (var i = 0; i < arr.length; i++) {
            var c = arr[i];
            var cMax = Math.max(c.start, c.end);
            if (cMax > searchStart) searchStart = cMax;
        }

        var nextIdx = text.indexOf(selText, searchStart);
        if (nextIdx === -1) {
            nextIdx = text.indexOf(selText, 0);
        }

        if (nextIdx !== -1) {
            var alreadyPresent = false;
            for (var j = 0; j < arr.length; j++) {
                if (arr[j].start === nextIdx && arr[j].end === nextIdx + selText.length) {
                    alreadyPresent = true;
                    break;
                }
            }
            if (!alreadyPresent) {
                arr.push({ start: nextIdx, end: nextIdx + selText.length, cursor: nextIdx + selText.length });
                arr.sort(function(a, b) { return a.start - b.start; });
                root.extraCursors = arr;
                var lastItem = arr[arr.length - 1];
                codeTextArea.select(lastItem.start, lastItem.end);
                codeTextArea.cursorPosition = lastItem.cursor;
            }
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

    // =========================================================================
    // VS CODE ADVANCED NAVIGATION, HOVER, RENAME & QUICK OPEN OVERLAYS
    // =========================================================================
    

    RenameSymbolDialog {
        id: renameSymbolDialog
        onRenameConfirmed: function(oldName, newName) {
            if (!codeTextArea) return;
            if (typeof backend !== "undefined" && backend && backend.rename_symbol) {
                var res = backend.rename_symbol(root.activeFilePath, root.cursorLine, root.cursorColumn, oldName, newName, codeTextArea.text);
                if (res && res.success) {
                    codeTextArea.text = res.new_code;
                    if (root.activeTabIndex >= 0 && root.activeTabIndex < tabModel.count) {
                        tabModel.setProperty(root.activeTabIndex, "isDirty", true);
                    }
                    root.isCurrentFileDirty = true;
                    if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                        mainWindow.showNotification(res.message || "Renamed successfully.", "success", "Rename Symbol");
                    }
                } else {
                    if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                        mainWindow.showNotification((res && res.message) ? res.message : "Rename failed.", "error", "Rename Symbol");
                    }
                }
            }
        }
    }

    QuickOpenPalette {
        id: quickOpenPalette
        objectName: "quickOpenPalette"
        onFileSelected: function(filePath) {
            if (typeof backend !== "undefined" && backend && backend.open_file) {
                backend.open_file(filePath);
            }
        }
        onLineSelected: function(lineNum) {
            root.jumpToLine(lineNum);
        }
    }

    AIQuickPromptPopup {
        id: aiQuickPromptPopup
        onPromptSubmitted: function(prompt) {
            root.sendAiPrompt(prompt);
        }
    }

    function jumpToLine(targetLine, targetCol) {
        var pane = root.activeEditorPane;
        if (!pane || !pane.codeTextArea) return;
        var ta = pane.codeTextArea;
        var col = targetCol !== undefined ? Math.max(1, targetCol) : 1;

        if (pane.isVirtualized && typeof backend !== "undefined" && backend && backend.get_backing_slice) {
            var totalLines = pane.paneTotalLineCount;
            var tLine = Math.max(1, Math.min(targetLine, totalLines));
            var zeroBasedLine = tLine - 1;

            if (zeroBasedLine < pane.windowStartLine + 60 || zeroBasedLine > pane.windowEndLine - 60) {
                var halfWindow = 400;
                var newStart = Math.max(0, zeroBasedLine - halfWindow);
                var newEnd = Math.min(totalLines - 1, newStart + 800);
                newStart = Math.max(0, newEnd - 800);

                var sliceObj = backend.get_backing_slice(pane.tabKey, newStart, newEnd);
                if (sliceObj && sliceObj.text !== undefined) {
                    pane.isShifting = true;
                    console.log("[Virtualization Shift]", "reason: goto", "from:", pane.windowStartLine, "-", pane.windowEndLine, "to:", sliceObj.startLine, "-", sliceObj.endLine, "targetLine:", tLine);
                    root.isRestoringTab = true;
                    try {
                        pane.windowStartLine = sliceObj.startLine;
                        pane.windowEndLine = sliceObj.endLine;
                        ta.text = sliceObj.text;
                        pane.paneScopeRanges = root.computeScopesForText(ta.text);
                        pane.paneGuideSegments = root.computeGuideSegmentsForText(ta.text);
                        if (pane.indentGuidesCanvas) {
                            pane.indentGuidesCanvas.requestPaint();
                        }
                    } finally {
                        root.isRestoringTab = false;
                        pane.isShifting = false;
                    }
                }
            }

            var localLine = Math.max(1, tLine - pane.windowStartLine);
            var lines = ta.text.split("\n");
            var targetLocalLine = Math.min(localLine, lines.length);
            var charPos = 0;
            for (var l = 0; l < targetLocalLine - 1; l++) {
                charPos += lines[l].length + 1;
            }
            if (targetLocalLine - 1 < lines.length) {
                charPos += Math.min(col - 1, lines[targetLocalLine - 1].length);
            }
            ta.cursorPosition = Math.min(charPos, ta.text.length);
            ta.forceActiveFocus();
            if (pane.editorFlickable) {
                var targetY = (tLine - 1) * pane.paneLineHeight;
                pane.editorFlickable.contentY = Math.max(0, targetY - (pane.editorFlickable.height / 2));
            }
            root.updateCursorPosition();
            return;
        }

        var lines = ta.text.split("\n");
        var line = Math.max(1, Math.min(targetLine, lines.length));
        var charPos = 0;
        for (var l = 0; l < line - 1; l++) {
            charPos += lines[l].length + 1;
        }
        charPos += Math.min(col - 1, lines[line - 1].length);
        ta.cursorPosition = Math.min(charPos, ta.text.length);
        ta.forceActiveFocus();
        if (pane.editorFlickable) {
            var targetY = (line - 1) * root.editorLineHeight;
            pane.editorFlickable.contentY = Math.max(0, targetY - (pane.editorFlickable.height / 2));
        }
        root.updateCursorPosition();
    }

    function triggerRenameSymbol() {
        if (!codeTextArea) return;
        var text = codeTextArea.text;
        var curPos = codeTextArea.cursorPosition;
        var wStart = curPos;
        while (wStart > 0 && /[a-zA-Z0-9_]/.test(text[wStart - 1])) wStart--;
        var wEnd = curPos;
        while (wEnd < text.length && /[a-zA-Z0-9_]/.test(text[wEnd])) wEnd++;
        var sym = text.substring(wStart, wEnd).trim();
        if (!sym) return;

        var r = codeTextArea.positionToRectangle(wStart);
        var pt = codeTextArea.mapToItem(root, r.x, r.y);
        renameSymbolDialog.openAt(pt.x, pt.y, sym, root.cursorLine, root.cursorColumn);
    }

    function updateSelectionOccurrences() {
        if (!codeTextArea) {
            root.selectionOccurrences = [];
            return;
        }
        var sel = codeTextArea.selectedText;
        if (!sel || sel.trim().length < 2 || sel.indexOf("\n") !== -1) {
            root.selectionOccurrences = [];
            return;
        }
        var doc = codeTextArea.text;
        var selStart = Math.min(codeTextArea.selectionStart, codeTextArea.selectionEnd);
        var selEnd = Math.max(codeTextArea.selectionStart, codeTextArea.selectionEnd);
        var occs = [];
        var idx = 0;
        var maxOcc = 100;
        var isWord = /^[a-zA-Z0-9_]+$/.test(sel);

        while ((idx = doc.indexOf(sel, idx)) !== -1) {
            if (idx !== selStart) {
                // If it's a word, enforce word boundary so substrings aren't highlighted
                var valid = true;
                if (isWord) {
                    if (idx > 0 && /[a-zA-Z0-9_]/.test(doc.charAt(idx - 1))) valid = false;
                    if (idx + sel.length < doc.length && /[a-zA-Z0-9_]/.test(doc.charAt(idx + sel.length))) valid = false;
                }
                if (valid) {
                    occs.push({ start: idx, end: idx + sel.length });
                    if (occs.length >= maxOcc) break;
                }
            }
            idx += sel.length;
        }
        root.selectionOccurrences = occs;
    }

    function saveWorkspaceSession() {
        if (typeof settingsBackend === "undefined" || !settingsBackend || !settingsBackend.save_session_state) return;
        var tabsData = [];
        for (var i = 0; i < tabModel.count; i++) {
            var t = tabModel.get(i);
            if (t && t.path && !t.isWhiteboard && !t.isWebPreview) {
                var pane = (tabEditorRepeater && i < tabEditorRepeater.count) ? tabEditorRepeater.itemAt(i) : null;
                var cursorPos = (pane && pane.codeTextArea) ? pane.codeTextArea.cursorPosition : 0;
                var scrollY = (pane && pane.editorFlickable) ? pane.editorFlickable.contentY : 0;
                tabsData.push({
                    path: t.path,
                    title: t.title,
                    isDirty: t.isDirty || false,
                    draftContent: t.isDirty ? (pane && pane.codeTextArea ? pane.codeTextArea.text : "") : "",
                    cursorPosition: cursorPos,
                    scrollY: scrollY
                });
            }
        }
        var sessionObj = {
            activeTabIndex: root.activeTabIndex,
            isSplitEditor: root.isSplitEditor,
            splitRatio: root.splitRatio,
            secondaryTabIndex: root.secondaryTabIndex,
            tabs: tabsData
        };
        settingsBackend.save_session_state(JSON.stringify(sessionObj));
    }

    function restoreWorkspaceSession() {
        if (typeof settingsBackend === "undefined" || !settingsBackend || !settingsBackend.get_session_state) return;
        var stateJson = settingsBackend.get_session_state();
        if (!stateJson || stateJson === "{}") return;
        try {
            var session = JSON.parse(stateJson);
            if (session && session.tabs && Array.isArray(session.tabs)) {
                for (var i = 0; i < session.tabs.length; i++) {
                    var tabInfo = session.tabs[i];
                    if (tabInfo && tabInfo.path) {
                        var cleanPath = tabInfo.path.replace("file:///", "");
                        if (typeof backend !== "undefined" && backend && backend.open_file) {
                            backend.open_file(cleanPath);
                        }
                    }
                }
                if (session.activeTabIndex !== undefined && session.activeTabIndex >= 0) {
                    root.activeTabIndex = session.activeTabIndex;
                }
                if (session.isSplitEditor !== undefined) {
                    root.isSplitEditor = session.isSplitEditor;
                }
                if (session.splitRatio !== undefined) {
                    root.splitRatio = session.splitRatio;
                }
            }
        } catch (e) {
            console.log("Error restoring workspace session:", e);
        }
    }
}

