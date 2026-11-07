import sys
import ctypes
from ctypes import wintypes
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

def test_unzoom_check():
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.load("qml/main.qml")
    root_window = engine.rootObjects()[0]
    hwnd = int(root_window.winId())

    root_window.showMaximized()
    print("IsZoomed after showMaximized:", bool(ctypes.windll.user32.IsZoomed(hwnd)))
    print("root_window.visibility:", root_window.visibility())

    # Simulate what Windows does when dragging: it sends WM_SYSCOMMAND SC_RESTORE or resizes window to normal size
    # and IsZoomed becomes False
    rect = wintypes.RECT(100, 100, 1000, 700)
    # SetWindowPos with SWP_NOZORDER
    ctypes.windll.user32.SetWindowPos(hwnd, 0, 100, 100, 900, 600, 0x0004 | 0x0020)
    print("IsZoomed after move/resize:", bool(ctypes.windll.user32.IsZoomed(hwnd)))

    def check():
        print("After event loop:")
        print("IsZoomed:", bool(ctypes.windll.user32.IsZoomed(hwnd)))
        print("root_window.visibility:", root_window.visibility())
        print("root_window.windowState:", root_window.windowState())
        app.quit()

    QTimer.singleShot(200, check)
    app.exec()

if __name__ == "__main__":
    test_unzoom_check()

