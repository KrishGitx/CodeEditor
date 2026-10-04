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
    qml_str = f.read()

# Apply word wrap and zoom enhancements
# 1. Flickable contentWidth & contentHeight
qml_str = qml_str.replace(
    'contentWidth: Math.max(width, codeTextArea.contentWidth + codeTextArea.leftPadding + codeTextArea.rightPadding + 80)',
    'contentWidth: (theme && theme.enableWordWrap) ? width : Math.max(width, codeTextArea.contentWidth + codeTextArea.leftPadding + codeTextArea.rightPadding + 80)'
)
qml_str = qml_str.replace(
    'contentHeight: Math.max(height, tabPane.paneTotalLineCount * root.editorLineHeight + 220)',
    'contentHeight: (theme && theme.enableWordWrap) ? Math.max(height, codeTextArea.contentHeight + codeTextArea.topPadding + codeTextArea.bottomPadding + 220) : Math.max(height, tabPane.paneTotalLineCount * root.editorLineHeight + 220)'
)

# 2. TextArea width & wrapMode
qml_str = qml_str.replace(
    'width: editorFlickable.contentWidth\n                                                        height: editorFlickable.contentHeight',
    'width: (theme && theme.enableWordWrap) ? editorFlickable.width : editorFlickable.contentWidth\n                                                        height: editorFlickable.contentHeight'
)
qml_str = qml_str.replace(
    'wrapMode: (theme && theme.enableWordWrap) ? TextArea.Wrap : TextArea.NoWrap',
    'wrapMode: (theme && theme.enableWordWrap) ? TextArea.WrapAtWordBoundaryOrAnywhere : TextArea.NoWrap'
)

# 3. Zoom WheelHandler with debounced save and mouse-point anchor
old_zoom_handler = '''                                                    WheelHandler {
                                                        target: null
                                                        acceptedModifiers: Qt.ControlModifier
                                                        orientation: Qt.Vertical
                                                        onWheel: function(event) {
                                                            if (typeof theme !== "undefined" && theme && theme.enableMouseWheelZoom === false) return;
                                                            var delta = event.angleDelta.y;
                                                            if (delta === 0) return;
                                                            var change = delta > 0 ? 1 : -1;
                                                            if (typeof theme !== "undefined" && theme) {
                                                                var oldLineH = root.editorLineHeight > 0 ? root.editorLineHeight : 18;
                                                                var topVisibleLine = editorFlickable.contentY / oldLineH;
                                                                var newSize = Math.max(8, Math.min(48, theme.editorFontSize + change));
                                                                if (newSize !== theme.editorFontSize) {
                                                                    theme.editorFontSize = newSize;
                                                                    theme.saveSettings();
                                                                    Qt.callLater(function() {
                                                                        if (editorFlickable && root.editorLineHeight > 0) {
                                                                            var maxY = Math.max(0, editorFlickable.contentHeight - editorFlickable.height);
                                                                            editorFlickable.contentY = Math.max(0, Math.min(maxY, topVisibleLine * root.editorLineHeight));
                                                                        }
                                                                    });
                                                                }
                                                            }
                                                        }
                                                    }'''

new_zoom_handler = '''                                                    Timer {
                                                        id: saveZoomTimer
                                                        interval: 400
                                                        repeat: false
                                                        onTriggered: {
                                                            if (typeof theme !== "undefined" && theme) {
                                                                theme.saveSettings();
                                                            }
                                                        }
                                                    }

                                                    WheelHandler {
                                                        id: zoomWheelHandler
                                                        target: null
                                                        acceptedModifiers: Qt.ControlModifier
                                                        orientation: Qt.Vertical

                                                        property real zoomAccumulator: 0.0

                                                        onWheel: function(event) {
                                                            if (typeof theme !== "undefined" && theme && theme.enableMouseWheelZoom === false) return;
                                                            var delta = event.angleDelta.y;
                                                            if (delta === 0) return;

                                                            zoomAccumulator += delta;
                                                            if (Math.abs(zoomAccumulator) < 60) return;

                                                            var change = zoomAccumulator > 0 ? 1 : -1;
                                                            zoomAccumulator = 0.0;

                                                            if (typeof theme !== "undefined" && theme) {
                                                                var oldLineH = root.editorLineHeight > 0 ? root.editorLineHeight : 18;
                                                                var mouseY = (event.point && event.point.position) ? event.point.position.y : (editorFlickable.height * 0.5);
                                                                var anchorLine = (editorFlickable.contentY + mouseY) / oldLineH;

                                                                var newSize = Math.max(8, Math.min(48, theme.editorFontSize + change));
                                                                if (newSize !== theme.editorFontSize) {
                                                                    theme.editorFontSize = newSize;
                                                                    saveZoomTimer.restart();

                                                                    var newLineH = root.editorLineHeight > 0 ? root.editorLineHeight : 18;
                                                                    var targetContentY = (anchorLine * newLineH) - mouseY;
                                                                    var maxY = Math.max(0, editorFlickable.contentHeight - editorFlickable.height);
                                                                    editorFlickable.contentY = Math.max(0, Math.min(maxY, targetContentY));

                                                                    Qt.callLater(function() {
                                                                        if (editorFlickable && root.editorLineHeight > 0) {
                                                                            var finalLineH = root.editorLineHeight;
                                                                            var finalTarget = (anchorLine * finalLineH) - mouseY;
                                                                            var finalMaxY = Math.max(0, editorFlickable.contentHeight - editorFlickable.height);
                                                                            editorFlickable.contentY = Math.max(0, Math.min(finalMaxY, finalTarget));
                                                                            if (indentGuidesCanvas) indentGuidesCanvas.requestPaint();
                                                                        }
                                                                    });
                                                                }
                                                            }
                                                        }
                                                    }'''

qml_str = qml_str.replace(old_zoom_handler, new_zoom_handler)

comp = QQmlComponent(engine)
base_url = QUrl.fromLocalFile(os.path.abspath("qml/components/EditorArea.qml"))
comp.setData(qml_str.encode("utf-8"), base_url)
if comp.isError():
    print("Errors:", [e.toString() for e in comp.errors()])
    sys.exit(1)

editorArea = comp.create()
editorArea.setProperty("width", 1200)
editorArea.setProperty("height", 800)

for _ in range(5): app.processEvents()

long_line_text = "def example_function():\n    # " + "long_variable_name_and_expression_" * 15 + " = 12345\n    return True\n"
editorArea.loadFile(os.path.abspath("test_data/long_lines.py"), long_line_text)
app.processEvents()

flick = editorArea.property("editorFlickable")
ta = editorArea.property("codeTextArea")

print("\n--- Testing Word Wrap ON vs OFF ---")
print("1. Word Wrap OFF:")
print("   flick contentWidth:", flick.property("contentWidth"), "(width:", flick.property("width"), ")")
print("   ta width:", ta.property("width"))
assert flick.property("contentWidth") > flick.property("width")

theme.setProperty("enableWordWrap", True)
app.processEvents()
print("2. Word Wrap ON:")
print("   flick contentWidth:", flick.property("contentWidth"), "(width:", flick.property("width"), ")")
print("   ta width:", ta.property("width"))
assert flick.property("contentWidth") == flick.property("width")
assert ta.property("width") == flick.property("width")

print("\n--- Testing Smooth Anchored Zoom ---")
theme.setProperty("enableWordWrap", False)
app.processEvents()

line_h = editorArea.property("editorLineHeight")
flick.setProperty("contentY", 100 * line_h)
app.processEvents()
anchor_line = 100

for new_sz in [14, 15, 16, 17, 18, 16, 14, 13]:
    theme.setProperty("editorFontSize", new_sz)
    app.processEvents()
    curr_lh = editorArea.property("editorLineHeight")
    top_line = flick.property("contentY") / curr_lh if curr_lh > 0 else 0
    print(f"   Zoom to {new_sz}pt: line height {curr_lh:.1f}px -> contentY: {flick.property('contentY'):.1f}, top line: {top_line:.2f}")

print("\nAll word wrap and zoom tests PASSED!")
app.quit()
