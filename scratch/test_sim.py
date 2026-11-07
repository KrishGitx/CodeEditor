doc = '''with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="Asia/Kolkata",
    )

    page = context.new_page()

    page.goto(
        "https://chatgpt.com/",
        wait_until="domcontentloaded",
    )

    print(page.title())
    print(page.url)

    textbox = page.get_by_role(
        "textbox",
    )'''

tabSize = 4
lines = doc.split("\n")
total = len(lines)

def getRawLineIndent(line):
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

def isCommentOnlyLine(line):
    trimmed = line.strip()
    return trimmed.startswith("//") or trimmed.startswith("#") or trimmed.startswith("/*") or trimmed.startswith("*")

lineIndents = [getRawLineIndent(l) for l in lines]
lineHasClosingBrace = [False] * total
lineHasOpeningBrace = [False] * total
lineEndsWithColon = [False] * total

for l in range(total):
    line = lines[l]
    trimmed = line.strip()
    lineEndsWithColon[l] = trimmed.endswith(":")
    
    inStr = False
    strQuote = ''
    inBlockComment = False
    inTripleQuote = False
    tripleQuoteChar = ''
    
    c = 0
    while c < len(line):
        char = line[c]
        nextChar = line[c+1] if c+1 < len(line) else ''
        
        if inBlockComment:
            if char == '*' and nextChar == '/':
                inBlockComment = False
                c += 2
                continue
            c += 1
            continue
        
        if inTripleQuote:
            if char == tripleQuoteChar and nextChar == tripleQuoteChar and c+2 < len(line) and line[c+2] == tripleQuoteChar:
                inTripleQuote = False
                c += 3
                continue
            c += 1
            continue
            
        if inStr:
            if char == '\\':
                c += 2
                continue
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
            
        if (char == '"' or char == "'") and nextChar == char and c+2 < len(line) and line[c+2] == char:
            inTripleQuote = True
            tripleQuoteChar = char
            c += 3
            continue
            
        if char == '"' or char == "'" or char == '`':
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
    if ind >= 0 and not isCommentOnlyLine(lines[l]):
        effectiveIndents[l] = ind
    else:
        prevValidIndent = -1
        prevValidLine = -1
        for pl in range(l - 1, -1, -1):
            if lineIndents[pl] >= 0 and not isCommentOnlyLine(lines[pl]):
                prevValidIndent = lineIndents[pl]
                prevValidLine = pl
                break
                
        nextValidIndent = -1
        nextValidLine = -1
        for nl in range(l + 1, total):
            if lineIndents[nl] >= 0 and not isCommentOnlyLine(lines[nl]):
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
            if lineHasOpeningBrace[prevValidLine] or lineEndsWithColon[prevValidLine]:
                effectiveIndents[l] = prevValidIndent + 1
            else:
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

print("Line analysis:")
for l in range(total):
    print(f"{l:2d}: raw={lineIndents[l]:2d}, eff={effectiveIndents[l]:2d}, colon={lineEndsWithColon[l]} | {lines[l]}")

# 3. Build segments
maxIndentObserved = max(effectiveIndents) if effectiveIndents else 0
maxIndentObserved = min(maxIndentObserved, 32)

activeSegments = [None] * (maxIndentObserved + 1)
segments = []

for l in range(total):
    curEff = effectiveIndents[l]
    isClosingLine = lineHasClosingBrace[l]
    isOpeningLine = lineHasOpeningBrace[l]
    rawInd = lineIndents[l]

    for k in range(maxIndentObserved + 1):
        isLevelActiveOnLine = (curEff > k)
        isOpeningThisLevel = (isOpeningLine  and  rawInd == k)
        isColonOpeningThisLevel = (lineEndsWithColon[l]  and  rawInd == k and (l + 1 < total and effectiveIndents[l + 1] > k))
        isClosingThisLevel = (isClosingLine  and  rawInd == k)

        if isOpeningThisLevel or isColonOpeningThisLevel:
            if not activeSegments[k]:
                activeSegments[k] = {
                    'startLine': l,
                    'endLine': l,
                    'level': k,
                    'hasClosingBrace': False
                }

        if isLevelActiveOnLine:
            if not activeSegments[k]:
                sLine = l
                for pl in range(l - 1, -1, -1):
                    if lineIndents[pl] == k and (lineHasOpeningBrace[pl] or lineEndsWithColon[pl]):
                        sLine = pl
                        break
                activeSegments[k] = {
                    'startLine': sLine,
                    'endLine': l,
                    'level': k,
                    'hasClosingBrace': False
                }
            else:
                activeSegments[k]['endLine'] = l
        elif isClosingThisLevel:
            if activeSegments[k]:
                activeSegments[k]['endLine'] = l
                activeSegments[k]['hasClosingBrace'] = True
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

print("\nSegments:")
for s in segments:
    print(s)
