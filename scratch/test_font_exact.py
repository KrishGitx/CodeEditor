import sys, os
sys.path.insert(0, os.path.abspath("."))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, QObject, QMetaObject, Q_ARG
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtGui import QFontMetrics, QFont
from main import EditorBackend

# Let's test the QML FontMetrics behavior
app = QApplication.instance() or QApplication(sys.argv)

fonts = ["Consolas", "Courier New", "Lucida Console"]
font_sizes = [9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 24]

print("=== VERIFYING FONT ADVANCE WIDTH CALCULATION ===")
for font_name in fonts:
    for sz in font_sizes:
        f = QFont(font_name, sz)
        fm = QFontMetrics(f)
        
        # Advance for N levels of 4 spaces
        tab_size = 4
        space_adv = fm.horizontalAdvance(" ")
        
        max_drift = 0.0
        for lvl in range(1, 9):
            # Advance of (lvl * tab_size) spaces:
            full_str = " " * (lvl * tab_size)
            actual_adv = fm.horizontalAdvance(full_str)
            
            # Cached calculation: fm.horizontalAdvance(" ".repeat(lvl * tab_size))
            calc_adv = fm.horizontalAdvance(full_str)
            
            diff = abs(calc_adv - actual_adv)
            if diff > max_drift:
                max_drift = diff
                
        print(f"Font: {font_name:14s} | Size: {sz:2d} | Space width: {space_adv:4.1f} | Level 1: {fm.horizontalAdvance('    '):5.1f} | Level 8: {fm.horizontalAdvance(' '*32):6.1f} | Max Drift: {max_drift:.2f}px")
