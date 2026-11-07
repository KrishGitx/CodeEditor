import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl, QAbstractNativeEventFilter, Qt
from PySide6.QtGui import QPainter, QColor

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

# Let's check how Chromium, Electron, and Qt properly do frameless window maximize on Windows!
# In Chromium / Electron (and proper Windows frameless implementations):
# 1. WS_THICKFRAME is kept so that Windows provides resize handles and maximize animation / Aero snap.
# 2. In WM_NCCALCSIZE:
#    When maximized (IsZoomed):
#    Windows passes rgrc[0] as the window rect (which Windows inflated by 8px in each direction: rcWork inflated by border).
#    If WM_GETMINMAXINFO is NOT modifying ptMaxPosition, Windows naturally places the window rect at [rcWork.left - border, rcWork.top - border, rcWork.right + border, rcWork.bottom + border].
#    Then in WM_NCCALCSIZE:
#    If you simply adjust rgrc[0] to equal mi.rcWork (or let DefWindowProc do it, or set rgrc[0] = mi.rcWork),
#    the client area is EXACTLY the work area!
# BUT what happens if WM_GETMINMAXINFO forces ptMaxPosition = (0, 0)?
# Let's inspect!

