with open('qml/components/EditorArea.qml', 'r', encoding='utf-8') as f:
    content = f.read()

# 2. Update selection occurrences and remove bracket matching overlay rectangles
old_occs = '''                                                         Repeater {
                                                             model: (tabPane.index === root.activeTabIndex) ? root.selectionOccurrences : []
                                                             delegate: Rectangle {
                                                                 property var occRect: codeTextArea.positionToRectangle(modelData.start)
                                                                 property var occEndRect: codeTextArea.positionToRectangle(modelData.end)
                                                                 x: occRect.x
                                                                 y: occRect.y
                                                                 width: Math.max(8, occEndRect.x - occRect.x)
                                                                 height: occRect.height > 0 ? occRect.height : root.editorLineHeight
                                                                 color: "#38bdf8"
                                                                 opacity: 0.14
                                                                 border.color: "#38bdf840"
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
                                                         }'''

new_occs = '''                                                         Repeater {
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
                                                         }'''

if old_occs in content:
    content = content.replace(old_occs, new_occs, 1)
    print("Replaced old_occs")
else:
    print("old_occs not found")

# 3. Update multi-cursor handling in Keys.onPressed
old_mc = '''                                                            // 0.4 Multi-Cursor Typing & Backspacing
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
                                                            }'''

new_mc = '''                                                            // 0.4 Multi-Cursor Typing, Backspacing, Deleting & Enter
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
                                                            }'''

if old_mc in content:
    content = content.replace(old_mc, new_mc, 1)
    print("Replaced old_mc")
else:
    print("old_mc not found")

# 4. Update auto close brackets / quotes
old_ac = '''                                                            // 4.1 Auto Bracket Matching & Closing
                                                            if (theme && theme.enableBracketMatching && !hasSelection) {
                                                                var pos = codeTextArea.cursorPosition;
                                                                var charMap = {
                                                                    "(": ")",
                                                                    "[": "]",
                                                                    "{": "}",
                                                                    "\\"": "\\"",
                                                                    "'": "'",
                                                                    "`": "`"
                                                                };

                                                                if (charMap[event.text]) {
                                                                    codeTextArea.insert(pos, event.text + charMap[event.text]);
                                                                    codeTextArea.cursorPosition = pos + 1;
                                                                    event.accepted = true;
                                                                    return;
                                                                }
                                                            }'''

new_ac = '''                                                            // 4.1 Auto Bracket & Quote Closing
                                                            if (theme && theme.autoCloseBracketsQuotes && !hasSelection) {
                                                                var pos = codeTextArea.cursorPosition;
                                                                var docT = codeTextArea.text;
                                                                var charMap = {
                                                                    "(": ")",
                                                                    "[": "]",
                                                                    "{": "}",
                                                                    "\\"": "\\"",
                                                                    "'": "'",
                                                                    "`": "`"
                                                                };
                                                                var closingChars = [")", "]", "}", "\\"", "'", "`"];

                                                                // Over-type existing closing character
                                                                if (closingChars.indexOf(event.text) !== -1 && pos < docT.length && docT.charAt(pos) === event.text) {
                                                                    codeTextArea.cursorPosition = pos + 1;
                                                                    event.accepted = true;
                                                                    return;
                                                                }

                                                                // Auto insert pair
                                                                if (charMap[event.text]) {
                                                                    var nextCh = pos < docT.length ? docT.charAt(pos) : "";
                                                                    if (!nextCh || /\\s|[)\\]};:,]/.test(nextCh)) {
                                                                        codeTextArea.insert(pos, event.text + charMap[event.text]);
                                                                        codeTextArea.cursorPosition = pos + 1;
                                                                        event.accepted = true;
                                                                        return;
                                                                    }
                                                                }
                                                            }'''

if old_ac in content:
    content = content.replace(old_ac, new_ac, 1)
    print("Replaced old_ac")
else:
    print("old_ac not found")

# 5. Update applySuggestion snippet handling
old_sugg = '''    function applySuggestion(word, kind) {
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
                insertStr = "<" + insertStr + ">\\n    \\n</" + insertStr + ">";
                targetOffset = insertStr.indexOf("\\n    ") + 5;
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
    }'''

new_sugg = '''    function applySuggestion(word, kind) {
        if (!word) return;
        var pos = codeTextArea.cursorPosition;
        var text = codeTextArea.text;
        var prefixStart = pos;
        while (prefixStart > 0 && /[a-zA-Z0-9_]/.test(text[prefixStart - 1])) {
            prefixStart--;
        }

        var lineStart = text.lastIndexOf("\\n", prefixStart - 1) + 1;
        var currentLine = text.substring(lineStart, prefixStart);
        var indentMatch = currentLine.match(/^(\\s*)/);
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
                insertStr = "<" + insertStr + ">\\n" + baseIndent + "    \\n" + baseIndent + "</" + insertStr + ">";
                targetOffset = insertStr.indexOf("\\n" + baseIndent + "    ") + (baseIndent.length + 5);
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
    }'''

if old_sugg in content:
    content = content.replace(old_sugg, new_sugg, 1)
    print("Replaced old_sugg")
else:
    print("old_sugg not found")

with open('qml/components/EditorArea.qml', 'w', encoding='utf-8') as f:
    f.write(content)
print("EditorArea.qml patch completed")
