import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_auth_dialog_closing_logic():
    print("=======================================================")
    print("TEST: ChatGPT Auth Dialog (#mobile-auth-dialog) Dismissal")
    print("=======================================================")

    # Test with real playwright headless browser by injecting mock #mobile-auth-dialog
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Create a mock ChatGPT page with #mobile-auth-dialog covering the #prompt-textarea
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { margin: 0; padding: 20px; font-family: sans-serif; background: #202123; color: white; }
                    #composer-container { position: relative; width: 600px; margin: 100px auto; }
                    #prompt-textarea { width: 100%; height: 60px; padding: 10px; background: #40414f; color: white; border: 1px solid #565869; }
                    #mobile-auth-dialog {
                        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                        background: rgba(0,0,0,0.7); display: flex; justify-content: center; align-items: center;
                        z-index: 9999;
                    }
                    .modal-card { background: #2d2d39; padding: 30px; border-radius: 8px; position: relative; width: 350px; text-align: center; }
                    .close-btn { position: absolute; top: 10px; right: 10px; background: transparent; border: none; color: white; font-size: 20px; cursor: pointer; }
                </style>
            </head>
            <body>
                <div id="composer-container">
                    <textarea id="prompt-textarea" placeholder="Message ChatGPT..."></textarea>
                </div>
                <div id="mobile-auth-dialog">
                    <div class="modal-card">
                        <button class="close-btn" aria-label="Close">✕</button>
                        <h2>Log in or Sign up</h2>
                        <p>Get smarter responses, upload files and images, and more.</p>
                        <button id="login-btn">Log in</button>
                    </div>
                </div>
                <script>
                    document.querySelector('.close-btn').addEventListener('click', function() {
                        document.getElementById('mobile-auth-dialog').style.display = 'none';
                    });
                </script>
            </body>
            </html>
            """
            page.set_content(html_content)

            # Define dismiss_modals and get_active_textbox exactly as in CustomApi.py
            def dismiss_modals(p_obj):
                if not p_obj or p_obj.is_closed():
                    return
                try:
                    dialog = p_obj.locator('#mobile-auth-dialog, [data-testid="auth-dialog"]').first
                    if dialog.count() > 0 and dialog.is_visible():
                        close_btn = dialog.locator('button[aria-label="Close"], button[aria-label="close"]').first
                        if close_btn.count() > 0 and close_btn.is_visible():
                            print("[Test] Detected #mobile-auth-dialog. Clicking button[aria-label='Close']...")
                            close_btn.click(timeout=1500)
                        else:
                            close_btn_alt = p_obj.locator('#mobile-auth-dialog button[aria-label="Close"], #mobile-auth-dialog [aria-label="Close"]').first
                            if close_btn_alt.count() > 0 and close_btn_alt.is_visible():
                                print("[Test] Clicking alternative close selector...")
                                close_btn_alt.click(timeout=1500)
                        try:
                            dialog.wait_for(state="hidden", timeout=2500)
                            print("[Test] Dialog successfully hidden/closed.")
                        except Exception as wait_err:
                            print("[Test] Wait for hidden notice:", wait_err)
                        time.sleep(0.2)
                except Exception as e:
                    print("[Test] Dismiss modals notice:", e)

            def is_auth_dialog_blocking(p_obj):
                if not p_obj or p_obj.is_closed():
                    return False
                try:
                    dialog = p_obj.locator('#mobile-auth-dialog, [data-testid="auth-dialog"]').first
                    if dialog.count() > 0 and dialog.is_visible():
                        return True
                except Exception:
                    pass
                return False

            def get_active_textbox(p_obj):
                dismiss_modals(p_obj)
                if is_auth_dialog_blocking(p_obj):
                    return None
                selectors = ['#prompt-textarea', 'textarea']
                for sel in selectors:
                    try:
                        loc = p_obj.locator(sel).first
                        if loc.count() > 0 and loc.is_visible():
                            return loc
                    except Exception:
                        continue
                return None

            # Verify dialog is initially blocking
            assert is_auth_dialog_blocking(page) == True, "Auth dialog should initially be blocking"
            print("[PASS] Initial state: #mobile-auth-dialog is blocking the page.")

            # Run dismiss_modals
            dismiss_modals(page)

            # Verify dialog is now closed and not blocking
            assert is_auth_dialog_blocking(page) == False, "Auth dialog should be closed"
            print("[PASS] Post-dismissal: #mobile-auth-dialog is no longer visible.")

            # Locate textbox
            textbox = get_active_textbox(page)
            assert textbox is not None, "Textbox should be found and interactable"
            print("[PASS] Composer textarea #prompt-textarea found.")

            # Interact with textbox without pointer event interception
            textbox.click(timeout=3000)
            textbox.fill("Test prompt from DGX Studio")
            print(f"[PASS] Textbox clicked and filled successfully: '{textbox.input_value()}'")
            assert textbox.input_value() == "Test prompt from DGX Studio"

            browser.close()

        print("\n>>> ALL AUTH DIALOG HANDLING TESTS PASSED (100%)! <<<")
        return True
    except Exception as e:
        print("[FAIL] Test error:", e)
        return False

if __name__ == "__main__":
    success = test_auth_dialog_closing_logic()
    if not success:
        sys.exit(1)
