"""
AIBackend.py - Asynchronous & Synchronous AI engine for QML AI Workspace & Smart Install
Uses CustomApi.py (Playwright ChatGPT client) with intelligent local developer fallback.
"""

import sys
import os
import threading
import time
import re
from typing import Optional, Callable
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
            # 1. Custom mock resolver hook (For test environments)
            if AIBackend._custom_resolver and callable(AIBackend._custom_resolver):
                try:
                    res = AIBackend._custom_resolver(self.prompt)
                    if self.cancelled:
                        return
                    if res:
                        self.callback_done(clean_ai_text(str(res)))
                        return
                    else:
                        raise RuntimeError("AI provider returned empty response.")
                except Exception as mock_err:
                    if not self.cancelled:
                        self.callback_error(f"AI mock provider error: {mock_err}")
                        return

            # 2. Live CustomApi.py ChatGPT client (Production path)
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

            # 3. Developer Offline Mock Engine (ONLY behind explicit developer flag DGX_DEV_MOCK_AI=1)
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

    _instance: Optional["AIBackend"] = None
    _custom_resolver: Optional[Callable[[str], str]] = None

    @classmethod
    def get_instance(cls) -> "AIBackend":
        if cls._instance is None:
            cls._instance = AIBackend()
        return cls._instance

    @classmethod
    def set_ai_provider(cls, provider_fn: Optional[Callable[[str], str]]):
        cls._custom_resolver = provider_fn

    def __init__(self):
        super().__init__()
        AIBackend._instance = self
        self.active_worker = None
        self.current_msg_id = 0

    @property
    def is_connected(self) -> bool:
        if AIBackend._custom_resolver is not None:
            return True
        if custom_api_available:
            try:
                client = ChatGPTClient(headless=True)
                return getattr(client, "is_connected", False)
            except Exception:
                return False
        return False

    def ask(self, prompt: str) -> str:
        """
        Synchronously queries the centralized CustomApi / ChatGPT pipeline.
        Used by Smart Install and backend subsystems.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        # 1. Custom mock resolver hook (For test environments)
        if AIBackend._custom_resolver and callable(AIBackend._custom_resolver):
            print("[SmartInstall] CustomApi request sent")
            try:
                res = AIBackend._custom_resolver(prompt)
                if not res or not str(res).strip():
                    raise RuntimeError("Empty response returned from AI service.")
                print("[SmartInstall] CustomApi response received")
                return clean_ai_text(str(res).strip())
            except Exception as ex:
                print(f"[SmartInstall] CustomApi request failed: {ex}")
                raise

        # 2. Live CustomApi.py ChatGPTClient (Production path)
        if custom_api_available:
            print("[SmartInstall] CustomApi request sent")
            try:
                client = ChatGPTClient(headless=True)
                response = client.ask(prompt)
                if not response or not str(response).strip():
                    raise RuntimeError("No response returned from ChatGPT service.")
                print("[SmartInstall] CustomApi response received")
                return clean_ai_text(response)
            except Exception as ex:
                print(f"[SmartInstall] CustomApi request failed: {ex}")
                raise

        # 3. CustomApi unavailable (e.g. missing Playwright)
        err_msg = "CustomApi dependency unavailable (Playwright not installed or failed to import)."
        print(f"[SmartInstall] CustomApi request failed: {err_msg}")
        raise RuntimeError(err_msg)

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

        display_prompt = prompt.strip()
        worker_prompt = prompt.strip()

        # If internal_instruction was explicitly passed (e.g. from custom prompt), prepend it
        if internal_instruction and internal_instruction.strip():
            worker_prompt = f"{internal_instruction.strip()}\n\n{display_prompt}"

        # In the chat UI, show only the code selection if prompt is an automated selection bug fix prompt
        if ("Here is the code to fix:" in display_prompt or
            "Fix the bug in the following code." in display_prompt or
            "Review the provided code selection and fix any bugs that exist." in display_prompt):
            code_match = re.search(r'(```[\s\S]*?```)', display_prompt)
            if code_match:
                display_prompt = code_match.group(1).strip()

        # Stage 2 Diagnostic: Exact final prompt sent to AI
        p_first20 = worker_prompt[:20] if worker_prompt else ""
        p_last20 = worker_prompt[-20:] if len(worker_prompt or "") > 20 else worker_prompt or ""
        print("[AI_DIAGNOSTIC_STAGE_2] === EXACT FINAL PROMPT SENT TO AI ===")
        print(f"[AI_DIAGNOSTIC_STAGE_2] Length: {len(worker_prompt or '')}")
        print(f"[AI_DIAGNOSTIC_STAGE_2] First 20 chars: {repr(p_first20)}")
        print(f"[AI_DIAGNOSTIC_STAGE_2] Last 20 chars: {repr(p_last20)}")
        print(f"[AI_DIAGNOSTIC_STAGE_2] Full prompt (with whitespace visible): {repr(worker_prompt or '')}")

        # Emit user message for UI display - ONLY user visible prompt, NEVER internal instruction
        self.messageReceived.emit(f"user_{self.current_msg_id}", "user", display_prompt)
        self.statusChanged.emit("thinking")

        def on_chunk(chunk):
            self.statusChanged.emit("streaming")
            self.chunkReceived.emit(msg_id_str, chunk)

        def on_done(full_text):
            # Stage 3 Diagnostic: Complete raw AI response before parsing
            r_first20 = (full_text or "")[:20]
            r_last20 = (full_text or "")[-20:] if len(full_text or "") > 20 else (full_text or "")
            print("[AI_DIAGNOSTIC_STAGE_3] === COMPLETE RAW AI RESPONSE BEFORE PARSING ===")
            print(f"[AI_DIAGNOSTIC_STAGE_3] Length: {len(full_text or '')}")
            print(f"[AI_DIAGNOSTIC_STAGE_3] First 20 chars: {repr(r_first20)}")
            print(f"[AI_DIAGNOSTIC_STAGE_3] Last 20 chars: {repr(r_last20)}")
            print(f"[AI_DIAGNOSTIC_STAGE_3] Full raw response (with whitespace visible): {repr(full_text or '')}")

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
