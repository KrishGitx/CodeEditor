with open('qml/components/EditorArea.qml', 'r', encoding='utf-8') as f:
    content = f.read()

target_start = '// 0.4 Multi-Cursor Copy & Paste Handling'
target_end = '// 0.5 Ctrl+Space: Manually Trigger Autocomplete'

idx1 = content.find(target_start)
idx2 = content.find(target_end)

if idx1 != -1 and idx2 != -1:
    replacement = """// 0.4 Multi-Cursor Copy & Paste & Undo/Redo Handling
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

                                                                        var pasteLines = pasteText.split("\\n");
                                                                        var cursors = getNormalizedCursors();
                                                                        cursors.sort(function(a, b) { return Math.max(b.start, b.end) - Math.max(a.start, a.end); });
                                                                        var newCursors = [];
                                                                        var isLineMatch = (pasteLines.length === cursors.length);

                                                                        for (var pi = 0; pi < cursors.length; pi++) {
                                                                            var cur = cursors[pi];
                                                                            var minP = Math.min(cur.start, cur.end);
                                                                            var maxP = Math.max(cur.start, cur.end);
                                                                            var curPaste = isLineMatch ? pasteLines[cursors.length - 1 - pi] : pasteText;
                                                                            if (minP !== maxP) {
                                                                                codeTextArea.remove(minP, maxP);
                                                                            }
                                                                            codeTextArea.insert(minP, curPaste);
                                                                            newCursors.unshift({ start: minP + curPaste.length, end: minP + curPaste.length, cursor: minP + curPaste.length });
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
                                                                    cursors.sort(function(a, b) { return Math.max(b.start, b.end) - Math.max(a.start, a.end); });
                                                                    var newCursors = [];

                                                                    for (var bi = 0; bi < cursors.length; bi++) {
                                                                        var cur = cursors[bi];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            codeTextArea.remove(minP, maxP);
                                                                            newCursors.unshift({ start: minP, end: minP, cursor: minP });
                                                                        } else if (minP > 0) {
                                                                            codeTextArea.remove(minP - 1, minP);
                                                                            newCursors.unshift({ start: minP - 1, end: minP - 1, cursor: minP - 1 });
                                                                        } else {
                                                                            newCursors.unshift({ start: 0, end: 0, cursor: 0 });
                                                                        }
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
                                                                    cursors.sort(function(a, b) { return Math.max(b.start, b.end) - Math.max(a.start, a.end); });
                                                                    var newCursors = [];

                                                                    for (var di = 0; di < cursors.length; di++) {
                                                                        var cur = cursors[di];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            codeTextArea.remove(minP, maxP);
                                                                            newCursors.unshift({ start: minP, end: minP, cursor: minP });
                                                                        } else if (minP < codeTextArea.text.length) {
                                                                            codeTextArea.remove(minP, minP + 1);
                                                                            newCursors.unshift({ start: minP, end: minP, cursor: minP });
                                                                        } else {
                                                                            newCursors.unshift({ start: minP, end: minP, cursor: minP });
                                                                        }
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
                                                                    cursors.sort(function(a, b) { return Math.max(b.start, b.end) - Math.max(a.start, a.end); });
                                                                    var newCursors = [];

                                                                    for (var ei = 0; ei < cursors.length; ei++) {
                                                                        var cur = cursors[ei];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            codeTextArea.remove(minP, maxP);
                                                                        }
                                                                        codeTextArea.insert(minP, "\\n");
                                                                        newCursors.unshift({ start: minP + 1, end: minP + 1, cursor: minP + 1 });
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
                                                                    cursors.sort(function(a, b) { return Math.max(b.start, b.end) - Math.max(a.start, a.end); });
                                                                    var newCursors = [];

                                                                    for (var ci = 0; ci < cursors.length; ci++) {
                                                                        var cur = cursors[ci];
                                                                        var minP = Math.min(cur.start, cur.end);
                                                                        var maxP = Math.max(cur.start, cur.end);
                                                                        if (minP !== maxP) {
                                                                            codeTextArea.remove(minP, maxP);
                                                                        }
                                                                        codeTextArea.insert(minP, charTyped);
                                                                        newCursors.unshift({ start: minP + charTyped.length, end: minP + charTyped.length, cursor: minP + charTyped.length });
                                                                    }

                                                                    root.extraCursors = newCursors;
                                                                    if (newCursors.length > 0) {
                                                                        codeTextArea.cursorPosition = newCursors[newCursors.length - 1].cursor;
                                                                    }
                                                                    event.accepted = true;
                                                                    return;
                                                                }
                                                            }
                                                            """
    new_content = content[:idx1] + replacement + content[idx2:]
    with open('qml/components/EditorArea.qml', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("PATCH APPLIED SUCCESSFULLY")
else:
    print(f"FAILED TO FIND TARGETS: {idx1}, {idx2}")
