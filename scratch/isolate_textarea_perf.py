import sys, os, time
sys.path.insert(0, os.getcwd())

from PySide6.QtGui import QGuiApplication, QTextDocument
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import Qt, QMetaObject, Q_ARG
from PySide6.QtQuickControls2 import QQuickStyle

os.environ['QT_QUICK_CONTROLS_STYLE'] = 'Basic'
app = QGuiApplication(sys.argv)
QQuickStyle.setStyle('Basic')

with open("test_data/file_a.py", "r", encoding="utf-8") as f:
    sample_text = f.read()

print(f"Sample text length: {len(sample_text)} chars, {sample_text.count(chr(10))} lines")

engine = QQmlApplicationEngine()

# Test 1: Bare QTextDocument creation & setPlainText
t0 = time.perf_counter()
doc = QTextDocument()
doc.setPlainText(sample_text)
t1 = time.perf_counter()
print(f"QTextDocument setPlainText: {(t1 - t0)*1000:.2f} ms")

# Test 2: Bare TextArea in QML
comp_str = """
import QtQuick 2.15
import QtQuick.Controls 2.15
Item {
    width: 800; height: 600
    TextArea {
        id: ta
        width: 800; height: 600
        textFormat: TextArea.PlainText
        font.family: "Consolas"
        font.pixelSize: 13
        wrapMode: TextArea.NoWrap
    }
}
"""
comp = QQmlComponent(engine)
comp.setData(comp_str.encode('utf-8'), "")
obj = comp.create()
ta = obj.findChild(object)

t0 = time.perf_counter()
# set text
ta.setProperty("text", sample_text)
t1 = time.perf_counter()
print(f"Bare TextArea setProperty('text'): {(t1 - t0)*1000:.2f} ms")

t2 = time.perf_counter()
app.processEvents()
t3 = time.perf_counter()
print(f"Bare TextArea processEvents: {(t3 - t2)*1000:.2f} ms")

# Test 3: Bare TextArea with Highlighter attached
from HighlighterEngine import MultiLanguageHighlighter
hl = MultiLanguageHighlighter(None)
hl.set_language("python")
doc_qquick = ta.property("textDocument").property("textDocument")
hl.setDocument(doc_qquick)

t0 = time.perf_counter()
app.processEvents()
t1 = time.perf_counter()
print(f"Highlighter setDocument + processEvents: {(t1 - t0)*1000:.2f} ms")

app.quit()
