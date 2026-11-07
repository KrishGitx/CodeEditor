from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QAbstractNativeEventFilter, Qt
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
root_window = engine.rootObjects()[0]
root_window.setFlags(
    Qt.Window
    | Qt.FramelessWindowHint
    | Qt.WindowMinimizeButtonHint
    | Qt.WindowMaximizeButtonHint
    | Qt.WindowSystemMenuHint
)

hwnd = int(root_window.winId())
GWL_STYLE = -16
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000

style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
style |= (WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int)
    ]
margins = MARGINS(1, 1, 1, 1)
ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

WM_NCCALCSIZE = 0x0083
WM_GETMINMAXINFO = 0x0024
MONITOR_DEFAULTTONEAREST = 2

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

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
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

class FramelessWindowNativeEventFilter(QAbstractNativeEventFilter):
    def __init__(self, hwnd):
        super().__init__()
        self.hwnd = hwnd

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.hWnd == self.hwnd:
                if msg.message == WM_GETMINMAXINFO:
                    hMonitor = ctypes.windll.user32.MonitorFromWindow(
                        self.hwnd, MONITOR_DEFAULTTONEAREST
                    )
                    mi = MONITORINFO()
                    mi.cbSize = ctypes.sizeof(MONITORINFO)
                    if ctypes.windll.user32.GetMonitorInfoW(
                        hMonitor, ctypes.byref(mi)
                    ):
                        mmi = MINMAXINFO.from_address(msg.lParam)
                        mmi.ptMaxPosition.x = mi.rcWork.left - mi.rcMonitor.left
                        mmi.ptMaxPosition.y = mi.rcWork.top - mi.rcMonitor.top
                        mmi.ptMaxSize.x = mi.rcWork.right - mi.rcWork.left
                        mmi.ptMaxSize.y = mi.rcWork.bottom - mi.rcWork.top
                        return True, 0
                elif msg.message == WM_NCCALCSIZE:
                    if msg.wParam:
                        if ctypes.windll.user32.IsZoomed(self.hwnd):
                            hMonitor = ctypes.windll.user32.MonitorFromWindow(
                                self.hwnd, MONITOR_DEFAULTTONEAREST
                            )
                            mi = MONITORINFO()
                            mi.cbSize = ctypes.sizeof(MONITORINFO)
                            if ctypes.windll.user32.GetMonitorInfoW(
                                hMonitor, ctypes.byref(mi)
                            ):
                                params = NCCALCSIZE_PARAMS.from_address(msg.lParam)
                                params.rgrc[0] = mi.rcWork
                                return True, 0
                        return True, 0
        return False, 0

win_filter = FramelessWindowNativeEventFilter(hwnd)
app.installNativeEventFilter(win_filter)

SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
ctypes.windll.user32.SetWindowPos(
    hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
)

print("Calling root_window.showMaximized()...")
root_window.showMaximized()
for _ in range(10):
    app.processEvents()
    time.sleep(0.05)

wr = RECT()
ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(wr))

user32 = ctypes.windll.user32
hMon = user32.MonitorFromWindow(hwnd, 2)
mi = MONITORINFO()
mi.cbSize = ctypes.sizeof(MONITORINFO)
user32.GetMonitorInfoW(hMon, ctypes.byref(mi))

print(f"WorkArea: [{mi.rcWork.left}, {mi.rcWork.top}, {mi.rcWork.right}, {mi.rcWork.bottom}]")
print(f"WindowRect: [{wr.left}, {wr.top}, {wr.right}, {wr.bottom}]")
print(f"Difference: left={wr.left - mi.rcWork.left}, top={wr.top - mi.rcWork.top}, right={wr.right - mi.rcWork.right}, bottom={wr.bottom - mi.rcWork.bottom}")

