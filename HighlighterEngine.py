"""
HighlighterEngine.py - High-Performance, Fully Accurate Multi-Language Syntax Highlighting Engine
Uses unified single-pass regular expressions with fast integer group indices, comment fast-paths,
and standard Qt QSyntaxHighlighter block-state propagation for multiline docstrings and comments.
Supports 25+ programming languages, file types, and dynamic color themes.
"""

from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QRegularExpression
import os

THEMES = {
    "obsidian": {
        "background": "#12141a",
        "foreground": "#e8ecf4",
        "keywords": "#c678dd",
        "functions": "#61afef",
        "strings": "#98c379",
        "numbers": "#d19a66",
        "comments": "#5c6478",
        "types": "#e5c07b",
        "operators": "#56b6c2",
        "preprocessor": "#e06c75",
        "current_line": "#181b24",
        "selection": "#264f78"
    },
    "dark": {
        "background": "#12141a",
        "foreground": "#e8ecf4",
        "keywords": "#c678dd",
        "functions": "#61afef",
        "strings": "#98c379",
        "numbers": "#d19a66",
        "comments": "#5c6478",
        "types": "#e5c07b",
        "operators": "#56b6c2",
        "preprocessor": "#e06c75",
        "current_line": "#181b24",
        "selection": "#264f78"
    },
    "midnight": {
        "background": "#090d18",
        "foreground": "#c8d3f5",
        "keywords": "#9d7cd8",
        "functions": "#7aa2f7",
        "strings": "#73daca",
        "numbers": "#ff9e64",
        "comments": "#4e567a",
        "types": "#2ac3de",
        "operators": "#bb9af7",
        "preprocessor": "#f7768e",
        "current_line": "#0d1222",
        "selection": "#28366a"
    },
    "dracula": {
        "background": "#1e1f29",
        "foreground": "#f8f8f2",
        "keywords": "#ff79c6",
        "functions": "#50fa7b",
        "strings": "#f1fa8c",
        "numbers": "#bd93f9",
        "comments": "#6272a4",
        "types": "#8be9fd",
        "operators": "#ff79c6",
        "preprocessor": "#ffb86c",
        "current_line": "#24253a",
        "selection": "#44475a"
    },
    "nord": {
        "background": "#242933",
        "foreground": "#eceff4",
        "keywords": "#81a1c1",
        "functions": "#88c0d0",
        "strings": "#a3be8c",
        "numbers": "#b48ead",
        "comments": "#6b7c96",
        "types": "#8fbcbb",
        "operators": "#81a1c1",
        "preprocessor": "#bf616a",
        "current_line": "#2a3040",
        "selection": "#3b4b68"
    },
    "monokai": {
        "background": "#272822",
        "foreground": "#f8f8f2",
        "keywords": "#f92672",
        "functions": "#a6e22e",
        "strings": "#e6db74",
        "numbers": "#ae81ff",
        "comments": "#75715e",
        "types": "#66d9ef",
        "operators": "#f92672",
        "preprocessor": "#fd971f",
        "current_line": "#2e2f28",
        "selection": "#494a3e"
    },
    "light": {
        "background": "#ffffff",
        "foreground": "#1a1d2b",
        "keywords": "#7c3aed",
        "functions": "#2563eb",
        "strings": "#059669",
        "numbers": "#d97706",
        "comments": "#8895ad",
        "types": "#0891b2",
        "operators": "#475569",
        "preprocessor": "#dc2626",
        "current_line": "#f5f7fb",
        "selection": "#add6ff"
    },
    "paper": {
        "background": "#faf8f4",
        "foreground": "#2c2820",
        "keywords": "#8b5a2b",
        "functions": "#2e6b4f",
        "strings": "#6b5b3a",
        "numbers": "#8b4513",
        "comments": "#9a9288",
        "types": "#2f6b6b",
        "operators": "#5a4e3c",
        "preprocessor": "#a04040",
        "current_line": "#f2efe8",
        "selection": "#d5c8a8"
    },
    "glass": {
        "background": "#10131b",
        "foreground": "#f0f4fc",
        "keywords": "#c084fc",
        "functions": "#60a5fa",
        "strings": "#4ade80",
        "numbers": "#fb923c",
        "comments": "#607090",
        "types": "#38bdf8",
        "operators": "#818cf8",
        "preprocessor": "#f87171",
        "current_line": "#18204030",
        "selection": "#305880"
    },
    "transparent": {
        "background": "#10131b",
        "foreground": "#f0f4fc",
        "keywords": "#c084fc",
        "functions": "#60a5fa",
        "strings": "#4ade80",
        "numbers": "#fb923c",
        "comments": "#607090",
        "types": "#38bdf8",
        "operators": "#818cf8",
        "preprocessor": "#f87171",
        "current_line": "#18204030",
        "selection": "#305880"
    }
}

EXT_TO_LANG = {
    ".py": "python",
    ".pyw": "python",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".cs": "csharp",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".bat": "batch",
    ".cmd": "batch",
    ".ps1": "powershell",
    ".qml": "qml",
    ".toml": "toml",
    ".ini": "ini",
    ".txt": "text"
}

STATE_NONE = 0
STATE_PY_TRIPLE_DOUBLE = 1
STATE_PY_TRIPLE_SINGLE = 2
STATE_C_BLOCK_COMMENT = 3
STATE_HTML_COMMENT = 4

# Standard Group Indices:
# 1: comment
# 2: string
# 3: keyword
# 4: function / identifier
# 5: number
# 6: type
# 7: preprocessor / decorator

class MultiLanguageHighlighter(QSyntaxHighlighter):
    def __init__(self, parent_document=None, theme_name="obsidian"):
        super().__init__(parent_document)
        self.theme_name = theme_name if theme_name in THEMES else "obsidian"
        self.current_theme = THEMES[self.theme_name]
        self.file_path = ""
        self.language = "python"
        self.formats = {}
        self.unified_regex = None
        self._init_formats()
        self._build_language_regex("python")

    def _init_formats(self):
        self.formats.clear()

        def make_fmt(color_hex, bold=False, italic=False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color_hex))
            if bold:
                fmt.setFontWeight(QFont.Bold)
            if italic:
                fmt.setFontItalic(True)
            return fmt

        t = self.current_theme
        self.formats["keyword"] = make_fmt(t["keywords"], bold=False)
        self.formats["function"] = make_fmt(t["functions"])
        self.formats["string"] = make_fmt(t["strings"])
        self.formats["number"] = make_fmt(t["numbers"])
        self.formats["comment"] = make_fmt(t["comments"], italic=True)
        self.formats["type"] = make_fmt(t["types"])
        self.formats["operator"] = make_fmt(t["operators"])
        self.formats["preprocessor"] = make_fmt(t["preprocessor"])

    def set_theme(self, theme_name):
        normalized = theme_name.lower()
        if normalized in THEMES and normalized != self.theme_name:
            self.theme_name = normalized
            self.current_theme = THEMES[normalized]
            self._init_formats()
            if self.document():
                self.rehighlight()

    def set_language_for_file(self, file_path, explicit_lang=None, force_rehighlight=True):
        self.file_path = file_path or ""
        ext = os.path.splitext(self.file_path)[1].lower() if self.file_path else ""
        new_lang = EXT_TO_LANG.get(ext, None)
        if not new_lang and explicit_lang:
            new_lang = explicit_lang.lower()
        if not new_lang:
            new_lang = "text"

        lang_changed = (new_lang != self.language or self.unified_regex is None)
        if lang_changed:
            self.language = new_lang
            self._build_language_regex(new_lang)

        if (force_rehighlight or lang_changed) and self.document():
            self.rehighlight()

    def _build_language_regex(self, lang):
        if lang == "text" or lang == "binary" or lang == "plain":
            self.unified_regex = None
            return

        # 1. Python
        if lang == "python":
            kw = (
                r"\b(?:def|class|return|import|from|if|else|elif|while|for|try|except|finally|"
                r"with|as|pass|break|continue|yield|lambda|global|nonlocal|raise|assert|"
                r"async|await|None|True|False|is|in|not|and|or)\b"
            )
            pattern = (
                r"(#.*)|"                                         # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                rf"({kw})|"                                       # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+(?:\.\d+)?\b)|"                          # 5: number
                r"(\b(?:self|cls|int|str|float|list|dict|set|tuple|bool|bytes)\b)|" # 6: type
                r"(@[A-Za-z0-9_]+)"                              # 7: preprocessor/decorator
            )
            self.unified_regex = QRegularExpression(pattern)

        # 2. C / C++ / C# / Java
        elif lang in ("c", "cpp", "csharp", "java"):
            kw = (
                r"\b(?:int|float|double|char|void|long|short|unsigned|signed|bool|string|String|"
                r"struct|class|union|enum|typedef|auto|const|static|extern|register|volatile|inline|"
                r"virtual|override|public|private|protected|friend|namespace|using|template|typename|"
                r"new|delete|if|else|switch|case|default|while|do|for|break|continue|return|goto|"
                r"try|catch|throw|sizeof|decltype|constexpr|nullptr|this|package|import|interface|"
                r"extends|implements|abstract|final|finally|synchronized|native|transient|var|async|await)\b"
            )
            types = (
                r"\b(?:string|String|std|vector|map|set|pair|unordered_map|unordered_set|queue|stack|"
                r"size_t|int8_t|int16_t|int32_t|int64_t|uint8_t|uint16_t|uint32_t|uint64_t|"
                r"cout|cin|endl|cerr|printf|scanf|malloc|free|memcpy|memset|NULL|List|Dictionary|"
                r"ArrayList|HashMap|HashSet|System|Console|Object|Boolean|Integer|Double|"
                r"MonoBehaviour|ScriptableObject|GameObject|Transform|RectTransform|Component|"
                r"Vector2|Vector3|Vector4|Quaternion|Matrix4x4|Color|Color32|Mathf|Bounds|Rect|"
                r"Ray|RaycastHit|RaycastHit2D|Rigidbody|Rigidbody2D|Collider|Collider2D|BoxCollider|"
                r"Camera|Light|AudioSource|AudioClip|Renderer|MeshRenderer|MeshFilter|Material|Shader|"
                r"Texture|Texture2D|Sprite|SpriteRenderer|Canvas|Time|Input|Debug)\b"
            )
            pattern = (
                r"(//.*)|"                                        # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                rf"({kw})|"                                       # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+(?:\.\d+)?[fFlLuU]?\b)|"                  # 5: number
                rf"({types})|"                                    # 6: type
                r"(#[a-zA-Z_]\w*)"                                # 7: preprocessor
            )
            self.unified_regex = QRegularExpression(pattern)

        # 3. JavaScript / TypeScript / QML
        elif lang in ("javascript", "typescript", "qml"):
            kw = (
                r"\b(?:function|const|let|var|if|else|while|for|do|switch|case|default|break|"
                r"continue|return|try|catch|finally|throw|class|extends|super|this|new|"
                r"import|export|from|as|default|async|await|yield|typeof|instanceof|void|"
                r"delete|null|undefined|true|false|in|of|interface|type|enum|implements|"
                r"public|private|protected|readonly|static|declare|property|signal|alias|"
                r"Component|Item|Rectangle|Text|ListView|MouseArea|TapHandler|ColumnLayout|"
                r"RowLayout|GridLayout|ScrollView|Window|Popup|Timer|Canvas|Flickable|Repeater|"
                r"WheelHandler|DragHandler|ScrollBar|ToolTip|Action|FileDialog|FolderDialog|"
                r"Loader|State|Transition|NumberAnimation|PropertyAnimation|SequentialAnimation|"
                r"ParallelAnimation|Connections|Binding|QtObject|FontMetrics|TextMetrics|"
                r"ListModel|ListElement|DoubleValidator|IntValidator|RegExpValidator|Shortcut|"
                r"SplitView|SplitHandle|StackView|SwipeView|TabBar|TabButton|ToolBar|ToolButton|"
                r"Button|CheckBox|RadioButton|Switch|Slider|ProgressBar|BusyIndicator)\b"
            )
            types = (
                r"\b(?:string|number|boolean|any|unknown|never|void|object|Promise|Array|Record|"
                r"Map|Set|String|Number|Boolean|Object|Math|JSON|Date|RegExp|console|document|window|"
                r"int|real|double|bool|url|color|var|point|size|rect|font|vector2d|vector3d|vector4d|matrix4x4|Qt)\b"
            )
            pattern = (
                r"(//.*)|"                                        # 1: comment
                r"(\"[^\"]*\"|'[^']*'|`[^`]*`)|"                  # 2: string
                rf"({kw})|"                                       # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*[\(:]))|"       # 4: function
                r"(\b\d+(?:\.\d+)?\b)|"                          # 5: number
                rf"({types})|"                                    # 6: type
                r"(@[A-Za-z0-9_]+)"                              # 7: decorator
            )
            self.unified_regex = QRegularExpression(pattern)

        # 4. Rust
        elif lang == "rust":
            kw = (
                r"\b(?:fn|let|mut|if|else|while|loop|for|in|match|return|break|continue|"
                r"struct|enum|trait|impl|type|pub|mod|use|as|crate|super|self|Self|"
                r"const|static|unsafe|async|await|dyn|where|true|false|Some|None|Ok|Err|"
                r"i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize|f32|f64|bool|char|str|String|Vec)\b"
            )
            pattern = (
                r"(//.*)|"                                        # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                rf"({kw})|"                                       # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*[\(!]))|"       # 4: function
                r"(\b\d+(?:\.\d+)?\b)|"                          # 5: number
                r"(\b(?:Option|Result|String|Vec|Box|Rc|Arc)\b)|" # 6: type
                r"(#!?\[.*?\])"                                   # 7: preprocessor
            )
            self.unified_regex = QRegularExpression(pattern)

        # 5. Go
        elif lang == "go":
            kw = (
                r"\b(?:func|var|const|type|struct|interface|package|import|return|if|else|"
                r"for|range|switch|case|default|select|go|defer|chan|map|make|new|len|cap|"
                r"append|true|false|nil|iota|int|int64|float64|string|bool|byte|error)\b"
            )
            pattern = (
                r"(//.*)|"                                        # 1: comment
                r"(\"[^\"]*\"|`[^`]*`|'[^']*')|"                  # 2: string
                rf"({kw})|"                                       # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+(?:\.\d+)?\b)"                            # 5: number
            )
            self.unified_regex = QRegularExpression(pattern)

        # 6. HTML / XML
        elif lang in ("html", "xml"):
            pattern = (
                r"(<!--.*?-->)|"                                  # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                r"(</?[a-zA-Z0-9_-]+)|"                           # 3: keyword (tag)
                r"(\b[a-zA-Z0-9_-]+(?=\=))|"                      # 4: attribute
                r"(\b\d+\b)|"                                     # 5: number
                r"(&[a-zA-Z0-9#]+;)|"                             # 6: entity
                r"(<!DOCTYPE.*?>)"                                # 7: doctype
            )
            self.unified_regex = QRegularExpression(pattern)

        # 7. CSS / SCSS
        elif lang in ("css", "scss"):
            pattern = (
                r"(/\*.*?\*/)|"                                   # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                r"(\b[a-zA-Z0-9_-]+(?=\s*:))|"                    # 3: property (keyword)
                r"(#[a-zA-Z0-9_-]+|\.[a-zA-Z0-9_-]+)|"            # 4: selector (function)
                r"(\b\d+(?:px|em|rem|%|vh|vw|s|ms|pt)?\b)"        # 5: number
            )
            self.unified_regex = QRegularExpression(pattern)

        # 8. JSON / YAML / TOML
        elif lang in ("json", "yaml", "toml"):
            pattern = (
                r"(#.*)|"                                         # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                r"(\b(?:true|false|null)\b)|"                     # 3: keyword
                r"(\"[^\"]+\"\s*(?=:))|"                          # 4: key
                r"(\b\d+(?:\.\d+)?\b)"                            # 5: number
            )
            self.unified_regex = QRegularExpression(pattern)

        # 9. SQL
        elif lang == "sql":
            kw = (
                r"\b(?:SELECT|FROM|WHERE|INSERT|INTO|UPDATE|DELETE|JOIN|LEFT|RIGHT|INNER|OUTER|"
                r"ON|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|CREATE|TABLE|DATABASE|DROP|ALTER|"
                r"INDEX|VIEW|PRIMARY|KEY|FOREIGN|REFERENCES|NOT|NULL|DEFAULT|AND|OR|IN|"
                r"LIKE|IS|AS|UNION|ALL|DISTINCT|COUNT|SUM|AVG|MIN|MAX|VARCHAR|INT|TEXT|BOOLEAN)\b"
            )
            pattern = (
                r"(--.*)|"                                        # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                rf"({kw})|"                                       # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+(?:\.\d+)?\b)"                            # 5: number
            )
            self.unified_regex = QRegularExpression(pattern, QRegularExpression.CaseInsensitiveOption)

        # 10. Bash / Shell / PowerShell
        elif lang in ("bash", "powershell", "batch"):
            kw = r"\b(?:if|else|elif|fi|for|in|while|do|done|case|esac|function|echo|exit|set|export)\b"
            pattern = (
                r"((?:#|::|REM\s).*)|"                            # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                rf"({kw})|"                                       # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+\b)|"                                     # 5: number
                r"(\$[a-zA-Z0-9_]+|\%[a-zA-Z0-9_]+\%)"           # 6: variable
            )
            self.unified_regex = QRegularExpression(pattern)

        # 11. Markdown
        elif lang == "markdown":
            pattern = (
                r"(<!--.*?-->)|"                                  # 1: comment
                r"(`[^`]*`)|"                                     # 2: inline code (string)
                r"(^#+.*)|"                                       # 3: headers (keyword)
                r"(\[.*?\]\(.*?\))|"                              # 4: link (func)
                r"(\b\d+\b)|"                                     # 5: number
                r"(\*\*.*?\*\*|\*.*?\*)"                          # 6: bold/italic
            )
            self.unified_regex = QRegularExpression(pattern)

        # Fallback Generic
        else:
            pattern = (
                r"((?:#|//).*)|"                                  # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                r"(\b(?:function|class|return|if|else|for|while)\b)|" # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+\b)"                                      # 5: number
            )
            self.unified_regex = QRegularExpression(pattern)

    def highlightBlock(self, text):
        if not text or not self.unified_regex or self.language in ("text", "binary", "plain"):
            self.setCurrentBlockState(STATE_NONE)
            return

        state = self.previousBlockState()
        if state <= 0:
            state = STATE_NONE

        offset = 0

        # 1. Handle incoming multiline construct state from previous block
        if state == STATE_PY_TRIPLE_DOUBLE:
            end_idx = text.find('"""')
            if end_idx == -1:
                self.setFormat(0, len(text), self.formats["comment"])
                self.setCurrentBlockState(STATE_PY_TRIPLE_DOUBLE)
                return
            else:
                self.setFormat(0, end_idx + 3, self.formats["comment"])
                offset = end_idx + 3
                state = STATE_NONE

        elif state == STATE_PY_TRIPLE_SINGLE:
            end_idx = text.find("'''")
            if end_idx == -1:
                self.setFormat(0, len(text), self.formats["comment"])
                self.setCurrentBlockState(STATE_PY_TRIPLE_SINGLE)
                return
            else:
                self.setFormat(0, end_idx + 3, self.formats["comment"])
                offset = end_idx + 3
                state = STATE_NONE

        elif state == STATE_C_BLOCK_COMMENT:
            end_idx = text.find("*/")
            if end_idx == -1:
                self.setFormat(0, len(text), self.formats["comment"])
                self.setCurrentBlockState(STATE_C_BLOCK_COMMENT)
                return
            else:
                self.setFormat(0, end_idx + 2, self.formats["comment"])
                offset = end_idx + 2
                state = STATE_NONE

        elif state == STATE_HTML_COMMENT:
            end_idx = text.find("-->")
            if end_idx == -1:
                self.setFormat(0, len(text), self.formats["comment"])
                self.setCurrentBlockState(STATE_HTML_COMMENT)
                return
            else:
                self.setFormat(0, end_idx + 3, self.formats["comment"])
                offset = end_idx + 3
                state = STATE_NONE

        # Fast path for line comments (strictly matching language syntax)
        rem_text = text[offset:]
        s_text = rem_text.lstrip()
        is_comment = False
        if self.language in ("python", "bash", "powershell", "yaml", "toml") and s_text.startswith("#"):
            is_comment = True
        elif self.language in ("c", "cpp", "csharp", "java", "javascript", "typescript", "qml", "rust", "go", "css", "scss") and s_text.startswith("//"):
            is_comment = True
        elif self.language == "sql" and s_text.startswith("--"):
            is_comment = True

        if is_comment:
            self.setFormat(offset, len(rem_text), self.formats["comment"])
            self.setCurrentBlockState(STATE_NONE)
            return

        # 2. Check for newly opened multiline construct in current line
        if self.language == "python":
            td_idx = rem_text.find('"""')
            ts_idx = rem_text.find("'''")
            if td_idx != -1 and (ts_idx == -1 or td_idx < ts_idx):
                close_idx = rem_text.find('"""', td_idx + 3)
                if close_idx == -1:
                    self._highlight_range(text, offset, offset + td_idx)
                    self.setFormat(offset + td_idx, len(rem_text) - td_idx, self.formats["comment"])
                    self.setCurrentBlockState(STATE_PY_TRIPLE_DOUBLE)
                    return
            elif ts_idx != -1:
                close_idx = rem_text.find("'''", ts_idx + 3)
                if close_idx == -1:
                    self._highlight_range(text, offset, offset + ts_idx)
                    self.setFormat(offset + ts_idx, len(rem_text) - ts_idx, self.formats["comment"])
                    self.setCurrentBlockState(STATE_PY_TRIPLE_SINGLE)
                    return

        elif self.language in ("c", "cpp", "csharp", "java", "javascript", "typescript", "qml", "rust", "go", "css", "scss"):
            c_idx = rem_text.find("/*")
            if c_idx != -1:
                close_idx = rem_text.find("*/", c_idx + 2)
                if close_idx == -1:
                    self._highlight_range(text, offset, offset + c_idx)
                    self.setFormat(offset + c_idx, len(rem_text) - c_idx, self.formats["comment"])
                    self.setCurrentBlockState(STATE_C_BLOCK_COMMENT)
                    return

        elif self.language in ("html", "xml"):
            h_idx = rem_text.find("<!--")
            if h_idx != -1:
                close_idx = rem_text.find("-->", h_idx + 4)
                if close_idx == -1:
                    self._highlight_range(text, offset, offset + h_idx)
                    self.setFormat(offset + h_idx, len(rem_text) - h_idx, self.formats["comment"])
                    self.setCurrentBlockState(STATE_HTML_COMMENT)
                    return

        self.setCurrentBlockState(STATE_NONE)
        self._highlight_range(text, offset, len(text))

    def _highlight_range(self, full_text, start_pos, end_pos):
        if end_pos <= start_pos or not self.unified_regex:
            return
        sub_str = full_text[start_pos:end_pos]
        it = self.unified_regex.globalMatch(sub_str)
        fmt_kw = self.formats.get("keyword")
        fmt_str = self.formats.get("string")
        fmt_com = self.formats.get("comment")
        fmt_fn = self.formats.get("function")
        fmt_num = self.formats.get("number")
        fmt_type = self.formats.get("type")
        fmt_prep = self.formats.get("preprocessor")
        set_fmt = self.setFormat

        while it.hasNext():
            m = it.next()
            start = start_pos + m.capturedStart()
            length = m.capturedLength()

            if m.capturedStart(1) != -1 and fmt_com:
                set_fmt(start, length, fmt_com)
            elif m.capturedStart(2) != -1 and fmt_str:
                set_fmt(start, length, fmt_str)
            elif m.capturedStart(3) != -1 and fmt_kw:
                set_fmt(start, length, fmt_kw)
            elif m.capturedStart(4) != -1 and fmt_fn:
                set_fmt(start, length, fmt_fn)
            elif m.capturedStart(5) != -1 and fmt_num:
                set_fmt(start, length, fmt_num)
            elif m.capturedStart(6) != -1 and fmt_type:
                set_fmt(start, length, fmt_type)
            elif m.capturedStart(7) != -1 and fmt_prep:
                set_fmt(start, length, fmt_prep)
