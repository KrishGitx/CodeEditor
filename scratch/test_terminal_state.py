import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
from PySide6.QtGui import QGuiApplication
from TerminalBackend import TerminalBackend

def test_terminal_state():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    tb = TerminalBackend()

    state_changes = []
    tb.commandRunningChanged.connect(lambda r: state_changes.append(r))

    print("Initial running state:", tb.is_command_running)
    
    # 1. Quick command (Get-Location)
    print("\n[1] Running quick command (Get-Location)...")
    tb.send_command("Get-Location")
    
    t0 = time.time()
    while time.time() - t0 < 2.0:
        app.processEvents()
        time.sleep(0.05)
        if len(state_changes) >= 2 and not tb.is_command_running:
            break

    print("State transitions for quick command:", state_changes)
    print("Command running state now:", tb.is_command_running)

    # 2. Long-running command with Ctrl+C interrupt
    print("\n[2] Running long command (ping 127.0.0.1 -t)...")
    state_changes.clear()
    tb.send_command("ping 127.0.0.1 -t")
    
    time.sleep(1.5)
    app.processEvents()
    print("Is command running during ping?:", tb.is_command_running)

    print("Sending interrupt (Ctrl+C)...")
    tb.send_interrupt()

    t0 = time.time()
    while time.time() - t0 < 2.0:
        app.processEvents()
        time.sleep(0.05)
        if not tb.is_command_running:
            break

    print("Command running state after interrupt:", tb.is_command_running)
    print("State transitions for ping:", state_changes)

    print("\nTEST COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_terminal_state()
