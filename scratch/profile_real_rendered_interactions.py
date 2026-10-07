import sys, os, time, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import (
    QGuiApplication, QSurfaceFormat, QWheelEvent, QMouseEvent, QKeyEvent
)
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, QEvent, Qt as QtCore_Qt, QPointF, QPoint
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQuick import QQuickWindow, QQuickItem
from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
app.setApplicationName("DGX Studio")
app.setOrganizationName("DGX")

fmt = QSurfaceFormat()
fmt.setAlphaBufferSize(8)
QSurfaceFormat.setDefaultFormat(fmt)
QQuickStyle.setStyle("Basic")

backend = EditorBackend()
musicPlayer = MusicPlayer()
aiBackend = AIBackend()
terminalBackend = TerminalBackend()
settingsBackend = SettingsBackend()
backend.settings_backend = settingsBackend

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
engine.rootContext().setContextProperty("extensionManager", backend.extension_manager)
engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
engine.rootContext().setContextProperty("aiBackend", aiBackend)
engine.rootContext().setContextProperty("terminalBackend", terminalBackend)
engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root_app = comp.create()
if not root_app:
    for err in comp.errors():
        print("QML Error:", err.toString())
    sys.exit(1)

root_window = root_app if isinstance(root_app, QQuickWindow) else root_app.findChild(QQuickWindow)
if not root_window:
    root_window = engine.rootObjects()[0]

root_window.show()
QCoreApplication.processEvents()

editor = root_app.findChild(QObject, "editorArea")

py_small = "def foo():\n    # hello\n    return 42\n"

# 3,000 lines
py_3000 = "\n".join([
    f"def py_func_{i}(x, y):\n"
    f"    '''Multiline docstring for function {i}\n"
    f"    Calculates weighted sum and transformations.'''\n"
    f"    if x > 0:\n"
    f"        val = x * {i} + len(str(y))\n"
    f"        return val\n"
    f"    else:\n"
    f"        return -1"
    for i in range(430)
])

# 10,000 lines
py_10000 = "\n".join([
    f"def py_func_10k_{i}(a, b):\n"
    f"    '''10k function {i}'''\n"
    f"    res = a + b * {i}\n"
    f"    return res"
    for i in range(2500)
])

def run_real_interaction_suite(label, filename, content):
    print(f"\n{'='*78}\nEND-TO-END RENDERED INTERACTION PROFILE: {label} ({filename})\n{'='*78}")
    editor.loadFile(filename, content)
    QCoreApplication.processEvents()

    ta = backend.qml_text_area
    doc = backend.text_document
    flick = editor.findChild(QObject, "editorFlickable")

    # -----------------------------------------------------------------
    # 1. REAL MOUSE-WHEEL SCROLLING (Real QWheelEvent sent to Window)
    # -----------------------------------------------------------------
    print("\n[1] Real Mouse-Wheel Scrolling (100 sequential QWheelEvent dispatches):")
    wheel_frame_times = []
    global_pt = QPoint(300, 300)
    local_pt = QPointF(300, 300)

    for i in range(100):
        t0 = time.perf_counter()
        
        # Construct real QWheelEvent
        delta = QPoint(0, -120)  # Standard scroll tick down
        wheel_ev = QWheelEvent(
            local_pt, global_pt, QPoint(0, 0), delta,
            QtCore_Qt.NoButton, QtCore_Qt.NoModifier, QtCore_Qt.ScrollUpdate, False
        )
        QCoreApplication.sendEvent(root_window, wheel_ev)
        
        # Flush all Qt events and trigger scene graph render / frame swap
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        
        wheel_frame_times.append((t1 - t0) * 1000)

    avg_w = statistics.mean(wheel_frame_times)
    max_w = max(wheel_frame_times)
    p95_w = sorted(wheel_frame_times)[int(len(wheel_frame_times)*0.95)]
    p99_w = sorted(wheel_frame_times)[int(len(wheel_frame_times)*0.99)]
    sp16_w = len([t for t in wheel_frame_times if t > 16.67])
    sp33_w = len([t for t in wheel_frame_times if t > 33.33])

    print(f"  Avg frame time:    {avg_w:6.2f} ms")
    print(f"  Max frame time:    {max_w:6.2f} ms")
    print(f"  p95 frame time:    {p95_w:6.2f} ms")
    print(f"  p99 frame time:    {p99_w:6.2f} ms")
    print(f"  Frames > 16.67 ms: {sp16_w:3d} / {len(wheel_frame_times)} ({sp16_w/len(wheel_frame_times)*100:.1f}%)")
    print(f"  Frames > 33.33 ms: {sp33_w:3d} / {len(wheel_frame_times)} ({sp33_w/len(wheel_frame_times)*100:.1f}%)")

    # -----------------------------------------------------------------
    # 2. REAL SCROLLBAR THUMB DRAGGING (Real QMouseEvent press + drag)
    # -----------------------------------------------------------------
    print("\n[2] Real Scrollbar Thumb Dragging (100 continuous QMouseEvent drag steps):")
    drag_frame_times = []
    
    # Locate scrollbar / flickable right edge
    flick_w = flick.property("width") if flick else 600
    flick_h = flick.property("height") if flick else 600
    scrollbar_x = flick_w - 5
    
    # 1. Mouse Press on scrollbar
    press_ev = QMouseEvent(
        QEvent.MouseButtonPress, QPointF(scrollbar_x, 20), QPointF(scrollbar_x, 20),
        QtCore_Qt.LeftButton, QtCore_Qt.LeftButton, QtCore_Qt.NoModifier
    )
    QCoreApplication.sendEvent(root_window, press_ev)
    QCoreApplication.processEvents()

    # 2. 100 continuous Move events
    for step in range(100):
        t0 = time.perf_counter()
        target_y = 20 + (step / 100.0) * (flick_h - 40)
        move_ev = QMouseEvent(
            QEvent.MouseMove, QPointF(scrollbar_x, target_y), QPointF(scrollbar_x, target_y),
            QtCore_Qt.LeftButton, QtCore_Qt.LeftButton, QtCore_Qt.NoModifier
        )
        QCoreApplication.sendEvent(root_window, move_ev)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        drag_frame_times.append((t1 - t0) * 1000)

    # 3. Mouse Release
    rel_ev = QMouseEvent(
        QEvent.MouseButtonRelease, QPointF(scrollbar_x, flick_h - 20), QPointF(scrollbar_x, flick_h - 20),
        QtCore_Qt.LeftButton, QtCore_Qt.NoButton, QtCore_Qt.NoModifier
    )
    QCoreApplication.sendEvent(root_window, rel_ev)
    QCoreApplication.processEvents()

    avg_d = statistics.mean(drag_frame_times)
    max_d = max(drag_frame_times)
    p95_d = sorted(drag_frame_times)[int(len(drag_frame_times)*0.95)]
    p99_d = sorted(drag_frame_times)[int(len(drag_frame_times)*0.99)]
    sp16_d = len([t for t in drag_frame_times if t > 16.67])
    sp33_d = len([t for t in drag_frame_times if t > 33.33])

    print(f"  Avg frame time:    {avg_d:6.2f} ms")
    print(f"  Max frame time:    {max_d:6.2f} ms")
    print(f"  p95 frame time:    {p95_d:6.2f} ms")
    print(f"  p99 frame time:    {p99_d:6.2f} ms")
    print(f"  Frames > 16.67 ms: {sp16_d:3d} / {len(drag_frame_times)} ({sp16_d/len(drag_frame_times)*100:.1f}%)")
    print(f"  Frames > 33.33 ms: {sp33_d:3d} / {len(drag_frame_times)} ({sp33_d/len(drag_frame_times)*100:.1f}%)")

    # -----------------------------------------------------------------
    # 3A. REAL KEYBOARD TYPING (Real QKeyEvent dispatched into active TextArea)
    # -----------------------------------------------------------------
    print("\n[3A] Real Keyboard Typing (50 KeyPress + KeyRelease events in middle of file):")
    mid_pos = len(content) // 2
    ta.setProperty("cursorPosition", mid_pos)
    QCoreApplication.processEvents()

    key_frame_times = []
    for i in range(50):
        ch = chr(ord('a') + (i % 26))
        t0 = time.perf_counter()
        
        # Send actual QKeyEvent Press
        press = QKeyEvent(QEvent.KeyPress, QtCore_Qt.Key_A, QtCore_Qt.NoModifier, ch)
        QCoreApplication.sendEvent(root_window, press)
        
        # Send actual QKeyEvent Release
        release = QKeyEvent(QEvent.KeyRelease, QtCore_Qt.Key_A, QtCore_Qt.NoModifier, ch)
        QCoreApplication.sendEvent(root_window, release)
        
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        key_frame_times.append((t1 - t0) * 1000)

    avg_k = statistics.mean(key_frame_times)
    max_k = max(key_frame_times)
    p95_k = sorted(key_frame_times)[int(len(key_frame_times)*0.95)]
    p99_k = sorted(key_frame_times)[int(len(key_frame_times)*0.99)]
    sp16_k = len([t for t in key_frame_times if t > 16.67])
    sp33_k = len([t for t in key_frame_times if t > 33.33])

    print(f"  Avg input-to-frame: {avg_k:6.2f} ms")
    print(f"  Max input-to-frame: {max_k:6.2f} ms")
    print(f"  p95 input-to-frame: {p95_k:6.2f} ms")
    print(f"  p99 input-to-frame: {p99_k:6.2f} ms")
    print(f"  Frames > 16.67 ms:  {sp16_k:3d} / {len(key_frame_times)} ({sp16_k/len(key_frame_times)*100:.1f}%)")
    print(f"  Frames > 33.33 ms:  {sp33_k:3d} / {len(key_frame_times)} ({sp33_k/len(key_frame_times)*100:.1f}%)")

    # -----------------------------------------------------------------
    # 3B. TYPING NEAR MULTILINE / SCOPES (30 Real Key events)
    # -----------------------------------------------------------------
    print("\n[3B] Real Typing Near Multiline Docstrings / Scopes (30 KeyPress events):")
    doc_pos = content.find("'''") if "'''" in content else 10
    ta.setProperty("cursorPosition", doc_pos + 3)
    QCoreApplication.processEvents()

    scope_key_times = []
    for i in range(30):
        t0 = time.perf_counter()
        press = QKeyEvent(QEvent.KeyPress, QtCore_Qt.Key_Space, QtCore_Qt.NoModifier, " ")
        QCoreApplication.sendEvent(root_window, press)
        release = QKeyEvent(QEvent.KeyRelease, QtCore_Qt.Key_Space, QtCore_Qt.NoModifier, " ")
        QCoreApplication.sendEvent(root_window, release)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        scope_key_times.append((t1 - t0) * 1000)

    avg_sk = statistics.mean(scope_key_times)
    max_sk = max(scope_key_times)
    p95_sk = sorted(scope_key_times)[int(len(scope_key_times)*0.95)]
    sp16_sk = len([t for t in scope_key_times if t > 16.67])

    print(f"  Avg input-to-frame: {avg_sk:6.2f} ms")
    print(f"  Max input-to-frame: {max_sk:6.2f} ms")
    print(f"  p95 input-to-frame: {p95_sk:6.2f} ms")
    print(f"  Frames > 16.67 ms:  {sp16_sk:3d} / {len(scope_key_times)} ({sp16_sk/len(scope_key_times)*100:.1f}%)")

    # -----------------------------------------------------------------
    # 4. REAL CTRL + MOUSE-WHEEL ZOOM (10 QWheelEvents with Ctrl modifier)
    # -----------------------------------------------------------------
    print("\n[4] Real Ctrl+Wheel Zoom (10 rapid Ctrl+Wheel events):")
    zoom_frame_times = []
    for i in range(10):
        delta = QPoint(0, 120 if i < 5 else -120)
        t0 = time.perf_counter()
        wheel_ev = QWheelEvent(
            local_pt, global_pt, QPoint(0, 0), delta,
            QtCore_Qt.NoButton, QtCore_Qt.ControlModifier, QtCore_Qt.ScrollUpdate, False
        )
        QCoreApplication.sendEvent(root_window, wheel_ev)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        zoom_frame_times.append((t1 - t0) * 1000)

    avg_z = statistics.mean(zoom_frame_times)
    max_z = max(zoom_frame_times)
    p95_z = sorted(zoom_frame_times)[int(len(zoom_frame_times)*0.95)]
    sp16_z = len([t for t in zoom_frame_times if t > 16.67])
    sp33_z = len([t for t in zoom_frame_times if t > 33.33])

    print(f"  Avg frame time:    {avg_z:6.2f} ms")
    print(f"  Max frame time:    {max_z:6.2f} ms")
    print(f"  p95 frame time:    {p95_z:6.2f} ms")
    print(f"  Frames > 16.67 ms: {sp16_z:3d} / {len(zoom_frame_times)} ({sp16_z/len(zoom_frame_times)*100:.1f}%)")
    print(f"  Frames > 33.33 ms: {sp33_z:3d} / {len(zoom_frame_times)} ({sp33_z/len(zoom_frame_times)*100:.1f}%)")

run_real_interaction_suite("Small File (~4 lines)", "small.py", py_small)
run_real_interaction_suite("Large File (~3,000 lines)", "large_3k.py", py_3000)
run_real_interaction_suite("Very Large File (~10,000 lines)", "large_10k.py", py_10000)

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass

print("\n>>> ALL REAL INTERACTION PASSES COMPLETED <<<")
