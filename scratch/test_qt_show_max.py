from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
import ctypes
from ctypes import wintypes
import time

app = QApplication([])
engine = QQmlApplicationEngine()
qml = b'''
import QtQuick 2.15
import QtQuick.Window 2.15

Window {
    id: win
    width: 800
    height: 600
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
    visible: true
    color: "#202020"
}
'''
engine.loadData(qml)
win = engine.rootObjects()[0]
hwnd = int(win.winId())

# Check before showMaximized
print("Calling win.showMaximized()...")
win.showMaximized()
for _ in range(10):
    app.processEvents()
    time.sleep(0.05)

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

wr = RECT()
ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(wr))

user32 = ctypes.windll.user32
class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]

hMon = user32.MonitorFromWindow(hwnd, 2)
mi = MONITORINFO()
mi.cbSize = ctypes.sizeof(MONITORINFO)
user32.GetMonitorInfoW(hMon, ctypes.byref(mi))

print(f"WorkArea: [{mi.rcWork.left}, {mi.rcWork.top}, {mi.rcWork.right}, {mi.rcWork.bottom}]")
print(f"WindowRect: [{wr.left}, {wr.top}, {wr.right}, {wr.bottom}]")
print(f"Difference: left={wr.left - mi.rcWork.left}, top={wr.top - mi.rcWork.top}, right={wr.right - mi.rcWork.right}, bottom={wr.bottom - mi.rcWork.bottom}")
