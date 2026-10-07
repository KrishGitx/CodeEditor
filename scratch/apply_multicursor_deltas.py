with open('qml/components/EditorArea.qml', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace paste block
paste_target = """                                                                    if (pasteText.length > 0) {
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
                                                                    }"""

paste_repl = """                                                                    if (pasteText.length > 0) {
                                                                        var snapUndo = root.multiCursorUndoStack.slice();
                                                                        snapUndo.push({ text: codeTextArea.text, cursors: JSON.parse(JSON.stringify(root.extraCursors)) });
                                                                        if (snapUndo.length > 50) snapUndo.shift();
                                                                        root.multiCursorUndoStack = snapUndo;
                                                                        root.multiCursorRedoStack = [];

                                                                        var pasteLines = pasteText.split("\\n");
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
                                                                    }"""

assert paste_target in content, "paste_target not found!"
content = content.replace(paste_target, paste_repl, 1)

# Replace typing / backspace / delete block
edit_target = """                                                                if (event.key === Qt.Key_Backspace) {
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
                                                                }"""

edit_repl = """                                                                if (event.key === Qt.Key_Backspace) {
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
                                                                        codeTextArea.insert(minP, "\\n");
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
                                                                }"""

assert edit_target in content, "edit_target not found!"
content = content.replace(edit_target, edit_repl, 1)

with open('qml/components/EditorArea.qml', 'w', encoding='utf-8') as f:
    f.write(content)

print("UPDATED MULTI-CURSOR DELTA TRACKING SUCCESSFULLY")
