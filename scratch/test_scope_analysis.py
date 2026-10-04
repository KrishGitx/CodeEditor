test_doc = """Item {
    property int a: 1

    Timer {
        interval: 1000

        Rectangle {
            width: 100
            height: 100
        }
    }
}"""

def compute_scopes(docText, tabSize=4):
    lines = docText.split("\n")
    stack = []
    scopes = []
    total = len(lines)
    for l in range(total):
        line = lines[l]
        trimmed = line.strip()
        cols = 0
        for i in range(len(line)):
            ch = line[i]
            if ch == ' ':
                cols += 1
            elif ch == '\t':
                cols += tabSize - (cols % tabSize)
            else:
                break
        rawIndent = cols // tabSize if len(trimmed) > 0 else -1
        inStr = False
        strQuote = ''
        c = 0
        while c < len(line):
            char = line[c]
            if char == '/' and c + 1 < len(line) and line[c+1] == '/' and not inStr:
                break
            if char in ('"', "'", '`'):
                if not inStr:
                    inStr = True
                    strQuote = char
                elif strQuote == char and (c == 0 or line[c-1] != '\\'):
                    inStr = False
                c += 1
                continue
            if inStr:
                c += 1
                continue
            if char == '{':
                blockIndent = max(0, rawIndent if rawIndent >= 0 else 0)
                stack.append({'startLine': l, 'level': blockIndent, 'rawIndent': rawIndent, 'lineText': line})
            elif char == '}':
                if len(stack) > 0:
                    top = stack.pop()
                    if l > top['startLine']:
                        scopes.append({
                            'startLine': top['startLine'],
                            'endLine': l,
                            'level': top['level'],
                            'rawIndent': top['rawIndent'],
                            'lineText': top['lineText']
                        })
            c += 1
    return scopes

scopes = compute_scopes(test_doc)
print("=== SCOPES ===")
for s in scopes:
    print(s)

lines = test_doc.split("\n")
print("\n=== LINE BY LINE ANALYSIS ===")
for l, line in enumerate(lines):
    trimmed = line.strip()
    cols = 0
    for i in range(len(line)):
        ch = line[i]
        if ch == ' ':
            cols += 1
        elif ch == '\t':
            cols += 4 - (cols % 4)
        else:
            break
    rawIndent = cols // 4 if len(trimmed) > 0 else -1
    
    # Check regular indent guides:
    regular_guides = []
    if len(trimmed) > 0:
        indentCount = cols // 4
        for lvl in range(1, indentCount):
            regular_guides.append(lvl)
            
    # Check scope guides at line l:
    scope_guides = []
    for sc in scopes:
        if sc['startLine'] + 1 <= l <= sc['endLine']:
            scope_guides.append((sc['level'], "bracket" if l == sc['endLine'] else "line"))
            
    print(f"Line {l:2d}: rawIndent={rawIndent:2d} | Regular guides (lvl)={regular_guides} | Scope guides (lvl)={scope_guides} | text: {line}")
