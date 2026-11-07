"""
HighlighterEngine.py - High-Performance, Fully Accurate Multi-Language Syntax Highlighting Engine
Uses unified single-pass regular expressions with fast integer group indices, comment fast-paths,
and standard Qt QSyntaxHighlighter block-state propagation for multiline docstrings and comments.
Supports 25+ programming languages, file types, and dynamic color themes.
"""

from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QTimer
import os
import re
import json
import collections

def load_themes():
    themes = {}
    theme_dirs = [
        os.path.join(os.path.dirname(__file__), "themes"),
        os.path.join(os.path.expanduser("~"), ".pod_studio", "themes"),
        os.path.join(os.path.expanduser("~"), ".dgx_studio", "themes")
    ]
    for tdir in theme_dirs:
        if not os.path.isdir(tdir):
            continue
        try:
            for fname in os.listdir(tdir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(tdir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    tid = str(data.get("id", os.path.splitext(fname)[0])).lower()
                    theme_entry = {
                        "background": data.get("background", data.get("bgEditor", "#12141a")),
                        "foreground": data.get("foreground", data.get("textPrimary", "#e8ecf4")),
                        "keywords": data.get("keywords", data.get("synKeyword", "#c678dd")),
                        "functions": data.get("functions", data.get("synFunction", "#61afef")),
                        "strings": data.get("strings", data.get("synString", "#98c379")),
                        "numbers": data.get("numbers", data.get("synNumber", "#d19a66")),
                        "comments": data.get("comments", data.get("synComment", "#5c6478")),
                        "types": data.get("types", data.get("synType", "#e5c07b")),
                        "operators": data.get("operators", data.get("accent", "#56b6c2")),
                        "preprocessor": data.get("preprocessor", data.get("error", "#e06c75")),
                        "current_line": data.get("current_line", data.get("synCurrentLine", "#181b24")),
                        "selection": data.get("selection", data.get("synSelection", "#264f78"))
                    }
                    themes[tid] = theme_entry
                except Exception as err:
                    print(f"[HighlighterEngine] Error loading theme file {fpath}: {err}")
        except Exception as e:
            print(f"[HighlighterEngine] Error scanning theme dir {tdir}: {e}")

    # Aliases
    if "obsidian" in themes:
        themes["dark"] = themes["obsidian"]
    elif themes:
        first_theme = next(iter(themes.values()))
        themes["dark"] = first_theme
        themes["obsidian"] = first_theme
    return themes

THEMES = load_themes()

def reload_themes():
    global THEMES
    THEMES = load_themes()


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

        self.viewport_start = 0
        self.viewport_end = 150
        self.buffer_size = 60
        self.formatted_blocks = set()

        self._pending_blocks_queue = collections.deque()
        self._pending_blocks_set = set()
        self._slice_timer = QTimer()
        self._slice_timer.setInterval(12)
        self._slice_timer.timeout.connect(self._process_slice_queue)
        self._batch_slice_size = 30
        self._is_incremental_loading = False

    def attach_document(self, doc, file_path="", explicit_lang=None, visible_lines=150):
        self.file_path = file_path or ""
        ext = os.path.splitext(self.file_path)[1].lower() if self.file_path else ""
        new_lang = EXT_TO_LANG.get(ext, None)
        if not new_lang and explicit_lang:
            new_lang = explicit_lang.lower()
        if not new_lang:
            new_lang = "text"

        self.language = new_lang
        self._build_language_regex(new_lang)

        self._slice_timer.stop()
        self._pending_blocks_queue.clear()
        self.formatted_blocks.clear()

        total_blocks = doc.blockCount() if doc else 0
        if total_blocks <= 1000:
            self.viewport_start = 0
            self.viewport_end = total_blocks
        else:
            self.viewport_start = 0
            self.viewport_end = min(total_blocks, visible_lines + self.buffer_size)

        self.setDocument(doc)
        print("[Timing] First visible syntax highlight complete", flush=True)

    def attach_document_incremental(self, doc, file_path="", explicit_lang=None):
        self.attach_document(doc, file_path, explicit_lang)

    def update_visible_range(self, start_line, end_line):
        doc = self.document()
        if not doc or self.language in ("text", "binary", "plain") or not self.unified_regex:
            return

        total_blocks = doc.blockCount()
        if total_blocks <= 1000:
            self.viewport_start = 0
            self.viewport_end = total_blocks
            return

        w_start = min(total_blocks - 1, max(0, start_line - self.buffer_size))
        w_end = min(total_blocks - 1, max(w_start, end_line + self.buffer_size + 40))

        self.viewport_start = w_start
        self.viewport_end = w_end

        new_blocks = [b for b in range(w_start, w_end + 1) if b not in self.formatted_blocks]
        if not new_blocks:
            return

        vp_blocks = [b for b in new_blocks if start_line <= b <= end_line]
        buf_blocks = [b for b in new_blocks if b < start_line or b > end_line]
        sorted_blocks = vp_blocks + buf_blocks

        for b in sorted_blocks:
            if b not in self._pending_blocks_set:
                self._pending_blocks_set.add(b)
                self._pending_blocks_queue.append(b)

        if not self._slice_timer.isActive():
            self._slice_timer.start()

    def _process_slice_queue(self):
        doc = self.document()
        if not doc or not self._pending_blocks_queue:
            self._pending_blocks_set.clear()
            self._slice_timer.stop()
            return

        count = 0
        while self._pending_blocks_queue and count < self._batch_slice_size:
            b_num = self._pending_blocks_queue.popleft()
            self._pending_blocks_set.discard(b_num)
            if b_num not in self.formatted_blocks:
                block = doc.findBlockByNumber(b_num)
                if block.isValid():
                    self.rehighlightBlock(block)
                count += 1

        if not self._pending_blocks_queue:
            self._pending_blocks_set.clear()
            self._slice_timer.stop()

    def set_language_for_file(self, file_path, explicit_lang=None, force_rehighlight=True):
        self.file_path = file_path or ""
        ext = os.path.splitext(self.file_path)[1].lower() if self.file_path else ""
        new_lang = EXT_TO_LANG.get(ext, None)
        if not new_lang and explicit_lang:
            new_lang = explicit_lang.lower().strip()
        if not new_lang:
            new_lang = "text"

        # Alias normalization
        if new_lang in ("shell", "sh", "bash", "powershell", "bat", "cmd", "batch"):
            new_lang = "bash" if new_lang in ("shell", "sh", "bash") else new_lang
        elif new_lang in ("plain", "plaintext"):
            new_lang = "text"
        elif new_lang in ("js", "javascript"):
            new_lang = "javascript"
        elif new_lang in ("ts", "typescript"):
            new_lang = "typescript"
        elif new_lang in ("py", "python"):
            new_lang = "python"
        elif new_lang in ("c++", "cpp"):
            new_lang = "cpp"

        lang_changed = (new_lang != self.language or self.unified_regex is None)
        if lang_changed or force_rehighlight:
            self.language = new_lang
            self._build_language_regex(new_lang)
            self._slice_timer.stop()
            self._pending_blocks_queue.clear()
            self.formatted_blocks.clear()

        doc = self.document()
        if doc and (force_rehighlight or lang_changed):
            total_blocks = doc.blockCount()
            self.viewport_start = 0
            self.viewport_end = min(total_blocks, 150 + self.buffer_size)
            self.rehighlight()

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
        self.fmts_list = [
            None,
            self.formats["comment"],
            self.formats["string"],
            self.formats["keyword"],
            self.formats["function"],
            self.formats["number"],
            self.formats["type"],
            self.formats["preprocessor"]
        ]

    def set_theme(self, theme_name):
        normalized = theme_name.lower()
        if normalized in THEMES and normalized != self.theme_name:
            self.theme_name = normalized
            self.current_theme = THEMES[normalized]
            self._init_formats()
            if self.document():
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
            self.unified_regex = re.compile(pattern)

        # 2. C / C++ / C# / Java
        elif lang in ("c", "cpp", "csharp", "java"):
            kw = (
                r"\b(?:struct|class|union|enum|typedef|const|static|extern|register|volatile|inline|"
                r"virtual|override|public|private|protected|friend|namespace|using|template|typename|"
                r"new|delete|if|else|switch|case|default|while|do|for|break|continue|return|goto|"
                r"try|catch|throw|sizeof|decltype|constexpr|nullptr|this|package|import|interface|"
                r"extends|implements|abstract|final|finally|synchronized|native|transient|var|async|await)\b"
            )
            types = (
                r"\b(?:int|float|double|char|void|long|short|unsigned|signed|bool|string|String|auto|"
                r"std|vector|map|set|pair|unordered_map|unordered_set|queue|stack|"
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
            self.unified_regex = re.compile(pattern)

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
            self.unified_regex = re.compile(pattern)

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
            self.unified_regex = re.compile(pattern)

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
            self.unified_regex = re.compile(pattern)

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
            self.unified_regex = re.compile(pattern)

        # 7. CSS / SCSS
        elif lang in ("css", "scss"):
            pattern = (
                r"(/\*.*?\*/)|"                                   # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                r"(\b[a-zA-Z0-9_-]+(?=\s*:))|"                    # 3: property (keyword)
                r"(#[a-zA-Z0-9_-]+|\.[a-zA-Z0-9_-]+)|"            # 4: selector (function)
                r"(\b\d+(?:px|em|rem|%|vh|vw|s|ms|pt)?\b)"        # 5: number
            )
            self.unified_regex = re.compile(pattern)

        # 8. JSON / YAML / TOML
        elif lang in ("json", "yaml", "toml"):
            pattern = (
                r"(#.*)|"                                         # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                r"(\b(?:true|false|null)\b)|"                     # 3: keyword
                r"(\"[^\"]+\"\s*(?=:))|"                          # 4: key
                r"(\b\d+(?:\.\d+)?\b)"                            # 5: number
            )
            self.unified_regex = re.compile(pattern)

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
            self.unified_regex = re.compile(pattern, re.IGNORECASE)

        # 10. Bash / Shell / PowerShell
        elif lang in ("bash", "powershell", "batch", "shell"):
            kw = r"\b(?:if|else|elif|fi|for|in|while|do|done|case|esac|function|echo|exit|set|export)\b"
            pattern = (
                r"((?:#|::|REM\s).*)|"                            # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                rf"({kw})|"                                       # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+\b)|"                                     # 5: number
                r"(\$[a-zA-Z0-9_]+|\%[a-zA-Z0-9_]+\%)"           # 6: variable
            )
            self.unified_regex = re.compile(pattern)

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
            self.unified_regex = re.compile(pattern)

        # Fallback Generic
        else:
            pattern = (
                r"((?:#|//).*)|"                                  # 1: comment
                r"(\"[^\"]*\"|'[^']*')|"                          # 2: string
                r"(\b(?:function|class|return|if|else|for|while)\b)|" # 3: keyword
                r"(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|"          # 4: function
                r"(\b\d+\b)"                                      # 5: number
            )
            self.unified_regex = re.compile(pattern)

    def highlightBlock(self, text):
        if not text or not self.unified_regex or self.language in ("text", "binary", "plain"):
            self.setCurrentBlockState(STATE_NONE)
            return

        b_num = self.currentBlock().blockNumber()
        doc = self.document()
        total_blocks = doc.blockCount() if doc else 0
        in_window = (total_blocks <= 1000) or (self.viewport_start <= b_num <= self.viewport_end)

        state = self.previousBlockState()
        if state <= 0:
            state = STATE_NONE

        offset = 0

        # 1. Handle incoming multiline construct state from previous block
        if state == STATE_PY_TRIPLE_DOUBLE:
            end_idx = text.find('"""')
            if end_idx == -1:
                if in_window:
                    self.setFormat(0, len(text), self.formats["comment"])
                    self.formatted_blocks.add(b_num)
                self.setCurrentBlockState(STATE_PY_TRIPLE_DOUBLE)
                return
            else:
                if in_window:
                    self.setFormat(0, end_idx + 3, self.formats["comment"])
                offset = end_idx + 3
                state = STATE_NONE

        elif state == STATE_PY_TRIPLE_SINGLE:
            end_idx = text.find("'''")
            if end_idx == -1:
                if in_window:
                    self.setFormat(0, len(text), self.formats["comment"])
                    self.formatted_blocks.add(b_num)
                self.setCurrentBlockState(STATE_PY_TRIPLE_SINGLE)
                return
            else:
                if in_window:
                    self.setFormat(0, end_idx + 3, self.formats["comment"])
                offset = end_idx + 3
                state = STATE_NONE

        elif state == STATE_C_BLOCK_COMMENT:
            end_idx = text.find("*/")
            if end_idx == -1:
                if in_window:
                    self.setFormat(0, len(text), self.formats["comment"])
                    self.formatted_blocks.add(b_num)
                self.setCurrentBlockState(STATE_C_BLOCK_COMMENT)
                return
            else:
                if in_window:
                    self.setFormat(0, end_idx + 2, self.formats["comment"])
                offset = end_idx + 2
                state = STATE_NONE

        elif state == STATE_HTML_COMMENT:
            end_idx = text.find("-->")
            if end_idx == -1:
                if in_window:
                    self.setFormat(0, len(text), self.formats["comment"])
                    self.formatted_blocks.add(b_num)
                self.setCurrentBlockState(STATE_HTML_COMMENT)
                return
            else:
                if in_window:
                    self.setFormat(0, end_idx + 3, self.formats["comment"])
                offset = end_idx + 3
                state = STATE_NONE

        # Fast path for line comments (strictly matching language syntax)
        rem_text = text[offset:]
        s_text = rem_text.lstrip()
        is_comment = False
        if self.language in ("python", "bash", "powershell", "yaml", "toml", "shell") and s_text.startswith("#"):
            is_comment = True
        elif self.language in ("c", "cpp", "csharp", "java", "javascript", "typescript", "qml", "rust", "go", "css", "scss") and s_text.startswith("//"):
            is_comment = True
        elif self.language == "sql" and s_text.startswith("--"):
            is_comment = True

        if is_comment:
            if in_window:
                self.setFormat(offset, len(rem_text), self.formats["comment"])
                self.formatted_blocks.add(b_num)
            self.setCurrentBlockState(STATE_NONE)
            return

        # 2. Check for newly opened multiline construct in current line
        if self.language == "python":
            td_idx = rem_text.find('"""')
            ts_idx = rem_text.find("'''")
            if td_idx != -1 and (ts_idx == -1 or td_idx < ts_idx):
                close_idx = rem_text.find('"""', td_idx + 3)
                if close_idx == -1:
                    if in_window:
                        self._highlight_range(text, offset, offset + td_idx)
                        self.setFormat(offset + td_idx, len(rem_text) - td_idx, self.formats["comment"])
                        self.formatted_blocks.add(b_num)
                    self.setCurrentBlockState(STATE_PY_TRIPLE_DOUBLE)
                    return
            elif ts_idx != -1:
                close_idx = rem_text.find("'''", ts_idx + 3)
                if close_idx == -1:
                    if in_window:
                        self._highlight_range(text, offset, offset + ts_idx)
                        self.setFormat(offset + ts_idx, len(rem_text) - ts_idx, self.formats["comment"])
                        self.formatted_blocks.add(b_num)
                    self.setCurrentBlockState(STATE_PY_TRIPLE_SINGLE)
                    return

        elif self.language in ("c", "cpp", "csharp", "java", "javascript", "typescript", "qml", "rust", "go", "css", "scss"):
            c_idx = rem_text.find("/*")
            if c_idx != -1:
                close_idx = rem_text.find("*/", c_idx + 2)
                if close_idx == -1:
                    if in_window:
                        self._highlight_range(text, offset, offset + c_idx)
                        self.setFormat(offset + c_idx, len(rem_text) - c_idx, self.formats["comment"])
                        self.formatted_blocks.add(b_num)
                    self.setCurrentBlockState(STATE_C_BLOCK_COMMENT)
                    return

        elif self.language in ("html", "xml"):
            h_idx = rem_text.find("<!--")
            if h_idx != -1:
                close_idx = rem_text.find("-->", h_idx + 4)
                if close_idx == -1:
                    if in_window:
                        self._highlight_range(text, offset, offset + h_idx)
                        self.setFormat(offset + h_idx, len(rem_text) - h_idx, self.formats["comment"])
                        self.formatted_blocks.add(b_num)
                    self.setCurrentBlockState(STATE_HTML_COMMENT)
                    return

        self.setCurrentBlockState(STATE_NONE)
        if in_window:
            self._highlight_range(text, offset, len(text))
            self.formatted_blocks.add(b_num)

    def _highlight_range(self, full_text, start_pos, end_pos):
        if end_pos <= start_pos or not self.unified_regex:
            return
        sub_str = full_text[start_pos:end_pos]
        fmts = self.fmts_list
        set_fmt = self.setFormat

        for m in self.unified_regex.finditer(sub_str):
            idx = m.lastindex
            if idx and idx < len(fmts) and fmts[idx]:
                s_m, e_m = m.span(idx)
                set_fmt(start_pos + s_m, e_m - s_m, fmts[idx])
