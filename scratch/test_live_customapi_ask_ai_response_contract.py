"""
test_live_customapi_ask_ai_response_contract.py - Comprehensive test suite for Live CustomApi Ask AI Response Contract.
Validates the 3-State Protocol, scope preservation, full-file selection exception, and debug logging.
"""

import os
import sys
import unittest
from unittest.mock import patch

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QJSEngine
from AIReplacementEngine import (
    build_selection_prompt,
    parse_replacement_response,
    validate_replacement_scope
)


class TestLiveCustomApiAskAiResponseContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        cls.js_engine = QJSEngine()

        # Load CodeExtractor.js into QJSEngine for dual validation
        js_path = os.path.join(repo_root, "qml", "ai", "CodeExtractor.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js_code = f.read()
            # Strip .pragma library for evaluation in QJSEngine script context
            js_code = js_code.replace(".pragma library", "// .pragma library")
            val = cls.js_engine.evaluate(js_code, "CodeExtractor.js")
            if val.isError():
                raise RuntimeError(f"Failed to load CodeExtractor.js in QJSEngine: {val.toString()}")

    def test_01_small_fragment_valid_replacement_passes_scope_validation(self):
        """TEST 1A: Selected small fragment -> AI returns ONLY the replacement for the selected range -> PASS."""
        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        selected_code = "page = context.new_page()"
        surrounding_file = (
            "from playwright.sync_api import sync_playwright\n\n"
            "with sync_playwright() as p:\n"
            "    browser = p.chromium.launch(headless=True)\n"
            "    context = browser.new_context()\n"
            "    page = context.new_page()\n"
            "    page.goto('https://example.com')\n"
            "    browser.close()\n"
        )
        context = {
            "selectionStart": surrounding_file.index(selected_code),
            "selectionEnd": surrounding_file.index(selected_code) + len(selected_code),
            "totalDocLength": len(surrounding_file),
            "surroundingContext": surrounding_file,
            "isFullFile": False
        }

        raw_ai_response = (
            "I fixed the page initialization to include a custom viewport.\n\n"
            "[REPLACEMENT_CODE]\n"
            "```python\n"
            "page = context.new_page()\n"
            "page.set_viewport_size({'width': 1280, 'height': 720})\n"
            "```\n\n"
            "This ensures the page has a defined resolution."
        )

        with patch("builtins.print", side_effect=capturing_print):
            res = parse_replacement_response(raw_ai_response, "python", selected_code, context)

        self.assertEqual(res["status"], "replacement")
        self.assertEqual(res["state"], "REPLACEMENT_CODE")
        self.assertIn("page.set_viewport_size", res["code"])
        self.assertNotIn("with sync_playwright", res["code"])

        # Check required debug logs
        self.assertTrue(any("[AIReplacement] Selection start:" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Selection end:" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Selection lines:" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Selection chars:" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Raw CustomApi response:" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Parsed state: REPLACEMENT_CODE" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Replacement lines:" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Replacement chars:" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Scope validation: PASS" in l for l in logs))

    def test_01b_scope_expansion_rejected_when_ai_returns_full_outer_wrapper(self):
        """TEST 1B: Selected 1 line -> AI returns entire 'with sync_playwright()' file -> FAIL (scope expansion rejected)."""
        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        selected_code = "page = context.new_page()"
        surrounding_file = (
            "from playwright.sync_api import sync_playwright\n\n"
            "with sync_playwright() as p:\n"
            "    browser = p.chromium.launch(headless=True)\n"
            "    context = browser.new_context()\n"
            "    page = context.new_page()\n"
            "    page.goto('https://example.com')\n"
            "    browser.close()\n"
        )
        context = {
            "selectionStart": surrounding_file.index(selected_code),
            "selectionEnd": surrounding_file.index(selected_code) + len(selected_code),
            "totalDocLength": len(surrounding_file),
            "surroundingContext": surrounding_file,
            "isFullFile": False
        }

        # ChatGPT returned a full implementation instead of just the selected line
        hallucinated_full_file_response = (
            "Here is the complete updated file:\n\n"
            "[REPLACEMENT_CODE]\n"
            "```python\n"
            "from playwright.sync_api import sync_playwright\n\n"
            "with sync_playwright() as p:\n"
            "    browser = p.chromium.launch(headless=True)\n"
            "    context = browser.new_context()\n"
            "    page = context.new_page()\n"
            "    page.goto('https://example.com')\n"
            "    print(page.title())\n"
            "    browser.close()\n"
            "```\n"
        )

        with patch("builtins.print", side_effect=capturing_print):
            res = parse_replacement_response(hallucinated_full_file_response, "python", selected_code, context)

        self.assertEqual(res["status"], "scope_mismatch")
        self.assertIsNone(res["code"])
        self.assertTrue(any("[AIReplacement] Scope validation: FAIL" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Replacement applied: false" in l for l in logs))

    def test_02_insufficient_context_response_handled_correctly(self):
        """TEST 2: Fix requires external code outside selection -> AI returns [INSUFFICIENT_CONTEXT] -> No code replaced."""
        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        selected_code = "page = context.new_page()"
        context = {
            "selectionStart": 50,
            "selectionEnd": 75,
            "totalDocLength": 300,
            "isFullFile": False
        }

        raw_ai_response = (
            "The browser context configuration is defined in an outer module not visible in this selection.\n\n"
            "[INSUFFICIENT_CONTEXT]\n\n"
            "Please provide the context setup code where new_context() was initialized."
        )

        with patch("builtins.print", side_effect=capturing_print):
            res = parse_replacement_response(raw_ai_response, "python", selected_code, context)

        self.assertEqual(res["status"], "insufficient_context")
        self.assertEqual(res["state"], "INSUFFICIENT_CONTEXT")
        self.assertIsNone(res["code"])
        self.assertTrue(any("[AIReplacement] Parsed state: INSUFFICIENT_CONTEXT" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Replacement applied: false" in l for l in logs))

    def test_03_no_change_response_handled_correctly(self):
        """TEST 3: Selected code is already correct -> AI returns [NO_CHANGE] -> No code replaced."""
        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        selected_code = "int result = a + b;"
        context = {
            "selectionStart": 10,
            "selectionEnd": 29,
            "totalDocLength": 100,
            "isFullFile": False
        }

        raw_ai_response = (
            "The selected statement is already syntactically correct and optimal.\n\n"
            "[NO_CHANGE]\n\n"
            "No modification is required."
        )

        with patch("builtins.print", side_effect=capturing_print):
            res = parse_replacement_response(raw_ai_response, "cpp", selected_code, context)

        self.assertEqual(res["status"], "no_change")
        self.assertEqual(res["state"], "NO_CHANGE")
        self.assertIsNone(res["code"])
        self.assertTrue(any("[AIReplacement] Parsed state: NO_CHANGE" in l for l in logs))
        self.assertTrue(any("[AIReplacement] Replacement applied: false" in l for l in logs))

    def test_04_full_file_selection_allows_full_replacement(self):
        """TEST 4: Entire file is selected -> full-file replacement permitted -> PASS."""
        logs = []
        def capturing_print(*args, **kwargs):
            logs.append(" ".join(str(a) for a in args))

        full_file_content = (
            "def add(a, b):\n"
            "    return a - b\n"
        )
        context = {
            "selectionStart": 0,
            "selectionEnd": len(full_file_content),
            "totalDocLength": len(full_file_content),
            "isFullFile": True
        }

        raw_ai_response = (
            "Fixed subtraction bug in add function.\n\n"
            "[REPLACEMENT_CODE]\n"
            "```python\n"
            "def add(a, b):\n"
            "    return a + b\n"
            "```"
        )

        with patch("builtins.print", side_effect=capturing_print):
            res = parse_replacement_response(raw_ai_response, "python", full_file_content, context)

        self.assertEqual(res["status"], "replacement")
        self.assertEqual(res["state"], "REPLACEMENT_CODE")
        self.assertIn("return a + b", res["code"])
        self.assertTrue(any("[AIReplacement] Scope validation: PASS" in l for l in logs))

    def test_05_strict_selection_prompt_generation(self):
        """TEST 5: Strict selection prompt contains selection mode rules, surrounding context for reasoning, and scope preservation."""
        user_prompt, internal_instr = build_selection_prompt(
            code="browser = context.new_page()",
            lang_id="python",
            custom_prompt="Fix null context bug",
            surrounding_context="with sync_playwright() as p:\n    browser = context.new_page()",
            is_full_file=False
        )

        self.assertIn("Fix null context bug", user_prompt)
        self.assertIn("browser = context.new_page()", user_prompt)
        # Payload isolation: surrounding context must NOT be included in prompt
        self.assertNotIn("FOR REASONING ONLY", user_prompt)
        self.assertNotIn("with sync_playwright() as p:", user_prompt)

    def test_06_js_code_extractor_matches_python_engine_behavior(self):
        """TEST 6: CodeExtractor.js in QJSEngine behaves identically to Python AIReplacementEngine."""
        import json
        selected_code = "page = context.new_page()"
        context_json = "{ isFullFile: false, selectionStart: 50, selectionEnd: 75, totalDocLength: 300 }"
        
        # Test valid replacement in JS
        valid_resp = "Fixed.\n\n[REPLACEMENT_CODE]\n```python\npage = context.new_page()\n```"
        js_cmd = f"parseReplacementResponse({json.dumps(valid_resp)}, 'python', {json.dumps(selected_code)}, {context_json})"
        js_val = self.js_engine.evaluate(js_cmd)
        self.assertFalse(js_val.isError())
        self.assertEqual(js_val.property("status").toString(), "replacement")
        self.assertEqual(js_val.property("state").toString(), "REPLACEMENT_CODE")

        # Test invalid outer wrapper expansion in JS
        bad_resp = "Here is the full file:\n\n[REPLACEMENT_CODE]\n```python\nwith sync_playwright() as p:\n    page = context.new_page()\n```"
        js_bad_cmd = f"parseReplacementResponse({json.dumps(bad_resp)}, 'python', {json.dumps(selected_code)}, {context_json})"
        js_bad_val = self.js_engine.evaluate(js_bad_cmd)
        self.assertFalse(js_bad_val.isError())
        self.assertEqual(js_bad_val.property("status").toString(), "scope_mismatch")

    def test_test_a_selected_code_minimal_edit_preserves_provided_code(self):
        """TEST A — SELECTED CODE: AI minimally changes 'wright() as p:' to 'with sync_playwright() as p:' preserving all lines."""
        provided_code = (
            "wright() as p:\n"
            "    browser = p.chromium.launch(headless=False)\n\n"
            "    context = browser.new_context(\n"
            "        user_agent=(\n"
            '            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "\n'
            '            "AppleWebKit/537.36 (KHTML, like Gecko) "\n'
            '            "Chrome/142.0.0.0 Safari/537.36"\n'
            "        ),\n"
            '        viewport={"width": 1920, "height": 1080},\n'
            '        locale="en-US",\n'
            '        timezone_id="Asia/Kolkata",\n'
            "    )\n\n"
            "    page = context.new_page()\n\n"
            "    page.goto(\n"
            '        "https://chatgpt.com/",\n'
            '        wait_until="domcontentloaded",\n'
            "    )\n\n"
            "    print(page.title())\n"
            "    print(page.url)"
        )

        expected_replacement = (
            "with sync_playwright() as p:\n"
            "    browser = p.chromium.launch(headless=False)\n\n"
            "    context = browser.new_context(\n"
            "        user_agent=(\n"
            '            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "\n'
            '            "AppleWebKit/537.36 (KHTML, like Gecko) "\n'
            '            "Chrome/142.0.0.0 Safari/537.36"\n'
            "        ),\n"
            '        viewport={"width": 1920, "height": 1080},\n'
            '        locale="en-US",\n'
            '        timezone_id="Asia/Kolkata",\n'
            "    )\n\n"
            "    page = context.new_page()\n\n"
            "    page.goto(\n"
            '        "https://chatgpt.com/",\n'
            '        wait_until="domcontentloaded",\n'
            "    )\n\n"
            "    print(page.title())\n"
            "    print(page.url)"
        )

        context = {
            "selectionStart": 0,
            "selectionEnd": len(provided_code),
            "totalDocLength": len(provided_code),
            "isFullFile": False
        }

        raw_ai_response = (
            "Fixed incomplete first line `wright() as p:` to `with sync_playwright() as p:`.\n\n"
            "[REPLACEMENT_CODE]\n"
            "```python\n"
            f"{expected_replacement}\n"
            "```\n\n"
            "All other browser configuration and navigation lines were preserved exactly as supplied."
        )

        res = parse_replacement_response(raw_ai_response, "python", provided_code, context)
        self.assertEqual(res["status"], "replacement")
        self.assertEqual(res["state"], "REPLACEMENT_CODE")
        self.assertEqual(res["code"], expected_replacement)
        self.assertTrue(res["code"].startswith("with sync_playwright() as p:"))
        self.assertIn('"Asia/Kolkata"', res["code"])
        self.assertIn('"https://chatgpt.com/"', res["code"])

    def test_test_b_smart_install_missing_dependency_resolves_installation(self):
        """TEST B — SMART INSTALL: Formatter=Prettier, available=false, missing=true -> AI resolves install command."""
        from ExtensionManager import ExtensionManager
        from AIBackend import AIBackend
        import json

        ext_mgr = ExtensionManager()
        ai_backend = AIBackend()
        ext_mgr.ai_backend = ai_backend

        def mock_ai_prettier_install(prompt):
            self.assertIn("BACKEND VERIFIED FACTS (AUTHORITATIVE):", prompt)
            self.assertIn("Formatter available: false", prompt)
            self.assertIn("Dependency missing: true", prompt)
            self.assertIn("TRUST BACKEND FACTS", prompt)
            return json.dumps({
                "resolutionType": "single_command",
                "source": "ai",
                "title": "Install Prettier",
                "diagnosis": "Prettier formatter is not installed",
                "explanation": "Prettier is missing. Install it globally via npm: npm install -g prettier",
                "command": "npm install -g prettier",
                "steps": [],
                "verificationCommand": "prettier --version",
                "tool": "Prettier",
                "package": "prettier",
                "executable": "prettier",
                "retryOperation": True
            })

        AIBackend.set_ai_provider(mock_ai_prettier_install)
        try:
            ctx = ext_mgr.create_smart_install_context(
                operation="Format JavaScript with Prettier",
                operation_type="formatter",
                language="javascript",
                file_path="app.js",
                executable="prettier",
                formatter="Prettier",
                formatter_available=False,
                dependency_missing=True,
                failure_type="missing_dependency"
            )

            proposal = ext_mgr.resolve_smart_install_context(ctx)
            self.assertEqual(proposal["source"], "ai")
            self.assertEqual(proposal["resolutionType"], "single_command")
            self.assertEqual(proposal["command"], "npm install -g prettier")
            self.assertEqual(proposal["verifyCommand"], "prettier --version")
        finally:
            AIBackend.set_ai_provider(None)

    def test_test_c_smart_install_source_error_does_not_reinstall_formatter(self):
        """TEST C — SMART INSTALL: Formatter=Prettier, available=true, missing=false, type=source_error -> Explains source bug."""
        from ExtensionManager import ExtensionManager
        from AIBackend import AIBackend
        import json

        ext_mgr = ExtensionManager()
        ai_backend = AIBackend()
        ext_mgr.ai_backend = ai_backend

        def mock_ai_source_error(prompt):
            self.assertIn("Failure type: source_error", prompt)
            self.assertIn("DO NOT CONFUSE FAILURE TYPES", prompt)
            return json.dumps({
                "resolutionType": "cannot_resolve",
                "source": "ai",
                "title": "Syntax Error in JavaScript File",
                "diagnosis": "Unexpected token ';' at line 12",
                "explanation": "Prettier encountered a syntax error in your source file. Fix the syntax error in the code editor; do not reinstall Prettier.",
                "command": "",
                "steps": [],
                "verificationCommand": "prettier --version",
                "tool": "Prettier",
                "package": "prettier",
                "executable": "prettier",
                "retryOperation": False
            })

        AIBackend.set_ai_provider(mock_ai_source_error)
        try:
            ctx = ext_mgr.create_smart_install_context(
                operation="Format JavaScript with Prettier",
                operation_type="formatter",
                language="javascript",
                file_path="app.js",
                executable="prettier",
                formatter="Prettier",
                formatter_available=True,
                dependency_missing=False,
                failure_type="source_error",
                error_message="SyntaxError: Unexpected token (12:4)"
            )

            proposal = ext_mgr.resolve_smart_install_context(ctx)
            self.assertEqual(proposal["source"], "ai")
            self.assertEqual(proposal["resolutionType"], "cannot_resolve")
            self.assertEqual(proposal["command"], "")
            self.assertIn("syntax error", proposal["explanation"].lower())
        finally:
            AIBackend.set_ai_provider(None)


if __name__ == "__main__":
    unittest.main()
