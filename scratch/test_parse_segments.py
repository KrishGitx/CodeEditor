from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from PySide6.QtQml import QJSEngine

js_engine = QJSEngine()

js_test = """
function cleanTextChunk(t) {
    if (!t) return "";
    var cleaned = t.replace(/\\[REPLACEMENT_CODE\\]/g, "")
                   .replace(/\\[NO_CHANGE\\]/g, "")
                   .replace(/\\[INSUFFICIENT_CONTEXT\\]/g, "");
    return cleaned.replace(/^\\r?\\n\\r?\\n/, "\\n").replace(/\\s+$/, "");
}

function parseMarkdownSegments(response) {
    if (!response || typeof response !== "string") {
        return [];
    }

    var text = response;
    var segments = [];
    var closedFenceRegex = /(?:`{3,}|~{3,})([a-zA-Z0-9_\\+#\\.\\-]*)[ \\t]*(?:\\r?\\n)?([\\s\\S]*?)(?:\\r?\\n)?(?:`{3,}|~{3,})/g;
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
        // Check if remaining contains an unclosed fence (streaming response)
        var unclosedFenceRegex = /(?:`{3,}|~{3,})([a-zA-Z0-9_\\+#\\.\\-]*)[ \\t]*(?:\\r?\\n)?([\\s\\S]*)$/;
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
        }
    }

    return segments;
}
"""
js_engine.evaluate(js_test)
fn = js_engine.globalObject().property("parseMarkdownSegments")

case_text = """Here is the explanation before the code.

```cpp
// Broken example:
k++
```

The issue was a missing semicolon.

[REPLACEMENT_CODE]
```cpp
k++;
```

Here is the explanation after the code.
"""
res = fn.call([case_text])
length = res.property("length").toInt()
print("Segments count:", length)
for i in range(length):
    item = res.property(i)
    print(f"{i}: type={item.property('type').toString()}, lang={item.property('lang').toString()}")
    print(f"   text: {repr(item.property('text').toString())}")
    print(f"   code: {repr(item.property('code').toString())}")
