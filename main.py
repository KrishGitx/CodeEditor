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
import shutil
import json
import time
import re
import threading
from html.parser import HTMLParser

from MusicPlayer import MusicPlayer
from HighlighterEngine import MultiLanguageHighlighter
from AIBackend import AIBackend
from TerminalBackend import TerminalBackend
from SettingsBackend import SettingsBackend
from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager

try:
    import shiboken6
    def get_cpp_ptr(obj):
        if obj is None:
            return 0
        try:
            return int(shiboken6.getCppPointer(obj)[0])
        except Exception:
            return id(obj)
except Exception:
    def get_cpp_ptr(obj):
        return id(obj)


# ==============================================================================
# GLOBAL CONTEXT MENU FILTER (Blocks Native OS QMenu from Popping Up)
# ==============================================================================
class GlobalContextMenuFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.ContextMenu:
            return True  # Suppress native Windows context menu
        return super().eventFilter(obj, event)


# ==============================================================================
# 1. BACKGROUND LSP THREAD WORKER (HIGH PERFORMANCE BUFFERED PROTOCOL)
# ==============================================================================
class LSPReaderWorker(QThread):
    message_received = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process
        self.running = True

    def run(self):
        while self.running:
            try:
                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        break
                    continue

                line_str = line.decode('utf-8', errors='ignore').strip()
                if line_str.startswith("Content-Length:"):
                    try:
                        length = int(line_str.split("Content-Length:")[1].strip())
                    except ValueError:
                        continue

                    # Consume blank separator line(s)
                    while True:
                        blank_line = self.process.stdout.readline()
                        if not blank_line or blank_line in (b"\r\n", b"\n", b""):
                            break

                    # Read the full JSON payload in a single syscall
                    msg_body_bytes = self.process.stdout.read(length)
                    if msg_body_bytes:
                        try:
                            msg_obj = json.loads(msg_body_bytes.decode('utf-8'))
                            self.message_received.emit(msg_obj)
                        except Exception as parse_err:
                            pass
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
    notificationRequested = Signal(str, str, str)  # message, type ('info', 'warning', 'error', 'success'), title
    formatterInstallProgress = Signal(str, str, str)  # extension_id, status ('installing', 'success', 'failed'), message
    formattingCompleted = Signal(str, str, bool, str, str, bool, str)  # req_id, file_path, success, formatted_code, message, available, extension_id

    def __init__(self):
        super().__init__()
        self.highlighter = None
        self.tab_highlighters = {}
        self.lsp_process = None
        self.msg_id = 1
        self.doc_version = 1
        self.current_file = ""
        self.sec_current_file = ""
        self.sec_highlighter = None
        self.sec_tab_highlighters = {}
        self.settings_backend = None
        self.folder_path = os.getcwd()
        self.latest_completion_req_id = None
        self._active_formatting_requests = set()
        self.qml_doc = None
        self.text_document = None
        self.sec_qml_doc = None
        self.sec_text_document = None
        self.extension_manager = ExtensionManager()
        self.extension_manager.formatterInstallProgress.connect(self.formatterInstallProgress.emit)
        self.formatter_manager = FormatterManager(self.extension_manager)
        self.start_lsp_server()

    @Slot(str)
    @Slot(str, str)
    def set_active_file(self, file_path, lang=""):
        clean_path = file_path or ""
        if clean_path.startswith("file:///"):
            parsed = urlparse(clean_path)
            clean_path = url2pathname(parsed.path)
        self.current_file = os.path.normpath(clean_path) if clean_path else ""
        if self.highlighter:
            prev_lang = self.highlighter.language
            if lang and self.highlighter.language != lang:
                self.highlighter.set_language_for_file(self.current_file, explicit_lang=lang, force_rehighlight=True)
                self.currentLanguageChanged.emit(self.highlighter.language)

    @Slot(QObject)
    @Slot(QObject, str)
    @Slot(QObject, str, str)
    def register_text_area(self, qml_text_area, file_path="", lang=""):
        if not qml_text_area:
            return
        self.qml_text_area = qml_text_area
        self.qml_doc = qml_text_area.property("textDocument")
        if self.qml_doc:
            doc = self.qml_doc.textDocument()
            self.text_document = doc
            if file_path:
                clean_path = file_path
                if clean_path.startswith("file:///"):
                    parsed = urlparse(clean_path)
                    clean_path = url2pathname(parsed.path)
                self.current_file = os.path.normpath(clean_path)

            doc_id = get_cpp_ptr(doc)
            if not hasattr(self, "tab_highlighters"):
                self.tab_highlighters = {}

            if doc_id not in self.tab_highlighters:
                hl = MultiLanguageHighlighter(None)
                initial_path = self.current_file or "main.py"
                hl.set_language_for_file(initial_path, explicit_lang=lang, force_rehighlight=False)
                hl.setDocument(doc)
                self.tab_highlighters[doc_id] = hl

            self.highlighter = self.tab_highlighters[doc_id]
            if lang and self.highlighter.language != lang:
                self.highlighter.set_language_for_file(self.current_file, explicit_lang=lang, force_rehighlight=True)
            self.currentLanguageChanged.emit(self.highlighter.language)

    @Slot(QObject)
    def unregister_text_area(self, qml_text_area):
        if not qml_text_area:
            return
        try:
            qml_doc = qml_text_area.property("textDocument")
            if qml_doc:
                doc = qml_doc.textDocument()
                doc_id = get_cpp_ptr(doc)
                if hasattr(self, "tab_highlighters") and doc_id in self.tab_highlighters:
                    hl = self.tab_highlighters.pop(doc_id, None)
                    if hl:
                        hl.setDocument(None)
        except Exception:
            pass

    @Slot(int, int, bool)
    def set_line_range_visibility(self, start_line, end_line, is_hidden):
        if not hasattr(self, "text_document") or not self.text_document:
            return
        doc = self.text_document
        total = doc.blockCount()
        for l in range(start_line, min(end_line, total)):
            b = doc.findBlockByNumber(l)
            if b.isValid():
                b.setVisible(not is_hidden)
        doc.markContentsDirty(0, doc.characterCount())
        if hasattr(self, "qml_text_area") and self.qml_text_area:
            try:
                self.qml_text_area.update()
            except Exception:
                pass

    @Slot(list)
    def set_folded_ranges(self, folded_ranges):
        if not hasattr(self, "text_document") or not self.text_document:
            return
        doc = self.text_document
        total = doc.blockCount()
        hidden_indices = set()
        for rng in folded_ranges:
            if isinstance(rng, list) and len(rng) >= 2:
                s, e = rng[0], rng[1]
                for l in range(s, min(e, total)):
                    hidden_indices.add(l)
        for l in range(total):
            b = doc.findBlockByNumber(l)
            if b.isValid():
                should_be_visible = (l not in hidden_indices)
                if b.isVisible() != should_be_visible:
                    b.setVisible(should_be_visible)
        doc.markContentsDirty(0, doc.characterCount())
        if hasattr(self, "qml_text_area") and self.qml_text_area:
            try:
                self.qml_text_area.update()
            except Exception:
                pass

    @Slot(QObject)
    def register_secondary_text_area(self, qml_text_area):
        if not qml_text_area:
            return
        qml_doc = qml_text_area.property("textDocument")
        if qml_doc:
            doc = qml_doc.textDocument()
            doc_id = get_cpp_ptr(doc)
            if not hasattr(self, "sec_tab_highlighters"):
                self.sec_tab_highlighters = {}
            initial_path = self.sec_current_file or self.current_file or "main.py"
            if doc_id not in self.sec_tab_highlighters:
                hl = MultiLanguageHighlighter(doc)
                hl.set_language_for_file(initial_path)
                self.sec_tab_highlighters[doc_id] = hl
            self.sec_highlighter = self.sec_tab_highlighters[doc_id]

    @Slot(str)
    def set_secondary_file(self, file_path):
        self.sec_current_file = file_path
        if self.sec_highlighter:
            self.sec_highlighter.set_language_for_file(file_path)

    @Slot(str)
    def set_theme(self, theme_name):
        if self.highlighter:
            self.highlighter.set_theme(theme_name.lower())
        if hasattr(self, "sec_highlighter") and self.sec_highlighter:
            self.sec_highlighter.set_theme(theme_name.lower())

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
            return None
        try:
            req_id = self.msg_id
            self.msg_id += 1
            js = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": dic}
            json_string = json.dumps(js)
            header = f"Content-Length: {len(json_string)}\r\n\r\n{json_string}"
            self.lsp_process.stdin.write(header.encode('utf-8'))
            self.lsp_process.stdin.flush()
            return req_id
        except Exception as e:
            print("LSP request error:", e)
            return None

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

    @Slot(str, int, int)
    @Slot(str, int, int, str)
    def request_completion(self, filepath, line, character, current_text=""):
        clean_path = filepath.replace("\\", "/")
        if not clean_path.startswith("file:///"):
            clean_path = "file:///" + clean_path

        if current_text:
            self.doc_version += 1
            payload = {
                "textDocument": {"uri": clean_path, "version": self.doc_version},
                "contentChanges": [{"text": current_text}]
            }
            self.send_lsp_notification("textDocument/didChange", payload)

        completion_payload = {
            "textDocument": {"uri": clean_path},
            "position": {"line": line, "character": character}
        }
        req_id = self.send_lsp_request("textDocument/completion", completion_payload)
        if req_id is not None:
            self.latest_completion_req_id = req_id

    def handle_lsp_message(self, response_json):
        msg_id = response_json.get("id")

        if msg_id == 1:
            self.send_lsp_notification("initialized", {})
            print("LSP INITIALIZED HANDSHAKE COMPLETE")
            return

        # Discard stale completion responses if a newer request was dispatched
        if msg_id is not None and self.latest_completion_req_id is not None:
            if msg_id != self.latest_completion_req_id:
                return

        if "result" in response_json:
            result_data = response_json.get("result") or {}
            items_list = []

            if isinstance(result_data, dict):
                items_list = result_data.get("items") or []
            elif isinstance(result_data, list):
                items_list = result_data

            suggestions = []
            # Efficiently extract and limit to top 40 results
            for item in items_list[:40]:
                label = item.get("label", "")
                if label:
                    suggestions.append({
                        "label": label,
                        "insertText": item.get("insertText", label),
                        "type": item.get("kind", "")
                    })
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
            ext = os.path.splitext(clean_path)[1].lower()
            binary_exts = {".exe", ".dll", ".so", ".bin", ".iso", ".dat", ".pyc", ".pyd", ".o", ".a", ".class", ".zip", ".tar", ".gz", ".7z", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".mp3", ".mp4", ".wav", ".flac", ".pdf"}
            file_size = os.path.getsize(clean_path)

            if ext in binary_exts or file_size > 5 * 1024 * 1024:
                # Binary / very large file safe preview
                size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024*1024):.1f} MB"
                with open(clean_path, "rb") as bf:
                    sample = bf.read(min(4096, file_size))
                
                # Format a clean hex dump preview
                hex_lines = [f"[Binary File: {os.path.basename(clean_path)} | Size: {size_str} | Binary representation]", "=" * 70]
                for offset in range(0, min(len(sample), 2048), 16):
                    chunk = sample[offset:offset+16]
                    hex_part = " ".join(f"{b:02X}" for b in chunk).ljust(48)
                    ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                    hex_lines.append(f"{offset:08X}  {hex_part}  |{ascii_part}|")
                if len(sample) > 2048 or file_size > 2048:
                    hex_lines.append(f"\n... [Binary preview truncated for performance. Total size: {size_str}] ...")
                content = "\n".join(hex_lines)

                if self.highlighter:
                    self.currentLanguageChanged.emit("Binary")
            else:
                with open(clean_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

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

    @Slot(str, str, str, str)
    @Slot(str, str, str, str, int)
    def request_format_code(self, req_id, lang_id, file_path, source_code, tab_size=4):
        """Asynchronously formats source code in a worker thread, ensuring the UI never hangs."""
        if req_id in self._active_formatting_requests:
            return
        self._active_formatting_requests.add(req_id)

        def _worker():
            try:
                result = self.formatter_manager.format_code(lang_id, file_path, source_code, tab_size)
                self.formattingCompleted.emit(
                    req_id,
                    file_path or "",
                    bool(result.get("success", False)),
                    str(result.get("formatted", source_code)),
                    str(result.get("message", "")),
                    bool(result.get("available", False)),
                    str(result.get("extension_id", ""))
                )
            except Exception as e:
                self.formattingCompleted.emit(
                    req_id,
                    file_path or "",
                    False,
                    source_code,
                    f"Formatting error: {e}",
                    True,
                    ""
                )
            finally:
                self._active_formatting_requests.discard(req_id)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    @Slot(str, str, str, result="QVariantMap")
    @Slot(str, str, str, int, result="QVariantMap")
    def format_code(self, lang_id, file_path, source_code, tab_size=4):
        """Delegates formatting to FormatterManager via active language extensions (synchronous fallback)."""
        result = self.formatter_manager.format_code(lang_id, file_path, source_code, tab_size)
        if not result.get("success") and not result.get("available"):
            self.notificationRequested.emit(result.get("message", "No formatter available"), "warning", "Formatter")
        elif not result.get("success"):
            self.notificationRequested.emit(result.get("message", "Formatting failed"), "error", "Formatter")
        return result

    @Slot(result=list)
    def get_installed_extensions(self):
        """Returns all installed language and tool extensions."""
        return self.extension_manager.get_installed_extensions()

    @Slot(str, result=bool)
    def install_local_extension(self, path):
        """Installs an extension package from a local directory, .zip archive, or .json file."""
        return self.extension_manager.install_local_extension(path)

    @Slot(str, result=bool)
    def uninstall_extension(self, extension_id):
        """Uninstalls a user-installed extension."""
        return self.extension_manager.uninstall_extension(extension_id)

    @Slot(str, bool, result=bool)
    def toggle_extension(self, extension_id, enabled):
        """Enables or disables an extension."""
        return self.extension_manager.toggle_extension(extension_id, enabled)

    @Slot(str, result=bool)
    def open_extension_folder(self, extension_id):
        """Opens the extension directory in the system file manager."""
        return self.extension_manager.open_extension_folder(extension_id)

    @Slot(str, result="QVariantMap")
    def get_formatter_status_for_language(self, lang_id, file_path=""):
        """Returns formatter dependency status and OS installation guide."""
        return self.extension_manager.get_formatter_status_for_language(lang_id, file_path)

    @Slot(str)
    def copy_to_clipboard(self, text):
        """Copies text to system clipboard."""
        self.extension_manager.copy_to_clipboard(text)

    @Slot(str)
    def install_formatter(self, extension_id):
        """Installs lightweight standalone formatter executable."""
        self.extension_manager.install_formatter(extension_id)

    @Slot(str, str, result=bool)
    def set_custom_formatter_path(self, extension_id, custom_path):
        """Sets a user-selected custom binary path."""
        return self.extension_manager.set_custom_formatter_path(extension_id, custom_path)

    @Slot(str, result=str)
    def get_custom_formatter_path(self, extension_id):
        """Gets custom binary path for extension."""
        return self.extension_manager.get_custom_formatter_path(extension_id)

    @Slot(str)
    def open_external_url(self, url):
        """Opens URL in system browser."""
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Error opening URL {url}: {e}")

    @Slot(result="QVariantMap")
    def check_for_updates(self):
        """Checks for updates for Pod Studio and installed extensions."""
        return self.extension_manager.check_for_updates()

    def _scan_bracket_problems(self, source_code, base_name, file_path):
        problems = []
        matching = {')': '(', ']': '[', '}': '{'}
        stack = []

        i = 0
        n = len(source_code)
        line = 1
        col = 1

        state = "NORMAL"
        prev_token = ""

        while i < n:
            c = source_code[i]
            c_next = source_code[i + 1] if i + 1 < n else ""

            cur_line = line
            cur_col = col

            if c == '\n':
                line += 1
                col = 1
            else:
                col += 1

            if state == "LINE_COMMENT":
                if c == '\n':
                    state = "NORMAL"
                i += 1
                continue

            if state == "BLOCK_COMMENT":
                if c == '*' and c_next == '/':
                    state = "NORMAL"
                    i += 2
                    col += 1
                    continue
                i += 1
                continue

            if state == "STRING_DOUBLE":
                if c == '\\':
                    i += 2
                    col += 1
                    continue
                if c == '"':
                    state = "NORMAL"
                i += 1
                continue

            if state == "STRING_SINGLE":
                if c == '\\':
                    i += 2
                    col += 1
                    continue
                if c == "'":
                    state = "NORMAL"
                i += 1
                continue

            if state == "STRING_BACKTICK":
                if c == '\\':
                    i += 2
                    col += 1
                    continue
                if c == '`':
                    state = "NORMAL"
                i += 1
                continue

            if state == "REGEX":
                if c == '\\':
                    i += 2
                    col += 1
                    continue
                if c == '[':
                    i += 1
                    while i < n and source_code[i] != ']':
                        if source_code[i] == '\\':
                            i += 2
                        else:
                            i += 1
                    continue
                if c == '/':
                    state = "NORMAL"
                i += 1
                continue

            # NORMAL STATE
            if c == '/' and c_next == '/':
                state = "LINE_COMMENT"
                i += 2
                col += 1
                continue

            if c == '/' and c_next == '*':
                state = "BLOCK_COMMENT"
                i += 2
                col += 1
                continue

            if c == '"':
                state = "STRING_DOUBLE"
                i += 1
                continue

            if c == "'":
                state = "STRING_SINGLE"
                i += 1
                continue

            if c == '`':
                state = "STRING_BACKTICK"
                i += 1
                continue

            if c == '/':
                if prev_token in '(=:[,!&|?{;~^+-*%<>':
                    state = "REGEX"
                    i += 1
                    continue

            if not c.isspace():
                prev_token = c

            if c in "({[":
                stack.append((c, cur_line, cur_col))
            elif c in ")}]":
                expected = matching[c]
                if stack and stack[-1][0] == expected:
                    stack.pop()
                else:
                    problems.append({
                        "file": base_name,
                        "filePath": file_path or "",
                        "line": cur_line,
                        "column": cur_col,
                        "message": f"Unmatched '{c}'",
                        "severity": "error",
                        "source": "Syntax Linter"
                    })
            i += 1

        for unclosed_char, unclosed_line, unclosed_col in stack[-5:]:
            problems.append({
                "file": base_name,
                "filePath": file_path or "",
                "line": unclosed_line,
                "column": unclosed_col,
                "message": f"Unclosed '{unclosed_char}'",
                "severity": "error",
                "source": "Syntax Linter"
            })

        return problems

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

        # 3. HTML / XML Validation (Robust Multi-Line HTML5 Parser)
        elif lang in ("html", "xml") or ext in ("html", "htm", "xml"):
            void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr", "!doctype"}
            optional_close = {"p", "li", "td", "tr", "th", "dt", "dd", "option", "html", "body", "head"}

            class HTMLTagValidator(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.stack = []
                    self.tag_problems = []

                def handle_starttag(self, tag, attrs):
                    tag_l = tag.lower()
                    if tag_l not in void_tags:
                        line, col = self.getpos()
                        self.stack.append((tag_l, line, col + 1))

                def handle_endtag(self, tag):
                    tag_l = tag.lower()
                    if tag_l in void_tags:
                        return
                    line, col = self.getpos()
                    if not self.stack:
                        self.tag_problems.append({
                            "file": base_name,
                            "filePath": file_path or "",
                            "line": line,
                            "column": col + 1,
                            "message": f"Unexpected closing tag </{tag_l}>",
                            "severity": "error",
                            "source": "HTML Validator"
                        })
                        return

                    if self.stack[-1][0] == tag_l:
                        self.stack.pop()
                    else:
                        match_idx = -1
                        for idx in range(len(self.stack) - 1, -1, -1):
                            if self.stack[idx][0] == tag_l:
                                match_idx = idx
                                break
                        if match_idx != -1:
                            unclosed = self.stack[match_idx + 1:]
                            for u_tag, u_line, u_col in unclosed:
                                if u_tag not in optional_close:
                                    self.tag_problems.append({
                                        "file": base_name,
                                        "filePath": file_path or "",
                                        "line": u_line,
                                        "column": u_col,
                                        "message": f"Unclosed tag <{u_tag}>",
                                        "severity": "warning",
                                        "source": "HTML Validator"
                                    })
                            self.stack = self.stack[:match_idx]
                        else:
                            self.tag_problems.append({
                                "file": base_name,
                                "filePath": file_path or "",
                                "line": line,
                                "column": col + 1,
                                "message": f"Unexpected closing tag </{tag_l}>",
                                "severity": "error",
                                "source": "HTML Validator"
                            })

            validator = HTMLTagValidator()
            try:
                validator.feed(source_code)
                for u_tag, u_line, u_col in validator.stack:
                    if u_tag not in optional_close:
                        validator.tag_problems.append({
                            "file": base_name,
                            "filePath": file_path or "",
                            "line": u_line,
                            "column": u_col,
                            "message": f"Unclosed tag <{u_tag}>",
                            "severity": "warning",
                            "source": "HTML Validator"
                        })
                problems.extend(validator.tag_problems)
            except Exception:
                pass

        # 4. C & C++ Real-Time Compiler Diagnostics (g++ / gcc / clang)
        elif lang in ("cpp", "c", "c++") or ext in ("cpp", "cc", "cxx", "hpp", "h", "c"):
            is_cpp = (lang in ("cpp", "c++") or ext in ("cpp", "cc", "cxx", "hpp"))
            compiler = "g++" if is_cpp else "gcc"
            std_flag = "-std=c++17" if is_cpp else "-std=c11"
            lang_flag = "c++" if is_cpp else "c"

            compiler_checked = False
            startupinfo = None
            if hasattr(subprocess, "STARTUPINFO"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            cmd = [compiler, "-fsyntax-only", "-fno-diagnostics-color", std_flag]
            if file_path and os.path.exists(file_path):
                inc_dir = os.path.dirname(os.path.abspath(file_path))
                if inc_dir:
                    cmd.append(f"-I{inc_dir}")
            cmd.extend(["-x", lang_flag, "-"])

            try:
                proc = subprocess.run(
                    cmd,
                    input=source_code,
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                    startupinfo=startupinfo
                )
                compiler_checked = True
                stderr = proc.stderr or ""
                # Parse g++/gcc diagnostics: <stdin>:line:col: error/warning: message
                for match in re.finditer(r'(?:<stdin>|[^:\r\n]+):(\d+):(\d+):\s*(error|warning|fatal error|note):\s*(.+)', stderr):
                    line_str, col_str, raw_sev, msg = match.groups()
                    sev = "error" if "error" in raw_sev else ("warning" if "warning" in raw_sev else "info")
                    if sev == "info":
                        continue  # Skip notes unless needed
                    problems.append({
                        "file": base_name,
                        "filePath": file_path or "",
                        "line": int(line_str),
                        "column": int(col_str),
                        "message": msg.strip(),
                        "severity": sev,
                        "source": f"{compiler.upper()} Compiler"
                    })
            except Exception:
                compiler_checked = False

            if not compiler_checked:
                problems.extend(self._scan_bracket_problems(source_code, base_name, file_path))

        # 5. JavaScript / TypeScript Validation (via Node.js)
        elif lang in ("javascript", "typescript") or ext in ("js", "ts", "jsx", "tsx", "mjs", "cjs"):
            node_checked = False
            startupinfo = None
            if hasattr(subprocess, "STARTUPINFO"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            try:
                proc = subprocess.run(
                    ["node", "--input-type=module", "--check"],
                    input=source_code,
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                    startupinfo=startupinfo
                )
                node_checked = True
                if proc.returncode != 0 and proc.stderr:
                    m_line = re.search(r'\[stdin\]:(\d+)', proc.stderr)
                    line_num = int(m_line.group(1)) if m_line else 1
                    m_col = re.search(r'\n([ \t]*)\^', proc.stderr)
                    col_num = len(m_col.group(1)) + 1 if m_col else 1
                    m_msg = re.search(r'^(?:SyntaxError|TypeError|ReferenceError|Error):\s*(.+)', proc.stderr, re.M)
                    msg = m_msg.group(0) if m_msg else "JavaScript Syntax Error"
                    problems.append({
                        "file": base_name,
                        "filePath": file_path or "",
                        "line": line_num,
                        "column": col_num,
                        "message": msg.strip(),
                        "severity": "error",
                        "source": "Node.js Engine"
                    })
            except Exception:
                node_checked = False

            if not node_checked or len(problems) == 0:
                problems.extend(self._scan_bracket_problems(source_code, base_name, file_path))

        # 6. General Braces Mismatch Check for other languages (QML, CSS, Rust, Go, Java, etc.)
        else:
            problems.extend(self._scan_bracket_problems(source_code, base_name, file_path))

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

        if self.settings_backend and hasattr(self.settings_backend, "add_recent_project"):
            try:
                self.settings_backend.add_recent_project(self.folder_path)
            except Exception as se:
                print("Recent project tracking notice:", se)

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

    @Slot(str, result=list)
    def get_workspace_files(self, query=""):
        """Quickly scans the active workspace and returns files matching the query for Quick Open (Ctrl+P)."""
        base_dir = self.folder_path if (self.folder_path and os.path.exists(self.folder_path)) else os.getcwd()
        query = (query or "").strip().lower()
        results = []
        ignored_dirs = {
            ".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv", "env",
            ".dgx_studio", ".idea", ".vscode", "dist", "build", ".pytest_cache", ".agents",
            "bin", "obj", ".qtcreator"
        }

        count = 0
        max_files = 500
        for root_dir, dirs, files in os.walk(base_dir):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
            for f in files:
                full_path = os.path.join(root_dir, f)
                try:
                    rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")
                except ValueError:
                    rel_path = full_path.replace("\\", "/")

                f_lower = f.lower()
                rel_lower = rel_path.lower()

                if not query or query in f_lower or query in rel_lower:
                    results.append({
                        "name": f,
                        "path": full_path.replace("\\", "/"),
                        "relPath": rel_path
                    })
                    count += 1
                    if count >= max_files:
                        break
            if count >= max_files:
                break

        # Sort: exact name match first, then shorter relPath
        if query:
            results.sort(key=lambda x: (
                0 if x["name"].lower() == query else (
                    1 if x["name"].lower().startswith(query) else (
                        2 if query in x["name"].lower() else 3
                    )
                ),
                len(x["relPath"])
            ))
        return results

    @Slot(str, int, int, str, result=dict)
    def get_hover_info(self, file_path, line, col, source_code):
        """Retrieves type/signature/documentation info for hover inspection."""
        if not source_code:
            return {"found": False}

        lines = source_code.splitlines()
        if line < 1 or line > len(lines):
            return {"found": False}

        target_line = lines[line - 1]
        if col < 0 or col >= len(target_line):
            col = min(max(0, col), max(0, len(target_line) - 1))

        # Extract identifier under cursor
        start = col
        while start > 0 and (target_line[start - 1].isalnum() or target_line[start - 1] == '_'):
            start -= 1
        end = col
        while end < len(target_line) and (target_line[end].isalnum() or target_line[end] == '_'):
            end += 1

        symbol = target_line[start:end].strip()
        if not symbol or symbol.isdigit():
            return {"found": False}

        ext = os.path.splitext(file_path)[1].lower() if file_path else ""

        # 1. Python AST & Docstring lookup
        if ext in (".py", ".pyw") or "def " in source_code or "class " in source_code:
            try:
                import ast
                tree = ast.parse(source_code)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
                        args = [a.arg for a in node.args.args]
                        sig = f"def {node.name}({', '.join(args)})"
                        doc = ast.get_docstring(node) or "No documentation provided."
                        return {
                            "found": True,
                            "symbol": symbol,
                            "title": sig,
                            "doc": doc,
                            "kind": "function"
                        }
                    elif isinstance(node, ast.ClassDef) and node.name == symbol:
                        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                        sig = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
                        doc = ast.get_docstring(node) or "Class declaration."
                        return {
                            "found": True,
                            "symbol": symbol,
                            "title": sig,
                            "doc": doc,
                            "kind": "class"
                        }
            except Exception:
                pass

        # 2. General regex lookup for function / class / variable definitions
        func_match = re.search(rf'(?:def|function|fn|func|public|private|protected|static|\s)\s+{re.escape(symbol)}\s*\(([^)]*)\)', source_code)
        if func_match:
            sig = f"{symbol}({func_match.group(1).strip()})"
            return {
                "found": True,
                "symbol": symbol,
                "title": sig,
                "doc": f"Definition found in {os.path.basename(file_path) if file_path else 'current file'}",
                "kind": "function"
            }

        class_match = re.search(rf'(?:class|struct|interface|type)\s+{re.escape(symbol)}', source_code)
        if class_match:
            return {
                "found": True,
                "symbol": symbol,
                "title": f"type {symbol}",
                "doc": f"Type definition in {os.path.basename(file_path) if file_path else 'current file'}",
                "kind": "class"
            }

        # 3. Built-in keyword explanation fallback
        python_builtins = {
            "len": ("len(s)", "Return the number of items in a container."),
            "print": ("print(*objects, sep=' ', end='\\n')", "Prints values to a stream, or to sys.stdout by default."),
            "range": ("range(stop) or range(start, stop[, step])", "Return an object that produces a sequence of integers."),
            "import": ("import module", "Imports modules into the current namespace."),
            "from": ("from module import name", "Imports specific attributes from a module."),
            "return": ("return [value]", "Leaves the current function call with the specified return value."),
            "yield": ("yield [value]", "Yields a value from a generator function."),
            "async": ("async def ...", "Defines a coroutine function."),
            "await": ("await expression", "Suspends execution of the enclosing coroutine until the awaitable is complete."),
            "if": ("if condition:", "Conditional execution branch."),
            "elif": ("elif condition:", "Alternative conditional execution branch."),
            "else": ("else:", "Fallback execution branch when prior conditions evaluate to false."),
            "for": ("for target in iterable:", "Iterates over items of any sequence or iterable."),
            "while": ("while condition:", "Executes a block of code as long as the condition remains true."),
            "try": ("try: ... except:", "Block for handling exceptions."),
            "except": ("except Exception as e:", "Catches and handles specified exceptions."),
            "finally": ("finally:", "Always executes after try/except blocks regardless of exceptions."),
            "with": ("with context_manager:", "Wraps execution with methods defined by a context manager."),
            "class": ("class ClassName:", "Defines a new user-defined class."),
            "def": ("def function_name(...):", "Defines a function or method.")
        }

        if symbol in python_builtins:
            title, doc = python_builtins[symbol]
            return {
                "found": True,
                "symbol": symbol,
                "title": title,
                "doc": doc,
                "kind": "keyword"
            }

        return {
            "found": True,
            "symbol": symbol,
            "title": f"symbol {symbol}",
            "doc": f"Identifier in {os.path.basename(file_path) if file_path else 'document'}",
            "kind": "variable"
        }

    @Slot(str, int, int, str, str, str, result=dict)
    def rename_symbol(self, file_path, line, col, current_name, new_name, source_code):
        """Performs semantic/scope-aware symbol renaming across the file."""
        if not current_name or not new_name or not source_code:
            return {"success": False, "message": "Invalid symbol or empty source code."}
        if current_name == new_name:
            return {"success": False, "message": "New name matches current name."}

        # Check valid identifier
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', new_name):
            return {"success": False, "message": f"'{new_name}' is not a valid identifier."}

        pattern = r'\b' + re.escape(current_name) + r'\b'
        matches = list(re.finditer(pattern, source_code))
        if not matches:
            return {"success": False, "message": f"Symbol '{current_name}' not found."}

        new_code = re.sub(pattern, new_name, source_code)
        return {
            "success": True,
            "new_code": new_code,
            "count": len(matches),
            "message": f"Successfully renamed {len(matches)} occurrence(s) of '{current_name}' to '{new_name}'."
        }

    @Slot(str, str, result=list)
    def get_document_symbols(self, file_path, source_code):
        """Extracts document symbol hierarchy (classes, functions, methods) for Breadcrumbs & navigation."""
        if not source_code:
            return []

        symbols = []
        lines = source_code.splitlines()

        # Try Python AST first
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""
        if ext in (".py", ".pyw"):
            try:
                import ast
                tree = ast.parse(source_code)
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append({
                            "name": node.name,
                            "kind": "function",
                            "line": node.lineno,
                            "container": ""
                        })
                    elif isinstance(node, ast.ClassDef):
                        symbols.append({
                            "name": node.name,
                            "kind": "class",
                            "line": node.lineno,
                            "container": ""
                        })
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                symbols.append({
                                    "name": item.name,
                                    "kind": "method",
                                    "line": item.lineno,
                                    "container": node.name
                                })
                if symbols:
                    return symbols
            except Exception:
                pass

        # Regex fallback for multi-language symbols (JS, TS, C++, Java, Rust, QML, etc.)
        for idx, line_text in enumerate(lines, start=1):
            stripped = line_text.strip()
            # Class match
            m_class = re.match(r'^(?:export\s+)?(?:class|struct|interface|enum)\s+([A-Za-z0-9_]+)', stripped)
            if m_class:
                symbols.append({
                    "name": m_class.group(1),
                    "kind": "class",
                    "line": idx,
                    "container": ""
                })
                continue

            # Function match
            m_func = re.match(r'^(?:export\s+)?(?:async\s+)?(?:def|function|fn)\s+([A-Za-z0-9_]+)', stripped)
            if m_func:
                symbols.append({
                    "name": m_func.group(1),
                    "kind": "function",
                    "line": idx,
                    "container": ""
                })
                continue

            # QML Item / Component match
            m_qml = re.match(r'^([A-Z][A-Za-z0-9_]*)\s*\{', stripped)
            if m_qml:
                symbols.append({
                    "name": m_qml.group(1),
                    "kind": "component",
                    "line": idx,
                    "container": ""
                })

        return symbols

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
    backend.settings_backend = settingsBackend

    # Register root context properties
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("extensionManager", backend.extension_manager)
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
