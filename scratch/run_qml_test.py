import sys
import os
from PySide6.QtCore import QUrl, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

doc = '''context = browser.new_context(
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    viewport={"width": 1920, "height": 1080},
    locale="en-US",
    timezone_id="Asia/Kolkata",
)

page = context.new_page()

page.goto(
    "https://chatgpt.com/",
    wait_until="domcontentloaded",
)

print(page.title())
print(page.url)

textbox = page.get_by_role(
    "textbox",'''

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
engine.load(QUrl.fromLocalFile(os.path.abspath("qml/main.qml")))
root_objects = engine.rootObjects()
assert len(root_objects) > 0, "Failed to load qml/main.qml!"
main_window = root_objects[0]
editor_area = main_window.findChild(QObject, "editorArea")

segs = editor_area.computeGuideSegmentsForText(doc)
if hasattr(segs, "toVariant"):
    segs = segs.toVariant()

print("Segments count:", len(segs))
for s in segs:
    print(s)

