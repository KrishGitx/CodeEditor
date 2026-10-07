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

py_3000 = "\n".join([f"def py_func_{i}(x, y):\n    # Calculation {i}\n    val = x * {i} + len(str(y))\n    return val" for i in range(750)])

def profile_qml_content(qml_text, test_name):
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    comp = QQmlComponent(engine)
    comp.setData(qml_text.encode('utf-8'), "")
    if comp.isError():
        print(f"[{test_name}] Compilation Error:", comp.errors())
        return
    obj = comp.create()
    editor = obj.findChild(QObject, "editorArea") or obj
    
    t0 = time.perf_counter()
    if hasattr(editor, "loadFile"):
        editor.loadFile("test.py", py_3000)
    t1 = time.perf_counter()
    
    t_pe0 = time.perf_counter()
    QCoreApplication.processEvents()
    t_pe1 = time.perf_counter()
    
    print(f"[{test_name}] loadFile: {(t1-t0)*1000:6.2f} ms | processEvents: {(t_pe1-t_pe0)*1000:6.2f} ms")

# Let's read EditorArea.qml
with open("qml/components/EditorArea.qml", "r", encoding="utf-8") as f:
    editor_qml = f.read()

# Test with original
print("="*70)
print("TEST 1: Original EditorArea.qml (wrapped in simple root)")
print("="*70)
wrapper_qml = f"""
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {{
    width: 1200; height: 800
    EditorArea {{
        id: editorArea
        objectName: "editorArea"
        anchors.fill: parent
    }}
}}
"""
profile_qml_content(wrapper_qml, "Full EditorArea")

# Test 2: Without indentGuidesCanvas (canvas onPaint / updatePaneScopes)
qml_no_canvas = editor_qml.replace("paneGuideSegments = root.computeGuideSegmentsForText(codeTextArea.text);", "// paneGuideSegments = []")
qml_no_canvas = qml_no_canvas.replace("paneScopeRanges = root.computeScopesForText(codeTextArea.text);", "// paneScopeRanges = []")
qml_no_canvas = qml_no_canvas.replace("indentGuidesCanvas.requestPaint();", "// indentGuidesCanvas.requestPaint();")
# Write temp
with open("qml/components/EditorArea_no_canvas.qml", "w", encoding="utf-8") as f:
    f.write(qml_no_canvas)

wrapper_no_canvas = """
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    width: 1200; height: 800
    EditorArea_no_canvas {
        id: editorArea
        objectName: "editorArea"
        anchors.fill: parent
    }
}
"""
profile_qml_content(wrapper_no_canvas, "EditorArea without Scopes/Canvas")

# Test 3: Without Gutter Repeater (line numbers)
qml_no_gutter = qml_no_canvas.replace("model: gutter.visibleLineCount > 0 ? gutter.visibleLineCount : 0", "model: 0")
with open("qml/components/EditorArea_no_gutter.qml", "w", encoding="utf-8") as f:
    f.write(qml_no_gutter)

wrapper_no_gutter = """
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    width: 1200; height: 800
    EditorArea_no_gutter {
        id: editorArea
        objectName: "editorArea"
        anchors.fill: parent
    }
}
"""
profile_qml_content(wrapper_no_gutter, "EditorArea without Scopes + without Gutter")

# Clean up temp files
for p in ["qml/components/EditorArea_no_canvas.qml", "qml/components/EditorArea_no_gutter.qml"]:
    if os.path.exists(p): os.remove(p)

if backend.lsp_process:
    try: backend.lsp_process.terminate()
    except Exception: pass
sys.exit(0)
