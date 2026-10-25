import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from AIReplacementEngine import (
    EXACT_TESTED_PROMPT,
    build_selection_prompt,
    parse_replacement_response,
    validate_replacement_scope
)

EXPECTED_PROMPT_TEXT = """Fix the bug in the following code. Make only the changes necessary to fix the actual problem.

Rules:

1. Return the complete corrected version of the provided code, preserving its original structure.
2. Do not add new features, autocomplete incomplete code, or write code that was not present in the original.
3. Do not add imports, functions, classes, comments, examples, or extra lines unless they are strictly necessary to fix the bug.
4. If the code is already correct, return it unchanged.
5. If the intended behavior is ambiguous, explain what is unclear instead of guessing.
6. Preserve existing variable names, formatting, and logic wherever possible.
7. Do not refactor or optimize unrelated code.
8. Return the corrected code in a single code block. Briefly explain the exact change outside the code block.

Here is the code to fix:"""

class TestReplaceWithAiExactPrompt(unittest.TestCase):

    def test_01_exact_prompt_string_matches(self):
        """Prompt constant must match user's exact tested prompt without alterations."""
        self.assertEqual(EXACT_TESTED_PROMPT.strip(), EXPECTED_PROMPT_TEXT.strip())

    def test_02_build_selection_prompt_structure(self):
        """Prompt construction appends selected code in a code block and has no internal instruction."""
        code = "def calculate_total(a, b):\n    return a - b"
        user_prompt, internal_instr = build_selection_prompt(code, "python")
        self.assertTrue(user_prompt.startswith(EXPECTED_PROMPT_TEXT))
        self.assertIn("```python\n" + code + "\n```", user_prompt)
        self.assertEqual(internal_instr, "")

    def test_03_parse_single_code_block_with_explanation(self):
        """AI response containing a single code block and explanation outside is parsed correctly."""
        selected_code = "def calculate_total(a, b)\n    return a + b"
        ai_response = (
            "I fixed the missing colon on the function definition header.\n\n"
            "```python\n"
            "def calculate_total(a, b):\n"
            "    return a + b\n"
            "```"
        )
        res = parse_replacement_response(ai_response, "python", selected_code)
        self.assertEqual(res["status"], "replacement")
        self.assertEqual(res["code"], "def calculate_total(a, b):\n    return a + b")
        self.assertIn("colon", res["explanation"])
        self.assertNotIn("colon", res["code"])

    def test_04_unchanged_code_detected(self):
        """Rule 4: If code is already correct, return unchanged without inventing a replacement."""
        selected_code = "def calculate_total(a, b):\n    return a + b"
        ai_response = (
            "The code is already correct and has no syntax or logic errors.\n\n"
            "```python\n"
            "def calculate_total(a, b):\n"
            "    return a + b\n"
            "```"
        )
        res = parse_replacement_response(ai_response, "python", selected_code)
        self.assertEqual(res["status"], "unchanged")
        self.assertEqual(res["state"], "UNCHANGED")

    def test_05_explanation_after_code_block(self):
        """Parses correctly when explanation is after the code block."""
        selected_code = "def calculate_total(a, b):\n    return a - b"
        ai_response = (
            "```python\n"
            "def calculate_total(a, b):\n"
            "    return a + b\n"
            "```\n\n"
            "Changed subtraction operator to addition to calculate total."
        )
        res = parse_replacement_response(ai_response, "python", selected_code)
        self.assertEqual(res["status"], "replacement")
        self.assertEqual(res["code"], "def calculate_total(a, b):\n    return a + b")
        self.assertIn("addition", res["explanation"])

    def test_06_scope_expansion_blocked(self):
        """Blocks full file or outer wrapper expansion on partial selection."""
        selected_code = "calculate_total(a, b)"
        ai_response = (
            "Here is the full program:\n\n"
            "```python\n"
            "import os\n"
            "import sys\n\n"
            "def calculate_total(a, b):\n"
            "    return a + b\n\n"
            "if __name__ == '__main__':\n"
            "    print(calculate_total(1, 2))\n"
            "```"
        )
        res = parse_replacement_response(ai_response, "python", selected_code)
        self.assertEqual(res["status"], "scope_mismatch")
        self.assertIsNone(res["code"])

if __name__ == "__main__":
    unittest.main()
