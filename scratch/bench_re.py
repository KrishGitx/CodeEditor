import re, time
from PySide6.QtCore import QRegularExpression

pattern_str = r'(#.*)|("[^"]*"|\'[^\']*\')|(\b(?:def|class|return|import|from|if|else|elif|while|for|try|except|finally|with|as|pass|break|continue|yield|lambda|global|nonlocal|raise|assert|async|await|None|True|False|is|in|not|and|or)\b)|(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|(\b\d+(?:\.\d+)?\b)|(\b(?:self|cls|int|str|float|list|dict|set|tuple|bool|bytes)\b)|(@[A-Za-z0-9_]+)'

py_re = re.compile(pattern_str)
qt_re = QRegularExpression(pattern_str)

lines = [f'def sample_function_{i}(arg1, arg2):\n    val = {i} * 100\n    return "result_" + str(val)' for i in range(2500)]
full_text = '\n'.join(lines)
split_lines = full_text.split('\n')

t0 = time.perf_counter()
for line in split_lines:
    for m in py_re.finditer(line):
        s = m.start()
        l = m.end() - s
        g = m.lastindex
t1 = time.perf_counter()
print(f'Python compiled re.finditer on 7500 lines: {(t1 - t0)*1000:.2f} ms')

t0 = time.perf_counter()
for line in split_lines:
    it = qt_re.globalMatch(line)
    while it.hasNext():
        m = it.next()
        s = m.capturedStart()
        l = m.capturedLength()
t1 = time.perf_counter()
print(f'Qt QRegularExpression.globalMatch on 7500 lines: {(t1 - t0)*1000:.2f} ms')
