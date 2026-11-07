import sys
import ctypes
from ctypes import wintypes
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

def test_drag_signals():
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.load("qml/main.qml")
    root_window = engine.rootObjects()[0]

    signals_fired = []
    root_window.visibilityChanged.connect(lambda v: signals_fired.append(f"visibilityChanged: {v}"))
    root_window.windowStateChanged.connect(lambda s: signals_fired.append(f"windowStateChanged: {s}"))
    root_window.widthChanged.connect(lambda: signals_fired.append(f"widthChanged: {root_window.width()}"))
    root_window.heightChanged.connect(lambda: signals_fired.append(f"heightChanged: {root_window.height()}"))

    hwnd = int(root_window.winId())
    print("Initial visibility:", root_window.visibility(), "windowState:", root_window.windowState())

    # Step 1: Maximize
    root_window.showMaximized()
    print("After showMaximized: visibility:", root_window.visibility(), "windowState:", root_window.windowState())

    # Step 2: Simulate Windows restoring the window (e.g. SC_RESTORE or SetWindowPlacement or resizing)
    SW_RESTORE = 9
    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)

    def check():
        print("After SW_RESTORE:")
        print("visibility:", root_window.visibility())
        print("windowState:", root_window.windowState())
        print("signals fired:", signals_fired)
        app.quit()

    QTimer.singleShot(400, check)
    app.exec()

if __name__ == "__main__":
    test_drag_signals()

