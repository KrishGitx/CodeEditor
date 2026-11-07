import QtQuick 2.15
import QtQml.Models 2.15
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
    title: qsTr("Pod Studio")
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
    color: theme.bgRoot

    Theme {
        id: theme
        objectName: "appTheme"
    }
    property alias appTheme: theme

    function syncMaximizeState() {
        var isMax = (mainWindow.visibility === Window.Maximized || mainWindow.visibility === Window.FullScreen || mainWindow.windowState === Qt.WindowMaximized);
        if (typeof Screen !== "undefined" && Screen.desktopAvailableWidth && mainWindow.width < Screen.desktopAvailableWidth - 30) {
            isMax = false;
        }
        if (appHeader) {
            appHeader.isMaximized = isMax;
        }
    }

    onVisibilityChanged: syncMaximizeState()
    onWindowStateChanged: syncMaximizeState()
    onWidthChanged: syncMaximizeState()
    onHeightChanged: syncMaximizeState()

    // Panel Resizing & Layout Properties
    property real explorerWidth: 220
    property real rightPanelWidth: 300
    property real terminalHeight: 160
    property real aiMusicSplitRatio: 0.55

    // Visibility States
    property bool explorerVisible: true
    property bool rightPanelVisible: true
    property bool terminalVisible: false
    property bool aiVisible: false
    property bool musicVisible: true
    property bool zenMode: false
    property bool editorMaximized: false
    property bool whiteboardVisible: false
    property string currentSidebarView: "explorer" // "explorer" or "extensions"

    // Presets
    property string currentPreset: "Full"

    // Layout memory for un-maximizing
    property bool preMaxExplorerVisible: true
    property bool preMaxRightPanelVisible: false
    property bool preMaxAiVisible: false
    property bool preMaxMusicVisible: false
    property bool preMaxTerminalVisible: false
    property bool preMaxWindowMaximized: false

    function toggleMaximizeEditor() {
        if (!editorMaximized) {
            preMaxExplorerVisible = mainWindow.explorerVisible;
            preMaxRightPanelVisible = mainWindow.rightPanelVisible;
            preMaxAiVisible = mainWindow.aiVisible;
            preMaxMusicVisible = mainWindow.musicVisible;
            preMaxTerminalVisible = mainWindow.terminalVisible;
            preMaxWindowMaximized = (mainWindow.visibility === Window.Maximized);

            editorMaximized = true;
            zenMode = true;
            mainWindow.explorerVisible = false;
            mainWindow.rightPanelVisible = false;
            mainWindow.aiVisible = false;
            mainWindow.musicVisible = false;
            mainWindow.terminalVisible = false;
            if (mainWindow.visibility !== Window.Maximized) {
                mainWindow.showMaximized();
            }
        } else {
            editorMaximized = false;
            zenMode = false;
            mainWindow.explorerVisible = preMaxExplorerVisible;
            mainWindow.rightPanelVisible = preMaxRightPanelVisible;
            mainWindow.aiVisible = preMaxAiVisible;
            mainWindow.musicVisible = preMaxMusicVisible;
            mainWindow.terminalVisible = preMaxTerminalVisible;
            if (!preMaxWindowMaximized && mainWindow.visibility === Window.Maximized) {
                mainWindow.showNormal();
            }
        }
    }

    // Clamping Limits
    readonly property real explorerMinWidth: 160
    readonly property real explorerMaxWidth: 440
    readonly property real rightPanelMinWidth: 200
    readonly property real rightPanelMaxWidth: 520
    readonly property real terminalMinHeight: 60
    readonly property real terminalMaxHeight: 440

    // Dynamic Layout Dimensions
    readonly property real effectiveExplorerWidth: (explorerVisible && !zenMode && !editorMaximized) ? explorerWidth : 0
    readonly property real effectiveRightWidth: (rightPanelVisible && !zenMode && !editorMaximized && (aiVisible || musicVisible)) ? rightPanelWidth : 0
    readonly property real effectiveTerminalHeight: (terminalVisible && !zenMode && !editorMaximized) ? terminalHeight : 0

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
            if (typeof explorerPanel !== "undefined" && explorerPanel && explorerPanel.selectAndRevealFile && path) {
                explorerPanel.selectAndRevealFile(path);
            }
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

        function onNotificationRequested(msg, type, title) {
            mainWindow.showNotification(msg, type, title);
        }

        function onWindowMaximizedChanged(isMax) {
            if (appHeader) {
                appHeader.isMaximized = isMax;
            }
        }
    }

    Connections {
        target: typeof aiBackend !== "undefined" ? aiBackend : null
        ignoreUnknownSignals: true

        function onErrorOccurred(err) {
            mainWindow.showNotification(err, "error", "AI Assistant");
        }
    }

    // Native File Dialogs
    FileDialog {
        id: openFileDialog
        title: "Open File in Pod Studio"
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
            mainWindow.openWorkspaceFolder(selectedFolder.toString());
        }
    }

    // =========================================================================
    // SINGLE OWNER KEYBOARD SHORTCUTS (DYNAMICALLY CUSTOMIZABLE)
    // =========================================================================
    Shortcut {
        sequence: "F2"
        onActivated: mainWindow.renameActiveOrSelectedFile()
    }
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
        onActivated: editorArea.closeActiveTab()
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
        sequence: "Ctrl+Shift+Z"
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
        sequence: (theme && theme.shortcutZenMode) ? theme.shortcutZenMode : "Ctrl+K Z"
        onActivated: mainWindow.toggleMaximizeEditor()
    }
    Shortcut {
        sequences: ["Ctrl+=", "Ctrl++", StandardKey.ZoomIn]
        context: Qt.ApplicationShortcut
        onActivated: {
            var th = (typeof theme !== "undefined" && theme) ? theme : null;
            var sz = th ? th.editorFontSize : 14;
            editorArea.setEditorZoom(sz + 1);
        }
    }
    Shortcut {
        sequences: ["Ctrl+-", StandardKey.ZoomOut]
        context: Qt.ApplicationShortcut
        onActivated: {
            var th = (typeof theme !== "undefined" && theme) ? theme : null;
            var sz = th ? th.editorFontSize : 14;
            editorArea.setEditorZoom(sz - 1);
        }
    }
    Shortcut {
        sequences: ["Ctrl+0"]
        context: Qt.ApplicationShortcut
        onActivated: {
            editorArea.setEditorZoom(14);
        }
    }
    Shortcut {
        sequence: "F11"
        context: Qt.ApplicationShortcut
        onActivated: {
            if (mainWindow.visibility === Window.FullScreen || mainWindow.visibility === Window.Maximized) {
                mainWindow.showNormal();
            } else {
                mainWindow.showFullScreen();
            }
        }
    }
    Shortcut {
        sequence: (theme && theme.shortcutSettings) ? theme.shortcutSettings : "Ctrl+,"
        onActivated: settingsOverlay.visible = true
    }
    Shortcut {
        sequence: "Ctrl+Shift+X"
        onActivated: {
            if (extensionsOverlay.visible) {
                extensionsOverlay.visible = false;
            } else {
                mainWindow.showExtensions();
            }
        }
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
        sequence: "Alt+Z"
        onActivated: {
            if (theme) {
                theme.enableWordWrap = !theme.enableWordWrap;
                theme.saveSettings();
            }
        }
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
            isMaximized: (mainWindow.visibility === Window.Maximized || mainWindow.visibility === Window.FullScreen || mainWindow.windowState === Qt.WindowMaximized) && (typeof Screen !== "undefined" && Screen.desktopAvailableWidth ? mainWindow.width >= Screen.desktopAvailableWidth - 30 : true)
            activeProjectName: explorerPanel.workspaceName
            activeFileName: editorArea.activeFileName
            activeFilePath: editorArea.activeFilePath
            isDirty: editorArea.isCurrentFileDirty
            explorerVisible: mainWindow.explorerVisible
            terminalVisible: mainWindow.terminalVisible
            aiVisible: mainWindow.aiVisible

            onNewFileRequested: editorArea.createNewFile()
            onOpenFileRequested: openFileDialog.open()
            onOpenFolderRequested: openFolderDialog.open()
            onOpenRecentRequested: function(folderPath) { mainWindow.openWorkspaceFolder(folderPath); }
            onSaveRequested: {
                var s = editorArea.saveCurrentFile();
                if (!s) saveAsDialog.open();
            }
            onSaveAsRequested: saveAsDialog.open()
            onCloseTabRequested: editorArea.closeActiveTab()
            onToggleExplorerRequested: mainWindow.explorerVisible = !mainWindow.explorerVisible
            onToggleTerminalRequested: mainWindow.terminalVisible = !mainWindow.terminalVisible
            onToggleAiRequested: mainWindow.aiVisible = !mainWindow.aiVisible
            onToggleMusicRequested: mainWindow.musicVisible = !mainWindow.musicVisible
            onToggleZenRequested: mainWindow.toggleMaximizeEditor()
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
            onExtensionsRequested: mainWindow.showExtensions()
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

                // Far Left: Activity Bar (VS Code style navigation)
                ActivityBar {
                    id: activityBar
                    Layout.fillHeight: true
                    visible: !mainWindow.zenMode && !mainWindow.editorMaximized
                    explorerActive: mainWindow.explorerVisible && mainWindow.currentSidebarView === "explorer"
                    extensionsActive: mainWindow.explorerVisible && mainWindow.currentSidebarView === "extensions"
                    settingsActive: settingsOverlay.visible
                    musicActive: mainWindow.musicVisible
                    aiActive: mainWindow.aiVisible
                    terminalActive: mainWindow.terminalVisible

                    onToggleExplorerRequested: {
                        if (mainWindow.explorerVisible && mainWindow.currentSidebarView === "explorer") {
                            mainWindow.explorerVisible = false;
                        } else {
                            mainWindow.currentSidebarView = "explorer";
                            mainWindow.explorerVisible = true;
                        }
                    }
                    onExtensionsRequested: {
                        if (mainWindow.explorerVisible && mainWindow.currentSidebarView === "extensions") {
                            mainWindow.explorerVisible = false;
                        } else {
                            mainWindow.currentSidebarView = "extensions";
                            mainWindow.explorerVisible = true;
                        }
                    }
                    onMusicRequested: mainWindow.musicVisible = !mainWindow.musicVisible
                    onAiRequested: mainWindow.aiVisible = !mainWindow.aiVisible
                    onTerminalRequested: mainWindow.terminalVisible = !mainWindow.terminalVisible
                    onSettingsRequested: settingsOverlay.visible = true
                }

                // Left Sidebar: Multi-View Container (File Explorer / Extensions)
                Item {
                    id: leftSidebarContainer
                    Layout.preferredWidth: mainWindow.effectiveExplorerWidth
                    Layout.fillHeight: true
                    visible: mainWindow.effectiveExplorerWidth > 0
                    clip: true

                    // 1. File Explorer View
                    ExplorerPanel {
                        id: explorerPanel
                        objectName: "explorerPanel"
                        anchors.fill: parent
                        visible: mainWindow.currentSidebarView === "explorer"

                        onFileClicked: function(path) {
                            if (typeof backend !== "undefined" && backend && backend.open_file) {
                                backend.open_file(path);
                            }
                        }
                        onOpenFolderRequested: openFolderDialog.open()
                        // onNewFolderRequested handled directly by ExplorerPanel
                        onRefreshRequested: {
                            if (typeof backend !== "undefined" && backend && explorerPanel.workspacePath) {
                                backend.open_Workspace(explorerPanel.workspacePath);
                            }
                        }
                    }

                    // 2. Extensions View (Shows right in the sidebar like VS Code)
                    ExtensionsSidebarPanel {
                        id: extensionsSidebarPanel
                        objectName: "extensionsSidebarPanel"
                        anchors.fill: parent
                        visible: mainWindow.currentSidebarView === "extensions"
                        onExtensionSelected: function(extData) {
                            if (editorArea) {
                                editorArea.openExtensionDetailsTab(extData);
                            }
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
                        theme: theme
                        isEditorMaximized: mainWindow.editorMaximized
                        onToggleMaximizeEditorRequested: mainWindow.toggleMaximizeEditor()

                        onSettingsPopupRequested: settingsOverlay.visible = true
                        onRequestOpenFile: openFileDialog.open()
                        onRequestOpenFolder: function(targetPath) {
                            if (targetPath) {
                                mainWindow.openWorkspaceFolder(targetPath);
                            } else {
                                openFolderDialog.open();
                            }
                        }
                        onRequestRunFile: mainWindow.runActiveFile()

                        onAskAi: function(code, startPos, endPos, langId) {
                            if (!mainWindow.rightPanelVisible) {
                                mainWindow.rightPanelVisible = true;
                            }
                            mainWindow.aiVisible = true;
                            if (startPos !== undefined && endPos !== undefined && startPos >= 0 && endPos >= startPos) {
                                aiWorkspace.askAboutSelection(code, startPos, endPos, langId || statusBar.currentLanguage);
                            } else {
                                aiWorkspace.askAboutCode(code);
                            }
                        }

                        onSendAiPrompt: function(prompt) {
                            if (!mainWindow.rightPanelVisible) {
                                mainWindow.rightPanelVisible = true;
                            }
                            mainWindow.aiVisible = true;
                            aiWorkspace.sendDirectPrompt(prompt);
                        }

                        onActiveFileChanged: function(path, name, lang, dirty) {
                            appHeader.activeFileName = name;
                            appHeader.activeFilePath = path;
                            appHeader.isDirty = dirty;
                            statusBar.currentLanguage = lang;
                            if (typeof explorerPanel !== "undefined" && explorerPanel && explorerPanel.selectAndRevealFile && path) {
                                explorerPanel.selectAndRevealFile(path);
                            }
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
                            onReplaceSelectionRequested: function(startPos, endPos, code, originalText) {
                                editorArea.replaceSelection(startPos, endPos, code, originalText);
                            }
                            onAiReplacementStarted: function(startPos, endPos, originalText) {
                                editorArea.startPendingAiReplacement(startPos, endPos, originalText);
                            }
                            onAiReplacementReady: function(startPos, endPos, code, originalText) {
                                editorArea.setPendingAiReplacement(startPos, endPos, code, originalText);
                            }
                            onAiReplacementFailed: {
                                editorArea.clearPendingAiReplacement();
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
            onToggleMusicRequested: mainWindow.musicVisible = !mainWindow.musicVisible
            onProfilerRequested: profilerDialog.visible = !profilerDialog.visible
        }
    }

    // =========================================================================
    // SMART INSTALL MODAL OVERLAY
    // =========================================================================
    SmartInstallDialog {
        id: smartInstallDialog
        objectName: "smartInstallDialog"
        z: 9990
        onRetryRequested: function(action, filePath, langId) {
            if (action === "format") {
                editorArea.formatDocument();
            } else if (action === "run") {
                mainWindow.runActiveFile();
            }
        }
    }

    // =========================================================================
    // SETTINGS MODAL OVERLAY
    // =========================================================================
    Rectangle {
        id: settingsOverlay
        objectName: "settingsOverlay"
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.70)
        visible: false
        z: 210
        opacity: visible ? 1.0 : 0.0

        Behavior on opacity {
            NumberAnimation { duration: 150; easing.type: Easing.OutQuad }
        }

        onVisibleChanged: {
            if (visible) {
                settingsDialog.x = Math.round((settingsOverlay.width - settingsDialog.width) / 2);
                settingsDialog.y = Math.round((settingsOverlay.height - settingsDialog.height) / 2);
            }
        }

        // Click outside on backdrop to dismiss ("click off" backdrop)
        MouseArea {
            anchors.fill: parent
            onClicked: settingsOverlay.visible = false
        }

        // Ambient dialog drop shadow
        Rectangle {
            x: settingsDialog.x - 6
            y: settingsDialog.y - 6
            width: settingsDialog.width + 12
            height: settingsDialog.height + 12
            radius: settingsDialog.radius + 6
            color: "transparent"
            border.color: "#00000066"
            border.width: 6
            visible: settingsOverlay.visible
        }

        SettingsDialog {
            id: settingsDialog
            objectName: "settingsDialog"
            x: Math.round((parent.width - width) / 2)
            y: Math.round((parent.height - height) / 2)
            scale: settingsOverlay.visible ? 1.0 : 0.98

            Behavior on scale {
                NumberAnimation { duration: 150; easing.type: Easing.OutQuad }
            }

            onCloseRequested: settingsOverlay.visible = false
            onOpenAsTabRequested: {
                settingsOverlay.visible = false;
                editorArea.openSettingsTab();
            }
            onExtensionsRequested: {
                settingsOverlay.visible = false;
                mainWindow.showExtensions();
            }
            onThemeSelected: function(tName) {
                theme.setTheme(tName);
            }
        }
    }

    // =========================================================================
    // EXTENSIONS MANAGER MODAL OVERLAY
    // =========================================================================
    Rectangle {
        id: extensionsOverlay
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.70)
        visible: false
        z: 220
        opacity: visible ? 1.0 : 0.0

        Behavior on opacity {
            NumberAnimation { duration: 150; easing.type: Easing.OutQuad }
        }

        onVisibleChanged: {
            if (visible) {
                extensionsDialog.x = Math.round((extensionsOverlay.width - extensionsDialog.width) / 2);
                extensionsDialog.y = Math.round((extensionsOverlay.height - extensionsDialog.height) / 2);
                extensionsDialog.refreshExtensions();
            }
        }

        // Click outside on backdrop to dismiss ("click off" backdrop)
        MouseArea {
            anchors.fill: parent
            onClicked: extensionsOverlay.visible = false
        }

        // Ambient dialog drop shadow
        Rectangle {
            x: extensionsDialog.x - 6
            y: extensionsDialog.y - 6
            width: extensionsDialog.width + 12
            height: extensionsDialog.height + 12
            radius: extensionsDialog.radius + 6
            color: "transparent"
            border.color: "#00000066"
            border.width: 6
            visible: extensionsOverlay.visible
        }

        ExtensionsDialog {
            id: extensionsDialog
            x: Math.round((parent.width - width) / 2)
            y: Math.round((parent.height - height) / 2)
            scale: extensionsOverlay.visible ? 1.0 : 0.98

            Behavior on scale {
                NumberAnimation { duration: 150; easing.type: Easing.OutQuad }
            }

            onCloseRequested: extensionsOverlay.visible = false
        }
    }

    // Dynamic Extension Custom Popup Host

    // Dynamic Pure-Python Extension Shortcuts
    Instantiator {
        model: (typeof extensionManager !== "undefined" && extensionManager && extensionManager.registeredShortcuts) ? extensionManager.registeredShortcuts : []
        delegate: Shortcut {
            sequence: modelData
            context: Qt.ApplicationShortcut
            onActivated: {
                if (typeof extensionManager !== "undefined" && extensionManager) {
                    extensionManager.dispatch_shortcut(modelData);
                }
            }
        }
    }
    DynamicPopupHost {
        id: dynamicPopupHost
        z: 9995
        anchors.fill: parent
        onCloseRequested: {
            if (typeof extensionManager !== "undefined" && extensionManager) {
                extensionManager.closeActivePopup();
            }
        }
    }

    // Dynamic Particle Effects Emitter Overlay
    ParticleEmitterOverlay {
        id: particleEmitterOverlay
        anchors.fill: parent
    }

    // Process Profiler & LSP Debugger Dialog
    ProcessProfilerDialog {
        id: profilerDialog
    }

    // Ctrl+Shift+M: Toggle Process Profiler & LSP Debugger
    Shortcut {
        sequence: "Ctrl+Shift+M"
        context: Qt.ApplicationShortcut
        onActivated: profilerDialog.visible = !profilerDialog.visible
    }



    function openWorkspaceFolder(path) {
        if (!path) return;
        var cleanPath = path.toString().replace(/^file:\/\/\//, "");
        // 1. Save current workspace's open files session
        if (typeof editorArea !== "undefined" && editorArea && editorArea.saveWorkspaceSession) {
            editorArea.saveWorkspaceSession();
        }
        // 2. Track new workspace path
        if (typeof editorArea !== "undefined" && editorArea) {
            editorArea.currentWorkspacePath = cleanPath;
        }
        // 3. Open workspace in backend (scans tree, sets fs watcher, indexes symbols)
        if (typeof backend !== "undefined" && backend && backend.open_Workspace) {
            backend.open_Workspace(cleanPath);
        }
        // 4. Restore files that were open in this project
        if (typeof editorArea !== "undefined" && editorArea && editorArea.restoreWorkspaceSession) {
            editorArea.restoreWorkspaceSession(cleanPath);
        }
    }

    function renameActiveOrSelectedFile() {
        var targetPath = "";

        // If user is currently in the editor, rename the current open file
        if (typeof editorArea !== "undefined" && editorArea && editorArea.codeTextArea && editorArea.codeTextArea.activeFocus && editorArea.activeFilePath) {
            targetPath = editorArea.activeFilePath;
        } else if (typeof explorerPanel !== "undefined" && explorerPanel && explorerPanel.selectedFilePath) {
            targetPath = explorerPanel.selectedFilePath;
        } else if (typeof editorArea !== "undefined" && editorArea && editorArea.activeFilePath) {
            targetPath = editorArea.activeFilePath;
        }

        if (targetPath && typeof explorerPanel !== "undefined" && explorerPanel) {
            if (!mainWindow.explorerVisible) {
                mainWindow.explorerVisible = true;
            }
            if (mainWindow.effectiveExplorerWidth <= 0) {
                mainWindow.explorerWidth = Math.max(200, mainWindow.explorerWidth);
            }
            explorerPanel.selectAndRevealFile(targetPath);
            explorerPanel.startInlineRename(targetPath);
        }
    }

    function showExtensions() {
        mainWindow.currentSidebarView = "extensions";
        mainWindow.explorerVisible = true;
    }

    function toggleProfiler() {
        profilerDialog.visible = !profilerDialog.visible;
    }

    // =========================================================================
    // VS CODE-STYLE BOTTOM-RIGHT NOTIFICATION POPUP
    // =========================================================================
    NotificationToast {
        id: notificationToast
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 16
        anchors.bottomMargin: (statusBar && statusBar.visible ? statusBar.height : 0) + 12
        z: 99999
    }

    function showNotification(msg, type, title, duration, actionText, actionCb, secActionText, secActionCb) {
        notificationToast.show(msg, type, title, duration, actionText, actionCb, secActionText, secActionCb);
    }

    Connections {
        target: typeof extensionManager !== "undefined" ? extensionManager : null
        ignoreUnknownSignals: true

        function onNotificationRequested(extId, title, message, icon, sound, actions) {
            mainWindow.showNotification(message, "info", title || "Extension");
        }

        function onSmartFixAvailable(proposal) {
            if (!proposal) return;
            var title = proposal.title || "Smart Fix Available";
            var msg = proposal.proposedFix || proposal.likelyCause || proposal.description || "A fix is available for review.";
            var actionLabel = "Review Fix";
            mainWindow.showNotification(
                msg,
                "info",
                title,
                10000,
                actionLabel,
                function() {
                    smartInstallDialog.openProposal(proposal);
                },
                "Dismiss",
                function() {}
            );
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

    function reloadWindow() {
        if (editorArea.isCurrentFileDirty) {
            editorArea.saveCurrentFile();
        }
        editorArea.saveWorkspaceSession();
        if (typeof backend !== "undefined" && backend && backend.reload_workspace) {
            backend.reload_workspace();
        }
        if (typeof extensionManager !== "undefined" && extensionManager) {
            extensionManager.reload_extensions();
        }
        mainWindow.showNotification("Window and workspace reloaded successfully.", "info", "Developer");
    }

    function runActiveFile() {
        if (!editorArea.activeFilePath) {
            mainWindow.showNotification("Please save the file first before running.", "warning", "Run");
            saveAsFileDialog.open();
            return;
        }

        // Auto-save pending changes before running
        if (editorArea.isCurrentFileDirty) {
            editorArea.saveCurrentFile();
        }

        // If this file belongs to an active extension, hot-reload it in-place
        if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.check_and_reload_extension_file) {
            extensionManager.check_and_reload_extension_file(editorArea.activeFilePath);
        }

        var rawPath = editorArea.activeFilePath.replace(/\//g, "\\");
        var ext = editorArea.activeFileName.split(".").pop().toLowerCase();
        var cmd = "";
        var requiredDep = "";
        var depType = "runtime";

        // 1. Check extension-contributed runners
        var extRunner = (typeof extensionManager !== "undefined" && extensionManager && extensionManager.get_runner_for_extension) ? extensionManager.get_runner_for_extension(ext) : null;
        if (extRunner && extRunner.command) {
            cmd = extRunner.command.replace(/\$\{filePath\}/g, rawPath);
            requiredDep = extRunner.executable || "";
            depType = "runner";
        } else if (ext === "py" || ext === "pyw") {
            requiredDep = "python";
            depType = "interpreter";
            cmd = 'python "' + rawPath + '"';
        } else if (ext === "cpp" || ext === "cc" || ext === "cxx" || ext === "c++") {
            requiredDep = "g++";
            depType = "compiler";
            cmd = 'g++ -std=c++17 "' + rawPath + '" -o output.exe; if ($?) { .\\output.exe }';
        } else if (ext === "c") {
            requiredDep = "gcc";
            depType = "compiler";
            cmd = 'gcc "' + rawPath + '" -o output.exe; if ($?) { .\\output.exe }';
        } else if (ext === "js" || ext === "mjs" || ext === "cjs") {
            requiredDep = "node";
            depType = "runtime";
            cmd = 'node "' + rawPath + '"';
        } else if (ext === "ts" || ext === "tsx") {
            requiredDep = "npx";
            depType = "cli";
            cmd = 'npx tsx "' + rawPath + '"';
        } else if (ext === "java") {
            requiredDep = "java";
            depType = "runtime";
            cmd = 'java "' + rawPath + '"';
        } else if (ext === "rs") {
            requiredDep = "rustc";
            depType = "compiler";
            cmd = 'rustc "' + rawPath + '" -o output.exe; if ($?) { .\\output.exe }';
        } else if (ext === "go") {
            requiredDep = "go";
            depType = "sdk";
            cmd = 'go run "' + rawPath + '"';
        } else if (ext === "cs") {
            requiredDep = "dotnet";
            depType = "sdk";
            cmd = 'dotnet run';
        } else if (ext === "ps1") {
            cmd = 'powershell -ExecutionPolicy Bypass -File "' + rawPath + '"';
        } else if (ext === "sh" || ext === "bash") {
            requiredDep = "bash";
            depType = "cli";
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
            // Clean application-level unsupported runner error
            var cleanErr = "No runner configured for ." + ext + " files.";
            terminalPanel.addOutputLog("Build/Run", cleanErr);

            var runnerCtx = null;
            if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.create_smart_install_context) {
                runnerCtx = extensionManager.create_smart_install_context(
                    "Run ." + ext + " file",
                    "runner",
                    editorArea.currentLanguageId,
                    rawPath,
                    "",
                    ext + " runner",
                    0,
                    "",
                    cleanErr,
                    cleanErr,
                    "No runner configured",
                    ext + " runner",
                    "run"
                );
            }

            mainWindow.showNotification(
                cleanErr,
                "warning",
                "Run",
                9000,
                "Smart Install",
                function() {
                    console.log("[SmartInstall] Smart Install clicked");
                    if (runnerCtx) {
                        smartInstallDialog.openContext(runnerCtx);
                    } else if (extensionManager && extensionManager.suggest_smart_install) {
                        smartInstallDialog.openProposal(extensionManager.suggest_smart_install("runner", ext + " runner", editorArea.currentLanguageId, ext, rawPath));
                    }
                },
                "Close",
                function() {}
            );
            return;
        }

        // Check if required dependency executable is installed before executing
        if (requiredDep && typeof extensionManager !== "undefined" && extensionManager) {
            var execFound = extensionManager.locate_executable ? extensionManager.locate_executable(requiredDep, "") : "";
            if (!execFound) {
                if (typeof smartInstallDialog !== "undefined" && smartInstallDialog && smartInstallDialog.isOpen) {
                    if (smartInstallDialog.dialogState === "retrying" || smartInstallDialog.dialogState === "installing") {
                        smartInstallDialog.reportRetryResult(false, "Required dependency '" + requiredDep + "' is not installed.");
                        return;
                    }
                }

                var depCtx = extensionManager.create_smart_install_context(
                    "Run " + (editorArea.activeFileName || "program"),
                    depType,
                    editorArea.currentLanguageId,
                    rawPath,
                    cmd,
                    requiredDep,
                    0,
                    "",
                    "Required dependency '" + requiredDep + "' is not installed.",
                    "Required dependency '" + requiredDep + "' is not installed.",
                    "Missing runtime / executable",
                    requiredDep,
                    "run"
                );
                mainWindow.showNotification(
                    "Required dependency '" + requiredDep + "' is not installed.",
                    "warning",
                    "Run",
                    9000,
                    "Smart Install",
                    function() {
                        console.log("[SmartInstall] Smart Install clicked");
                        smartInstallDialog.openContext(depCtx);
                    },
                    "Close",
                    function() {}
                );
                return;
            }
        }

        if (typeof smartInstallDialog !== "undefined" && smartInstallDialog && smartInstallDialog.isOpen) {
            if (smartInstallDialog.dialogState === "retrying" || smartInstallDialog.dialogState === "installing") {
                smartInstallDialog.reportRetryResult(true, "Execution started.");
            }
        }

        mainWindow.terminalVisible = true;
        terminalPanel.activeTab = "TERMINAL";
        terminalPanel.addOutputLog("Build/Run", "Executing " + (editorArea.activeFileName || "script") + " [" + cmd + "]");
        terminalPanel.executeCommand(cmd);
    }
}
