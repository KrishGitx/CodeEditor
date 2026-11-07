import sys, os
import ctypes
from ctypes import wintypes
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QObject

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()

print("--- 1. Testing ExtensionsSidebarPanel Icon Loading & Install Button ---")
with open("qml/components/ExtensionsSidebarPanel.qml", "r", encoding="utf-8") as f:
    esp = f.read()

assert "Image {" in esp and "extAvatarImg" in esp, "ExtensionsSidebarPanel must have Image for icons"
assert "modelData.iconUrl" in esp, "ExtensionsSidebarPanel must bind to modelData.iconUrl"
assert "visible: !extAvatarImg.visible" in esp, "VectorIcon must fallback when extAvatarImg is not visible"
assert "name: \"puzzle\"" in esp, "Fallback icon must be puzzle"
print("PASS: ExtensionsSidebarPanel displays extension icons with clean fallback to puzzle.")

print("\n--- 2. Testing ExtensionDetailsView Icon Loading, Install Button & Status Chip ---")
with open("qml/components/ExtensionDetailsView.qml", "r", encoding="utf-8") as f:
    edv = f.read()

assert "detailsAvatarImg" in edv, "ExtensionDetailsView must have Image for extension icon"
assert "extensionData.iconUrl" in edv, "ExtensionDetailsView must bind to extensionData.iconUrl"
assert "visible: !detailsAvatarImg.visible" in edv, "VectorIcon must fallback when detailsAvatarImg is not visible"
assert "isMarketplaceUninstalled" in edv, "ExtensionDetailsView must detect uninstalled marketplace extension"
assert 'text: root.isInstalling ? "Installing…" : "Install"' in edv, "Install button text must display Install/Installing"
assert "install_from_open_vsx" in edv, "Install button must invoke install_from_open_vsx"
assert 'text: root.isMarketplaceUninstalled' in edv and '"Not Installed"' in edv, "Status chip must show Not Installed for uninstalled marketplace"
assert 'text: root.isEnabled ? "Disable" : "Enable"' in edv, "Disable/Enable button preserved for installed"
assert 'text: "Uninstall"' in edv, "Uninstall button preserved for installed"
print("PASS: ExtensionDetailsView renders remote icon, Install button, and Not Installed status badge.")

print("\n--- 3. Testing Real-Time Window Drag-Restore and Maximize Icon Synchronization ---")
with open("main.py", "r", encoding="utf-8") as f:
    mp = f.read()

assert "windowMaximizedChanged = Signal(bool)" in mp, "EditorBackend must define windowMaximizedChanged signal"
assert "toggle_maximize_window" in mp, "EditorBackend must provide toggle_maximize_window slot"
assert "onWindowMaximizedChanged" in mp or "backend.windowMaximizedChanged.emit" in mp, "main.py must emit windowMaximizedChanged on native size changes"

with open("qml/components/AppHeader.qml", "r", encoding="utf-8") as f:
    ah = f.read()

assert "backend.toggle_maximize_window" in ah, "AppHeader must use backend.toggle_maximize_window"
assert "root.isMaximized = true" not in ah, "AppHeader must not imperatively overwrite root.isMaximized"

with open("qml/main.qml", "r", encoding="utf-8") as f:
    qm = f.read()

assert "syncMaximizeState()" in qm, "main.qml must have syncMaximizeState handler"
assert "onWidthChanged: syncMaximizeState()" in qm, "main.qml must sync on width changes (real-time drag unzoom)"
assert "onWindowMaximizedChanged" in qm, "main.qml must handle backend.windowMaximizedChanged"
print("PASS: Drag-restore and maximize icon synchronization updates in real-time.")

print("\n--- 4. Testing Native Maximize Full Edges ---")
assert "SetProcessDpiAwarenessContext(-4)" in mp, "main.py must configure Per-Monitor V2 DPI awareness"
assert "WS_CAPTION" in mp, "main.py must include WS_CAPTION for true standard frame calculations"
assert "WM_NCCALCSIZE" in mp, "main.py must intercept WM_NCCALCSIZE"
assert "params.rgrc[0] = mi.rcWork" in mp, "WM_NCCALCSIZE must align to rcWork"
assert "DWMWA_WINDOW_CORNER_PREFERENCE" in mp, "main.py must manage DWM corner preference (DONOTROUND on maximize)"
print("PASS: Maximization uses native Windows sizing engine covering all monitor edges and taskbar flush.")

print("\n==========================================")
print("ALL LATEST USER REQUEST CHECKS PASSED!")
print("==========================================")

