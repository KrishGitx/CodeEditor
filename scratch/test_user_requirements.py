import os
import sys

def test_qml_properties():
    with open("qml/music/MusicPlayerPanel.qml", "r", encoding="utf-8") as f:
        mp = f.read()
    assert 'property string viewMode: "search"' in mp, "MusicPlayerPanel default viewMode should be 'search'"
    print("PASS: MusicPlayerPanel default viewMode is 'search'")

    for path in ["qml/main.qml", "main.qml"]:
        with open(path, "r", encoding="utf-8") as f:
            m = f.read()
        assert "property bool terminalVisible: false" in m, f"{path}: terminalVisible must be false"
        assert "property bool aiVisible: false" in m, f"{path}: aiVisible must be false"
        assert "property bool musicVisible: true" in m, f"{path}: musicVisible must be true"
        print(f"PASS: {path} default view visibility verified (terminal=false, ai=false, music=true)")

    with open("qml/components/ExplorerPanel.qml", "r", encoding="utf-8") as f:
        ep = f.read()

    assert 'Shortcut {' in ep and 'sequence: "F2"' in ep, "ExplorerPanel must have F2 Shortcut"
    assert 'root.startInlineRename(root.selectedFilePath)' in ep, "F2 must activate startInlineRename"
    assert 'Keys.onPressed:' in ep and 'Qt.Key_F2' in ep, "fileListView must have F2 key handler"
    assert 'root.isCreatingFile = true;' in ep, "startNewFile must set isCreatingFile = true"
    assert 'wasCreating && backend.open_file' in ep or ('backend.open_file(newFullPath)' in ep and 'wasCreating' in ep), "commitRenameFile must open file after naming"
    assert 'root.cancelInlineEdit(oldNorm)' in ep, "Empty name on creation cancels edit"
    print("PASS: ExplorerPanel F2 and inline creation logic verified")

    with open("qml/components/EditorArea.qml", "r", encoding="utf-8") as f:
        ea = f.read()

    assert 'enabled: Boolean(codeTextArea && codeTextArea.activeFocus)' in ea, "EditorArea F2 must be scoped to active editor focus"
    assert 'mainWindow.showNotification' in ea, "EditorArea F2 has helpful feedback toast when no symbol selected"
    print("PASS: EditorArea F2 scoped properly without collision")

if __name__ == "__main__":
    test_qml_properties()
    print("\nALL USER REQUIREMENT CHECKS PASSED SUCCESSFULLY!")

