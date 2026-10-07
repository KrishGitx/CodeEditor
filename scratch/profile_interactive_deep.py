import sys, os, time, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, Qt
from PySide6.QtQuickControls2 import QQuickStyle
from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend, GlobalContextMenuFilter

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

editor = root_app.findChild(QObject, "editorArea")

py_small = "def foo():\n    # hello\n    return 42\n"

# 3,000 lines with multiline docstrings, nested scopes, and math
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

def benchmark_interaction(doc_label, filename, content):
    print(f"\n{'='*75}\nREAL USER INTERACTION BENCHMARK: {doc_label} ({filename})\n{'='*75}")
    editor.loadFile(filename, content)
    QCoreApplication.processEvents()

    ta = backend.qml_text_area
    doc = backend.text_document

    def get_flick():
        return editor.findChild(QObject, "editorFlickable")

    flick = get_flick()

    # -------------------------------------------------------------
    # 1. ACTUAL MOUSE-WHEEL SCROLLING (Simulating real mouse wheel ticks)
    # -------------------------------------------------------------
    print("\n[1] Mouse-Wheel Scrolling (100 rapid wheel ticks):")
    wheel_frame_times = []
    maxY = max(0, flick.property("contentHeight") - flick.property("height")) if flick else 0
    for i in range(100):
        t0 = time.perf_counter()
        flick = get_flick()
        if flick:
            lines = -120.0 / 120.0
            step = lines * 18.0 * 3.0
            current_y = flick.property("contentY")
            flick.setProperty("contentY", max(0, min(maxY, current_y - step)))
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        wheel_frame_times.append((t1 - t0) * 1000)

    avg_wheel = statistics.mean(wheel_frame_times)
    max_wheel = max(wheel_frame_times)
    p95_wheel = sorted(wheel_frame_times)[int(len(wheel_frame_times)*0.95)]
    p99_wheel = sorted(wheel_frame_times)[int(len(wheel_frame_times)*0.99)]
    spikes_16_wheel = len([t for t in wheel_frame_times if t > 16.67])
    spikes_33_wheel = len([t for t in wheel_frame_times if t > 33.33])

    print(f"  Avg frame time:    {avg_wheel:6.2f} ms")
    print(f"  Max frame time:    {max_wheel:6.2f} ms")
    print(f"  p95 frame time:    {p95_wheel:6.2f} ms")
    print(f"  p99 frame time:    {p99_wheel:6.2f} ms")
    print(f"  Frames > 16.67 ms: {spikes_16_wheel:3d} / {len(wheel_frame_times)} ({spikes_16_wheel/len(wheel_frame_times)*100:.1f}%)")
    print(f"  Frames > 33.33 ms: {spikes_33_wheel:3d} / {len(wheel_frame_times)} ({spikes_33_wheel/len(wheel_frame_times)*100:.1f}%)")

    # -------------------------------------------------------------
    # 2. SCROLLBAR THUMB DRAGGING (Simulating dragging thumb top to bottom)
    # -------------------------------------------------------------
    print("\n[2] Scrollbar Thumb Dragging (100 continuous drag steps):")
    drag_frame_times = []
    flick = get_flick()
    maxY = max(0, flick.property("contentHeight") - flick.property("height")) if flick else 0
    for i in range(100):
        target_y = (i / 100.0) * maxY
        t0 = time.perf_counter()
        if flick:
            flick.setProperty("contentY", target_y)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        drag_frame_times.append((t1 - t0) * 1000)

    avg_drag = statistics.mean(drag_frame_times)
    max_drag = max(drag_frame_times)
    p95_drag = sorted(drag_frame_times)[int(len(drag_frame_times)*0.95)]
    p99_drag = sorted(drag_frame_times)[int(len(drag_frame_times)*0.99)]
    spikes_16_drag = len([t for t in drag_frame_times if t > 16.67])
    spikes_33_drag = len([t for t in drag_frame_times if t > 33.33])

    print(f"  Avg frame time:    {avg_drag:6.2f} ms")
    print(f"  Max frame time:    {max_drag:6.2f} ms")
    print(f"  p95 frame time:    {p95_drag:6.2f} ms")
    print(f"  p99 frame time:    {p99_drag:6.2f} ms")
    print(f"  Frames > 16.67 ms: {spikes_16_drag:3d} / {len(drag_frame_times)} ({spikes_16_drag/len(drag_frame_times)*100:.1f}%)")
    print(f"  Frames > 33.33 ms: {spikes_33_drag:3d} / {len(drag_frame_times)} ({spikes_33_drag/len(drag_frame_times)*100:.1f}%)")

    # -------------------------------------------------------------
    # 3. TYPING IN THE MIDDLE OF FILE (50 keystrokes)
    # -------------------------------------------------------------
    print("\n[3A] Typing in Middle of File (50 continuous keystrokes):")
    mid_pos = len(content) // 2
    type_frame_times = []
    for i in range(50):
        t0 = time.perf_counter()
        ta.insert(mid_pos + i, "x")
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        type_frame_times.append((t1 - t0) * 1000)

    avg_type = statistics.mean(type_frame_times)
    max_type = max(type_frame_times)
    p95_type = sorted(type_frame_times)[int(len(type_frame_times)*0.95)]
    p99_type = sorted(type_frame_times)[int(len(type_frame_times)*0.99)]
    spikes_16_type = len([t for t in type_frame_times if t > 16.67])
    spikes_33_type = len([t for t in type_frame_times if t > 33.33])

    print(f"  Avg key latency:   {avg_type:6.2f} ms")
    print(f"  Max key latency:   {max_type:6.2f} ms")
    print(f"  p95 key latency:   {p95_type:6.2f} ms")
    print(f"  p99 key latency:   {p99_type:6.2f} ms")
    print(f"  Frames > 16.67 ms: {spikes_16_type:3d} / {len(type_frame_times)} ({spikes_16_type/len(type_frame_times)*100:.1f}%)")
    print(f"  Frames > 33.33 ms: {spikes_33_type:3d} / {len(type_frame_times)} ({spikes_33_type/len(type_frame_times)*100:.1f}%)")

    # -------------------------------------------------------------
    # 3B. TYPING NEAR MULTILINE / SCOPE CHANGE (30 keystrokes)
    # -------------------------------------------------------------
    print("\n[3B] Typing Near Multiline Docstring / Indentation Scope (30 keystrokes):")
    docstring_pos = content.find("'''") if "'''" in content else 10
    scope_type_times = []
    for i in range(30):
        t0 = time.perf_counter()
        ta.insert(docstring_pos + 3 + i, " ")
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        scope_type_times.append((t1 - t0) * 1000)

    avg_sc = statistics.mean(scope_type_times)
    max_sc = max(scope_type_times)
    p95_sc = sorted(scope_type_times)[int(len(scope_type_times)*0.95)]
    spikes_16_sc = len([t for t in scope_type_times if t > 16.67])

    print(f"  Avg key latency:   {avg_sc:6.2f} ms")
    print(f"  Max key latency:   {max_sc:6.2f} ms")
    print(f"  p95 key latency:   {p95_sc:6.2f} ms")
    print(f"  Frames > 16.67 ms: {spikes_16_sc:3d} / {len(scope_type_times)} ({spikes_16_sc/len(scope_type_times)*100:.1f}%)")

    # -------------------------------------------------------------
    # 4. CTRL+WHEEL ZOOM (10 rapid zoom steps)
    # -------------------------------------------------------------
    print("\n[4] Ctrl+Wheel Zoom (10 rapid zoom changes):")
    zoom_frame_times = []
    for sz in [14, 15, 16, 17, 18, 17, 16, 15, 14, 13]:
        t0 = time.perf_counter()
        editor.setEditorZoom(sz)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        zoom_frame_times.append((t1 - t0) * 1000)

    avg_zoom = statistics.mean(zoom_frame_times)
    max_zoom = max(zoom_frame_times)
    p95_zoom = sorted(zoom_frame_times)[int(len(zoom_frame_times)*0.95)]
    spikes_16_zoom = len([t for t in zoom_frame_times if t > 16.67])
    spikes_33_zoom = len([t for t in zoom_frame_times if t > 33.33])

    print(f"  Avg frame time:    {avg_zoom:6.2f} ms")
    print(f"  Max frame time:    {max_zoom:6.2f} ms")
    print(f"  p95 frame time:    {p95_zoom:6.2f} ms")
    print(f"  Frames > 16.67 ms: {spikes_16_zoom:3d} / {len(zoom_frame_times)} ({spikes_16_zoom/len(zoom_frame_times)*100:.1f}%)")
    print(f"  Frames > 33.33 ms: {spikes_33_zoom:3d} / {len(zoom_frame_times)} ({spikes_33_zoom/len(zoom_frame_times)*100:.1f}%)")

benchmark_interaction("Small File (~4 lines)", "small.py", py_small)
benchmark_interaction("Large File (~3,000 lines)", "large_3k.py", py_3000)
benchmark_interaction("Very Large File (~10,000 lines)", "large_10k.py", py_10000)

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass

print("\n[ALL BENCHMARKS COMPLETED SUCCESSFULLY]")
