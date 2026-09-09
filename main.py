import sys
from PySide6.QtGui import QGuiApplication, QSurfaceFormat, QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import Qt, QObject, Slot, QRegularExpression, QThread, Signal
from PySide6.QtQuick import QQuickTextDocument
from urllib.parse import urlparse
from urllib.request import url2pathname
import os
import subprocess
import json
import time
from MusicPlayer import MusicPlayer
from pathlib import Path

musicPlayer = MusicPlayer()


# ==============================================================================
# 1. SYNTAX HIGHLIGHTER UTILITIES
# ==============================================================================
ALL_KEYWORDS_PATTERN = (
    r"\b("
    r"def|class|return|import|from|if|else|elif|while|for|try|except|print|with|as|"
    r"function|const|let|var|switch|case|export|console|"
    r"int|float|double|char|void|struct|public|private"
    r")\b|"
    r"(#include|#define|#ifdef|#ifndef|#endif)"
)
ALL_COMMENTS_PATTERN = r"(#.*|//.*)"

THEMES = {
    "one_dark": {
        "keywords": "#c678dd", "functions": "#61afef", "strings": "#98c379", "comments": "#5c6370"
    }
}

class highlighter(QSyntaxHighlighter):
    def __init__(self, parent_document, theme_name="one_dark"):
        super().__init__(parent_document)
        self.rules = []
        self.current_theme = THEMES.get(theme_name, THEMES["one_dark"])
        self.setup_rules()

    def setup_rules(self):
        self.rules.clear()
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(self.current_theme["keywords"]))
        keyword_format.setFontWeight(QFont.Bold)
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(self.current_theme["functions"]))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(self.current_theme["strings"]))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(self.current_theme["comments"]))

        self.rules = [
            (QRegularExpression(ALL_COMMENTS_PATTERN), comment_format),
            (QRegularExpression(r"(\".*?\"|'.*?')"), string_format),
            (QRegularExpression(ALL_KEYWORDS_PATTERN), keyword_format),
            (QRegularExpression(r"\b[A-Za-z0-9_]+(?=\()"), function_format)
        ]
        self.rehighlight()

    def highlightBlock(self, text):
        for pattern, text_format in self.rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), text_format)


# ==============================================================================
# 2. BACKGROUND LSP THREAD WORKER
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
                    if self.process.poll() is not None: break
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
                            if not next_byte: break
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
# 3. LSP BACKEND ENGINE
# ==============================================================================
class EditorBackend(QObject):
    completionsReceived  = Signal(list)
    fileOpened = Signal(str,str)
    explorerContent = Signal(list,str)

    def __init__(self):
        super().__init__()
        self.highlighter = None
        self.lsp_process = None
        self.msg_id = 1
        self.doc_version = 1
        self.start_lsp_server()
        self.folder_path = ""


    @Slot(QObject)
    def register_text_area(self, qml_text_area):
        qml_doc = qml_text_area.property("textDocument")
        self.highlighter = highlighter(qml_doc.textDocument())

        # Trigger an initial open sequence now that we have the text document area context mapping
        initial_text = qml_text_area.property("text") or ""
        self.initial_file_open("C:/Users/amazi/OneDrive/Documents/DGX/test.py", initial_text)

    def start_lsp_server(self):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        server_path = r"C:\Users\amazi/OneDrive/Documents/DGX/.qtcreator/Python_3_14_3venv/Scripts/pylsp.exe"

        self.lsp_process = subprocess.Popen(
            [server_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=False, bufsize=0, env=env
        )

        if self.lsp_process.poll() is None:
            print("LSP STARTED")
            self.reader_thread = LSPReaderWorker(self.lsp_process)
            self.reader_thread.message_received.connect(self.handle_lsp_message)
            self.reader_thread.start()

            # Capability announcement tells pylsp to calculate autocomplete items
            self.send_lsp_request("initialize", {
                "processId": os.getpid(),
                "rootUri": "file:///C:/Users/amazi/OneDrive/Documents/DGX",
                "capabilities": {
                    "textDocument": {
                        "completion": {
                            "completionItem": {"snippetSupport": True},
                            "contextSupport": True
                        }
                    }
                }
            })

    def send_lsp_request(self, method, dic):
        js = {"jsonrpc": "2.0", "id": self.msg_id, "method": method, "params": dic}
        self.msg_id += 1
        json_string = json.dumps(js)
        header = f"Content-Length: {len(json_string)}\r\n\r\n{json_string}"
        self.lsp_process.stdin.write(header.encode('utf-8'))
        self.lsp_process.stdin.flush()

    def send_lsp_notification(self, method, dic):
        js = {"jsonrpc": "2.0", "method": method, "params": dic}
        json_string = json.dumps(js)
        header = f"Content-Length: {len(json_string)}\r\n\r\n{json_string}"
        self.lsp_process.stdin.write(header.encode('utf-8'))
        self.lsp_process.stdin.flush()

    def initial_file_open(self, filepath, current_text):
        clean_path = filepath.replace("\\", "/")
        if not clean_path.startswith("file:///"): clean_path = "file:///" + clean_path

        open_payload = {
            "textDocument": {
                "uri": clean_path,
                "languageId": "python",
                "version": self.doc_version,
                "text": current_text
            }
        }
        self.send_lsp_notification("textDocument/didOpen", open_payload)
        print(f"LSP LIFECYCLE: Registered open path context for {clean_path}")

    @Slot(str, str)
    def notify_change(self, filepath, full_text):
        clean_path = filepath.replace("\\", "/")
        if not clean_path.startswith("file:///"): clean_path = "file:///" + clean_path

        self.doc_version += 1
        payload = {
            "textDocument": {"uri": clean_path, "version": self.doc_version},
            "contentChanges": [{"text": full_text}]
        }
        self.send_lsp_notification("textDocument/didChange", payload)

    @Slot(str, int, int, str)
    def request_completion(self, filepath, line, character, current_text):
        clean_path = filepath.replace("\\", "/")
        if not clean_path.startswith("file:///"): clean_path = "file:///" + clean_path

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


            for item in items_list:
                print(item)
                break
            suggestions = [
                {
                    "label": item.get("label", ""),
                    "insertText": item.get("insertText", item.get("label", "")),
                    "type": item.get("kind","")
                }
                for item in items_list
            ]
            self.completionsReceived .emit(suggestions)
            print(f"--- AUTOCOMPLETE DATAPACK RECEIVED: Emitted {len(suggestions)} items ---")

    @Slot(str)
    def open_file(self, filePath):

        print(filePath)

        with open(filePath, "r", encoding="utf-8") as f:
            content = f.read()

        self.fileOpened.emit(filePath,content)


    @Slot(str)
    def open_Workspace(self,path):

        if path.startswith("file:///"):
            parsed = urlparse(path)
            path = url2pathname(parsed.path)



        self.folder_path = path
        print(path)
       # self.folder_path =  self.folder_path[:c] + "\\"
        root , arr =  self.search_folder_items(self.folder_path)

        result = self.explorerList(arr, root)
        self.explorerContent.emit(result,self.folder_path)


    def search_folder_items(self, path):
        path = Path(path)

        files = list(path.iterdir())

        root_folder = path.name
        ls = []

        for file in files:
            if file.is_dir():
              root,childs =  self.search_folder_items(file)
              arr = [root,childs]
              ls.append(arr)
            else:
                ls.append(file.name)


        return root_folder, ls


    def explorerList(self,arry,pid):
        depth = 0
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

                final_list.extend(self.explorerList(li,folder_name))
            else:
                if "." not in item:
                    node["name"] = item
                    node["parentId"] = pid
                    node["type"] = "Folder"
                else:
                    node["name"] = item
                    node["parentId"] = pid
                    node["type"] = "File"
                final_list.append(node)

        return final_list



# ==============================================================================
# 4. APPLICATION ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)

    engine = QQmlApplicationEngine()
    backend = EditorBackend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("musicPlayer", musicPlayer)

    engine.load("main.qml")
    if not engine.rootObjects(): sys.exit(-1)

    root_window = engine.rootObjects()[0]
    root_window.setFlags(Qt.Window | Qt.FramelessWindowHint)
    sys.exit(app.exec())
