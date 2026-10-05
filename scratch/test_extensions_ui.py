import os
import sys
import json
import shutil
import zipfile
import tempfile
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, r"c:\Users\amazi\OneDrive\Documents\DGX")

from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager

def run_tests():
    print("==================================================")
    print("   RUNNING EXTENSION & FORMATTER MANAGER TESTS    ")
    print("==================================================")
    
    ext_mgr = ExtensionManager()
    fmt_mgr = FormatterManager(ext_mgr)
    
    # Test 1: OS Detection
    os_name = ext_mgr.get_current_os()
    print(f"[TEST 1] Current OS detected: {os_name}")
    assert os_name in ["windows", "macos", "linux"], f"Invalid OS: {os_name}"
    
    # Test 2: Installed extensions discovery & schema
    exts = ext_mgr.get_installed_extensions()
    print(f"[TEST 2] Discovered {len(exts)} extensions:")
    for ext in exts:
        print(f"  - {ext.get('name')} v{ext.get('version')} ({ext.get('id')}): "
              f"Enabled={ext.get('enabled')}, Formatter={ext.get('formatter')}, "
              f"Installed={ext.get('formatterInstalled')}, Executable={ext.get('executable')}")
        assert "id" in ext
        assert "name" in ext
        assert "version" in ext
        assert "enabled" in ext
        assert "installCommand" in ext
        assert "formatterInstalled" in ext
        assert "location" in ext
    
    # Test 3: C++ Formatter Status & Missing message
    cpp_status = ext_mgr.check_formatter_status("cpp")
    print(f"[TEST 3] C++ Formatter Status: {cpp_status}")
    assert "installed" in cpp_status
    assert "executable" in cpp_status
    
    res = fmt_mgr.format_code("cpp", "test.cpp", "int main() { return 0; }")
    print(f"[TEST 3.1] Format C++ result message: {res.get('message')}")
    if not cpp_status["installed"]:
        assert res.get("available") is False
        assert "clang-format" in res.get("message")
        assert "not installed" in res.get("message")
        print("  -> Verified missing clang-format produces descriptive, actionable notification.")
    else:
        assert res.get("success") is True
        print("  -> clang-format is present and formatted code successfully.")

    # Test 4: Python Formatter Status
    py_status = ext_mgr.check_formatter_status("python")
    print(f"[TEST 4] Python Formatter Status: {py_status}")
    assert "installed" in py_status

    # Test 5: Enable / Disable Toggle Persistence
    test_ext_id = exts[0]["id"]
    print(f"[TEST 5] Testing toggle for extension {test_ext_id}...")
    ext_mgr.toggle_extension(test_ext_id, False)
    exts_after_disable = ext_mgr.get_installed_extensions()
    target = next((x for x in exts_after_disable if x["id"] == test_ext_id), None)
    assert target is not None and target["enabled"] is False, "Extension should be disabled"
    
    # Re-enable
    ext_mgr.toggle_extension(test_ext_id, True)
    exts_after_enable = ext_mgr.get_installed_extensions()
    target = next((x for x in exts_after_enable if x["id"] == test_ext_id), None)
    assert target is not None and target["enabled"] is True, "Extension should be enabled"
    print("  -> Toggle extension persistence verified.")

    # Test 6: Install from Folder
    temp_dir = tempfile.mkdtemp(prefix="dgx_ext_test_")
    try:
        dummy_manifest = {
            "id": "test.dummy_plugin",
            "name": "Dummy Test Plugin",
            "version": "1.2.3",
            "description": "A test dummy extension",
            "language": "dummy",
            "formatter": "dummy-fmt",
            "executable": "dummy-fmt",
            "installGuide": {
                "windows": "winget install dummy",
                "macos": "brew install dummy",
                "linux": "sudo apt install dummy"
            }
        }
        with open(os.path.join(temp_dir, "extension.json"), "w") as f:
            json.dump(dummy_manifest, f)

        res_folder = ext_mgr.install_local_extension(temp_dir)
        print(f"[TEST 6] Install from folder result: {res_folder}")
        assert res_folder is True, f"Failed to install from folder: {res_folder}"
        
        # Verify it appears in installed list
        installed = ext_mgr.get_installed_extensions()
        dummy_installed = next((x for x in installed if x["id"] == "test.dummy_plugin"), None)
        assert dummy_installed is not None, "Dummy extension should be listed in installed"
        assert dummy_installed["name"] == "Dummy Test Plugin"
        assert dummy_installed["isBuiltIn"] is False
        print("  -> Verified folder installation and discovery.")

        # Test 7: Uninstall Extension
        uninst_res = ext_mgr.uninstall_extension("test.dummy_plugin")
        print(f"[TEST 7] Uninstall result: {uninst_res}")
        assert uninst_res is True
        
        installed_after_uninst = ext_mgr.get_installed_extensions()
        assert not any(x["id"] == "test.dummy_plugin" for x in installed_after_uninst), "Extension should be removed"
        print("  -> Verified clean uninstall.")

        # Test 8: Install from .ZIP package
        zip_path = os.path.join(tempfile.gettempdir(), "dummy_ext.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("extension.json", json.dumps(dummy_manifest))
            zf.writestr("README.md", "# Dummy Extension")

        res_zip = ext_mgr.install_local_extension(zip_path)
        print(f"[TEST 8] Install from ZIP result: {res_zip}")
        assert res_zip is True, f"Failed to install from zip: {res_zip}"

        installed_from_zip = ext_mgr.get_installed_extensions()
        assert any(x["id"] == "test.dummy_plugin" for x in installed_from_zip)
        print("  -> Verified ZIP installation.")

        # Clean up installed extension
        ext_mgr.uninstall_extension("test.dummy_plugin")
        if os.path.exists(zip_path):
            os.remove(zip_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("==================================================")
    print("   ALL EXTENSION & FORMATTER TESTS PASSED!        ")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
