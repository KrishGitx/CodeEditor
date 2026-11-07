import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickWindow
from PySide6.QtCore import Qt, QAbstractNativeEventFilter
import time

user32 = ctypes.windll.user32
app = QApplication([])
win = QQuickWindow()
win.setFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
win.setWidth(800)
win.setHeight(600)
win.show()
hwnd = int(win.winId())

GWL_STYLE = -16
WS_THICKFRAME = 0x00040000
WS_CAPTION = 0x00C00000
WS_MAXIMIZEBOX = 0x00010000
WS_MINIMIZEBOX = 0x00020000
WS_SYSMENU = 0x00080000

style = user32.GetWindowLongW(hwnd, GWL_STYLE)
style |= (WS_THICKFRAME | WS_CAPTION | WS_MAXIMIZEBOX | WS_MINIMIZEBOX | WS_SYSMENU)
user32.SetWindowLongW(hwnd, GWL_STYLE, style)

class MARGINS(ctypes.Structure):
    _fields_ = [("cxLeftWidth", ctypes.c_int), ("cxRightWidth", ctypes.c_int), ("cyTopHeight", ctypes.c_int), ("cyBottomHeight", ctypes.c_int)]
margins = MARGINS(1, 1, 1, 1)
ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

class NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [("rgrc", RECT * 3), ("lppos", ctypes.c_void_p)]

class WinFilter(QAbstractNativeEventFilter):
    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.hWnd == hwnd:
                if msg.message == 0x0083 and msg.wParam: # WM_NCCALCSIZE
                    if user32.IsZoomed(hwnd):
                        hMon = user32.MonitorFromWindow(hwnd, 2)
                        mi = MONITORINFO()
                        mi.cbSize = ctypes.sizeof(MONITORINFO)
                        if user32.GetMonitorInfoW(hMon, ctypes.byref(mi)):
                            params = NCCALCSIZE_PARAMS.from_address(msg.lParam)
                            params.rgrc[0] = mi.rcWork
                            return True, 0
                    return True, 0
        return False, 0

wf = WinFilter()
app.installNativeEventFilter(wf)

user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0020)
win.showMaximized()
for _ in range(10):
    app.processEvents()
    time.sleep(0.05)

cr = RECT()
user32.GetClientRect(hwnd, ctypes.byref(cr))
hMon = user32.MonitorFromWindow(hwnd, 2)
mi = MONITORINFO()
mi.cbSize = ctypes.sizeof(MONITORINFO)
user32.GetMonitorInfoW(hMon, ctypes.byref(mi))

print(f"WorkArea: [{mi.rcWork.left}, {mi.rcWork.top}, {mi.rcWork.right}, {mi.rcWork.bottom}]")
print(f"ClientRect: [{cr.left}, {cr.top}, {cr.right}, {cr.bottom}]")
print(f"Qt geometry: x={win.x()}, y={win.y()}, w={win.width()}, h={win.height()}")
win.close()
