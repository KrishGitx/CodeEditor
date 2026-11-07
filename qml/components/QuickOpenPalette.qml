import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: root

    property bool isOpen: false
    property string mode: "files" // "files", "goto", or "commands"
    property var filesList: []
    property int selectedIndex: 0

    property var builtInCommands: [
        {
            id: "workbench.action.reloadWindow",
            name: "Developer: Reload Window",
            relPath: "Reload workspace, window, and active extensions",
            icon: "refresh",
            iconColor: "#38bdf8",
            isCommand: true
        },
        {
            id: "extensions.createCustomExtension",
            name: "Extensions: Create Custom Extension",
            relPath: "Scaffold a new custom extension with ExtensionSDK",
            icon: "puzzle",
            iconColor: "#a855f7",
            isCommand: true
        },
        {
            id: "workbench.action.terminal.toggleTerminal",
            name: "View: Toggle Terminal",
            relPath: "Toggle integrated terminal panel",
            icon: "terminal",
            iconColor: "#4ade80",
            isCommand: true
        },
        {
            id: "workbench.action.files.save",
            name: "File: Save",
            relPath: "Save current file to disk",
            icon: "save",
            iconColor: "#facc15",
            isCommand: true
        },
        {
            id: "workbench.action.files.openFolder",
            name: "File: Open Folder...",
            relPath: "Open folder in DGX Studio",
            icon: "folder",
            iconColor: "#ea580c",
            isCommand: true
        }
    ]

    signal fileSelected(string filePath)
    signal lineSelected(int lineNumber)
    signal previewRequested(string filePath, int lineNumber)
    signal reloadWindowRequested()
    signal createCustomExtensionRequested()
    signal commandSelected(string commandId)
    signal closeRequested()

    onSelectedIndexChanged: {
        if (isOpen && mode === "files" && filesList && selectedIndex >= 0 && selectedIndex < filesList.length) {
            var item = filesList[selectedIndex];
            if (item && !item.isCommand && item.path) {
                root.previewRequested(item.path, 1);
            }
        }
    }

    function getFileIconInfo(fileName) {
        if (!fileName) return { icon: "file", color: (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#656565" };
        var lower = fileName.toLowerCase();
        var dotIdx = lower.lastIndexOf(".");
        var ext = dotIdx !== -1 ? lower.substring(dotIdx + 1) : "";

        if (lower === "package.json") return { icon: "file-code", color: "#22c55e" };
        if (lower === "cargo.toml") return { icon: "file-code", color: "#ea580c" };
        if (lower === "project.godot") return { icon: "sparkles", color: "#478cbf" };
        if (lower === "extension.json") return { icon: "puzzle", color: "#a855f7" };
        if (lower === ".gitignore" || lower === ".gitmodules") return { icon: "file-text", color: "#f97316" };
        if (lower === "readme.md") return { icon: "file-text", color: "#38bdf8" };

        if (ext === "py" || ext === "pyw") return { icon: "file-code", color: "#38bdf8" };
        if (ext === "cpp" || ext === "cc" || ext === "cxx" || ext === "c++") return { icon: "file-code", color: "#60a5fa" };
        if (ext === "c") return { icon: "file-code", color: "#93c5fd" };
        if (ext === "h" || ext === "hpp" || ext === "hxx") return { icon: "file-code", color: "#a78bfa" };
        if (ext === "qml") return { icon: "file-code", color: "#4ade80" };
        if (ext === "js" || ext === "mjs" || ext === "cjs") return { icon: "file-code", color: "#facc15" };
        if (ext === "jsx") return { icon: "file-code", color: "#38bdf8" };
        if (ext === "ts") return { icon: "file-code", color: "#3b82f6" };
        if (ext === "tsx") return { icon: "file-code", color: "#60a5fa" };
        if (ext === "html" || ext === "htm") return { icon: "file-code", color: "#f97316" };
        if (ext === "css" || ext === "scss" || ext === "less") return { icon: "file-code", color: "#38bdf8" };
        if (ext === "json") return { icon: "file-code", color: "#facc15" };
        if (ext === "xml" || ext === "svg") return { icon: "file-code", color: "#fb923c" };
        if (ext === "yaml" || ext === "yml") return { icon: "file-code", color: "#ef4444" };
        if (ext === "rs") return { icon: "file-code", color: "#ea580c" };
        if (ext === "go") return { icon: "file-code", color: "#06b6d4" };
        if (ext === "java") return { icon: "file-code", color: "#f87171" };
        if (ext === "cs") return { icon: "file-code", color: "#38bdf8" };
        if (ext === "sln" || ext === "slnx" || ext === "csproj") return { icon: "file-code", color: "#a855f7" };
        if (ext === "unity" || ext === "prefab" || ext === "asset" || ext === "mat" || ext === "shader") return { icon: "sparkles", color: "#e2e8f0" };
        if (ext === "gd") return { icon: "file-code", color: "#478cbf" };
        if (ext === "meta") return { icon: "file-text", color: "#64748b" };
        if (ext === "md" || ext === "markdown" || ext === "txt") return { icon: "file-text", color: "#38bdf8" };
        return { icon: "file", color: (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#656565" };
    }

    anchors.fill: parent
    visible: isOpen
    z: 9999

    // Backdrop
    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
        onWheel: function(wheel) {
            // Forward mouse wheel scrolling to editor flickable behind the palette
            if (typeof root.parent !== "undefined" && root.parent && root.parent.activeEditorPane && root.parent.activeEditorPane.editorFlickable) {
                var f = root.parent.activeEditorPane.editorFlickable;
                var delta = wheel.angleDelta.y;
                if (delta !== 0) {
                    var lineH = root.parent.activeEditorPane.paneLineHeight || 18.0;
                    var step = (delta / 120.0) * lineH * 3.0;
                    var maxY = Math.max(0, f.contentHeight - f.height);
                    f.contentY = Math.max(0, Math.min(maxY, f.contentY - step));
                    wheel.accepted = true;
                }
            } else {
                wheel.accepted = false;
            }
        }
    }

    function openQuickOpen() {
        mode = "files";
        searchInput.text = "";
        selectedIndex = 0;
        updateFileList("");
        isOpen = true;
        searchInput.forceActiveFocus();
    }

    function openCommands() {
        mode = "commands";
        searchInput.text = ">";
        selectedIndex = 0;
        updateFileList(">");
        isOpen = true;
        searchInput.forceActiveFocus();
    }

    function openGotoLine(currentLine) {
        mode = "goto";
        searchInput.text = ":" + (currentLine !== undefined ? currentLine : "");
        selectedIndex = 0;
        isOpen = true;
        searchInput.forceActiveFocus();
        searchInput.selectAll();
    }

    function close() {
        isOpen = false;
        root.closeRequested();
    }

    function updateFileList(query) {
        var trimmed = query ? query.trim() : "";
        var results = [];

        if (trimmed.startsWith(">")) {
            mode = "commands";
            var cmdQuery = trimmed.substring(1).trim().toLowerCase();
            for (var i = 0; i < builtInCommands.length; i++) {
                var cmd = builtInCommands[i];
                if (!cmdQuery || cmd.name.toLowerCase().indexOf(cmdQuery) !== -1 || cmd.relPath.toLowerCase().indexOf(cmdQuery) !== -1) {
                    results.push(cmd);
                }
            }
            filesList = results;
            selectedIndex = 0;
            return;
        }

        // Match commands if query includes keywords like "reload", "extension", "custom", "terminal", "window", etc.
        var lowerQuery = trimmed.toLowerCase();
        var matchingCmds = [];
        if (lowerQuery.length >= 2) {
            for (var c = 0; c < builtInCommands.length; c++) {
                var bCmd = builtInCommands[c];
                if (bCmd.name.toLowerCase().indexOf(lowerQuery) !== -1 || bCmd.relPath.toLowerCase().indexOf(lowerQuery) !== -1) {
                    matchingCmds.push(bCmd);
                }
            }
        }

        var workspaceFiles = [];
        if (typeof backend !== "undefined" && backend && backend.get_workspace_files) {
            workspaceFiles = backend.get_workspace_files(trimmed) || [];
        }

        if (matchingCmds.length > 0) {
            filesList = matchingCmds.concat(workspaceFiles);
        } else {
            filesList = workspaceFiles;
        }
        selectedIndex = 0;
    }

    function handleAccept() {
        var query = searchInput.text.trim();
        if (query.startsWith(":") || mode === "goto") {
            var rawNum = query.startsWith(":") ? query.substring(1) : query;
            var parts = rawNum.split(":");
            var lineNum = parseInt(parts[0], 10);
            if (!isNaN(lineNum) && lineNum > 0) {
                root.lineSelected(lineNum);
                root.close();
            }
        } else {
            if (filesList && filesList.length > 0 && selectedIndex >= 0 && selectedIndex < filesList.length) {
                var selectedItem = filesList[selectedIndex];
                if (selectedItem.isCommand) {
                    root.commandSelected(selectedItem.id);
                    if (selectedItem.id === "workbench.action.reloadWindow") {
                        root.reloadWindowRequested();
                    } else if (selectedItem.id === "extensions.createCustomExtension") {
                        root.createCustomExtensionRequested();
                    }
                    root.close();
                } else if (selectedItem.path) {
                    root.fileSelected(selectedItem.path);
                    root.close();
                }
            }
        }
    }

    // Modal Card
    Rectangle {
        id: paletteBox
        width: Math.min(parent.width - 48, 520)
        height: Math.min(parent.height - 80, (mode === "goto" || filesList.length === 0) ? 56 : Math.min(340, 56 + filesList.length * 30 + 10))
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 36
        radius: 6
        color: (typeof theme !== "undefined" && theme && theme.bgPopup) ? theme.bgPopup : "#1e1e24"
        border.color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#333338"
        border.width: 1

        // Elevation Glow
        Rectangle {
            anchors.fill: parent
            anchors.margins: -2
            radius: 8
            color: "transparent"
            border.color: "#000000"
            opacity: 0.35
            z: -1
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 6
            spacing: 4

            // Search Box Input
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                radius: 4
                color: (typeof theme !== "undefined" && theme && theme.bgEditor) ? theme.bgEditor : "#141417"
                border.color: searchInput.activeFocus ? ((typeof theme !== "undefined" && theme && theme.accent) ? theme.accent : "#0078d4") : ((typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#2b2b30")
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 6

                    VectorIcon {
                        name: root.mode === "goto" ? "zen" : (root.mode === "commands" ? "terminal" : "search")
                        size: 13
                        color: (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#71717a"
                    }

                    TextInput {
                        id: searchInput
                        Layout.fillWidth: true
                        color: (typeof theme !== "undefined" && theme && theme.textBright) ? theme.textBright : "#ffffff"
                        selectionColor: (typeof theme !== "undefined" && theme && theme.selectionBackground) ? theme.selectionBackground : "#264f78"
                        selectedTextColor: "#ffffff"
                        font.pixelSize: 12
                        font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                        clip: true

                        Text {
                            text: root.mode === "goto" ? "Type line number to navigate..." : (root.mode === "commands" ? "Type command name to execute..." : "Search files by name (type > for commands, : for line)...")
                            color: (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#52525b"
                            font.pixelSize: 11
                            font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                            visible: !searchInput.text && !searchInput.inputMethodComposing
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        onTextChanged: {
                            if (text.startsWith(":")) {
                                root.mode = "goto";
                                var rawNum = text.substring(1).trim();
                                var parts = rawNum.split(":");
                                var lNum = parseInt(parts[0], 10);
                                if (!isNaN(lNum) && lNum > 0) {
                                    root.previewRequested("", lNum);
                                }
                            } else if (text.startsWith(">")) {
                                root.mode = "commands";
                                root.updateFileList(text);
                            } else {
                                root.mode = "files";
                                root.updateFileList(text);
                            }
                        }

                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Escape) {
                                root.close();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                root.handleAccept();
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Down) {
                                if (root.filesList.length > 0) {
                                    root.selectedIndex = (root.selectedIndex + 1) % root.filesList.length;
                                    fileListView.positionViewAtIndex(root.selectedIndex, ListView.Contain);
                                }
                                event.accepted = true;
                            } else if (event.key === Qt.Key_Up) {
                                if (root.filesList.length > 0) {
                                    root.selectedIndex = (root.selectedIndex - 1 + root.filesList.length) % root.filesList.length;
                                    fileListView.positionViewAtIndex(root.selectedIndex, ListView.Contain);
                                }
                                event.accepted = true;
                            }
                        }
                    }
                }
            }

            // Results List
            ListView {
                id: fileListView
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: (root.mode === "files" || root.mode === "commands") && root.filesList.length > 0
                clip: true
                model: root.filesList
                spacing: 1

                delegate: Rectangle {
                    width: fileListView.width
                    height: 28
                    radius: 3
                    color: index === root.selectedIndex ? ((typeof theme !== "undefined" && theme && theme.selectionBackground) ? theme.selectionBackground : "#094771") : (itemMouseArea.containsMouse ? ((typeof theme !== "undefined" && theme && theme.bgSurfaceHover) ? theme.bgSurfaceHover : "#24242a") : "transparent")

                    readonly property var iconInfo: root.getFileIconInfo(modelData.name)

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        VectorIcon {
                            name: (modelData && modelData.isCommand) ? modelData.icon : iconInfo.icon
                            size: 14
                            color: (modelData && modelData.isCommand) ? modelData.iconColor : iconInfo.color
                        }

                        Text {
                            text: modelData.name
                            color: index === root.selectedIndex ? "#ffffff" : ((typeof theme !== "undefined" && theme && theme.textPrimary) ? theme.textPrimary : "#e4e4e7")
                            font.pixelSize: 11
                            font.bold: index === root.selectedIndex
                            font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData.relPath
                            color: index === root.selectedIndex ? "#cbd5e1" : ((typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#71717a")
                            font.pixelSize: 10
                            font.family: (typeof theme !== "undefined" && theme && theme.fontFamilyUi) ? theme.fontFamilyUi : "sans-serif"
                            elide: Text.ElideMiddle
                        }
                    }

                    MouseArea {
                        id: itemMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.selectedIndex = index;
                            root.handleAccept();
                        }
                    }
                }
            }
        }
    }
}
