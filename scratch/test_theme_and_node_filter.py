import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json, tempfile, zipfile
from ExtensionManager import ExtensionManager
from SettingsBackend import SettingsBackend
import HighlighterEngine

def run_tests():
    em = ExtensionManager()
    sb = SettingsBackend()
    em.settings_backend = sb

    print("=== 1. Checking extension installation case-insensitivity ===")
    assert em.is_extension_installed("enBonnet.orange-ocean") == True, "enBonnet.orange-ocean should be installed"
    assert em.is_extension_installed("enbonnet.orange-ocean") == True, "enbonnet.orange-ocean should be installed"
    assert em.is_extension_installed("dgx.python") == True, "dgx.python should be installed"
    assert em.is_extension_installed("python") == True, "python should be installed"
    assert em.is_extension_installed("nonexistent.extension") == False
    print("PASS: Extension case-insensitivity check")

    print("=== 2. Checking available themes ===")
    themes = sb.get_available_themes()
    theme_ids = [t["id"] for t in themes]
    print("Available themes:", theme_ids)
    assert "orange_ocean" in theme_ids, "orange_ocean must be in available themes"
    orange_theme = next(t for t in themes if t["id"] == "orange_ocean")
    assert orange_theme["name"] == "Orange Ocean"
    print("PASS: Available themes check")

    print("=== 3. Checking HighlighterEngine theme loading ===")
    HighlighterEngine.reload_themes()
    assert "orange_ocean" in HighlighterEngine.THEMES, "orange_ocean must be in HighlighterEngine.THEMES"
    t_data = HighlighterEngine.THEMES["orange_ocean"]
    assert t_data.get("bgEditor") or t_data.get("background"), "theme data must contain background"
    print("PASS: HighlighterEngine check")

    print("=== 4. Checking Node.js extension filtering ===")
    fake_fd, fake_path = tempfile.mkstemp(suffix=".vsix")
    os.close(fake_fd)
    try:
        with zipfile.ZipFile(fake_path, "w") as z:
            z.writestr("extension/package.json", json.dumps({
                "name": "fake-node-tool",
                "publisher": "fake-publisher",
                "main": "./out/extension.js",
                "engines": {"vscode": "^1.80.0"}
            }))
            z.writestr("extension/out/extension.js", "console.log('hello');")

        res = em.install_local_extension(fake_path)
        assert res == False, "Pure Node.js extension must be rejected!"
        print("PASS: Node.js extension installation rejection check")
    finally:
        if os.path.exists(fake_path):
            os.remove(fake_path)

    print("=== 5. Checking theme data retrieval ===")
    theme_json_str = sb.get_theme_data("orange_ocean")
    theme_json = json.loads(theme_json_str)
    assert theme_json["id"] == "orange_ocean"
    assert "synKeyword" in theme_json
    assert "synString" in theme_json
    print("PASS: get_theme_data check")

    print("=== ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
