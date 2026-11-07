import sys
import os
import json
from pathlib import Path
from PySide6.QtCore import QCoreApplication

def test_per_project_workspace_persistence():
    print("=== Testing Per-Project Workspace Persistence ===")
    from SettingsBackend import SettingsBackend
    sb = SettingsBackend()

    proj_a = r"C:\fake\path\to\ProjectA"
    session_a = json.dumps({
        "activeTabIndex": 1,
        "tabs": [
            {"path": r"C:\fake\path\to\ProjectA\main.py", "title": "main.py"},
            {"path": r"C:\fake\path\to\ProjectA\utils.py", "title": "utils.py"}
        ]
    })

    proj_b = r"C:\fake\path\to\ProjectB"
    session_b = json.dumps({
        "activeTabIndex": 0,
        "tabs": [
            {"path": r"C:\fake\path\to\ProjectB\index.js", "title": "index.js"}
        ]
    })

    sb.save_project_session(proj_a, session_a)
    sb.save_project_session(proj_b, session_b)

    retrieved_a = json.loads(sb.get_project_session(proj_a))
    retrieved_b = json.loads(sb.get_project_session(proj_b))

    assert retrieved_a["activeTabIndex"] == 1, f"Expected activeTabIndex 1, got {retrieved_a.get('activeTabIndex')}"
    assert len(retrieved_a["tabs"]) == 2, f"Expected 2 tabs for Project A, got {len(retrieved_a.get('tabs', []))}"
    assert retrieved_b["activeTabIndex"] == 0, f"Expected activeTabIndex 0, got {retrieved_b.get('activeTabIndex')}"
    assert len(retrieved_b["tabs"]) == 1, f"Expected 1 tab for Project B, got {len(retrieved_b.get('tabs', []))}"
    print("[PASS] Per-Project Workspace Sessions persist and load cleanly!")


def test_icon_theme_support():
    print("=== Testing File & Folder Icon Theme Support ===")
    from ExtensionManager import ExtensionManager
    em = ExtensionManager()

    avail = em.get_available_icon_themes()
    print("Available Icon Themes count:", len(avail))
    theme_ids = [t["id"] for t in avail]
    assert "none" in theme_ids, "Expected 'none' (Minimalist) in available themes"
    assert "icons" in theme_ids, "Expected 'icons' (from yusifaliyevpro.vscicons) in available themes"

    # Activate VSC Icons
    ok = em.set_active_icon_theme("icons")
    assert ok, "Failed to set active icon theme to 'icons'"
    assert em.get_active_icon_theme() == "icons"

    py_icon = em.get_file_icon("main.py")
    assert py_icon.endswith("python.svg"), f"Expected python.svg, got {py_icon}"

    pkg_icon = em.get_file_icon("package.json")
    assert pkg_icon.endswith("nodejs.svg"), f"Expected nodejs.svg, got {pkg_icon}"

    src_closed = em.get_folder_icon("src", True)
    assert src_closed.endswith("folder_src.svg"), f"Expected folder_src.svg, got {src_closed}"

    src_open = em.get_folder_icon("src", False)
    assert src_open.endswith("folder_src_open.svg"), f"Expected folder_src_open.svg, got {src_open}"

    # Test 'none' (minimalist vector fallback)
    em.set_active_icon_theme("none")
    assert em.get_file_icon("main.py") == "", "Expected empty string when theme is 'none'"
    assert em.get_folder_icon("src", True) == "", "Expected empty string when theme is 'none'"

    # Switch back to 'icons'
    em.set_active_icon_theme("icons")
    assert em.get_active_icon_theme() == "icons"
    print("[PASS] Icon theme resolution and switching work flawlessly!")


def test_activity_bar_and_vector_icons():
    print("=== Testing Activity Bar and VectorIcon Stroke Width ===")
    v_path = Path("qml/components/VectorIcon.qml").read_text(encoding="utf-8")
    assert "property real strokeWidth: -1" in v_path, "VectorIcon missing strokeWidth property"
    assert "Math.max(1.0, width / 18.0)" in v_path, "VectorIcon default stroke width not set to sleek thin 1.1px"

    a_path = Path("qml/components/ActivityBar.qml").read_text(encoding="utf-8")
    assert "strokeWidth: 1.1" in a_path, "ActivityBar missing strokeWidth: 1.1"
    print("[PASS] Activity Bar and VectorIcon are sleek and thin (strokeWidth 1.1)!")


if __name__ == "__main__":
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    test_per_project_workspace_persistence()
    test_icon_theme_support()
    test_activity_bar_and_vector_icons()
    print("\nALL RECENT PROJECT AND ICON THEME TESTS PASSED SUCCESSFULLY!")

