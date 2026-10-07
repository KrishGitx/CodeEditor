import re

with open('qml/components/EditorArea.qml', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add isSyncingSecondary property
if 'property bool isSyncingSecondary: false' not in content:
    content = content.replace(
        'property bool isFormatting: false',
        'property bool isSyncingSecondary: false\n    property bool isFormatting: false',
        1
    )

# 2. Update toggleExtraCursor and addNextOccurrenceCursor functions
old_mc_funcs = """    function toggleExtraCursor(charPos) {
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
    }"""

new_mc_funcs = """    function toggleExtraCursor(charPos) {
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
        } else {
            arr.push({ start: charPos, end: charPos, cursor: charPos });
        }
        root.extraCursors = arr;
    }

    function addNextOccurrenceCursor() {
        if (!codeTextArea) return;
        var text = codeTextArea.text;
        var sStart = codeTextArea.selectionStart;
        var sEnd = codeTextArea.selectionEnd;
        var curPos = codeTextArea.cursorPosition;
        var selText = (sStart !== undefined && sEnd !== undefined && sStart !== sEnd) ? text.substring(Math.min(sStart, sEnd), Math.max(sStart, sEnd)) : "";

        if (!selText || selText.length === 0) {
            var wordStart = curPos;
            while (wordStart > 0 && /[a-zA-Z0-9_]/.test(text[wordStart - 1])) wordStart--;
            var wordEnd = curPos;
            while (wordEnd < text.length && /[a-zA-Z0-9_]/.test(text[wordEnd])) wordEnd++;
            if (wordEnd > wordStart) {
                codeTextArea.select(wordStart, wordEnd);
                selText = text.substring(wordStart, wordEnd);
                root.extraCursors = [{ start: wordStart, end: wordEnd, cursor: wordEnd }];
                return;
            } else {
                return;
            }
        }

        var arr = root.extraCursors.slice();
        if (arr.length === 0) {
            arr.push({ start: Math.min(sStart, sEnd), end: Math.max(sStart, sEnd), cursor: Math.max(sStart, sEnd) });
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
                root.extraCursors = arr;
                var lastItem = arr[arr.length - 1];
                codeTextArea.select(lastItem.start, lastItem.end);
                codeTextArea.cursorPosition = lastItem.cursor;
            }
        }
    }"""

assert old_mc_funcs in content, "old_mc_funcs not found"
content = content.replace(old_mc_funcs, new_mc_funcs, 1)

# 3. Update Multi-Cursor Caret and Selection Overlays in tabPane delegate
old_mc_overlays = """                                                         // Multi-Cursor Caret Overlays
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
                                                        }"""

new_mc_overlays = """                                                         // Multi-Cursor Extra Selection Highlights
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
                                                        }"""

assert old_mc_overlays in content, "old_mc_overlays not found"
content = content.replace(old_mc_overlays, new_mc_overlays, 1)

# 4. Update multi-cursor key handlers (typing, backspace, delete, enter, copy, paste)
old_mc_keys = """                                                            // 0.4 Multi-Cursor Typing, Backspacing, Deleting & Enter
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
                                                                } else if (event.key === Qt.Key_Delete) {
                                                                    var allDelPos = root.extraCursors.concat([codeTextArea.cursorPosition]);
                                                                    allDelPos.sort(function(a, b) { return b - a; });
                                                                    allDelPos = allDelPos.filter(function(item, pos, self) { return self.indexOf(item) === pos; });

                                                                    var delDoc = codeTextArea.text;
                                                                    for (var di = 0; di < allDelPos.length; di++) {
                                                                        var dp = allDelPos[di];
                                                                        if (dp < delDoc.length) {
                                                                            delDoc = delDoc.substring(0, dp) + delDoc.substring(dp + 1);
                                                                        }
                                                                    }

                                                                    var sortedDelAsc = allDelPos.slice().sort(function(a, b) { return a - b; });
                                                                    var finalDelExtras = [];
                                                                    var mainDelPos = codeTextArea.cursorPosition;
                                                                    for (var sDel = 0; sDel < sortedDelAsc.length; sDel++) {
                                                                        var oDelP = sortedDelAsc[sDel];
                                                                        var sDelP = Math.max(0, oDelP - sDel);
                                                                        if (oDelP === codeTextArea.cursorPosition) {
                                                                            mainDelPos = sDelP;
                                                                        } else {
                                                                            finalDelExtras.push(sDelP);
                                                                        }
                                                                    }
                                                                    codeTextArea.text = delDoc;
                                                                    codeTextArea.cursorPosition = mainDelPos;
                                                                    root.extraCursors = finalDelExtras;
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                                                    var allEnt = root.extraCursors.concat([codeTextArea.cursorPosition]);
                                                                    allEnt.sort(function(a, b) { return b - a; });
                                                                    allEnt = allEnt.filter(function(item, pos, self) { return self.indexOf(item) === pos; });

                                                                    var entDoc = codeTextArea.text;
                                                                    for (var ei = 0; ei < allEnt.length; ei++) {
                                                                        var ep = allEnt[ei];
                                                                        entDoc = entDoc.substring(0, ep) + "\\n" + entDoc.substring(ep);
                                                                    }

                                                                    var sortedEntAsc = allEnt.slice().sort(function(a, b) { return a - b; });
                                                                    var finalEntExtras = [];
                                                                    var mainEntPos = codeTextArea.cursorPosition;
                                                                    for (var se = 0; se < sortedEntAsc.length; se++) {
                                                                        var oeP = sortedEntAsc[se];
                                                                        var seP = oeP + se + 1;
                                                                        if (oeP === codeTextArea.cursorPosition) {
                                                                            mainEntPos = seP;
                                                                        } else {
                                                                            finalEntExtras.push(seP);
                                                                        }
                                                                    }
                                                                    codeTextArea.text = entDoc;
                                                                    codeTextArea.cursorPosition = mainEntPos;
                                                                    root.extraCursors = finalEntExtras;
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.text && event.text.length === 1 && !(event.modifiers & Qt.ControlModifier) && !(event.modifiers & Qt.AltModifier) && event.key !== Qt.Key_Tab) {
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
                                                            }"""

new_mc_keys = """                                                            // 0.4 Multi-Cursor Copy & Paste Handling
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
                                                                        backend.set_clipboard_text(selPieces.join("\\n"));
                                                                        event.accepted = true;
                                                                        return;
                                                                    }
                                                                }
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
                                                                    // Ensure list is unique by start/end
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

                                                                if (event.key === Qt.Key_Backspace) {
                                                                    var cursors = getNormalizedCursors();
                                                                    cursors.sort(function(a, b) { return Math.max(b.start, b.end) - Math.max(a.start, a.end); });
                                                                    var docStr = codeTextArea.text;
                                                                    var newCursors = [];

                                                                    for (var bi = 0; bi < cursors.length; bi++) {
                                                                        var cur = cursors[bi];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            docStr = docStr.substring(0, minP) + docStr.substring(maxP);
                                                                            newCursors.unshift({ start: minP, end: minP, cursor: minP });
                                                                        } else if (minP > 0) {
                                                                            docStr = docStr.substring(0, minP - 1) + docStr.substring(minP);
                                                                            newCursors.unshift({ start: minP - 1, end: minP - 1, cursor: minP - 1 });
                                                                        } else {
                                                                            newCursors.unshift({ start: 0, end: 0, cursor: 0 });
                                                                        }
                                                                    }

                                                                    codeTextArea.text = docStr;
                                                                    root.extraCursors = newCursors;
                                                                    if (newCursors.length > 0) {
                                                                        codeTextArea.cursorPosition = newCursors[newCursors.length - 1].cursor;
                                                                    }
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.key === Qt.Key_Delete) {
                                                                    var cursors = getNormalizedCursors();
                                                                    cursors.sort(function(a, b) { return Math.max(b.start, b.end) - Math.max(a.start, a.end); });
                                                                    var docStr = codeTextArea.text;
                                                                    var newCursors = [];

                                                                    for (var di = 0; di < cursors.length; di++) {
                                                                        var cur = cursors[di];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            docStr = docStr.substring(0, minP) + docStr.substring(maxP);
                                                                            newCursors.unshift({ start: minP, end: minP, cursor: minP });
                                                                        } else if (minP < docStr.length) {
                                                                            docStr = docStr.substring(0, minP) + docStr.substring(minP + 1);
                                                                            newCursors.unshift({ start: minP, end: minP, cursor: minP });
                                                                        } else {
                                                                            newCursors.unshift({ start: minP, end: minP, cursor: minP });
                                                                        }
                                                                    }

                                                                    codeTextArea.text = docStr;
                                                                    root.extraCursors = newCursors;
                                                                    if (newCursors.length > 0) {
                                                                        codeTextArea.cursorPosition = newCursors[newCursors.length - 1].cursor;
                                                                    }
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                                                    var cursors = getNormalizedCursors();
                                                                    cursors.sort(function(a, b) { return Math.max(b.start, b.end) - Math.max(a.start, a.end); });
                                                                    var docStr = codeTextArea.text;
                                                                    var newCursors = [];

                                                                    for (var ei = 0; ei < cursors.length; ei++) {
                                                                        var cur = cursors[ei];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        docStr = docStr.substring(0, minP) + "\\n" + docStr.substring(maxP);
                                                                        newCursors.unshift({ start: minP + 1, end: minP + 1, cursor: minP + 1 });
                                                                    }

                                                                    codeTextArea.text = docStr;
                                                                    root.extraCursors = newCursors;
                                                                    if (newCursors.length > 0) {
                                                                        codeTextArea.cursorPosition = newCursors[newCursors.length - 1].cursor;
                                                                    }
                                                                    event.accepted = true;
                                                                    return;
                                                                } else if (event.text && event.text.length === 1 && !(event.modifiers & Qt.ControlModifier) && !(event.modifiers & Qt.AltModifier) && event.key !== Qt.Key_Tab) {
                                                                    var charTyped = event.text;
                                                                    var cursors = getNormalizedCursors();
                                                                    cursors.sort(function(a, b) { return Math.max(b.start, b.end) - Math.max(a.start, a.end); });
                                                                    var docStr = codeTextArea.text;
                                                                    var newCursors = [];

                                                                    for (var ci = 0; ci < cursors.length; ci++) {
                                                                        var cur = cursors[ci];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        docStr = docStr.substring(0, minP) + charTyped + docStr.substring(maxP);
                                                                        newCursors.unshift({ start: minP + 1, end: minP + 1, cursor: minP + 1 });
                                                                    }

                                                                    codeTextArea.text = docStr;
                                                                    root.extraCursors = newCursors;
                                                                    if (newCursors.length > 0) {
                                                                        codeTextArea.cursorPosition = newCursors[newCursors.length - 1].cursor;
                                                                    }
                                                                    event.accepted = true;
                                                                    return;
                                                                }
                                                            }"""

assert old_mc_keys in content, "old_mc_keys not found"
content = content.replace(old_mc_keys, new_mc_keys, 1)

# 5. Fix secCodeTextArea onTextChanged and syncSecondaryEditor
old_sec_changed = """                                                onTextChanged: {
                                                    if (root.secondaryTab && root.secondaryTabIndex >= 0) {
                                                        tabModel.setProperty(root.secondaryTabIndex, "content", secCodeTextArea.text);
                                                        tabModel.setProperty(root.secondaryTabIndex, "isDirty", true);
                                                        if (root.secondaryTabIndex === root.activeTabIndex && codeTextArea.text !== secCodeTextArea.text) {
                                                            codeTextArea.text = secCodeTextArea.text;
                                                        }
                                                    }
                                                }"""

new_sec_changed = """                                                onTextChanged: {
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
                                                }"""

assert old_sec_changed in content, "old_sec_changed not found"
content = content.replace(old_sec_changed, new_sec_changed, 1)

old_sync_sec = """    function syncSecondaryEditor() {
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
    }"""

new_sync_sec = """    function syncSecondaryEditor() {
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
    }"""

assert old_sync_sec in content, "old_sync_sec not found"
content = content.replace(old_sync_sec, new_sync_sec, 1)

with open('qml/components/EditorArea.qml', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched EditorArea.qml with robust Multi-Cursor and Split Editor protections.")
