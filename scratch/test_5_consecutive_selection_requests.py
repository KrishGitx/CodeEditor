import sys
import os
import time

sys.path.insert(0, r"c:\Users\amazi\OneDrive\Documents\DGX")
os.environ["PYTHONIOENCODING"] = "utf-8"

from AIBackend import AIBackend, AIWorkerThread, clean_ai_text

INTERNAL_INSTRUCTION = (
    "You are Pod Studio AI analyzing a user's selected code snippet.\n"
    "You MUST classify your review into one of the following 3 STRICT PROTOCOL STATES and include the exact state marker in your response:\n\n"
    "1. [REPLACEMENT_CODE]\n"
    "Include `[REPLACEMENT_CODE]` followed by a single fenced code block containing ONLY the corrected replacement for the selected range whenever a safe, unambiguous local fix exists inside the selected text (e.g. missing semicolon, operator fix, logic fix, typo, closure binding, or fragment fix like `++count;`). The replacement must match the exact selection scope.\n\n"
    "2. [NO_CHANGE]\n"
    "Include `[NO_CHANGE]` and explain why no changes are needed whenever the selected code has no bug and is already correct.\n\n"
    "3. [INSUFFICIENT_CONTEXT]\n"
    "Include `[INSUFFICIENT_CONTEXT]` and explain what external context is needed whenever the real bug or fix depends on code outside the selected range (e.g. surrounding loop boundary, missing variable declaration/type).\n\n"
    "Always explain your reasoning in clear text. Always include exactly one of the markers: [REPLACEMENT_CODE], [NO_CHANGE], or [INSUFFICIENT_CONTEXT]."
)

def test_consecutive_requests():
    print("=" * 70)
    print("TESTING 5+ CONSECUTIVE SELECTION-AI REQUESTS")
    print("=" * 70)

    requests = [
        ("Req 1: C++ Syntax", "Please review and improve the selected cpp code:\n\n```cpp\nint result = a + b\n```"),
        ("Req 2: C++ Incomplete Fragment", "Please review and improve the selected cpp code:\n\n```cpp\n++count\n```"),
        ("Req 3: Python Logic", "Please review and improve the selected python code:\n\n```python\ndef add_item(item, items=[]):\n    items.append(item)\n    return items\n```"),
        ("Req 4: C++ Logic", "Please review and improve the selected cpp code:\n\n```cpp\nint findMax(const vector<int>& nums) {\n    int best = nums[0];\n    for (int i = 1; i < nums.size(); ++i) {\n        if (nums[i] < best) best = nums[i];\n    }\n    return best;\n}\n```"),
        ("Req 5: C++ No Change", "Please review and improve the selected cpp code:\n\n```cpp\nint add(int a, int b) {\n    return a + b;\n}\n```"),
        ("Req 6: JS Missing Await", "Please review and improve the selected javascript code:\n\n```javascript\nconst response = fetch(\"/api/user\");\n```")
    ]

    for label, prompt in requests:
        print(f"\nDispatching {label}...")
        full_prompt = f"{INTERNAL_INSTRUCTION}\n\n{prompt}"
        done_resp = []
        worker = AIWorkerThread(
            full_prompt,
            lambda c: None,
            lambda d: done_resp.append(d),
            lambda e: print(f"Error in {label}: {e}")
        )
        worker.run()
        assert len(done_resp) > 0, f"No response for {label}"
        resp = done_resp[0]
        assert len(resp.strip()) > 0, f"Response was empty for {label}"
        has_protocol = any(m in resp for m in ["[REPLACEMENT_CODE]", "[NO_CHANGE]", "[INSUFFICIENT_CONTEXT]"])
        assert has_protocol, f"Response missing protocol marker for {label}:\n{resp}"
        print(f"[PASS] {label}: Non-empty response with valid protocol ({len(resp)} chars)")

    print("\n" + "=" * 70)
    print("ALL 6 CONSECUTIVE REQUESTS COMPLETED SUCCESSFULLY (100% PASS)")
    print("=" * 70)

if __name__ == "__main__":
    test_consecutive_requests()
