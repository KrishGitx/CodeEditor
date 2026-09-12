"""
HighlighterEngine.py - Multi-language syntax highlighting engine for PySide6 QTextDocument
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


class MultiLanguageHighlighter(QSyntaxHighlighter):
    """
    High-performance syntax highlighter capable of adapting to any file extension
    dynamically, with support for Python, C, C++, C#, Java, JS, TS, JSX, TSX,
    Go, Rust, PHP, HTML, CSS, SCSS, JSON, XML, YAML, Markdown, SQL, Shell, Batch,
    PowerShell, QML, etc.
    """

    def __init__(self, parent_document, theme_name="obsidian"):
        super().__init__(parent_document)
        self.theme_name = theme_name if theme_name in THEMES else "obsidian"
        self.current_theme = THEMES[self.theme_name]
        self.file_path = ""
        self.language = "python"
        self.rules = []
        self.formats = {}
        self._init_formats()
        self.set_language_for_file("main.py")

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
        self.formats["keyword"] = make_fmt(t["keywords"], bold=True)
        self.formats["function"] = make_fmt(t["functions"])
        self.formats["string"] = make_fmt(t["strings"])
        self.formats["number"] = make_fmt(t["numbers"])
        self.formats["comment"] = make_fmt(t["comments"], italic=True)
        self.formats["type"] = make_fmt(t["types"])
        self.formats["operator"] = make_fmt(t["operators"])
        self.formats["preprocessor"] = make_fmt(t["preprocessor"])

    def set_theme(self, theme_name):
        # Normalize theme name to lowercase for lookup
        normalized = theme_name.lower()
        if normalized in THEMES and normalized != self.theme_name:
            self.theme_name = normalized
            self.current_theme = THEMES[normalized]
            self._init_formats()
            self._setup_rules()
            self.rehighlight()

    def set_language_for_file(self, file_path):
        self.file_path = file_path or ""
        ext = os.path.splitext(self.file_path)[1].lower()

        ext_to_lang = {
            ".py": "python",
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
        self.language = ext_to_lang.get(ext, "text")
        self._setup_rules()
        self.rehighlight()

    def _setup_rules(self):
        self.rules.clear()
        lang = self.language

        if lang == "text":
            return

        # Python rules
        if lang == "python":
            keywords = [
                r"\b(def|class|return|import|from|if|else|elif|while|for|try|except|finally|"
                r"with|as|pass|break|continue|yield|lambda|global|nonlocal|raise|assert|"
                r"async|await|None|True|False|is|in|not|and|or)\b"
            ]
            self.rules.append((QRegularExpression(r"#.*"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'""".*?"""|\'\'\'.*?\'\'\''), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|\'.*?\')'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), self.formats["number"]))
            self.rules.append((QRegularExpression(keywords[0]), self.formats["keyword"]))
            self.rules.append((QRegularExpression(r"\b[A-Za-z0-9_]+(?=\s*\()"), self.formats["function"]))
            self.rules.append((QRegularExpression(r"@[A-Za-z0-9_]+"), self.formats["preprocessor"]))

        # C / C++ / C# / Java rules
        elif lang in ("c", "cpp", "csharp", "java"):
            keywords = [
                r"\b(int|float|double|char|void|long|short|unsigned|signed|bool|struct|class|union|"
                r"enum|typedef|auto|const|static|extern|register|volatile|inline|virtual|override|"
                r"public|private|protected|friend|namespace|using|template|typename|new|delete|"
                r"if|else|switch|case|default|while|do|for|break|continue|return|goto|try|catch|"
                r"throw|sizeof|decltype|constexpr|nullptr|this|package|import|interface|extends|"
                r"implements|abstract|final|finally|synchronized|native|transient|var|async|await)\b"
            ]
            self.rules.append((QRegularExpression(r"//.*"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r"/\*.*?\*/"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|\'.*?\')'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"#[a-zA-Z_]\w*"), self.formats["preprocessor"]))
            self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?[fFlLuU]?\b"), self.formats["number"]))
            self.rules.append((QRegularExpression(keywords[0]), self.formats["keyword"]))
            self.rules.append((QRegularExpression(r"\b[A-Za-z0-9_]+(?=\s*\()"), self.formats["function"]))

        # JavaScript / TypeScript / QML rules
        elif lang in ("javascript", "typescript", "qml"):
            keywords = [
                r"\b(function|const|let|var|if|else|while|for|do|switch|case|default|break|"
                r"continue|return|try|catch|finally|throw|class|extends|super|this|new|"
                r"import|export|from|as|default|async|await|yield|typeof|instanceof|void|"
                r"delete|null|undefined|true|false|in|of|interface|type|enum|implements|"
                r"public|private|protected|readonly|static|declare|property|signal|alias|"
                r"Component|Item|Rectangle|Text|ListView|MouseArea|TapHandler|ColumnLayout|"
                r"RowLayout|GridLayout|ScrollView|Window|Popup|Timer)\b"
            ]
            self.rules.append((QRegularExpression(r"//.*"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r"/\*.*?\*/"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|\'.*?\'|`.*?`)'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), self.formats["number"]))
            self.rules.append((QRegularExpression(keywords[0]), self.formats["keyword"]))
            self.rules.append((QRegularExpression(r"\b[A-Za-z0-9_]+(?=\s*[\(:])"), self.formats["function"]))

        # Rust rules
        elif lang == "rust":
            keywords = [
                r"\b(fn|let|mut|if|else|while|loop|for|in|match|return|break|continue|"
                r"struct|enum|trait|impl|type|pub|mod|use|as|crate|super|self|Self|"
                r"const|static|unsafe|async|await|dyn|where|true|false|Some|None|Ok|Err|"
                r"i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize|f32|f64|bool|char|str|String|Vec)\b"
            ]
            self.rules.append((QRegularExpression(r"//.*"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|\'.*?\')'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"#!?\[.*?\]"), self.formats["preprocessor"]))
            self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), self.formats["number"]))
            self.rules.append((QRegularExpression(keywords[0]), self.formats["keyword"]))
            self.rules.append((QRegularExpression(r"\b[A-Za-z0-9_]+(?=\s*[\(!])"), self.formats["function"]))

        # Go rules
        elif lang == "go":
            keywords = [
                r"\b(func|var|const|type|struct|interface|package|import|return|if|else|"
                r"for|range|switch|case|default|select|go|defer|chan|map|make|new|len|cap|"
                r"append|true|false|nil|iota|int|int64|float64|string|bool|byte|error)\b"
            ]
            self.rules.append((QRegularExpression(r"//.*"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|`.*?`|\'.*?\')'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), self.formats["number"]))
            self.rules.append((QRegularExpression(keywords[0]), self.formats["keyword"]))
            self.rules.append((QRegularExpression(r"\b[A-Za-z0-9_]+(?=\s*\()"), self.formats["function"]))

        # HTML / XML rules
        elif lang in ("html", "xml"):
            self.rules.append((QRegularExpression(r"<!--.*?-->"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|\'.*?\')'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"<!DOCTYPE.*?>"), self.formats["preprocessor"]))
            self.rules.append((QRegularExpression(r"</?[a-zA-Z0-9_-]+"), self.formats["keyword"]))
            self.rules.append((QRegularExpression(r"\b[a-zA-Z0-9_-]+(?=\=)"), self.formats["type"]))

        # CSS / SCSS rules
        elif lang in ("css", "scss"):
            self.rules.append((QRegularExpression(r"/\*.*?\*/"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|\'.*?\')'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"#[a-zA-Z0-9_-]+|\.[a-zA-Z0-9_-]+"), self.formats["function"]))
            self.rules.append((QRegularExpression(r"\b[a-zA-Z0-9_-]+(?=\s*:)"), self.formats["keyword"]))
            self.rules.append((QRegularExpression(r":\s*[^;]+;"), self.formats["string"]))

        # JSON / YAML / TOML
        elif lang in ("json", "yaml", "toml"):
            self.rules.append((QRegularExpression(r"#.*"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|\'.*?\')'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"\b(true|false|null)\b"), self.formats["keyword"]))
            self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), self.formats["number"]))
            self.rules.append((QRegularExpression(r'"[^"]+"\s*(?=:)'), self.formats["type"]))

        # SQL
        elif lang == "sql":
            keywords = [
                r"\b(SELECT|FROM|WHERE|INSERT|INTO|UPDATE|DELETE|JOIN|LEFT|RIGHT|INNER|OUTER|"
                r"ON|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|CREATE|TABLE|DATABASE|DROP|ALTER|"
                r"INDEX|VIEW|PRIMARY|KEY|FOREIGN|REFERENCES|NOT|NULL|DEFAULT|AND|OR|IN|"
                r"LIKE|IS|AS|UNION|ALL|DISTINCT|COUNT|SUM|AVG|MIN|MAX|VARCHAR|INT|TEXT|BOOLEAN)\b"
            ]
            self.rules.append((QRegularExpression(r"--.*"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|\'.*?\')'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), self.formats["number"]))
            self.rules.append((QRegularExpression(keywords[0], QRegularExpression.CaseInsensitiveOption), self.formats["keyword"]))

        # Shell / Bash / PowerShell / Batch
        elif lang in ("bash", "powershell", "batch"):
            self.rules.append((QRegularExpression(r"(#|::|REM ).*"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|\'.*?\')'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"\$[a-zA-Z0-9_]+|\%[a-zA-Z0-9_]+\%"), self.formats["type"]))
            self.rules.append((QRegularExpression(r"\b(if|else|elif|fi|for|in|while|do|done|case|esac|function|echo|exit|set|export)\b"), self.formats["keyword"]))

        # Markdown
        elif lang == "markdown":
            self.rules.append((QRegularExpression(r"^#+.*"), self.formats["keyword"]))
            self.rules.append((QRegularExpression(r"`.*?`"), self.formats["string"]))
            self.rules.append((QRegularExpression(r"\*\*.*?\*\*|\*.*?\*"), self.formats["type"]))
            self.rules.append((QRegularExpression(r"\[.*?\]\(.*?\)"), self.formats["function"]))

        # Generic fallback
        else:
            self.rules.append((QRegularExpression(r"(#|//).*"), self.formats["comment"]))
            self.rules.append((QRegularExpression(r'(".*?"|\'.*?\')'), self.formats["string"]))
            self.rules.append((QRegularExpression(r"\b\d+\b"), self.formats["number"]))

    def highlightBlock(self, text):
        for pattern, text_format in self.rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), text_format)
