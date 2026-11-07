import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine, QQmlComponent
from ExtensionManager import ExtensionManager
from SettingsBackend import SettingsBackend

def test_qml():
    app = QGuiApplication(sys.argv)
    engine = QQmlEngine()
    em = ExtensionManager()
    sb = SettingsBackend()
    engine.rootContext().setContextProperty("extensionManager", em)
    engine.rootContext().setContextProperty("settingsBackend", sb)

    # 1. Test ExtensionDetailsView.qml
    comp = QQmlComponent(engine, "qml/components/ExtensionDetailsView.qml")
    obj = comp.create()
    if not obj:
        print("ExtensionDetailsView errors:", comp.errors())
    assert obj is not None, "Failed to load ExtensionDetailsView.qml"
    print("PASS: ExtensionDetailsView.qml loaded successfully")

    # Set mock extension data (uninstalled marketplace item)
    obj.setProperty("extensionData", {
        "id": "enBonnet.orange-ocean",
        "name": "Orange Ocean Theme",
        "is_marketplace": True,
        "installed": False
    })
    # Because enBonnet.orange-ocean is installed in em:
    assert obj.property("isInstalled") == True, "Should detect installed extension!"
    assert obj.property("isMarketplaceUninstalled") == False, "isMarketplaceUninstalled should be false when installed!"
    print("PASS: ExtensionDetailsView reactive properties evaluated correctly!")

    # 2. Test ExtensionsSidebarPanel.qml
    comp2 = QQmlComponent(engine, "qml/components/ExtensionsSidebarPanel.qml")
    obj2 = comp2.create()
    if not obj2:
        print("ExtensionsSidebarPanel errors:", comp2.errors())
    assert obj2 is not None, "Failed to load ExtensionsSidebarPanel.qml"
    print("PASS: ExtensionsSidebarPanel.qml loaded successfully")

    print("ALL QML TESTS PASSED!")

if __name__ == "__main__":
    test_qml()
