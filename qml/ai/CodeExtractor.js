// CodeExtractor.js - Single source of truth for pure AI code extraction

.pragma library

if (typeof console === "undefined") {
    var console = { log: function() {}, warn: function() {}, error: function() {} };
}

/**
 * Normalizes language names to a canonical identifier.
 */
function normalizeLang(lang) {
    if (!lang || typeof lang !== "string") return "";
    var l = lang.toLowerCase().trim();
    if (l === "py" || l === "python3") return "python";
    if (l === "js" || l === "jsx" || l === "mjs") return "javascript";
    if (l === "ts" || l === "tsx") return "typescript";
    if (l === "htm") return "html";
    if (l === "c++" || l === "c" || l === "h" || l === "hpp" || l === "cc" || l === "cxx") return "cpp";
    if (l === "golang") return "go";
    if (l === "rs") return "rust";
    if (l === "scss" || l === "less") return "css";
    if (l === "yml") return "yaml";
    if (l === "ps1") return "powershell";
    return l;
}

/**
 * Checks if two language tags match or are compatible aliases.
 */
function isLangMatch(lang1, lang2) {
    if (!lang1 || !lang2) return false;
    var n1 = normalizeLang(lang1);
    var n2 = normalizeLang(lang2);
    if (n1 === n2) return true;
    if (n1.indexOf(n2) !== -1 || n2.indexOf(n1) !== -1) return true;
    return false;
}

/**
 * Validates that an extracted replacement code covers the complete selected scope
 * and is not a destructive partial fragment or unauthorized scope expansion (e.g. full-file rewrite on small selection).
 *
 * @param {string} extractedCode - The extracted replacement candidate
 * @param {string} originalSelectedText - The original text selected by the user
 * @param {object} context - Selection context metadata (optional: { isFullFile, selectionStart, selectionEnd, totalDocLength, surroundingContext })
 * @returns {object} - { isValid: boolean, reason?: string }
 */
function validateReplacementScope(extractedCode, originalSelectedText, context) {
    if (!originalSelectedText || typeof originalSelectedText !== "string" || !originalSelectedText.trim()) {
        return { isValid: true, reason: "No original selection" };
    }
    if (!extractedCode || typeof extractedCode !== "string" || !extractedCode.trim()) {
        return { isValid: false, reason: "Replacement code is empty." };
    }

    var ctx = context || {};
    var isFullFile = (ctx.isFullFile === true) || (ctx.selectionStart === 0 && ctx.totalDocLength > 0 && ctx.selectionEnd >= ctx.totalDocLength);

    if (isFullFile) {
        return { isValid: true, reason: "Full file selection allows complete replacement." };
    }

    var origTrim = originalSelectedText.trim();
    var replTrim = extractedCode.trim();

    if (origTrim === replTrim) {
        return { isValid: true, reason: "Code identical" };
    }

    var origLines = origTrim.split(/\r?\n/).filter(function(l) { return l.trim().length > 0; });
    var replLines = replTrim.split(/\r?\n/).filter(function(l) { return l.trim().length > 0; });

    var origLineCount = origLines.length;
    var replLineCount = replLines.length;

    // 1. Scope Expansion Hazard: Outer Enclosure Insertion (e.g. with sync_playwright(), def main(), class X)
    var outerWrapperPatterns = [
        { regex: /\bwith\s+sync_playwright\b/, name: "with sync_playwright block", allowRegex: /\b(?:playwright|wright)\b/i },
        { regex: /\bdef\s+main\s*\(/, name: "def main() entrypoint", allowRegex: /\bmain\b/i },
        { regex: /\bif\s+__name__\s*==\s*['"]__main__['"]/, name: "if __name__ == '__main__' block", allowRegex: /__main__/ },
        { regex: /\bclass\s+\w+/, name: "class definition", allowRegex: /\bclass\b/ },
        { regex: /\bint\s+main\s*\(/, name: "main() function", allowRegex: /\bmain\b/i },
        { regex: /\bpublic\s+static\s+void\s+main\b/, name: "public static void main entrypoint", allowRegex: /\bmain\b/i }
    ];

    for (var i = 0; i < outerWrapperPatterns.length; i++) {
        var pat = outerWrapperPatterns[i];
        if (pat.regex.test(replTrim) && !pat.regex.test(origTrim)) {
            if (pat.allowRegex && pat.allowRegex.test(origTrim)) {
                continue;
            }
            if (origLineCount <= 6) {
                return {
                    isValid: false,
                    reason: "Scope Hazard: Replacement introduced outer wrapper (" + pat.name + ") not present in selected code."
                };
            }
        }
    }

    // 2. Scope Expansion Hazard: Small Statement expanded into full multi-statement application with top-level imports
    var origHasImports = /\b(import\s+|#include\s+|package\s+|using\s+|from\s+\w+\s+import)/i.test(origTrim);
    var replHasImports = /\b(import\s+|#include\s+|package\s+|using\s+|from\s+\w+\s+import)/i.test(replTrim);

    if (!origHasImports && replHasImports && origLineCount <= 4 && replLineCount >= 8) {
        return {
            isValid: false,
            reason: "Scope Hazard: Replacement expanded small statement into full multi-statement application with imports."
        };
    }

    // 3. Scope Expansion Hazard: Surrounding Context Duplication
    var surrounding = ctx.surroundingContext || "";
    if (surrounding && surrounding.trim().length > 0 && replTrim.indexOf(origTrim) !== -1) {
        if (replLineCount >= origLineCount + 6) {
            return {
                isValid: false,
                reason: "Scope Hazard: Replacement contains unselected surrounding context code."
            };
        }
    }

    // 4. Under-Scope Hazard: Significant line-count mismatch (e.g. original >= 8 lines, replacement <= 3 lines)
    if (origLineCount >= 8 && replLineCount <= 3) {
        return {
            isValid: false,
            reason: "Scope Hazard: Selection has " + origLineCount + " lines, but replacement contains only " + replLineCount + " lines. The replacement must preserve the entire selected scope."
        };
    }

    if (origLineCount >= 15 && (replLineCount / origLineCount) < 0.35) {
        return {
            isValid: false,
            reason: "Scope Hazard: Replacement line count (" + replLineCount + ") is less than 35% of selected scope (" + origLineCount + " lines)."
        };
    }

    // 5. Structural checks for whole-file/class selections (>= 10 lines)
    var origHasClass = /\b(class\s+|interface\s+|struct\s+|enum\s+)\w+/i.test(origTrim);
    var replHasClass = /\b(class\s+|interface\s+|struct\s+|enum\s+)\w+/i.test(replTrim);

    if (origHasClass && !replHasClass && origLineCount >= 10 && replLineCount < origLineCount * 0.6) {
        return {
            isValid: false,
            reason: "Scope Hazard: Selected scope contains class definitions which are missing from the replacement."
        };
    }

    if (origHasImports && !replHasImports && origLineCount >= 10 && replLineCount < origLineCount * 0.6) {
        return {
            isValid: false,
            reason: "Scope Hazard: Selected scope contains import/package statements which are missing from the replacement."
        };
    }

    // 6. Duplicated Leading Line Hazard (Case B)
    // Detect if the AI returned the same leading line twice when the original contains it once.
    if (replLines.length >= 2) {
        var replFirst = replLines[0].trim();
        var replSecond = replLines[1].trim();
        if (replFirst && replFirst === replSecond) {
            var origFirst = origLines.length >= 1 ? origLines[0].trim() : "";
            var origSecond = origLines.length >= 2 ? origLines[1].trim() : "";
            var origHadRepetition = (origFirst === origSecond && origFirst === replFirst);
            var origOccurrences = 0;
            for (var oi = 0; oi < origLines.length; oi++) {
                if (origLines[oi].trim() === replFirst) origOccurrences++;
            }
            if (!origHadRepetition && origOccurrences <= 1) {
                return {
                    isValid: false,
                    reason: "Duplication Hazard: AI returned duplicated leading line ('" + replFirst + "') when original selection contains it once. Rejection prevents accidental duplicate insertion."
                };
            }
        }
    }

    return { isValid: true, reason: "Valid replacement scope" };
}

/**
 * Strictly parses an AI response according to the 3-State Protocol:
 * Case 1: [REPLACEMENT_CODE] -> { status: "replacement", code: "..." }
 * Case 2: [NO_CHANGE]        -> { status: "no_change", code: null }
 * Case 3: [INSUFFICIENT_CONTEXT] -> { status: "insufficient_context", code: null }
 * Invalid: Missing all 3 markers -> { status: "invalid", code: null }
 *
 * @param {string} response - The raw response from the AI
 * @param {string} preferredLang - The active editor language identifier (optional)
 * @param {string} originalSelectedText - The original selected scope to validate complete replacement (optional)
 * @param {object} context - Selection context metadata (optional)
 * @returns {object} - { status: string, code: string | null, state: string, error?: string }
 */
function parseReplacementResponse(response, preferredLang, originalSelectedText, context) {
    var ctx = context || {};
    var selStart = ctx.selectionStart !== undefined ? ctx.selectionStart : -1;
    var selEnd = ctx.selectionEnd !== undefined ? ctx.selectionEnd : -1;
    var origText = originalSelectedText || ctx.originalSelectedText || "";
    var origLines = origText.split(/\r?\n/).filter(function(l) { return l.trim().length > 0; });
    var selLineCount = origLines.length > 0 ? origLines.length : 1;
    var selChars = origText.length;

    console.log("[AIReplacement] Selection start: " + selStart);
    console.log("[AIReplacement] Selection end: " + selEnd);
    console.log("[AIReplacement] Selection lines: " + selLineCount);
    console.log("[AIReplacement] Selection chars: " + selChars);
    console.log("[AIReplacement] Raw CustomApi response: " + (response || ""));

    if (!response || typeof response !== "string") {
        console.log("[AIReplacement] Parsed state: INVALID");
        console.log("[AIReplacement] Replacement lines: 0");
        console.log("[AIReplacement] Replacement chars: 0");
        console.log("[AIReplacement] Scope validation: FAIL");
        console.log("[AIReplacement] Replacement applied: false");
        return { status: "invalid", code: null, state: "INVALID" };
    }

    var text = response;

    // 1. FIXED_CODE ([Fixed Code])
    var fixedCodeMatch = text.match(/\[Fixed\s+Code\]:?/i);
    if (fixedCodeMatch) {
        var splitIdx = fixedCodeMatch.index;
        var explanation = text.substring(0, splitIdx).trim();
        var afterMarker = text.substring(splitIdx + fixedCodeMatch[0].length).trim();

        // Check for fenced code block below [Fixed Code]
        var fenceRegex = /(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,}|$)/;
        var match = afterMarker.match(fenceRegex);
        var extracted = "";
        if (match && match[2] !== undefined && match[2].trim().length > 0) {
            extracted = sanitizeExtractedCode(match[2], origText);
        } else {
            extracted = sanitizeExtractedCode(afterMarker, origText);
        }

        if (extracted && extracted.length > 0) {
            var replLines = extracted.split(/\r?\n/).filter(function(l) { return l.trim().length > 0; });
            var replLineCount = replLines.length;
            var replChars = extracted.length;

            console.log("[AIReplacement] Parsed state: FIXED_CODE");
            console.log("[AIReplacement] Replacement lines: " + replLineCount);
            console.log("[AIReplacement] Replacement chars: " + replChars);

            var scopeCheck = validateReplacementScope(extracted, origText, ctx);
            if (!scopeCheck.isValid) {
                console.log("[AIReplacement] Scope validation: FAIL");
                console.log("[AIReplacement] Replacement applied: false");
                logStage4Diagnostic("scope_mismatch", null, scopeCheck.reason);
                return {
                    status: "scope_mismatch",
                    code: null,
                    state: "FIXED_CODE",
                    error: scopeCheck.reason
                };
            }

            if (origText && extracted.trim() === origText.trim()) {
                console.log("[AIReplacement] Parsed state: UNCHANGED");
                console.log("[AIReplacement] Replacement lines: 0");
                console.log("[AIReplacement] Replacement chars: 0");
                console.log("[AIReplacement] Scope validation: PASS");
                console.log("[AIReplacement] Replacement applied: false");
                logStage4Diagnostic("unchanged", extracted);
                return {
                    status: "unchanged",
                    code: extracted,
                    state: "UNCHANGED",
                    explanation: explanation,
                    message: "Code is already correct and remains unchanged."
                };
            }

            console.log("[AIReplacement] Scope validation: PASS");
            logStage4Diagnostic("replacement", extracted);
            return {
                status: "replacement",
                code: extracted,
                state: "FIXED_CODE",
                explanation: explanation
            };
        }

        console.log("[AIReplacement] Parsed state: INVALID");
        console.log("[AIReplacement] Replacement lines: 0");
        console.log("[AIReplacement] Replacement chars: 0");
        console.log("[AIReplacement] Scope validation: FAIL");
        console.log("[AIReplacement] Replacement applied: false");
        logStage4Diagnostic("invalid", null);
        return { status: "invalid", code: null, state: "INVALID" };
    }

    // 2. Direct Single Code Block (per Rule 8: single code block with explanation outside)
    var directFenceRegex = /(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,}|$)/;
    var directMatch = text.match(directFenceRegex);
    if (directMatch && directMatch[2] !== undefined && directMatch[2].trim().length > 0) {
        var directExtracted = sanitizeExtractedCode(directMatch[2], origText);
        var preText = text.substring(0, directMatch.index).trim();
        var postText = text.substring(directMatch.index + directMatch[0].length).trim();
        var directExplanation = (preText && postText) ? (preText + "\n" + postText) : (preText || postText);

        if (directExtracted && directExtracted.length > 0) {
            // Check Rule 4: If code is already correct, return it unchanged
            if (origText && directExtracted.trim() === origText.trim()) {
                console.log("[AIReplacement] Parsed state: UNCHANGED");
                console.log("[AIReplacement] Replacement lines: 0");
                console.log("[AIReplacement] Replacement chars: 0");
                console.log("[AIReplacement] Scope validation: PASS");
                console.log("[AIReplacement] Replacement applied: false");
                logStage4Diagnostic("unchanged", directExtracted);
                return {
                    status: "unchanged",
                    code: directExtracted,
                    state: "UNCHANGED",
                    explanation: directExplanation,
                    message: "Code is already correct and remains unchanged."
                };
            }

            var directReplLines = directExtracted.split(/\r?\n/).filter(function(l) { return l.trim().length > 0; });
            var directReplLineCount = directReplLines.length;
            var directReplChars = directExtracted.length;

            console.log("[AIReplacement] Parsed state: FIXED_CODE");
            console.log("[AIReplacement] Replacement lines: " + directReplLineCount);
            console.log("[AIReplacement] Replacement chars: " + directReplChars);

            var directScopeCheck = validateReplacementScope(directExtracted, origText, ctx);
            if (!directScopeCheck.isValid) {
                console.log("[AIReplacement] Scope validation: FAIL");
                console.log("[AIReplacement] Replacement applied: false");
                logStage4Diagnostic("scope_mismatch", null, directScopeCheck.reason);
                return {
                    status: "scope_mismatch",
                    code: null,
                    state: "FIXED_CODE",
                    error: directScopeCheck.reason
                };
            }

            console.log("[AIReplacement] Scope validation: PASS");
            logStage4Diagnostic("replacement", directExtracted);
            return {
                status: "replacement",
                code: directExtracted,
                state: "FIXED_CODE",
                explanation: directExplanation
            };
        }
    }

    // 2. SUCCESS (No bugs found)
    var trimResp = text.trim();
    var isSuccess = (/^\s*SUCCESS\b/i.test(trimResp) || trimResp === "SUCCESS");
    if (!isSuccess && text.indexOf("[Fixed Code]") === -1) {
        if (/\bSUCCESS\b/i.test(text) && trimResp.split(/\s+/).length <= 10) {
            isSuccess = true;
        }
    }

    if (isSuccess) {
        console.log("[AIReplacement] Parsed state: SUCCESS");
        console.log("[AIReplacement] Replacement lines: 0");
        console.log("[AIReplacement] Replacement chars: 0");
        console.log("[AIReplacement] Scope validation: PASS");
        console.log("[AIReplacement] Replacement applied: false");
        return {
            status: "success",
            code: null,
            state: "SUCCESS",
            message: "SUCCESS: No bugs found in the provided code selection."
        };
    }

    // 3. Legacy REPLACEMENT_CODE
    var replMarker = "[REPLACEMENT_CODE]";
    var noChangeMarker = "[NO_CHANGE]";
    var insuffMarker = "[INSUFFICIENT_CONTEXT]";

    var replIdx = text.indexOf(replMarker);
    var noChangeIdx = text.indexOf(noChangeMarker);
    var insuffIdx = text.indexOf(insuffMarker);

    if (replIdx !== -1) {
        var textAfterMarker = text.substring(replIdx + replMarker.length);
        var fenceRegexLegacy = /(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,}|$)/;
        var matchLegacy = textAfterMarker.match(fenceRegexLegacy);
        if (matchLegacy && matchLegacy[2] !== undefined && matchLegacy[2].trim().length > 0) {
            var extractedLegacy = sanitizeExtractedCode(matchLegacy[2]);
            var replLinesLegacy = extractedLegacy.split(/\r?\n/).filter(function(l) { return l.trim().length > 0; });
            var replLineCountLegacy = replLinesLegacy.length;
            var replCharsLegacy = extractedLegacy.length;

            console.log("[AIReplacement] Parsed state: REPLACEMENT_CODE");
            console.log("[AIReplacement] Replacement lines: " + replLineCountLegacy);
            console.log("[AIReplacement] Replacement chars: " + replCharsLegacy);

            var scopeCheckLegacy = validateReplacementScope(extractedLegacy, origText, ctx);
            if (!scopeCheckLegacy.isValid) {
                console.log("[AIReplacement] Scope validation: FAIL");
                console.log("[AIReplacement] Replacement applied: false");
                return {
                    status: "scope_mismatch",
                    code: null,
                    state: "REPLACEMENT_CODE",
                    error: scopeCheckLegacy.reason
                };
            }

            console.log("[AIReplacement] Scope validation: PASS");
            return {
                status: "replacement",
                code: extractedLegacy,
                state: "REPLACEMENT_CODE"
            };
        }

        console.log("[AIReplacement] Parsed state: INVALID");
        console.log("[AIReplacement] Replacement lines: 0");
        console.log("[AIReplacement] Replacement chars: 0");
        console.log("[AIReplacement] Scope validation: FAIL");
        console.log("[AIReplacement] Replacement applied: false");
        return { status: "invalid", code: null, state: "INVALID" };
    }

    // 4. Legacy NO_CHANGE
    if (noChangeIdx !== -1) {
        console.log("[AIReplacement] Parsed state: NO_CHANGE");
        console.log("[AIReplacement] Replacement lines: 0");
        console.log("[AIReplacement] Replacement chars: 0");
        console.log("[AIReplacement] Scope validation: PASS");
        console.log("[AIReplacement] Replacement applied: false");
        return { status: "no_change", code: null, state: "NO_CHANGE" };
    }

    // 5. Legacy INSUFFICIENT_CONTEXT
    if (insuffIdx !== -1) {
        console.log("[AIReplacement] Parsed state: INSUFFICIENT_CONTEXT");
        console.log("[AIReplacement] Replacement lines: 0");
        console.log("[AIReplacement] Replacement chars: 0");
        console.log("[AIReplacement] Scope validation: PASS");
        console.log("[AIReplacement] Replacement applied: false");
        return { status: "insufficient_context", code: null, state: "INSUFFICIENT_CONTEXT" };
    }

    // 6. INVALID / EXPLANATION ONLY (Case D & E)
    console.log("[AIReplacement] Parsed state: INVALID");
    console.log("[AIReplacement] Replacement lines: 0");
    console.log("[AIReplacement] Replacement chars: 0");
    console.log("[AIReplacement] Scope validation: FAIL");
    console.log("[AIReplacement] Replacement applied: false");
    var rejReason = "No code block returned in AI response (explanation only).";
    logStage4Diagnostic("invalid", null, rejReason);
    return { status: "invalid", code: null, state: "INVALID", explanation: (response || "").trim(), error: rejReason };
}

/**
 * Extracts code explicitly marked with [REPLACEMENT_CODE] for selection-based replacement.
 *
 * @param {string} response - The markdown response from the AI
 * @param {string} preferredLang - The active editor language identifier (optional)
 * @param {string} originalSelectedText - The original selected scope to validate complete replacement (optional)
 * @returns {string} - The clean extracted replacement code, or "" if invalid/missing
 */
function extractReplacementCode(response, preferredLang, originalSelectedText, context) {
    var result = parseReplacementResponse(response, preferredLang, originalSelectedText, context);
    if (result.status === "replacement" && result.code && result.code.trim().length > 0) {
        return result.code;
    }
    return "";
}

/**
 * Extracts pure code from an AI response containing Markdown or conversational text.
 * - Fenced code blocks (```...``` or ~~~...~~~) take absolute priority over any surrounding text.
 * - Discards all text before and after the fence.
 * - Removes the opening ```language and closing ``` markers.
 * - Preserves code indentation, blank lines, and formatting exactly.
 * - Supports language identifiers (html, qml, python, cpp, javascript, js, css, json, etc.) or no identifier.
 * - Supports unclosed/truncated fences.
 * - If multiple fenced blocks exist, selects the block matching preferredLang.
 * - Fallback mode ONLY runs when no code fences exist.
 *
 * @param {string} response - The markdown response from the AI
 * @param {string} preferredLang - The active editor language identifier (optional)
 * @returns {string} - The clean extracted code
 */
function extractCodeFromMarkdown(response, preferredLang) {
    if (!response || typeof response !== "string") {
        return "";
    }

    var text = response.trim();
    if (!text) return "";

    var matches = [];

    // 1. Match all closed code blocks: ```[lang]\n[code]``` or ~~~[lang]\n[code]~~~
    var closedFenceRegex = /(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,})/g;
    var match;

    while ((match = closedFenceRegex.exec(text)) !== null) {
        var langTag = (match[1] || "").toLowerCase().trim();
        var codeContent = match[2];

        matches.push({
            lang: langTag,
            code: codeContent
        });
    }

    // 2. If no closed fences found, check for an unclosed fence (streaming or truncated response)
    if (matches.length === 0) {
        var unclosedFenceRegex = /(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*)$/;
        var unclosedMatch = text.match(unclosedFenceRegex);
        if (unclosedMatch && unclosedMatch[2] !== undefined && unclosedMatch[2].length > 0) {
            var uLang = (unclosedMatch[1] || "").toLowerCase().trim();
            var uCode = unclosedMatch[2];
            matches.push({
                lang: uLang,
                code: uCode
            });
        }
    }

    // 3. Web format: "html\nCopy code\n[code]" or "Copy code\n[code]"
    if (matches.length === 0) {
        var copyCodeIdx = text.indexOf("Copy code");
        if (copyCodeIdx === -1) copyCodeIdx = text.indexOf("Copy\n");
        if (copyCodeIdx !== -1) {
            var nlAfterCopy = text.indexOf("\n", copyCodeIdx);
            if (nlAfterCopy !== -1) {
                var remaining = text.substring(nlAfterCopy + 1);
                var textBeforeCopy = text.substring(0, copyCodeIdx).trim();
                var lastWordMatch = textBeforeCopy.match(/([a-zA-Z0-9_\+#\.\-]+)$/);
                var wLang = lastWordMatch ? lastWordMatch[1] : "";

                var stopRegex = /\n\s*(?:Explanation|Notes|The key correction|There's|Here's|\*\*|Hope this helps|#|\bLet me know\b|The explanation)/i;
                var stopMatch = remaining.match(stopRegex);
                var wCode = stopMatch ? remaining.substring(0, stopMatch.index).trim() : remaining.trim();
                if (wCode.length > 0) {
                    matches.push({
                        lang: wLang.toLowerCase(),
                        code: wCode
                    });
                }
            }
        }
    }

    // 4. Fenced blocks are authoritative: if any were found, return the best match
    if (matches.length > 0) {
        if (matches.length === 1) {
            return sanitizeExtractedCode(matches[0].code);
        }

        // Multiple fenced blocks: match against preferred language
        if (preferredLang && typeof preferredLang === "string") {
            var normPref = normalizeLang(preferredLang);

            // Direct match
            for (var i = 0; i < matches.length; i++) {
                if (matches[i].lang && normalizeLang(matches[i].lang) === normPref) {
                    return sanitizeExtractedCode(matches[i].code);
                }
            }

            // Compatibility/alias match
            for (var j = 0; j < matches.length; j++) {
                if (matches[j].lang && isLangMatch(matches[j].lang, preferredLang)) {
                    return sanitizeExtractedCode(matches[j].code);
                }
            }
        }

        // Default to first code block if none matched preferredLang
        return sanitizeExtractedCode(matches[0].code);
    }

    // 5. Fallback: ONLY when NO code fences exist at all, filter conversational explanation
    var lines = text.split(/\r?\n/);
    var filtered = [];
    var skipHeader = true;

    for (var k = 0; k < lines.length; k++) {
        var line = lines[k];
        var trimmed = line.trim().toLowerCase();

        if (skipHeader) {
            if (trimmed.startsWith("here is") ||
                trimmed.startsWith("here's") ||
                trimmed.startsWith("certainly") ||
                trimmed.startsWith("sure,") ||
                trimmed.startsWith("sure!") ||
                trimmed.startsWith("i have") ||
                trimmed.startsWith("to fix this") ||
                trimmed.startsWith("below is") ||
                trimmed.startsWith("please find") ||
                trimmed.startsWith("there's") ||
                trimmed.startsWith("there is") ||
                trimmed.startsWith("the key correction") ||
                trimmed.startsWith("log in") ||
                trimmed.startsWith("sign up") ||
                trimmed.indexOf("log in for more personalized help") !== -1 ||
                trimmed.startsWith("###") ||
                trimmed.startsWith("##") ||
                trimmed.startsWith("#") ||
                trimmed === "") {
                continue;
            } else {
                skipHeader = false;
            }
        }

        if (trimmed.startsWith("hope this helps") ||
            trimmed.startsWith("let me know") ||
            trimmed.startsWith("feel free to") ||
            trimmed.startsWith("explanation:") ||
            trimmed.startsWith("**explanation") ||
            trimmed.startsWith("### explanation") ||
            trimmed.startsWith("note:") ||
            trimmed.startsWith("**notes") ||
            trimmed.startsWith("key changes:") ||
            trimmed.startsWith("what was improved") ||
            trimmed.startsWith("what changed:") ||
            trimmed.indexOf("log in for more personalized help") !== -1 ||
            trimmed.indexOf("sign up for free") !== -1) {
            break;
        }

        filtered.push(line);
    }

    var fallbackResult = sanitizeExtractedCode(filtered.join("\n").trim());
    return fallbackResult.length > 0 ? fallbackResult : sanitizeExtractedCode(text);
}

function sanitizeExtractedCode(code, originalSelectedText) {
    if (!code || typeof code !== "string") return "";
    var lines = code.split(/\r?\n/);
    var cleanLines = [];
    for (var i = 0; i < lines.length; i++) {
        var l = lines[i];
        var t = l.trim().toLowerCase();
        if (t.indexOf("log in for more personalized help") !== -1 ||
            t.indexOf("sign up for free") !== -1 ||
            t.indexOf("log in sign up") !== -1 ||
            t.startsWith("what was improved") ||
            t.startsWith("what changed:")) {
            continue;
        }
        cleanLines.push(l);
    }
    var cleaned = cleanLines.join("\n").trim();

    // Guard against spurious leading '(' introduced by AI output when original selection did not start with '('
    var origText = originalSelectedText || "";
    if (origText && typeof origText === "string" && origText.trim().length > 0) {
        var origTrim = origText.trim();
        var origStartsWithParen = (origTrim.charAt(0) === '(');
        if (!origStartsWithParen) {
            var cLines = cleaned.split(/\r?\n/);
            if (cLines.length > 0 && cLines[0].trim() === "(") {
                console.log("[AIReplacement] Diagnostic: Detected and removed spurious leading '(' line introduced by AI response.");
                cLines.shift();
                cleaned = cLines.join("\n").trim();
            } else if (cleaned.charAt(0) === '(') {
                var openCount = (cleaned.match(/\(/g) || []).length;
                var closeCount = (cleaned.match(/\)/g) || []).length;
                if (openCount > closeCount) {
                    console.log("[AIReplacement] Diagnostic: Detected and removed spurious leading '(' character introduced by AI response.");
                    cleaned = cleaned.substring(1).trim();
                }
            }
        }
    }

    return cleaned;
}

function logStage4Diagnostic(status, extracted, rejectionReason) {
    var first10 = (extracted || "").substring(0, 10);
    var last10 = (extracted || "").length > 10 ? (extracted || "").substring((extracted || "").length - 10) : (extracted || "");
    console.log("[AI_DIAGNOSTIC_STAGE_4] === EXTRACTED REPLACEMENT CODE IMMEDIATELY AFTER PARSING ===");
    console.log("[AI_DIAGNOSTIC_STAGE_4] Status: " + status);
    if (rejectionReason) {
        console.log("[AI_DIAGNOSTIC_STAGE_4] Rejection Reason: " + rejectionReason);
    }
    console.log("[AI_DIAGNOSTIC_STAGE_4] Length: " + (extracted ? extracted.length : 0));
    console.log("[AI_DIAGNOSTIC_STAGE_4] First 10 chars: " + JSON.stringify(first10));
    console.log("[AI_DIAGNOSTIC_STAGE_4] Last 10 chars: " + JSON.stringify(last10));
    console.log("[AI_DIAGNOSTIC_STAGE_4] Full extracted code (with whitespace visible): " + JSON.stringify(extracted || ""));
}

/**
 * Parses markdown text into sequential text and code block segments.
 * Each segment object has: { type: "text" | "code", text: string, code: string, lang: string }
 */
function parseMarkdownSegments(response) {
    if (!response || typeof response !== "string") {
        return [];
    }

    var text = response;
    var trimText = text.trim();
    if (/^\s*SUCCESS\s*$/i.test(trimText)) {
        return [{
            type: "text",
            text: "SUCCESS: No bugs found in the provided code selection.",
            code: "",
            lang: ""
        }];
    }

    function cleanTextChunk(t) {
        if (!t) return "";
        var trimT = t.trim();
        if (/^\s*SUCCESS\s*$/i.test(trimT)) {
            return "SUCCESS: No bugs found in the provided code selection.";
        }
        // Clean protocol control markers from user-facing text display
        var cleaned = t.replace(/\[Fixed\s+Code\]:?/gi, "")
                       .replace(/\[REPLACEMENT_CODE\]/g, "")
                       .replace(/\[NO_CHANGE\]/g, "")
                       .replace(/\[INSUFFICIENT_CONTEXT\]/g, "");
        // Clean leading/trailing blank lines resulting from marker removal
        return cleaned.replace(/^\r?\n\r?\n/, "\n").trim();
    }

    var segments = [];

    // Special case: unfenced [Fixed Code] response
    if (!/(?:`{3,}|~{3,})/.test(text) && /\[Fixed\s+Code\]:?/i.test(text)) {
        var fcMatch = text.match(/\[Fixed\s+Code\]:?/i);
        var expText = cleanTextChunk(text.substring(0, fcMatch.index));
        var codeText = sanitizeExtractedCode(text.substring(fcMatch.index + fcMatch[0].length));
        if (expText.length > 0) {
            segments.push({
                type: "text",
                text: expText,
                code: "",
                lang: ""
            });
        }
        if (codeText.length > 0) {
            segments.push({
                type: "code",
                text: "",
                code: codeText,
                lang: "code"
            });
        }
        return segments;
    }

    var closedFenceRegex = /(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,})/g;
    var lastIdx = 0;
    var match;

    while ((match = closedFenceRegex.exec(text)) !== null) {
        if (match.index > lastIdx) {
            var textChunk = text.substring(lastIdx, match.index);
            var cleaned = cleanTextChunk(textChunk);
            if (cleaned.length > 0) {
                segments.push({
                    type: "text",
                    text: cleaned,
                    code: "",
                    lang: ""
                });
            }
        }

        var lang = (match[1] || "").trim();
        var code = match[2] !== undefined ? match[2] : "";

        segments.push({
            type: "code",
            text: "",
            code: code,
            lang: lang || "code"
        });

        lastIdx = closedFenceRegex.lastIndex;
    }

    if (lastIdx < text.length) {
        var remaining = text.substring(lastIdx);
        // Check if remaining contains an unclosed fence (e.g. while streaming)
        var unclosedFenceRegex = /(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*)$/;
        var uMatch = remaining.match(unclosedFenceRegex);
        if (uMatch) {
            var beforeUnclosed = remaining.substring(0, uMatch.index);
            var cleanedBefore = cleanTextChunk(beforeUnclosed);
            if (cleanedBefore.length > 0) {
                segments.push({
                    type: "text",
                    text: cleanedBefore,
                    code: "",
                    lang: ""
                });
            }
            var uLang = (uMatch[1] || "").trim();
            var uCode = uMatch[2] !== undefined ? uMatch[2] : "";
            segments.push({
                type: "code",
                text: "",
                code: uCode,
                lang: uLang || "code"
            });
        } else {
            var cleanedRem = cleanTextChunk(remaining);
            if (cleanedRem.length > 0) {
                segments.push({
                    type: "text",
                    text: cleanedRem,
                    code: "",
                    lang: ""
                });
            }
        }
    }

    if (segments.length === 0) {
        var trimText = text.trim();
        if (/^\s*SUCCESS\b/i.test(trimText) || trimText === "SUCCESS") {
            segments.push({
                type: "text",
                text: "SUCCESS: No bugs found in the provided code selection.",
                code: "",
                lang: ""
            });
        } else if (/\[Fixed\s+Code\]:?/i.test(text)) {
            var fcMatch = text.match(/\[Fixed\s+Code\]:?/i);
            var expText = cleanTextChunk(text.substring(0, fcMatch.index));
            var codeText = sanitizeExtractedCode(text.substring(fcMatch.index + fcMatch[0].length));
            if (expText.length > 0) {
                segments.push({
                    type: "text",
                    text: expText,
                    code: "",
                    lang: ""
                });
            }
            if (codeText.length > 0) {
                segments.push({
                    type: "code",
                    text: "",
                    code: codeText,
                    lang: "code"
                });
            }
        } else {
            var onlyCleaned = cleanTextChunk(text);
            if (onlyCleaned.length > 0) {
                segments.push({
                    type: "text",
                    text: onlyCleaned,
                    code: "",
                    lang: ""
                });
            } else {
                if (text.indexOf("[NO_CHANGE]") !== -1) {
                    segments.push({
                        type: "text",
                        text: "No changes needed. The selected code has no issues.",
                        code: "",
                        lang: ""
                    });
                } else if (text.indexOf("[INSUFFICIENT_CONTEXT]") !== -1) {
                    segments.push({
                        type: "text",
                        text: "Insufficient context to determine a safe modification. The fix requires information outside the selected code range.",
                        code: "",
                        lang: ""
                    });
                } else if (text.trim().length > 0) {
                    segments.push({
                        type: "text",
                        text: text.trim(),
                        code: "",
                        lang: ""
                    });
                }
            }
        }
    }

    return segments;
}
