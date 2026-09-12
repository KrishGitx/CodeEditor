"""
TerminalBackend.py - Real interactive system terminal backend for PySide6 / QML
Executes system commands and interacts with PowerShell / CMD / Bash without blocking the UI.
"""

import sys
import os
import subprocess
import threading
import queue
from PySide6.QtCore import QObject, Signal, Slot


class TerminalBackend(QObject):
    outputReceived = Signal(str)
    commandFinished = Signal(int)

    def __init__(self, initial_cwd=None):
        super().__init__()
        self.cwd = initial_cwd or os.getcwd()
        self.process = None
        self.is_running = False
        self._start_shell()

    def _start_shell(self):
        try:
            # On Windows, start powershell with NoLogo
            if sys.platform == "win32":
                shell_cmd = ["powershell.exe", "-NoLogo", "-NoExit"]
            else:
                shell_cmd = [os.environ.get("SHELL", "/bin/bash")]

            self.process = subprocess.Popen(
                shell_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self.cwd,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self.is_running = True

            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()
            self.outputReceived.emit(f"Terminal session started in {self.cwd}\n")
        except Exception as e:
            self.outputReceived.emit(f"Error starting terminal: {str(e)}\n")

    def _read_output(self):
        while self.is_running and self.process and self.process.stdout:
            try:
                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        break
                    continue
                self.outputReceived.emit(line)
            except Exception as e:
                break

    @Slot(str)
    def send_command(self, command):
        if not self.process or self.process.poll() is not None:
            self._start_shell()

        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
            except Exception as e:
                self.outputReceived.emit(f"\n[Execution error: {str(e)}]\n")

    @Slot()
    def clear(self):
        # Notify terminal to clear buffer
        self.outputReceived.emit("__CLEAR_BUFFER__")

    @Slot()
    def restart(self):
        if self.process:
            try:
                self.process.kill()
            except:
                pass
        self._start_shell()

    @Slot(str)
    def set_cwd(self, path):
        if os.path.exists(path):
            self.cwd = path
            self.send_command(f'cd "{path}"')
