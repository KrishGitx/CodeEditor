import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QUrl, Qt

app = QApplication([])
view = QQuickView()
view.setFlag(Qt.FramelessWindowHint, True)
view.setWidth(800)
view.setHeight(600)
view.show()
hwnd = int(view.winId())

print("Initial:")
print("  visibility:", view.visibility())
print("  windowStates:", view.windowStates())
print("  width/height:", view.width(), view.height())

view.showMaximized()
app.processEvents()

print("After showMaximized:")
print("  visibility:", view.visibility())
print("  windowStates:", view.windowStates())
print("  IsZoomed:", ctypes.windll.user32.IsZoomed(hwnd))
print("  width/height:", view.width(), view.height())

view.showNormal()
app.processEvents()

print("After showNormal:")
print("  visibility:", view.visibility())
print("  windowStates:", view.windowStates())
print("  IsZoomed:", ctypes.windll.user32.IsZoomed(hwnd))
print("  width/height:", view.width(), view.height())

view.close()

