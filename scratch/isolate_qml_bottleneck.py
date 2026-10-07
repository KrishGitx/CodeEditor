import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
os.environ['QSG_RENDER_LOOP'] = 'basic'

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QObject
from main import EditorBackend

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
backend = EditorBackend()

# Let's generate a 3,000 line Python file
lines_3000 = [f"def test_func_{i}(a, b):\n    # line {i}\n    val = a + b * {i}\n    return val" for i in range(750)]
py_3000 = "\n".join(lines_3000)

def test_qml_snippet(qml_code, description):
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    comp = QQmlComponent(engine)
    comp.setData(qml_code.encode('utf-8'), "")
    if comp.isError():
        print(f"Error in {description}:", comp.errors())
        return
    obj = comp.create()
    
    t0 = time.perf_counter()
    QCoreApplication.processEvents()
    t1 = time.perf_counter()
    print(f"[{description}] Initial layout/render: {(t1-t0)*1000:.2f} ms")

# Test 1: Bare QML TextArea with 3000 lines
qml_bare_textarea = f"""
import QtQuick 2.15
import QtQuick.Controls 2.15

Item {{
    width: 1000; height: 800
    Flickable {{
        anchors.fill: parent
        TextArea.flickable: TextArea {{
            text: {repr(py_3000)}
            font.family: "Consolas"
            font.pixelSize: 13
            wrapMode: Text.NoWrap
        }}
    }}
}}
"""
test_qml_snippet(qml_bare_textarea, "1. Bare QML TextArea (NoWrap)")

# Test 2: Bare QML TextArea with Wrap
qml_bare_textarea_wrap = f"""
import QtQuick 2.15
import QtQuick.Controls 2.15

Item {{
    width: 1000; height: 800
    Flickable {{
        anchors.fill: parent
        TextArea.flickable: TextArea {{
            text: {repr(py_3000)}
            font.family: "Consolas"
            font.pixelSize: 13
            wrapMode: Text.Wrap
        }}
    }}
}}
"""
test_qml_snippet(qml_bare_textarea_wrap, "2. Bare QML TextArea (Wrap)")

# Test 3: Bare QML TextArea + Highlighter
qml_textarea_hl = f"""
import QtQuick 2.15
import QtQuick.Controls 2.15

Item {{
    id: root
    width: 1000; height: 800
    Flickable {{
        anchors.fill: parent
        TextArea.flickable: TextArea {{
            id: ta
            text: {repr(py_3000)}
            font.family: "Consolas"
            font.pixelSize: 13
            wrapMode: Text.NoWrap
            Component.onCompleted: {{
                backend.register_text_area(ta, "test.py", "python")
            }}
        }}
    }}
}}
"""
test_qml_snippet(qml_textarea_hl, "3. Bare QML TextArea + MultiLanguageHighlighter")

# Test 4: Full EditorArea with different sub-features disabled
print("\n" + "="*70)
print("TESTING FULL EDITOR AREA WITH SUB-FEATURE BREAKDOWN")
print("="*70)

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
comp = QQmlComponent(engine, os.path.abspath("qml/main.qml"))
root_app = comp.create()
editor = root_app.findChild(QObject, "editorArea")

# Measure step-by-step
t0 = time.perf_counter()
editor.loadFile("test_3000.py", py_3000)
t1 = time.perf_counter()
print(f"loadFile call: {(t1-t0)*1000:.2f} ms")

t2 = time.perf_counter()
QCoreApplication.processEvents()
t3 = time.perf_counter()
print(f"processEvents after loadFile: {(t3-t2)*1000:.2f} ms")

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
