import os
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.abspath("."))
from ExtensionManager import ExtensionManager

url = "https://open-vsx.org/api/enBonnet/orange-ocean/0.0.4/file/enBonnet.orange-ocean-0.0.4.vsix"
temp_file = os.path.join(tempfile.gettempdir(), "test_orange_ocean.vsix")

req = urllib.request.Request(url, headers={"User-Agent": "PodStudio/1.0"})
with urllib.request.urlopen(req, timeout=20) as resp, open(temp_file, "wb") as f:
    f.write(resp.read())

print(f"Downloaded vsix, size: {os.path.getsize(temp_file)} bytes")

mgr = ExtensionManager(base_dir=os.path.abspath("."))
ok = mgr.install_local_extension(temp_file)
print(f"install_local_extension result: {ok}")

installed_dir = os.path.join(mgr.user_extensions_dir, "enBonnet_orange-ocean")
print(f"Target dir exists? {os.path.exists(installed_dir)}")
if os.path.exists(installed_dir):
    print("Files in target dir:", os.listdir(installed_dir))
    manifest_p = os.path.join(installed_dir, "extension.json")
    if os.path.exists(manifest_p):
        with open(manifest_p, "r", encoding="utf-8") as mf:
            print("extension.json contents:", mf.read()[:500])

if os.path.exists(temp_file):
    os.remove(temp_file)

