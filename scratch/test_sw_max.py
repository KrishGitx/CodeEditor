import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickWindow
from PySide6.QtCore import Qt

user32 = ctypes.windll.user32
app = QApplication([])
win = QQuickWindow()
win.setFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
win.setWidth(800)
win.setHeight(600)
win.show()
hwnd = int(win.winId())

SW_MAXIMIZE = 3
SW_RESTORE = 9

user32.ShowWindow(hwnd, SW_MAXIMIZE)
app.processEvents()
print("ShowWindow SW_MAXIMIZE, IsZoomed:", user32.IsZoomed(hwnd), "win.visibility:", win.visibility())

user32.ShowWindow(hwnd, SW_RESTORE)
app.processEvents()
print("ShowWindow SW_RESTORE, IsZoomed:", user32.IsZoomed(hwnd), "win.visibility:", win.visibility())
win.close()

