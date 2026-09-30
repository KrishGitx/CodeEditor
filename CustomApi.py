"""
CustomApi.py - Playwright-powered ChatGPT API Bridge for DGX Studio AI Assistant
Uses a single dedicated background thread to guarantee Playwright thread affinity across all turns.
"""

import sys
import os
import time
import threading
import queue


class ChatGPTClient:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ChatGPTClient, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, headless=True):
        if self._initialized:
            return
        self.headless = headless
        self._task_queue = queue.Queue()
        self.is_connected = False
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        self._initialized = True

    def _worker_loop(self):
        """Dedicated background thread managing Playwright instance for 100% thread affinity."""
        playwright = None
        browser = None
        context = None
        page = None

        def init_browser():
            nonlocal playwright, browser, context, page
            try:
                from playwright.sync_api import sync_playwright
                playwright = sync_playwright().start()
                browser = playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox"
                    ]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                    timezone_id="Asia/Kolkata"
                )
                page = context.new_page()
                page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=45000)
                time.sleep(1.5)
                dismiss_modals(page)
                self.is_connected = True
                print("[CustomApi] Successfully connected to ChatGPT service.")
                return True
            except Exception as e:
                print(f"[CustomApi] Playwright connection error in worker thread: {e}")
                self.is_connected = False
                return False

        def dismiss_modals(p):
            if not p or p.is_closed():
                return
            try:
                stay_logged_out = p.locator('a[href="#"], button', has_text="Stay logged out")
                if stay_logged_out.count() > 0:
                    stay_logged_out.first.click(timeout=1500)
            except Exception:
                pass

        def get_active_textbox(p):
            dismiss_modals(p)
            selectors = [
                '#prompt-textarea',
                'div[contenteditable="true"]',
                'textarea[placeholder*="Message"]',
                'textarea[data-id="root"]',
                'textarea',
                '[data-placeholder]'
            ]
            for sel in selectors:
                try:
                    loc = p.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        return loc
                except Exception:
                    continue
            try:
                return p.get_by_role("textbox").first
            except Exception:
                return None

        # Main task loop on dedicated thread
        while True:
            task = self._task_queue.get()
            if task is None:
                break

            action, args, result_holder, done_event = task
            try:
                if action == "connect":
                    if not self.is_connected or not page or page.is_closed():
                        init_browser()
                    result_holder["success"] = self.is_connected

                elif action == "ask":
                    prompt = args.get("prompt", "")
                    chunk_callback = args.get("chunk_callback", None)

                    if not self.is_connected or not page or page.is_closed():
                        if not init_browser():
                            raise RuntimeError("Could not establish connection with ChatGPT service.")

                    dismiss_modals(page)

                    # Locate active textbox
                    textbox = None
                    for _ in range(25):
                        textbox = get_active_textbox(page)
                        if textbox:
                            break
                        time.sleep(0.3)

                    if not textbox:
                        raise RuntimeError("Chat input textbox not found or busy.")

                    # Enter prompt
                    textbox.click()
                    textbox.fill(prompt)
                    time.sleep(0.2)
                    textbox.press("Enter")

                    try:
                        send_btn = page.locator('button[data-testid="send-button"], button[aria-label="Send prompt"]').first
                        if send_btn.count() > 0 and send_btn.is_enabled():
                            send_btn.click()
                    except Exception:
                        pass

                    # Stream response
                    stable_cycles = 0
                    previous = ""
                    last_reported_len = 0
                    full_response = ""

                    for _ in range(150):  # up to 45 seconds polling
                        time.sleep(0.3)
                        dismiss_modals(page)

                        messages = page.locator('[data-message-role="assistant"], [data-message-author-role="assistant"]')
                        count = messages.count()
                        if count <= 0:
                            continue

                        res = messages.nth(count - 1)
                        current = ""
                        try:
                            md = res.locator(".markdown, [data-assistant-markdown]").first
                            if md.count() > 0:
                                current = md.inner_text()
                            else:
                                current = res.inner_text()
                        except Exception:
                            try:
                                current = res.inner_text()
                            except Exception:
                                current = ""

                        if current:
                            if len(current) > last_reported_len and chunk_callback:
                                chunk = current[last_reported_len:]
                                chunk_callback(chunk)
                                last_reported_len = len(current)

                            if current == previous and len(current) > 0:
                                stable_cycles += 1
                            else:
                                stable_cycles = 0

                            stop_btn = page.locator('button[data-testid="stop-button"], button[aria-label="Stop generating"]')
                            is_generating = stop_btn.count() > 0 and stop_btn.first.is_visible()

                            if not is_generating and stable_cycles >= 4:
                                full_response = current
                                break

                            previous = current

                    result_holder["response"] = full_response or previous

            except Exception as e:
                print(f"[CustomApi] Error during prompt execution: {e}")
                result_holder["error"] = str(e)
            finally:
                done_event.set()
                self._task_queue.task_done()

        # Cleanup on shutdown
        try:
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
        except Exception:
            pass

    def connect(self):
        result_holder = {}
        done_event = threading.Event()
        self._task_queue.put(("connect", {}, result_holder, done_event))
        done_event.wait(timeout=50.0)
        return result_holder.get("success", False)

    def ask(self, prompt, chunk_callback=None):
        result_holder = {}
        done_event = threading.Event()
        self._task_queue.put(("ask", {"prompt": prompt, "chunk_callback": chunk_callback}, result_holder, done_event))
        done_event.wait(timeout=60.0)

        if "error" in result_holder:
            raise RuntimeError(result_holder["error"])

        return result_holder.get("response", "")

    def close(self):
        self._task_queue.put(None)
        self.is_connected = False


if __name__ == "__main__":
    client = ChatGPTClient(headless=False)
    if client.connect():
        while True:
            msg = input("\nEnter prompt (or 'exit'): ")
            if msg.lower() == "exit":
                break
            print("\nResponse: ", end="", flush=True)
            res = client.ask(msg, chunk_callback=lambda c: print(c, end="", flush=True))
            print()
    client.close()