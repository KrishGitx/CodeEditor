import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15
import QtQuick.Dialogs
import QtCore

import "components"
import "ai"
import "music"

Window {
    id: mainWindow
    width: 1440
    height: 900
    minimumWidth: 1000
    minimumHeight: 600
    visible: true
    title: qsTr("DGX Studio")
    flags: Qt.Window | Qt.FramelessWindowHint
    color: theme.bgRoot

    // ─── Global Theme Engine ───
    Theme {
        id: theme
    }

    // ─── Panel Size State ───
    property real explorerWidth: 250
    property real rightPanelWidth: 320
    property real terminalHeight: 180
    property real aiMusicSplit: 0.55  // fraction of right panel for AI

    // ─── Panel Visibility ───
    property bool explorerVisible: true
    property bool rightPanelVisible: true
    property bool terminalVisible: true
    property bool aiVisible: true
    property bool musicVisible: true

    // ─── Focus / Zen Mode ───
    property bool zenMode: false

    // ─── Panel Size Constraints ───
    readonly property real explorerMin: 180
    readonly property real explorerMax: 440
    readonly property real rightPanelMin: 260
    readonly property real rightPanelMax: 540
    readonly property real terminalMin: 80
    readonly property real terminalMax: 440
    readonly property real editorMinWidth: 420
    readonly property real editorMinHeight: 240
    readonly property real headerHeight: 34
    readonly property real statusBarHeight: 24

    // ─── Computed Positions ───
    readonly property real effectiveExplorerWidth: (explorerVisible && !zenMode) ? explorerWidth : 0
    readonly property real effectiveRightWidth: (rightPanelVisible && !zenMode && (aiVisible || musicVisible)) ? rightPanelWidth : 0
    readonly property real effectiveTerminalHeight: (terminalVisible && !zenMode) ? terminalHeight : 0
    readonly property real editorAreaWidth: mainWindow.width - effectiveExplorerWidth - effectiveRightWidth
                                           - (effectiveExplorerWidth > 0 ? 5 : 0)
                                           - (effectiveRightWidth > 0 ? 5 : 0)
    readonly property real mainContentHeight: mainWindow.height - headerHeight - statusBarHeight
                                              - effectiveTerminalHeight
                                              - (effectiveTerminalHeight > 0 ? 5 : 0)

    function syncRightPanelVisibility() {
        rightPanelVisible = aiVisible || musicVisible
    }

    function constrainPanelSizes() {
        // Preserve a usable editing surface before growing secondary panels.
        var maxRight = width - explorerWidth - editorMinWidth - 10
        rightPanelWidth = Math.max(rightPanelMin, Math.min(rightPanelMax, maxRight, rightPanelWidth))
        var maxExplorer = width - rightPanelWidth - editorMinWidth - 10
        explorerWidth = Math.max(explorerMin, Math.min(explorerMax, maxExplorer, explorerWidth))
        var maxTerminal = height - headerHeight - statusBarHeight - editorMinHeight - 5
        terminalHeight = Math.max(terminalMin, Math.min(terminalMax, maxTerminal, terminalHeight))
    }

    Component.onCompleted: constrainPanelSizes()
    onWidthChanged: constrainPanelSizes()
    onHeightChanged: constrainPanelSizes()

    // ─── Backend Signal Connections ───
    Connections {
        target: backend

        function onCompletionsReceived(suggestions) {
            editorArea.showCompletions(suggestions)
        }

        function onFileOpened(path, content) {
            editorArea.loadFile(path, content)
            appHeader.activeFilePath = path
        }

        function onExplorerContent(list, fPath) {
            explorerPanel.populateModel(list, fPath)
            appHeader.activeProjectName = fPath.split("/").pop().split("\\").pop()
        }
    }

    // ─── Dialogs ───
    FileDialog {
        id: openFileDialog
        title: "Choose a file to open"
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: {
            backend.open_file(selectedFile.toString())
        }
    }

    FolderDialog {
        id: openWorkspaceDialog
        title: "Choose a workspace folder"
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: {
            backend.open_Workspace(selectedFolder.toString())
        }
    }

    // ─── Global Keyboard Shortcuts ───
    Shortcut {
        sequence: "Ctrl+S"
        onActivated: editorArea.saveCurrentFile()
    }
    Shortcut {
        sequence: "Ctrl+N"
        onActivated: editorArea.newBlankTab()
    }
    Shortcut {
        sequence: "Ctrl+O"
        onActivated: openFileDialog.open()
    }
    Shortcut {
        sequence: "Ctrl+Shift+O"
        onActivated: openWorkspaceDialog.open()
    }
    Shortcut {
        sequence: "Ctrl+`"
        onActivated: mainWindow.terminalVisible = !mainWindow.terminalVisible
    }
    Shortcut {
        sequence: "Ctrl+,"
        onActivated: settingsDialog.open()
    }
    Shortcut {
        sequence: "Ctrl+M"
        onActivated: radialMenu.openAt(mainWindow.width / 2, mainWindow.height / 2)
    }
    Shortcut {
        sequence: "Ctrl+B"
        onActivated: mainWindow.explorerVisible = !mainWindow.explorerVisible
    }
    Shortcut {
        sequence: "Ctrl+Shift+Z"
        onActivated: mainWindow.zenMode = !mainWindow.zenMode
    }
    Shortcut {
        sequence: "Ctrl+F"
        onActivated: editorArea.toggleFindBar()
    }

    // ═══════════════════════════════════════════════════════════════
    //  MAIN LAYOUT — Manual coordinate positioning with 4 draggable splitters
    // ═══════════════════════════════════════════════════════════════

    // ─── 1. App Header ───
    AppHeader {
        id: appHeader
        x: 0; y: 0
        width: mainWindow.width
        height: headerHeight
        z: 10

        onOpenFileDialogRequested: openFileDialog.open()
        onOpenWorkspaceDialogRequested: openWorkspaceDialog.open()
        onSettingsRequested: settingsDialog.open()
        onToggleTerminalRequested: mainWindow.terminalVisible = !mainWindow.terminalVisible
        onToggleMusicRequested: { mainWindow.musicVisible = !mainWindow.musicVisible; mainWindow.syncRightPanelVisibility() }
        onToggleAIRequested: { mainWindow.aiVisible = !mainWindow.aiVisible; mainWindow.syncRightPanelVisibility() }
        onToggleZenRequested: mainWindow.zenMode = !mainWindow.zenMode
        onSaveRequested: editorArea.saveCurrentFile()
        onNewFileRequested: editorArea.newBlankTab()
        onPresetRequested: (preset) => mainWindow.applyPreset(preset)
    }

    // ─── 2. Explorer Panel (Left) ───
    ExplorerPanel {
        id: explorerPanel
        x: 0
        y: headerHeight
        width: effectiveExplorerWidth
        height: mainContentHeight
        visible: explorerVisible && !zenMode

        Behavior on width { NumberAnimation { duration: theme.animNormal; easing.type: Easing.OutCubic } }

        onFileSelected: (filePath, fileName) => {
            backend.open_file(filePath)
        }
        onOpenWorkspaceRequested: openWorkspaceDialog.open()
    }

    // ─── Splitter 1: Explorer ↔ Editor ───
    SplitHandle {
        id: explorerSplitter
        orientation: "horizontal"
        x: effectiveExplorerWidth
        y: headerHeight
        height: mainContentHeight
        visible: explorerVisible && !zenMode
        z: 20

        onDragged: function(delta) {
            var maxForEditor = mainWindow.width - mainWindow.rightPanelWidth - mainWindow.editorMinWidth - 10
            mainWindow.explorerWidth = Math.max(explorerMin, Math.min(explorerMax, maxForEditor, explorerWidth + delta))
        }
    }

    // ─── 3. Code Editor (Center & Largest) ───
    EditorArea {
        id: editorArea
        x: effectiveExplorerWidth + (effectiveExplorerWidth > 0 ? 5 : 0)
        y: headerHeight
        width: Math.max(editorMinWidth, editorAreaWidth)
        height: mainContentHeight

        Behavior on x { NumberAnimation { duration: theme.animNormal; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: theme.animNormal; easing.type: Easing.OutCubic } }

        onRequestRadialMenu: (posX, posY) => {
            radialMenu.openAt(editorArea.x + posX, editorArea.y + posY)
        }

        onCursorPositionChanged: (line, col) => {
            statusBar.cursorLine = line
            statusBar.cursorCol = col
        }
    }

    // ─── Splitter 2: Editor ↔ Right Sidebar ───
    SplitHandle {
        id: rightSplitter
        orientation: "horizontal"
        x: mainWindow.width - effectiveRightWidth - 5
        y: headerHeight
        height: mainContentHeight
        visible: rightPanelVisible && (aiVisible || musicVisible) && !zenMode
        z: 20

        onDragged: function(delta) {
            var maxForEditor = mainWindow.width - mainWindow.explorerWidth - mainWindow.editorMinWidth - 10
            mainWindow.rightPanelWidth = Math.max(rightPanelMin, Math.min(rightPanelMax, maxForEditor, rightPanelWidth - delta))
        }
    }

    // ─── 4. Right Sidebar (AI Workspace Upper-Right + Music Player Lower-Right) ───
    Item {
        id: rightPanel
        x: mainWindow.width - effectiveRightWidth
        y: headerHeight
        width: effectiveRightWidth
        height: mainContentHeight
        visible: rightPanelVisible && (aiVisible || musicVisible) && !zenMode

        Behavior on x { NumberAnimation { duration: theme.animNormal; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: theme.animNormal; easing.type: Easing.OutCubic } }

        property real aiHeight: {
            if (aiVisible && musicVisible) {
                return Math.round(rightPanel.height * aiMusicSplit)
            } else if (aiVisible) {
                return rightPanel.height
            } else {
                return 0
            }
        }
        property real musicY: aiVisible ? (aiHeight + (aiVisible && musicVisible ? 5 : 0)) : 0
        property real musicHeight: {
            if (aiVisible && musicVisible) {
                return rightPanel.height - aiHeight - 5
            } else if (musicVisible) {
                return rightPanel.height
            } else {
                return 0
            }
        }

        // Upper-Right: AI Workspace
        AIWorkspace {
            id: aiWorkspace
            x: 0; y: 0
            width: rightPanel.width
            height: rightPanel.aiHeight
            visible: mainWindow.aiVisible
            onCloseRequested: { mainWindow.aiVisible = false; mainWindow.syncRightPanelVisibility() }
        }

        // Splitter 3: AI ↔ Music
        SplitHandle {
            id: aiMusicSplitter
            orientation: "vertical"
            x: 0
            y: rightPanel.aiHeight
            width: rightPanel.width
            visible: mainWindow.aiVisible && mainWindow.musicVisible
            z: 20

            onDragged: function(delta) {
                var newFrac = (rightPanel.aiHeight + delta) / rightPanel.height
                mainWindow.aiMusicSplit = Math.max(0.25, Math.min(0.8, newFrac))
            }
        }

        // Lower-Right: Music Player
        MusicPlayerPanel {
            id: musicPlayerPanel
            x: 0
            y: rightPanel.musicY
            width: rightPanel.width
            height: rightPanel.musicHeight
            visible: mainWindow.musicVisible
            onCloseRequested: { mainWindow.musicVisible = false; mainWindow.syncRightPanelVisibility() }
        }
    }

    // ─── Splitter 4: Workspace ↔ Terminal ───
    SplitHandle {
        id: terminalSplitter
        orientation: "vertical"
        x: 0
        y: headerHeight + mainContentHeight
        width: mainWindow.width
        visible: terminalVisible && !zenMode
        z: 20

        onDragged: function(delta) {
            mainWindow.terminalHeight = Math.max(terminalMin, Math.min(terminalMax, terminalHeight - delta))
        }
    }

    // ─── 5. Terminal Panel (Bottom) ───
    TerminalPanel {
        id: terminalPanel
        x: 0
        y: headerHeight + mainContentHeight + (terminalVisible && !zenMode ? 5 : 0)
        width: mainWindow.width
        height: effectiveTerminalHeight
        visible: terminalVisible && !zenMode

        Behavior on y { NumberAnimation { duration: theme.animNormal; easing.type: Easing.OutCubic } }
        Behavior on height { NumberAnimation { duration: theme.animNormal; easing.type: Easing.OutCubic } }

        onCloseRequested: mainWindow.terminalVisible = false
    }

    // ─── 6. Status Bar ───
    StatusBar {
        id: statusBar
        x: 0
        y: mainWindow.height - statusBarHeight
        width: mainWindow.width
        height: statusBarHeight
        z: 10

        onToggleTerminal: mainWindow.terminalVisible = !mainWindow.terminalVisible
        onToggleMusic: {
            mainWindow.musicVisible = !mainWindow.musicVisible
            mainWindow.rightPanelVisible = mainWindow.aiVisible || mainWindow.musicVisible
        }
    }

    // ─── Radial Menu Contextual Overlay ───
    RadialMenu {
        id: radialMenu
        z: 10000

        onActionTriggered: action => {
            if (action === "save") {
                editorArea.saveCurrentFile()
            } else if (action === "run") {
                mainWindow.terminalVisible = true
                terminalBackend.send_command("python main.py")
            } else if (action === "undo") {
                editorArea.textAreaItem.undo()
            } else if (action === "redo") {
                editorArea.textAreaItem.redo()
            } else if (action === "format") {
                editorArea.saveCurrentFile()
            } else if (action === "find") {
                editorArea.toggleFindBar()
            } else if (action === "zen") {
                mainWindow.zenMode = !mainWindow.zenMode
            } else if (action === "settings") {
                settingsDialog.open()
            } else if (action === "ai") {
                mainWindow.aiVisible = !mainWindow.aiVisible
                mainWindow.rightPanelVisible = mainWindow.aiVisible || mainWindow.musicVisible
            } else if (action === "music") {
                mainWindow.musicVisible = !mainWindow.musicVisible
                mainWindow.rightPanelVisible = mainWindow.aiVisible || mainWindow.musicVisible
            }
        }
    }

    // ─── Settings Dialog Modal ───
    SettingsDialog {
        id: settingsDialog
        z: 9999
    }

    // ─── Workspace Presets Engine ───
    function applyPreset(presetName) {
        switch (presetName) {
            case "Coding":
                explorerVisible = true; aiVisible = false; musicVisible = false
                rightPanelVisible = false; terminalVisible = true
                zenMode = false
                break
            case "AI":
                explorerVisible = false; aiVisible = true; musicVisible = false
                rightPanelVisible = true; terminalVisible = false
                zenMode = false
                break
            case "Music":
                explorerVisible = false; aiVisible = false; musicVisible = true
                rightPanelVisible = true; terminalVisible = false
                zenMode = false
                break
            case "Debugging":
                explorerVisible = true; aiVisible = false; musicVisible = false
                rightPanelVisible = false; terminalVisible = true
                terminalHeight = 300
                zenMode = false
                break
            case "Focus":
                zenMode = true
                break
            case "Full":
                explorerVisible = true; aiVisible = true; musicVisible = true
                rightPanelVisible = true; terminalVisible = true
                zenMode = false
                break
        }
    }
}
