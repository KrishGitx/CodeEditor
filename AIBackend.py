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
            # 1. Live CustomApi.py ChatGPT client (Production path)
            if custom_api_available:
                try:
                    client = ChatGPTClient(headless=True)
                    response = client.ask(
                        self.prompt,
                        chunk_callback=lambda c: self.callback_chunk(c) if not self.cancelled else None
                    )
                    if response and not self.cancelled:
                        self.callback_done(clean_ai_text(response))
                        return
                    elif not response and not self.cancelled:
                        raise RuntimeError("No response returned from ChatGPT service.")
                except Exception as api_err:
                    print(f"[AIBackend] CustomApi query error: {api_err}")
                    if not self.cancelled:
                        self.callback_error(f"ChatGPT service error: {api_err}")
                        return

            if self.cancelled:
                return

            # 2. Developer Offline Mock Engine (ONLY behind explicit developer flag DGX_DEV_MOCK_AI=1)
            if os.environ.get("DGX_DEV_MOCK_AI") == "1":
                mock_response = (
                    "### DGX Dev Mock Assistant\n\n"
                    "Developer mock mode is active (`DGX_DEV_MOCK_AI=1`).\n\n"
                    "```text\n"
                    f"# Query received:\n{self.prompt[:160]}\n"
                    "```"
                )
                words = re.split(r'(\s+)', mock_response)
                accumulated = ""
                for word in words:
                    if self.cancelled:
                        return
                    accumulated += word
                    self.callback_chunk(word)
                    time.sleep(0.01)
                self.callback_done(accumulated)
                return

            # If CustomApi is unavailable and no dev mock flag is set, return a clear error
            if not self.cancelled:
                self.callback_error(
                    "ChatGPT AI assistant service is currently unavailable. "
                    "Please verify network connection and ChatGPT authentication."
                )

        except Exception as e:
            if not self.cancelled:
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

        if self.active_worker and self.active_worker.is_alive():
            try:
                self.active_worker.cancel()
            except Exception:
                pass

        self.current_msg_id += 1
        msg_id_str = f"msg_{self.current_msg_id}"

        # Emit user message for UI display - ONLY user visible prompt, NEVER internal instruction
        self.messageReceived.emit(f"user_{self.current_msg_id}", "user", prompt.strip())
        self.statusChanged.emit("thinking")

        def on_chunk(chunk):
            self.statusChanged.emit("streaming")
            self.chunkReceived.emit(msg_id_str, chunk)

        def on_done(full_text):
            cleaned = clean_ai_text(full_text)
            if cleaned and cleaned.strip():
                self.messageReceived.emit(msg_id_str, "assistant", cleaned)
                self.statusChanged.emit("idle")
            else:
                self.errorOccurred.emit("No response received from assistant.")
                self.statusChanged.emit("error")

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
