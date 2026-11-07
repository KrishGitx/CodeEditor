import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl, QAbstractNativeEventFilter, Qt

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
view = QQuickView()
view.setFlag(Qt.FramelessWindowHint, True)
view.setWidth(800)
view.setHeight(600)
view.show()
hwnd = int(view.winId())

# Get monitor info
hMonitor = user32.MonitorFromWindow(hwnd, 2)
mi = MONITORINFO()
mi.cbSize = ctypes.sizeof(MONITORINFO)
user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
print(f"Monitor: [{mi.rcMonitor.left}, {mi.rcMonitor.top}, {mi.rcMonitor.right}, {mi.rcMonitor.bottom}]")
print(f"WorkArea: [{mi.rcWork.left}, {mi.rcWork.top}, {mi.rcWork.right}, {mi.rcWork.bottom}]")

# Now check current main.py approach
GWL_STYLE = -16
WS_THICKFRAME = 0x00040000
WS_MAXIMIZEBOX = 0x00010000
style = user32.GetWindowLongW(hwnd, GWL_STYLE)
style |= (WS_THICKFRAME | WS_MAXIMIZEBOX)
user32.SetWindowLongW(hwnd, GWL_STYLE, style)

class TestFilter(QAbstractNativeEventFilter):
    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.hWnd == hwnd:
                if msg.message == 0x0024: # WM_GETMINMAXINFO
                    mmi = MINMAXINFO.from_address(msg.lParam)
                    mmi.ptMaxPosition.x = mi.rcWork.left - mi.rcMonitor.left
                    mmi.ptMaxPosition.y = mi.rcWork.top - mi.rcMonitor.top
                    mmi.ptMaxSize.x = mi.rcWork.right - mi.rcWork.left
                    mmi.ptMaxSize.y = mi.rcWork.bottom - mi.rcWork.top
                    return True, 0
                elif msg.message == 0x0083: # WM_NCCALCSIZE
                    if msg.wParam:
                        if user32.IsZoomed(hwnd):
                            params = NCCALCSIZE_PARAMS.from_address(msg.lParam)
                            print(f"WM_NCCALCSIZE before: [{params.rgrc[0].left}, {params.rgrc[0].top}, {params.rgrc[0].right}, {params.rgrc[0].bottom}]")
                            params.rgrc[0] = mi.rcWork
                            print(f"WM_NCCALCSIZE after: [{params.rgrc[0].left}, {params.rgrc[0].top}, {params.rgrc[0].right}, {params.rgrc[0].bottom}]")
                            return True, 0
                        return True, 0
        return False, 0

tf = TestFilter()
app.installNativeEventFilter(tf)

user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
app.processEvents()

wr = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(wr))
cr = RECT()
user32.GetClientRect(hwnd, ctypes.byref(cr))
print(f"Maximized WindowRect: [{wr.left}, {wr.top}, {wr.right}, {wr.bottom}]")
print(f"Maximized ClientRect: [{cr.left}, {cr.top}, {cr.right}, {cr.bottom}]")
print(f"Qt view geometry: {view.geometry().toTuple()}, width={view.width()}, height={view.height()}")
view.close()

