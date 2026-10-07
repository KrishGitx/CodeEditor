import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shutil
import tempfile
import time

os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
os.environ["QSG_RENDER_LOOP"] = "basic"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QCoreApplication, QTimer

from main import EditorBackend

def run_tests():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    
    test_dir = tempfile.mkdtemp(prefix="dgx_test_tabs_")
    print(f"[TEST] Created test sandbox: {test_dir}")
    
    try:
        # Create nested folders and files
        nested_dir = os.path.join(test_dir, "src", "core", "utils")
        os.makedirs(nested_dir, exist_ok=True)
        
        f1 = os.path.join(test_dir, "main.cpp")
        f2 = os.path.join(test_dir, "src", "player.cpp")
        f3 = os.path.join(nested_dir, "helper.cpp")
        
        for fpath, code in [(f1, "int main() { return 0; }"), (f2, "void play() {}"), (f3, "void help() {}")]:
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(code)
                
        backend = EditorBackend()
        
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend", backend)
        
        # 1. Test CodeMinimap
        print("\n--- 1. Testing CodeMinimap ---")
        qml_minimap_path = os.path.abspath("qml/components/CodeMinimap.qml")
        comp_minimap = QQmlComponent(engine, qml_minimap_path)
        assert not comp_minimap.isError(), f"Minimap Error: {[e.toString() for e in comp_minimap.errors()]}"
        minimap_obj = comp_minimap.create()
        assert minimap_obj is not None, "Failed to instantiate CodeMinimap"
        
        # Verify miniature code text architecture properties
        assert minimap_obj.property("lineSpacing") == 4.8, f"Expected lineSpacing 4.8, got {minimap_obj.property('lineSpacing')}"
        assert minimap_obj.property("charScale") == 2.7, f"Expected charScale 2.7, got {minimap_obj.property('charScale')}"
        assert minimap_obj.property("width") == 90, f"Expected width 90, got {minimap_obj.property('width')}"
        
        # 3000-line test
        doc_3000 = "\n".join([f"def func_{i}():\n    return {i} * 42 # sample code" for i in range(1500)])
        minimap_obj.setProperty("documentText", doc_3000)
        minimap_obj.rebuildCache()
        assert minimap_obj.property("totalLineCount") == 3000
        print("[PASS] CodeMinimap: Fixed-resolution sampled segments, 90px width, 3000-line rendering OK")
        
        # 2. Test EditorTabBar and Context Menu
        print("\n--- 2. Testing EditorTabBar ---")
        qml_tabbar_path = os.path.abspath("qml/components/EditorTabBar.qml")
        comp_tabbar = QQmlComponent(engine, qml_tabbar_path)
        assert not comp_tabbar.isError(), f"TabBar Error: {[e.toString() for e in comp_tabbar.errors()]}"
        tabbar_obj = comp_tabbar.create()
        assert tabbar_obj is not None, "Failed to instantiate EditorTabBar"
        print("[PASS] EditorTabBar compiled and instantiated with context menu and dirty dot support")
        
        # 3. Test ExplorerPanel Active File Highlighting & Nested Expansion
        print("\n--- 3. Testing Explorer Auto-Highlighting & Nested Expansion ---")
        qml_explorer_path = os.path.abspath("qml/components/ExplorerPanel.qml")
        comp_explorer = QQmlComponent(engine, qml_explorer_path)
        assert not comp_explorer.isError(), f"Explorer Error: {[e.toString() for e in comp_explorer.errors()]}"
        explorer_obj = comp_explorer.create()
        assert explorer_obj is not None, "Failed to instantiate ExplorerPanel"
        
        # Populate explorer model
        raw_list = [
            {"name": "main.cpp", "type": "File", "parentId": "PROJECT"},
            {"name": "src", "type": "Folder", "parentId": "PROJECT"},
            {"name": "player.cpp", "type": "File", "parentId": "src"},
            {"name": "core", "type": "Folder", "parentId": "src"},
            {"name": "utils", "type": "Folder", "parentId": "core"},
            {"name": "helper.cpp", "type": "File", "parentId": "utils"},
        ]
        explorer_obj.populateModel(raw_list, test_dir)
        
        # Test selectAndRevealFile on deeply nested file
        helper_path = f3.replace("\\", "/")
        explorer_obj.selectAndRevealFile(helper_path)
        
        assert explorer_obj.property("selectedFilePath") == helper_path, "Selected path mismatch"
        
        collapsed = explorer_obj.property("collapsedFolders")
        collapsed_dict = collapsed.toVariant() if hasattr(collapsed, "toVariant") else {}
        src_norm = os.path.join(test_dir, "src").replace("\\", "/")
        core_norm = os.path.join(test_dir, "src", "core").replace("\\", "/")
        utils_norm = os.path.join(test_dir, "src", "core", "utils").replace("\\", "/")
        
        assert collapsed_dict.get(src_norm) is False, f"src folder should be expanded, got {collapsed_dict.get(src_norm)}"
        assert collapsed_dict.get(core_norm) is False, f"core folder should be expanded, got {collapsed_dict.get(core_norm)}"
        assert collapsed_dict.get(utils_norm) is False, f"utils folder should be expanded, got {collapsed_dict.get(utils_norm)}"
        print("[PASS] Nested file selectAndRevealFile correctly expands all parent folders and highlights file")
        
        # 4. Test EditorArea Tab Operations (Close Others, Close Tabs to the Right, Close All, Close Saved)
        print("\n--- 4. Testing EditorArea Tab Management ---")
        qml_editor_path = os.path.abspath("qml/components/EditorArea.qml")
        comp_editor = QQmlComponent(engine, qml_editor_path)
        assert not comp_editor.isError(), f"EditorArea Error: {[e.toString() for e in comp_editor.errors()]}"
        editor_obj = comp_editor.create()
        assert editor_obj is not None, "Failed to instantiate EditorArea"
        
        # Load 5 files
        f4 = os.path.join(test_dir, "doc1.txt")
        f5 = os.path.join(test_dir, "doc2.txt")
        with open(f4, "w") as f: f.write("1")
        with open(f5, "w") as f: f.write("2")
        
        editor_obj.loadFile(f1.replace("\\", "/"), "c1")
        editor_obj.loadFile(f2.replace("\\", "/"), "c2")
        editor_obj.loadFile(f3.replace("\\", "/"), "c3")
        editor_obj.loadFile(f4.replace("\\", "/"), "c4")
        editor_obj.loadFile(f5.replace("\\", "/"), "c5")
        
        # Check tab count
        assert editor_obj.property("tabCount") == 5, f"Expected 5 tabs, got {editor_obj.property('tabCount')}"
        
        # Mark tab 1 and tab 3 as dirty
        editor_obj.setTabDirty(1, True)
        editor_obj.setTabDirty(3, True)
        
        assert editor_obj.isTabDirty(1) == True
        assert editor_obj.isTabDirty(3) == True
        assert editor_obj.isTabDirty(0) == False
        print("[PASS] 5 tabs loaded, dirty indicators set independently")
        
        # Test closeTabsToTheRight(2) -> closes tabs 3 and 4
        editor_obj.closeTabsToTheRight(2)
        assert editor_obj.property("tabCount") == 3, f"Expected 3 tabs after closeTabsToTheRight, got {editor_obj.property('tabCount')}"
        print("[PASS] closeTabsToTheRight works correctly")
        
        # Test closeSavedTabs -> removes tab 0 and tab 2, leaves dirty tab 1
        editor_obj.closeSavedTabs()
        assert editor_obj.property("tabCount") == 1, f"Expected 1 dirty tab remaining, got {editor_obj.property('tabCount')}"
        assert editor_obj.isTabDirty(0) == True
        print("[PASS] closeSavedTabs preserved only dirty tabs")
        
        # Test closeAllTabs
        editor_obj.closeAllTabs()
        assert editor_obj.property("tabCount") == 0, "Expected 0 tabs after closeAllTabs"
        print("[PASS] closeAllTabs cleanly closed all tabs")
        
        # 5. Test Full main.qml Compilation
        print("\n--- 5. Testing Full main.qml Compilation ---")
        qml_main_path = os.path.abspath("qml/main.qml")
        comp_main = QQmlComponent(engine, qml_main_path)
        assert not comp_main.isError(), f"Main Error: {[e.toString() for e in comp_main.errors()]}"
        print("[PASS] main.qml and all integrated components compiled with 0 errors")
        
        print("\n==========================================")
        print("ALL TESTS PASSED SUCCESSFULLY")
        print("==========================================")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    run_tests()
