import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl, QAbstractNativeEventFilter, Qt

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

SM_CXFRAME = 32
SM_CYFRAME = 33
SM_CXPADDEDBORDER = 92

cx_frame = user32.GetSystemMetrics(SM_CXFRAME)
cy_frame = user32.GetSystemMetrics(SM_CYFRAME)
cx_padded = user32.GetSystemMetrics(SM_CXPADDEDBORDER)

print(f"Metrics: cx_frame={cx_frame}, cy_frame={cy_frame}, cx_padded={cx_padded}")
border_x = cx_frame + cx_padded
border_y = cy_frame + cx_padded
print(f"Total resize border: border_x={border_x}, border_y={border_y}")

