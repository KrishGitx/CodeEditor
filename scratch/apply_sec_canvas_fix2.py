with open("qml/components/EditorArea.qml", "r", encoding="utf-8") as f:
    content = f.read()

target = """                                            onPaint: {
                                                var ctx = getContext("2d");
                                                ctx.clearRect(0, 0, width, height);
                                                var doc = secCodeTextArea.text;
                                                if (!doc) return;"""

replacement_paint = """                                            onPaint: {
                                                var ctx = getContext("2d");
                                                ctx.clearRect(0, 0, width, height);
                                                var doc = secCodeTextArea.text;
                                                if (!doc) return;

                                                var leftPadding = secCodeTextArea.leftPadding - secEditorFlickable.contentX;
                                                var topPadding = secCodeTextArea.topPadding;
                                                var lineH = root.editorLineHeight;
                                                var charW = root.charWidth;
                                                var cachedWidths = root.cachedIndentLevelWidths;

                                                var viewTop = secEditorFlickable.contentY;
                                                var visibleStartLine = Math.max(0, Math.floor(viewTop / lineH) - 1);
                                                var visibleEndLine = visibleStartLine + Math.ceil(height / lineH) + 4;

                                                var segments = root.computeGuideSegmentsForText(doc);
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

                                                    ctx.strokeStyle = (typeof theme !== "undefined" && theme) ? "#35383d" : "#303030";
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
                                            }"""

idx1 = content.find("id: secIndentGuidesCanvas")
assert idx1 != -1, "secIndentGuidesCanvas not found"
idx2 = content.find("onPaint: {", idx1)
assert idx2 != -1, "onPaint not found after secIndentGuidesCanvas"
idx3 = content.find("ctx.globalAlpha = 1.0;\n                                            }", idx2)
assert idx3 != -1, "end of onPaint not found"
end_idx = idx3 + len("ctx.globalAlpha = 1.0;\n                                            }")

old_chunk = content[idx2:end_idx]
print(f"Replacing {len(old_chunk)} chars...")
new_content = content[:idx2] + replacement_paint.strip() + content[end_idx:]

with open("qml/components/EditorArea.qml", "w", encoding="utf-8") as f:
    f.write(new_content)
print("Successfully updated EditorArea.qml!")
