import re

kw = (
    r'\b(?:struct|class|union|enum|typedef|const|static|extern|register|volatile|inline|'
    r'virtual|override|public|private|protected|friend|namespace|using|template|typename|'
    r'new|delete|if|else|switch|case|default|while|do|for|break|continue|return|goto|'
    r'try|catch|throw|sizeof|decltype|constexpr|nullptr|this|package|import|interface|'
    r'extends|implements|abstract|final|finally|synchronized|native|transient|var|async|await)\b'
)
types = (
    r'\b(?:int|float|double|char|void|long|short|unsigned|signed|bool|string|String|auto|'
    r'std|vector|map|set|pair|unordered_map|unordered_set|queue|stack|'
    r'size_t|int8_t|int16_t|int32_t|int64_t|uint8_t|uint16_t|uint32_t|uint64_t|'
    r'cout|cin|endl|cerr|printf|scanf|malloc|free|memcpy|memset|NULL)\b'
)
pattern = (
    r'(//.*)|'
    r'("[^"]*"|\'[^\']*\')|'
    rf'({kw})|'
    r'(\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())|'
    r'(\b\d+(?:\.\d+)?[fFlLuU]?\b)|'
    rf'({types})|'
    r'(#[a-zA-Z_]\w*)'
)
regex = re.compile(pattern)

test_code = '''#include <string>
using namespace std;
int main() {
    cout << "Hello" << endl;
    vector<string> strs = {"aa", "ab"};
    int count, i = 0, j = strs.size() - 1, k = 0; // j == 1
    while (i != j) {
        if (lngstring[k] == strs[j][k]) {
            return 0;
        }
    }
}'''

names = [None, 'comment', 'string', 'keyword', 'function', 'number', 'type', 'preprocessor']

for line in test_code.splitlines():
    tokens = []
    for m in regex.finditer(line):
        tokens.append((m.group(0), names[m.lastindex]))
    print(f"{line[:40]:<40} -> {tokens}")

