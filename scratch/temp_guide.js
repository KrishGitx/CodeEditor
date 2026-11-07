
const theme = { tabSize: 4 };
function computeGuideSegmentsForText(docText) {
        if (!docText) return [];
        var tabSize = (typeof theme !== "undefined" && theme && theme.tabSize) ? theme.tabSize : 4;
        var lines = docText.split("\n");
        var total = lines.length;
        if (total === 0) return [];

        function getRawLineIndent(line) {
            var trimmed = line.trim();
            if (trimmed.length === 0) return -1;
            var cols = 0;
            for (var i = 0; i < line.length; i++) {
                var ch = line.charAt(i);
                if (ch === ' ') cols += 1;
                else if (ch === '\t') cols += tabSize - (cols % tabSize);
                else break;
            }
            return Math.floor(cols / tabSize);
        }

        function isCommentOnlyLine(line) {
            var trimmed = line.trim();
            return trimmed.startsWith("//") || trimmed.startsWith("#") || trimmed.startsWith("/*") || trimmed.startsWith("*");
        }

        var lineIndents = new Array(total);
        var lineHasClosingBrace = new Array(total);
        var lineHasOpeningBrace = new Array(total);
        var lineEndsWithColon = new Array(total);

        var inBlockComment = false;
        var inTripleQuote = false;
        var tripleQuoteChar = '';

        for (var l = 0; l < total; l++) {
            var line = lines[l];
            lineIndents[l] = getRawLineIndent(line);
            lineHasClosingBrace[l] = false;
            lineHasOpeningBrace[l] = false;
            var trimmed = line.trim();
            lineEndsWithColon[l] = trimmed.endsWith(":");

            var inStr = false;
            var strQuote = '';

            for (var c = 0; c < line.length; c++) {
                var char = line.charAt(c);
                var nextChar = c + 1 < line.length ? line.charAt(c + 1) : '';

                if (inBlockComment) {
                    if (char === '*' && nextChar === '/') {
                        inBlockComment = false;
                        c++;
                    }
                    continue;
                }

                if (inTripleQuote) {
                    if (char === tripleQuoteChar && nextChar === tripleQuoteChar && c + 2 < line.length && line.charAt(c + 2) === tripleQuoteChar) {
                        inTripleQuote = false;
                        c += 2;
                    }
                    continue;
                }

                if (inStr) {
                    if (char === '\\') {
                        c++;
                    } else if (char === strQuote) {
                        inStr = false;
                    }
                    continue;
                }

                if (char === '/' && nextChar === '*') {
                    inBlockComment = true;
                    c++;
                    continue;
                }
                if (char === '/' && nextChar === '/') break;
                if (char === '#') break;

                if ((char === '"' || char === '\'') && nextChar === char && c + 2 < line.length && line.charAt(c + 2) === char) {
                    inTripleQuote = true;
                    tripleQuoteChar = char;
                    c += 2;
                    continue;
                }

                if (char === '"' || char === '\'' || char === '`') {
                    inStr = true;
                    strQuote = char;
                    continue;
                }

                if (char === '{') {
                    lineHasOpeningBrace[l] = true;
                } else if (char === '}') {
                    lineHasClosingBrace[l] = true;
                }
            }
        }

        // 2. Resolve effective indentation for blank and comment-only lines
        var effectiveIndents = new Array(total);

        for (var l = 0; l < total; l++) {
            var ind = lineIndents[l];
            if (ind >= 0 && !isCommentOnlyLine(lines[l])) {
                effectiveIndents[l] = ind;
            } else {
                var prevValidIndent = -1;
                var prevValidLine = -1;
                for (var pl = l - 1; pl >= 0; pl--) {
                    if (lineIndents[pl] >= 0 && !isCommentOnlyLine(lines[pl])) {
                        prevValidIndent = lineIndents[pl];
                        prevValidLine = pl;
                        break;
                    }
                }

                var nextValidIndent = -1;
                var nextValidLine = -1;
                for (var nl = l + 1; nl < total; nl++) {
                    if (lineIndents[nl] >= 0 && !isCommentOnlyLine(lines[nl])) {
                        nextValidIndent = lineIndents[nl];
                        nextValidLine = nl;
                        break;
                    }
                }

                if (prevValidIndent === -1 && nextValidIndent === -1) {
                    effectiveIndents[l] = 0;
                } else if (prevValidIndent === -1) {
                    effectiveIndents[l] = 0;
                } else if (nextValidIndent === -1) {
                    effectiveIndents[l] = 0;
                } else if (prevValidIndent === nextValidIndent) {
                    if (lineHasOpeningBrace[prevValidLine] || lineEndsWithColon[prevValidLine]) {
                        effectiveIndents[l] = prevValidIndent + 1;
                    } else {
                        effectiveIndents[l] = prevValidIndent;
                    }
                } else if (nextValidIndent > prevValidIndent) {
                    if (lineHasOpeningBrace[prevValidLine] || lineEndsWithColon[prevValidLine]) {
                        effectiveIndents[l] = nextValidIndent;
                    } else {
                        effectiveIndents[l] = prevValidIndent;
                    }
                } else {
                    if (lineHasClosingBrace[nextValidLine]) {
                        effectiveIndents[l] = prevValidIndent;
                    } else {
                        effectiveIndents[l] = nextValidIndent;
                    }
                }
            }
        }
        
     
        // 3. Build Continuous Logical Guide Segments
        var segments = [];
        var maxIndentObserved = 0;
        for (var l = 0; l < total; l++) {
            if (effectiveIndents[l] > maxIndentObserved) {
                maxIndentObserved = effectiveIndents[l];
            }
        }
        maxIndentObserved = Math.min(maxIndentObserved, 32);

        var activeSegments = new Array(maxIndentObserved + 1);
        for (var k = 0; k <= maxIndentObserved; k++) activeSegments[k] = null;

        for (var l = 0; l < total; l++) {
            var curEff = effectiveIndents[l];
            var isClosingLine = lineHasClosingBrace[l];
            var isOpeningLine = lineHasOpeningBrace[l];
            var rawInd = lineIndents[l];

            for (var k = 0; k <= maxIndentObserved; k++) {
                var isLevelActiveOnLine = (curEff > k);
                var isOpeningThisLevel = (isOpeningLine && rawInd === k);
                var isColonOpeningThisLevel = (lineEndsWithColon[l] && rawInd === k && (l + 1 < total && effectiveIndents[l + 1] > k));
                var isClosingThisLevel = (isClosingLine && rawInd === k);

                if (isOpeningThisLevel || isColonOpeningThisLevel) {
                    if (!activeSegments[k]) {
                        activeSegments[k] = {
                            startLine: l,
                            endLine: l,
                            level: k,
                            hasClosingBrace: false
                        };
                    }
                }

                if (isLevelActiveOnLine) {
                    if (!activeSegments[k]) {
                        var sLine = l;
                        for (var pl = l - 1; pl >= 0; pl--) {
                            if (lineIndents[pl] === k && (lineHasOpeningBrace[pl] || lineEndsWithColon[pl])) {
                                sLine = pl;
                                break;
                            }
                        }
                        activeSegments[k] = {
                            startLine: sLine,
                            endLine: l,
                            level: k,
                            hasClosingBrace: false
                        };
                    } else {
                        activeSegments[k].endLine = l;
                    }
                } else if (isClosingThisLevel) {
                    if (activeSegments[k]) {
                        activeSegments[k].endLine = l;
                        activeSegments[k].hasClosingBrace = true;
                        segments.push(activeSegments[k]);
                        activeSegments[k] = null;
                    }
                } else if (!isOpeningThisLevel && !isColonOpeningThisLevel) {
                    if (activeSegments[k]) {
                        segments.push(activeSegments[k]);
                        activeSegments[k] = null;
                    }
                }
            }
        }

        for (var k = 0; k <= maxIndentObserved; k++) {
            if (activeSegments[k]) {
                segments.push(activeSegments[k]);
                activeSegments[k] = null;
            }
        }

        return segments;
    }

    
const testDoc = public class Main {
    public static void main(String[] args) {
        try {
            // code
        }
    }
};
console.log(JSON.stringify(computeGuideSegmentsForText(testDoc), null, 2));
