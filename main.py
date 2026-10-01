import sys
import os
from pathlib import Path

# Add current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import Qt, QObject, Slot, Signal, QThread, QEvent
from PySide6.QtQuick import QQuickTextDocument
from PySide6.QtQuickControls2 import QQuickStyle
from urllib.parse import urlparse
from urllib.request import url2pathname
import subprocess
import json
import time
import re

from MusicPlayer import MusicPlayer
from HighlighterEngine import MultiLanguageHighlighter
from AIBackend import AIBackend
from TerminalBackend import TerminalBackend
from SettingsBackend import SettingsBackend


# ==============================================================================
# GLOBAL CONTEXT MENU FILTER (Blocks Native OS QMenu from Popping Up)
# ==============================================================================
class GlobalContextMenuFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.ContextMenu:
            return True  # Suppress native Windows context menu
        return super().eventFilter(obj, event)


# ==============================================================================
# 1. BACKGROUND LSP THREAD WORKER
# ==============================================================================
class LSPReaderWorker(QThread):
    message_received = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process
        self.running = True

    def run(self):
        buffer = b""
        while self.running:
            try:
                chunk = self.process.stdout.read(1)
                if not chunk:
                    if self.process.poll() is not None:
                        break
                    continue
                buffer += chunk

                if b"\r\n\r\n" in buffer:
                    header_part, remaining = buffer.split(b"\r\n\r\n", 1)
                    header_text = header_part.decode('utf-8', errors='ignore')

                    if "Content-Length" in header_text:
                        try:
                            length = int(header_text.split("Content-Length:")[1].split("\r\n")[0].strip())
                        except (IndexError, ValueError):
                            buffer = remaining
                            continue

                        while len(remaining) < length:
                            next_byte = self.process.stdout.read(1)
                            if not next_byte:
                                break
                            remaining += next_byte

                        msg_body_bytes = remaining[:length]
                        buffer = remaining[length:]

                        try:
                            response_text = msg_body_bytes.decode('utf-8').strip()
                            self.message_received.emit(json.loads(response_text))
                        except Exception as parse_error:
                            print(f"JSON Parsing failed: {parse_error}")
                    else:
                        buffer = remaining
            except Exception as e:
                self.error_occurred.emit(str(e))
                break


# ==============================================================================
# 2. LSP & CODE EDITOR BACKEND ENGINE
# ==============================================================================
class EditorBackend(QObject):
    completionsReceived = Signal(list)
    fileOpened = Signal(str, str)
    fileSaved = Signal(str, bool)
    explorerContent = Signal(list, str)
    currentLanguageChanged = Signal(str)
    diagnosticsUpdated = Signal(list)
    outputLogReceived = Signal(str, str)  # channel, text

    def __init__(self):
        super().__init__()
        self.highlighter = None
        self.lsp_process = None
        self.msg_id = 1
        self.doc_version = 1
        self.current_file = ""
        self.folder_path = os.getcwd()
        self.start_lsp_server()

    @Slot(QObject)
    def register_text_area(self, qml_text_area):
        qml_doc = qml_text_area.property("textDocument")
        if qml_doc:
            doc = qml_doc.textDocument()
            if not self.highlighter:
                self.highlighter = MultiLanguageHighlighter(doc)
            initial_path = self.current_file or "main.py"
            self.highlighter.set_language_for_file(initial_path)
            self.currentLanguageChanged.emit(self.highlighter.language)
            initial_text = qml_text_area.property("text") or ""
            self.initial_file_open(initial_path, initial_text)

    @Slot(str)
    def set_theme(self, theme_name):
        if self.highlighter:
            self.highlighter.set_theme(theme_name.lower())

    def start_lsp_server(self):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Look for pylsp in local venv or system PATH
        venv_pylsp = Path(__file__).parent / ".qtcreator" / "Python_3_14_3venv" / "Scripts" / "pylsp.exe"
        server_path = str(venv_pylsp) if venv_pylsp.exists() else "pylsp"

        try:
            self.lsp_process = subprocess.Popen(
                [server_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=False, bufsize=0, env=env
            )

            if self.lsp_process.poll() is None:
                print("LSP STARTED:", server_path)
                self.reader_thread = LSPReaderWorker(self.lsp_process)
                self.reader_thread.message_received.connect(self.handle_lsp_message)
                self.reader_thread.start()

                root_uri = Path(self.folder_path).as_uri()
                self.send_lsp_request("initialize", {
                    "processId": os.getpid(),
                    "rootUri": root_uri,
                    "capabilities": {
                        "textDocument": {
                            "completion": {
                                "completionItem": {"snippetSupport": True},
                                "contextSupport": True
                            }
                        }
                    }
                })
        except Exception as e:
            print("LSP could not be started:", e)

    def send_lsp_request(self, method, dic):
        if not self.lsp_process or self.lsp_process.poll() is not None:
            return
        try:
            js = {"jsonrpc": "2.0", "id": self.msg_id, "method": method, "params": dic}
            self.msg_id += 1
            json_string = json.dumps(js)
            header = f"Content-Length: {len(json_string)}\r\n\r\n{json_string}"
            self.lsp_process.stdin.write(header.encode('utf-8'))
            self.lsp_process.stdin.flush()
        except Exception as e:
            print("LSP request error:", e)

    def send_lsp_notification(self, method, dic):
        if not self.lsp_process or self.lsp_process.poll() is not None:
            return
        try:
            js = {"jsonrpc": "2.0", "method": method, "params": dic}
            json_string = json.dumps(js)
            header = f"Content-Length: {len(json_string)}\r\n\r\n{json_string}"
            self.lsp_process.stdin.write(header.encode('utf-8'))
            self.lsp_process.stdin.flush()
        except Exception as e:
            print("LSP notification error:", e)

    def initial_file_open(self, filepath, current_text):
        clean_path = filepath.replace("\\", "/")
        if not clean_path.startswith("file:///"):
            clean_path = "file:///" + clean_path

        open_payload = {
            "textDocument": {
                "uri": clean_path,
                "languageId": "python",
                "version": self.doc_version,
                "text": current_text
            }
        }
        self.send_lsp_notification("textDocument/didOpen", open_payload)

    @Slot(str, str)
    def notify_change(self, filepath, full_text):
        clean_path = filepath.replace("\\", "/")
        if not clean_path.startswith("file:///"):
            clean_path = "file:///" + clean_path

        self.doc_version += 1
        payload = {
            "textDocument": {"uri": clean_path, "version": self.doc_version},
            "contentChanges": [{"text": full_text}]
        }
        self.send_lsp_notification("textDocument/didChange", payload)

    @Slot(str, int, int, str)
    def request_completion(self, filepath, line, character, current_text):
        clean_path = filepath.replace("\\", "/")
        if not clean_path.startswith("file:///"):
            clean_path = "file:///" + clean_path

        completion_payload = {
            "textDocument": {"uri": clean_path},
            "position": {"line": line, "character": character}
        }
        self.send_lsp_request("textDocument/completion", completion_payload)

    def handle_lsp_message(self, response_json):
        msg_id = response_json.get("id")

        if msg_id == 1:
            self.send_lsp_notification("initialized", {})
            print("LSP INITIALIZED HANDSHAKE COMPLETE")
            return

        if "result" in response_json:
            result_data = response_json.get("result") or {}
            items_list = []

            if isinstance(result_data, dict):
                items_list = result_data.get("items") or []
            elif isinstance(result_data, list):
                items_list = result_data

            suggestions = [
                {
                    "label": item.get("label", ""),
                    "insertText": item.get("insertText", item.get("label", "")),
                    "type": item.get("kind", "")
                }
                for item in items_list
            ]
            self.completionsReceived.emit(suggestions)

    @Slot(str)
    def open_file(self, filePath):
        if filePath.startswith("file:///"):
            parsed = urlparse(filePath)
            filePath = url2pathname(parsed.path)

        clean_path = os.path.normpath(filePath)
        if not os.path.exists(clean_path):
            print("File not found:", clean_path)
            return

        self.current_file = clean_path
        try:
            with open(clean_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if self.highlighter:
                self.highlighter.set_language_for_file(clean_path)
                self.currentLanguageChanged.emit(self.highlighter.language)

            self.fileOpened.emit(clean_path, content)
        except Exception as e:
            print(f"Error opening file {clean_path}:", e)

    @Slot(str, str)
    def save_file(self, filePath, content):
        if not filePath:
            self.fileSaved.emit("", False)
            return

        # QML can pass either a normal Windows path or a file:// URL.
        if filePath.startswith("file:///"):
            parsed = urlparse(filePath)
            filePath = url2pathname(parsed.path)

        clean_path = os.path.abspath(os.path.normpath(filePath))

        try:
            # Make sure the parent directory exists for newly-created files.
            parent = os.path.dirname(clean_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            # newline="" prevents Python from unexpectedly translating
            # line endings while saving editor content.
            with open(clean_path, "w", encoding="utf-8", newline="") as f:
                f.write(content)

            self.current_file = clean_path
            self.fileSaved.emit(clean_path, True)
            print(f"File saved successfully: {clean_path}")

        except (OSError, UnicodeError) as e:
            print(f"Error saving file {clean_path}: {e}")
            self.fileSaved.emit(clean_path, False)

    @Slot(str, str, str, int, result=str)
    def format_code(self, lang_id, file_path, source_code, tab_size=4):
        if not source_code or not source_code.strip():
            return source_code

        ext = file_path.split(".")[-1].lower() if file_path and "." in file_path else ""
        lang = (lang_id or "").lower()

        # 1. JSON Formatter
        if lang == "json" or ext == "json":
            try:
                parsed = json.loads(source_code)
                return json.dumps(parsed, indent=tab_size)
            except Exception:
                return source_code

        # 2. Python Formatter (PEP8 compliant)
        if lang == "python" or ext in ("py", "pyw"):
            try:
                import autopep8
                formatted = autopep8.fix_code(source_code, options={"indent_size": tab_size})
                if formatted and formatted.strip():
                    return formatted.rstrip() + "\n"
            except Exception as e:
                print("[Formatter] autopep8 notice:", e)

        # 3. HTML / XML / SVG Formatter
        if lang in ("html", "xml", "svg") or ext in ("html", "htm", "xml", "svg"):
            try:
                lines = source_code.split("\n")
                indent = 0
                formatted_lines = []
                tab_spaces = " " * tab_size
                void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr", "!doctype"}

                for line in lines:
                    trimmed = line.strip()
                    if not trimmed:
                        formatted_lines.append("")
                        continue

                    is_closing = trimmed.startswith("</")
                    if is_closing:
                        indent = max(0, indent - 1)

                    formatted_lines.append((tab_spaces * indent) + trimmed)

                    if trimmed.startswith("<") and not is_closing and not trimmed.startswith("<!--") and not trimmed.startswith("<!"):
                        parts = trimmed[1:].split()
                        tag_name = parts[0].split(">")[0].lower() if parts else ""
                        if not trimmed.endswith("/>") and tag_name not in void_tags and "</" not in trimmed:
                            indent += 1

                return "\n".join(formatted_lines)
            except Exception:
                return source_code

        # 4. JS / TS / C / C++ / C# / Java / Rust / Go / CSS / QML Formatter
        try:
            lines = source_code.split("\n")
            indent = 0
            formatted_lines = []
            tab_spaces = " " * tab_size

            for line in lines:
                trimmed = line.strip()
                if not trimmed:
                    formatted_lines.append("")
                    continue

                clean = re.sub(r'"(\\.|[^"\\])*"', '""', trimmed)
                clean = re.sub(r"'(\\.|[^'\\])*'", "''", clean)
                clean = re.sub(r"//.*$", "", clean)

                unindent_start = bool(re.match(r"^(\}|\]|\)|else\b|catch\b|finally\b|case\b|default:)", clean))
                if unindent_start:
                    indent = max(0, indent - 1)

                formatted_lines.append((tab_spaces * indent) + trimmed)

                opens = len(re.findall(r"[\{\[\(]", clean))
                closes = len(re.findall(r"[\}\]\)]", clean))
                if unindent_start:
                    closes = max(0, closes - 1)

                indent = max(0, indent + (opens - closes))

            return "\n".join(formatted_lines)
        except Exception:
            return source_code

    @Slot(str, str, str, result=list)
    def check_diagnostics(self, file_path, source_code, lang_id=""):
        if not source_code:
            self.diagnosticsUpdated.emit([])
            return []

        problems = []
        ext = file_path.split(".")[-1].lower() if file_path and "." in file_path else ""
        lang = (lang_id or "").lower()
        base_name = os.path.basename(file_path) if file_path else "untitled"

        # 1. Python Syntax & Indentation Check
        if lang == "python" or ext in ("py", "pyw"):
            try:
                compile(source_code, file_path or "<string>", "exec")
            except SyntaxError as e:
                problems.append({
                    "file": base_name,
                    "filePath": file_path or "",
                    "line": e.lineno or 1,
                    "column": e.offset or 1,
                    "message": e.msg or "Syntax Error",
                    "severity": "error",
                    "source": "Python Parser"
                })
            except Exception as e:
                problems.append({
                    "file": base_name,
                    "filePath": file_path or "",
                    "line": 1,
                    "column": 1,
                    "message": str(e),
                    "severity": "error",
                    "source": "Python Parser"
                })

        # 2. JSON Validation
        elif lang == "json" or ext == "json":
            try:
                json.loads(source_code)
            except json.JSONDecodeError as e:
                problems.append({
                    "file": base_name,
                    "filePath": file_path or "",
                    "line": e.lineno,
                    "column": e.colno,
                    "message": e.msg,
                    "severity": "error",
                    "source": "JSON Validator"
                })

        # 3. HTML / XML Validation (Unclosed tags check)
        elif lang in ("html", "xml") or ext in ("html", "htm", "xml"):
            void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr", "!doctype"}
            lines = source_code.split("\n")
            tag_stack = []
            for line_idx, line in enumerate(lines, 1):
                matches = re.finditer(r'<(/)?([a-zA-Z0-9_\-]+)(?:\s+[^<>]*)?(/)?>', line)
                for m in matches:
                    is_close = bool(m.group(1))
                    tag_name = m.group(2).lower()
                    is_self_closing = bool(m.group(3)) or tag_name in void_tags

                    if is_self_closing:
                        continue
                    if is_close:
                        if tag_stack and tag_stack[-1][0] == tag_name:
                            tag_stack.pop()
                        else:
                            problems.append({
                                "file": base_name,
                                "filePath": file_path or "",
                                "line": line_idx,
                                "column": m.start() + 1,
                                "message": f"Unexpected closing tag </{tag_name}>",
                                "severity": "error",
                                "source": "HTML Validator"
                            })
                    else:
                        tag_stack.append((tag_name, line_idx, m.start() + 1))

            for unclosed_tag, unclosed_line, unclosed_col in tag_stack[-5:]:
                problems.append({
                    "file": base_name,
                    "filePath": file_path or "",
                    "line": unclosed_line,
                    "column": unclosed_col,
                    "message": f"Unclosed tag <{unclosed_tag}>",
                    "severity": "warning",
                    "source": "HTML Validator"
                })

        # 4. General Braces Mismatch Check (JS, TS, C, C++, QML, CSS, etc.)
        elif lang in ("javascript", "typescript", "cpp", "c", "qml", "css", "rust", "go", "csharp", "java") or ext in ("js", "ts", "jsx", "tsx", "cpp", "c", "h", "hpp", "qml", "css", "rs", "go", "cs", "java"):
            lines = source_code.split("\n")
            bracket_stack = []
            matching = {')': '(', ']': '[', '}': '{'}

            for line_idx, line in enumerate(lines, 1):
                clean_line = re.sub(r'"(\\.|[^"\\])*"', '""', line)
                clean_line = re.sub(r"'(\\.|[^'\\])*'", "''", clean_line)
                clean_line = re.sub(r"//.*$", "", clean_line)

                for col_idx, char in enumerate(clean_line, 1):
                    if char in "({[":
                        bracket_stack.append((char, line_idx, col_idx))
                    elif char in ")}]":
                        expected = matching[char]
                        if bracket_stack and bracket_stack[-1][0] == expected:
                            bracket_stack.pop()
                        else:
                            problems.append({
                                "file": base_name,
                                "filePath": file_path or "",
                                "line": line_idx,
                                "column": col_idx,
                                "message": f"Unmatched '{char}'",
                                "severity": "error",
                                "source": "Syntax Linter"
                            })

            for unclosed_char, unclosed_line, unclosed_col in bracket_stack[-5:]:
                problems.append({
                    "file": base_name,
                    "filePath": file_path or "",
                    "line": unclosed_line,
                    "column": unclosed_col,
                    "message": f"Unclosed '{unclosed_char}'",
                    "severity": "error",
                    "source": "Syntax Linter"
                })

        self.diagnosticsUpdated.emit(problems)
        return problems

    @Slot(str, str)
    def log_output(self, channel, text):
        self.outputLogReceived.emit(channel, text)

    @Slot(str)
    def open_Workspace(self, path):
        if path.startswith("file:///"):
            parsed = urlparse(path)
            path = url2pathname(parsed.path)

        self.folder_path = os.path.normpath(path)
        print("Opening workspace:", self.folder_path)

        try:
            root, arr = self.search_folder_items(self.folder_path)
            result = self.explorerList(arr, root)
            self.explorerContent.emit(result, self.folder_path)
        except Exception as e:
            print("Error loading workspace tree:", e)

    def search_folder_items(self, path):
        p = Path(path)
        try:
            files = list(p.iterdir())
        except PermissionError:
            return p.name, []

        root_folder = p.name
        ls = []

        # Sort folders first, then files alphabetically
        dirs = [f for f in files if f.is_dir() and not f.name.startswith(".")]
        nondirs = [f for f in files if not f.is_dir()]

        for d in sorted(dirs, key=lambda x: x.name.lower()):
            root, childs = self.search_folder_items(d)
            ls.append([root, childs])

        for f in sorted(nondirs, key=lambda x: x.name.lower()):
            ls.append(f.name)

        return root_folder, ls

    def explorerList(self, arry, pid):
        final_list = []
        for item in arry:
            node = {}
            if isinstance(item, list):
                folder_name = item[0]
                li = item[1]
                node["name"] = folder_name
                node["parentId"] = pid
                node["type"] = "Folder"
                final_list.append(node)
                final_list.extend(self.explorerList(li, folder_name))
            else:
                node["name"] = item
                node["parentId"] = pid
                node["type"] = "Folder" if "." not in item else "File"
                final_list.append(node)
        return final_list


# ==============================================================================
# 3. APPLICATION ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    try:
        from PySide6.QtWebEngineQuick import QtWebEngineQuick
        QtWebEngineQuick.initialize()
    except Exception as we_err:
        print("[main.py] QtWebEngineQuick initialization notice:", we_err)

    app = QGuiApplication(sys.argv)
    app.setApplicationName("DGX Studio")
    app.setOrganizationName("DGX")

    # Install context menu blocker application-wide
    context_menu_filter = GlobalContextMenuFilter()
    app.installEventFilter(context_menu_filter)

    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    QQuickStyle.setStyle("Basic")

    engine = QQmlApplicationEngine()

    # Initialize backend singleton services
    backend = EditorBackend()
    musicPlayer = MusicPlayer()
    aiBackend = AIBackend()
    terminalBackend = TerminalBackend()
    settingsBackend = SettingsBackend()

    # Register root context properties
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
    engine.rootContext().setContextProperty("aiBackend", aiBackend)
    engine.rootContext().setContextProperty("terminalBackend", terminalBackend)
    engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

    engine.load("qml/main.qml")
    if not engine.rootObjects():
        # Fallback to main.qml in root if qml/ directory isn't used
        engine.load("main.qml")
        if not engine.rootObjects():
            sys.exit(-1)

    root_window = engine.rootObjects()[0]
    root_window.setFlags(
        Qt.Window
        | Qt.FramelessWindowHint
        | Qt.WindowMinimizeButtonHint
        | Qt.WindowMaximizeButtonHint
        | Qt.WindowSystemMenuHint
    )

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            hwnd = int(root_window.winId())
            GWL_STYLE = -16
            WS_THICKFRAME = 0x00040000
            WS_MINIMIZEBOX = 0x00020000
            WS_MAXIMIZEBOX = 0x00010000
            WS_SYSMENU = 0x00080000

            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            style |= (WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

            class MARGINS(ctypes.Structure):
                _fields_ = [
                    ("cxLeftWidth", ctypes.c_int),
                    ("cxRightWidth", ctypes.c_int),
                    ("cyTopHeight", ctypes.c_int),
                    ("cyBottomHeight", ctypes.c_int)
                ]
            margins = MARGINS(1, 1, 1, 1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
        except Exception as e:
            print("Native window setup warning:", e)

    sys.exit(app.exec())
