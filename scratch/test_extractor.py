import sys
import json
from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QJSEngine

app = QCoreApplication(sys.argv)
engine = QJSEngine()
with open('qml/ai/CodeExtractor.js', 'r', encoding='utf-8') as f:
    js_content = f.read().replace('.pragma library', '')
engine.evaluate(js_content)

test_cases = [
    (
        "HTML with explanation before and after",
        """There's one syntax error in your HTML. The key correction is closing the <div> tag.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Fixed Document</title>
</head>
<body>
    <div class="container">
        <h1>Fixed Title</h1>
        <p>This is corrected HTML content.</p>
    </div>
</body>
</html>
```

Explanation:
1. Added missing closing div tag.
2. Standardized HTML5 structure.""",
        "html"
    ),
    (
        "Unclosed fence",
        """Here is the fixed code:

```python
def calculate_sum(a, b):
    return a + b
""",
        "python"
    ),
    (
        "Multiple code fences with preferred language",
        """Here is the QML code and Python backend:

```python
import sys
print("Backend")
```

And the QML UI:

```qml
import QtQuick 2.15
Item {
    width: 100
    height: 100
}
```
""",
        "qml"
    ),
    (
        "No fences, fallback text",
        """Here is your code:
def hello():
    print("Hello world")

Hope this helps!""",
        "python"
    ),
    (
        "ChatGPT web text format with Copy code header",
        """There's one syntax error in your HTML. The key correction is closing the <div> tag.

html
Copy code
<!DOCTYPE html>
<html>
<body>
  <div>Fixed</div>
</body>
</html>

The explanation follows.""",
        "html"
    )
]

for title, resp, lang in test_cases:
    code_eval = f"extractCodeFromMarkdown({json.dumps(resp)}, {json.dumps(lang)})"
    res = engine.evaluate(code_eval).toString()
    print(f"=== TEST: {title} (lang={lang}) ===")
    print("Extracted:")
    print(res)
    print("-----------------------------------")
