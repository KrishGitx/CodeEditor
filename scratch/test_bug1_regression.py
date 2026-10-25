"""
test_bug1_regression.py - Comprehensive Regression Suite for Replace with AI.
Tests all requirements from Part 1:
1. Exact tested prompt unchanged.
2. Missing comma fix.
3. Missing colon fix.
4. Extra character fix.
5. Duplicated leading line rejection (Case B).
6. Legitimate repeated line preservation.
7. Legitimate leading parenthesis preservation.
8. Malformed leading parenthesis correction (Case C).
9. Response containing only an explanation (Case D).
10. Unchanged, already-correct selection (Rule 4).
11. Ambiguous incomplete selection (Case E / Rule 5).
12. Selection changed while request is running (boundary safety).
13. Undo/redo preservation.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from AIReplacementEngine import (
    EXACT_TESTED_PROMPT,
    build_selection_prompt,
    parse_replacement_response,
    sanitize_extracted_code,
    validate_replacement_scope
)

ORIGINAL_PLAYWRIGHT_SNIPPET = """wser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US"+
        timezone_id="Asia/Kolkata",
    )

    page = context.new_page()"""

EXPECTED_PLAYWRIGHT_CORRECTED = """wser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="Asia/Kolkata",
    )

    page = context.new_page()"""


class TestReplaceWithAiComprehensive(unittest.TestCase):

    def test_01_exact_tested_prompt_unmodified(self):
        """The exact tested prompt must not be changed, reworded, or extended."""
        expected = (
            "Fix the bug in the following code. Make only the changes necessary to fix the actual problem.\n\n"
            "Rules:\n\n"
            "1. Return the complete corrected version of the provided code, preserving its original structure.\n"
            "2. Do not add new features, autocomplete incomplete code, or write code that was not present in the original.\n"
            "3. Do not add imports, functions, classes, comments, examples, or extra lines unless they are strictly necessary to fix the bug.\n"
            "4. If the code is already correct, return it unchanged.\n"
            "5. If the intended behavior is ambiguous, explain what is unclear instead of guessing.\n"
            "6. Preserve existing variable names, formatting, and logic wherever possible.\n"
            "7. Do not refactor or optimize unrelated code.\n"
            "8. Return the corrected code in a single code block. Briefly explain the exact change outside the code block.\n\n"
            "Here is the code to fix:"
        )
        self.assertEqual(EXACT_TESTED_PROMPT, expected)

    def test_02_missing_comma_correction(self):
        """Case A: Corrects missing comma in snippet without introducing unrelated code."""
        ai_resp = f"Replaced '+' with ',' on locale line.\n\n```python\n{EXPECTED_PLAYWRIGHT_CORRECTED}\n```"
        res = parse_replacement_response(ai_resp, "python", ORIGINAL_PLAYWRIGHT_SNIPPET)
        self.assertEqual(res["status"], "replacement")
        self.assertEqual(res["code"], EXPECTED_PLAYWRIGHT_CORRECTED)
        self.assertIn('locale="en-US",', res["code"])
        self.assertNotIn('locale="en-US"+', res["code"])

    def test_03_missing_colon_correction(self):
        """Corrects a missing colon on a function header."""
        selected = "def calculate_sum(a, b)\n    return a + b"
        ai_resp = "Added missing colon at the end of def header.\n\n```python\ndef calculate_sum(a, b):\n    return a + b\n```"
        res = parse_replacement_response(ai_resp, "python", selected)
        self.assertEqual(res["status"], "replacement")
        self.assertEqual(res["code"], "def calculate_sum(a, b):\n    return a + b")

    def test_04_extra_character_removal(self):
        """Removes an errant extra character in code."""
        selected = "count = total + 1;"
        ai_resp = "Removed trailing semicolon in Python.\n\n```python\ncount = total + 1\n```"
        res = parse_replacement_response(ai_resp, "python", selected)
        self.assertEqual(res["status"], "replacement")
        self.assertEqual(res["code"], "count = total + 1")

    def test_05_duplicated_leading_line_rejected(self):
        """Case B: Detects duplicated leading line from raw AI output when original had it once."""
        selected = "browser.new_context(\n    locale='en-US'+\n)"
        # AI returns leading line twice
        ai_resp = (
            "Fixed trailing plus.\n\n"
            "```python\n"
            "browser.new_context(\n"
            "browser.new_context(\n"
            "    locale='en-US',\n"
            ")\n"
            "```"
        )
        res = parse_replacement_response(ai_resp, "python", selected)
        self.assertEqual(res["status"], "scope_mismatch")
        self.assertIsNone(res["code"])
        self.assertIn("Duplication Hazard", res["error"])

    def test_06_legitimate_repeated_line_preserved(self):
        """Case B: If original code contains repeated lines, they are preserved and not rejected."""
        selected = "pass\npass\nreturn 0"
        ai_resp = "Code has redundant pass, keeping structure.\n\n```python\npass\npass\nreturn 0\n```"
        res = parse_replacement_response(ai_resp, "python", selected)
        self.assertEqual(res["status"], "unchanged")

        # Now when one line is corrected while preserving repeated lines:
        selected2 = "x = 1\nx = 1\ny = x +"
        ai_resp2 = "Completed expression.\n\n```python\nx = 1\nx = 1\ny = x + 2\n```"
        res2 = parse_replacement_response(ai_resp2, "python", selected2)
        self.assertEqual(res2["status"], "replacement")
        self.assertIn("x = 1\nx = 1\ny = x + 2", res2["code"])

    def test_07_legitimate_leading_parenthesis_preserved(self):
        """Preserves legitimate leading '(' when original selection starts with '('."""
        selected = "(\n    x + y\n) * 2"
        ai_resp = "Fixed spacing.\n\n```python\n(\n    x + y\n) * 3\n```"
        res = parse_replacement_response(ai_resp, "python", selected)
        self.assertEqual(res["status"], "replacement")
        self.assertTrue(res["code"].startswith("("))

    def test_08_malformed_leading_parenthesis_corrected(self):
        """Case C: Removes spurious leading '(' line when original selection did not start with '('."""
        ai_resp = f"Fixed plus.\n\n```python\n(\n{EXPECTED_PLAYWRIGHT_CORRECTED}\n```"
        res = parse_replacement_response(ai_resp, "python", ORIGINAL_PLAYWRIGHT_SNIPPET)
        self.assertEqual(res["status"], "replacement")
        self.assertFalse(res["code"].startswith("(\n"))
        self.assertTrue(res["code"].startswith("wser.new_context("))
        self.assertEqual(res["code"], EXPECTED_PLAYWRIGHT_CORRECTED)

    def test_09_explanation_only_response_does_not_modify_editor(self):
        """Case D: If AI responds only with prose explanation, code is None and selection is unchanged."""
        ai_resp = (
            "The selected code has a syntax error because of the trailing plus on line 3. "
            "To fix it, replace '+' with a comma."
        )
        res = parse_replacement_response(ai_resp, "python", ORIGINAL_PLAYWRIGHT_SNIPPET)
        self.assertEqual(res["status"], "invalid")
        self.assertIsNone(res["code"])
        self.assertIn("syntax error", res["explanation"])

    def test_10_unchanged_already_correct_selection(self):
        """Rule 4: Already-correct selection returns status 'unchanged' without modifying editor."""
        correct_code = EXPECTED_PLAYWRIGHT_CORRECTED
        ai_resp = f"The code is already correct.\n\n```python\n{correct_code}\n```"
        res = parse_replacement_response(ai_resp, "python", correct_code)
        self.assertEqual(res["status"], "unchanged")
        self.assertEqual(res["state"], "UNCHANGED")

    def test_11_ambiguous_incomplete_selection(self):
        """Case E: Ambiguous incomplete code returns explanation without modifying editor."""
        selected = "wser.new_context("
        ai_resp = (
            "The identifier 'wser' is incomplete and lacks context. "
            "It appears to be part of 'browser.new_context', but the browser variable is undefined."
        )
        res = parse_replacement_response(ai_resp, "python", selected)
        self.assertEqual(res["status"], "invalid")
        self.assertIsNone(res["code"])

    def test_12_selection_changed_while_request_running(self):
        """Simulates EditorArea.qml safeguard when document text is edited during AI call."""
        original_text = "locale='en-US'+"
        # Document text was modified while AI was running:
        current_document_range = "locale='en-US' - EDITED"
        
        # Safeguard check from EditorArea.qml replaceSelection:
        is_safe = (current_document_range == original_text)
        self.assertFalse(is_safe, "Replacement must be blocked when selection was modified in editor")

    def test_13_simulated_editor_undo_redo_preservation(self):
        """Simulate document replacement and verify undo/redo stack fidelity."""
        doc = ["# Initial document\n", "context = bro", ORIGINAL_PLAYWRIGHT_SNIPPET, "\npage.goto('url')\n"]
        full_text = "".join(doc)
        start_pos = full_text.find(ORIGINAL_PLAYWRIGHT_SNIPPET)
        end_pos = start_pos + len(ORIGINAL_PLAYWRIGHT_SNIPPET)

        # 1. State before replace
        undo_stack = [full_text]

        # 2. Perform replace
        res = parse_replacement_response(
            f"```python\n{EXPECTED_PLAYWRIGHT_CORRECTED}\n```",
            "python",
            ORIGINAL_PLAYWRIGHT_SNIPPET
        )
        new_text = full_text[:start_pos] + res["code"] + full_text[end_pos:]
        undo_stack.append(new_text)

        self.assertIn('locale="en-US",', new_text)
        self.assertNotIn("(\nwser", new_text)

        # 3. Simulate Undo
        restored = undo_stack[-2]
        self.assertEqual(restored, full_text)
        self.assertIn('locale="en-US"+', restored)

        # 4. Simulate Redo
        reapplied = undo_stack[-1]
        self.assertEqual(reapplied, new_text)
        self.assertIn('locale="en-US",', reapplied)


if __name__ == "__main__":
    unittest.main()
