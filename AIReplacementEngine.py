"""
AIReplacementEngine.py - Protocol Parser & Scope Validator for DGX Studio AI Code Replacement.
Enforces the 3-State Protocol: [REPLACEMENT_CODE], [NO_CHANGE], [INSUFFICIENT_CONTEXT].
Validates scope preservation and blocks unauthorized full-file/full-block expansions on partial selections.
"""

import re
from typing import Optional, Dict, Any, Tuple


REPL_MARKER = "[REPLACEMENT_CODE]"
FIXED_CODE_MARKER = "[Fixed Code]"
NO_CHANGE_MARKER = "[NO_CHANGE]"
SUCCESS_MARKER = "SUCCESS"
INSUFF_MARKER = "[INSUFFICIENT_CONTEXT]"

SELECTION_BUG_FIX_PROMPT = (
    "Review the provided code selection and fix any bugs that exist.\n\n"
    "If there are no bugs, return only:\n"
    "SUCCESS\n\n"
    "If a bug exists:\n"
    "1. Give a brief explanation of approximately 50 words describing the bug.\n"
    "2. Write [Fixed Code] on a separate line.\n"
    "3. Below [Fixed Code], provide the corrected code.\n\n"
    "IMPORTANT:\n"
    "- Fix only actual bugs or errors.\n"
    "- Return the exact same selection of code with only the necessary bug fixes applied.\n"
    "- Do not rewrite correct code.\n"
    "- Do not refactor, optimize, or change formatting unnecessarily.\n"
    "- Do not autocomplete incomplete code or fragments.\n"
    "- Do not add missing code that was not part of the selection.\n"
    "- Preserve all other supplied code exactly as it was.\n"
    "- The selected code defines the maximum replacement scope.\n"
    "- If no bug exists, return only SUCCESS without explanation or code."
)


def build_selection_internal_instruction(is_full_file: bool = False, lang_tag: str = "") -> str:
    """
    Constructs the system instruction for selection replacement mode.
    """
    return SELECTION_BUG_FIX_PROMPT


def build_selection_prompt(
    code: str,
    lang_id: str = "",
    custom_prompt: str = "",
    surrounding_context: str = "",
    is_full_file: bool = False
) -> Tuple[str, str]:
    """
    Builds the user-visible prompt and backend internal instruction for selection bug fixing.
    Sends ONLY the selected code as the source-code payload (no full file or surrounding context).
    Returns (user_prompt, internal_instruction).
    """
    lang_tag = (lang_id or "").lower().strip()
    base_prompt = custom_prompt.strip() if custom_prompt and custom_prompt.strip() else SELECTION_BUG_FIX_PROMPT
    user_prompt = f"{base_prompt}\n\n```{lang_tag}\n{code}\n```"
    return user_prompt, ""


def sanitize_extracted_code(code: str) -> str:
    """Cleans marker artifacts or unescaped control tags from code blocks."""
    if not code:
        return ""
    cleaned = (
        code.replace(FIXED_CODE_MARKER, "")
        .replace(REPL_MARKER, "")
        .replace(NO_CHANGE_MARKER, "")
        .replace(INSUFF_MARKER, "")
    )
    return cleaned.strip("\r\n")
    return cleaned.strip("\r\n")


def validate_replacement_scope(
    extracted_code: str,
    original_selected_text: str,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Validates that extracted code matches the user's selected scope and does not perform
    an unauthorized scope expansion (e.g. returning full-file wrappers on a small selection)
    or destructive partial truncation on a large selection.
    """
    if not original_selected_text or not original_selected_text.strip():
        return True, "No original selection provided"

    if not extracted_code or not extracted_code.strip():
        return False, "Replacement code is empty."

    ctx = context or {}
    is_full_file = ctx.get("isFullFile", False)
    total_doc_len = ctx.get("totalDocLength", -1)
    sel_start = ctx.get("selectionStart", -1)
    sel_end = ctx.get("selectionEnd", -1)

    if sel_start == 0 and total_doc_len > 0 and sel_end >= total_doc_len:
        is_full_file = True

    if is_full_file:
        return True, "Full file selection allows full replacement."

    orig_trim = original_selected_text.strip()
    repl_trim = extracted_code.strip()

    if orig_trim == repl_trim:
        return True, "Code identical"

    orig_lines = [l for l in orig_trim.splitlines() if l.strip()]
    repl_lines = [l for l in repl_trim.splitlines() if l.strip()]
    orig_line_count = len(orig_lines)
    repl_line_count = len(repl_lines)

    # 1. Scope Expansion: Outer Enclosure Insertion (e.g. with sync_playwright(), def main(), class X)
    outer_wrapper_patterns = [
        (r"\bwith\s+sync_playwright\b", "with sync_playwright block", r"\b(?:playwright|wright)\b"),
        (r"\bdef\s+main\s*\(", "def main() entrypoint", r"\bmain\b"),
        (r"\bif\s+__name__\s*==\s*['\"]__main__['\"]", "if __name__ == '__main__' block", r"__main__"),
        (r"\bclass\s+\w+", "class definition", r"\bclass\b"),
        (r"\bint\s+main\s*\(", "main() function", r"\bmain\b"),
        (r"\bpublic\s+static\s+void\s+main\b", "public static void main entrypoint", r"\bmain\b")
    ]

    for pat, name, allow_pat in outer_wrapper_patterns:
        if re.search(pat, repl_trim) and not re.search(pat, orig_trim):
            if allow_pat and re.search(allow_pat, orig_trim, re.IGNORECASE):
                continue
            if orig_line_count <= 6:
                return False, f"Scope Hazard: Replacement introduced outer wrapper ({name}) not present in selected code."

    # 2. Scope Expansion: Small Statement turned into full multi-statement program with top-level imports
    orig_has_imports = bool(re.search(r"\b(import\s+|#include\s+|package\s+|using\s+|from\s+\w+\s+import)", orig_trim, re.IGNORECASE))
    repl_has_imports = bool(re.search(r"\b(import\s+|#include\s+|package\s+|using\s+|from\s+\w+\s+import)", repl_trim, re.IGNORECASE))

    if not orig_has_imports and repl_has_imports and orig_line_count <= 4 and repl_line_count >= 8:
        return False, "Scope Hazard: Replacement expanded small statement into full multi-statement application with imports."

    # 3. Scope Expansion: Surrounding Context Duplication
    surrounding = ctx.get("surroundingContext", "")
    if surrounding and surrounding.strip() and orig_trim in repl_trim:
        # If the replacement contains the original text plus substantial unselected code
        if repl_line_count >= orig_line_count + 6:
            return False, "Scope Hazard: Replacement contains unselected surrounding context code."

    # 4. Under-Scope Hazard: Large Selection replaced with tiny fragment
    if orig_line_count >= 8 and repl_line_count <= 3:
        return False, f"Scope Hazard: Selection has {orig_line_count} lines, but replacement contains only {repl_line_count} lines."

    if orig_line_count >= 15 and (repl_line_count / max(1, orig_line_count)) < 0.35:
        return False, f"Scope Hazard: Replacement line count ({repl_line_count}) is less than 35% of selected scope ({orig_line_count} lines)."

    # 5. Structural integrity: Whole class/file selections preserving definitions
    orig_has_class = bool(re.search(r"\b(class\s+|interface\s+|struct\s+|enum\s+)\w+", orig_trim, re.IGNORECASE))
    repl_has_class = bool(re.search(r"\b(class\s+|interface\s+|struct\s+|enum\s+)\w+", repl_trim, re.IGNORECASE))

    if orig_has_class and not repl_has_class and orig_line_count >= 10 and repl_line_count < orig_line_count * 0.6:
        return False, "Scope Hazard: Selected scope contains class definitions which are missing from the replacement."

    if orig_has_imports and not repl_has_imports and orig_line_count >= 10 and repl_line_count < orig_line_count * 0.6:
        return False, "Scope Hazard: Selected scope contains import/package statements which are missing from the replacement."

    return True, "Valid replacement scope"


def parse_replacement_response(
    response: str,
    preferred_lang: str = "",
    original_selected_text: str = "",
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Strictly parses an AI response according to the 3-State Protocol and emits the exact required logs.
    """
    ctx = context or {}
    sel_start = ctx.get("selectionStart", -1)
    sel_end = ctx.get("selectionEnd", -1)
    orig_lines = [l for l in (original_selected_text or "").splitlines() if l.strip()]
    sel_line_count = len(orig_lines) if orig_lines else 1
    sel_chars = len(original_selected_text) if original_selected_text else 0

    print(f"[AIReplacement] Selection start: {sel_start}")
    print(f"[AIReplacement] Selection end: {sel_end}")
    print(f"[AIReplacement] Selection lines: {sel_line_count}")
    print(f"[AIReplacement] Selection chars: {sel_chars}")
    print(f"[AIReplacement] Raw CustomApi response: {response}")

    if not response or not isinstance(response, str):
        print(f"[AIReplacement] Parsed state: INVALID")
        print(f"[AIReplacement] Replacement lines: 0")
        print(f"[AIReplacement] Replacement chars: 0")
        print(f"[AIReplacement] Scope validation: FAIL")
        print(f"[AIReplacement] Replacement applied: false")
        return {"status": "invalid", "code": None, "state": "INVALID"}

    # 1. FIXED_CODE ([Fixed Code])
    fixed_code_match = re.search(r'\[Fixed\s+Code\]:?', response, re.IGNORECASE)
    if fixed_code_match:
        split_idx = fixed_code_match.start()
        explanation = response[:split_idx].strip()
        after_marker = response[fixed_code_match.end():].strip()

        # Check for fenced code block below [Fixed Code]
        fence_regex = re.compile(r"(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,}|\Z)")
        fence_match = fence_regex.search(after_marker)
        if fence_match and fence_match.group(2) and fence_match.group(2).strip():
            extracted = sanitize_extracted_code(fence_match.group(2))
        else:
            extracted = sanitize_extracted_code(after_marker)

        if extracted and extracted.strip():
            repl_lines = [l for l in extracted.splitlines() if l.strip()]
            repl_line_count = len(repl_lines)
            repl_chars = len(extracted)

            print("[AIReplacement] Parsed state: FIXED_CODE")
            print(f"[AIReplacement] Replacement lines: {repl_line_count}")
            print(f"[AIReplacement] Replacement chars: {repl_chars}")

            is_valid, reason = validate_replacement_scope(extracted, original_selected_text, ctx)
            if is_valid:
                print("[AIReplacement] Scope validation: PASS")
                return {
                    "status": "replacement",
                    "code": extracted,
                    "state": "FIXED_CODE",
                    "explanation": explanation,
                    "reason": reason
                }
            else:
                print("[AIReplacement] Scope validation: FAIL")
                print("[AIReplacement] Replacement applied: false")
                return {
                    "status": "scope_mismatch",
                    "code": None,
                    "state": "FIXED_CODE",
                    "error": reason
                }

        print("[AIReplacement] Parsed state: INVALID")
        print("[AIReplacement] Replacement lines: 0")
        print("[AIReplacement] Replacement chars: 0")
        print("[AIReplacement] Scope validation: FAIL")
        print("[AIReplacement] Replacement applied: false")
        return {"status": "invalid", "code": None, "state": "INVALID"}

    # 2. SUCCESS (No bugs found)
    trim_resp = response.strip()
    is_success = bool(re.search(r'^\s*SUCCESS\b', trim_resp, re.IGNORECASE) or (trim_resp == "SUCCESS"))
    if not is_success and "[Fixed Code]" not in response:
        if re.search(r'\bSUCCESS\b', response) and len(trim_resp.split()) <= 10:
            is_success = True

    if is_success:
        print("[AIReplacement] Parsed state: SUCCESS")
        print("[AIReplacement] Replacement lines: 0")
        print("[AIReplacement] Replacement chars: 0")
        print("[AIReplacement] Scope validation: PASS")
        print("[AIReplacement] Replacement applied: false")
        return {
            "status": "success",
            "code": None,
            "state": "SUCCESS",
            "message": "SUCCESS: No bugs found in the provided code selection."
        }

    # 3. Legacy REPLACEMENT_CODE
    has_repl = REPL_MARKER in response
    if has_repl:
        text_after_marker = response.split(REPL_MARKER, 1)[1]
        fence_regex = re.compile(r"(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,}|\Z)")
        match = fence_regex.search(text_after_marker)

        if match and match.group(2) and match.group(2).strip():
            extracted = sanitize_extracted_code(match.group(2))
            repl_lines = [l for l in extracted.splitlines() if l.strip()]
            repl_line_count = len(repl_lines)
            repl_chars = len(extracted)

            print(f"[AIReplacement] Parsed state: REPLACEMENT_CODE")
            print(f"[AIReplacement] Replacement lines: {repl_line_count}")
            print(f"[AIReplacement] Replacement chars: {repl_chars}")

            is_valid, reason = validate_replacement_scope(extracted, original_selected_text, ctx)
            if is_valid:
                print(f"[AIReplacement] Scope validation: PASS")
                return {
                    "status": "replacement",
                    "code": extracted,
                    "state": "REPLACEMENT_CODE",
                    "reason": reason
                }
            else:
                print(f"[AIReplacement] Scope validation: FAIL")
                print(f"[AIReplacement] Replacement applied: false")
                return {
                    "status": "scope_mismatch",
                    "code": None,
                    "state": "REPLACEMENT_CODE",
                    "error": reason
                }

        print(f"[AIReplacement] Parsed state: INVALID")
        print(f"[AIReplacement] Replacement lines: 0")
        print(f"[AIReplacement] Replacement chars: 0")
        print(f"[AIReplacement] Scope validation: FAIL")
        print(f"[AIReplacement] Replacement applied: false")
        return {"status": "invalid", "code": None, "state": "INVALID"}

    # 4. Legacy NO_CHANGE
    has_no_change = NO_CHANGE_MARKER in response
    if has_no_change:
        print(f"[AIReplacement] Parsed state: NO_CHANGE")
        print(f"[AIReplacement] Replacement lines: 0")
        print(f"[AIReplacement] Replacement chars: 0")
        print(f"[AIReplacement] Scope validation: PASS")
        print(f"[AIReplacement] Replacement applied: false")
        return {"status": "no_change", "code": None, "state": "NO_CHANGE"}

    # 5. Legacy INSUFFICIENT_CONTEXT
    has_insuff = INSUFF_MARKER in response
    if has_insuff:
        print(f"[AIReplacement] Parsed state: INSUFFICIENT_CONTEXT")
        print(f"[AIReplacement] Replacement lines: 0")
        print(f"[AIReplacement] Replacement chars: 0")
        print(f"[AIReplacement] Scope validation: PASS")
        print(f"[AIReplacement] Replacement applied: false")
        return {"status": "insufficient_context", "code": None, "state": "INSUFFICIENT_CONTEXT"}

    # 6. INVALID / UNSTRUCTURED
    print(f"[AIReplacement] Parsed state: INVALID")
    print(f"[AIReplacement] Replacement lines: 0")
    print(f"[AIReplacement] Replacement chars: 0")
    print(f"[AIReplacement] Scope validation: FAIL")
    print(f"[AIReplacement] Replacement applied: false")
    return {"status": "invalid", "code": None, "state": "INVALID"}
