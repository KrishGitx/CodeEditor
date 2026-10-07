import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property string workspacePath: ""
    property string workspaceName: "NO FOLDER OPENED"
    property string selectedFilePath: ""
    property string editingFilePath: ""
    property int nextUntitledIndex: 1
    property var collapsedFolders: ({})
    property int collapseVersion: 0
    property bool isCreatingFile: false
    property var cutPaths: ({})

    // Drag & Drop State
    property bool isDragging: false
    property string draggedFilePath: ""
    property string draggedFileName: ""
    property string draggedFileType: "File"
    property string hoveredDropTargetPath: ""
    property bool isDropTargetValid: false
    property real dragGlobalX: 0
    property real dragGlobalY: 0

    signal fileClicked(string filePath)
    signal openFolderRequested()
    signal newFileRequested()
    signal newFolderRequested()
    signal refreshRequested()

    color: theme ? theme.bgSidebar : "#181818"

    ListModel {
        id: fileTreeModel
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Explorer Header
        Rectangle {
            Layout.fillWidth: true
            height: 28
            color: theme ? theme.bgHeader : "#181818"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 6
                spacing: 4

                Text {
                    text: root.workspaceName.toUpperCase()
                    color: theme ? theme.textSecondary : "#858585"
                    font.pixelSize: 11
                    font.bold: true
                    font.letterSpacing: 0.5
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                // New File
                Rectangle {
                    width: 20
                    height: 20
                    radius: 2
                    color: newFileMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "new-file"
                        size: 11
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    ToolTip.visible: newFileMa.containsMouse
                    ToolTip.text: "New File"

                    MouseArea {
                        id: newFileMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.startNewFile();
                            root.newFileRequested();
                        }
                    }
                }

                // New Folder
                Rectangle {
                    width: 20
                    height: 20
                    radius: 2
                    color: newFolderMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "new-folder"
                        size: 11
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    ToolTip.visible: newFolderMa.containsMouse
                    ToolTip.text: "New Folder"

                    MouseArea {
                        id: newFolderMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.startNewFolder();
                            root.newFolderRequested();
                        }
                    }
                }

                // Refresh
                Rectangle {
                    width: 20
                    height: 20
                    radius: 2
                    color: refreshMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "refresh"
                        size: 11
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    ToolTip.visible: refreshMa.containsMouse
                    ToolTip.text: "Refresh Explorer"

                    MouseArea {
                        id: refreshMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.cutPaths = {};
                            root.refreshRequested();
                        }
                    }
                }
            }
        }

        // 2. Tree View
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ScrollView {
                anchors.fill: parent
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                ListView {
                    id: fileListView
                    anchors.fill: parent
                    model: fileTreeModel
                    boundsBehavior: Flickable.StopAtBounds

                    delegate: Rectangle {
                        id: itemRow
                        width: Math.max(fileListView.width, contentRow.width + 16)
                        readonly property bool isInlineEditing: root.editingFilePath !== "" && root.editingFilePath === model.fullPath
                        readonly property bool isRowVisible: isInlineEditing || root.isItemVisible(model.parentFullPath, root.collapseVersion)
                        visible: isRowVisible
                        height: isRowVisible ? 22 : 0

                        readonly property bool isSelected: !itemRow.isInlineEditing && root.selectedFilePath === model.fullPath
                        readonly property bool isFolder: model.type === "Folder"
                        readonly property bool isCollapsed: isFolder && (root.collapsedFolders[model.fullPath.replace(/\\/g, "/")] === true)
                        readonly property bool isCut: root.cutPaths[model.fullPath.replace(/\\/g, "/")] === true
                        readonly property bool isBeingDragged: root.isDragging && root.draggedFilePath === model.fullPath
                        readonly property bool isHoveredTarget: root.isDragging && root.hoveredDropTargetPath === model.fullPath
                        readonly property string itemFullPath: model.fullPath

                        color: isHoveredTarget ? (root.isDropTargetValid ? (theme ? theme.accentMuted : "#0078d433") : "#f14c4c22") : (isSelected ? (theme ? theme.bgSelected : "#04395e") : (rowMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"))
                        opacity: isBeingDragged ? 0.35 : (isCut ? 0.45 : 1.0)

                        Behavior on opacity {
                            NumberAnimation { duration: 80 }
                        }

                        // Drag & Drop Target Highlight Border
                        Rectangle {
                            anchors.fill: parent
                            color: "transparent"
                            border.color: root.isDropTargetValid ? (theme ? theme.accent : "#0078d4") : "#f14c4c"
                            border.width: 1
                            radius: 2
                            visible: itemRow.isHoveredTarget
                            z: 2
                        }

                        // Drop Area for this item/row
                        DropArea {
                            anchors.fill: parent
                            keys: ["explorer-path"]
                            enabled: !itemRow.isInlineEditing

                            onEntered: function(drag) {
                                var src = root.draggedFilePath || "";
                                var targetDir = itemRow.isFolder ? model.fullPath : model.parentFullPath;
                                var valid = root.canDropItem(src, targetDir);
                                root.hoveredDropTargetPath = model.fullPath;
                                root.isDropTargetValid = valid;
                                if (valid) {
                                    drag.accept();
                                } else {
                                    drag.accepted = false;
                                }
                            }

                            onPositionChanged: function(drag) {
                                var pos = mapToItem(root, drag.x, drag.y);
                                root.dragGlobalX = pos.x;
                                root.dragGlobalY = pos.y;
                            }

                            onExited: {
                                if (root.hoveredDropTargetPath === model.fullPath) {
                                    root.hoveredDropTargetPath = "";
                                    root.isDropTargetValid = false;
                                }
                            }

                            onDropped: function(drop) {
                                var src = root.draggedFilePath || "";
                                var targetDir = itemRow.isFolder ? model.fullPath : model.parentFullPath;
                                root.hoveredDropTargetPath = "";
                                root.isDropTargetValid = false;
                                root.isDragging = false;
                                root.draggedFilePath = "";

                                if (src && root.canDropItem(src, targetDir)) {
                                    root.moveItem(src, targetDir);
                                    drop.accept();
                                }
                            }
                        }

                        RowLayout {
                            id: contentRow
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: Math.max(6, model.level * 12 + 6)
                            spacing: 4

                            // Chevron for Folders
                            Item {
                                width: 12
                                height: 12
                                visible: itemRow.isFolder

                                VectorIcon {
                                    anchors.centerIn: parent
                                    name: itemRow.isCollapsed ? "chevron-right" : "chevron-down"
                                    size: 8
                                    color: theme ? theme.textMuted : "#656565"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        root.toggleFolder(model.fullPath);
                                    }
                                }
                            }

                            Item {
                                width: 12
                                height: 12
                                visible: !itemRow.isFolder
                            }

                            // File / Folder Icon
                            VectorIcon {
                                name: itemRow.isFolder ? (itemRow.isCollapsed ? "folder" : "folder-open") : "file"
                                size: 12
                                color: itemRow.isFolder ? (theme ? theme.textSecondary : "#858585") : (theme ? theme.textMuted : "#656565")
                            }

                            // Label
                            Text {
                                visible: !itemRow.isInlineEditing
                                text: model.name || ""
                                color: itemRow.isSelected ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                font.pixelSize: 12
                                font.family: theme ? theme.fontFamilyUi : "Segoe UI, sans-serif"
                            }

                            // Inline VS Code-style File Name Editor
                            Rectangle {
                                id: inlineRenameRect
                                visible: itemRow.isInlineEditing
                                Layout.preferredWidth: Math.max(140, inlineRenameInput.implicitWidth + 24)
                                Layout.preferredHeight: 18
                                color: theme ? theme.bgInput : "#1e1e1e"
                                border.color: theme ? theme.accent : "#0078d4"
                                border.width: 1
                                radius: 2

                                TextInput {
                                    id: inlineRenameInput
                                    anchors.fill: parent
                                    anchors.leftMargin: 4
                                    anchors.rightMargin: 4
                                    verticalAlignment: TextInput.AlignVCenter
                                    color: theme ? theme.textBright : "#ffffff"
                                    font.pixelSize: 12
                                    font.family: theme ? theme.fontFamilyUi : "Segoe UI, sans-serif"
                                    selectByMouse: true
                                    text: model.name || ""
                                    focus: itemRow.isInlineEditing

                                    property bool hasBeenFocused: false

                                    function initFocusAndSelection() {
                                        forceActiveFocus();
                                        hasBeenFocused = true;
                                        var dotIdx = text.lastIndexOf(".");
                                        if (dotIdx > 0 && model.type !== "Folder") {
                                            select(0, dotIdx);
                                        } else {
                                            selectAll();
                                        }
                                    }

                                    onVisibleChanged: {
                                        if (visible) {
                                            text = model.name || "";
                                            hasBeenFocused = false;
                                            Qt.callLater(initFocusAndSelection);
                                        }
                                    }

                                    Component.onCompleted: {
                                        if (itemRow.isInlineEditing) {
                                            hasBeenFocused = false;
                                            Qt.callLater(initFocusAndSelection);
                                        }
                                    }

                                    onActiveFocusChanged: {
                                        if (activeFocus) {
                                            hasBeenFocused = true;
                                            var dotIdx = text.lastIndexOf(".");
                                            if (dotIdx > 0 && model.type !== "Folder") {
                                                select(0, dotIdx);
                                            } else {
                                                selectAll();
                                            }
                                        } else {
                                            if (hasBeenFocused && root.editingFilePath === model.fullPath) {
                                                root.commitRenameFile(model.fullPath, text, model.parentFullPath);
                                            }
                                        }
                                    }

                                    Keys.onPressed: function(event) {
                                        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                            root.commitRenameFile(model.fullPath, inlineRenameInput.text, model.parentFullPath);
                                            event.accepted = true;
                                        } else if (event.key === Qt.Key_Escape) {
                                            root.cancelInlineEdit(model.fullPath);
                                            event.accepted = true;
                                        }
                                    }
                                }
                            }
                        }

                        MouseArea {
                            id: rowMa
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            hoverEnabled: !itemRow.isInlineEditing
                            enabled: !itemRow.isInlineEditing
                            cursorShape: root.isDragging ? (root.isDropTargetValid ? Qt.DragMoveCursor : Qt.ForbiddenCursor) : Qt.PointingHandCursor
                            drag.target: dragProxy
                            drag.axis: Drag.XAndYAxis

                            property real pressX: 0
                            property real pressY: 0
                            property bool dragInitiated: false

                            onPressed: function(mouse) {
                                if (mouse.button === Qt.LeftButton) {
                                    pressX = mouse.x;
                                    pressY = mouse.y;
                                    dragInitiated = false;
                                }
                            }

                            onPositionChanged: function(mouse) {
                                if (mouse.buttons & Qt.LeftButton) {
                                    if (!dragInitiated) {
                                        var dist = Math.sqrt(Math.pow(mouse.x - pressX, 2) + Math.pow(mouse.y - pressY, 2));
                                        if (dist > 4) {
                                            dragInitiated = true;
                                            root.isDragging = true;
                                            root.draggedFilePath = model.fullPath;
                                            root.draggedFileName = model.name;
                                            root.draggedFileType = model.type;
                                        }
                                    }
                                    if (dragInitiated) {
                                        var globalP = mapToItem(root, mouse.x, mouse.y);
                                        root.dragGlobalX = globalP.x;
                                        root.dragGlobalY = globalP.y;
                                    }
                                }
                            }

                            onReleased: function(mouse) {
                                if (dragInitiated) {
                                    dragInitiated = false;
                                    dragProxy.Drag.drop();
                                    root.isDragging = false;
                                    root.draggedFilePath = "";
                                    root.hoveredDropTargetPath = "";
                                    root.isDropTargetValid = false;
                                }
                            }

                            onCanceled: {
                                dragInitiated = false;
                                root.isDragging = false;
                                root.draggedFilePath = "";
                                root.hoveredDropTargetPath = "";
                                root.isDropTargetValid = false;
                            }

                            onClicked: function(mouse) {
                                if (dragInitiated) return;
                                root.selectedFilePath = model.fullPath;
                                if (mouse.button === Qt.RightButton) {
                                    contextMenuPopup.openAt(mouse.x, mouse.y, model.fullPath, model.name, model.type, model.parentFullPath, itemRow);
                                } else {
                                    if (itemRow.isFolder) {
                                        root.toggleFolder(model.fullPath);
                                    } else {
                                        root.fileClicked(model.fullPath);
                                    }
                                }
                            }

                            Item {
                                id: dragProxy
                                Drag.active: rowMa.drag.active
                                Drag.source: itemRow
                                Drag.keys: ["explorer-path"]
                                Drag.hotSpot.x: 10
                                Drag.hotSpot.y: 10
                            }
                        }
                    }
                }
            }

            // Drop Area on empty background of explorer tree
            DropArea {
                anchors.fill: parent
                z: -1
                keys: ["explorer-path"]

                onEntered: function(drag) {
                    var src = root.draggedFilePath || "";
                    var targetDir = root.workspacePath;
                    var valid = root.canDropItem(src, targetDir);
                    root.hoveredDropTargetPath = root.workspacePath;
                    root.isDropTargetValid = valid;
                    if (valid) drag.accept();
                    else drag.accepted = false;
                }

                onPositionChanged: function(drag) {
                    var pos = mapToItem(root, drag.x, drag.y);
                    root.dragGlobalX = pos.x;
                    root.dragGlobalY = pos.y;
                }

                onExited: {
                    if (root.hoveredDropTargetPath === root.workspacePath) {
                        root.hoveredDropTargetPath = "";
                        root.isDropTargetValid = false;
                    }
                }

                onDropped: function(drop) {
                    var src = root.draggedFilePath || "";
                    var targetDir = root.workspacePath;
                    root.hoveredDropTargetPath = "";
                    root.isDropTargetValid = false;
                    root.isDragging = false;
                    root.draggedFilePath = "";

                    if (src && root.canDropItem(src, targetDir)) {
                        root.moveItem(src, targetDir);
                        drop.accept();
                    }
                }
            }

            // Right click on empty background
            MouseArea {
                anchors.fill: parent
                z: -2
                acceptedButtons: Qt.RightButton
                onClicked: function(mouse) {
                    root.selectedFilePath = "";
                    contextMenuPopup.openAt(mouse.x, mouse.y, root.workspacePath, root.workspaceName, "Folder", root.workspacePath, null);
                }
            }

            // Empty State
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 8
                visible: fileTreeModel.count === 0

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "You have not opened a folder."
                    color: theme ? theme.textMuted : "#656565"
                    font.pixelSize: 11
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Open Folder"
                    color: theme ? theme.accent : "#0078d4"
                    font.pixelSize: 12
                    font.underline: openFldrHover.containsMouse

                    MouseArea {
                        id: openFldrHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.openFolderRequested()
                    }
                }
            }
        }
    }

    // =========================================================================
    // FLOATING DRAG GHOST / PREVIEW (Follows cursor smoothly during drag)
    // =========================================================================
    Rectangle {
        id: dragGhostBadge
        visible: root.isDragging && root.draggedFilePath !== ""
        x: Math.max(4, Math.min(root.width - width - 4, root.dragGlobalX + 12))
        y: Math.max(4, Math.min(root.height - height - 4, root.dragGlobalY + 12))
        z: 9999
        width: ghostRow.implicitWidth + 18
        height: 24
        color: (typeof theme !== "undefined" && theme && theme.bgSurface) ? theme.bgSurface : "#252526"
        border.color: root.isDropTargetValid ? (theme ? theme.accent : "#0078d4") : "#f14c4c"
        border.width: 1
        radius: 4
        opacity: 0.95

        RowLayout {
            id: ghostRow
            anchors.centerIn: parent
            spacing: 6

            VectorIcon {
                name: root.draggedFileType === "Folder" ? "folder" : "file"
                size: 12
                color: theme ? theme.textSecondary : "#cccccc"
            }

            Text {
                text: root.draggedFileName
                color: theme ? theme.textBright : "#ffffff"
                font.pixelSize: 11
                font.family: theme ? theme.fontFamilyUi : "Segoe UI, sans-serif"
            }

            Rectangle {
                width: 12
                height: 12
                radius: 6
                color: root.isDropTargetValid ? "#107c41" : "#a80000"
                visible: root.hoveredDropTargetPath !== ""

                VectorIcon {
                    anchors.centerIn: parent
                    name: root.isDropTargetValid ? "check" : "x"
                    size: 8
                    color: "#ffffff"
                }
            }
        }
    }

    // =========================================================================
    // EXPLORER RIGHT-CLICK CONTEXT MENU
    // =========================================================================
    Popup {
        id: contextMenuPopup
        width: 190
        padding: 4
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        property string targetPath: ""
        property string targetName: ""
        property string targetType: "File"
        property string targetParentPath: ""
        property var targetItem: null

        background: Rectangle {
            color: theme ? theme.bgSurface : "#252526"
            border.color: theme ? theme.borderNormal : "#454545"
            border.width: 1
            radius: 4
        }

        function openAt(mouseX, mouseY, fPath, fName, fType, fParent, itemObj) {
            targetPath = fPath || "";
            targetName = fName || "";
            targetType = fType || "File";
            targetParentPath = fParent || root.workspacePath;
            targetItem = itemObj;

            var globalPos = itemObj ? itemObj.mapToItem(root, mouseX, mouseY) : { x: mouseX, y: mouseY };
            contextMenuPopup.x = Math.max(4, Math.min(root.width - contextMenuPopup.width - 6, globalPos.x));
            contextMenuPopup.y = Math.max(4, Math.min(root.height - 280, globalPos.y));
            contextMenuPopup.open();
        }

        contentItem: ColumnLayout {
            spacing: 2

            // Open
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: openMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Open"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: openMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        if (contextMenuPopup.targetType === "Folder") {
                            root.toggleFolder(contextMenuPopup.targetPath);
                        } else {
                            root.fileClicked(contextMenuPopup.targetPath);
                        }
                    }
                }
            }

            // New File (Folder only)
            Rectangle {
                visible: contextMenuPopup.targetType === "Folder"
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: newFMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "New File"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: newFMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        root.startNewFile(contextMenuPopup.targetPath);
                    }
                }
            }

            // New Folder (Folder only)
            Rectangle {
                visible: contextMenuPopup.targetType === "Folder"
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: newFldMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "New Folder"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: newFldMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        root.startNewFolder(contextMenuPopup.targetPath);
                    }
                }
            }

            // Separator
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: theme ? theme.borderNormal : "#3c3c3c"
                Layout.topMargin: 2
                Layout.bottomMargin: 2
            }

            // Rename
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: renMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Rename"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "F2"
                        color: theme ? theme.textMuted : "#656565"
                        font.pixelSize: 11
                    }
                }
                MouseArea {
                    id: renMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        root.startInlineRename(contextMenuPopup.targetPath);
                    }
                }
            }

            // Copy
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: copyMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Copy"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "Ctrl+C"
                        color: theme ? theme.textMuted : "#656565"
                        font.pixelSize: 11
                    }
                }
                MouseArea {
                    id: copyMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        if (typeof backend !== "undefined" && backend && backend.set_explorer_clipboard) {
                            backend.set_explorer_clipboard(contextMenuPopup.targetPath, "copy");
                            root.cutPaths = {};
                        }
                    }
                }
            }

            // Cut
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: cutMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Cut"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "Ctrl+X"
                        color: theme ? theme.textMuted : "#656565"
                        font.pixelSize: 11
                    }
                }
                MouseArea {
                    id: cutMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        if (typeof backend !== "undefined" && backend && backend.set_explorer_clipboard) {
                            backend.set_explorer_clipboard(contextMenuPopup.targetPath, "cut");
                            var cp = {};
                            cp[contextMenuPopup.targetPath.replace(/\\/g, "/")] = true;
                            root.cutPaths = cp;
                        }
                    }
                }
            }

            // Paste
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: pasteMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Paste"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "Ctrl+V"
                        color: theme ? theme.textMuted : "#656565"
                        font.pixelSize: 11
                    }
                }
                MouseArea {
                    id: pasteMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        var targetDir = contextMenuPopup.targetType === "Folder" ? contextMenuPopup.targetPath : contextMenuPopup.targetParentPath;
                        if (typeof backend !== "undefined" && backend && backend.paste_explorer_clipboard) {
                            backend.paste_explorer_clipboard(targetDir);
                            root.cutPaths = {};
                            root.refreshRequested();
                        }
                    }
                }
            }

            // Duplicate (Files only)
            Rectangle {
                visible: contextMenuPopup.targetType !== "Folder"
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: dupMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Duplicate"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: dupMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        if (typeof backend !== "undefined" && backend && backend.duplicate_file) {
                            backend.duplicate_file(contextMenuPopup.targetPath);
                            root.refreshRequested();
                        }
                    }
                }
            }

            // Separator
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: theme ? theme.borderNormal : "#3c3c3c"
                Layout.topMargin: 2
                Layout.bottomMargin: 2
            }

            // Copy Path
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: cpPathMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Copy Path"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: cpPathMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        if (typeof backend !== "undefined" && backend && backend.copy_path_to_clipboard) {
                            backend.copy_path_to_clipboard(contextMenuPopup.targetPath);
                        }
                    }
                }
            }

            // Reveal in File Explorer
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: revMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Reveal in File Explorer"
                        color: theme ? theme.textPrimary : "#cccccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    id: revMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        if (typeof backend !== "undefined" && backend && backend.reveal_in_explorer) {
                            backend.reveal_in_explorer(contextMenuPopup.targetPath);
                        }
                    }
                }
            }

            // Delete
            Rectangle {
                Layout.fillWidth: true
                height: 24
                radius: 2
                color: delMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    Text {
                        text: "Delete"
                        color: theme ? theme.error : "#f14c4c"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                    Text {
                        text: "Del"
                        color: theme ? theme.textMuted : "#656565"
                        font.pixelSize: 11
                    }
                }
                MouseArea {
                    id: delMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        contextMenuPopup.close();
                        deleteConfirmDialog.promptDelete(contextMenuPopup.targetPath, contextMenuPopup.targetName, contextMenuPopup.targetType);
                    }
                }
            }
        }
    }

    // =========================================================================
    // DELETE CONFIRMATION DIALOG (Centered in Window with Equal Button Sizes)
    // =========================================================================
    Dialog {
        id: deleteConfirmDialog
        parent: Overlay.overlay
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        width: 380
        modal: true
        header: null
        footer: null
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        property string deleteTargetPath: ""
        property string deleteTargetName: ""
        property string deleteTargetType: "File"

        function promptDelete(fPath, fName, fType) {
            deleteTargetPath = fPath;
            deleteTargetName = fName;
            deleteTargetType = fType || "File";
            deleteConfirmDialog.open();
        }

        Overlay.modal: Rectangle {
            color: "#99000000"
        }

        background: Rectangle {
            color: (typeof theme !== "undefined" && theme && theme.bgSurface) ? theme.bgSurface : "#252526"
            border.color: (typeof theme !== "undefined" && theme && theme.borderNormal) ? theme.borderNormal : "#454545"
            border.width: 1
            radius: 6
        }

        contentItem: ColumnLayout {
            spacing: 14

            Text {
                text: "Delete " + deleteConfirmDialog.deleteTargetType
                color: (typeof theme !== "undefined" && theme && theme.textBright) ? theme.textBright : "#ffffff"
                font.pixelSize: 13
                font.bold: true
            }

            Text {
                text: "Are you sure you want to delete '" + deleteConfirmDialog.deleteTargetName + "'?"
                color: (typeof theme !== "undefined" && theme && theme.textPrimary) ? theme.textPrimary : "#cccccc"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Text {
                text: "This action cannot be undone."
                color: (typeof theme !== "undefined" && theme && theme.textMuted) ? theme.textMuted : "#858585"
                font.pixelSize: 11
            }

            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8
                Layout.topMargin: 4

                Button {
                    id: cancelBtn
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: 28
                    contentItem: Text {
                        text: "Cancel"
                        color: cancelBtn.hovered ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 12
                    }
                    background: Rectangle {
                        color: cancelBtn.hovered ? (theme ? theme.bgSurfaceHover : "#3a3d41") : (theme ? theme.bgInput : "#2d2d2d")
                        border.color: theme ? theme.borderNormal : "#454545"
                        border.width: 1
                        radius: 3
                    }
                    onClicked: deleteConfirmDialog.close()
                }

                Button {
                    id: deleteBtn
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: 28
                    contentItem: Text {
                        text: "Delete"
                        color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 12
                        font.bold: true
                    }
                    background: Rectangle {
                        color: deleteBtn.hovered ? "#e03e3e" : (theme ? theme.error : "#f14c4c")
                        radius: 3
                    }
                    onClicked: {
                        deleteConfirmDialog.close();
                        var target = deleteConfirmDialog.deleteTargetPath;
                        if (typeof backend !== "undefined" && backend && backend.delete_file) {
                            backend.delete_file(target);
                        }
                        if (typeof editorArea !== "undefined" && editorArea && editorArea.closeTabByPath) {
                            editorArea.closeTabByPath(target);
                        }
                        for (var i = fileTreeModel.count - 1; i >= 0; i--) {
                            if (fileTreeModel.get(i).fullPath === target) {
                                fileTreeModel.remove(i);
                            }
                        }
                        root.refreshRequested();
                    }
                }
            }
        }
    }

    // =========================================================================
    // HELPER FUNCTIONS & WORKSPACE STATE
    // =========================================================================
    function toggleFolder(fPath) {
        if (!fPath) return;
        var norm = fPath.replace(/\\/g, "/");
        var isCol = root.collapsedFolders[norm] === true;
        var copy = Object.assign({}, root.collapsedFolders);
        copy[norm] = !isCol;
        root.collapsedFolders = copy;
        root.collapseVersion++;
    }

    function expandFolderHierarchy(fPath) {
        if (!fPath) return;
        var norm = fPath.replace(/\\/g, "/");
        var ws = root.workspacePath ? root.workspacePath.replace(/\\/g, "/") : "";
        var copy = Object.assign({}, root.collapsedFolders);
        var changed = false;
        var cur = norm;
        while (cur && cur.length >= ws.length) {
            if (copy[cur] === true) {
                copy[cur] = false;
                changed = true;
            }
            if (cur === ws) break;
            var slash = cur.lastIndexOf("/");
            if (slash <= 0) break;
            cur = cur.substring(0, slash);
        }
        if (changed) {
            root.collapsedFolders = copy;
            root.collapseVersion++;
        }
    }

    function selectAndRevealFile(fPath) {
        if (!fPath) return;
        var norm = fPath.replace(/\\/g, "/");
        root.selectedFilePath = norm;
        root.expandFolderHierarchy(norm);
        for (var i = 0; i < fileTreeModel.count; i++) {
            if (fileTreeModel.get(i).fullPath === norm) {
                fileListView.positionViewAtIndex(i, ListView.Contain);
                break;
            }
        }
    }

    function isItemVisible(parentFullPath, version) {
        if (!parentFullPath) return true;
        var p = parentFullPath.replace(/\\/g, "/");
        var ws = root.workspacePath ? root.workspacePath.replace(/\\/g, "/") : "";
        if (p === ws) return true;

        while (p && p.length > 0) {
            if (root.collapsedFolders[p] === true) {
                return false;
            }
            if (ws && p === ws) break;
            var slash = p.lastIndexOf("/");
            if (slash <= 0) break;
            p = p.substring(0, slash);
        }
        return true;
    }

    function populateModel(rawList, fPath) {
        fileTreeModel.clear();
        root.workspacePath = fPath ? fPath.replace(/\\/g, "/") : "";
        root.workspaceName = (fPath ? fPath.split("/").pop().split("\\").pop() : "") || "PROJECT";

        if (!rawList || rawList.length === 0) return;

        var parentLevelMap = {};
        parentLevelMap[root.workspaceName] = 0;

        var folderPathMap = {};
        folderPathMap[root.workspaceName] = root.workspacePath;

        var existingCollapsed = root.collapsedFolders || {};
        var mergedCollapsed = {};

        for (var i = 0; i < rawList.length; i++) {
            var item = rawList[i];
            var pId = item.parentId || root.workspaceName;
            var parentDir = folderPathMap[pId] || root.workspacePath;
            var fullPath = (parentDir + "/" + item.name).replace(/\\/g, "/");

            if (item.type === "Folder") {
                folderPathMap[item.name] = fullPath;
                if (existingCollapsed[fullPath] !== undefined) {
                    mergedCollapsed[fullPath] = existingCollapsed[fullPath];
                } else {
                    mergedCollapsed[fullPath] = true;
                }
            }

            var level = (parentLevelMap[pId] !== undefined) ? (parentLevelMap[pId] + 1) : 0;
            if (item.type === "Folder") {
                parentLevelMap[item.name] = level;
            }

            fileTreeModel.append({
                name: item.name,
                parentId: item.parentId,
                parentFullPath: parentDir.replace(/\\/g, "/"),
                type: item.type,
                level: level,
                fullPath: fullPath
            });
        }

        root.collapsedFolders = mergedCollapsed;
        root.collapseVersion++;
    }

    function getTargetDirectoryForNewItem() {
        var targetDir = root.workspacePath;
        var targetLevel = 0;
        var insertIdx = fileTreeModel.count;

        if (root.selectedFilePath) {
            for (var i = 0; i < fileTreeModel.count; i++) {
                var item = fileTreeModel.get(i);
                if (item.fullPath === root.selectedFilePath) {
                    if (item.type === "Folder") {
                        targetDir = item.fullPath;
                        targetLevel = item.level + 1;
                        insertIdx = i + 1;
                    } else {
                        targetDir = item.parentFullPath;
                        targetLevel = item.level;
                        insertIdx = i + 1;
                    }
                    break;
                }
            }
        }

        if (!targetDir) {
            targetDir = root.workspacePath || ".";
        }

        return { dir: targetDir, level: targetLevel, insertIdx: insertIdx };
    }

    function startNewFile(customDir) {
        var cDir = (typeof customDir === "string") ? customDir : "";
        var targetInfo = (cDir !== "") ? { dir: cDir, level: 0, insertIdx: fileTreeModel.count } : root.getTargetDirectoryForNewItem();
        var targetDir = targetInfo.dir;
        var targetLevel = targetInfo.level;
        var insertIdx = targetInfo.insertIdx;

        // Rule 2: Unfold collapsed folder and hierarchy
        root.expandFolderHierarchy(targetDir);

        var n = root.nextUntitledIndex;
        var dirSep = (targetDir.endsWith("/") || targetDir.endsWith("\\")) ? "" : "/";
        var candidateName = "Untitled-" + n + ".txt";
        var candidatePath = (targetDir + dirSep + candidateName).replace(/\\/g, "/");

        while (typeof backend !== "undefined" && backend && backend.file_exists && backend.file_exists(candidatePath)) {
            n++;
            candidateName = "Untitled-" + n + ".txt";
            candidatePath = (targetDir + dirSep + candidateName).replace(/\\/g, "/");
        }
        root.nextUntitledIndex = n + 1;

        // 1. Create file on disk
        if (typeof backend !== "undefined" && backend && backend.create_file_on_disk) {
            backend.create_file_on_disk(candidatePath);
        }

        // 2. Add to fileTreeModel if not already present
        var found = false;
        for (var f = 0; f < fileTreeModel.count; f++) {
            if (fileTreeModel.get(f).fullPath === candidatePath) {
                found = true;
                insertIdx = f;
                break;
            }
        }
        if (!found) {
            fileTreeModel.insert(Math.min(insertIdx, fileTreeModel.count), {
                name: candidateName,
                parentId: "",
                parentFullPath: targetDir.replace(/\\/g, "/"),
                type: "File",
                level: targetLevel,
                fullPath: candidatePath
            });
        }

        // 3. Mark for editing & selected
        root.editingFilePath = candidatePath;
        root.selectedFilePath = candidatePath;
        fileListView.positionViewAtIndex(insertIdx, ListView.Contain);

        // 4. Open in editor
        if (typeof backend !== "undefined" && backend && backend.open_file) {
            backend.open_file(candidatePath);
        }
    }

    function startNewFolder(customDir) {
        var cDir = (typeof customDir === "string") ? customDir : "";
        var targetInfo = (cDir !== "") ? { dir: cDir, level: 0, insertIdx: fileTreeModel.count } : root.getTargetDirectoryForNewItem();
        var targetDir = targetInfo.dir;
        var targetLevel = targetInfo.level;
        var insertIdx = targetInfo.insertIdx;

        root.expandFolderHierarchy(targetDir);

        var n = 1;
        var dirSep = (targetDir.endsWith("/") || targetDir.endsWith("\\")) ? "" : "/";
        var candidateName = "New Folder";
        var candidatePath = (targetDir + dirSep + candidateName).replace(/\\/g, "/");

        while (typeof backend !== "undefined" && backend && backend.file_exists && backend.file_exists(candidatePath)) {
            n++;
            candidateName = "New Folder " + n;
            candidatePath = (targetDir + dirSep + candidateName).replace(/\\/g, "/");
        }

        if (typeof backend !== "undefined" && backend && backend.create_folder_on_disk) {
            backend.create_folder_on_disk(candidatePath);
        }

        var found = false;
        for (var f = 0; f < fileTreeModel.count; f++) {
            if (fileTreeModel.get(f).fullPath === candidatePath) {
                found = true;
                insertIdx = f;
                break;
            }
        }
        if (!found) {
            fileTreeModel.insert(Math.min(insertIdx, fileTreeModel.count), {
                name: candidateName,
                parentId: "",
                parentFullPath: targetDir.replace(/\\/g, "/"),
                type: "Folder",
                level: targetLevel,
                fullPath: candidatePath
            });
        }

        root.editingFilePath = candidatePath;
        root.selectedFilePath = candidatePath;
        fileListView.positionViewAtIndex(insertIdx, ListView.Contain);
    }

    function startInlineRename(fPath) {
        if (!fPath) return;
        root.editingFilePath = fPath;
        root.selectedFilePath = fPath;
    }

    function cancelInlineEdit(targetFullPath) {
        var pathToDelete = targetFullPath || root.editingFilePath;
        root.editingFilePath = "";

        if (pathToDelete) {
            var norm = pathToDelete.replace(/\\/g, "/");
            var base = norm.split("/").pop();
            // If it's an unrenamed Untitled file, delete it cleanly
            if (/^Untitled-\d+\.txt$/i.test(base)) {
                if (typeof backend !== "undefined" && backend && backend.delete_file) {
                    backend.delete_file(norm);
                }
                if (typeof editorArea !== "undefined" && editorArea && editorArea.closeTabByPath) {
                    editorArea.closeTabByPath(norm);
                }
                for (var i = fileTreeModel.count - 1; i >= 0; i--) {
                    if (fileTreeModel.get(i).fullPath === norm) {
                        fileTreeModel.remove(i);
                    }
                }
            }
        }
    }

    function canDropItem(srcPath, destDir) {
        if (!srcPath || !destDir) return false;
        var normSrc = srcPath.replace(/\\/g, "/");
        var normDst = destDir.replace(/\\/g, "/");
        if (normSrc === normDst) return false;

        var lastSlash = normSrc.lastIndexOf("/");
        var srcParent = (lastSlash >= 0) ? normSrc.substring(0, lastSlash) : "";
        if (srcParent === normDst) return false;

        if (normDst.startsWith(normSrc + "/")) return false;

        return true;
    }

    function moveItem(srcPath, destDir) {
        if (!root.canDropItem(srcPath, destDir)) return;
        var normSrc = srcPath.replace(/\\/g, "/");
        var normDst = destDir.replace(/\\/g, "/");

        if (typeof backend !== "undefined" && backend && backend.move_file_or_folder) {
            var newPath = backend.move_file_or_folder(normSrc, normDst);
            if (newPath) {
                newPath = newPath.replace(/\\/g, "/");
                if (typeof editorArea !== "undefined" && editorArea && editorArea.renameTabByPath) {
                    editorArea.renameTabByPath(normSrc, newPath);
                }
                root.refreshRequested();
            }
        }
    }

    function commitRenameFile(oldFullPath, newName, parentDir) {
        var trimmedName = (newName || "").trim();
        var oldNorm = (oldFullPath || "").replace(/\\/g, "/");
        var oldBaseName = oldNorm.split("/").pop();

        if (!trimmedName || trimmedName === oldBaseName) {
            root.editingFilePath = "";
            return;
        }

        var invalidChars = /[<>:"/\\|?*]/;
        if (invalidChars.test(trimmedName)) {
            if (typeof backend !== "undefined" && backend && backend.notificationRequested) {
                backend.notificationRequested.emit("Invalid name. Characters <>:\"/\\|?* are not allowed.", "error", "Explorer");
            }
            return;
        }

        var dir = parentDir || root.workspacePath || "";
        var sep = (dir.endsWith("/") || dir.endsWith("\\")) ? "" : "/";
        var newFullPath = (dir ? (dir + sep + trimmedName) : trimmedName).replace(/\\/g, "/");

        if (typeof backend !== "undefined" && backend && backend.file_exists && backend.file_exists(newFullPath) && newFullPath.toLowerCase() !== oldNorm.toLowerCase()) {
            if (backend.notificationRequested) {
                backend.notificationRequested.emit("An item with the name '" + trimmedName + "' already exists.", "warning", "Explorer");
            }
            return;
        }

        root.editingFilePath = "";

        if (typeof backend !== "undefined" && backend) {
            if (backend.rename_file) {
                var success = backend.rename_file(oldNorm, newFullPath);
                if (success) {
                    root.selectedFilePath = newFullPath;
                    // Update model entry
                    for (var i = 0; i < fileTreeModel.count; i++) {
                        if (fileTreeModel.get(i).fullPath === oldNorm) {
                            fileTreeModel.setProperty(i, "name", trimmedName);
                            fileTreeModel.setProperty(i, "fullPath", newFullPath);
                            break;
                        }
                    }
                    if (typeof editorArea !== "undefined" && editorArea && editorArea.renameTabByPath) {
                        editorArea.renameTabByPath(oldNorm, newFullPath);
                    }
                }
            }
        }
    }
}
