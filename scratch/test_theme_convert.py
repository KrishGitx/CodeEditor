import json
import os
import re

theme_file = r"C:\Users\amazi\.dgx\extensions\enbonnet_orange-ocean\theme\orange-ocean-theme.json"
with open(theme_file, "r", encoding="utf-8") as f:
    text = f.read()

# Strip comments if any
clean_text = re.sub(r'//.*', '', text)
data = json.loads(clean_text)

print("Theme name:", data.get("name"))
print("Colors keys count:", len(data.get("colors", {})))
print("tokenColors count:", len(data.get("tokenColors", [])))
print("Sample colors:")
for k, v in list(data.get("colors", {}).items())[:10]:
    print(f"  {k}: {v}")

