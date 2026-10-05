import sys
import time

def compute_guide_segments(docText, tabSize=4):
    lines = docText.split("\n")
    total = len(lines)
    if total == 0:
        return []

    def get_raw_line_indent(line):
        trimmed = line.strip()
        if len(trimmed) == 0:
            return -1
        cols = 0
        for ch in line:
            if ch == ' ':
                cols += 1
            elif ch == '\t':
                cols += tabSize - (cols % tabSize)
            else:
                break
        return cols // tabSize

    def is_comment_only(line):
        trimmed = line.strip()
        return trimmed.startswith("//") or trimmed.startswith("#") or trimmed.startswith("/*") or trimmed.startswith("*")

    lineIndents = [get_raw_line_indent(l) for l in lines]
    lineHasClosingBrace = [False] * total
    lineHasOpeningBrace = [False] * total
    lineEndsWithColon = [lines[l].strip().endswith(":") for l in range(total)]

    inBlockComment = False
    inTripleQuote = False
    tripleQuoteChar = ''

    for l in range(total):
        line = lines[l]
        inStr = False
        strQuote = ''
        c = 0
        while c < len(line):
            char = line[c]
            nextChar = line[c + 1] if c + 1 < len(line) else ''

            if inBlockComment:
                if char == '*' and nextChar == '/':
                    inBlockComment = False
                    c += 1
                c += 1
                continue

            if inTripleQuote:
                if char == tripleQuoteChar and nextChar == tripleQuoteChar and c + 2 < len(line) and line[c + 2] == tripleQuoteChar:
                    inTripleQuote = False
                    c += 2
                c += 1
                continue

            if inStr:
                if char == '\\':
                    c += 1
                elif char == strQuote:
                    inStr = False
                c += 1
                continue

            if char == '/' and nextChar == '*':
                inBlockComment = True
                c += 2
                continue
            if char == '/' and nextChar == '/':
                break
            if char == '#':
                break

            if (char == '"' or char == '\'') and nextChar == char and c + 2 < len(line) and line[c + 2] == char:
                inTripleQuote = True
                tripleQuoteChar = char
                c += 3
                continue

            if char in ('"', "'", '`'):
                inStr = True
                strQuote = char
                c += 1
                continue

            if char == '{':
                lineHasOpeningBrace[l] = True
            elif char == '}':
                lineHasClosingBrace[l] = True
            c += 1

    effectiveIndents = [0] * total
    for l in range(total):
        ind = lineIndents[l]
        if ind >= 0 and not is_comment_only(lines[l]):
            effectiveIndents[l] = ind
        else:
            prevValidIndent = -1
            prevValidLine = -1
            for pl in range(l - 1, -1, -1):
                if lineIndents[pl] >= 0 and not is_comment_only(lines[pl]):
                    prevValidIndent = lineIndents[pl]
                    prevValidLine = pl
                    break

            nextValidIndent = -1
            nextValidLine = -1
            for nl in range(l + 1, total):
                if lineIndents[nl] >= 0 and not is_comment_only(lines[nl]):
                    nextValidIndent = lineIndents[nl]
                    nextValidLine = nl
                    break

            if prevValidIndent == -1 and nextValidIndent == -1:
                effectiveIndents[l] = 0
            elif prevValidIndent == -1:
                effectiveIndents[l] = 0
            elif nextValidIndent == -1:
                effectiveIndents[l] = 0
            elif prevValidIndent == nextValidIndent:
                effectiveIndents[l] = prevValidIndent
            elif nextValidIndent > prevValidIndent:
                if lineHasOpeningBrace[prevValidLine] or lineEndsWithColon[prevValidLine]:
                    effectiveIndents[l] = nextValidIndent
                else:
                    effectiveIndents[l] = prevValidIndent
            else:
                if lineHasClosingBrace[nextValidLine]:
                    effectiveIndents[l] = prevValidIndent
                else:
                    effectiveIndents[l] = nextValidIndent

    segments = []
    maxIndentObserved = min(max(effectiveIndents) if effectiveIndents else 0, 32)
    activeSegments = [None] * (maxIndentObserved + 1)

    for l in range(total):
        curEff = effectiveIndents[l]
        isClosingLine = lineHasClosingBrace[l]
        isOpeningLine = lineHasOpeningBrace[l]
        rawInd = lineIndents[l]

        for k in range(maxIndentObserved + 1):
            isLevelActiveOnLine = (curEff > k)
            isOpeningThisLevel = (isOpeningLine and rawInd == k)
            isColonOpeningThisLevel = (lineEndsWithColon[l] and rawInd == k and (l + 1 < total and effectiveIndents[l + 1] > k))
            isClosingThisLevel = (isClosingLine and rawInd == k)

            if isOpeningThisLevel or isColonOpeningThisLevel:
                if not activeSegments[k]:
                    activeSegments[k] = {
                        "startLine": l,
                        "endLine": l,
                        "level": k,
                        "hasClosingBrace": False
                    }

            if isLevelActiveOnLine:
                if not activeSegments[k]:
                    sLine = l
                    for pl in range(l - 1, -1, -1):
                        if lineIndents[pl] == k and (lineHasOpeningBrace[pl] or lineEndsWithColon[pl]):
                            sLine = pl
                            break
                    activeSegments[k] = {
                        "startLine": sLine,
                        "endLine": l,
                        "level": k,
                        "hasClosingBrace": False
                    }
                else:
                    activeSegments[k]["endLine"] = l
            elif isClosingThisLevel:
                if activeSegments[k]:
                    activeSegments[k]["endLine"] = l
                    activeSegments[k]["hasClosingBrace"] = True
                    segments.append(activeSegments[k])
                    activeSegments[k] = None
            elif not isOpeningThisLevel and not isColonOpeningThisLevel:
                if activeSegments[k]:
                    segments.append(activeSegments[k])
                    activeSegments[k] = None

    for k in range(maxIndentObserved + 1):
        if activeSegments[k]:
            segments.append(activeSegments[k])
            activeSegments[k] = None

    return segments

def run_tests():
    print("--- Running Indentation Guide Tests ---")

    # TEST 1: Blank lines inside scope
    doc1 = """if (foo) {
    code();


    moreCode();
}"""
    segs1 = compute_guide_segments(doc1)
    print("Test 1 Segments:", segs1)
    assert any(s['startLine'] == 0 and s['endLine'] == 5 and s['level'] == 0 and s['hasClosingBrace'] for s in segs1), "Test 1 failed!"
    print("[PASS] Test 1: Blank lines inside scope continuous from line 0 to line 5")

    # TEST 2: Blank lines before first line
    doc2 = """if (foo) {


    code();
}"""
    segs2 = compute_guide_segments(doc2)
    print("Test 2 Segments:", segs2)
    assert any(s['startLine'] == 0 and s['endLine'] == 4 and s['level'] == 0 and s['hasClosingBrace'] for s in segs2), "Test 2 failed!"
    print("[PASS] Test 2: Blank lines before first line starts at line 0")

    # TEST 3: Blank lines before closing bracket
    doc3 = """if (foo) {
    code();


}"""
    segs3 = compute_guide_segments(doc3)
    print("Test 3 Segments:", segs3)
    assert any(s['startLine'] == 0 and s['endLine'] == 4 and s['level'] == 0 and s['hasClosingBrace'] for s in segs3), "Test 3 failed!"
    print("[PASS] Test 3: Blank lines before closing bracket connects to line 4")

    # TEST 4: Nested scopes
    doc4 = """function outer() {
    if (a) {
        inner();
    }
}"""
    segs4 = compute_guide_segments(doc4)
    print("Test 4 Segments:", segs4)
    has_outer = any(s['startLine'] == 0 and s['endLine'] == 4 and s['level'] == 0 and s['hasClosingBrace'] for s in segs4)
    has_inner = any(s['startLine'] == 1 and s['endLine'] == 3 and s['level'] == 1 and s['hasClosingBrace'] for s in segs4)
    assert has_outer and has_inner, "Test 4 failed!"
    print("[PASS] Test 4: Nested scopes at level 0 and level 1")

    # TEST 5: Comments inside scope
    doc5 = """if (foo) {
    // Single line comment
    /* Multi line
       comment */
    code();
}"""
    segs5 = compute_guide_segments(doc5)
    print("Test 5 Segments:", segs5)
    assert any(s['startLine'] == 0 and s['endLine'] == 5 and s['level'] == 0 and s['hasClosingBrace'] for s in segs5), "Test 5 failed!"
    print("[PASS] Test 5: Comments inside scope do not break guide")

    # TEST 6: Python / Colon-based indentation
    doc6 = """def my_func():

    x = 1

    y = 2
z = 3"""
    segs6 = compute_guide_segments(doc6)
    print("Test 6 Segments:", segs6)
    assert any(s['startLine'] == 0 and s['endLine'] == 4 and s['level'] == 0 for s in segs6), "Test 6 failed!"
    print("[PASS] Test 6: Python function guide starts at line 0, runs through blank lines to line 4")

    # TEST 7: Malformed / unclosed block
    doc7 = """if (open) {
    code();"""
    segs7 = compute_guide_segments(doc7)
    print("Test 7 Segments:", segs7)
    assert any(s['startLine'] == 0 and s['endLine'] == 1 and s['level'] == 0 and not s['hasClosingBrace'] for s in segs7), "Test 7 failed!"
    print("[PASS] Test 7: Malformed / unclosed block terminates gracefully")

    # TEST 8: Large file (3000 lines) performance test
    large_lines = []
    for i in range(500):
        large_lines.append(f"function fn_{i}() {{")
        large_lines.append("    // Comment")
        large_lines.append("    if (true) {")
        large_lines.append("        doSomething();")
        large_lines.append("")
        large_lines.append("    }")
        large_lines.append("}")
    large_doc = "\n".join(large_lines)
    assert len(large_lines) == 3500

    t0 = time.time()
    large_segs = compute_guide_segments(large_doc)
    dt = time.time() - t0
    print(f"[PASS] Test 8: 3500 lines processed in {dt*1000:.2f}ms. Total segments found: {len(large_segs)}")
    assert dt < 0.1, "Large file performance took too long!"

    print("\nALL PYTHON UNIT TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
