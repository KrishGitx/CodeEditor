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

    // Cursor and Line Metrics
    property int cursorLine: 1
    property int cursorColumn: 1
    property int totalLineCount: 1
    readonly property real editorLineHeight: fontMetrics.lineSpacing > 0 ? fontMetrics.lineSpacing : (codeTextArea.font.pixelSize * 1.45)

    // Signals for parent / status bar
    signal fileSaved(string path, bool success)
    signal activeFileChanged(string path, string name, string lang, bool dirty)
    signal cursorPositionChanged(int line, int col)
    signal requestOpenFile()
    signal requestOpenFolder()
    signal requestRunFile()

    FontMetrics {
        id: fontMetrics
        font: codeTextArea.font
    }

    Component.onCompleted: {
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

            onTabSelected: function(index) {
                root.switchToTab(index);
            }

            onTabClosed: function(index) {
                root.closeTab(index);
            }

            onNewTabRequested: function() {
                root.createNewFile();
            }
        }

        // Editor Surface (Code Editor OR Whiteboard Canvas Tab)
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            // 1. Code Editor Surface (Visible for code files)
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

                // Line Numbers Gutter
                Rectangle {
                    id: gutter
                    Layout.preferredWidth: Math.max(42, (root.totalLineCount.toString().length * 8 + 24))
                    Layout.fillHeight: true
                    color: theme ? theme.bgPanel : "#181818"
                    visible: theme ? theme.enableLineNumbers : true
                    clip: true

                    Flickable {
                        id: gutterFlickable
                        anchors.fill: parent
                        contentHeight: editorFlickable.contentHeight
                        contentY: editorFlickable.contentY
                        interactive: false
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            width: parent.width
                            anchors.top: parent.top
                            anchors.topMargin: codeTextArea.topPadding

                            Repeater {
                                model: root.totalLineCount

                                delegate: Item {
                                    width: gutter.width
                                    height: root.editorLineHeight

                                    Text {
                                        anchors.right: parent.right
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: (index + 1).toString()
                                        font.pixelSize: codeTextArea.font.pixelSize
                                        font.family: theme ? theme.fontFamilyMono : "monospace"
                                        color: (index + 1) === root.cursorLine ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
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

                    Flickable {
                        id: editorFlickable
                        anchors.fill: parent
                        contentWidth: Math.max(width, codeTextArea.contentWidth + codeTextArea.leftPadding + codeTextArea.rightPadding + 60)
                        contentHeight: Math.max(height, codeTextArea.contentHeight + codeTextArea.topPadding + codeTextArea.bottomPadding + Math.max(160, height * 0.5))
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        flickableDirection: Flickable.AutoFlickIfNeeded

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
                            y: codeTextArea.topPadding + (root.cursorLine - 1) * root.editorLineHeight
                            width: Math.max(editorFlickable.contentWidth, editorFlickable.width)
                            height: root.editorLineHeight
                            color: theme ? theme.synCurrentLine : "#282828"
                            z: 0
                        }

                        TextArea {
                            id: codeTextArea
                            width: Math.max(editorFlickable.width, editorFlickable.contentWidth)
                            height: Math.max(editorFlickable.height, contentHeight + topPadding + bottomPadding + 100)
                            topPadding: 6
                            bottomPadding: 160
                            leftPadding: 10
                            rightPadding: 20
                            wrapMode: (theme && theme.enableWordWrap) ? TextArea.Wrap : TextArea.NoWrap
                            tabStopDistance: (theme ? theme.tabSize : 4) * fontMetrics.averageCharacterWidth
                            color: theme ? theme.textPrimary : "#cccccc"
                            selectionColor: theme ? theme.synSelection : "#264f78"
                            selectedTextColor: theme ? theme.textBright : "#ffffff"
                            font.pixelSize: theme ? theme.editorFontSize : 13
                            font.family: theme ? theme.fontFamilyMono : "monospace"
                            selectByMouse: true
                            focus: true
                            textFormat: TextArea.PlainText
                            background: null

                            // Multi-Cursor Caret Overlays
                            Repeater {
                                model: root.extraCursors
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
                                running: root.extraCursors.length > 0
                                repeat: true
                                property bool blinkOn: true
                                onTriggered: blinkOn = !blinkOn
                            }

                            // Alt+Click Multi-Cursor TapHandler / MouseArea
                            MouseArea {
                                anchors.fill: parent
                                acceptedButtons: Qt.LeftButton
                                propagateComposedEvents: true
                                z: 5
                                cursorShape: Qt.IBeamCursor

                                onPressed: function(mouse) {
                                    if (mouse.modifiers & Qt.AltModifier) {
                                        mouse.accepted = true;
                                        var charPos = codeTextArea.positionAt(mouse.x, mouse.y);
                                        root.toggleExtraCursor(charPos);
                                    } else {
                                        if (root.extraCursors.length > 0) {
                                            root.extraCursors = [];
                                        }
                                        mouse.accepted = false; // Let TextArea handle normal cursor positioning
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
                                    var containerPos = mapToItem(textAreaContainer, mouse.x, mouse.y);
                                    rightClickOverlay.handleRightClickPress(containerPos.x, containerPos.y);
                                }

                                onPositionChanged: function(mouse) {
                                    mouse.accepted = true;
                                    var containerPos = mapToItem(textAreaContainer, mouse.x, mouse.y);
                                    rightClickOverlay.handleRightClickMove(containerPos.x, containerPos.y);
                                }

                                onReleased: function(mouse) {
                                    mouse.accepted = true;
                                    var containerPos = mapToItem(textAreaContainer, mouse.x, mouse.y);
                                    rightClickOverlay.handleRightClickRelease(containerPos.x, containerPos.y);
                                }

                                onCanceled: {
                                    rightClickOverlay.handleRightClickCancel();
                                }
                            }

                            // Left-click tap handler - dismisses autocomplete popup on clicking another line
                            TapHandler {
                                acceptedButtons: Qt.LeftButton
                                onTapped: {
                                    suggestionModel.clear();
                                }
                            }

                            onCursorPositionChanged: {
                                root.updateCursorPosition();
                                if (suggestionModel.count > 0 && !autocompleteTimer.running) {
                                    suggestionModel.clear();
                                }
                            }

                            onTextChanged: {
                                root.handleEditorContentChanged();
                            }

                            Keys.onPressed: function(event) {
                                // 0. Multi-Cursor Next Occurrence: Ctrl+D
                                if ((event.modifiers & Qt.ControlModifier) && (event.key === Qt.Key_D)) {
                                    root.addNextOccurrenceCursor();
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

                                // 4. Auto Bracket Matching & Closing
                                if (theme && theme.enableBracketMatching) {
                                    var pos = codeTextArea.cursorPosition;
                                    var charMap = {
                                        "(": ")",
                                        "[": "]",
                                        "{": "}",
                                        "\"": "\"",
                                        "'": "'"
                                    };

                                    if (charMap[event.text]) {
                                        codeTextArea.insert(pos, event.text + charMap[event.text]);
                                        codeTextArea.cursorPosition = pos + 1;
                                        event.accepted = true;
                                        return;
                                    }
                                }

                                // 4.1 HTML / XML Auto Close Tag on '>'
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

                                // 5. Auto Indentation on Enter
                                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                    var curPos = codeTextArea.cursorPosition;
                                    var docText = codeTextArea.text;
                                    var lineStart = docText.lastIndexOf("\n", curPos - 1) + 1;
                                    var currentLineContent = docText.substring(lineStart, curPos);

                                    var match = currentLineContent.match(/^(\s*)/);
                                    var indent = match ? match[1] : "";

                                    var trimmed = currentLineContent.trim();
                                    if (trimmed.endsWith(":") || trimmed.endsWith("{") || trimmed.endsWith("(") || trimmed.endsWith("[")) {
                                        indent += "    ";
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

                            if (useRadial) {
                                isHolding = true;
                                radialContextMenu.x = Math.max(10, Math.min(textAreaContainer.width - radialContextMenu.width - 10, posX - (radialContextMenu.width / 2)));
                                radialContextMenu.y = Math.max(10, Math.min(textAreaContainer.height - radialContextMenu.height - 10, posY - (radialContextMenu.height / 2)));
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
                            text: "Run File\tF5"
                            onTriggered: root.requestRunFile()
                        }
                        MenuSeparator {
                            contentItem: Rectangle {
                                implicitHeight: 1
                                color: theme ? theme.borderSubtle : "#282828"
                            }
                        }
                        Action {
                            text: "Cut\tCtrl+X"
                            onTriggered: codeTextArea.cut()
                        }
                        Action {
                            text: "Copy\tCtrl+C"
                            onTriggered: codeTextArea.copy()
                        }
                        Action {
                            text: "Paste\tCtrl+V"
                            onTriggered: codeTextArea.paste()
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
                            var r = codeTextArea.cursorRectangle;
                            return codeTextArea.mapToItem(textAreaContainer, r.x, r.y + r.height + 2);
                        }

                        x: Math.min(textAreaContainer.width - width - 10, Math.max(10, cursorPt.x))
                        y: (cursorPt.y + height > textAreaContainer.height - 10) ? Math.max(10, cursorPt.y - height - codeTextArea.cursorRectangle.height - 4) : Math.max(10, cursorPt.y)

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
                            codeTextArea.forceActiveFocus();
                        }
                    }

                    // Floating Color Picker Popup
                    ColorPickerPopup {
                        id: colorPickerPopup
                        visible: false
                        z: 120
                        onColorChosen: function(hex) {
                            if (colorPickerPopup.targetStart >= 0 && colorPickerPopup.targetEnd > colorPickerPopup.targetStart) {
                                codeTextArea.remove(colorPickerPopup.targetStart, colorPickerPopup.targetEnd);
                                codeTextArea.insert(colorPickerPopup.targetStart, hex);
                                colorPickerPopup.targetEnd = colorPickerPopup.targetStart + hex.length;
                            }
                        }
                        onCloseRequested: {
                            colorPickerPopup.visible = false;
                            codeTextArea.forceActiveFocus();
                        }
                    }
                }

                // Minimap on right edge
                CodeMinimap {
                    id: codeMinimap
                    Layout.fillHeight: true
                    visible: theme ? theme.enableMinimap : true
                    documentText: codeTextArea.text
                    visibleRatio: editorFlickable.height / Math.max(1, editorFlickable.contentHeight)
                    scrollRatio: editorFlickable.contentY / Math.max(1, (editorFlickable.contentHeight - editorFlickable.height))

                    onScrollRequested: function(ratio) {
                        editorFlickable.contentY = ratio * Math.max(0, editorFlickable.contentHeight - editorFlickable.height);
                    }
                }
            }
        }

        // 2. Whiteboard Canvas Tab View (Embedded as a full tab)
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

        // 3. Web & Markdown Live Preview Tab View
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
    }

    Timer {
        id: autocompleteTimer
        interval: 100
        repeat: false
        onTriggered: {
            root.triggerCompletionRequest();
        }
    }

    function executeEditorAction(actionId) {
        if (actionId === "format") {
            root.formatDocument();
        } else if (actionId === "run") {
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
    // ACCURATE MULTI-LANGUAGE CODE FORMATTER
    // =========================================================================
    function formatDocument() {
        var text = codeTextArea.text;
        if (!text || text.trim().length === 0) return;

        var lang = root.currentLanguageId;
        var ext = root.activeFileName ? root.activeFileName.split(".").pop().toLowerCase() : "";
        var tabSize = theme ? theme.tabSize : 4;
        var tabSpaces = " ".repeat(tabSize);

        // 1. JSON Formatter
        if (lang === "json" || ext === "json") {
            try {
                var parsed = JSON.parse(text);
                codeTextArea.text = JSON.stringify(parsed, null, tabSize);
                return;
            } catch (e) {}
        }

        // 2. Python Formatter
        if (lang === "python" || ext === "py" || ext === "pyw") {
            var pyLines = text.split("\n");
            var pyIndent = 0;
            var formattedPy = [];

            for (var p = 0; p < pyLines.length; p++) {
                var pLine = pyLines[p].trim();
                if (pLine.length === 0) {
                    formattedPy.push("");
                    continue;
                }

                if (/^(elif |else:|except(\s.*)?:|finally:)/.test(pLine)) {
                    pyIndent = Math.max(0, pyIndent - 1);
                } else if (/^(\]|\}|\))/.test(pLine)) {
                    pyIndent = Math.max(0, pyIndent - 1);
                }

                formattedPy.push(tabSpaces.repeat(pyIndent) + pLine);

                if (pLine.endsWith(":") || pLine.endsWith("(") || pLine.endsWith("[") || pLine.endsWith("{")) {
                    pyIndent++;
                }
            }
            codeTextArea.text = formattedPy.join("\n");
            return;
        }

        // 3. HTML / XML / SVG Formatter
        if (lang === "html" || lang === "xml" || ext === "html" || ext === "htm" || ext === "xml" || ext === "svg") {
            var htmlLines = text.split("\n");
            var htmlIndent = 0;
            var formattedHtml = [];

            for (var h = 0; h < htmlLines.length; h++) {
                var hLine = htmlLines[h].trim();
                if (hLine.length === 0) {
                    formattedHtml.push("");
                    continue;
                }

                var isClosing = /^<\/[^>]+>/.test(hLine);
                if (isClosing) {
                    htmlIndent = Math.max(0, htmlIndent - 1);
                }

                formattedHtml.push(tabSpaces.repeat(htmlIndent) + hLine);

                var isOpening = /^<[a-zA-Z0-9_-]+(\s[^>]*)?>/.test(hLine) && !hLine.endsWith("/>") && !/^(<area|<base|<br|<col|<embed|<hr|<img|<input|<link|<meta|<param|<source|<track|<wbr)/i.test(hLine);
                if (isOpening && !isClosing && !hLine.includes("</")) {
                    htmlIndent++;
                }
            }
            codeTextArea.text = formattedHtml.join("\n");
            return;
        }

        // 4. JS / TS / C / C++ / C# / Java / Rust / Go / CSS / QML Formatter
        var lines = text.split("\n");
        var indentLevel = 0;
        var formattedLines = [];

        for (var i = 0; i < lines.length; i++) {
            var rawLine = lines[i].trim();

            if (rawLine.length === 0) {
                formattedLines.push("");
                continue;
            }

            // Strip strings and comments for clean token parsing
            var cleanLine = rawLine.replace(/"(\\.|[^"\\])*"/g, '""').replace(/'(\\.|[^'\\])*'/g, "''").replace(/\/\/.*$/, "");

            // Check if current line starts with a closing structure or branch keyword
            var unindentAtStart = /^(\}|\]|\)|else\b|catch\b|finally\b|case\b|default:)/.test(cleanLine);
            if (unindentAtStart) {
                indentLevel = Math.max(0, indentLevel - 1);
            }

            var currentIndent = tabSpaces.repeat(indentLevel);
            formattedLines.push(currentIndent + rawLine);

            // Compute open and close braces on this line
            var opens = (cleanLine.match(/[\{\[\(]/g) || []).length;
            var closes = (cleanLine.match(/[\}\]\)]/g) || []).length;

            if (unindentAtStart) {
                closes = Math.max(0, closes - 1);
            }

            indentLevel = Math.max(0, indentLevel + (opens - closes));
        }

        codeTextArea.text = formattedLines.join("\n");
    }

    function indentSelectedText() {
        var tabSpaces = "    ";
        if (theme && theme.tabSize) {
            tabSpaces = " ".repeat(theme.tabSize);
        }
        var fullText = codeTextArea.text;
        var start = codeTextArea.selectionStart;
        var end = codeTextArea.selectionEnd;

        if (start === end) {
            // No multi-char selection: insert tab spaces at cursor
            var cur = codeTextArea.cursorPosition;
            codeTextArea.insert(cur, tabSpaces);
            codeTextArea.cursorPosition = cur + tabSpaces.length;
            return;
        }

        // Multi-line / selected text indentation
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
    }

    function unindentSelectedText() {
        var tabSize = (theme && theme.tabSize) ? theme.tabSize : 4;
        var fullText = codeTextArea.text;
        var start = codeTextArea.selectionStart;
        var end = codeTextArea.selectionEnd;

        if (start === end) {
            // No selection: unindent current line before cursor
            var cur = codeTextArea.cursorPosition;
            var lineStart = fullText.lastIndexOf("\n", cur - 1) + 1;
            var lineContent = fullText.substring(lineStart, cur);
            var match = lineContent.match(/ {1,4}$/);
            if (match) {
                var removeCount = match[0].length;
                codeTextArea.remove(cur - removeCount, cur);
                codeTextArea.cursorPosition = cur - removeCount;
            }
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

    function updateCursorPosition() {
        var pos = codeTextArea.cursorPosition;
        var text = codeTextArea.text;
        var lines = text.substring(0, pos).split("\n");
        root.cursorLine = Math.max(1, lines.length);
        root.cursorColumn = Math.max(1, lines[lines.length - 1].length + 1);
        root.totalLineCount = Math.max(1, text.split("\n").length);
        root.cursorPositionChanged(root.cursorLine, root.cursorColumn);
    }

    function handleEditorContentChanged() {
        if (root.currentTab) {
            root.currentTab.content = codeTextArea.text;
            if (!root.currentTab.isDirty) {
                root.currentTab.isDirty = true;
            }
        }
        root.totalLineCount = Math.max(1, codeTextArea.text.split("\n").length);
        root.activeFileChanged(root.activeFilePath, root.activeFileName, root.currentLanguage, root.isCurrentFileDirty);

        // Real-time live update for Web / Markdown preview tab
        for (var t = 0; t < tabModel.count; t++) {
            var tab = tabModel.get(t);
            if (tab && (tab.isWebPreview || tab.languageId === "webpreview")) {
                tabModel.setProperty(t, "content", codeTextArea.text);
            }
        }

        if (typeof backend !== "undefined" && backend && backend.notify_change) {
            backend.notify_change(root.activeFilePath || "untitled.txt", codeTextArea.text);
        }
    }

    function createNewFile() {
        var newNum = tabModel.count + 1;
        var title = "Untitled-" + newNum;

        tabModel.append({
            fileId: "tab_" + Date.now() + "_" + newNum,
            title: title,
            path: "",
            content: "",
            isDirty: true,
            languageName: "Plain Text",
            languageId: "text",
            cursorPos: 0
        });

        switchToTab(tabModel.count - 1);
    }

    function loadFile(path, content) {
        for (var i = 0; i < tabModel.count; i++) {
            if (tabModel.get(i).path === path) {
                tabModel.setProperty(i, "content", content);
                tabModel.setProperty(i, "isDirty", false);
                switchToTab(i);
                return;
            }
        }

        var fileName = path.split("/").pop().split("\\").pop();
        var langObj = LanguageRegistry.detectLanguage(fileName);

        tabModel.append({
            fileId: "file_" + Date.now(),
            title: fileName,
            path: path,
            content: content,
            isDirty: false,
            languageName: langObj.name,
            languageId: langObj.id,
            cursorPos: 0
        });

        switchToTab(tabModel.count - 1);
    }

    function openWhiteboardTab() {
        for (var i = 0; i < tabModel.count; i++) {
            if (tabModel.get(i).isWhiteboard) {
                switchToTab(i);
                return;
            }
        }

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

        switchToTab(tabModel.count - 1);
    }

    function openWebPreviewTab() {
        var currentContent = codeTextArea.text || "";
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

        switchToTab(tabModel.count - 1);
    }

    function switchToTab(index) {
        if (index < 0 || index >= tabModel.count) return;

        autocompleteTimer.stop();
        suggestionModel.clear();

        if (root.currentTab && !root.currentTab.isWhiteboard && !root.currentTab.isWebPreview) {
            root.currentTab.content = codeTextArea.text;
            root.currentTab.cursorPos = codeTextArea.cursorPosition;
        }

        root.activeTabIndex = index;
        var newTab = tabModel.get(index);

        if (!newTab.isWhiteboard && !newTab.isWebPreview) {
            codeTextArea.text = newTab.content || "";
            codeTextArea.cursorPosition = Math.min(newTab.cursorPos || 0, codeTextArea.text.length);

            if (typeof backend !== "undefined" && backend && backend.register_text_area) {
                backend.register_text_area(codeTextArea);
            }
        }

        root.currentLanguage = newTab.languageName || "Plain Text";
        root.currentLanguageId = newTab.languageId || "text";

        updateCursorPosition();
        root.activeFileChanged(newTab.path || "", newTab.title || "", root.currentLanguage, newTab.isDirty || false);
    }

    function closeTab(index) {
        if (index < 0 || index >= tabModel.count) return;

        tabModel.remove(index);
        if (tabModel.count === 0) {
            root.activeTabIndex = -1;
            root.activeFileChanged("", "", "Plain Text", false);
        } else {
            switchToTab(Math.min(index, tabModel.count - 1));
        }
    }

    function saveCurrentFile() {
        if (!root.currentTab) return false;

        if (!root.currentTab.path) {
            return false;
        }

        if (typeof backend !== "undefined" && backend) {
            backend.save_file(root.currentTab.path, codeTextArea.text);
            root.currentTab.isDirty = false;
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
            root.currentTab.isDirty = false;
            root.currentLanguage = langObj.name;
            root.currentLanguageId = langObj.id;
        }

        if (typeof backend !== "undefined" && backend) {
            backend.save_file(cleanPath, codeTextArea.text);
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
        findReplaceBar.visible = true;
    }

    function findNext(pattern, matchCase) {
        if (!pattern) return;
        var text = codeTextArea.text;
        var startPos = codeTextArea.cursorPosition;
        var idx = matchCase ? text.indexOf(pattern, startPos) : text.toLowerCase().indexOf(pattern.toLowerCase(), startPos);

        if (idx === -1) {
            idx = matchCase ? text.indexOf(pattern, 0) : text.toLowerCase().indexOf(pattern.toLowerCase(), 0);
        }

        if (idx !== -1) {
            codeTextArea.select(idx, idx + pattern.length);
        }
    }

    function findPrev(pattern, matchCase) {
        if (!pattern) return;
        var text = codeTextArea.text;
        var startPos = Math.max(0, codeTextArea.selectionStart - 1);
        var sub = text.substring(0, startPos);
        var idx = matchCase ? sub.lastIndexOf(pattern) : sub.toLowerCase().lastIndexOf(pattern.toLowerCase());

        if (idx === -1) {
            idx = matchCase ? text.lastIndexOf(pattern) : text.toLowerCase().lastIndexOf(pattern.toLowerCase());
        }

        if (idx !== -1) {
            codeTextArea.select(idx, idx + pattern.length);
        }
    }

    function replaceNext(pattern, replacement, matchCase) {
        if (!pattern) return;
        if (codeTextArea.selectedText && (matchCase ? codeTextArea.selectedText === pattern : codeTextArea.selectedText.toLowerCase() === pattern.toLowerCase())) {
            var start = codeTextArea.selectionStart;
            codeTextArea.remove(start, codeTextArea.selectionEnd);
            codeTextArea.insert(start, replacement);
            codeTextArea.select(start, start + replacement.length);
        }
        findNext(pattern, matchCase);
    }

    function replaceAll(pattern, replacement, matchCase) {
        if (!pattern) return;
        var text = codeTextArea.text;
        var regex = new RegExp(escapeRegExp(pattern), matchCase ? "g" : "gi");
        codeTextArea.text = text.replace(regex, replacement);
    }

    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // =========================================================================
    // INTELLIGENT LANGUAGE-AWARE AUTOCOMPLETE
    // =========================================================================
    function triggerCompletionRequest() {
        var pos = codeTextArea.cursorPosition;
        var text = codeTextArea.text;
        if (!text || pos <= 0) {
            suggestionModel.clear();
            return;
        }

        // Find prefix word before cursor
        var prefixStart = pos;
        while (prefixStart > 0 && /[a-zA-Z0-9_]/.test(text[prefixStart - 1])) {
            prefixStart--;
        }
        var prefix = text.substring(prefixStart, pos);

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

        // 2. Match Document Symbols / Identifiers
        var docWords = text.match(/[a-zA-Z_][a-zA-Z0-9_]{2,}/g) || [];
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

        // Query Backend LSP if available
        if (typeof backend !== "undefined" && backend && backend.request_completion) {
            backend.request_completion(root.activeFilePath || "untitled.txt", root.cursorLine - 1, root.cursorColumn - 1, text);
        }
    }

    function showCompletions(suggestions) {
        if (!suggestions || suggestions.length === 0) return;
        var pos = codeTextArea.cursorPosition;
        var text = codeTextArea.text;
        if (!text || pos <= 0) return;

        var prefixStart = pos;
        while (prefixStart > 0 && /[a-zA-Z0-9_]/.test(text[prefixStart - 1])) {
            prefixStart--;
        }
        var prefix = text.substring(prefixStart, pos);
        if (!prefix || prefix.length < 1) return;
        var prefixLower = prefix.toLowerCase();

        for (var i = 0; i < suggestions.length; i++) {
            var label = suggestions[i].label || suggestions[i];
            var ins = suggestions[i].insertText || label;

            // ONLY append if suggestion actually starts with what the user is typing!
            if (label.toLowerCase().startsWith(prefixLower) && label !== prefix) {
                var exists = false;
                for (var m = 0; m < suggestionModel.count; m++) {
                    if (suggestionModel.get(m).label === label) {
                        exists = true;
                        break;
                    }
                }
                if (!exists) {
                    suggestionModel.append({ label: label, insertText: ins, kind: suggestions[i].type || "lsp" });
                }
            }
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
