import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time

def test_selection_ai_live():
    print("\n--- Testing Live Selection AI Request via CustomApi ---")
    from AIBackend import AIWorkerThread
    
    code_snippet = """def calculate_total(prices):
    total = 0
    for p in prices:
        total += p
    return total"""

    prompt = f"""Review the following selected code:
```python
{code_snippet}
```
If the code is already correct and optimal, answer with [NO_CHANGE]. If it needs improvement or replacement, provide the updated code within [REPLACEMENT_CODE]."""

    done_text = []
    error_text = []

    worker = AIWorkerThread(
        prompt,
        callback_chunk=lambda c: None,
        callback_done=lambda r: done_text.append(r),
        callback_error=lambda e: error_text.append(e)
    )
    worker.start()
    worker.join(timeout=60)

    if done_text:
        resp = done_text[0]
        print("SUCCESS: Live AI Response received:")
        print("-" * 50)
        print(resp[:400])
        print("-" * 50)
        return True
    else:
        print(f"FAILED: No response received. Error: {error_text}")
        return False

if __name__ == "__main__":
    test_selection_ai_live()
