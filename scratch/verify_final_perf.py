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
    file_a_text = f.read()

with open("test_data/file_b.py", "r", encoding="utf-8") as f:
    file_b_text = f.read()

backend = EditorBackend()
settingsBackend = SettingsBackend()
backend.settings_backend = settingsBackend

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)
engine.rootContext().setContextProperty("settingsBackend", settingsBackend)

theme_comp = QQmlComponent(engine, "qml/Theme.qml")
theme = theme_comp.create()
engine.rootContext().setContextProperty("theme", theme)

with open("qml/components/EditorArea.qml", "r", encoding="utf-8") as f:
    qml_test = f.read()

# Apply optimization:
qml_test = qml_test.replace(
    'property bool isRestoringTab: false',
    'property bool isRestoringTab: false\n    property bool isInitialTextLoading: false'
)

qml_test = qml_test.replace(
    'content: content,',
    'content: "",'
)

qml_test = qml_test.replace(
    'function loadFile(path, content) {',
    '''function loadFile(path, content) {
        root.isInitialTextLoading = true;'''
)

qml_test = qml_test.replace(
    'switchToTab(newIdx);',
    '''switchToTab(newIdx);
        if (root.activeEditorPane && root.activeEditorPane.codeTextArea) {
            root.activeEditorPane.codeTextArea.text = content;
            root.activeEditorPane.paneTotalLineCount = root.countLines(content);
            root.activeEditorPane.updatePaneScopes();
        }
        root.isInitialTextLoading = false;'''
)

qml_test = qml_test.replace(
    'text: model.content || ""',
    'text: ""'
)

qml_test = qml_test.replace(
    'if (model) {\n                                                                model.content = codeTextArea.text;\n                                                                if (!model.isDirty) {\n                                                                    model.isDirty = true;\n                                                                    root.activeFileChanged(model.path || "", model.title || "", root.currentLanguage, true);\n                                                                }\n                                                            }',
    '''if (tabPane.index >= 0 && tabPane.index < tabModel.count) {
                                                                tabModel.setProperty(tabPane.index, "isDirty", true);
                                                                var curTabObj = tabModel.get(tabPane.index);
                                                                root.activeFileChanged(curTabObj ? (curTabObj.path || "") : "", curTabObj ? (curTabObj.title || "") : "", root.currentLanguage, true);
                                                            }'''
)

qml_test = qml_test.replace(
    'onTextChanged: {',
    '''onTextChanged: {
                                                            if (root.isInitialTextLoading || root.isRestoringTab || root.isFoldingOperation) return;'''
)

comp = QQmlComponent(engine)
base_url = QUrl.fromLocalFile(os.path.abspath("qml/components/EditorArea.qml"))
comp.setData(qml_test.encode("utf-8"), base_url)
if comp.isError():
    print("Errors:", [e.toString() for e in comp.errors()])
    sys.exit(1)

editorArea = comp.create()
editorArea.setProperty("width", 1200)
editorArea.setProperty("height", 800)

for _ in range(5): app.processEvents()

print("\n=== Comprehensive Verification ===")

# Test 1: Open Large File A
t0 = time.perf_counter()
editorArea.loadFile(os.path.abspath("test_data/file_a.py"), file_a_text)
t1 = time.perf_counter()
app.processEvents()
t2 = time.perf_counter()
print(f"1. Open File A (3000 lines): {(t2 - t0)*1000:.2f} ms (JS: {(t1 - t0)*1000:.2f} ms, Events: {(t2 - t1)*1000:.2f} ms)")
assert len(editorArea.property("codeTextArea").property("text")) == len(file_a_text)
assert editorArea.property("isCurrentFileDirty") == False
print("   File A loaded cleanly, dirty:", editorArea.property("isCurrentFileDirty"), "lines:", editorArea.property("totalLineCount"))

# Test 2: Open Large File B
t0 = time.perf_counter()
editorArea.loadFile(os.path.abspath("test_data/file_b.py"), file_b_text)
t1 = time.perf_counter()
app.processEvents()
t2 = time.perf_counter()
print(f"2. Open File B (3000 lines): {(t2 - t0)*1000:.2f} ms (JS: {(t1 - t0)*1000:.2f} ms, Events: {(t2 - t1)*1000:.2f} ms)")
assert len(editorArea.property("codeTextArea").property("text")) == len(file_b_text)
assert editorArea.property("isCurrentFileDirty") == False
print("   File B loaded cleanly, dirty:", editorArea.property("isCurrentFileDirty"), "lines:", editorArea.property("totalLineCount"))

# Test 3: Tab Switching A -> B -> A
t0 = time.perf_counter()
editorArea.switchToTab(0)
app.processEvents()
t1 = time.perf_counter()
print(f"3. Switch Tab to File A: {(t1 - t0)*1000:.2f} ms")
assert "file_a.py" in editorArea.property("activeFilePath")
assert len(editorArea.property("codeTextArea").property("text")) == len(file_a_text)

t0 = time.perf_counter()
editorArea.switchToTab(1)
app.processEvents()
t1 = time.perf_counter()
print(f"4. Switch Tab to File B: {(t1 - t0)*1000:.2f} ms")
assert "file_b.py" in editorArea.property("activeFilePath")
assert len(editorArea.property("codeTextArea").property("text")) == len(file_b_text)

# Test 4: Edit Tab B, Switch to A, Switch back to B (Unsaved edit preserved)
ta_b = editorArea.property("codeTextArea")
ta_b.setProperty("text", "modified content line 1\nmodified line 2")
app.processEvents()
assert editorArea.property("isCurrentFileDirty") == True
print("5. Made edit in Tab B, isCurrentFileDirty:", editorArea.property("isCurrentFileDirty"))

editorArea.switchToTab(0)
app.processEvents()
print("   Switched to Tab A, dirty:", editorArea.property("isCurrentFileDirty"), "text length:", len(editorArea.property("codeTextArea").property("text")))
assert editorArea.property("isCurrentFileDirty") == False

editorArea.switchToTab(1)
app.processEvents()
print("   Switched back to Tab B, dirty:", editorArea.property("isCurrentFileDirty"), "text:", editorArea.property("codeTextArea").property("text"))
assert editorArea.property("isCurrentFileDirty") == True
assert editorArea.property("codeTextArea").property("text") == "modified content line 1\nmodified line 2"
print("   Unsaved edits and per-tab dirty state fully preserved!")

print("\nALL CHECKS PASSED 100% PERFECTLY!")
app.quit()
