import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))
from SettingsBackend import SettingsBackend

sb = SettingsBackend()
print("Config dir:", sb.config_dir)
themes_dir = sb.config_dir / "themes"
themes_dir.mkdir(parents=True, exist_ok=True)
print("Themes dir:", themes_dir)
print("Available themes count before:", len(sb.get_available_themes()))
for t in sb.get_available_themes():
    print(" -", t["id"], t["name"])

