"""
TerminalBackend.py - Real interactive system terminal backend for PySide6 / QML
Executes system commands and interacts with PowerShell / CMD / Bash without blocking the UI.
Supports single and split/multi-session interactive terminals.
"""

import sys
import os
import time
import subprocess
import threading
from PySide6.QtCore import QObject, Signal, Slot

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ('dwSize', ctypes.wintypes.DWORD),
            ('cntUsage', ctypes.wintypes.DWORD),
            ('th32ProcessID', ctypes.wintypes.DWORD),
            ('th32DefaultHeapID', ctypes.POINTER(ctypes.wintypes.ULONG)),
            ('th32ModuleID', ctypes.wintypes.DWORD),
            ('cntThreads', ctypes.wintypes.DWORD),
            ('th32ParentProcessID', ctypes.wintypes.DWORD),
            ('pcPriClassBase', ctypes.c_long),
            ('dwFlags', ctypes.wintypes.DWORD),
            ('szExeFile', ctypes.c_char * 260)
        ]


class SingleTerminalSession:
    def __init__(self, session_id, initial_cwd, output_callback, finished_callback, cwd_callback, running_callback):
        self.session_id = session_id
        self.cwd = os.path.abspath(initial_cwd or os.getcwd())
        self.process = None
        self.is_running = False
        self.is_command_running = False
        self.output_callback = output_callback
        self.finished_callback = finished_callback
        self.cwd_callback = cwd_callback
        self.running_callback = running_callback
        self._start_shell()

    def _get_child_pids(self, parent_pid):
        if sys.platform != "win32":
            return []
        try:
            snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(2, 0)
            entry = PROCESSENTRY32()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
            children = []
            if ctypes.windll.kernel32.Process32First(snapshot, ctypes.byref(entry)):
                while True:
                    if entry.th32ParentProcessID == parent_pid:
                        children.append((entry.th32ProcessID, entry.szExeFile.decode('utf-8', errors='ignore')))
                    if not ctypes.windll.kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                        break
            ctypes.windll.kernel32.CloseHandle(snapshot)
            return children
        except Exception:
            return []

    def _start_shell(self):
        try:
            if sys.platform == "win32":
                shell_cmd = ["powershell.exe", "-NoLogo", "-NoExit", "-ExecutionPolicy", "Bypass"]
            else:
                shell_cmd = [os.environ.get("SHELL", "/bin/bash")]

            self.process = subprocess.Popen(
                shell_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self.cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=0,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self.is_running = True

            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()
        except Exception as e:
            self.output_callback(self.session_id, f"Error starting terminal: {str(e)}\n")

    def _read_output(self):
        buf = ""
        while self.is_running and self.process and self.process.stdout:
            try:
                chunk = self.process.stdout.read(1)
                if not chunk:
                    if self.process.poll() is not None:
                        break
                    time.sleep(0.01)
                    continue

                buf += chunk
                if len(buf) > 2048:
                    buf = buf[-512:]

                if buf.endswith("> ") or buf.endswith(">\r\n") or buf.endswith(">\n") or (buf.endswith("$ ") and not buf.endswith("# ")):
                    if self.is_command_running:
                        self.is_command_running = False
                        self.running_callback(self.session_id, False)
                        self.finished_callback(self.session_id, 0)

                self.output_callback(self.session_id, chunk)
            except Exception:
                break

    def send_command(self, command):
        if not self.process or self.process.poll() is not None:
            self._start_shell()

        cmd_strip = command.strip()
        if cmd_strip.lower().startswith("cd ") or cmd_strip.lower().startswith("chdir "):
            parts = cmd_strip.split(" ", 1)
            if len(parts) > 1:
                target = parts[1].strip().strip('"').strip("'")
                if target == "..":
                    new_dir = os.path.dirname(self.cwd)
                    if os.path.isdir(new_dir):
                        self.cwd = new_dir
                        self.cwd_callback(self.session_id, self.cwd)
                elif target in ("\\", "/"):
                    drive = os.path.splitdrive(self.cwd)[0] or "C:"
                    self.cwd = drive + "\\"
                    self.cwd_callback(self.session_id, self.cwd)
                elif os.path.isabs(target) and os.path.isdir(target):
                    self.cwd = os.path.normpath(target)
                    self.cwd_callback(self.session_id, self.cwd)
                else:
                    combined = os.path.normpath(os.path.join(self.cwd, target))
                    if os.path.isdir(combined):
                        self.cwd = combined
                        self.cwd_callback(self.session_id, self.cwd)

        if cmd_strip:
            self.is_command_running = True
            self.running_callback(self.session_id, True)

        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
            except Exception as e:
                self.is_command_running = False
                self.running_callback(self.session_id, False)
                self.output_callback(self.session_id, f"\n[Execution error: {str(e)}]\n")

    def send_interrupt(self):
        if self.process and self.process.poll() is None:
            if sys.platform == "win32":
                try:
                    children = self._get_child_pids(self.process.pid)
                    for cpid, _ in children:
                        handle = ctypes.windll.kernel32.OpenProcess(1, False, cpid)
                        if handle:
                            ctypes.windll.kernel32.TerminateProcess(handle, 1)
                            ctypes.windll.kernel32.CloseHandle(handle)
                except Exception:
                    pass
            try:
                if self.process.stdin:
                    self.process.stdin.write("\x03\n")
                    self.process.stdin.flush()
            except Exception:
                pass
        self.is_command_running = False
        self.running_callback(self.session_id, False)

    def restart(self):
        if self.process:
            try:
                self.process.kill()
            except Exception:
                pass
        self.is_command_running = False
        self.running_callback(self.session_id, False)
        self._start_shell()

    def close(self):
        self.is_running = False
        if self.process:
            try:
                self.process.kill()
            except Exception:
                pass


class TerminalBackend(QObject):
    # Primary session signals (Backwards Compatible)
    outputReceived = Signal(str)
    commandFinished = Signal(int)
    cwdChanged = Signal(str)
    commandRunningChanged = Signal(bool)

    # Multi-session / Split Terminal signals
    sessionOutputReceived = Signal(int, str)
    sessionCommandFinished = Signal(int, int)
    sessionCwdChanged = Signal(int, str)
    sessionCommandRunningChanged = Signal(int, bool)

    def __init__(self, initial_cwd=None):
        super().__init__()
        self.default_cwd = os.path.abspath(initial_cwd or os.getcwd())
        self.sessions = {}
        self.next_session_id = 0

        # Initialize primary session 0
        self.create_session(self.default_cwd)

    def _on_output(self, session_id, text):
        if session_id == 0:
            self.outputReceived.emit(text)
        self.sessionOutputReceived.emit(session_id, text)

    def _on_finished(self, session_id, code):
        if session_id == 0:
            self.commandFinished.emit(code)
        self.sessionCommandFinished.emit(session_id, code)

    def _on_cwd(self, session_id, cwd):
        if session_id == 0:
            self.cwdChanged.emit(cwd)
        self.sessionCwdChanged.emit(session_id, cwd)

    def _on_running(self, session_id, running):
        if session_id == 0:
            self.commandRunningChanged.emit(running)
        self.sessionCommandRunningChanged.emit(session_id, running)

    @Slot(result=int)
    @Slot(str, result=int)
    def create_session(self, cwd=None):
        sid = self.next_session_id
        self.next_session_id += 1
        init_cwd = cwd or self.default_cwd
        session = SingleTerminalSession(
            sid,
            init_cwd,
            self._on_output,
            self._on_finished,
            self._on_cwd,
            self._on_running
        )
        self.sessions[sid] = session
        return sid

    @Slot(result=list)
    def get_sessions(self):
        return list(self.sessions.keys())

    @Slot(int)
    def close_session(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id].close()
            if session_id != 0:
                del self.sessions[session_id]

    @Slot(int, str)
    def send_session_command(self, session_id, command):
        if session_id in self.sessions:
            self.sessions[session_id].send_command(command)
        elif session_id == 0:
            self.send_command(command)

    @Slot(int)
    def send_session_interrupt(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id].send_interrupt()

    @Slot(int)
    def restart_session(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id].restart()

    @Slot(int, result=str)
    def get_session_cwd(self, session_id):
        if session_id in self.sessions:
            return self.sessions[session_id].cwd
        return self.get_cwd()

    @Slot(int, result=str)
    def get_session_prompt(self, session_id):
        cwd = self.get_session_cwd(session_id)
        if sys.platform == "win32":
            return f"PS {cwd}> "
        return f"{cwd}$ "

    @Slot(int, result=bool)
    def is_session_running_cmd(self, session_id):
        if session_id in self.sessions:
            return self.sessions[session_id].is_command_running
        return False

    # Primary Session Methods (Backwards Compatible)
    @property
    def cwd(self):
        return self.sessions[0].cwd if 0 in self.sessions else self.default_cwd

    @cwd.setter
    def cwd(self, val):
        if 0 in self.sessions:
            self.sessions[0].cwd = val

    @property
    def is_command_running(self):
        return self.sessions[0].is_command_running if 0 in self.sessions else False

    @Slot(list, str)
    @Slot(list)
    def execute_command_sequence(self, commands, action_type="bash"):
        """
        Executes a sequence of commands sequentially in the primary terminal session.
        Stops on first command failure.
        """
        self.execute_session_command_sequence(0, commands, action_type)

    @Slot(int, list, str)
    @Slot(int, list)
    def execute_session_command_sequence(self, session_id, commands, action_type="bash"):
        """
        Executes a sequence of commands sequentially in the specified terminal session.
        Stops immediately on failure of any command in the sequence.
        """
        if not commands:
            return

        clean_cmds = [str(c).strip() for c in commands if str(c).strip()]
        if not clean_cmds:
            return

        act_type = (action_type or "bash").lower().strip()

        if session_id not in self.sessions:
            if session_id == 0:
                self.create_session(self.default_cwd)
            else:
                return

        session = self.sessions[session_id]
        if not session.process or session.process.poll() is not None:
            session._start_shell()

        # Single command: execute directly
        if len(clean_cmds) == 1:
            session.send_command(clean_cmds[0])
            return

        # Multiple commands: sequential execution with failure stopping
        if sys.platform == "win32":
            if act_type == "cmd":
                # In CMD shell, && runs the next command only if previous exited with 0
                joined = " && ".join(clean_cmds)
                session.send_command(f'cmd /c "{joined}"')
            else:
                # In PowerShell, chain each command conditionally on $? and $LASTEXITCODE
                nested = ""
                for cmd in reversed(clean_cmds):
                    if not nested:
                        nested = cmd
                    else:
                        nested = f'{cmd}; if (($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null) -and $?) {{ {nested} }}'
                session.send_command(nested)
        else:
            # Unix / macOS (bash/zsh/sh):
            joined = " && ".join(clean_cmds)
            session.send_command(joined)

    @Slot(str)
    def send_command(self, command):
        if 0 in self.sessions:
            self.sessions[0].send_command(command)

    @Slot(result=bool)
    def is_running_cmd(self):
        return self.is_command_running

    @Slot(result=str)
    def get_cwd(self):
        return self.cwd

    @Slot(result=str)
    def get_prompt(self):
        if sys.platform == "win32":
            return f"PS {self.cwd}> "
        return f"{self.cwd}$ "

    @Slot()
    def send_interrupt(self):
        if 0 in self.sessions:
            self.sessions[0].send_interrupt()

    @Slot()
    def clear(self):
        self.outputReceived.emit("__CLEAR_BUFFER__")
        self.sessionOutputReceived.emit(0, "__CLEAR_BUFFER__")

    @Slot(int)
    def clear_session(self, session_id):
        if session_id == 0:
            self.clear()
        else:
            self.sessionOutputReceived.emit(session_id, "__CLEAR_BUFFER__")

    @Slot()
    def restart(self):
        if 0 in self.sessions:
            self.sessions[0].restart()

    @Slot(str)
    def set_cwd(self, path):
        if os.path.exists(path):
            abs_p = os.path.abspath(path)
            self.cwd = abs_p
            self.cwdChanged.emit(abs_p)
            self.send_command(f'cd "{path}"')
