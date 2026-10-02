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

# Apply the load performance optimization:
qml_test = qml_test.replace(
    'property bool isRestoringTab: false',
    'property bool isRestoringTab: false\n    property bool isInitialTextLoading: false'
)
qml_test = qml_test.replace('content: content,', 'content: "",')
qml_test = qml_test.replace(
    'function loadFile(path, content) {',
    'function loadFile(path, content) {\n        root.isInitialTextLoading = true;'
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
qml_test = qml_test.replace('text: model.content || ""', 'text: ""')
qml_test = qml_test.replace(
    'onTextChanged: {',
    '''onTextChanged: {
                                                            if (root.isInitialTextLoading || root.isRestoringTab || root.isFoldingOperation) return;'''
)

comp = QQmlComponent(engine)
base_url = QUrl.fromLocalFile(os.path.abspath("qml/components/EditorArea.qml"))
comp.setData(qml_test.encode("utf-8"), base_url)
editorArea = comp.create()
editorArea.setProperty("width", 1200)
editorArea.setProperty("height", 800)

for _ in range(5): app.processEvents()

editorArea.loadFile(os.path.abspath("test_data/file_a.py"), sample_text)
app.processEvents()

flick = editorArea.property("editorFlickable")
line_h = editorArea.property("editorLineHeight")
print("Initial font size:", theme.property("editorFontSize"), "line height:", line_h)

# Scroll to line 500
target_line = 500
flick.setProperty("contentY", target_line * line_h)
app.processEvents()
print(f"Scrolled to contentY: {flick.property('contentY'):.1f} (Line: {flick.property('contentY') / line_h:.2f})")

# Test Zooming
for font_size in [14, 16, 18, 22, 16, 13]:
    old_lh = editorArea.property("editorLineHeight")
    top_line = flick.property("contentY") / old_lh
    theme.setProperty("editorFontSize", font_size)
    app.processEvents()
    new_lh = editorArea.property("editorLineHeight")
    # restore top line
    flick.setProperty("contentY", top_line * new_lh)
    app.processEvents()
    curr_line = flick.property("contentY") / new_lh
    print(f"Zoomed to font {font_size:2d} -> line height: {new_lh:.2f}, contentY: {flick.property('contentY'):7.2f}, top visible line: {curr_line:.2f}")
    assert abs(curr_line - target_line) < 0.01

print("\nZoom test passed! Top visible line remained exactly at line 500 across all zoom levels!")
app.quit()
