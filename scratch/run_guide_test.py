import json
import subprocess

with open('qml/components/EditorArea.qml', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('function computeGuideSegmentsForText(docText)')
end = content.find('function recomputeScopes(docText)')
js_code = content[start:end]

runner = """
const theme = { tabSize: 4 };
""" + js_code + """
const testDoc = "public class Main {\\n    public static void main(String[] args) {\\n        try {\\n            // code\\n        }\\n    }\\n}";
console.log(JSON.stringify(computeGuideSegmentsForText(testDoc), null, 2));
"""

with open('scratch/temp_runner.js', 'w', encoding='utf-8') as f:
    f.write(runner)

res = subprocess.run(['node', 'scratch/temp_runner.js'], capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print('ERR:', res.stderr)

