"""
AIReplacementEngine.py - Protocol Parser & Scope Validator for DGX Studio AI Code Replacement.
Enforces the 3-State Protocol: [REPLACEMENT_CODE], [NO_CHANGE], [INSUFFICIENT_CONTEXT].
Validates scope preservation and blocks unauthorized full-file/full-block expansions on partial selections.
"""

import re
from typing import Optional, Dict, Any, Tuple


REPL_MARKER = "[REPLACEMENT_CODE]"
NO_CHANGE_MARKER = "[NO_CHANGE]"
INSUFF_MARKER = "[INSUFFICIENT_CONTEXT]"


def build_selection_internal_instruction(is_full_file: bool = False, lang_tag: str = "") -> str:
    """
    Constructs the strict system instruction sent to CustomApi/ChatGPT for selection replacement mode.
    """
    scope_note = " (which spans the entire file)." if is_full_file else "."
    lang_str = f"```{lang_tag}\ncomplete replacement for ONLY the selected region\n```" if lang_tag else "```\ncomplete replacement for ONLY the selected region\n```"

    return (
        "SELECTION REPLACEMENT MODE\n"
        f"The user has selected a specific region of an existing source file{scope_note}\n"
        "Your response is NOT a request to rewrite or regenerate the entire file or block.\n"
        "You MUST reason about the selected region and surrounding context, but your replacement output MUST remain limited to the exact selected scope.\n\n"
        "CORE PRINCIPLE:\n"
        "THE PROVIDED CODE IS THE SOURCE OF TRUTH.\n"
        "Only modify the minimum text required to fix the requested problem.\n\n"
        "Strict Code Preservation Rules:\n"
        "1. Preserve all provided code EXACTLY unless a specific change is required to solve the user's request.\n"
        "2. MINIMAL EDIT PRINCIPLE: Think of the task as a surgical edit. Only fix the broken part (e.g. changing an incomplete or broken statement) and preserve every other line, variable name, string literal, comment, URL, browser setting, import, indentation, and formatting verbatim as supplied.\n"
        "3. Do NOT rewrite the whole block, do NOT regenerate unchanged code, and do NOT replace equivalent code with an alternative implementation.\n"
        "4. Do NOT rename variables, reorder lines, change quotes/formatting, 'clean up', or modernize code that was not requested.\n"
        "5. Do NOT create a complete example, new application, or boilerplate when only a fragment was selected.\n"
        "6. Never return the full source file unless the user's selected scope itself is the full file.\n"
        "7. Never return unrelated surrounding code or duplicate unselected code.\n"
        "8. If the selected fragment can be fixed independently, return ONLY its complete corrected replacement preserving all unchanged lines.\n"
        "9. If the correct fix requires code outside the selection, return:\n"
        "   [INSUFFICIENT_CONTEXT]\n"
        "10. If no useful modification is necessary or the code is already correct, return:\n"
        "   [NO_CHANGE]\n"
        "11. If a replacement is possible, return exactly:\n"
        "   [REPLACEMENT_CODE]\n"
        f"   {lang_str}\n"
        "12. The fenced block must contain ONLY replacement source code.\n"
        "13. Keep explanations, diagnostics, and reasoning OUTSIDE the code block.\n"
        "14. Do not include phrases like 'here is the complete code' or conversational text inside the code block.\n\n"
        "Always explain your reasoning in clear text outside the code block. Always include exactly one of the markers: [REPLACEMENT_CODE], [NO_CHANGE], or [INSUFFICIENT_CONTEXT]."
    )


def build_selection_prompt(
    code: str,
    lang_id: str = "",
    custom_prompt: str = "",
    surrounding_context: str = "",
    is_full_file: bool = False
) -> Tuple[str, str]:
    """
    Builds the user-visible prompt and the backend internal instruction.
    Returns (user_prompt, internal_instruction).
    """
    lang_tag = (lang_id or "").lower().strip()
    base_prompt = custom_prompt.strip() if custom_prompt and custom_prompt.strip() else f"Please review and improve the selected {lang_tag + ' ' if lang_tag else ''}code:"
    user_prompt = f"{base_prompt}\n\n```{lang_tag}\n{code}\n```"

    if surrounding_context and surrounding_context.strip() and surrounding_context.strip() != code.strip():
        user_prompt += f"\n\nSurrounding file context (FOR REASONING ONLY - DO NOT INCLUDE IN REPLACEMENT):\n```{lang_tag}\n{surrounding_context.strip()}\n```"

    internal_instr = build_selection_internal_instruction(is_full_file=is_full_file, lang_tag=lang_tag)
    return user_prompt, internal_instr


def sanitize_extracted_code(code: str) -> str:
    """Cleans marker artifacts or unescaped control tags from code blocks."""
    if not code:
        return ""
    cleaned = code.replace(REPL_MARKER, "").replace(NO_CHANGE_MARKER, "").replace(INSUFF_MARKER, "")
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

    has_repl = REPL_MARKER in response
    has_no_change = NO_CHANGE_MARKER in response
    has_insuff = INSUFF_MARKER in response

    # 1. REPLACEMENT_CODE
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

    # 2. NO_CHANGE
    if has_no_change:
        print(f"[AIReplacement] Parsed state: NO_CHANGE")
        print(f"[AIReplacement] Replacement lines: 0")
        print(f"[AIReplacement] Replacement chars: 0")
        print(f"[AIReplacement] Scope validation: PASS")
        print(f"[AIReplacement] Replacement applied: false")
        return {"status": "no_change", "code": None, "state": "NO_CHANGE"}

    # 3. INSUFFICIENT_CONTEXT
    if has_insuff:
        print(f"[AIReplacement] Parsed state: INSUFFICIENT_CONTEXT")
        print(f"[AIReplacement] Replacement lines: 0")
        print(f"[AIReplacement] Replacement chars: 0")
        print(f"[AIReplacement] Scope validation: PASS")
        print(f"[AIReplacement] Replacement applied: false")
        return {"status": "insufficient_context", "code": None, "state": "INSUFFICIENT_CONTEXT"}

    # 4. INVALID / UNSTRUCTURED
    print(f"[AIReplacement] Parsed state: INVALID")
    print(f"[AIReplacement] Replacement lines: 0")
    print(f"[AIReplacement] Replacement chars: 0")
    print(f"[AIReplacement] Scope validation: FAIL")
    print(f"[AIReplacement] Replacement applied: false")
    return {"status": "invalid", "code": None, "state": "INVALID"}
