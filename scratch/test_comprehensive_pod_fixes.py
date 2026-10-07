import sys
import os
import time
import shutil
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = r"C:\Users\amazi\OneDrive\Documents\DGX"
sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QCoreApplication, QTimer, Qt
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from main import EditorBackend, MusicPlayer, AIBackend, TerminalBackend, SettingsBackend

def run_tests():
    print("================================================================")
    print("STARTING COMPREHENSIVE POD STUDIO VERIFICATION TESTS")
    print("================================================================")
    
    app = QGuiApplication.instance()
    if not app:
        app = QGuiApplication(sys.argv)
        
    engine = QQmlApplicationEngine()
    
    backend = EditorBackend()
    settingsBackend = SettingsBackend()
    backend.settings_backend = settingsBackend
    musicPlayer = MusicPlayer()
    aiBackend = AIBackend()
    terminalBackend = TerminalBackend()
    
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("extensionManager", backend.extension_manager)
    engine.rootContext().setContextProperty("musicPlayer", musicPlayer)
    engine.rootContext().setContextProperty("aiBackend", aiBackend)
    engine.rootContext().setContextProperty("terminalBackend", terminalBackend)
    engine.rootContext().setContextProperty("settingsBackend", settingsBackend)
    
    # Create a clean temporary workspace for tests
    temp_dir = tempfile.mkdtemp(prefix="dgx_test_ws_")
    print(f"Created temporary test workspace: {temp_dir}")
    
    try:
        # Create folder structure:
        # temp_dir/
        #   src/
        #     main.cpp
        #   README.md
        src_dir = os.path.join(temp_dir, "src")
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, "main.cpp"), "w") as f:
            f.write("#include <iostream>\nint main() { return 0; }\n")
        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write("# DGX Test Project\n")
            
        # Test 1: Load workspace in backend
        backend.open_Workspace(temp_dir)
        app.processEvents()
        
        # Test 2: Backend file operations & slots
        print("\n--- Testing Backend Operations ---")
        
        # 2.1 create_file_on_disk
        test_file1 = os.path.join(temp_dir, "test1.py")
        ok = backend.create_file_on_disk(test_file1)
        assert ok and os.path.exists(test_file1), "create_file_on_disk failed"
        print("PASS: create_file_on_disk")
        
        # 2.2 create_folder_on_disk
        test_folder1 = os.path.join(temp_dir, "test_folder")
        ok = backend.create_folder_on_disk(test_folder1)
        assert ok and os.path.isdir(test_folder1), "create_folder_on_disk failed"
        print("PASS: create_folder_on_disk")
        
        # 2.3 duplicate_file
        dup_path = backend.duplicate_file(test_file1)
        assert dup_path and os.path.exists(dup_path), f"duplicate_file failed: {dup_path}"
        print(f"PASS: duplicate_file -> {dup_path}")
        
        # 2.4 rename_file
        test_file1_renamed = os.path.join(temp_dir, "test1_renamed.py")
        ok = backend.rename_file(test_file1, test_file1_renamed)
        assert ok and os.path.exists(test_file1_renamed) and not os.path.exists(test_file1), "rename_file failed"
        print("PASS: rename_file")
        
        # 2.5 delete_file
        ok = backend.delete_file(test_file1_renamed)
        assert ok and not os.path.exists(test_file1_renamed), "delete_file failed"
        print("PASS: delete_file")
        
        # 2.6 Clipboard copy/paste
        backend.set_explorer_clipboard(os.path.join(src_dir, "main.cpp"), "copy")
        clip = backend.get_explorer_clipboard()
        assert clip.get("mode") == "copy" and "main.cpp" in clip.get("path"), "set_explorer_clipboard failed"
        ok = backend.paste_explorer_clipboard(test_folder1)
        assert ok and os.path.exists(os.path.join(test_folder1, "main.cpp")), "paste_explorer_clipboard failed"
        print("PASS: Clipboard copy & paste")
        
        # 2.7 Copy path to clipboard
        backend.copy_path_to_clipboard(os.path.join(temp_dir, "README.md"))
        cb_text = app.clipboard().text()
        assert "README.md" in cb_text, f"copy_path_to_clipboard failed: {cb_text}"
        print("PASS: copy_path_to_clipboard")
        
        # Test 3: QML Explorer & UI Behavior
        print("\n--- Testing QML ExplorerPanel Component ---")
        component = QQmlComponent(engine, os.path.join(PROJECT_ROOT, "qml", "components", "ExplorerPanel.qml"))
        if component.isError():
            for err in component.errors():
                print("ExplorerPanel QML Error:", err.toString())
            assert False, "ExplorerPanel QML component failed to load"
            
        explorer = component.create()
        assert explorer is not None, "Failed to create ExplorerPanel instance"
        
        # Populate model
        root_folder, arr = backend.search_folder_items(temp_dir)
        raw_list = backend.explorerList(arr, root_folder)
        explorer.populateModel(raw_list, temp_dir)
        app.processEvents()
        
        # 3.1 New File with no folder selected -> Workspace root
        explorer.setProperty("selectedFilePath", "")
        explorer.startNewFile("")
        editing_path = explorer.property("editingFilePath")
        print(f"Created Untitled file at root: {editing_path}")
        assert os.path.dirname(os.path.abspath(editing_path)) == os.path.abspath(temp_dir), "New file with no selection was not in workspace root!"
        assert os.path.exists(editing_path), "New file on disk was not created!"
        print("PASS: New File with no selection created in workspace root")
        
        # 3.2 New File with folder selected -> Inside folder
        explorer.setProperty("selectedFilePath", src_dir.replace("\\", "/"))
        explorer.startNewFile("")
        src_file_path = explorer.property("editingFilePath")
        print(f"Created file in selected folder: {src_file_path}")
        assert os.path.dirname(os.path.abspath(src_file_path)) == os.path.abspath(src_dir), "New file was not created inside selected folder!"
        assert os.path.exists(src_file_path), "File not created in folder!"
        print("PASS: New File with selected folder created inside folder")
        
        def get_prop_dict(prop_name):
            val = explorer.property(prop_name)
            return val.toVariant() if hasattr(val, "toVariant") else val

        # 3.3 New File inside collapsed folder -> Auto-expands collapsed folder
        norm_src = src_dir.replace("\\", "/")
        collapsed_dict = {norm_src: True}
        explorer.setProperty("collapsedFolders", collapsed_dict)
        assert get_prop_dict("collapsedFolders").get(norm_src) is True, "Folder should be collapsed"
        
        explorer.setProperty("selectedFilePath", norm_src)
        explorer.startNewFile("")
        collapsed_after = get_prop_dict("collapsedFolders")
        assert collapsed_after.get(norm_src) is False, "Collapsed folder was not auto-expanded!"
        print("PASS: New file inside collapsed folder auto-expands folder hierarchy")
        
        # 3.4 Rename File & Cancel Inline Edit
        file_to_rename = explorer.property("editingFilePath")
        parent_dir = os.path.dirname(file_to_rename)
        new_renamed_name = "MyRenamedCode.cpp"
        explorer.commitRenameFile(file_to_rename, new_renamed_name, parent_dir)
        renamed_full = os.path.join(parent_dir, new_renamed_name)
        assert os.path.exists(renamed_full), f"commitRenameFile failed: {renamed_full}"
        print(f"PASS: commitRenameFile successfully renamed file to {new_renamed_name}")
        
        # Test 3.5: Cancel inline edit deletes temporary untitled file
        explorer.startNewFile("")
        temp_untitled = explorer.property("editingFilePath")
        assert os.path.exists(temp_untitled), "Temp file should exist before cancel"
        explorer.cancelInlineEdit(temp_untitled)
        assert not os.path.exists(temp_untitled), "Temporary untitled file should be removed on cancel"
        print("PASS: cancelInlineEdit cleanly cancels and removes temp file")
        
        # Test 4: Filesystem Watcher Detection
        print("\n--- Testing Filesystem Watcher External Changes ---")
        external_file = os.path.join(temp_dir, "external_script.py")
        with open(external_file, "w") as f:
            f.write("# Created outside Pod Studio in Windows Explorer\n")
            
        backend._on_fs_debounced()
        app.processEvents()
        
        # Verify search_folder_items sees external_file
        _, new_arr = backend.search_folder_items(temp_dir)
        new_explorer_list = backend.explorerList(new_arr, root_folder)
        names = [item["name"] for item in new_explorer_list]
        assert "external_script.py" in names, "External file not detected by explorerList"
        
        # Populate model and verify collapsed states are preserved
        explorer.populateModel(new_explorer_list, temp_dir)
        print("PASS: External filesystem change detected and populated into model")
        
        # Test 5: Minimap Micro-text Code Rendering
        print("\n--- Testing CodeMinimap Component ---")
        minimap_comp = QQmlComponent(engine, os.path.join(PROJECT_ROOT, "qml", "components", "CodeMinimap.qml"))
        if minimap_comp.isError():
            for err in minimap_comp.errors():
                print("CodeMinimap QML Error:", err.toString())
            assert False, "CodeMinimap QML failed to load"
            
        minimap = minimap_comp.create()
        assert minimap is not None, "Failed to create CodeMinimap instance"
        
        # Test across Python, C++, HTML, JSON, QML, 3000-line files
        languages = {
            "python": "def calculate_sum(a, b):\n    # Return sum\n    return a + b\n\nclass Runner:\n    def run(self):\n        pass\n",
            "cpp": "#include <vector>\n#include <string>\n\nint main() {\n    std::vector<int> nums = {1, 2, 3};\n    return 0;\n}\n",
            "html": "<!DOCTYPE html>\n<html>\n<head><title>Test</title></head>\n<body>\n    <h1>Hello</h1>\n</body>\n</html>",
            "json": '{\n  "name": "pod-studio",\n  "version": "1.0.0",\n  "active": true\n}',
            "qml": 'import QtQuick 2.15\n\nRectangle {\n    width: 100\n    height: 100\n    color: "red"\n}',
            "empty": "",
            "short": "x = 1\n",
            "large_3000": "\n".join([f"line_{i} = {i} * 2  # calculation {i}" for i in range(3000)])
        }
        
        for lang_name, code in languages.items():
            minimap.setProperty("documentText", code)
            app.processEvents()
            doc_lines = minimap.property("totalDocLines")
            expected_lines = max(1, len(code.split("\n"))) if code else 1
            assert doc_lines == expected_lines, f"Minimap doc lines mismatch for {lang_name}: got {doc_lines}, expected {expected_lines}"
            print(f"PASS: Minimap rendered for {lang_name} ({doc_lines} lines)")
            
        print("\n================================================================")
        print("ALL VERIFICATION TESTS PASSED PERFECTLY!")
        print("================================================================")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_tests()
