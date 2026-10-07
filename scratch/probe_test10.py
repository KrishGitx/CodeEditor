import sys
import os

sys.path.insert(0, r"c:\Users\amazi\OneDrive\Documents\DGX")
os.environ["PYTHONIOENCODING"] = "utf-8"

from AIBackend import AIWorkerThread
from scratch.test_pod_studio_fixes import INTERNAL_INSTRUCTION

prompt = (
    INTERNAL_INSTRUCTION +
    "\n\nasync function loadUser() {\n"
    "    const response = fetch('/api/user');\n"
    "    const data = await response.json();\n"
    "    return data;\n"
    "}\n\n"
    "Please review and improve the selected javascript code:\n\n"
    "```javascript\n"
    "const response = fetch('/api/user');\n"
    "```"
)

resp = []
w = AIWorkerThread(prompt, lambda c: None, lambda d: resp.append(d), lambda e: print('err', e))
w.run()
print("TEST 10 RESPONSE:\n" + (resp[0] if resp else "NO RESPONSE"))
