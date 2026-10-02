import sys, os, time
sys.path.insert(0, os.getcwd())

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import Qt, QUrl
from PySide6.QtQuickControls2 import QQuickStyle

os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
app = QGuiApplication(sys.argv)
QQuickStyle.setStyle('Basic')

from main import EditorBackend
from SettingsBackend import SettingsBackend

with open("test_data/file_a.py", "r", encoding="utf-8") as f:
    sample_text = f.read()

with open("qml/components/EditorArea.qml", "r", encoding="utf-8") as f:
    orig_qml = f.read()

def test_qml(label, qml_content):
    backend = EditorBackend()
    settingsBackend = SettingsBackend()
    backend.settings_backend = settingsBackend

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

    theme_comp = QQmlComponent(engine, "qml/Theme.qml")
    theme = theme_comp.create()
    engine.rootContext().setContextProperty("theme", theme)

    comp = QQmlComponent(engine)
    base_url = QUrl.fromLocalFile(os.path.abspath("qml/components/EditorArea.qml"))
    comp.setData(qml_content.encode("utf-8"), base_url)
    if comp.isError():
        print(f"[{label}] Errors:", [e.toString() for e in comp.errors()])
        return
    editorArea = comp.create()
    editorArea.setProperty("width", 1200)
    editorArea.setProperty("height", 800)

    for _ in range(5): app.processEvents()

    t0 = time.perf_counter()
    editorArea.loadFile(os.path.abspath("test_data/file_a.py"), sample_text)
    t1 = time.perf_counter()
    app.processEvents()
    t2 = time.perf_counter()
    print(f"[{label}]: loadFile {(t1 - t0)*1000:.1f} ms | processEvents {(t2 - t1)*1000:.1f} ms | Total: {(t2 - t0)*1000:.1f} ms")

print("--- Binary Search on EditorArea.qml ---")
test_qml("Full Baseline", orig_qml)

# B1: Remove everything after line 1345 (Secondary editor, split pane, findReplaceBar, color picker, etc.)
idx_split = orig_qml.find("// 1.2 Whiteboard Canvas Tab View")
if idx_split != -1:
    # Keep up to idx_split, close codeEditorContainer, primaryEditorContainer, RowLayout, mainEditorSurface, ColumnLayout, root Item
    # and re-add loadFile and switchToTab functions
    qml_b1 = orig_qml[:idx_split] + """
                    }
                }
            }
        }
    }
    function loadFile(path, content) {
        var fileName = path.split("/").pop().split("\\\\").pop();
        var newIdx = tabModel.count;
        tabModel.append({
            fileId: "file_" + Date.now(),
            title: fileName,
            path: path,
            content: content,
            isDirty: false,
            languageName: "Python",
            languageId: "python",
            cursorPos: 0, scrollX: 0, scrollY: 0
        });
        switchToTab(newIdx);
    }
    function switchToTab(index) {
        root.activeTabIndex = index;
        if (tabEditorStack) tabEditorStack.currentIndex = index;
        var newTab = tabModel.get(index);
        if (root.codeTextArea && typeof backend !== "undefined" && backend.register_text_area) {
            backend.register_text_area(root.codeTextArea, newTab.path, newTab.languageId);
        }
    }
}
"""
    test_qml("B1 (Only primary editor container, no secondary/overlays)", qml_b1)

app.quit()
