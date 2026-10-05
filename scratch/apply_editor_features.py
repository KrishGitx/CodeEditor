import re

editor_path = "qml/components/EditorArea.qml"
with open(editor_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add properties and shortcuts near top
props_to_add = '''    property bool copiedWholeLine: false
    property string clipboardWholeLineText: ""
    property var activeSnippetStops: []
    property int activeSnippetStopIndex: -1
    property int bracketMatchPos1: -1
    property int bracketMatchPos2: -1
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
'''

if "property bool copiedWholeLine:" not in content:
    # Insert after 'property var extraCursors:'
    content = content.replace(
        "property var extraCursors: [] // Array of character indices for Multi-Cursor editing",
        "property var extraCursors: [] // Array of character indices for Multi-Cursor editing\n" + props_to_add
    )

# 2. Add BreadcrumbsBar above the editor surface in primaryEditorContainer
breadcrumbs_code = '''                        // Breadcrumbs Hierarchy & Symbol Bar
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
'''

if "BreadcrumbsBar {" not in content:
    # Anchor the inner RowLayout or container below breadcrumbsBar
    content = content.replace(
        '''                        Rectangle {
                            anchors.fill: parent
                            color: theme ? theme.bgEditor : "#1e1e1e"
                        }

                        RowLayout {
                            anchors.fill: parent
                            spacing: 0''',
        '''                        Rectangle {
                            anchors.fill: parent
                            color: theme ? theme.bgEditor : "#1e1e1e"
                        }

''' + breadcrumbs_code + '''
                        RowLayout {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.top: breadcrumbsBar.bottom
                            spacing: 0'''
    )

# 3. Add bracket matching overlay and selection occurrence overlay in tabPane
overlays_code = '''                                                         // Selection Occurrences Highlight Overlays
                                                         Repeater {
                                                             model: (tabPane.index === root.activeTabIndex) ? root.selectionOccurrences : []
                                                             delegate: Rectangle {
                                                                 property var occRect: codeTextArea.positionToRectangle(modelData.start)
                                                                 property var occEndRect: codeTextArea.positionToRectangle(modelData.end)
                                                                 x: occRect.x
                                                                 y: occRect.y
                                                                 width: Math.max(8, occEndRect.x - occRect.x)
                                                                 height: occRect.height > 0 ? occRect.height : root.editorLineHeight
                                                                 color: theme ? theme.selectionHighlight : "#264f78"
                                                                 opacity: 0.35
                                                                 border.color: theme ? theme.borderGlow : "#60a5fa"
                                                                 border.width: 1
                                                                 radius: 2
                                                                 z: 5
                                                             }
                                                         }

                                                         // Bracket Matching Highlight Overlays
                                                         Rectangle {
                                                             property var b1Rect: (root.bracketMatchPos1 >= 0 && tabPane.index === root.activeTabIndex) ? codeTextArea.positionToRectangle(root.bracketMatchPos1) : null
                                                             visible: b1Rect !== null && root.bracketMatchPos1 >= 0 && tabPane.index === root.activeTabIndex
                                                             x: b1Rect ? b1Rect.x : 0
                                                             y: b1Rect ? b1Rect.y : 0
                                                             width: root.charWidth
                                                             height: b1Rect && b1Rect.height > 0 ? b1Rect.height : root.editorLineHeight
                                                             color: "transparent"
                                                             border.color: theme ? theme.accent : "#38bdf8"
                                                             border.width: 1.5
                                                             radius: 2
                                                             z: 14
                                                         }

                                                         Rectangle {
                                                             property var b2Rect: (root.bracketMatchPos2 >= 0 && tabPane.index === root.activeTabIndex) ? codeTextArea.positionToRectangle(root.bracketMatchPos2) : null
                                                             visible: b2Rect !== null && root.bracketMatchPos2 >= 0 && tabPane.index === root.activeTabIndex
                                                             x: b2Rect ? b2Rect.x : 0
                                                             y: b2Rect ? b2Rect.y : 0
                                                             width: root.charWidth
                                                             height: b2Rect && b2Rect.height > 0 ? b2Rect.height : root.editorLineHeight
                                                             color: "transparent"
                                                             border.color: theme ? theme.accent : "#38bdf8"
                                                             border.width: 1.5
                                                             radius: 2
                                                             z: 14
                                                         }
'''

if "Selection Occurrences Highlight Overlays" not in content:
    content = content.replace(
        "// Multi-Cursor Caret Overlays",
        overlays_code + "\n                                                         // Multi-Cursor Caret Overlays"
    )

# 4. Add hover detection and mouse tracker on codeTextArea
hover_handler_code = '''                                                        // Hover Information & Mouse tracking
                                                        HoverHandler {
                                                            id: textHoverHandler
                                                            onHoveredChanged: {
                                                                if (!hovered) {
                                                                    hoverHideTimer.start();
                                                                }
                                                            }
                                                            onPointChanged: {
                                                                if (hovered && tabPane.index === root.activeTabIndex) {
                                                                    root.lastHoverPoint = point.position;
                                                                    hoverDebounceTimer.restart();
                                                                }
                                                            }
                                                        }
'''

if "textHoverHandler" not in content:
    content = content.replace(
        "// Alt+Click Multi-Cursor TapHandler (does not block mouse selection)",
        hover_handler_code + "\n                                                         // Alt+Click Multi-Cursor TapHandler (does not block mouse selection)"
    )

# 5. Add Whole-Line Copy/Paste, Snippet Navigation, and F2 Rename inside Keys.onPressed
key_actions_code = '''                                                            // Whole-line copy / paste behavior
                                                            if ((event.modifiers & Qt.ControlModifier) && (event.key === Qt.Key_C)) {
                                                                var sStart = codeTextArea.selectionStart;
                                                                var sEnd = codeTextArea.selectionEnd;
                                                                if (sStart === undefined || sEnd === undefined || sStart === sEnd) {
                                                                    var docT = codeTextArea.text;
                                                                    var cPos = codeTextArea.cursorPosition;
                                                                    var lStart = docT.lastIndexOf("\\n", cPos - 1) + 1;
                                                                    var lEnd = docT.indexOf("\\n", cPos);
                                                                    if (lEnd === -1) lEnd = docT.length;
                                                                    var lineCopy = docT.substring(lStart, lEnd) + "\\n";
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
                                                                    var lineSt = dText.lastIndexOf("\\n", curP - 1) + 1;
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
'''

if "Whole-line copy / paste behavior" not in content:
    content = content.replace(
        "Keys.onPressed: function(event) {",
        "Keys.onPressed: function(event) {\n" + key_actions_code
    )

# 6. Add Helper functions and Overlays at the end of EditorArea.qml
end_additions = '''
    // =========================================================================
    // VS CODE ADVANCED NAVIGATION, HOVER, RENAME & QUICK OPEN OVERLAYS
    // =========================================================================
    property var lastHoverPoint: Qt.point(0, 0)

    Timer {
        id: hoverDebounceTimer
        interval: 350
        repeat: false
        onTriggered: {
            if (!codeTextArea) return;
            var pos = codeTextArea.positionAt(root.lastHoverPoint.x, root.lastHoverPoint.y);
            if (pos < 0 || pos >= codeTextArea.text.length) return;
            var r = codeTextArea.positionToRectangle(pos);
            var mapped = codeTextArea.mapToItem(root, r.x, r.y);

            // Compute line and col for hover
            var doc = codeTextArea.text;
            var lineStart = doc.lastIndexOf("\\n", pos - 1) + 1;
            var lineNum = doc.substring(0, pos).split("\\n").length;
            var colNum = pos - lineStart;

            if (typeof backend !== "undefined" && backend && backend.get_hover_info) {
                var info = backend.get_hover_info(root.activeFilePath, lineNum, colNum, doc);
                if (info && info.found) {
                    hoverTooltip.showAt(mapped.x, mapped.y, info.title, info.doc, info.kind);
                }
            }
        }
    }

    Timer {
        id: hoverHideTimer
        interval: 150
        repeat: false
        onTriggered: hoverTooltip.hide()
    }

    HoverTooltip {
        id: hoverTooltip
    }

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
        onFileSelected: function(filePath) {
            if (typeof backend !== "undefined" && backend && backend.open_file) {
                backend.open_file(filePath);
            }
        }
        onLineSelected: function(lineNum) {
            root.jumpToLine(lineNum);
        }
    }

    function jumpToLine(targetLine, targetCol) {
        if (!codeTextArea) return;
        var lines = codeTextArea.text.split("\\n");
        var line = Math.max(1, Math.min(targetLine, lines.length));
        var col = targetCol !== undefined ? Math.max(1, targetCol) : 1;
        var charPos = 0;
        for (var l = 0; l < line - 1; l++) {
            charPos += lines[l].length + 1;
        }
        charPos += Math.min(col - 1, lines[line - 1].length);
        codeTextArea.cursorPosition = charPos;
        codeTextArea.forceActiveFocus();
        if (editorFlickable) {
            var targetY = (line - 1) * root.editorLineHeight;
            editorFlickable.contentY = Math.max(0, targetY - (editorFlickable.height / 2));
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

    function updateBracketMatching() {
        if (!codeTextArea) {
            root.bracketMatchPos1 = -1;
            root.bracketMatchPos2 = -1;
            return;
        }
        var pos = codeTextArea.cursorPosition;
        var text = codeTextArea.text;
        var pairs = {
            "(": { partner: ")", dir: 1 },
            ")": { partner: "(", dir: -1 },
            "{": { partner: "}", dir: 1 },
            "}": { partner: "{", dir: -1 },
            "[": { partner: "]", dir: 1 },
            "]": { partner: "[", dir: -1 }
        };

        var checkIndices = [pos - 1, pos];
        var foundPos = -1;
        var partnerPos = -1;

        for (var ci = 0; ci < checkIndices.length; ci++) {
            var idx = checkIndices[ci];
            if (idx >= 0 && idx < text.length) {
                var ch = text.charAt(idx);
                if (pairs[ch]) {
                    var rule = pairs[ch];
                    var depth = 1;
                    var scan = idx + rule.dir;
                    while (scan >= 0 && scan < text.length) {
                        var scChar = text.charAt(scan);
                        if (scChar === ch) depth++;
                        else if (scChar === rule.partner) {
                            depth--;
                            if (depth === 0) {
                                foundPos = idx;
                                partnerPos = scan;
                                break;
                            }
                        }
                        scan += rule.dir;
                    }
                    if (foundPos !== -1) break;
                }
            }
        }

        root.bracketMatchPos1 = foundPos;
        root.bracketMatchPos2 = partnerPos;
    }

    function updateSelectionOccurrences() {
        if (!codeTextArea) {
            root.selectionOccurrences = [];
            return;
        }
        var sel = codeTextArea.selectedText;
        if (!sel || sel.trim().length < 2 || sel.indexOf("\\n") !== -1) {
            root.selectionOccurrences = [];
            return;
        }
        var doc = codeTextArea.text;
        var selStart = codeTextArea.selectionStart;
        var selEnd = codeTextArea.selectionEnd;
        var occs = [];
        var idx = 0;
        var maxOcc = 100;
        while ((idx = doc.indexOf(sel, idx)) !== -1) {
            if (idx !== selStart) {
                occs.push({ start: idx, end: idx + sel.length });
                if (occs.length >= maxOcc) break;
            }
            idx += sel.length;
        }
        root.selectionOccurrences = occs;
    }

    // Connect selection and cursor updates
    onCursorPositionChanged: {
        root.updateBracketMatching();
        root.updateSelectionOccurrences();
        if (breadcrumbsBar && typeof breadcrumbsBar.updateActiveSymbolForLine === "function") {
            breadcrumbsBar.updateActiveSymbolForLine(root.cursorLine);
        }
        root.saveWorkspaceSession();
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

    Component.onCompleted: {
        root.restoreWorkspaceSession();
    }
'''

if "QuickOpenPalette {" not in content:
    content = content[:-1] + end_additions + "\n}\n"

with open(editor_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully applied advanced VS Code features to EditorArea.qml")
