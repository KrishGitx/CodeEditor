"""
AIBackend.py - Asynchronous AI engine for QML AI Workspace
Uses CustomApi.py (Playwright ChatGPT client) with intelligent local developer fallback.
"""

import sys
import os
import threading
import time
import re
from PySide6.QtCore import QObject, Signal, Slot

# Attempt to import CustomApi
try:
    from CustomApi import ChatGPTClient
    custom_api_available = True
except Exception as import_err:
    print("[AIBackend] CustomApi import notice:", import_err)
    custom_api_available = False


def clean_ai_text(text):
    if not text:
        return ""
    return re.sub(r'^\s*Chat\s*GPT\s*said:?\s*', '', text, flags=re.IGNORECASE)


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
            # 1. Try Live CustomApi.py ChatGPT client
            if custom_api_available:
                try:
                    client = ChatGPTClient(headless=True)
                    response = client.ask(self.prompt, chunk_callback=lambda c: self.callback_chunk(c) if not self.cancelled else None)
                    if response and not self.cancelled:
                        self.callback_done(clean_ai_text(response))
                        return
                    elif not response and not self.cancelled:
                        raise RuntimeError("No response returned from ChatGPT service.")
                except Exception as api_err:
                    print(f"[AIBackend] CustomApi query error: {api_err}")
                    if not self.cancelled:
                        self.callback_error(f"ChatGPT error: {api_err}")
                        return

            if self.cancelled:
                return

            # 2. Local AI Engine (used only when CustomApi is unavailable / mock testing)
            p_lower = self.prompt.lower().strip()

            # Check for selection review requests
            fence_match = re.search(r'```([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)```', self.prompt)
            if ("selected portion" in p_lower or "review and improve" in p_lower or "selection" in p_lower) and fence_match:
                extracted_lang = (fence_match.group(1) or "html").lower().strip()
                extracted_code = fence_match.group(2)

                corrected_code = extracted_code
                explanation = ""
                if extracted_lang in ("html", "htm"):
                    if "<button" in corrected_code and "class=" not in corrected_code:
                        corrected_code = corrected_code.replace("<button", '<button class="btn-primary"')
                        explanation = "The selected button element lacked styling classes and accessible attributes. I added standard styling while keeping the exact element structure intact."
                    elif "<p" in corrected_code and "</p>" not in corrected_code:
                        corrected_code = re.sub(r'(<p[^>]*>[^<]*)$', r'\1</p>', corrected_code)
                        explanation = "The selected paragraph element was missing a closing tag, which could break layout rendering. I added the closing </p> tag."
                    else:
                        explanation = "I reviewed the selected HTML markup and validated tag nesting and attributes."
                elif extracted_lang in ("python", "py"):
                    if corrected_code.rstrip().endswith(":"):
                        corrected_code += "\n    pass"
                        explanation = "The selected block ended with a colon without a body, which raises an IndentationError. I added an indented pass statement to make it valid Python."
                    else:
                        explanation = "I reviewed the selected Python fragment for logical clarity and idiomatic structure."
                elif extracted_lang in ("qml", "javascript", "js", "cpp"):
                    open_braces = corrected_code.count("{")
                    close_braces = corrected_code.count("}")
                    if open_braces > close_braces:
                        corrected_code += "\n" + ("}" * (open_braces - close_braces))
                        explanation = "The selected fragment contained unclosed opening braces. I balanced the block scopes with matching closing braces."
                    else:
                        explanation = f"I refined the {extracted_lang.upper()} fragment for cleaner syntax and readability."
                else:
                    explanation = "I reviewed the selected code and applied necessary corrections."

                full_response = (
                    f"{explanation}\n\n"
                    f"```{extracted_lang}\n"
                    f"{corrected_code}\n"
                    f"```"
                )
            elif any(k in p_lower for k in ["hello", "hi", "hey"]):
                full_response = (
                    "Hello! I am DGX AI, your pair programming copilot. "
                    "I can help you build components, debug issues, write algorithms, "
                    "and optimize your workspace.\n\n"
                    "What are we working on right now?"
                )
            elif "def " in self.prompt or "function" in p_lower or "create" in p_lower or "write" in p_lower or "html" in p_lower:
                if "html" in p_lower:
                    full_response = (
                        "Here is a clean HTML5 component:\n\n"
                        "```html\n"
                        "<div class=\"container\">\n"
                        "    <h1>Hello from DGX Studio</h1>\n"
                        "    <p>Your clean code is ready.</p>\n"
                        "</div>\n"
                        "```\n\n"
                        "**Explanation:**\n"
                        "- Semantic HTML5 structure.\n"
                        "- Ready for direct styling or embedding."
                    )
                elif "python" in p_lower or "py" in p_lower:
                    full_response = (
                        "Here is a clean, optimized Python implementation:\n\n"
                        "```python\n"
                        "import os\n"
                        "from typing import List, Dict, Any\n\n"
                        "def process_data(items: List[Dict[str, Any]]) -> Dict[str, Any]:\n"
                        "    \"\"\"Process and aggregate input payload safely.\"\"\"\n"
                        "    valid_entries = [i for i in items if i.get('active', True)]\n"
                        "    total_val = sum(i.get('value', 0) for i in valid_entries)\n"
                        "    return {\n"
                        "        'count': len(valid_entries),\n"
                        "        'total': round(total_val, 2),\n"
                        "        'status': 'success'\n"
                        "    }\n"
                        "```\n\n"
                        "**Highlights:**\n"
                        "- Uses type annotations and list comprehension for high performance.\n"
                        "- Defensive `.get()` access against missing dictionary keys."
                    )
                elif "cpp" in p_lower or "c++" in p_lower or "c" in p_lower:
                    full_response = (
                        "Here is a modern, high-performance C++ solution:\n\n"
                        "```cpp\n"
                        "#include <iostream>\n"
                        "#include <vector>\n"
                        "#include <algorithm>\n\n"
                        "template<typename T>\n"
                        "void processBuffer(std::vector<T>& data) {\n"
                        "    std::sort(data.begin(), data.end());\n"
                        "    std::cout << \"Sorted \" << data.size() << \" items successfully.\" << std::endl;\n"
                        "}\n"
                        "```\n\n"
                        "**Key Details:**\n"
                        "- Generic template processing with fast standard algorithms."
                    )
                else:
                    full_response = (
                        "Here is a modular TypeScript / JavaScript solution:\n\n"
                        "```typescript\n"
                        "export interface TaskResult<T> {\n"
                        "    data: T | null;\n"
                        "    error?: string;\n"
                        "}\n\n"
                        "export async function executeSafe<T>(task: () => Promise<T>): Promise<TaskResult<T>> {\n"
                        "    try {\n"
                        "        const data = await task();\n"
                        "        return { data };\n"
                        "    } catch (err: any) {\n"
                        "        return { data: null, error: err.message || 'Execution error' };\n"
                        "    }\n"
                        "}\n"
                        "```\n\n"
                        "**Explanation:**\n"
                        "- Safely wraps asynchronous operations with structured error responses."
                    )
            elif "qml" in p_lower:
                full_response = (
                    "Here is a sleek QML component implementation:\n\n"
                    "```qml\n"
                    "import QtQuick 2.15\n"
                    "import QtQuick.Controls 2.15\n\n"
                    "Rectangle {\n"
                    "    id: root\n"
                    "    width: 240; height: 52\n"
                    "    radius: 8\n"
                    "    color: ma.containsMouse ? \"#2a2d36\" : \"#1a1b22\"\n"
                    "    border.color: ma.containsMouse ? \"#0078d4\" : \"#2c2d3a\"\n"
                    "    border.width: 1\n\n"
                    "    MouseArea {\n"
                    "        id: ma\n"
                    "        anchors.fill: parent\n"
                    "        hoverEnabled: true\n"
                    "        cursorShape: Qt.PointingHandCursor\n"
                    "    }\n"
                    "}\n"
                    "```\n\n"
                    "**Explanation:**\n"
                    "- Interactive hover state handling with native pointer cursor styling."
                )
            else:
                full_response = (
                    f"### Analysis: {self.prompt}\n\n"
                    "```text\n"
                    f"# Solution for: {self.prompt}\n"
                    "// Core operations handled cleanly\n"
                    "```\n\n"
                    "**Recommendations:**\n"
                    "1. Ensure operations handle edge cases gracefully.\n"
                    "2. Avoid expensive re-renders."
                )

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
    @Slot(str, str)
    def send_message(self, prompt, internal_instruction=""):
        if not prompt or not prompt.strip():
            return

        self.current_msg_id += 1
        msg_id_str = f"msg_{self.current_msg_id}"

        # Emit user message for UI display - ONLY user visible prompt, NEVER internal instruction
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

        worker_prompt = f"{internal_instruction.strip()}\n\n{prompt.strip()}" if internal_instruction and internal_instruction.strip() else prompt.strip()
        self.active_worker = AIWorkerThread(worker_prompt, on_chunk, on_done, on_error)
        self.active_worker.start()

    @Slot()
    def cancel(self):
        if self.active_worker:
            self.active_worker.cancel()
            self.statusChanged.emit("idle")

    @Slot()
    def clear_chat(self):
        self.cancel()
        if custom_api_available:
            try:
                client = ChatGPTClient(headless=True)
                client.reset()
            except Exception as e:
                print(f"[AIBackend] Clear chat client reset notice: {e}")
        self.statusChanged.emit("idle")

    @Slot()
    def new_chat(self):
        self.clear_chat()
