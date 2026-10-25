import re

SHELL_LABELS = {
    'powershell', 'pwsh', 'cmd', 'batch', 'bat', 'bash', 'sh', 'zsh', 'shell', 'terminal', 'console'
}

def normalize_command(cmd: str) -> str:
    if not cmd:
        return ""
    # Strip comments, extra whitespace, lower-case for comparison
    lines = [l.strip() for l in cmd.strip().splitlines() if l.strip() and not l.strip().startswith(("#", "//", "REM ", "rem "))]
    single = " ".join(" ".join(lines).split())
    return single.lower()

def parse_post_install_ai_response(response_text: str):
    if not response_text or not response_text.strip():
        return "INVALID", "", "Empty AI response"

    text = response_text.strip()
    if text.lower().startswith("chatgpt said:"):
        text = text[13:].strip()

    # Check for [FIX] command
    fix_match = re.search(r'\[FIX\]\s*(.*)', text, re.IGNORECASE | re.DOTALL)
    if fix_match:
        pre_fix = text[:fix_match.start()].strip()
        after_fix = fix_match.group(1).strip()

        # Check for fenced code block
        fence_regex = re.compile(r'(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,}|\Z)')
        fence_match = fence_regex.search(after_fix)

        fix_cmd = ""
        post_explanation = ""

        if fence_match and fence_match.group(2) and fence_match.group(2).strip():
            code_inside = fence_match.group(2).strip()
            cmd_lines = [l.strip() for l in code_inside.splitlines() if l.strip() and not l.strip().startswith(("#", "//", "REM ", "rem "))]
            candidate_cmd = "\n".join(cmd_lines).strip()

            text_before_fence = after_fix[:fence_match.start()].strip()
            if text_before_fence.lower() in SHELL_LABELS:
                text_before_fence = ""

            text_after_fence = after_fix[fence_match.end():].strip()
            explanation_parts = [p for p in (pre_fix, text_before_fence, text_after_fence) if p]
            post_explanation = "\n\n".join(explanation_parts)

            if candidate_cmd:
                fix_cmd = candidate_cmd
        else:
            lines = after_fix.splitlines()
            first_line = lines[0].strip() if lines else ""
            if first_line.lower() in SHELL_LABELS:
                rem_lines = [l.strip() for l in lines[1:] if l.strip()]
                if rem_lines:
                    fix_cmd = rem_lines[0].strip("`").strip()
                    post_explanation = "\n".join(rem_lines[1:]).strip() if len(rem_lines) > 1 else ""
                else:
                    fix_cmd = ""
                    post_explanation = first_line
            else:
                fix_cmd = first_line.strip("`").strip()
                post_explanation = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

            explanation_parts = [p for p in (pre_fix, post_explanation) if p]
            post_explanation = "\n\n".join(explanation_parts)

        split_m = re.search(r'(?i)(Root\s*cause|Explanation|Reason|Note)\s*:\s*', fix_cmd)
        if split_m and split_m.start(1) > 0:
            split_idx = split_m.start(1)
            extra_exp = fix_cmd[split_idx:].strip()
            fix_cmd = fix_cmd[:split_idx].strip()
            post_explanation = (extra_exp + "\n" + post_explanation).strip()

        if not fix_cmd or fix_cmd.lower() in SHELL_LABELS:
            return "INVALID", "", post_explanation or text

        explanation = post_explanation or text
        return "FIX", fix_cmd, explanation

    # Check for MANUAL_INSTALLATION_REQUIRED
    if re.search(r'\bMANUAL_INSTALLATION_REQUIRED\b', text, re.IGNORECASE):
        return "MANUAL_INSTALLATION_REQUIRED", "", text

    # Check for SUCCESS
    first_word = text.split()[0].upper() if text.split() else ""
    if first_word == "SUCCESS" or re.search(r'^\s*SUCCESS\b', text, re.MULTILINE):
        return "SUCCESS", "", text

    # Check for FAILED
    if first_word == "FAILED" or re.search(r'^\s*FAILED\b', text, re.MULTILINE):
        return "FAILED", "", text

    return "INVALID", "", text

# Test 1: exact logged response
t1 = """[FIX]powershell
```powershell
winget install --id Microsoft.OpenJDK.21 --exact
```

Root cause: google-java-format 1.35.0 requires JDK 21 or newer...
"""
s1, c1, e1 = parse_post_install_ai_response(t1)
assert s1 == "FIX" and c1 == "winget install --id Microsoft.OpenJDK.21 --exact"
assert "google-java-format 1.35.0" in e1

# Test 2: bash label
t2 = """[FIX]bash
```bash
sudo apt-get install -y openjdk-21-jdk
```
Diagnosis: Java runtime outdated.
"""
s2, c2, e2 = parse_post_install_ai_response(t2)
assert s2 == "FIX" and c2 == "sudo apt-get install -y openjdk-21-jdk"
assert "Java runtime outdated" in e2

# Test 3: cmd label
t3 = """[FIX]cmd
```cmd
winget install --id Microsoft.OpenJDK.21 --exact
```
"""
s3, c3, e3 = parse_post_install_ai_response(t3)
assert s3 == "FIX" and c3 == "winget install --id Microsoft.OpenJDK.21 --exact"

# Test 4: inline command without code fence
t4 = """[FIX] winget install --id Microsoft.OpenJDK.21 --exact
Please run this in an elevated prompt.
"""
s4, c4, e4 = parse_post_install_ai_response(t4)
assert s4 == "FIX" and c4 == "winget install --id Microsoft.OpenJDK.21 --exact"

# Test 5: bare shell label with no command -> INVALID
t5 = """[FIX]powershell"""
s5, c5, e5 = parse_post_install_ai_response(t5)
assert s5 == "INVALID" and c5 == ""

# Test 6: empty fenced block -> INVALID
t6 = """[FIX]
```powershell
```
"""
s6, c6, e6 = parse_post_install_ai_response(t6)
assert s6 == "INVALID" and c6 == ""

# Test 7: command normalization for repeated command detection
cmd_a = "winget install --id Microsoft.OpenJDK.21 --exact"
cmd_b = "  winget   install   --id   Microsoft.OpenJDK.21   --exact  \n"
assert normalize_command(cmd_a) == normalize_command(cmd_b)
assert normalize_command("powershell") != normalize_command(cmd_a)

# Test 8: AI emits command and Root cause without a newline
t8 = """[FIX]
winget install --id Microsoft.OpenJDK.21 --exact --accept-package-agreementsRoot cause: google-java-format 1.35.0 requires JDK 21
"""
s8, c8, e8 = parse_post_install_ai_response(t8)
assert s8 == "FIX"
assert c8 == "winget install --id Microsoft.OpenJDK.21 --exact --accept-package-agreements", f"Got: {c8}"
assert "Root cause: google-java-format 1.35.0 requires JDK 21" in e8

print("ALL 8 PARSER TESTS PASSED!")
