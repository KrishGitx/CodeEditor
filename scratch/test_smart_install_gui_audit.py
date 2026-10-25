import os
import sys
import unittest
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QCoreApplication, QUrl, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem

from ExtensionManager import ExtensionManager


class TestSmartInstallGUIAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        cls.engine = QQmlApplicationEngine()
        cls.engine.addImportPath("qml")
        cls.em = ExtensionManager()
        cls.engine.rootContext().setContextProperty("extensionManager", cls.em)

        cls.engine.load(QUrl.fromLocalFile("qml/main.qml"))
        root_objects = cls.engine.rootObjects()
        assert len(root_objects) > 0, "Failed to load qml/main.qml"
        cls.root = root_objects[0]
        cls.dialog = cls.root.findChild(QObject, "smartInstallDialog")
        assert cls.dialog is not None, "Failed to find smartInstallDialog"

    def setUp(self):
        self.dialog.setProperty("isOpen", True)
        self.dialog.setProperty("dialogState", "installing")
        self.dialog.setProperty("toolName", "test-tool")
        self.dialog.setProperty("installLogs", "Starting test tool installation...\n")
        self.app.processEvents()

    def tearDown(self):
        self.dialog.setProperty("isOpen", False)
        self.dialog.setProperty("installLogs", "")
        self.app.processEvents()

    # 32. Short logs fit within dialog
    def test_32_short_logs_fit_within_dialog(self):
        modal_card = self.dialog.findChild(QQuickItem, "modalCard")
        self.assertIsNotNone(modal_card)
        initial_h = modal_card.property("height")
        initial_w = modal_card.property("width")

        self.assertLessEqual(initial_h, 520)
        self.assertLessEqual(initial_w, 640)
        self.assertGreaterEqual(initial_h, 380)

    # 33. Thousands of log lines do not break layout and are scrollable
    def test_33_thousands_of_lines_scrollable_without_overflow(self):
        modal_card = self.dialog.findChild(QQuickItem, "modalCard")
        h_before = modal_card.property("height")
        w_before = modal_card.property("width")

        # Append 1,000 log lines
        bulk_logs = "\n".join([f"Step {i}: executing installation check and compiling dependency..." for i in range(1000)])
        self.dialog.setProperty("installLogs", bulk_logs)
        self.app.processEvents()

        # Dialog dimensions must remain strictly constrained
        h_after = modal_card.property("height")
        w_after = modal_card.property("width")
        self.assertEqual(h_before, h_after, "Dialog height must not grow indefinitely from long logs")
        self.assertEqual(w_before, w_after, "Dialog width must not grow indefinitely from long logs")

        log_container = self.dialog.findChild(QQuickItem, "logOutputContainer")
        self.assertIsNotNone(log_container)

        log_flickable = self.dialog.findChild(QQuickItem, "logFlickable")
        self.assertIsNotNone(log_flickable)
        content_h = log_flickable.property("contentHeight")
        flick_h = log_flickable.property("height")
        self.assertGreater(content_h, flick_h, "Long output must be vertically scrollable")

    # 34. Long commands / paths do not cause uncontrolled width expansion
    def test_34_long_commands_wrap_without_width_expansion(self):
        modal_card = self.dialog.findChild(QQuickItem, "modalCard")
        w_before = modal_card.property("width")

        long_line = "C:\\Users\\amazi\\AppData\\Local\\VeryLongProjectDirectoryPath\\" * 10
        self.dialog.setProperty("installLogs", long_line)
        self.app.processEvents()

        w_after = modal_card.property("width")
        self.assertEqual(w_before, w_after, "Long line must not expand modal card width")

    # 35. Footer buttons remain accessible
    def test_35_footer_buttons_remain_accessible(self):
        self.dialog.setProperty("dialogState", "failed")
        self.app.processEvents()

        confirm_btn = self.dialog.findChild(QQuickItem, "confirmMa")
        self.assertIsNotNone(confirm_btn)
        cancel_btn = self.dialog.findChild(QQuickItem, "cancelMa")
        self.assertIsNotNone(cancel_btn)


if __name__ == "__main__":
    unittest.main()
