import re

fence_regex = re.compile(r"(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,}|\Z)")

text1 = """```browser.new_context(
browser.new_context(
        locale="en-US",
)
```"""

m = fence_regex.search(text1)
print("text1 G1:", repr(m.group(1)))
print("text1 G2:", repr(m.group(2)))

text2 = """```python
browser.new_context(
browser.new_context(
        locale="en-US",
)
```"""

m2 = fence_regex.search(text2)
print("text2 G1:", repr(m2.group(1)))
print("text2 G2:", repr(m2.group(2)))
