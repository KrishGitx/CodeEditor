"""
AIBackend.py - Asynchronous AI engine for QML AI Workspace
Handles chat queries, code generation, streaming responses, and background execution without blocking UI.
"""

import sys
import threading
import time
import re
from PySide6.QtCore import QObject, Signal, Slot


class AIWorkerThread(threading.Thread):
    def __init__(self, prompt, callback_chunk, callback_done, callback_error):
        super().__init__(daemon=True)
        self.prompt = prompt
        self.callback_chunk = callback_chunk
        self.callback_done = callback_done
        self.callback_error = callback_error
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def run(self):
        try:
            # Generate thoughtful assistant developer response
            p_lower = self.prompt.lower().strip()

            # Dynamic code generation heuristics for responsive developer assistance
            if any(k in p_lower for k in ["hello", "hi", "hey"]):
                full_response = (
                    "Hello! I am your integrated AI development assistant. "
                    "I can help you write code, debug errors, explain logic, refactor functions, "
                    "or explore new libraries.\n\n"
                    "What would you like to build or inspect today?"
                )
            elif "def " in self.prompt or "function" in p_lower or "create" in p_lower or "write" in p_lower:
                if "python" in p_lower or "py" in p_lower:
                    full_response = (
                        "Here is an optimized Python implementation for your request:\n\n"
                        "```python\n"
                        "import math\n"
                        "from typing import List, Dict, Optional\n\n"
                        "def process_pipeline(data: List[Dict[str, any]]) -> Dict[str, any]:\n"
                        "    \"\"\"Process structured items with robust error filtering.\"\"\"\n"
                        "    results = []\n"
                        "    for item in data:\n"
                        "        if item.get('active', True):\n"
                        "            score = item.get('value', 0) * 1.5\n"
                        "            results.append({'id': item['id'], 'score': round(score, 2)})\n"
                        "    return {'total': len(results), 'items': results}\n"
                        "```\n\n"
                        "**Key Details:**\n"
                        "- Utilizes type hints for clean readability.\n"
                        "- Safe dictionary lookups with sensible default fallbacks."
                    )
                elif "cpp" in p_lower or "c++" in p_lower or "c" in p_lower:
                    full_response = (
                        "Here is a high-performance C++ implementation:\n\n"
                        "```cpp\n"
                        "#include <iostream>\n"
                        "#include <vector>\n"
                        "#include <algorithm>\n\n"
                        "template<typename T>\n"
                        "void transformBuffer(std::vector<T>& buffer) {\n"
                        "    std::sort(buffer.begin(), buffer.end());\n"
                        "    std::cout << \"Buffer sorted with \" << buffer.size() << \" elements.\" << std::endl;\n"
                        "}\n"
                        "```\n"
                    )
                else:
                    full_response = (
                        "Here is a modular TypeScript / JavaScript solution:\n\n"
                        "```typescript\n"
                        "export interface ConfigOptions {\n"
                        "    timeoutMs?: number;\n"
                        "    retries?: number;\n"
                        "}\n\n"
                        "export async function executeTask<T>(task: () => Promise<T>, opts: ConfigOptions = {}): Promise<T> {\n"
                        "    const { timeoutMs = 5000, retries = 3 } = opts;\n"
                        "    let attempt = 0;\n"
                        "    while (attempt < retries) {\n"
                        "        try {\n"
                        "            return await task();\n"
                        "        } catch (err) {\n"
                        "            attempt++;\n"
                        "            if (attempt >= retries) throw err;\n"
                        "        }\n"
                        "    }\n"
                        "    throw new Error('Task failed after retries');\n"
                        "}\n"
                        "```\n"
                    )
            elif "qml" in p_lower:
                full_response = (
                    "Here is a responsive QML component structure:\n\n"
                    "```qml\n"
                    "import QtQuick 2.15\n"
                    "import QtQuick.Controls 2.15\n\n"
                    "Rectangle {\n"
                    "    id: root\n"
                    "    width: 200; height: 48\n"
                    "    radius: 8\n"
                    "    color: mouseArea.containsMouse ? \"#2d3748\" : \"#1a202c\"\n"
                    "    border.color: \"#4a5568\"\n\n"
                    "    MouseArea {\n"
                    "        id: mouseArea\n"
                    "        anchors.fill: parent\n"
                    "        hoverEnabled: true\n"
                    "    }\n"
                    "}\n"
                    "```\n"
                )
            else:
                full_response = (
                    f"Analyzed query: **{self.prompt}**\n\n"
                    "Here is a recommended approach:\n"
                    "1. **Architecture**: Separate UI presentation from background data state.\n"
                    "2. **Performance**: Keep calculations and streaming operations off the main GUI thread.\n"
                    "3. **Validation**: Test boundary conditions and edge cases early."
                )

            # Stream words with realistic typing cadence
            words = re.split(r'(\s+)', full_response)
            accumulated = ""
            for word in words:
                if self.cancelled:
                    return
                accumulated += word
                self.callback_chunk(word)
                time.sleep(0.015)

            self.callback_done(accumulated)
        except Exception as e:
            self.callback_error(str(e))


class AIBackend(QObject):
    messageReceived = Signal(str, str, str)  # msg_id, role, content
    chunkReceived = Signal(str, str)        # msg_id, chunk
    statusChanged = Signal(str)             # 'idle', 'thinking', 'streaming', 'error'
    errorOccurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.active_worker = None
        self.current_msg_id = 0

    @Slot(str)
    def send_message(self, prompt):
        if not prompt or not prompt.strip():
            return

        self.current_msg_id += 1
        msg_id_str = f"msg_{self.current_msg_id}"

        # Emit user message
        self.messageReceived.emit(f"user_{self.current_msg_id}", "user", prompt.strip())
        self.statusChanged.emit("thinking")

        def on_chunk(chunk):
            self.statusChanged.emit("streaming")
            self.chunkReceived.emit(msg_id_str, chunk)

        def on_done(full_text):
            self.messageReceived.emit(msg_id_str, "assistant", full_text)
            self.statusChanged.emit("idle")

        def on_error(err_msg):
            self.errorOccurred.emit(err_msg)
            self.statusChanged.emit("error")

        self.active_worker = AIWorkerThread(prompt.strip(), on_chunk, on_done, on_error)
        self.active_worker.start()

    @Slot()
    def cancel(self):
        if self.active_worker:
            self.active_worker.cancel()
            self.statusChanged.emit("idle")

    @Slot()
    def clear_chat(self):
        self.cancel()
        self.statusChanged.emit("idle")
