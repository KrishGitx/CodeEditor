import sys, os, time
sys.path.insert(0, os.path.abspath("."))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, QObject
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from main import EditorBackend

app = QApplication.instance() or QApplication(sys.argv)
backend = EditorBackend()

# Let's inspect how fast switching between two tabs is if each tab has its own editor surface or if we use a tab-editor model
print("Testing tab switch concepts...")
