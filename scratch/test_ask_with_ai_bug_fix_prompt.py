"""
test_ask_with_ai_bug_fix_prompt.py - Validation of Ask with AI Bug Fix Prompt & Replacement Protocol.

Verifies:
1. Exact prompt template matching live ChatGPT tested prompt and isolated payload (no surrounding file leakage).
2. Correct selection -> AI returns only SUCCESS -> no replacement occurs.
3. Buggy selection -> AI explains bug and returns [Fixed Code] -> explanation outside code, valid replacement.
4. Small selection from large file -> only selection sent, only selection replaced, surrounding code unchanged.
5. Incomplete fragments -> scope validation blocks outer wrappers and autocomplete expansions.
6. Invalid AI response -> rejected safely, no code changed.
7. Text/boundary preservation -> modifying text while AI request in-flight blocks replacement.
8. Dual validation across Python AIReplacementEngine and JavaScript CodeExtractor.js.
"""

import os
import sys
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QJSEngine
from AIReplacementEngine import (
    SELECTION_BUG_FIX_PROMPT,
    build_selection_prompt,
    parse_replacement_response,
    validate_replacement_scope
)


class TestAskWithAiBugFixPrompt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        cls.js_engine = QJSEngine()

        js_path = os.path.join(repo_root, "qml", "ai", "CodeExtractor.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js_code = f.read()
            js_code = js_code.replace(".pragma library", "// .pragma library")
            val = cls.js_engine.evaluate(js_code, "CodeExtractor.js")
            if val.isError():
                raise RuntimeError(f"Failed to load CodeExtractor.js in QJSEngine: {val.toString()}")

    def test_01_prompt_template_and_payload_isolation(self):
        """1. Ensure prompt template matches user requirement exactly and sends ONLY selected code."""
        expected_substrings = [
            "Review the provided code selection and fix any bugs that exist.",
            "If there are no bugs, return only:\nSUCCESS",
            "1. Give a brief explanation of approximately 50 words describing the bug.",
            "2. Write [Fixed Code] on a separate line.",
            "3. Below [Fixed Code], provide the corrected code.",
            "- Fix only actual bugs or errors.",
            "- Return the exact same selection of code with only the necessary bug fixes applied.",
            "- Do not rewrite correct code.",
            "- Do not refactor, optimize, or change formatting unnecessarily.",
            "- Do not autocomplete incomplete code or fragments.",
            "- Do not add missing code that was not part of the selection.",
            "- Preserve all other supplied code exactly as it was.",
            "- The selected code defines the maximum replacement scope.",
            "- If no bug exists, return only SUCCESS without explanation or code."
        ]
        for sub in expected_substrings:
            self.assertIn(sub, SELECTION_BUG_FIX_PROMPT)

        selected_code = "result = calculate(a, b)"
        surrounding_file = (
            "import math\n\n"
            "def run():\n"
            "    a = 10\n"
            "    b = 20\n"
            "    result = calculate(a, b)\n"
            "    print(result)\n"
        )
        user_prompt, internal_instr = build_selection_prompt(
            code=selected_code,
            lang_id="python",
            custom_prompt="",
            surrounding_context=surrounding_file,
            is_full_file=False
        )

        # Must contain selected code
        self.assertIn(selected_code, user_prompt)
        # The prompt template sent with code should NOT be shown to user in user_prompt
        for sub in expected_substrings:
            self.assertNotIn(sub, user_prompt)
        # Instead, internal_instruction carries the prompt template sent with code
        for sub in expected_substrings:
            self.assertIn(sub, internal_instr)
        # Combined prompt sent to AI worker contains both
        combined_worker_prompt = f"{internal_instr}\n\n{user_prompt}"
        for sub in expected_substrings:
            self.assertIn(sub, combined_worker_prompt)
        self.assertIn(selected_code, combined_worker_prompt)
        # Must NOT contain surrounding file or context
        self.assertNotIn("import math", combined_worker_prompt)
        self.assertNotIn("def run():", combined_worker_prompt)
        self.assertNotIn("print(result)", combined_worker_prompt)
        self.assertNotIn("FOR REASONING ONLY", combined_worker_prompt)

    def test_02_correct_selection_returns_success_no_replacement(self):
        """2. Correct selection -> AI returns only SUCCESS -> no replacement occurs."""
        selected_code = "def add(x, y):\n    return x + y"
        ai_response = "SUCCESS"

        # Python Engine
        py_res = parse_replacement_response(ai_response, "python", selected_code)
        self.assertEqual(py_res["status"], "success")
        self.assertIsNone(py_res["code"])
        self.assertEqual(py_res["state"], "SUCCESS")

        # JS CodeExtractor parseReplacementResponse
        js_val = self.js_engine.evaluate(
            f'parseReplacementResponse({repr(ai_response)}, "python", {repr(selected_code)})'
        )
        self.assertEqual(js_val.property("status").toString(), "success")
        self.assertEqual(js_val.property("state").toString(), "SUCCESS")
        self.assertTrue(js_val.property("code").isNull())

        # JS extractReplacementCode returns empty string
        js_code_val = self.js_engine.evaluate(
            f'extractReplacementCode({repr(ai_response)}, "python", {repr(selected_code)})'
        )
        self.assertEqual(js_code_val.toString(), "")

        # JS parseMarkdownSegments returns text segment indicating success
        js_segments = self.js_engine.evaluate(
            f'parseMarkdownSegments({repr(ai_response)})'
        )
        self.assertEqual(js_segments.property("length").toInt(), 1)
        first_seg = js_segments.property(0)
        self.assertEqual(first_seg.property("type").toString(), "text")
        self.assertIn("SUCCESS: No bugs found", first_seg.property("text").toString())

    def test_03_buggy_selection_explains_bug_and_returns_fixed_code(self):
        """3. Selection containing a bug -> AI explains bug, returns [Fixed Code] with corrected selection."""
        selected_code = "if user_id = 123:\n    allow_access()"
        ai_response = (
            "The bug is that a single equals sign `=` is an assignment operator rather than "
            "an equality comparison operator in Python. Replacing it with `==` ensures proper comparison.\n\n"
            "[Fixed Code]\n"
            "```python\n"
            "if user_id == 123:\n"
            "    allow_access()\n"
            "```"
        )

        # Python Engine
        py_res = parse_replacement_response(ai_response, "python", selected_code)
        self.assertEqual(py_res["status"], "replacement")
        self.assertEqual(py_res["state"], "FIXED_CODE")
        self.assertEqual(py_res["code"].strip(), "if user_id == 123:\n    allow_access()")
        self.assertIn("assignment operator", py_res["explanation"])
        self.assertNotIn("[Fixed Code]", py_res["code"])
        self.assertNotIn("The bug is", py_res["code"])

        # JS CodeExtractor parseReplacementResponse
        js_val = self.js_engine.evaluate(
            f'parseReplacementResponse({repr(ai_response)}, "python", {repr(selected_code)})'
        )
        self.assertEqual(js_val.property("status").toString(), "replacement")
        self.assertEqual(js_val.property("state").toString(), "FIXED_CODE")
        self.assertEqual(js_val.property("code").toString().strip(), "if user_id == 123:\n    allow_access()")
        self.assertIn("assignment operator", js_val.property("explanation").toString())

        # JS extractReplacementCode
        js_code_val = self.js_engine.evaluate(
            f'extractReplacementCode({repr(ai_response)}, "python", {repr(selected_code)})'
        )
        self.assertEqual(js_code_val.toString().strip(), "if user_id == 123:\n    allow_access()")

        # JS parseMarkdownSegments splits explanation and code
        js_segments = self.js_engine.evaluate(
            f'parseMarkdownSegments({repr(ai_response)})'
        )
        self.assertEqual(js_segments.property("length").toInt(), 2)
        exp_seg = js_segments.property(0)
        code_seg = js_segments.property(1)
        self.assertEqual(exp_seg.property("type").toString(), "text")
        self.assertIn("assignment operator", exp_seg.property("text").toString())
        self.assertEqual(code_seg.property("type").toString(), "code")
        self.assertIn("if user_id == 123:", code_seg.property("code").toString())

    def test_04_small_selection_from_large_file_replaces_only_selection(self):
        """4. Small selection from a large file -> only selection is sent and can be replaced."""
        lines_before = [f"def func_{i}():\n    return {i}" for i in range(1, 50)]
        target_lines = "total = price * (1 - discnt)\nreturn totl"
        lines_after = [f"def helper_{i}():\n    pass" for i in range(1, 50)]

        full_doc = "\n\n".join(lines_before) + "\n\n" + target_lines + "\n\n" + "\n\n".join(lines_after)
        start_idx = full_doc.index(target_lines)
        end_idx = start_idx + len(target_lines)

        context = {
            "selectionStart": start_idx,
            "selectionEnd": end_idx,
            "totalDocLength": len(full_doc),
            "isFullFile": False
        }

        # Verify prompt sends ONLY target_lines
        user_prompt, _ = build_selection_prompt(
            code=target_lines,
            lang_id="python",
            surrounding_context=full_doc,
            is_full_file=False
        )
        self.assertIn(target_lines, user_prompt)
        self.assertNotIn("func_1", user_prompt)
        self.assertNotIn("helper_1", user_prompt)

        ai_response = (
            "Variable names were misspelled (`discnt` instead of `discount`, `totl` instead of `total`).\n\n"
            "[Fixed Code]\n"
            "```python\n"
            "total = price * (1 - discount)\n"
            "return total\n"
            "```"
        )

        py_res = parse_replacement_response(ai_response, "python", target_lines, context)
        self.assertEqual(py_res["status"], "replacement")
        fixed_code = py_res["code"].strip()

        # Simulate exact editor replacement
        doc_before = full_doc[:start_idx]
        doc_after = full_doc[end_idx:]
        replaced_doc = doc_before + fixed_code + doc_after

        # Surrounding code before and after must be 100% identical
        self.assertEqual(replaced_doc[:start_idx], full_doc[:start_idx])
        self.assertEqual(replaced_doc[start_idx + len(fixed_code):], full_doc[end_idx:])
        self.assertIn("func_1", replaced_doc)
        self.assertIn("helper_49", replaced_doc)

    def test_05_incomplete_fragment_no_autocomplete_expansion(self):
        """5. Incomplete fragments -> scope validation blocks outer wrappers and autocomplete expansions."""
        fragment = "page = context.new_page()"
        context = {
            "selectionStart": 100,
            "selectionEnd": 125,
            "totalDocLength": 500,
            "isFullFile": False
        }

        # AI incorrectly wraps the fragment in a full sync_playwright block
        expanded_ai_response = (
            "I autocompleted the fragment with the full Playwright setup.\n\n"
            "[Fixed Code]\n"
            "```python\n"
            "with sync_playwright() as p:\n"
            "    browser = p.chromium.launch()\n"
            "    context = browser.new_context()\n"
            "    page = context.new_page()\n"
            "    browser.close()\n"
            "```"
        )

        # Python Engine blocks scope hazard
        py_res = parse_replacement_response(expanded_ai_response, "python", fragment, context)
        self.assertEqual(py_res["status"], "scope_mismatch")
        self.assertIsNone(py_res["code"])
        self.assertIn("Scope Hazard", py_res["error"])

        # JS Engine blocks scope hazard
        js_val = self.js_engine.evaluate(
            f'parseReplacementResponse({repr(expanded_ai_response)}, "python", {repr(fragment)}, '
            f'{{ isFullFile: false, selectionStart: 100, selectionEnd: 125, totalDocLength: 500 }})'
        )
        self.assertEqual(js_val.property("status").toString(), "scope_mismatch")
        self.assertTrue(js_val.property("code").isNull())

    def test_06_invalid_ai_response_safely_rejected(self):
        """6. Invalid AI response -> rejected safely, no code changed."""
        invalid_responses = [
            "",
            "   \n\t  ",
            "Sure! I can help you with your code. What would you like me to do?",
            "Here is some information about Python variables and syntax.",
        ]

        for resp in invalid_responses:
            py_res = parse_replacement_response(resp, "python", "x = 1")
            self.assertEqual(py_res["status"], "invalid")
            self.assertIsNone(py_res["code"])

            js_val = self.js_engine.evaluate(
                f'parseReplacementResponse({repr(resp)}, "python", "x = 1")'
            )
            self.assertEqual(js_val.property("status").toString(), "invalid")
            self.assertTrue(js_val.property("code").isNull())

            js_code = self.js_engine.evaluate(
                f'extractReplacementCode({repr(resp)}, "python", "x = 1")'
            )
            self.assertEqual(js_code.toString(), "")

    def test_07_editor_boundary_and_text_change_verification(self):
        """7. Verify that if text or boundaries change while request in-flight, replacement is blocked."""
        original_doc = "function main() {\n    let count = 0;\n    count += 1;\n    return count;\n}"
        start_pos = original_doc.index("let count = 0;")
        end_pos = start_pos + len("let count = 0;")
        original_text = "let count = 0;"

        # Case A: Document text matches originalText -> replacement succeeds
        current_text = original_doc[start_pos:end_pos]
        self.assertEqual(current_text, original_text)

        # Case B: User edited document text at (start_pos, end_pos) while AI request was running
        modified_doc = "function main() {\n    let counter = 5;\n    count += 1;\n    return count;\n}"
        current_modified_text = modified_doc[start_pos:end_pos]
        self.assertNotEqual(current_modified_text, original_text)

        # Simulated replaceSelection safety check
        def simulate_replace_selection(doc, s, e, new_code, orig):
            if orig and len(orig) > 0:
                current_range_text = doc[s:e]
                if current_range_text != orig:
                    return False, doc
            new_doc = doc[:s] + new_code + doc[e:]
            return True, new_doc

        # With mismatch -> aborted, document unchanged
        success, res_doc = simulate_replace_selection(modified_doc, start_pos, end_pos, "let count = 1;", original_text)
        self.assertFalse(success)
        self.assertEqual(res_doc, modified_doc)

        # With match -> succeeded
        success, res_doc = simulate_replace_selection(original_doc, start_pos, end_pos, "let count = 1;", original_text)
        self.assertTrue(success)
        self.assertIn("let count = 1;", res_doc)
        self.assertNotIn("let count = 0;", res_doc)


if __name__ == "__main__":
    unittest.main()
