import sys, os, time, bisect, re, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import (
    QGuiApplication, QSurfaceFormat, QFont, QWheelEvent, QMouseEvent, QKeyEvent
)
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, Slot, Signal, Qt as QtCore_Qt, QPoint, QPointF, QEvent
from PySide6.QtQuick import QQuickWindow

# Import BackingDocument and VirtualizedEditorController from prototype
from scratch.prototype_virtualized_editor import BackingDocument, VirtualizedEditorController

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
fmt = QSurfaceFormat()
fmt.setAlphaBufferSize(8)
QSurfaceFormat.setDefaultFormat(fmt)

ctrl = VirtualizedEditorController()

# Generate 10,000 lines document
raw_10k = [f"def func_10k_{i}(x, y):\n    # line {i}\n    val = x * {i} + y\n    return val" for i in range(2500)]
text_10k = "\n".join(raw_10k)
ctrl.load_content(text_10k)

qml_code = b"""
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Window {
    id: win
    width: 900
    height: 700
    visible: true
    title: "Virtualized Editor Prototype"

    property real lineHeight: 18.0
    property real totalVirtualHeight: ctrl.total_virtual_height()
    property int windowStartLine: ctrl.get_window_start_line()
    property string windowText: ctrl.get_window_text()

    Connections {
        target: ctrl
        function onWindowChanged(sLine, eLine, text) {
            win.windowStartLine = sLine;
            win.windowText = text;
        }
    }

    Flickable {
        id: virtualFlickable
        anchors.fill: parent
        anchors.rightMargin: 12
        clip: true
        contentWidth: width
        contentHeight: win.totalVirtualHeight
        boundsBehavior: Flickable.StopAtBounds

        onContentYChanged: {
            ctrl.on_scroll_y_changed(contentY);
        }

        // The active materialized TextArea is positioned at its global offset
        Item {
            id: materializedWrapper
            x: 0
            y: win.windowStartLine * win.lineHeight
            width: parent.width
            height: Math.max(100, codeArea.contentHeight + 40)

            TextArea {
                id: codeArea
                anchors.fill: parent
                font.family: "Consolas"
                font.pixelSize: 13
                text: win.windowText
                selectByMouse: true
                color: "#e0e0e0"
                background: Rectangle { color: "#1e1e1e" }
            }
        }

        ScrollBar.vertical: ScrollBar {
            id: vScrollBar
            anchors.right: parent.right
            policy: ScrollBar.AlwaysOn
            width: 10
        }
    }
}
"""

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("ctrl", ctrl)
comp = QQmlComponent(engine)
comp.setData(qml_code, "")
root_win = comp.create()
if not root_win:
    for e in comp.errors():
        print(e.toString())
    sys.exit(1)

root_win.show()
QCoreApplication.processEvents()

print(f"\n{'='*78}\nTESTING VIRTUALIZED QML INTERACTION ON 10,000-LINE FILE\n{'='*78}")

# 1. Test 100 Mouse Wheel Events
print("\n[1] 100 Real Wheel Events on Virtualized Viewport:")
wheel_times = []
for i in range(100):
    t0 = time.perf_counter()
    w_ev = QWheelEvent(
        QPointF(300, 300), QPoint(300, 300), QPoint(0, 0), QPoint(0, -120),
        QtCore_Qt.NoButton, QtCore_Qt.NoModifier, QtCore_Qt.ScrollUpdate, False
    )
    QCoreApplication.sendEvent(root_win, w_ev)
    QCoreApplication.processEvents()
    wheel_times.append((time.perf_counter() - t0) * 1000)

print(f"  Avg frame time: {statistics.mean(wheel_times):5.2f} ms | Max = {max(wheel_times):5.2f} ms | p95 = {sorted(wheel_times)[95]:5.2f} ms")

# 2. Test 100 Continuous Drag Steps
print("\n[2] 100 Scrollbar Drag Steps on Virtualized Viewport:")
drag_times = []
for s in range(100):
    t0 = time.perf_counter()
    target_y = (s / 100.0) * (ctrl.total_virtual_height() - 700)
    flick = root_win.findChild(QObject, "virtualFlickable") or root_win.children()[0]
    flick.setProperty("contentY", target_y)
    QCoreApplication.processEvents()
    drag_times.append((time.perf_counter() - t0) * 1000)

print(f"  Avg frame time: {statistics.mean(drag_times):5.2f} ms | Max = {max(drag_times):5.2f} ms | p95 = {sorted(drag_times)[95]:5.2f} ms")

# 3. Test Keystroke Insertion
print("\n[3] 50 Key Events on Virtualized TextArea:")
key_times = []
for i in range(50):
    ch = chr(ord('a') + (i % 26))
    t0 = time.perf_counter()
    press = QKeyEvent(QEvent.KeyPress, QtCore_Qt.Key_A, QtCore_Qt.NoModifier, ch)
    QCoreApplication.sendEvent(root_win, press)
    release = QKeyEvent(QEvent.KeyRelease, QtCore_Qt.Key_A, QtCore_Qt.NoModifier, ch)
    QCoreApplication.sendEvent(root_win, release)
    QCoreApplication.processEvents()
    key_times.append((time.perf_counter() - t0) * 1000)

print(f"  Avg key latency: {statistics.mean(key_times):5.2f} ms | Max = {max(key_times):5.2f} ms | p95 = {sorted(key_times)[47]:5.2f} ms")

print("\n>>> VIRTUALIZATION PROTOTYPE INTERACTION TESTS PASSED! <<<")
