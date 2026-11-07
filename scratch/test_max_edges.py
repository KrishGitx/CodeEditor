import sys
import ctypes
from ctypes import wintypes
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

def test_max_edges():
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.load("qml/main.qml")
    root_window = engine.rootObjects()[0]
    
    # Run the exact code from main.py
    import main
    hwnd = int(root_window.winId())

    screen = root_window.screen()
    print("Screen geometry:", screen.geometry().getRect())
    print("Screen availableGeometry:", screen.availableGeometry().getRect())

    root_window.showMaximized()

    def check():
        w_rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(w_rect))
        c_rect = wintypes.RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(c_rect))
        pt = wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))
        
        print(f"Qt geometry: {root_window.geometry().getRect()}")
        print(f"Win32 WindowRect: ({w_rect.left}, {w_rect.top}, {w_rect.right}, {w_rect.bottom}) w={w_rect.right - w_rect.left}, h={w_rect.bottom - w_rect.top}")
        print(f"ClientToScreen(0,0): ({pt.x}, {pt.y})")
        print(f"Win32 ClientRect: ({c_rect.left}, {c_rect.top}, {c_rect.right}, {c_rect.bottom}) w={c_rect.right - c_rect.left}, h={c_rect.bottom - c_rect.top}")
        app.quit()

    QTimer.singleShot(500, check)
    app.exec()

if __name__ == "__main__":
    test_max_edges()

