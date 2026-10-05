import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import QtCore
import "."

Rectangle {
    id: root

    signal closeRequested()

    width: 880
    height: 620
    radius: theme ? theme.radiusMd : 6
    color: theme ? theme.bgPopup : "#1e1e1e"
    border.color: theme ? theme.borderNormal : "#333333"
    border.width: 1
    clip: true

    property string searchQuery: ""
    property string selectedCategory: "all" // "all", "formatters", "installed", "missing"
    property var allExtensions: []
    property var selectedExt: null
    property int selectedIndex: 0
    property string copyFeedbackText: ""
    property var installingMap: ({})
    property var statusMsgMap: ({})
    property var statusTypeMap: ({})

    Timer {
        id: feedbackTimer
        interval: 2000
        repeat: false
        onTriggered: root.copyFeedbackText = ""
    }

    function refreshExtensions() {
        if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.get_installed_extensions) {
            allExtensions = extensionManager.get_installed_extensions();
        } else if (typeof backend !== "undefined" && backend && backend.get_installed_extensions) {
            allExtensions = backend.get_installed_extensions();
        } else {
            allExtensions = [];
        }

        // Keep selection valid
        if (allExtensions.length > 0) {
            if (selectedIndex >= allExtensions.length || selectedIndex < 0) selectedIndex = 0;
            selectedExt = allExtensions[selectedIndex];
        } else {
            selectedExt = null;
        }
    }

    Component.onCompleted: {
        refreshExtensions();
    }

    Connections {
        target: typeof extensionManager !== "undefined" ? extensionManager : (typeof backend !== "undefined" ? backend : null)
        ignoreUnknownSignals: true
        function onExtensionsChanged() {
            root.refreshExtensions();
        }
        function onFormatterInstallProgress(extId, status, msg) {
            var newMap = Object.assign({}, root.installingMap);
            var newMsgMap = Object.assign({}, root.statusMsgMap);
            var newTypeMap = Object.assign({}, root.statusTypeMap);

            if (status === "installing") {
                newMap[extId] = true;
                newMsgMap[extId] = msg;
                newTypeMap[extId] = "installing";
            } else if (status === "success") {
                delete newMap[extId];
                newMsgMap[extId] = msg;
                newTypeMap[extId] = "success";
                root.refreshExtensions();
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification(msg, "success", "Extensions");
                }
            } else if (status === "failed") {
                delete newMap[extId];
                newMsgMap[extId] = msg;
                newTypeMap[extId] = "failed";
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification("Installation failed: " + msg, "error", "Extensions");
                }
            }
            root.installingMap = newMap;
            root.statusMsgMap = newMsgMap;
            root.statusTypeMap = newTypeMap;
        }
    }

    FileDialog {
        id: locateBinaryDialog
        title: "Select Formatter Executable"
        nameFilters: ["Executable Files (*.exe *.cmd *.bat *)", "All Files (*.*)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: {
            var file = selectedFile.toString();
            if (root.selectedExt) {
                var ok = false;
                if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.set_custom_formatter_path) {
                    ok = extensionManager.set_custom_formatter_path(root.selectedExt.id, file);
                } else if (typeof backend !== "undefined" && backend && backend.set_custom_formatter_path) {
                    ok = backend.set_custom_formatter_path(root.selectedExt.id, file);
                }
                if (ok) {
                    root.refreshExtensions();
                    if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                        mainWindow.showNotification("Custom formatter path configured successfully!", "success", "Extensions");
                    }
                } else {
                    if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                        mainWindow.showNotification("Selected file is not a valid executable.", "error", "Extensions");
                    }
                }
            }
        }
    }

    // Native Dialogs for File/Folder Install
    FolderDialog {
        id: installFolderDialog
        title: "Select Extension Folder to Install"
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: {
            var folder = selectedFolder.toString();
            var success = false;
            if (typeof extensionManager !== "undefined" && extensionManager) {
                success = extensionManager.install_local_extension(folder);
            } else if (typeof backend !== "undefined" && backend) {
                success = backend.install_local_extension(folder);
            }
            if (success) {
                root.refreshExtensions();
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification("Extension installed successfully from folder!", "success", "Extensions");
                }
            } else {
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification("Failed to install extension. Please make sure the folder contains a valid extension.json file.", "error", "Extensions");
                }
            }
        }
    }

    FileDialog {
        id: installFileDialog
        title: "Select Extension Package (.zip, .vsix, extension.json)"
        nameFilters: ["Extension Packages (*.zip *.vsix *.json)", "Zip Archives (*.zip *.vsix)", "JSON Manifests (*.json)", "All Files (*.*)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: {
            var file = selectedFile.toString();
            var success = false;
            if (typeof extensionManager !== "undefined" && extensionManager) {
                success = extensionManager.install_local_extension(file);
            } else if (typeof backend !== "undefined" && backend) {
                success = backend.install_local_extension(file);
            }
            if (success) {
                root.refreshExtensions();
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification("Extension installed successfully from package!", "success", "Extensions");
                }
            } else {
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification("Failed to install extension. Please verify the archive contains a valid extension.json manifest.", "error", "Extensions");
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Header Bar (Draggable)
        Rectangle {
            id: headerRect
            Layout.fillWidth: true
            height: 44
            color: theme ? theme.bgHeader : "#181818"

            // Draggable Area (Left portion)
            MouseArea {
                anchors.fill: parent
                anchors.rightMargin: 380
                drag.target: root
                drag.axis: Drag.XAndYAxis
                cursorShape: Qt.SizeAllCursor
                acceptedButtons: Qt.LeftButton
                z: 0
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 14
                spacing: 10
                z: 1

                VectorIcon {
                    name: "puzzle"
                    size: 16
                    color: theme ? theme.accent : "#0078d4"
                }

                Text {
                    text: "Extensions & Language Formatters"
                    color: theme ? theme.textBright : "#ffffff"
                    font.pixelSize: 13
                    font.bold: true
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                }

                Item { Layout.fillWidth: true }

                // Install from Folder Button
                Rectangle {
                    width: 130
                    height: 26
                    radius: 4
                    color: installFolderMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : (theme ? theme.bgSurface : "#252526")
                    border.color: theme ? theme.borderSubtle : "#3e3e42"
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        VectorIcon {
                            name: "folder"
                            size: 12
                            color: theme ? theme.accent : "#0078d4"
                        }
                        Text {
                            text: "Install Folder..."
                            font.pixelSize: 11
                            color: theme ? theme.textPrimary : "#cccccc"
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        }
                    }

                    MouseArea {
                        id: installFolderMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: installFolderDialog.open()
                    }
                }

                // Install from ZIP / Package Button
                Rectangle {
                    width: 130
                    height: 26
                    radius: 4
                    color: installZipMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : (theme ? theme.bgSurface : "#252526")
                    border.color: theme ? theme.borderSubtle : "#3e3e42"
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        VectorIcon {
                            name: "download"
                            size: 12
                            color: theme ? theme.accent : "#0078d4"
                        }
                        Text {
                            text: "Install from File..."
                            font.pixelSize: 11
                            color: theme ? theme.textPrimary : "#cccccc"
                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                        }
                    }

                    MouseArea {
                        id: installZipMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: installFileDialog.open()
                    }
                }

                // Reload Button
                Rectangle {
                    width: 28
                    height: 26
                    radius: 4
                    color: reloadMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : "transparent"
                    border.color: reloadMa.containsMouse ? (theme ? theme.borderSubtle : "#3e3e42") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "refresh"
                        size: 13
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    MouseArea {
                        id: reloadMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (typeof extensionManager !== "undefined" && extensionManager) {
                                extensionManager.reload_extensions();
                            } else if (typeof backend !== "undefined" && backend && backend.reload_extensions) {
                                backend.reload_extensions();
                            }
                            root.refreshExtensions();
                        }
                    }
                }

                // Close Button
                Rectangle {
                    width: 28
                    height: 26
                    radius: 4
                    color: closeMa.containsMouse ? "#e81123" : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "close"
                        size: 11
                        color: closeMa.containsMouse ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                    }

                    MouseArea {
                        id: closeMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.closeRequested()
                    }
                }
            }
        }

        // Header Divider
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: theme ? theme.borderSubtle : "#282828"
        }

        // 2. Main Body Split Area
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            RowLayout {
                anchors.fill: parent
                spacing: 0

                // =============================================================
                // LEFT PANE: Extension List & Filter
                // =============================================================
                Rectangle {
                    Layout.preferredWidth: 340
                    Layout.fillHeight: true
                    color: theme ? theme.bgPanel : "#181818"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        // Search Input
                        Rectangle {
                            Layout.fillWidth: true
                            height: 30
                            radius: 4
                            color: theme ? theme.bgSurface : "#252526"
                            border.color: searchInput.activeFocus ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderSubtle : "#3e3e42")
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 6

                                VectorIcon {
                                    name: "search"
                                    size: 12
                                    color: theme ? theme.textMuted : "#656565"
                                }

                                TextInput {
                                    id: searchInput
                                    Layout.fillWidth: true
                                    font.pixelSize: 11
                                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                    color: theme ? theme.textPrimary : "#cccccc"
                                    clip: true
                                    selectByMouse: true
                                    onTextChanged: {
                                        root.searchQuery = text;
                                    }

                                    Text {
                                        text: "Filter extensions..."
                                        color: theme ? theme.textMuted : "#656565"
                                        font.pixelSize: 11
                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                        visible: !searchInput.text && !searchInput.activeFocus
                                    }
                                }

                                VectorIcon {
                                    name: "close"
                                    size: 10
                                    color: theme ? theme.textMuted : "#656565"
                                    visible: searchInput.text.length > 0
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            searchInput.text = "";
                                        }
                                    }
                                }
                            }
                        }

                        // Filter Pills
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Repeater {
                                model: [
                                    { id: "all", label: "All" },
                                    { id: "formatters", label: "Formatters" },
                                    { id: "missing", label: "Missing Tools" },
                                    { id: "installed", label: "User-Added" }
                                ]

                                delegate: Rectangle {
                                    height: 22
                                    radius: 3
                                    Layout.fillWidth: true
                                    color: root.selectedCategory === modelData.id ? (theme ? theme.accent : "#0078d4") : (pillMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")
                                    border.color: root.selectedCategory === modelData.id ? "transparent" : (theme ? theme.borderSubtle : "#333333")
                                    border.width: 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.label
                                        font.pixelSize: 10
                                        font.bold: root.selectedCategory === modelData.id
                                        color: root.selectedCategory === modelData.id ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                    }

                                    MouseArea {
                                        id: pillMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.selectedCategory = modelData.id
                                    }
                                }
                            }
                        }

                        // Extensions ListView
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            ListView {
                                id: extListView
                                anchors.fill: parent
                                spacing: 4

                                model: {
                                    var list = root.allExtensions || [];
                                    var q = root.searchQuery.toLowerCase().trim();
                                    var cat = root.selectedCategory;

                                    return list.filter(function(item) {
                                        if (cat === "formatters" && !item.hasFormatter) return false;
                                        if (cat === "missing" && (!item.hasFormatter || item.formatterInstalled)) return false;
                                        if (cat === "installed" && !item.isUserInstalled) return false;

                                        if (!q) return true;
                                        var name = (item.name || "").toLowerCase();
                                        var desc = (item.description || "").toLowerCase();
                                        var langs = (item.languages || []).join(" ").toLowerCase();
                                        var dep = (item.formatterDependency || "").toLowerCase();
                                        return name.indexOf(q) !== -1 || desc.indexOf(q) !== -1 || langs.indexOf(q) !== -1 || dep.indexOf(q) !== -1;
                                    });
                                }

                                delegate: Rectangle {
                                    width: extListView.width
                                    height: 64
                                    radius: 4
                                    color: (root.selectedExt && root.selectedExt.id === modelData.id) ? (theme ? theme.bgSurfaceActive : "#37373d") : (cardMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : (theme ? theme.bgSurface : "#1e1e1e"))
                                    border.color: (root.selectedExt && root.selectedExt.id === modelData.id) ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderSubtle : "#2d2d30")
                                    border.width: 1

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        spacing: 8

                                        // Extension Language Icon / Badge
                                        Rectangle {
                                            width: 36
                                            height: 36
                                            radius: 4
                                            color: modelData.enabled ? (theme ? theme.accentSubtle : "#1a2736") : "#252526"
                                            border.color: modelData.enabled ? (theme ? theme.accent : "#0078d4") : "#3e3e42"
                                            border.width: 1

                                            VectorIcon {
                                                anchors.centerIn: parent
                                                name: modelData.hasFormatter ? "code" : "puzzle"
                                                size: 16
                                                color: modelData.enabled ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                                            }
                                        }

                                        // Extension Meta
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 2

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 4

                                                Text {
                                                    text: modelData.name
                                                    font.pixelSize: 11
                                                    font.bold: true
                                                    color: modelData.enabled ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textMuted : "#656565")
                                                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                }

                                                Text {
                                                    text: "v" + modelData.version
                                                    font.pixelSize: 9
                                                    color: theme ? theme.textMuted : "#656565"
                                                }
                                            }

                                            // Formatter dependency pill
                                            RowLayout {
                                                spacing: 4
                                                visible: modelData.hasFormatter

                                                Rectangle {
                                                    width: 6
                                                    height: 6
                                                    radius: 3
                                                    color: modelData.formatterInstalled ? "#4ec9b0" : "#d7ba7d"
                                                }

                                                Text {
                                                    text: modelData.formatterDependency + (modelData.formatterInstalled ? " (Ready)" : " (Missing)")
                                                    font.pixelSize: 9
                                                    color: modelData.formatterInstalled ? "#4ec9b0" : "#d7ba7d"
                                                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                                }
                                            }

                                            // Languages chips
                                            Text {
                                                text: (modelData.languages || []).slice(0, 4).join(", ")
                                                font.pixelSize: 9
                                                color: theme ? theme.textMuted : "#656565"
                                                elide: Text.ElideRight
                                                visible: !modelData.hasFormatter
                                            }
                                        }
                                    }

                                    MouseArea {
                                        id: cardMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.selectedExt = modelData;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Vertical Divider
                Rectangle {
                    Layout.fillHeight: true
                    width: 1
                    color: theme ? theme.borderSubtle : "#282828"
                }

                // =============================================================
                // RIGHT PANE: Extension Detail Inspector & Dependency Helper
                // =============================================================
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: theme ? theme.bgSurface : "#1e1e1e"

                    ScrollView {
                        id: rightDetailScroll
                        anchors.fill: parent
                        anchors.margins: 16
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded

                        Column {
                            width: Math.max(260, rightDetailScroll.availableWidth)
                            spacing: 14
                            visible: root.selectedExt !== null

                            // 1. Extension Header
                            RowLayout {
                                width: parent.width
                                spacing: 12

                                Rectangle {
                                    width: 46
                                    height: 46
                                    radius: 6
                                    color: (root.selectedExt && root.selectedExt.enabled) ? (theme ? theme.accentSubtle : "#1a2736") : "#252526"
                                    border.color: (root.selectedExt && root.selectedExt.enabled) ? (theme ? theme.accent : "#0078d4") : "#3e3e42"
                                    border.width: 1

                                    VectorIcon {
                                        anchors.centerIn: parent
                                        name: (root.selectedExt && root.selectedExt.hasFormatter) ? "code" : "puzzle"
                                        size: 22
                                        color: (root.selectedExt && root.selectedExt.enabled) ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3

                                    RowLayout {
                                        spacing: 6
                                        Text {
                                            text: root.selectedExt ? root.selectedExt.name : ""
                                            font.pixelSize: 15
                                            font.bold: true
                                            color: theme ? theme.textBright : "#ffffff"
                                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                        }

                                        Rectangle {
                                            height: 18
                                            width: isBuiltInText.width + 10
                                            radius: 3
                                            color: (root.selectedExt && root.selectedExt.isBuiltIn) ? "#2d3748" : "#2b4c38"

                                            Text {
                                                id: isBuiltInText
                                                anchors.centerIn: parent
                                                text: (root.selectedExt && root.selectedExt.isBuiltIn) ? "Built-in" : "User Package"
                                                font.pixelSize: 9
                                                color: (root.selectedExt && root.selectedExt.isBuiltIn) ? "#a0aec0" : "#68d391"
                                                font.bold: true
                                            }
                                        }
                                    }

                                    Text {
                                        text: "Version: " + (root.selectedExt ? root.selectedExt.version : "") + " | Author: " + (root.selectedExt ? root.selectedExt.author : "") + " | ID: " + (root.selectedExt ? root.selectedExt.id : "")
                                        font.pixelSize: 10
                                        color: theme ? theme.textSecondary : "#858585"
                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                    }
                                }
                            }

                            // 2. Action Controls Bar (Enable / Disable / Uninstall / Open Folder)
                            RowLayout {
                                width: parent.width
                                spacing: 8

                                // Toggle Enable/Disable Button
                                Rectangle {
                                    width: 120
                                    height: 28
                                    radius: 4
                                    color: toggleMa.containsMouse ? (theme ? theme.accentHover : "#0062a8") : (theme ? theme.accent : "#0078d4")

                                    RowLayout {
                                        anchors.centerIn: parent
                                        spacing: 6
                                        VectorIcon {
                                            name: (root.selectedExt && root.selectedExt.enabled) ? "close" : "play"
                                            size: 11
                                            color: "#ffffff"
                                        }
                                        Text {
                                            text: (root.selectedExt && root.selectedExt.enabled) ? "Disable" : "Enable"
                                            color: "#ffffff"
                                            font.pixelSize: 11
                                            font.bold: true
                                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                        }
                                    }

                                    MouseArea {
                                        id: toggleMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (!root.selectedExt) return;
                                            var newEnabled = !root.selectedExt.enabled;
                                            if (typeof extensionManager !== "undefined" && extensionManager) {
                                                extensionManager.toggle_extension(root.selectedExt.id, newEnabled);
                                            } else if (typeof backend !== "undefined" && backend) {
                                                backend.toggle_extension(root.selectedExt.id, newEnabled);
                                            }
                                            root.refreshExtensions();
                                        }
                                    }
                                }

                                // Uninstall Button (Active for user-installed extensions)
                                Rectangle {
                                    width: 100
                                    height: 28
                                    radius: 4
                                    visible: root.selectedExt && root.selectedExt.isUserInstalled
                                    color: uninstallMa.containsMouse ? "#d83b01" : "#3e2723"
                                    border.color: "#d83b01"
                                    border.width: 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: "Uninstall"
                                        color: "#ffffff"
                                        font.pixelSize: 11
                                        font.bold: true
                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                    }

                                    MouseArea {
                                        id: uninstallMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (!root.selectedExt) return;
                                            if (typeof extensionManager !== "undefined" && extensionManager) {
                                                extensionManager.uninstall_extension(root.selectedExt.id);
                                            } else if (typeof backend !== "undefined" && backend) {
                                                backend.uninstall_extension(root.selectedExt.id);
                                            }
                                            root.refreshExtensions();
                                        }
                                    }
                                }

                                // Open Folder on Disk
                                Rectangle {
                                    width: 140
                                    height: 28
                                    radius: 4
                                    color: openFolderMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : (theme ? theme.bgPanel : "#181818")
                                    border.color: theme ? theme.borderSubtle : "#3e3e42"
                                    border.width: 1

                                    RowLayout {
                                        anchors.centerIn: parent
                                        spacing: 6
                                        VectorIcon {
                                            name: "folder"
                                            size: 11
                                            color: theme ? theme.textSecondary : "#858585"
                                        }
                                        Text {
                                            text: "Open Folder on Disk"
                                            color: theme ? theme.textPrimary : "#cccccc"
                                            font.pixelSize: 11
                                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                        }
                                    }

                                    MouseArea {
                                        id: openFolderMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (!root.selectedExt) return;
                                            if (typeof extensionManager !== "undefined" && extensionManager) {
                                                extensionManager.open_extension_folder(root.selectedExt.id);
                                            } else if (typeof backend !== "undefined" && backend) {
                                                backend.open_extension_folder(root.selectedExt.id);
                                            }
                                        }
                                    }
                                }
                            }

                            // 3. Description
                            Text {
                                width: parent.width
                                text: root.selectedExt ? root.selectedExt.description : ""
                                font.pixelSize: 12
                                color: theme ? theme.textPrimary : "#cccccc"
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                wrapMode: Text.WordWrap
                            }

                            // 4. FORMATTER DEPENDENCY INSPECTOR
                            Rectangle {
                                id: formatterCard
                                width: parent.width
                                radius: 6
                                color: theme ? theme.bgPanel : "#181818"
                                border.color: (root.selectedExt && root.selectedExt.hasFormatter && !root.selectedExt.formatterInstalled) ? "#6b5829" : (theme ? theme.borderSubtle : "#2d2d30")
                                border.width: 1
                                height: depCol.implicitHeight + 24
                                visible: Boolean(root.selectedExt && root.selectedExt.hasFormatter)

                                readonly property bool isExtInstalling: Boolean(root.selectedExt && root.installingMap[root.selectedExt.id])
                                readonly property string extStatusMsg: (root.selectedExt && root.statusMsgMap[root.selectedExt.id]) || ""
                                readonly property string extStatusType: (root.selectedExt && root.statusTypeMap[root.selectedExt.id]) || ""
                                readonly property bool isExtReady: Boolean(root.selectedExt && root.selectedExt.formatterInstalled && !isExtInstalling)

                                Column {
                                    id: depCol
                                    width: parent.width - 24
                                    x: 12
                                    y: 12
                                    spacing: 10

                                    // Header Row with Status Pill
                                    RowLayout {
                                        width: parent.width
                                        spacing: 8

                                        VectorIcon {
                                            name: formatterCard.isExtReady ? "check" : (formatterCard.isExtInstalling ? "bolt" : "warning")
                                            size: 13
                                            color: formatterCard.isExtReady ? "#4ec9b0" : (formatterCard.isExtInstalling ? "#60a5fa" : "#d7ba7d")
                                        }

                                        Text {
                                            text: "FORMATTER DEPENDENCY: " + (root.selectedExt ? root.selectedExt.formatterDependency : "")
                                            font.pixelSize: 11
                                            font.bold: true
                                            color: formatterCard.isExtReady ? "#4ec9b0" : (formatterCard.isExtInstalling ? "#60a5fa" : "#d7ba7d")
                                            font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }

                                        // Status Pill
                                        Rectangle {
                                            height: 20
                                            width: statusPillText.width + 14
                                            radius: 10
                                            color: formatterCard.isExtReady ? "#1b4d3e" : (formatterCard.isExtInstalling ? "#1a365d" : "#3d3018")

                                            Text {
                                                id: statusPillText
                                                anchors.centerIn: parent
                                                text: formatterCard.isExtReady ? "Ready" : (formatterCard.isExtInstalling ? "Installing…" : "Executable Missing")
                                                font.pixelSize: 10
                                                font.bold: true
                                                color: formatterCard.isExtReady ? "#4ec9b0" : (formatterCard.isExtInstalling ? "#60a5fa" : "#d7ba7d")
                                            }
                                        }
                                    }

                                    // When Ready / Installed: Show Detected Executable Path & Option to Change
                                    Column {
                                        width: parent.width
                                        spacing: 6
                                        visible: formatterCard.isExtReady

                                        Text {
                                            text: "Detected Executable Location:"
                                            font.pixelSize: 10
                                            color: theme ? theme.textSecondary : "#858585"
                                            font.bold: true
                                        }

                                        Rectangle {
                                            width: parent.width
                                            height: 28
                                            radius: 3
                                            color: "#121418"
                                            border.color: "#2a2d34"
                                            border.width: 1

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 8
                                                anchors.rightMargin: 6
                                                spacing: 6

                                                Text {
                                                    text: root.selectedExt ? root.selectedExt.formatterDetectedPath : ""
                                                    font.pixelSize: 10
                                                    font.family: "Consolas, monospace"
                                                    color: "#4ec9b0"
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideMiddle
                                                }

                                                Rectangle {
                                                    width: 80
                                                    height: 20
                                                    radius: 2
                                                    color: changeBinaryMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : (theme ? theme.bgPanel : "#181818")
                                                    border.color: theme ? theme.borderSubtle : "#3e3e42"
                                                    border.width: 1

                                                    Text {
                                                        anchors.centerIn: parent
                                                        text: "Change..."
                                                        font.pixelSize: 9
                                                        color: theme ? theme.textPrimary : "#cccccc"
                                                    }

                                                    MouseArea {
                                                        id: changeBinaryMa
                                                        anchors.fill: parent
                                                        hoverEnabled: true
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: locateBinaryDialog.open()
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // When Missing / Installing
                                    Column {
                                        width: parent.width
                                        spacing: 8
                                        visible: !formatterCard.isExtReady

                                        Text {
                                            width: parent.width
                                            text: root.selectedExt ? root.selectedExt.installInstructions : "Install the external formatter executable to enable code formatting."
                                            font.pixelSize: 11
                                            color: theme ? theme.textPrimary : "#cccccc"
                                            wrapMode: Text.WordWrap
                                        }

                                        // Status / Progress / Error Banner
                                        Rectangle {
                                            width: parent.width
                                            height: bannerText.implicitHeight + 12
                                            radius: 3
                                            visible: Boolean(formatterCard.extStatusMsg)
                                            color: formatterCard.extStatusType === "failed" ? "#381818" : (formatterCard.extStatusType === "success" ? "#143324" : "#16283d")
                                            border.color: formatterCard.extStatusType === "failed" ? "#7f2323" : (formatterCard.extStatusType === "success" ? "#237f48" : "#2563eb")
                                            border.width: 1

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 8
                                                anchors.rightMargin: 8
                                                spacing: 6

                                                VectorIcon {
                                                    name: formatterCard.extStatusType === "failed" ? "warning" : (formatterCard.extStatusType === "success" ? "check" : "bolt")
                                                    size: 11
                                                    color: formatterCard.extStatusType === "failed" ? "#f87171" : (formatterCard.extStatusType === "success" ? "#4ec9b0" : "#60a5fa")
                                                }

                                                Text {
                                                    id: bannerText
                                                    text: formatterCard.extStatusMsg
                                                    font.pixelSize: 10
                                                    color: formatterCard.extStatusType === "failed" ? "#fca5a5" : (formatterCard.extStatusType === "success" ? "#a7f3d0" : "#bfdbfe")
                                                    wrapMode: Text.WordWrap
                                                    Layout.fillWidth: true
                                                }
                                            }
                                        }

                                        // Action Buttons Flow (Responsive wrap)
                                        Flow {
                                            width: parent.width
                                            spacing: 6

                                            // 1. Primary "Install Formatter" Button
                                            Rectangle {
                                                width: 130
                                                height: 26
                                                radius: 3
                                                enabled: !formatterCard.isExtInstalling
                                                opacity: enabled ? 1.0 : 0.6
                                                color: formatterCard.isExtInstalling ? "#1a365d" : (installBtnMa.containsMouse ? (theme ? theme.accentHover : "#0062a8") : (theme ? theme.accent : "#0078d4"))

                                                RowLayout {
                                                    anchors.centerIn: parent
                                                    spacing: 5

                                                    VectorIcon {
                                                        name: formatterCard.isExtInstalling ? "bolt" : "download"
                                                        size: 11
                                                        color: "#ffffff"
                                                    }

                                                    Text {
                                                        text: formatterCard.isExtInstalling ? "Installing…" : "Install Formatter"
                                                        font.pixelSize: 10
                                                        color: "#ffffff"
                                                        font.bold: true
                                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                                    }
                                                }

                                                MouseArea {
                                                    id: installBtnMa
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: parent.enabled ? Qt.PointingHandCursor : Qt.ForbiddenCursor
                                                    onClicked: {
                                                        if (!root.selectedExt || formatterCard.isExtInstalling) return;
                                                        var extId = root.selectedExt.id;

                                                        var newMap = Object.assign({}, root.installingMap);
                                                        var newMsgMap = Object.assign({}, root.statusMsgMap);
                                                        var newTypeMap = Object.assign({}, root.statusTypeMap);
                                                        newMap[extId] = true;
                                                        newMsgMap[extId] = "Starting lightweight installation...";
                                                        newTypeMap[extId] = "installing";
                                                        root.installingMap = newMap;
                                                        root.statusMsgMap = newMsgMap;
                                                        root.statusTypeMap = newTypeMap;

                                                        if (typeof extensionManager !== "undefined" && extensionManager) {
                                                            extensionManager.install_formatter(extId);
                                                        } else if (typeof backend !== "undefined" && backend) {
                                                            backend.install_formatter(extId);
                                                        }
                                                    }
                                                }
                                            }

                                            // 2. "Select Binary..." Button
                                            Rectangle {
                                                width: 115
                                                height: 26
                                                radius: 3
                                                color: selectBinaryMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : (theme ? theme.bgPanel : "#181818")
                                                border.color: theme ? theme.borderSubtle : "#3e3e42"
                                                border.width: 1

                                                RowLayout {
                                                    anchors.centerIn: parent
                                                    spacing: 4

                                                    VectorIcon {
                                                        name: "folder"
                                                        size: 10
                                                        color: theme ? theme.textSecondary : "#858585"
                                                    }

                                                    Text {
                                                        text: "Select Binary..."
                                                        font.pixelSize: 10
                                                        color: theme ? theme.textPrimary : "#cccccc"
                                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                                    }
                                                }

                                                MouseArea {
                                                    id: selectBinaryMa
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: locateBinaryDialog.open()
                                                }
                                            }

                                            // 3. "Copy Command" Button
                                            Rectangle {
                                                width: 105
                                                height: 26
                                                radius: 3
                                                color: copyCmdMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d30") : (theme ? theme.bgPanel : "#181818")
                                                border.color: theme ? theme.borderSubtle : "#3e3e42"
                                                border.width: 1

                                                RowLayout {
                                                    anchors.centerIn: parent
                                                    spacing: 4

                                                    VectorIcon {
                                                        name: root.copyFeedbackText ? "check" : "copy"
                                                        size: 10
                                                        color: root.copyFeedbackText ? "#4ec9b0" : (theme ? theme.textSecondary : "#858585")
                                                    }

                                                    Text {
                                                        text: root.copyFeedbackText ? root.copyFeedbackText : "Copy Command"
                                                        font.pixelSize: 10
                                                        color: root.copyFeedbackText ? "#4ec9b0" : (theme ? theme.textPrimary : "#cccccc")
                                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                                    }
                                                }

                                                MouseArea {
                                                    id: copyCmdMa
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        if (!root.selectedExt || !root.selectedExt.installCommand) return;
                                                        if (typeof extensionManager !== "undefined" && extensionManager) {
                                                            extensionManager.copy_to_clipboard(root.selectedExt.installCommand);
                                                        } else if (typeof backend !== "undefined" && backend) {
                                                            backend.copy_to_clipboard(root.selectedExt.installCommand);
                                                        }
                                                        root.copyFeedbackText = "Copied!";
                                                        feedbackTimer.restart();
                                                    }
                                                }
                                            }
                                        }

                                        // Command Preview Box
                                        Rectangle {
                                            width: parent.width
                                            height: 26
                                            radius: 3
                                            color: "#121418"
                                            border.color: "#282c34"
                                            border.width: 1
                                            visible: Boolean(root.selectedExt && root.selectedExt.installCommand)

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 8
                                                anchors.rightMargin: 8

                                                Text {
                                                    text: root.selectedExt ? root.selectedExt.installCommand : ""
                                                    font.pixelSize: 10
                                                    font.family: "Consolas, monospace"
                                                    color: "#85e89d"
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                            }
                                        }

                                        // Docs URL Link
                                        Rectangle {
                                            height: 20
                                            width: docsText.width + 8
                                            radius: 2
                                            color: "transparent"
                                            visible: Boolean(root.selectedExt && root.selectedExt.docsUrl)

                                            Text {
                                                id: docsText
                                                anchors.centerIn: parent
                                                text: "🔗 Official Documentation & Manual Setup"
                                                font.pixelSize: 10
                                                color: theme ? theme.accent : "#0078d4"
                                                font.underline: true
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    if (root.selectedExt && root.selectedExt.docsUrl) {
                                                        if (typeof backend !== "undefined" && backend && backend.open_external_url) {
                                                            backend.open_external_url(root.selectedExt.docsUrl);
                                                        } else {
                                                            Qt.openUrlExternally(root.selectedExt.docsUrl);
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // 5. Supported Languages and Extensions Tags
                            Column {
                                width: parent.width
                                spacing: 6

                                Text {
                                    text: "Supported Languages & File Types:"
                                    font.pixelSize: 11
                                    font.bold: true
                                    color: theme ? theme.textSecondary : "#858585"
                                }

                                Flow {
                                    width: parent.width
                                    spacing: 4

                                    Repeater {
                                        model: root.selectedExt ? root.selectedExt.languages : []
                                        delegate: Rectangle {
                                            height: 20
                                            width: langTagText.width + 10
                                            radius: 3
                                            color: theme ? theme.bgPanel : "#181818"
                                            border.color: theme ? theme.borderSubtle : "#333333"

                                            Text {
                                                id: langTagText
                                                anchors.centerIn: parent
                                                text: modelData
                                                font.pixelSize: 10
                                                color: theme ? theme.textPrimary : "#cccccc"
                                            }
                                        }
                                    }

                                    Repeater {
                                        model: root.selectedExt ? root.selectedExt.extensions : []
                                        delegate: Rectangle {
                                            height: 20
                                            width: extTagText.width + 10
                                            radius: 3
                                            color: theme ? theme.bgPanel : "#181818"
                                            border.color: theme ? theme.borderSubtle : "#333333"

                                            Text {
                                                id: extTagText
                                                anchors.centerIn: parent
                                                text: modelData
                                                font.pixelSize: 10
                                                color: theme ? theme.textMuted : "#858585"
                                                font.family: "Consolas, monospace"
                                            }
                                        }
                                    }
                                }
                            }

                            // 6. Installation Location
                            Column {
                                width: parent.width
                                spacing: 2

                                Text {
                                    text: "Location on disk:"
                                    font.pixelSize: 10
                                    color: theme ? theme.textSecondary : "#858585"
                                    font.bold: true
                                }
                                Text {
                                    width: parent.width
                                    text: root.selectedExt ? root.selectedExt.path : ""
                                    font.pixelSize: 10
                                    font.family: "Consolas, monospace"
                                    color: theme ? theme.textMuted : "#656565"
                                    wrapMode: Text.WrapAnywhere
                                }
                            }
                        }
                    }

                    // Empty Selection State
                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 12
                        visible: root.selectedExt === null

                        VectorIcon {
                            name: "puzzle"
                            size: 40
                            color: theme ? theme.textMuted : "#555555"
                            Layout.alignment: Qt.AlignHCenter
                        }

                        Text {
                            text: "No Extension Selected"
                            font.pixelSize: 14
                            font.bold: true
                            color: theme ? theme.textSecondary : "#858585"
                            Layout.alignment: Qt.AlignHCenter
                        }

                        Text {
                            text: "Select an extension from the list or install a new package."
                            font.pixelSize: 11
                            color: theme ? theme.textMuted : "#656565"
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }
            }
        }
    }
}
