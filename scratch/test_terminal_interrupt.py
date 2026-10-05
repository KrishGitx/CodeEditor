import subprocess
import time
import threading
import os
import sys
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

def get_child_pids(parent_pid):
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

def test_interrupt():
    p = subprocess.Popen(
        ['powershell.exe', '-NoLogo', '-NoExit', '-ExecutionPolicy', 'Bypass'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    output = []
    def read_loop():
        for line in iter(p.stdout.readline, ''):
            output.append(line)
            print('STREAM:', repr(line))

    t = threading.Thread(target=read_loop, daemon=True)
    t.start()

    print('PowerShell PID:', p.pid)
    time.sleep(0.5)
    p.stdin.write('ping 127.0.0.1 -t\n')
    p.stdin.flush()
    
    time.sleep(2)
    children = get_child_pids(p.pid)
    print('Found children:', children)
    for cpid, name in children:
        print(f'Terminating child PID {cpid} ({name})...')
        handle = ctypes.windll.kernel32.OpenProcess(1, False, cpid)
        if handle:
            ctypes.windll.kernel32.TerminateProcess(handle, 1)
            ctypes.windll.kernel32.CloseHandle(handle)

    time.sleep(0.5)
    p.stdin.write('echo AFTER_INTERRUPT_SUCCESS\n')
    p.stdin.flush()
    time.sleep(1)
    p.kill()

if __name__ == '__main__':
    test_interrupt()
