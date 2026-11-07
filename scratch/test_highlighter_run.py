import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PySide6.QtGui import QTextDocument, QColor
import HighlighterEngine

def test_highlighter():
    HighlighterEngine.reload_themes()
    doc = QTextDocument()
    hl = HighlighterEngine.MultiLanguageHighlighter(doc, "orange_ocean")
    hl.set_language_for_file("LCP.cpp")

    sample = """#include <string>
#include <iostream>
#include <vector>

using namespace std;

int main() {
    cout << "Hello" << endl;
    vector<string> strs = {"aa", "ab"};

    int count, i = 0, j = strs.size() - 1, k = 0; // j == 1
    while (i != j) {
        if (lngstring[k] == strs[j][k]) {
            return 0;
        }
    }
}"""
    doc.setPlainText(sample)

    print("Formats for sample lines:")
    for b_idx in range(doc.blockCount()):
        block = doc.findBlockByNumber(b_idx)
        text = block.text()
        if not text.strip():
            continue
        formats = block.layout().formats()
        ranges = []
        for r in formats:
            sub = text[r.start:r.start + r.length]
            color = r.format.foreground().color().name()
            ranges.append((sub, color))
        print(f"Line {b_idx+1}: {text}")
        print(f"  -> {ranges}")

if __name__ == "__main__":
    test_highlighter()
