// CodeExtractor.js - Single source of truth for pure AI code extraction

.pragma library

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
 * Strictly parses an AI response according to the 3-State Protocol:
 * Case 1: [REPLACEMENT_CODE] -> { status: "replacement", code: "..." }
 * Case 2: [NO_CHANGE]        -> { status: "no_change", code: null }
 * Case 3: [INSUFFICIENT_CONTEXT] -> { status: "insufficient_context", code: null }
 * Invalid: Missing all 3 markers -> { status: "invalid", code: null }
 *
 * @param {string} response - The raw response from the AI
 * @param {string} preferredLang - The active editor language identifier (optional)
 * @returns {object} - { status: string, code: string | null }
 */
function parseReplacementResponse(response, preferredLang) {
    if (!response || typeof response !== "string") {
        return { status: "invalid", code: null };
    }

    var text = response;

    var replMarker = "[REPLACEMENT_CODE]";
    var noChangeMarker = "[NO_CHANGE]";
    var insuffMarker = "[INSUFFICIENT_CONTEXT]";

    var replIdx = text.indexOf(replMarker);
    var noChangeIdx = text.indexOf(noChangeMarker);
    var insuffIdx = text.indexOf(insuffMarker);

    // Step 1: Look for one of [REPLACEMENT_CODE], [NO_CHANGE], [INSUFFICIENT_CONTEXT]
    // If [REPLACEMENT_CODE] exists:
    if (replIdx !== -1) {
        var textAfterMarker = text.substring(replIdx + replMarker.length);
        // Find the FIRST fenced code block AFTER that marker:
        var fenceRegex = /(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,}|$)/;
        var match = textAfterMarker.match(fenceRegex);
        if (match && match[2] !== undefined && match[2].trim().length > 0) {
            var extracted = sanitizeExtractedCode(match[2]);
            return {
                status: "replacement",
                code: extracted
            };
        }
        return { status: "invalid", code: null };
    }

    if (noChangeIdx !== -1) {
        return { status: "no_change", code: null };
    }

    if (insuffIdx !== -1) {
        return { status: "insufficient_context", code: null };
    }

    // If none of the required markers exist, treat the response as invalid for automatic replacement
    return { status: "invalid", code: null };
}

/**
 * Extracts code explicitly marked with [REPLACEMENT_CODE] for selection-based replacement.
 *
 * @param {string} response - The markdown response from the AI
 * @param {string} preferredLang - The active editor language identifier (optional)
 * @returns {string} - The clean extracted replacement code, or "" if invalid/missing
 */
function extractReplacementCode(response, preferredLang) {
    var result = parseReplacementResponse(response, preferredLang);
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

function sanitizeExtractedCode(code) {
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
    return cleanLines.join("\n").trim();
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
    var segments = [];
    var closedFenceRegex = /(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,})/g;
    var lastIdx = 0;
    var match;

    function cleanTextChunk(t) {
        if (!t) return "";
        // Clean protocol control markers from user-facing text display
        var cleaned = t.replace(/\[REPLACEMENT_CODE\]/g, "")
                       .replace(/\[NO_CHANGE\]/g, "")
                       .replace(/\[INSUFFICIENT_CONTEXT\]/g, "");
        // Clean leading/trailing blank lines resulting from marker removal
        return cleaned.replace(/^\r?\n\r?\n/, "\n").trim();
    }

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

    return segments;
}
