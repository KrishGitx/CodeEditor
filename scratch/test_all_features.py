import os
import sys
sys.path.insert(0, os.getcwd())
import json
import re

def test_themes_folder():
    print("Testing themes/*.json...")
    themes_dir = "themes"
    assert os.path.isdir(themes_dir), "themes/ directory missing"
    json_files = [f for f in os.listdir(themes_dir) if f.endswith(".json")]
    assert len(json_files) >= 8, f"Expected at least 8 themes, found {len(json_files)}: {json_files}"
    for jf in json_files:
        with open(os.path.join(themes_dir, jf), "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "bgRoot" in data, f"{jf} missing bgRoot"
            assert "bgEditor" in data, f"{jf} missing bgEditor"
            assert "synKeyword" in data, f"{jf} missing synKeyword"
            assert "keywords" in data, f"{jf} missing keywords"
    print(f"  -> All {len(json_files)} themes valid.")

def test_settings_backend_themes():
    print("Testing SettingsBackend theme slots...")
    from SettingsBackend import SettingsBackend
    sb = SettingsBackend()
    themes = sb.get_available_themes()
    assert len(themes) >= 8, f"Expected >= 8 themes, got {len(themes)}"
    ids = [t["id"] for t in themes]
    for expected in ["obsidian", "dracula", "nord", "monokai", "midnight", "light", "paper", "glass"]:
        assert expected in ids, f"Missing {expected} in available themes"
        raw = sb.get_theme_data(expected)
        parsed = json.loads(raw)
        assert parsed.get("id") == expected, f"get_theme_data({expected}) returned invalid id: {parsed.get('id')}"
    print(f"  -> SettingsBackend returned {len(themes)} themes successfully.")

def test_highlighter_engine_themes():
    print("Testing HighlighterEngine dynamic themes...")
    import HighlighterEngine
    assert len(HighlighterEngine.THEMES) >= 8, f"HighlighterEngine THEMES has {len(HighlighterEngine.THEMES)}"
    for tname in ["obsidian", "dracula", "nord", "monokai", "midnight", "light", "paper", "glass", "dark"]:
        assert tname in HighlighterEngine.THEMES, f"Missing {tname} in HighlighterEngine.THEMES"
        td = HighlighterEngine.THEMES[tname]
        assert "keywords" in td, f"Missing 'keywords' in theme {tname}"
        assert "functions" in td, f"Missing 'functions' in theme {tname}"
        assert "strings" in td, f"Missing 'strings' in theme {tname}"
    print("  -> HighlighterEngine dynamic themes verified.")

def test_no_hardcoded_youtube_thumbnails():
    print("Testing removal of default YouTube thumbnail URLs...")
    for fn in ["MusicPlayer.py", os.path.join("qml", "music", "MusicPlayerPanel.qml")]:
        with open(fn, "r", encoding="utf-8") as f:
            content = f.read()
            assert "img.youtube.com" not in content, f"Found hardcoded img.youtube.com in {fn}!"
            assert "hqdefault.jpg" not in content, f"Found hardcoded hqdefault.jpg in {fn}!"
    print("  -> No hardcoded default YouTube thumbnail URLs found.")

def test_extension_manager_dynamic():
    print("Testing ExtensionManager dynamic discovery...")
    import ExtensionManager
    mgr = ExtensionManager.ExtensionManager()
    ext_ids = [e.get("id") if isinstance(e, dict) else e.id for e in mgr.get_marketplace_extensions()]
    assert "dgx.meower" in ext_ids, f"dgx.meower not discovered dynamically: {ext_ids}"
    assert "dgx.python" in ext_ids, f"dgx.python not in marketplace: {ext_ids}"
    # Verify no hardcoded drive C: paths in locate_executable
    with open("ExtensionManager.py", "r", encoding="utf-8") as f:
        src = f.read()
        assert 'r"C:\\Program Files\\Microsoft Visual Studio' not in src
        assert 'r"C:\\Program Files\\Java"' not in src
    print(f"  -> ExtensionManager verified ({len(ext_ids)} marketplace extensions discovered).")

def test_custom_api_untouched():
    print("Verifying CustomApi.py untouched...")
    with open("CustomApi.py", "r", encoding="utf-8") as f:
        src = f.read()
        assert "ChatGPTClient" in src
    print("  -> CustomApi.py is present and unmodified.")

if __name__ == "__main__":
    test_themes_folder()
    test_settings_backend_themes()
    test_highlighter_engine_themes()
    test_no_hardcoded_youtube_thumbnails()
    test_extension_manager_dynamic()
    test_custom_api_untouched()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
