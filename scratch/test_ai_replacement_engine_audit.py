import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AIReplacementEngine import (
    build_selection_prompt,
    build_selection_internal_instruction,
    parse_replacement_response,
    validate_replacement_scope,
    MANDATORY_SCOPE_INSTRUCTIONS,
    SELECTION_BUG_FIX_PROMPT
)


class TestAIReplacementEngineAudit(unittest.TestCase):
    # 23. Correct code remains unchanged (SUCCESS marker handling)
    def test_23_correct_code_remains_unchanged(self):
        resp = "SUCCESS"
        result = parse_replacement_response(resp, "python", "def add(a, b):\n    return a + b\n")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["state"], "SUCCESS")
        self.assertIsNone(result["code"])

    # 24. Syntax errors receive minimal corrections
    def test_24_syntax_error_minimal_correction(self):
        orig = "def calculate_total(a, b)\n    return a + b"
        ai_resp = (
            "Fixed missing colon on the function definition header.\n\n"
            "[Fixed Code]\n"
            "```python\n"
            "def calculate_total(a, b):\n"
            "    return a + b\n"
            "```"
        )
        result = parse_replacement_response(ai_resp, "python", orig)
        self.assertEqual(result["status"], "replacement")
        self.assertEqual(result["state"], "FIXED_CODE")
        self.assertEqual(result["code"].strip(), "def calculate_total(a, b):\n    return a + b")

    # 25. Identifiable logic errors receive minimal corrections
    def test_25_logic_error_minimal_correction(self):
        orig = "def calculate_total(a, b):\n    return a - b"
        ai_resp = (
            "The function was subtracting instead of adding total.\n\n"
            "[Fixed Code]\n"
            "```python\n"
            "def calculate_total(a, b):\n"
            "    return a + b\n"
            "```"
        )
        result = parse_replacement_response(ai_resp, "python", orig)
        self.assertEqual(result["status"], "replacement")
        self.assertEqual(result["code"].strip(), "def calculate_total(a, b):\n    return a + b")

    # 26. Incomplete code is not autocompleted
    def test_26_incomplete_code_not_autocompleted(self):
        orig = "def calculate_total(a, b):\n    return"
        # Prompt explicitly mandates returning SUCCESS or not inventing code for incomplete valid code
        user_prompt, internal_instr = build_selection_prompt(orig, "python")
        self.assertIn("Do NOT autocomplete incomplete code or fragments", internal_instr)
        self.assertIn("Do not autocomplete incomplete code or fragments", internal_instr)

        # If AI correctly returns SUCCESS for incomplete code without hallucinating
        result = parse_replacement_response("SUCCESS", "python", orig)
        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["code"])

    # 27. Custom prompts retain mandatory scope restrictions
    def test_27_custom_prompt_retains_mandatory_scope_rules(self):
        custom = "Please rename variable x to count"
        user_prompt, internal_instr = build_selection_prompt("x = 10", "python", custom_prompt=custom)
        # Verify user prompt has user request and code
        self.assertIn("Please rename variable x to count", user_prompt)
        self.assertIn("```python\nx = 10\n```", user_prompt)
        # Verify internal instruction strictly includes mandatory scope rules
        self.assertIn("MANDATORY SCOPE AND SELECTION PRESERVATION RULES", internal_instr)
        self.assertIn("The selected code defines the strict replacement boundary", internal_instr)
        self.assertIn("Do NOT autocomplete incomplete code or fragments", internal_instr)
        self.assertIn("Do NOT expand the selection into a full file or application", internal_instr)

    # 28. Unselected code remains unchanged (outer wrapper injection blocked)
    def test_28_unselected_outer_wrapper_blocked(self):
        orig = "page.goto('https://example.com')"
        repl = (
            "with sync_playwright() as p:\n"
            "    browser = p.chromium.launch()\n"
            "    page = browser.new_page()\n"
            "    page.goto('https://example.com')\n"
            "    browser.close()"
        )
        valid, reason = validate_replacement_scope(repl, orig)
        self.assertFalse(valid)
        self.assertIn("Scope Hazard", reason)

    # 29. Malformed responses are rejected safely
    def test_29_malformed_responses_rejected(self):
        res1 = parse_replacement_response("", "python", "x = 1")
        self.assertEqual(res1["status"], "invalid")

        res2 = parse_replacement_response("I think you should change this code to be better.", "python", "x = 1")
        self.assertEqual(res2["status"], "invalid")

    # 30. Stale response or destructive truncation rejected
    def test_30_destructive_truncation_rejected(self):
        large_selection = "\n".join([f"    line_{i} = {i}" for i in range(12)])
        tiny_repl = "    pass"
        valid, reason = validate_replacement_scope(tiny_repl, large_selection)
        self.assertFalse(valid)
        self.assertIn("Scope Hazard", reason)


if __name__ == "__main__":
    unittest.main()
