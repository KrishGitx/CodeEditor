import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickWindow
from PySide6.QtCore import Qt, QAbstractNativeEventFilter, QObject, Signal, Slot
import time

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

try:
    user32.SetProcessDpiAwarenessContext(-4)
except Exception:
    pass

app = QApplication([])
win = QQuickWindow()
win.setFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowSystemMenuHint)
win.setWidth(1000)
win.setHeight(700)
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
dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MINMAXINFO(ctypes.Structure):
    _fields_ = [("ptReserved", POINT), ("ptMaxSize", POINT), ("ptMaxPosition", POINT), ("ptMinTrackSize", POINT), ("ptMaxTrackSize", POINT)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

class NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [("rgrc", RECT * 3), ("lppos", ctypes.c_void_p)]

class SignalTester(QObject):
    maxChanged = Signal(bool)

tester = SignalTester()
recorded_signals = []
tester.maxChanged.connect(lambda s: recorded_signals.append(s))

class WinFilter(QAbstractNativeEventFilter):
    def __init__(self, hwnd):
        super().__init__()
        self.hwnd = hwnd
        self._last_max = None

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.hWnd == self.hwnd:
                if msg.message in (0x0005, 0x0047): # WM_SIZE, WM_WINDOWPOSCHANGED
                    is_max = bool(user32.IsZoomed(self.hwnd))
                    if is_max != self._last_max:
                        self._last_max = is_max
                        tester.maxChanged.emit(is_max)
                        # Corner rounding adjustment
                        DWMWA_WINDOW_CORNER_PREFERENCE = 33
                        pref = ctypes.c_int(1 if is_max else 2) # 1=DONOTROUND, 2=ROUND
                        dwmapi.DwmSetWindowAttribute(self.hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(pref), ctypes.sizeof(pref))
                elif msg.message == 0x0024: # WM_GETMINMAXINFO
                    hMon = user32.MonitorFromWindow(self.hwnd, 2)
                    mi = MONITORINFO()
                    mi.cbSize = ctypes.sizeof(MONITORINFO)
                    if user32.GetMonitorInfoW(hMon, ctypes.byref(mi)):
                        mmi = MINMAXINFO.from_address(msg.lParam)
                        work_w = mi.rcWork.right - mi.rcWork.left
                        work_h = mi.rcWork.bottom - mi.rcWork.top
                        mmi.ptMaxSize.x = work_w
                        mmi.ptMaxSize.y = work_h
                        mmi.ptMaxTrackSize.x = max(mmi.ptMaxTrackSize.x, work_w + 100)
                        mmi.ptMaxTrackSize.y = max(mmi.ptMaxTrackSize.y, work_h + 100)
                        return True, 0
                elif msg.message == 0x0083 and msg.wParam: # WM_NCCALCSIZE
                    if user32.IsZoomed(self.hwnd):
                        hMon = user32.MonitorFromWindow(self.hwnd, 2)
                        mi = MONITORINFO()
                        mi.cbSize = ctypes.sizeof(MONITORINFO)
                        if user32.GetMonitorInfoW(hMon, ctypes.byref(mi)):
                            params = NCCALCSIZE_PARAMS.from_address(msg.lParam)
                            params.rgrc[0] = mi.rcWork
                            return True, 0
                    return True, 0
        return False, 0

wf = WinFilter(hwnd)
app.installNativeEventFilter(wf)
user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0020)

print("--- 1. Testing native ShowWindow SW_MAXIMIZE ---")
user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
for _ in range(10):
    app.processEvents()
    time.sleep(0.05)

cr = RECT()
user32.GetClientRect(hwnd, ctypes.byref(cr))
hMon = user32.MonitorFromWindow(hwnd, 2)
mi = MONITORINFO()
mi.cbSize = ctypes.sizeof(MONITORINFO)
user32.GetMonitorInfoW(hMon, ctypes.byref(mi))

work_w = mi.rcWork.right - mi.rcWork.left
work_h = mi.rcWork.bottom - mi.rcWork.top
print(f"WorkArea: w={work_w}, h={work_h}")
print(f"ClientRect: w={cr.right}, h={cr.bottom}")
print(f"Qt size: w={win.width()}, h={win.height()}")
assert cr.right == work_w, f"Client width {cr.right} != work width {work_w}"
assert cr.bottom == work_h, f"Client height {cr.bottom} != work height {work_h}"
assert True in recorded_signals, "Signal maxChanged(True) must have fired"

print("--- 2. Testing native ShowWindow SW_RESTORE (as happens when dragging) ---")
user32.ShowWindow(hwnd, 9) # SW_RESTORE
for _ in range(10):
    app.processEvents()
    time.sleep(0.05)

print(f"After restore: IsZoomed={user32.IsZoomed(hwnd)}, Qt width={win.width()}")
assert recorded_signals[-1] == False, f"Signal maxChanged(False) must have fired on restore, got: {recorded_signals}"

win.close()
print("PASS: Maximization covers full screen edges and drag-restore emits update signal in real time!")

