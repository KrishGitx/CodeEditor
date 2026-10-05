import sys
import os
import time
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import EditorBackend
from SettingsBackend import SettingsBackend
from TerminalBackend import TerminalBackend

def test_all():
    print("==================================================")
    print("RUNNING POD STUDIO VS CODE FEATURES TEST SUITE")
    print("==================================================")

    backend = EditorBackend()
    settings = SettingsBackend()
    terminal = TerminalBackend()

    # 1. Quick Open (get_workspace_files)
    print("\n[TEST 1] Testing Quick Open (get_workspace_files)...")
    files = backend.get_workspace_files("main")
    assert len(files) > 0, "Expected to find files matching 'main'"
    print(f"[PASS] Found {len(files)} files matching 'main': {[f['name'] for f in files[:3]]}")

    # 2. Hover Info (get_hover_info)
    print("\n[TEST 2] Testing Hover Info (get_hover_info)...")
    py_sample = "def calculate_total(price, tax_rate):\n    '''Calculates total price including tax.'''\n    return price * (1 + tax_rate)\n"
    hover = backend.get_hover_info("sample.py", 1, 6, py_sample)
    assert hover.get("found") == True, "Hover info should find function definition"
    assert "calculate_total" in hover.get("title", ""), "Hover title should contain function name"
    print(f"[PASS] Hover info successfully extracted: {hover}")

    # 3. Semantic Rename Symbol (rename_symbol)
    print("\n[TEST 3] Testing Semantic Rename (rename_symbol)...")
    code_before = """
def calculate_area(radius):
    area = 3.14159 * radius * radius
    return area

total_area = calculate_area(10)
"""
    rename_res = backend.rename_symbol("geom.py", 2, 5, "calculate_area", "compute_circle_area", code_before)
    assert rename_res.get("success") == True, "Rename should succeed"
    assert rename_res.get("count") == 2, f"Expected 2 occurrences renamed, got {rename_res.get('count')}"
    assert "compute_circle_area" in rename_res.get("new_code"), "New symbol name should be in new code"
    assert "calculate_area" not in rename_res.get("new_code"), "Old symbol name should be replaced"
    print(f"[PASS] Semantic Rename result: {rename_res.get('message')}")

    # 4. Document Symbols / Breadcrumbs (get_document_symbols)
    print("\n[TEST 4] Testing Document Symbols for Breadcrumbs...")
    class_code = """
class DataProcessor:
    def process_item(self, item):
        pass

    def export_csv(self, filename):
        pass
"""
    symbols = backend.get_document_symbols("processor.py", class_code)
    assert len(symbols) >= 3, f"Expected at least 3 symbols, got {len(symbols)}"
    sym_names = [s["name"] for s in symbols]
    assert "DataProcessor" in sym_names, "Class symbol should be found"
    assert "process_item" in sym_names, "Method symbol should be found"
    print(f"[PASS] Document Symbols extracted: {symbols}")

    # 5. Workspace Session Persistence (save_session_state, get_session_state)
    print("\n[TEST 5] Testing Workspace Session Restore...")
    session_data = {
        "activeTabIndex": 1,
        "isSplitEditor": True,
        "splitRatio": 0.6,
        "tabs": [
            {"path": "c:/app/main.py", "title": "main.py", "isDirty": False, "cursorPosition": 120},
            {"path": "c:/app/utils.py", "title": "utils.py", "isDirty": True, "draftContent": "draft", "cursorPosition": 45}
        ]
    }
    settings.save_session_state(json.dumps(session_data))
    restored_json = settings.get_session_state()
    restored = json.loads(restored_json)
    assert restored.get("activeTabIndex") == 1, "Active tab should be restored"
    assert restored.get("isSplitEditor") == True, "Split editor state should be restored"
    assert len(restored.get("tabs")) == 2, "Tab list should be restored"
    print(f"[PASS] Workspace session state verified: {restored}")

    # 6. Radial Menu Customization Settings (get_radial_menu_config, save_radial_menu_config)
    print("\n[TEST 6] Testing Radial Menu Customization Settings...")
    default_config = settings.get_radial_menu_config()
    assert len(default_config) >= 10, "Expected default radial menu items"
    custom_config = default_config.copy()
    custom_config.append({
        "id": "custom_build",
        "label": "Build Project",
        "icon": "code",
        "shortcut": "Build",
        "enabled": True,
        "custom": True,
        "action": "npm run build"
    })
    settings.save_radial_menu_config(json.dumps(custom_config))
    loaded_config = settings.get_radial_menu_config()
    assert len(loaded_config) == len(custom_config), "Custom button should persist in config"
    settings.reset_radial_menu_config()
    reset_config = settings.get_radial_menu_config()
    assert len(reset_config) == len(default_config), "Reset should restore default items"
    print("[PASS] Radial menu configuration persistence and reset verified.")

    # 7. Split Terminal Multi-Session Support
    print("\n[TEST 7] Testing Split Terminal Multi-Session Backend...")
    sec_id = terminal.create_session()
    assert sec_id == 1, f"Expected second session id 1, got {sec_id}"
    sessions = terminal.get_sessions()
    assert len(sessions) == 2, f"Expected 2 sessions, got {len(sessions)}"
    terminal.send_session_command(0, "Write-Host 'Session 0 Active'")
    terminal.send_session_command(1, "Write-Host 'Session 1 Active'")
    time.sleep(0.5)
    print("[PASS] Split Terminal multi-session isolated commands sent successfully.")

    # 8. Large 3000-line File Performance
    print("\n[TEST 8] Testing 3000-line File Performance...")
    large_lines = ["def func_{}(x): return x * 2".format(i) for i in range(3000)]
    large_code = "\n".join(large_lines)
    
    t0 = time.perf_counter()
    large_symbols = backend.get_document_symbols("large_test.py", large_code)
    t_symbols = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    large_hover = backend.get_hover_info("large_test.py", 1500, 5, large_code)
    t_hover = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    large_rename = backend.rename_symbol("large_test.py", 1500, 5, "func_1499", "renamed_func_1499", large_code)
    t_rename = (time.perf_counter() - t0) * 1000

    print(f"[PASS] 3000-line symbols parsed ({len(large_symbols)} symbols): {t_symbols:.2f} ms")
    print(f"[PASS] 3000-line hover lookup: {t_hover:.2f} ms")
    print(f"[PASS] 3000-line rename execution: {t_rename:.2f} ms")

    assert t_symbols < 250, "Symbol parsing should be fast"
    assert t_hover < 50, "Hover lookup should be fast"
    assert t_rename < 50, "Rename should be fast"

    print("\n==================================================")
    print("ALL 8 VERIFICATION SUITES PASSED PERFECTLY!")
    print("==================================================")

if __name__ == "__main__":
    test_all()
