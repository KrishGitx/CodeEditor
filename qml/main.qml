import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import QtQuick.Dialogs
import QtCore

import "."
import "components"
import "ai"
import "music"

Window {
    id: mainWindow

    width: 1440
    height: 900
    minimumWidth: 800
    minimumHeight: 600
    visible: true
    title: qsTr("DGX Studio")
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
    color: theme.bgRoot

    Theme {
        id: theme
    }

    onVisibilityChanged: {
        if (visibility === Window.Maximized) {
            appHeader.isMaximized = true;
        } else if (visibility === Window.Windowed) {
            appHeader.isMaximized = false;
        }
    }

    // Panel Resizing & Layout Properties
    property real explorerWidth: 220
    property real rightPanelWidth: 300
    property real terminalHeight: 160
    property real aiMusicSplitRatio: 0.55

    // Visibility States
    property bool explorerVisible: true
    property bool rightPanelVisible: true
    property bool terminalVisible: true
    property bool aiVisible: true
    property bool musicVisible: true
    property bool zenMode: false
    property bool whiteboardVisible: false

    // Presets
    property string currentPreset: "Full"

    // Clamping Limits
    readonly property real explorerMinWidth: 160
    readonly property real explorerMaxWidth: 440
    readonly property real rightPanelMinWidth: 200
    readonly property real rightPanelMaxWidth: 520
    readonly property real terminalMinHeight: 60
    readonly property real terminalMaxHeight: 440

    // Dynamic Layout Dimensions
    readonly property real effectiveExplorerWidth: (explorerVisible && !zenMode) ? explorerWidth : 0
    readonly property real effectiveRightWidth: (rightPanelVisible && !zenMode && (aiVisible || musicVisible)) ? rightPanelWidth : 0
    readonly property real effectiveTerminalHeight: (terminalVisible && !zenMode) ? terminalHeight : 0

    // Connect to Python Backend Services
    Connections {
        target: typeof backend !== "undefined" ? backend : null
        ignoreUnknownSignals: true

        function onCompletionsReceived(suggestions) {
            editorArea.showCompletions(suggestions);
        }

        function onFileOpened(path, content) {
            editorArea.loadFile(path, content);
            appHeader.activeFilePath = path;
        }

        function onFileSaved(path, success) {
            editorArea.fileSaved(path, success);
        }

        function onExplorerContent(list, folderPath) {
            explorerPanel.populateModel(list, folderPath);
            appHeader.activeProjectName = folderPath.split("/").pop().split("\\").pop();
        }

        function onCurrentLanguageChanged(lang) {
            statusBar.currentLanguage = lang;
        }
    }

    // Native File Dialogs
    FileDialog {
        id: openFileDialog
        title: "Open File in DGX Studio"
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: {
            if (typeof backend !== "undefined" && backend && backend.open_file) {
                backend.open_file(selectedFile.toString());
            }
        }
    }

    FileDialog {
        id: saveAsDialog
        title: "Save As"
        fileMode: FileDialog.SaveFile
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: {
            editorArea.saveAsCurrentFile(selectedFile.toString());
        }
    }

    FolderDialog {
        id: openFolderDialog
        title: "Open Workspace Folder"
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: {
            if (typeof backend !== "undefined" && backend && backend.open_Workspace) {
                backend.open_Workspace(selectedFolder.toString());
            }
        }
    }

    // =========================================================================
    // SINGLE OWNER KEYBOARD SHORTCUTS (DYNAMICALLY CUSTOMIZABLE)
    // =========================================================================
    Shortcut {
        sequence: (theme && theme.shortcutNewFile) ? theme.shortcutNewFile : "Ctrl+N"
        onActivated: editorArea.createNewFile()
    }
    Shortcut {
        sequence: (theme && theme.shortcutOpenFile) ? theme.shortcutOpenFile : "Ctrl+O"
        onActivated: openFileDialog.open()
    }
    Shortcut {
        sequence: (theme && theme.shortcutOpenFolder) ? theme.shortcutOpenFolder : "Ctrl+Shift+O"
        onActivated: openFolderDialog.open()
    }
    Shortcut {
        sequence: (theme && theme.shortcutSave) ? theme.shortcutSave : "Ctrl+S"
        onActivated: {
            var saved = editorArea.saveCurrentFile();
            if (!saved) {
                saveAsDialog.open();
            }
        }
    }
    Shortcut {
        sequence: (theme && theme.shortcutSaveAs) ? theme.shortcutSaveAs : "Ctrl+Shift+S"
        onActivated: saveAsDialog.open()
    }
    Shortcut {
        sequence: (theme && theme.shortcutCloseTab) ? theme.shortcutCloseTab : "Ctrl+W"
        onActivated: editorArea.closeTab(editorArea.activeTabIndex)
    }
    Shortcut {
        sequence: (theme && theme.shortcutFind) ? theme.shortcutFind : "Ctrl+F"
        onActivated: editorArea.showFind(false)
    }
    Shortcut {
        sequence: (theme && theme.shortcutReplace) ? theme.shortcutReplace : "Ctrl+H"
        onActivated: editorArea.showFind(true)
    }
    Shortcut {
        sequence: "Ctrl+Z"
        onActivated: editorArea.undo()
    }
    Shortcut {
        sequence: "Ctrl+Y"
        onActivated: editorArea.redo()
    }
    Shortcut {
        sequence: (theme && theme.shortcutFormat) ? theme.shortcutFormat : "Shift+Alt+F"
        onActivated: editorArea.formatDocument()
    }
    Shortcut {
        sequence: (theme && theme.shortcutRun) ? theme.shortcutRun : "F5"
        onActivated: mainWindow.runActiveFile()
    }
    Shortcut {
        sequence: (theme && theme.shortcutToggleExplorer) ? theme.shortcutToggleExplorer : "Ctrl+B"
        onActivated: mainWindow.explorerVisible = !mainWindow.explorerVisible
    }
    Shortcut {
        sequence: (theme && theme.shortcutToggleTerminal) ? theme.shortcutToggleTerminal : "Ctrl+`"
        onActivated: mainWindow.terminalVisible = !mainWindow.terminalVisible
    }
    Shortcut {
        sequence: (theme && theme.shortcutZenMode) ? theme.shortcutZenMode : "Ctrl+Shift+Z"
        onActivated: mainWindow.zenMode = !mainWindow.zenMode
    }
    Shortcut {
        sequence: (theme && theme.shortcutSettings) ? theme.shortcutSettings : "Ctrl+,"
        onActivated: settingsOverlay.visible = true
    }
    Shortcut {
        sequence: (theme && theme.shortcutToggleAI) ? theme.shortcutToggleAI : "Ctrl+Shift+A"
        onActivated: {
            if (!mainWindow.rightPanelVisible) {
                mainWindow.rightPanelVisible = true;
                mainWindow.aiVisible = true;
            } else {
                mainWindow.aiVisible = !mainWindow.aiVisible;
            }
        }
    }
    Shortcut {
        sequence: (theme && theme.shortcutToggleMusic) ? theme.shortcutToggleMusic : "Ctrl+Shift+M"
        onActivated: {
            if (!mainWindow.rightPanelVisible) {
                mainWindow.rightPanelVisible = true;
                mainWindow.musicVisible = true;
            } else {
                mainWindow.musicVisible = !mainWindow.musicVisible;
            }
        }
    }
    Shortcut {
        sequence: (theme && theme.shortcutComment) ? theme.shortcutComment : "Ctrl+/"
        onActivated: editorArea.toggleComment()
    }
    Shortcut {
        sequence: (theme && theme.shortcutWhiteboard) ? theme.shortcutWhiteboard : "Ctrl+Alt+W"
        onActivated: editorArea.openWhiteboardTab()
    }
    Shortcut {
        sequence: "Ctrl+\\"
        onActivated: editorArea.toggleSplitEditor()
    }
    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (settingsOverlay.visible) {
                settingsOverlay.visible = false;
            }
        }
    }

    // =========================================================================
    // MAIN LAYOUT
    // =========================================================================
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Top Header
        AppHeader {
            id: appHeader
            Layout.fillWidth: true
            activeProjectName: explorerPanel.workspaceName
            activeFileName: editorArea.activeFileName
            activeFilePath: editorArea.activeFilePath
            isDirty: editorArea.isCurrentFileDirty

            onNewFileRequested: editorArea.createNewFile()
            onOpenFileRequested: openFileDialog.open()
            onOpenFolderRequested: openFolderDialog.open()
            onSaveRequested: {
                var s = editorArea.saveCurrentFile();
                if (!s) saveAsDialog.open();
            }
            onSaveAsRequested: saveAsDialog.open()
            onCloseTabRequested: editorArea.closeTab(editorArea.activeTabIndex)
            onToggleExplorerRequested: mainWindow.explorerVisible = !mainWindow.explorerVisible
            onToggleTerminalRequested: mainWindow.terminalVisible = !mainWindow.terminalVisible
            onToggleAiRequested: mainWindow.aiVisible = !mainWindow.aiVisible
            onToggleMusicRequested: mainWindow.musicVisible = !mainWindow.musicVisible
            onToggleZenRequested: mainWindow.zenMode = !mainWindow.zenMode
            onToggleSplitEditorRequested: editorArea.toggleSplitEditor()
            onToggleWhiteboardRequested: editorArea.openWhiteboardTab()
            onOpenWebPreviewRequested: editorArea.openWebPreviewTab()
            onOpenColorPickerRequested: editorArea.openColorPickerAtCursor()
            onFindRequested: editorArea.showFind(false)
            onReplaceRequested: editorArea.showFind(true)
            onFormatRequested: editorArea.formatDocument()
            onUndoRequested: editorArea.undo()
            onRedoRequested: editorArea.redo()
            onSettingsRequested: settingsOverlay.visible = true
            onRunFileRequested: mainWindow.runActiveFile()
            onPresetSelected: function(preset) { mainWindow.applyPreset(preset); }
            onThemeSelected: function(tName) { theme.setTheme(tName); }
        }

        // 2. Main Middle Workspace
        Item {
            id: middleWorkspaceArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            RowLayout {
                anchors.fill: parent
                spacing: 0

                // Left: Explorer Panel
                ExplorerPanel {
                    id: explorerPanel
                    Layout.preferredWidth: mainWindow.effectiveExplorerWidth
                    Layout.fillHeight: true
                    visible: mainWindow.effectiveExplorerWidth > 0

                    onFileClicked: function(path) {
                        if (typeof backend !== "undefined" && backend && backend.open_file) {
                            backend.open_file(path);
                        }
                    }
                    onOpenFolderRequested: openFolderDialog.open()
                    onNewFileRequested: editorArea.createNewFile()
                    onNewFolderRequested: openFolderDialog.open()
                    onRefreshRequested: {
                        if (typeof backend !== "undefined" && backend && explorerPanel.workspacePath) {
                            backend.open_Workspace(explorerPanel.workspacePath);
                        }
                    }
                }

                // Explorer SplitHandle (Single 1px divider between Explorer and Editor)
                SplitHandle {
                    Layout.fillHeight: true
                    orientation: Qt.Horizontal
                    visible: mainWindow.effectiveExplorerWidth > 0
                    enabled: mainWindow.effectiveExplorerWidth > 0

                    onMoved: function(delta) {
                        var newW = mainWindow.explorerWidth + delta;
                        mainWindow.explorerWidth = Math.max(mainWindow.explorerMinWidth, Math.min(mainWindow.explorerMaxWidth, newW));
                    }
                }

                // Center: Code Editor Area & Tabbed Whiteboard Workspace
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    EditorArea {
                        id: editorArea
                        objectName: "editorArea"
                        anchors.fill: parent

                        onRequestOpenFile: openFileDialog.open()
                        onRequestOpenFolder: openFolderDialog.open()
                        onRequestRunFile: mainWindow.runActiveFile()

                        onAskAi: function(code) {
                            if (!mainWindow.rightPanelVisible) {
                                mainWindow.rightPanelVisible = true;
                            }
                            mainWindow.aiVisible = true;
                            aiWorkspace.askAboutCode(code);
                        }

                        onActiveFileChanged: function(path, name, lang, dirty) {
                            appHeader.activeFileName = name;
                            appHeader.activeFilePath = path;
                            appHeader.isDirty = dirty;
                            statusBar.currentLanguage = lang;
                        }

                        onCursorPositionChanged: function(line, col) {
                            statusBar.cursorLine = line;
                            statusBar.cursorColumn = col;
                        }
                    }
                }

                // Right Sidebar SplitHandle (Single 1px divider between Editor and Right Sidebar)
                SplitHandle {
                    Layout.fillHeight: true
                    orientation: Qt.Horizontal
                    visible: mainWindow.effectiveRightWidth > 0
                    enabled: mainWindow.effectiveRightWidth > 0

                    onMoved: function(delta) {
                        var newW = mainWindow.rightPanelWidth - delta;
                        mainWindow.rightPanelWidth = Math.max(mainWindow.rightPanelMinWidth, Math.min(mainWindow.rightPanelMaxWidth, newW));
                    }
                }

                // Right Sidebar (AI top, Music bottom)
                Item {
                    id: rightSidebar
                    Layout.preferredWidth: mainWindow.effectiveRightWidth
                    Layout.fillHeight: true
                    visible: mainWindow.effectiveRightWidth > 0
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        // AI Workspace
                        AIWorkspace {
                            id: aiWorkspace
                            Layout.fillWidth: true
                            Layout.preferredHeight: (mainWindow.aiVisible && mainWindow.musicVisible) ? (rightSidebar.height * mainWindow.aiMusicSplitRatio) : (mainWindow.aiVisible ? rightSidebar.height : 0)
                            visible: mainWindow.aiVisible

                            onInsertCodeRequested: function(code) {
                                editorArea.insertSnippet(code);
                            }
                            onCloseRequested: mainWindow.aiVisible = false
                        }

                        // AI / Music Vertical SplitHandle (Single 1px divider between AI and Music)
                        SplitHandle {
                            Layout.fillWidth: true
                            orientation: Qt.Vertical
                            visible: mainWindow.aiVisible && mainWindow.musicVisible
                            enabled: mainWindow.aiVisible && mainWindow.musicVisible

                            onMoved: function(delta) {
                                var currentH = rightSidebar.height * mainWindow.aiMusicSplitRatio;
                                var newH = currentH + delta;
                                var newRatio = newH / Math.max(1, rightSidebar.height);
                                mainWindow.aiMusicSplitRatio = Math.max(0.25, Math.min(0.75, newRatio));
                            }
                        }

                        // Music Player Panel
                        MusicPlayerPanel {
                            id: musicPlayerPanel
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: mainWindow.musicVisible

                            onCloseRequested: mainWindow.musicVisible = false
                        }
                    }
                }
            }
        }

        // Workspace <-> Terminal SplitHandle (Single 1px divider between Workspace and Terminal)
        SplitHandle {
            Layout.fillWidth: true
            orientation: Qt.Vertical
            visible: mainWindow.effectiveTerminalHeight > 0
            enabled: mainWindow.effectiveTerminalHeight > 0

            onMoved: function(delta) {
                var newH = mainWindow.terminalHeight - delta;
                mainWindow.terminalHeight = Math.max(mainWindow.terminalMinHeight, Math.min(mainWindow.terminalMaxHeight, newH));
            }
        }

        // 3. Bottom Terminal Panel (VS Code Style)
        TerminalPanel {
            id: terminalPanel
            Layout.fillWidth: true
            Layout.preferredHeight: mainWindow.effectiveTerminalHeight
            visible: mainWindow.effectiveTerminalHeight > 0

            onCloseRequested: mainWindow.terminalVisible = false
            onProblemSelected: function(filePath, line, column) {
                editorArea.jumpToLineAndCol(line, column);
            }
        }

        // 4. Status Bar
        StatusBar {
            id: statusBar
            Layout.fillWidth: true
            currentLanguage: editorArea.currentLanguage
            cursorLine: editorArea.cursorLine
            cursorColumn: editorArea.cursorColumn

            onLanguageSelected: function(lang) {
                if (editorArea.currentTab) {
                    editorArea.currentTab.languageName = lang;
                }
                statusBar.currentLanguage = lang;
            }

            onSettingsRequested: settingsOverlay.visible = true
            onThemeSelected: function(tName) { theme.setTheme(tName); }
        }
    }

    // =========================================================================
    // SETTINGS MODAL OVERLAY
    // =========================================================================
    Rectangle {
        id: settingsOverlay
        anchors.fill: parent
        color: "#00000066"
        visible: false
        z: 210

        onVisibleChanged: {
            if (visible) {
                settingsDialog.x = Math.round((settingsOverlay.width - settingsDialog.width) / 2);
                settingsDialog.y = Math.round((settingsOverlay.height - settingsDialog.height) / 2);
            }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: settingsOverlay.visible = false
        }

        SettingsDialog {
            id: settingsDialog
            x: Math.round((parent.width - width) / 2)
            y: Math.round((parent.height - height) / 2)

            onCloseRequested: settingsOverlay.visible = false
            onThemeSelected: function(tName) {
                theme.setTheme(tName);
            }
        }
    }

    // =========================================================================
    // WORKSPACE PRESETS LOGIC
    // =========================================================================
    function applyPreset(presetName) {
        mainWindow.currentPreset = presetName;
        mainWindow.zenMode = false;

        if (presetName === "Full") {
            mainWindow.explorerVisible = true;
            mainWindow.rightPanelVisible = true;
            mainWindow.aiVisible = true;
            mainWindow.musicVisible = true;
            mainWindow.terminalVisible = true;
        } else if (presetName === "Coding") {
            mainWindow.explorerVisible = true;
            mainWindow.rightPanelVisible = false;
            mainWindow.terminalVisible = true;
        } else if (presetName === "AI") {
            mainWindow.explorerVisible = false;
            mainWindow.rightPanelVisible = true;
            mainWindow.aiVisible = true;
            mainWindow.musicVisible = false;
            mainWindow.terminalVisible = false;
        } else if (presetName === "Music") {
            mainWindow.explorerVisible = false;
            mainWindow.rightPanelVisible = true;
            mainWindow.aiVisible = false;
            mainWindow.musicVisible = true;
            mainWindow.terminalVisible = false;
        } else if (presetName === "Focus") {
            mainWindow.zenMode = true;
        }
    }

    function runActiveFile() {
        if (!editorArea.activeFilePath) {
            terminalPanel.executeCommand("Write-Host 'Please save the file first before running.' -ForegroundColor Yellow");
            return;
        }
        mainWindow.terminalVisible = true;
        var rawPath = editorArea.activeFilePath.replace(/\//g, "\\");
        var ext = editorArea.activeFileName.split(".").pop().toLowerCase();
        var cmd = "";

        if (ext === "py" || ext === "pyw") {
            cmd = 'python "' + rawPath + '"';
        } else if (ext === "cpp" || ext === "cc" || ext === "cxx" || ext === "c++") {
            cmd = 'g++ -std=c++17 "' + rawPath + '" -o output.exe; if ($?) { .\\output.exe }';
        } else if (ext === "c") {
            cmd = 'gcc "' + rawPath + '" -o output.exe; if ($?) { .\\output.exe }';
        } else if (ext === "js" || ext === "mjs" || ext === "cjs") {
            cmd = 'node "' + rawPath + '"';
        } else if (ext === "ts" || ext === "tsx") {
            cmd = 'npx tsx "' + rawPath + '"';
        } else if (ext === "java") {
            cmd = 'java "' + rawPath + '"';
        } else if (ext === "rs") {
            cmd = 'rustc "' + rawPath + '" -o output.exe; if ($?) { .\\output.exe }';
        } else if (ext === "go") {
            cmd = 'go run "' + rawPath + '"';
        } else if (ext === "cs") {
            cmd = 'dotnet run';
        } else if (ext === "ps1") {
            cmd = 'powershell -ExecutionPolicy Bypass -File "' + rawPath + '"';
        } else if (ext === "sh" || ext === "bash") {
            cmd = 'bash "' + rawPath + '"';
        } else if (ext === "html" || ext === "htm") {
            var target = (theme && theme.htmlRunTarget) ? theme.htmlRunTarget : "built_in";
            if (target === "built_in") {
                editorArea.openWebPreviewTab();
                return;
            } else {
                mainWindow.terminalVisible = true;
                terminalPanel.executeCommand('Start-Process "' + rawPath + '"');
                return;
            }
        } else {
            mainWindow.terminalVisible = true;
            cmd = 'Write-Host "No runner configured for .' + ext + ' files." -ForegroundColor Yellow';
        }

        terminalPanel.addOutputLog("Build/Run", "Executing " + (editorArea.activeFileName || "script") + " [" + cmd + "]");
        terminalPanel.executeCommand(cmd);
    }
}
