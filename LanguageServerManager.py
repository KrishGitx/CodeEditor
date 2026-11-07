"""
LanguageServerManager.py - Multi-Language Server Protocol (LSP) Engine & Process Profiler
Manages language server processes (C#, Python, Rust, Godot, Web), tracks real-time RAM/CPU footprint,
latency, throughput, and provides live profiling data to the Pod Studio debugger HUD.
"""

import os
import sys
import json
import time
import shutil
import socket
import gc
import subprocess
import threading
import queue
from pathlib import Path
from typing import Dict, Any, Optional, List

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QThread


# ==============================================================================
# 1. CROSS-PLATFORM PROCESS MEMORY INSPECTOR
# ==============================================================================
if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    def get_process_memory_mb(pid: int) -> float:
        if not pid or pid <= 0:
            return 0.0
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not handle:
            return 0.0
        try:
            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return round(counters.WorkingSetSize / (1024 * 1024), 2)
            return 0.0
        except Exception:
            return 0.0
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
else:
    def get_process_memory_mb(pid: int) -> float:
        if not pid or pid <= 0:
            return 0.0
        try:
            stat_file = f"/proc/{pid}/statm"
            if os.path.exists(stat_file):
                with open(stat_file, "r") as f:
                    parts = f.read().split()
                    rss_pages = int(parts[1])
                    page_size_kb = os.sysconf("SC_PAGE_SIZE") / 1024
                    return round((rss_pages * page_size_kb) / 1024, 2)
        except Exception:
            pass
        return 0.0


# ==============================================================================
# 2. LSP THREAD WORKERS
# ==============================================================================
class SubprocessLSPReader(QThread):
    message_received = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process
        self.running = True

    def run(self):
        while self.running and self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        break
                    continue

                line_str = line.decode("utf-8", errors="ignore").strip()
                if line_str.startswith("Content-Length:"):
                    try:
                        length = int(line_str.split("Content-Length:")[1].strip())
                    except ValueError:
                        continue

                    while True:
                        sep = self.process.stdout.readline()
                        if not sep or sep in (b"\r\n", b"\n", b""):
                            break

                    msg_bytes = self.process.stdout.read(length)
                    if msg_bytes:
                        try:
                            msg_obj = json.loads(msg_bytes.decode("utf-8"))
                            self.message_received.emit(msg_obj)
                        except Exception:
                            pass
            except Exception as e:
                self.error_occurred.emit(str(e))
                break

    def stop(self):
        self.running = False
        try:
            if self.process and self.process.stdout:
                self.process.stdout.close()
        except Exception:
            pass


class SubprocessLSPWriter(QThread):
    def __init__(self, process):
        super().__init__()
        self.process = process
        self.queue = queue.Queue()
        self.running = True

    def send(self, data: bytes):
        self.queue.put(data)

    def run(self):
        while self.running:
            try:
                data = self.queue.get(timeout=0.2)
                if data and self.process and self.process.poll() is None:
                    self.process.stdin.write(data)
                    self.process.stdin.flush()
                self.queue.task_done()
            except queue.Empty:
                if self.process and self.process.poll() is not None:
                    break
            except Exception:
                break

    def stop(self):
        self.running = False
        try:
            if self.process and self.process.stdout:
                self.process.stdout.close()
        except Exception:
            pass


# ==============================================================================
# 3. LANGUAGE SERVER INSTANCE TRACKER
# ==============================================================================
class ServerInstance:
    def __init__(self, server_id: str, name: str, language: str, command: str = "", transport: str = "stdio"):
        self.id = server_id
        self.name = name
        self.language = language
        self.command = command
        self.transport = transport
        self.process: Optional[subprocess.Popen] = None
        self.socket: Optional[socket.socket] = None
        self.reader_thread: Optional[SubprocessLSPReader] = None
        self.writer_thread: Optional[SubprocessLSPWriter] = None
        self.status = "STOPPED"  # RUNNING, IDLE, STARTING, STOPPED, ERROR
        self.pid = 0
        self.memory_mb = 0.0
        self.requests_sent = 0
        self.responses_received = 0
        self.avg_latency_ms = 0.0
        self.start_time = 0.0
        self.pending_requests: Dict[int, float] = {}  # req_id -> timestamp sent
        self.msg_id_counter = 1


# ==============================================================================
# 4. MAIN LANGUAGE SERVER MANAGER & PROFILER BACKEND
# ==============================================================================
class LanguageServerManager(QObject):
    profilerStatsUpdated = Signal(dict)
    completionsReceived = Signal(str, list)  # language, items
    logReceived = Signal(str, str, str)      # server_id, level, message

    def __init__(self, workspace_path: str = ""):
        super().__init__()
        self.workspace_path = workspace_path
        self.ide_pid = os.getpid()
        self.active_language = "csharp"
        self.servers: Dict[str, ServerInstance] = {}
        self.activity_log: List[Dict[str, Any]] = []

        # Initialize default registered servers
        self._register_default_servers()

        # Profiler Update Timer (Every 1.5 seconds)
        self.profiler_timer = QTimer(self)
        self.profiler_timer.setInterval(1500)
        self.profiler_timer.timeout.connect(self._on_profiler_tick)
        self.profiler_timer.start()

    def _register_default_servers(self):
        self.servers["csharp"] = ServerInstance(
            server_id="csharp",
            name="Unity & C# Language Server",
            language="csharp",
            command="LSPDaemon.py --lang csharp",
            transport="stdio"
        )
        self.servers["python"] = ServerInstance(
            server_id="python",
            name="Python Language Server",
            language="python",
            command="pylsp",
            transport="stdio"
        )
        self.servers["rust"] = ServerInstance(
            server_id="rust",
            name="Rust Analyzer",
            language="rust",
            command="rust-analyzer",
            transport="stdio"
        )
        self.servers["godot"] = ServerInstance(
            server_id="godot",
            name="Godot Engine LSP",
            language="gdscript",
            command="127.0.0.1:6005",
            transport="tcp"
        )
        self.servers["javascript"] = ServerInstance(
            server_id="javascript",
            name="TypeScript & React Language Server",
            language="javascript",
            command="LSPDaemon.py --lang javascript",
            transport="stdio"
        )

    def set_workspace_path(self, path: str):
        self.workspace_path = path

    def set_active_language(self, lang: str):
        clean_lang = (lang or "csharp").lower().strip()
        lang_alias = {
            "cs": "csharp", "c#": "csharp", "py": "python", "rs": "rust",
            "gd": "gdscript", "js": "javascript", "ts": "javascript", "tsx": "javascript", "jsx": "javascript"
        }
        self.active_language = lang_alias.get(clean_lang, clean_lang)
        # Auto-ensure server for active language is running
        self.start_server_for_language(self.active_language)

    @Slot(str)
    def start_server_for_language(self, language: str):
        clean_lang = language.lower().strip()
        server = self.servers.get(clean_lang)
        if not server:
            # Fallback alias check
            for s_id, s_inst in self.servers.items():
                if s_inst.language == clean_lang:
                    server = s_inst
                    break
        if not server:
            return

        if server.status == "RUNNING" and server.process and server.process.poll() is None:
            return

        self._spawn_server(server)

    def _spawn_server(self, server: ServerInstance):
        server.status = "STARTING"
        self._add_log(server.id, "info", f"Starting {server.name}...")

        # 1. Check for standalone native binary first
        binary_cmd = shutil.which(server.command) if not server.command.endswith(".py") else None

        cmd_list = []
        if binary_cmd:
            cmd_list = [binary_cmd]
        elif server.command.startswith("LSPDaemon.py") or not binary_cmd:
            # Launch self-contained autonomous Python daemon
            daemon_script = str(Path(__file__).parent / "LSPDaemon.py")
            cmd_list = [sys.executable, daemon_script, "--lang", server.language]
            if self.workspace_path:
                cmd_list.extend(["--workspace", self.workspace_path])

        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            parent_dir = str(Path(__file__).parent.resolve())
            env["PYTHONPATH"] = parent_dir + os.pathsep + env.get("PYTHONPATH", "")
            proc = subprocess.Popen(
                cmd_list,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
                env=env
            )
            server.process = proc
            server.pid = proc.pid
            server.status = "RUNNING"
            server.start_time = time.time()
            server.memory_mb = get_process_memory_mb(proc.pid)

            # Start background reader and writer threads
            reader = SubprocessLSPReader(proc)
            reader.message_received.connect(lambda msg, s=server: self._handle_message(s, msg))
            reader.start()
            server.reader_thread = reader

            writer = SubprocessLSPWriter(proc)
            writer.start()
            server.writer_thread = writer

            # Send standard LSP initialize
            root_uri = Path(self.workspace_path or os.getcwd()).as_uri()
            self._send_request(server, "initialize", {
                "processId": os.getpid(),
                "rootUri": root_uri,
                "capabilities": {
                    "textDocument": {
                        "completion": {"completionItem": {"snippetSupport": True}},
                        "hover": True
                    }
                }
            })
            self._add_log(server.id, "success", f"{server.name} active (PID: {server.pid})")
        except Exception as e:
            server.status = "ERROR"
            self._add_log(server.id, "error", f"Failed to start {server.name}: {e}")

    def _send_request(self, server: ServerInstance, method: str, params: dict) -> Optional[int]:
        if not server.process or server.process.poll() is not None:
            return None
        try:
            req_id = server.msg_id_counter
            server.msg_id_counter += 1
            server.pending_requests[req_id] = time.time()
            server.requests_sent += 1

            payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
            body = json.dumps(payload)
            header = f"Content-Length: {len(body)}\r\n\r\n{body}".encode("utf-8")

            if server.writer_thread and server.writer_thread.isRunning():
                server.writer_thread.send(header)
            else:
                server.process.stdin.write(header)
                server.process.stdin.flush()
            return req_id
        except Exception as e:
            self._add_log(server.id, "error", f"Send error: {e}")
            return None

    def _send_notification(self, server: ServerInstance, method: str, params: dict):
        if not server.process or server.process.poll() is not None:
            return
        try:
            payload = {"jsonrpc": "2.0", "method": method, "params": params}
            body = json.dumps(payload)
            header = f"Content-Length: {len(body)}\r\n\r\n{body}".encode("utf-8")
            if server.writer_thread and server.writer_thread.isRunning():
                server.writer_thread.send(header)
            else:
                server.process.stdin.write(header)
                server.process.stdin.flush()
        except Exception:
            pass

    def _handle_message(self, server: ServerInstance, msg: dict):
        msg_id = msg.get("id")
        if msg_id in server.pending_requests:
            sent_time = server.pending_requests.pop(msg_id)
            latency = (time.time() - sent_time) * 1000.0
            server.responses_received += 1
            # Moving average latency
            server.avg_latency_ms = round(
                latency if server.avg_latency_ms == 0 else (server.avg_latency_ms * 0.7 + latency * 0.3),
                1
            )

        if msg_id == 1:
            self._send_notification(server, "initialized", {})
            return

        if "result" in msg:
            res = msg.get("result") or {}
            items = []
            if isinstance(res, dict):
                items = res.get("items") or []
            elif isinstance(res, list):
                items = res

            if items:
                clean_items = []
                for it in items[:40]:
                    clean_items.append({
                        "label": it.get("label", ""),
                        "insertText": it.get("insertText", it.get("label", "")),
                        "type": self._kind_to_str(it.get("kind", 10))
                    })
                self.completionsReceived.emit(server.language, clean_items)

    def _kind_to_str(self, kind_num: int) -> str:
        mapping = {
            1: "text", 2: "method", 3: "function", 4: "constructor", 5: "field",
            6: "variable", 7: "class", 8: "interface", 9: "module", 10: "property"
        }
        return mapping.get(kind_num, "property")

    def notify_did_open(self, file_path: str, language: str, text: str):
        clean_lang = language.lower()
        server = self.servers.get(clean_lang)
        if server and server.status == "RUNNING":
            clean_uri = Path(file_path).as_uri() if not file_path.startswith("file://") else file_path
            self._send_notification(server, "textDocument/didOpen", {
                "textDocument": {
                    "uri": clean_uri,
                    "languageId": clean_lang,
                    "version": 1,
                    "text": text
                }
            })

    def notify_did_change(self, file_path: str, language: str, text: str, version: int):
        clean_lang = language.lower()
        server = self.servers.get(clean_lang)
        if server and server.status == "RUNNING":
            clean_uri = Path(file_path).as_uri() if not file_path.startswith("file://") else file_path
            self._send_notification(server, "textDocument/didChange", {
                "textDocument": {"uri": clean_uri, "version": version},
                "contentChanges": [{"text": text}]
            })

    def request_completion(self, file_path: str, language: str, line: int, char: int):
        clean_lang = (language or "").lower().strip()
        lang_alias = {
            "cs": "csharp", "c#": "csharp", "py": "python", "rs": "rust",
            "gd": "gdscript", "js": "javascript", "ts": "javascript", "tsx": "javascript", "jsx": "javascript"
        }
        target_lang = lang_alias.get(clean_lang, clean_lang)
        server = self.servers.get(target_lang)
        if server and server.status == "RUNNING":
            clean_uri = Path(file_path).as_uri() if not file_path.startswith("file://") else file_path
            self._send_request(server, "textDocument/completion", {
                "textDocument": {"uri": clean_uri},
                "position": {"line": line, "character": char}
            })

    @Slot(str)
    def restart_server(self, server_id: str):
        server = self.servers.get(server_id)
        if server:
            self._stop_server_instance(server)
            self._spawn_server(server)

    @Slot(str)
    def stop_server(self, server_id: str):
        server = self.servers.get(server_id)
        if server:
            self._stop_server_instance(server)

    def stop_all_servers(self):
        for server in list(self.servers.values()):
            self._stop_server_instance(server)

    def _stop_server_instance(self, server: ServerInstance):
        if server.writer_thread:
            server.writer_thread.stop()
            server.writer_thread.wait(300)
            server.writer_thread = None
        if server.reader_thread:
            server.reader_thread.stop()
            server.reader_thread.wait(300)
            server.reader_thread = None
        if server.process:
            try:
                server.process.terminate()
                server.process.kill()
            except Exception:
                pass
            server.process = None
        server.status = "STOPPED"
        server.pid = 0
        server.memory_mb = 0.0
        self._add_log(server.id, "info", f"{server.name} stopped.")

    @Slot(result=float)
    def force_gc_collect(self) -> float:
        before = get_process_memory_mb(self.ide_pid)
        gc.collect()
        after = get_process_memory_mb(self.ide_pid)
        freed = max(0.0, round(before - after, 2))
        self._add_log("ide", "info", f"Garbage Collection freed {freed} MB")
        return freed

    def _on_profiler_tick(self):
        ide_ram = get_process_memory_mb(self.ide_pid)
        total_lsp_ram = 0.0

        for server in self.servers.values():
            if server.process and server.process.poll() is None:
                mem = get_process_memory_mb(server.pid)
                server.memory_mb = mem
                total_lsp_ram += mem
                if server.status != "RUNNING":
                    server.status = "RUNNING"
            else:
                server.memory_mb = 0.0
                if server.status not in ("STOPPED", "ERROR"):
                    server.status = "STOPPED"

        stats = self.get_profiler_stats()
        self.profilerStatsUpdated.emit(stats)

    @Slot(result="QVariantMap")
    def get_profiler_stats(self) -> Dict[str, Any]:
        ide_ram = get_process_memory_mb(self.ide_pid)
        total_lsp_ram = 0.0
        servers_list = []

        for server in self.servers.values():
            total_lsp_ram += server.memory_mb
            uptime_sec = int(time.time() - server.start_time) if server.status == "RUNNING" else 0
            mins, secs = divmod(uptime_sec, 60)
            uptime_str = f"{mins:02d}:{secs:02d}"

            servers_list.append({
                "id": server.id,
                "name": server.name,
                "language": server.language,
                "status": server.status,
                "pid": server.pid,
                "memoryMb": server.memory_mb,
                "requestsSent": server.requests_sent,
                "responsesReceived": server.responses_received,
                "avgLatencyMs": server.avg_latency_ms,
                "uptime": uptime_str,
                "transport": server.transport,
                "command": server.command
            })

        active_srv = self.servers.get(self.active_language)
        active_name = active_srv.name if active_srv else "Idle"
        active_ram = active_srv.memory_mb if active_srv else 0.0

        return {
            "idePid": self.ide_pid,
            "ideRamMb": ide_ram,
            "lspRamMb": round(total_lsp_ram, 2),
            "totalRamMb": round(ide_ram + total_lsp_ram, 2),
            "activeLanguage": self.active_language,
            "activeServerName": active_name,
            "activeServerRam": active_ram,
            "servers": servers_list,
            "recentLogs": self.activity_log[-8:]
        }

    def _add_log(self, source: str, level: str, message: str):
        t_str = time.strftime("%H:%M:%S")
        entry = {"time": t_str, "source": source, "level": level, "message": message}
        self.activity_log.append(entry)
        if len(self.activity_log) > 50:
            self.activity_log.pop(0)
        self.logReceived.emit(source, level, message)
