"""
LSPDaemon.py - Autonomous Multi-Language Server Daemon for Pod Studio
Runs as an independent OS background subprocess, implementing standard Language Server Protocol (LSP)
over JSON-RPC (stdin/stdout). Measures true memory, response latency, and handles completions.
"""

import sys
import os
import json
import re
import argparse
from typing import Dict, Any, List

# Add parent directory to sys.path so it can access ProjectCompletionEngine
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from ProjectCompletionEngine import ProjectCompletionEngine
    ENGINE = ProjectCompletionEngine()
except Exception:
    ENGINE = None


class LSPDaemon:
    def __init__(self, language: str = "csharp", workspace_root: str = ""):
        self.language = language.lower()
        self.workspace_root = workspace_root
        self.documents: Dict[str, str] = {}
        self.engine = ENGINE
        if self.engine and self.workspace_root and os.path.exists(self.workspace_root):
            self.engine.index_workspace(self.workspace_root)

    def run(self):
        stdin = sys.stdin.buffer
        stdout = sys.stdout.buffer

        while True:
            try:
                line = stdin.readline()
                if not line:
                    break

                line_str = line.decode("utf-8", errors="ignore").strip()
                if line_str.startswith("Content-Length:"):
                    try:
                        content_length = int(line_str.split("Content-Length:")[1].strip())
                    except ValueError:
                        continue

                    # Read empty lines separating headers from body
                    while True:
                        sep = stdin.readline()
                        if not sep or sep in (b"\r\n", b"\n", b""):
                            break

                    body_bytes = stdin.read(content_length)
                    if not body_bytes:
                        break

                    try:
                        msg = json.loads(body_bytes.decode("utf-8"))
                        self.handle_message(msg, stdout)
                    except Exception as err:
                        pass
            except Exception:
                break

    def send_response(self, stdout, msg_id: Any, result: Any = None, error: Any = None):
        res = {"jsonrpc": "2.0", "id": msg_id}
        if error:
            res["error"] = error
        else:
            res["result"] = result
        self._write_msg(stdout, res)

    def _write_msg(self, stdout, obj: dict):
        body_bytes = json.dumps(obj).encode("utf-8")
        header = f"Content-Length: {len(body_bytes)}\r\n\r\n".encode("utf-8")
        stdout.write(header + body_bytes)
        stdout.flush()

    def handle_message(self, msg: dict, stdout):
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            root_uri = params.get("rootUri", "")
            if root_uri and self.engine:
                clean_root = root_uri.replace("file:///", "").replace("file://", "")
                if os.path.exists(clean_root):
                    self.workspace_root = clean_root
                    self.engine.index_workspace(clean_root)

            capabilities = {
                "textDocumentSync": 1,  # Full sync
                "completionProvider": {
                    "resolveProvider": False,
                    "triggerCharacters": [".", "(", "<", '"', ":", " "]
                },
                "hoverProvider": True
            }
            self.send_response(stdout, msg_id, {"capabilities": capabilities})

        elif method == "initialized":
            # Handshake complete
            pass

        elif method == "textDocument/didOpen":
            text_doc = params.get("textDocument", {})
            uri = text_doc.get("uri", "")
            text = text_doc.get("text", "")
            self.documents[uri] = text

        elif method == "textDocument/didChange":
            text_doc = params.get("textDocument", {})
            uri = text_doc.get("uri", "")
            changes = params.get("contentChanges", [])
            if changes:
                # Full sync: last change has the complete text
                self.documents[uri] = changes[-1].get("text", "")

        elif method == "textDocument/completion":
            text_doc = params.get("textDocument", {})
            uri = text_doc.get("uri", "")
            pos = params.get("position", {})
            line_idx = pos.get("line", 0)
            char_idx = pos.get("character", 0)

            doc_text = self.documents.get(uri, "")
            items = self.compute_completions(uri, line_idx, char_idx, doc_text)
            self.send_response(stdout, msg_id, {"isIncomplete": False, "items": items})

        elif method == "shutdown":
            self.send_response(stdout, msg_id, None)

        elif method == "exit":
            sys.exit(0)

    def compute_completions(self, uri: str, line: int, char: int, doc_text: str) -> List[Dict[str, Any]]:
        target_obj = ""
        prefix = ""

        if doc_text:
            lines = doc_text.splitlines()
            if 0 <= line < len(lines):
                cur_line = lines[line]
                col = min(char, len(cur_line))
                chunk = cur_line[:col]
                m_dot = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z0-9_]*)$', chunk)
                if m_dot:
                    target_obj = m_dot.group(1)
                    prefix = m_dot.group(2)
                else:
                    m_word = re.search(r'([a-zA-Z0-9_]+)$', chunk)
                    if m_word:
                        prefix = m_word.group(1)

        clean_path = uri.replace("file:///", "").replace("file://", "")

        if self.engine:
            raw_items = self.engine.get_completions(clean_path, line, char, target_obj, prefix, doc_text)
            lsp_items = []
            for item in raw_items:
                kind_str = item.get("type", "property")
                # Map to standard LSP CompletionItemKind (2 = Method, 6 = Variable, 7 = Class, 10 = Property)
                kind_map = {
                    "method": 2, "function": 3, "constructor": 4, "field": 5,
                    "variable": 6, "class": 7, "interface": 8, "module": 9, "property": 10
                }
                lsp_kind = kind_map.get(kind_str, 10)
                lsp_items.append({
                    "label": item.get("label", ""),
                    "kind": lsp_kind,
                    "insertText": item.get("insertText", item.get("label", "")),
                    "detail": f"{self.language.upper()} {kind_str}"
                })
            return lsp_items

        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pod Studio LSP Daemon")
    parser.add_argument("--lang", default="csharp", help="Target language")
    parser.add_argument("--workspace", default="", help="Workspace root directory")
    args = parser.parse_args()

    daemon = LSPDaemon(language=args.lang, workspace_root=args.workspace)
    daemon.run()

