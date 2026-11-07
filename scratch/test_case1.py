import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickWindow
from PySide6.QtCore import Qt, QAbstractNativeEventFilter
import time

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MINMAXINFO(ctypes.Structure):
    _fields_ = [
        ("ptReserved", POINT),
        ("ptMaxSize", POINT),
        ("ptMaxPosition", POINT),
        ("ptMinTrackSize", POINT),
        ("ptMaxTrackSize", POINT),
    ]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]

class NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [("rgrc", RECT * 3), ("lppos", ctypes.c_void_p)]

app = QApplication([])
win = QQuickWindow()
win.setFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
win.setWidth(800)
win.setHeight(600)
win.show()
hwnd = int(win.winId())

GWL_STYLE = -16
WS_THICKFRAME = 0x00040000
WS_MAXIMIZEBOX = 0x00010000
style = user32.GetWindowLongW(hwnd, GWL_STYLE)
style |= (WS_THICKFRAME | WS_MAXIMIZEBOX)
user32.SetWindowLongW(hwnd, GWL_STYLE, style)

# Case 1: Standard Chromium / VS Code frameless approach:
# In WM_NCCALCSIZE:
# When maximized, params.rgrc[0] comes in with the 8px border (e.g. left=-8, top=-8, right=1928, bottom=1040).
# If we deflate params.rgrc[0] by the border (or set params.rgrc[0] = mi.rcWork), the client rect fills rcWork exactly!
# Let's see what WM_NCCALCSIZE receives when WM_GETMINMAXINFO is NOT handled:

class TestFilter(QAbstractNativeEventFilter):
    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.hWnd == hwnd:
                if msg.message == 0x0083 and msg.wParam: # WM_NCCALCSIZE
                    if user32.IsZoomed(hwnd):
                        params = NCCALCSIZE_PARAMS.from_address(msg.lParam)
                        print(f"Incoming rgrc[0] without WM_GETMINMAXINFO: [{params.rgrc[0].left}, {params.rgrc[0].top}, {params.rgrc[0].right}, {params.rgrc[0].bottom}]")
                        hMon = user32.MonitorFromWindow(hwnd, 2)
                        mi = MONITORINFO()
                        mi.cbSize = ctypes.sizeof(MONITORINFO)
                        user32.GetMonitorInfoW(hMon, ctypes.byref(mi))
                        params.rgrc[0] = mi.rcWork
                        return True, 0
                    return True, 0
        return False, 0

tf = TestFilter()
app.installNativeEventFilter(tf)

win.showMaximized()
for _ in range(10):
    app.processEvents()
    time.sleep(0.05)

wr = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(wr))
cr = RECT()
user32.GetClientRect(hwnd, ctypes.byref(cr))

hMon = user32.MonitorFromWindow(hwnd, 2)
mi = MONITORINFO()
mi.cbSize = ctypes.sizeof(MONITORINFO)
user32.GetMonitorInfoW(hMon, ctypes.byref(mi))

print(f"Monitor: [{mi.rcMonitor.left}, {mi.rcMonitor.top}, {mi.rcMonitor.right}, {mi.rcMonitor.bottom}]")
print(f"WorkArea: [{mi.rcWork.left}, {mi.rcWork.top}, {mi.rcWork.right}, {mi.rcWork.bottom}]")
print(f"WindowRect: [{wr.left}, {wr.top}, {wr.right}, {wr.bottom}]")
print(f"ClientRect: [{cr.left}, {cr.top}, {cr.right}, {cr.bottom}]")
print(f"Qt geometry: x={win.x()}, y={win.y()}, w={win.width()}, h={win.height()}")
win.close()

