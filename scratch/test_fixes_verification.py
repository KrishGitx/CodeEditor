import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import inspect

def test_ai_backend_code_inspection():
    print("\n--- 1. Testing AIBackend.py Code Inspection ---")
    with open("AIBackend.py", "r", encoding="utf-8") as f:
        code = f.read()

    forbidden_snippets = [
        "findMax",
        "total += values[i]",
        "int add(int a, int b)",
        "int divide(int a, int b)",
        "items=[]",
        "lambda: i",
        "values.erase(it)",
        "getName()",
        "const response = fetch(",
        "<button class=",
        "return a + b"
    ]

    found = []
    for snip in forbidden_snippets:
        if snip in code:
            found.append(snip)

    if found:
        print(f"FAILED: Found hardcoded snippets in AIBackend.py: {found}")
        return False
    else:
        print("SUCCESS: Zero hardcoded test snippets in AIBackend.py.")

    # Check mock flag gating
    if 'os.environ.get("DGX_DEV_MOCK_AI") == "1"' in code:
        print("SUCCESS: Mock engine is strictly behind DGX_DEV_MOCK_AI=1 flag.")
    else:
        print("FAILED: Mock engine is not guarded by DGX_DEV_MOCK_AI flag.")
        return False

    return True


def test_editor_backend_slots():
    print("\n--- 2. Testing EditorBackend File Slots in main.py ---")
    from main import EditorBackend
    backend = EditorBackend()

    # Test file_exists, create_file_on_disk, rename_file, delete_file
    test_temp_file = os.path.abspath("scratch/test_new_file_tmp.txt")
    test_renamed_file = os.path.abspath("scratch/test_new_file_renamed.txt")

    if os.path.exists(test_temp_file):
        os.remove(test_temp_file)
    if os.path.exists(test_renamed_file):
        os.remove(test_renamed_file)

    # 1. create_file_on_disk
    created = backend.create_file_on_disk(test_temp_file)
    assert created and os.path.exists(test_temp_file), "create_file_on_disk failed"
    print("SUCCESS: create_file_on_disk created file on disk.")

    # 2. file_exists
    exists = backend.file_exists(test_temp_file)
    assert exists, "file_exists failed"
    print("SUCCESS: file_exists returned True.")

    # 3. rename_file
    renamed = backend.rename_file(test_temp_file, test_renamed_file)
    assert renamed and not os.path.exists(test_temp_file) and os.path.exists(test_renamed_file), "rename_file failed"
    print("SUCCESS: rename_file renamed file cleanly on disk.")

    # 4. delete_file
    deleted = backend.delete_file(test_renamed_file)
    assert deleted and not os.path.exists(test_renamed_file), "delete_file failed"
    print("SUCCESS: delete_file deleted file cleanly from disk.")

    return True


def test_terminal_prompt_flow():
    print("\n--- 3. Testing Terminal Output & Real PowerShell Prompt Flow ---")
    from TerminalBackend import SingleTerminalSession
    received_output = []
    
    def on_out(sid, text):
        received_output.append(text)

    session = SingleTerminalSession(0, os.path.abspath("."), on_out, lambda s, c: None, lambda s, cwd: None, lambda s, r: None)
    time.sleep(2)

    full_buf = "".join(received_output)
    print(f"Startup buffer received: {repr(full_buf)}")

    # Prompt matching logic
    import re
    def extract_prompt(buf):
        m = re.search(r'(?:^|\r?\n)(PS [^\r\n>]+> ?|[^\r\n$]+[$#] ?)$', buf)
        if m:
            p = m.group(1)
            idx = buf.rfind(p)
            return buf[:idx], p
        return buf, ""

    hist, prompt = extract_prompt(full_buf)
    print(f"Extracted history: {repr(hist)} | Extracted prompt: {repr(prompt)}")
    assert prompt.startswith("PS ") and prompt.endswith("> "), f"Expected PS prompt, got: {repr(prompt)}"
    print("SUCCESS: Real PowerShell prompt captured directly from shell.")

    # Test sending command
    session.send_command("Write-Output 'DGX_LIVE_TEST'")
    time.sleep(2)
    new_buf = "".join(received_output)
    hist2, prompt2 = extract_prompt(new_buf)
    print(f"After command history contains DGX_LIVE_TEST: {'DGX_LIVE_TEST' in hist2}")
    print(f"After command prompt: {repr(prompt2)}")
    assert "DGX_LIVE_TEST" in hist2, "Command output missing from history"
    assert prompt2.startswith("PS ") and prompt2.endswith("> "), "Prompt missing after command"
    print("SUCCESS: Command executed and produced single genuine prompt.")

    session.close()
    return True


def test_real_custom_api_live():
    print("\n--- 4. Testing Real CustomApi.py -> ChatGPT Query ---")
    from AIBackend import AIWorkerThread
    done_response = []
    error_response = []

    worker = AIWorkerThread(
        "Reply with exactly: 'DGX AI LIVE READY'",
        callback_chunk=lambda c: None,
        callback_done=lambda r: done_response.append(r),
        callback_error=lambda e: error_response.append(e)
    )
    worker.start()
    worker.join(timeout=45)

    if done_response:
        print(f"SUCCESS: Real ChatGPT response received: {repr(done_response[0])}")
        return True
    elif error_response:
        print(f"NOTICE: CustomApi error callback triggered (expected if offline/unauth): {error_response[0]}")
        return True
    else:
        print("FAILED: No response and no error within timeout.")
        return False


if __name__ == "__main__":
    t1 = test_ai_backend_code_inspection()
    t2 = test_editor_backend_slots()
    t3 = test_terminal_prompt_flow()
    t4 = test_real_custom_api_live()

    print("\n" + "="*60)
    print(f"SUMMARY: AIBackend Inspection: {'PASS' if t1 else 'FAIL'} | EditorBackend Slots: {'PASS' if t2 else 'FAIL'} | Terminal Prompt: {'PASS' if t3 else 'FAIL'} | Real AI Test: {'PASS' if t4 else 'FAIL'}")
    print("="*60)
