import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication, QTextCursor
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject, QTimer, QElapsedTimer
from main import EditorBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root_app = comp.create()
editor = root_app.findChild(QObject, "editorArea")

py_small = "def foo():\n    print('hello world')\n    return 42\n"
py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])

def profile_continuous_interaction(label, filename, content):
    print(f"\n{'='*70}\nPROFILING FRAME PACING & INTERACTION SMOOTHNESS: {label}\n{'='*70}")
    editor.loadFile(filename, content)
    QCoreApplication.processEvents()

    ta = backend.qml_text_area
    flick = editor.findChild(QObject, "editorFlickable")

    # 1. Continuous Scrolling Profile (simulate 60 frames of smooth scrolling)
    print("\n[1] Continuous Scrolling (60 frames):")
    scroll_frame_times = []
    max_scroll = 10000.0 if len(content) > 1000 else 50.0
    steps = 60
    for i in range(steps):
        target_y = (i / steps) * max_scroll
        t0 = time.perf_counter()
        if flick:
            flick.setProperty("contentY", target_y)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        frame_ms = (t1 - t0) * 1000
        scroll_frame_times.append(frame_ms)

    avg_scroll = sum(scroll_frame_times) / len(scroll_frame_times)
    max_scroll_t = max(scroll_frame_times)
    spikes_scroll = [t for t in scroll_frame_times if t > 16.67]
    print(f"  Avg frame time: {avg_scroll:6.2f} ms")
    print(f"  Max frame time: {max_scroll_t:6.2f} ms")
    print(f"  Spikes > 16.6ms: {len(spikes_scroll)} / {len(scroll_frame_times)} ({len(spikes_scroll)/len(scroll_frame_times)*100:.1f}%)")

    # 2. Continuous Cursor Navigation (simulate 60 rapid arrow key movements)
    print("\n[2] Continuous Cursor Navigation (60 steps):")
    cursor_frame_times = []
    max_pos = min(len(content) - 1, 5000)
    for i in range(steps):
        target_pos = int((i / steps) * max_pos)
        t0 = time.perf_counter()
        if ta:
            ta.setProperty("cursorPosition", target_pos)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        frame_ms = (t1 - t0) * 1000
        cursor_frame_times.append(frame_ms)

    avg_cursor = sum(cursor_frame_times) / len(cursor_frame_times)
    max_cursor = max(cursor_frame_times)
    spikes_cursor = [t for t in cursor_frame_times if t > 16.67]
    print(f"  Avg frame time: {avg_cursor:6.2f} ms")
    print(f"  Max frame time: {max_cursor:6.2f} ms")
    print(f"  Spikes > 16.6ms: {len(spikes_cursor)} / {len(cursor_frame_times)} ({len(spikes_cursor)/len(cursor_frame_times)*100:.1f}%)")

    # 3. Continuous Typing Stream (30 rapid keystrokes with 16ms cadence)
    print("\n[3] Continuous Typing Stream (30 keystrokes):")
    typing_frame_times = []
    for i in range(30):
        t0 = time.perf_counter()
        if ta:
            ta.insert(100 + i, "a")
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        frame_ms = (t1 - t0) * 1000
        typing_frame_times.append(frame_ms)

    avg_type = sum(typing_frame_times) / len(typing_frame_times)
    max_type = max(typing_frame_times)
    spikes_type = [t for t in typing_frame_times if t > 16.67]
    print(f"  Avg frame time: {avg_type:6.2f} ms")
    print(f"  Max frame time: {max_type:6.2f} ms")
    print(f"  Spikes > 16.6ms: {len(spikes_type)} / {len(typing_frame_times)} ({len(spikes_type)/len(typing_frame_times)*100:.1f}%)")

    # 4. Zoom Sweep (12 frames of zooming)
    print("\n[4] Continuous Zoom Sweep (12 steps):")
    zoom_frame_times = []
    sizes = [11, 12, 13, 14, 15, 16, 17, 16, 15, 14, 13, 12]
    for sz in sizes:
        t0 = time.perf_counter()
        editor.setEditorZoom(sz)
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        frame_ms = (t1 - t0) * 1000
        zoom_frame_times.append(frame_ms)

    avg_zoom = sum(zoom_frame_times) / len(zoom_frame_times)
    max_zoom = max(zoom_frame_times)
    spikes_zoom = [t for t in zoom_frame_times if t > 16.67]
    print(f"  Avg frame time: {avg_zoom:6.2f} ms")
    print(f"  Max frame time: {max_zoom:6.2f} ms")
    print(f"  Spikes > 16.6ms: {len(spikes_zoom)} / {len(zoom_frame_times)} ({len(spikes_zoom)/len(zoom_frame_times)*100:.1f}%)")

profile_continuous_interaction("Small File (~4 lines)", "small.py", py_small)
profile_continuous_interaction("Large File (~3000 lines)", "large_3k.py", py_3000)

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
