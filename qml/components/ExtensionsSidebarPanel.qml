import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import QtCore
import "."

Rectangle {
    id: root

    color: (typeof theme !== "undefined" && theme) ? theme.bgSidebar : "#181818"
    clip: true

    signal extensionSelected(var extensionData)

    property string searchQuery: ""
    property string selectedCategory: "all" // "all", "installed", "marketplace", "frameworks", "formatters"
    property var allExtensions: []
    property var openVsxExtensions: []
    property bool isSearchingOpenVsx: false
    property var installingMap: ({})
    property var statusMsgMap: ({})
    property var statusTypeMap: ({})

    Timer {
        id: searchDebounceTimer
        interval: 350
        repeat: false
        onTriggered: {
            if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.search_open_vsx) {
                root.isSearchingOpenVsx = true;
                extensionManager.search_open_vsx(root.searchQuery);
            }
        }
    }

    onSearchQueryChanged: {
        if (root.selectedCategory === "marketplace" || root.searchQuery.trim().length >= 2) {
            searchDebounceTimer.restart();
        }
    }

    onSelectedCategoryChanged: {
        if (root.selectedCategory === "marketplace") {
            searchDebounceTimer.restart();
        }
    }

    function refreshExtensions() {
        if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.get_installed_extensions) {
            root.allExtensions = extensionManager.get_installed_extensions();
        } else if (typeof backend !== "undefined" && backend && backend.get_installed_extensions) {
            root.allExtensions = backend.get_installed_extensions();
        } else {
            root.allExtensions = [];
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
        function onOpenVsxSearchCompleted(results) {
            root.isSearchingOpenVsx = false;
            root.openVsxExtensions = results || [];
        }
        function onOpenVsxInstallProgress(extId, status, message) {
            var newMap = Object.assign({}, root.installingMap);
            if (status === "done" || status === "error") {
                delete newMap[extId];
            } else {
                newMap[extId] = true;
            }
            root.installingMap = newMap;
            if (status === "done") {
                root.refreshExtensions();
                if (typeof theme !== "undefined" && theme && theme.refreshAvailableThemes) {
                    theme.refreshAvailableThemes();
                }
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification(message, "success", "Extensions");
                }
            } else if (status === "error") {
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification(message, "error", "Extensions");
                }
            }
        }
    }

    FileDialog {
        id: vsixFileDialog
        title: "Install Extension from VSIX / Package"
        nameFilters: ["Extension Packages (*.vsix *.dgxext *.zip)", "All Files (*.*)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: {
            var rawPath = selectedFile.toString();
            var cleanPath = rawPath.replace(/^(file:\/{3}|file:\/{2}|file:\/)/, "");
            cleanPath = decodeURIComponent(cleanPath);

            var ok = false;
            if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.install_local_extension) {
                ok = extensionManager.install_local_extension(cleanPath);
            } else if (typeof backend !== "undefined" && backend && backend.install_local_extension) {
                ok = backend.install_local_extension(cleanPath);
            }

            if (ok) {
                root.refreshExtensions();
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification("Extension package installed successfully!", "success", "Extensions");
                }
            } else {
                if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                    mainWindow.showNotification("Failed to install package. Please ensure it contains a valid manifest.", "error", "Extensions");
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Sidebar Header (VS Code style EXTENSIONS title and top actions)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 35
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8
                spacing: 6

                Text {
                    text: "EXTENSIONS"
                    font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                    font.pixelSize: 11
                    font.bold: true
                    color: (typeof theme !== "undefined" && theme) ? theme.textSecondary : "#858585"
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                // Install from VSIX button
                Rectangle {
                    width: 24
                    height: 24
                    radius: 3
                    color: vsixMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "install"
                        size: 14
                        color: vsixMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textSecondary : "#858585")
                    }

                    ToolTip.visible: vsixMa.containsMouse
                    ToolTip.text: "Install from VSIX / Package..."
                    ToolTip.delay: 350

                    MouseArea {
                        id: vsixMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: vsixFileDialog.open()
                    }
                }

                // Refresh Button
                Rectangle {
                    width: 24
                    height: 24
                    radius: 3
                    color: refMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "refresh"
                        size: 13
                        color: refMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textSecondary : "#858585")
                    }

                    ToolTip.visible: refMa.containsMouse
                    ToolTip.text: "Refresh Extensions"
                    ToolTip.delay: 350

                    MouseArea {
                        id: refMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.refreshExtensions()
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: (typeof theme !== "undefined" && theme) ? theme.borderSubtle : "#252525"
            }
        }

        // 2. Search Box
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            color: "transparent"

            Rectangle {
                anchors.fill: parent
                anchors.margins: 6
                radius: 4
                color: (typeof theme !== "undefined" && theme) ? theme.bgInput : "#222222"
                border.color: searchInput.activeFocus ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderNormal : "#333333")
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 6
                    spacing: 6

                    VectorIcon {
                        name: "search"
                        size: 13
                        color: (typeof theme !== "undefined" && theme) ? theme.textSecondary : "#858585"
                    }

                    TextInput {
                        id: searchInput
                        Layout.fillWidth: true
                        font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                        font.pixelSize: 12
                        color: (typeof theme !== "undefined" && theme) ? theme.textBright : "#ffffff"
                        clip: true
                        selectByMouse: true
                        text: root.searchQuery
                        onTextChanged: root.searchQuery = text

                        Text {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            text: "Search Extensions..."
                            font: searchInput.font
                            color: (typeof theme !== "undefined" && theme) ? theme.textDisabled : "#666666"
                            visible: !searchInput.text && !searchInput.activeFocus
                        }
                    }

                    // Clear search button
                    Rectangle {
                        width: 16
                        height: 16
                        radius: 8
                        color: "transparent"
                        visible: searchInput.text.length > 0

                        Text {
                            anchors.centerIn: parent
                            text: "✕"
                            font.pixelSize: 10
                            color: clrMa.containsMouse ? "#ffffff" : "#888888"
                        }

                        MouseArea {
                            id: clrMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: searchInput.text = ""
                        }
                    }
                }
            }
        }

        // 3. Category Filter Chips (All, Frameworks, Installed, Formatters)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 28
            color: "transparent"

            Row {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 4

                Repeater {
                    model: [
                        { id: "all", label: "All" },
                        { id: "installed", label: "Installed" },
                        { id: "marketplace", label: "Open VSX" },
                        { id: "frameworks", label: "Frameworks" },
                        { id: "formatters", label: "Formatters" }
                    ]

                    Rectangle {
                        height: 22
                        width: chipText.implicitWidth + 14
                        radius: 11
                        color: root.selectedCategory === modelData.id
                               ? ((typeof theme !== "undefined" && theme) ? theme.accent : "#0078d4")
                               : (chipMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2d2d2d") : (theme ? theme.bgPanel : "#202020"))
                        border.color: (typeof theme !== "undefined" && theme) ? theme.borderSubtle : "#333333"
                        border.width: root.selectedCategory === modelData.id ? 0 : 1

                        Text {
                            id: chipText
                            anchors.centerIn: parent
                            text: modelData.label
                            font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                            font.pixelSize: 10
                            font.bold: root.selectedCategory === modelData.id
                            color: root.selectedCategory === modelData.id
                                   ? "#ffffff"
                                   : (theme ? theme.textSecondary : "#999999")
                        }

                        MouseArea {
                            id: chipMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.selectedCategory = modelData.id
                        }
                    }
                }
            }
        }

        // 4. Extensions List
        ListView {
            id: extListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            boundsBehavior: Flickable.StopAtBounds

            model: {
                var list = root.allExtensions || [];
                var q = root.searchQuery.toLowerCase().trim();
                var cat = root.selectedCategory;

                // Build set of installed IDs for fast case-insensitive lookup
                var installedMap = {};
                for (var k = 0; k < list.length; k++) {
                    var eid = (list[k].id || "").toLowerCase();
                    installedMap[eid] = list[k];
                    if (eid.startsWith("dgx.")) {
                        installedMap[eid.substring(4)] = list[k];
                    } else {
                        installedMap["dgx." + eid] = list[k];
                    }
                }

                if (cat === "marketplace") {
                    var mList = root.openVsxExtensions || [];
                    var mFiltered = [];
                    for (var m = 0; m < mList.length; m++) {
                        var mItem = Object.assign({}, mList[m]);
                        var mKey = (mItem.id || "").toLowerCase();
                        var isInst = Boolean(installedMap[mKey]) || ((typeof extensionManager !== "undefined" && extensionManager && extensionManager.is_extension_installed) ? extensionManager.is_extension_installed(mItem.id) : false);
                        if (isInst) {
                            mItem.installed = true;
                            mItem.enabled = installedMap[mKey] ? installedMap[mKey].enabled : true;
                        }
                        if (q.length > 0) {
                            var mName = (mItem.name || "").toLowerCase();
                            var mDesc = (mItem.description || "").toLowerCase();
                            var mAuth = (mItem.author || "").toLowerCase();
                            if (mName.indexOf(q) === -1 && mDesc.indexOf(q) === -1 && mAuth.indexOf(q) === -1) {
                                continue;
                            }
                        }
                        mFiltered.push(mItem);
                    }
                    return mFiltered;
                }

                var filtered = [];
                for (var i = 0; i < list.length; i++) {
                    var ext = list[i];
                    var name = (ext.name || "").toLowerCase();
                    var desc = (ext.description || "").toLowerCase();
                    var author = (ext.author || "").toLowerCase();
                    var category = (ext.category || "").toLowerCase();

                    // Search filter
                    if (q.length > 0 && name.indexOf(q) === -1 && desc.indexOf(q) === -1 && author.indexOf(q) === -1) {
                        continue;
                    }

                    // Category filter
                    if (cat === "installed") {
                        if (!ext.enabled) continue;
                    } else if (cat === "frameworks") {
                        if (category.indexOf("framework") === -1 && category.indexOf("game") === -1 && name.indexOf("framework") === -1 && name.indexOf("unity") === -1 && name.indexOf("godot") === -1 && name.indexOf("react") === -1 && name.indexOf("astro") === -1) {
                            continue;
                        }
                    } else if (cat === "formatters") {
                        if (!ext.formatter && category.indexOf("formatter") === -1 && name.indexOf("formatter") === -1) {
                            continue;
                        }
                    }

                    filtered.push(ext);
                }

                // If searching in "all", also append Open VSX online results not already in local list
                if (cat === "all" && q.length > 0) {
                    var vsxList = root.openVsxExtensions || [];
                    for (var j = 0; j < vsxList.length; j++) {
                        var vExt = Object.assign({}, vsxList[j]);
                        var vKey = (vExt.id || "").toLowerCase();
                        var vInst = Boolean(installedMap[vKey]) || ((typeof extensionManager !== "undefined" && extensionManager && extensionManager.is_extension_installed) ? extensionManager.is_extension_installed(vExt.id) : false);
                        if (!vInst) {
                            filtered.push(vExt);
                        }
                    }
                }

                return filtered;
            }

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
                width: 6
            }

            delegate: Rectangle {
                id: extCard
                width: extListView.width
                height: 72
                color: cardMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#252525") : "transparent"

                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 1
                    color: (typeof theme !== "undefined" && theme) ? theme.borderSubtle : "#222222"
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8

                    // Extension Icon Avatar
                    Rectangle {
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        radius: 5
                        color: {
                            var n = (modelData.name || "").toLowerCase();
                            if (n.indexOf("react") !== -1) return "#087ea4";
                            if (n.indexOf("astro") !== -1) return "#bc52ee";
                            if (n.indexOf("unity") !== -1) return "#222c37";
                            if (n.indexOf("godot") !== -1) return "#478cbf";
                            if (n.indexOf("rust") !== -1) return "#b7410e";
                            if (n.indexOf("python") !== -1) return "#3572A5";
                            return (theme ? theme.bgPanel : "#2a2d2e");
                        }
                        border.color: (theme ? theme.borderSubtle : "#3c3c3c")
                        border.width: 1

                        Image {
                            id: extAvatarImg
                            anchors.centerIn: parent
                            width: 22
                            height: 22
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            source: (modelData && (modelData.iconUrl || modelData.icon)) ? (modelData.iconUrl || modelData.icon) : ""
                            visible: status === Image.Ready
                        }

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "puzzle"
                            size: 16
                            color: "#ffffff"
                            visible: !extAvatarImg.visible
                        }
                    }

                    // Extension Info
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                text: modelData.name || modelData.id
                                font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                                font.pixelSize: 12
                                font.bold: true
                                color: (typeof theme !== "undefined" && theme) ? theme.textBright : "#ffffff"
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            Text {
                                text: "v" + (modelData.version || "1.0.0")
                                font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                                font.pixelSize: 9
                                color: (typeof theme !== "undefined" && theme) ? theme.textDisabled : "#666666"
                            }
                        }

                        Text {
                            text: modelData.description || "Extension package"
                            font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                            font.pixelSize: 10
                            color: (typeof theme !== "undefined" && theme) ? theme.textSecondary : "#858585"
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            maximumLineCount: 1
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                text: modelData.author || "DGX Studio"
                                font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                                font.pixelSize: 9
                                color: (typeof theme !== "undefined" && theme) ? theme.textDisabled : "#666666"
                            }

                            Item { Layout.fillWidth: true }

                            // Enable / Disable / Install Action
                            Rectangle {
                                width: (modelData.is_marketplace && !modelData.installed) ? 66 : 56
                                height: 18
                                radius: 3
                                color: (modelData.is_marketplace && !modelData.installed)
                                       ? ((typeof theme !== "undefined" && theme) ? theme.accent : "#0078d4")
                                       : (modelData.enabled
                                          ? ((typeof theme !== "undefined" && theme) ? theme.bgSurfaceHover : "#333333")
                                          : ((typeof theme !== "undefined" && theme) ? theme.accent : "#0078d4"))
                                border.color: (typeof theme !== "undefined" && theme) ? theme.borderNormal : "#444444"
                                border.width: 1
                                opacity: root.installingMap[modelData.id] ? 0.6 : 1.0

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 4

                                    VectorIcon {
                                        visible: modelData.is_marketplace && !modelData.installed
                                        name: root.installingMap[modelData.id] ? "refresh" : "install"
                                        size: 10
                                        color: "#ffffff"
                                    }

                                    Text {
                                        text: {
                                            if (root.installingMap[modelData.id]) return "Installing…";
                                            if (modelData.is_marketplace && !modelData.installed) return "Install";
                                            return modelData.enabled ? "Disable" : "Enable";
                                        }
                                        font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                                        font.pixelSize: 9
                                        font.bold: true
                                        color: (modelData.enabled && !(modelData.is_marketplace && !modelData.installed))
                                               ? ((typeof theme !== "undefined" && theme) ? theme.textPrimary : "#cccccc")
                                               : "#ffffff"
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: root.installingMap[modelData.id] ? Qt.ArrowCursor : Qt.PointingHandCursor
                                    onClicked: {
                                        if (root.installingMap[modelData.id]) return;
                                        if (modelData.is_marketplace && !modelData.installed) {
                                            var newMap = Object.assign({}, root.installingMap);
                                            newMap[modelData.id] = true;
                                            root.installingMap = newMap;
                                            if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.install_from_open_vsx) {
                                                extensionManager.install_from_open_vsx(modelData.downloadUrl, modelData.id, modelData.name);
                                            }
                                            return;
                                        }
                                        var targetId = modelData.id;
                                        var newSt = !modelData.enabled;
                                        if (typeof extensionManager !== "undefined" && extensionManager && extensionManager.toggle_extension) {
                                            extensionManager.toggle_extension(targetId, newSt);
                                            root.refreshExtensions();
                                        } else if (typeof backend !== "undefined" && backend && backend.toggle_extension) {
                                            backend.toggle_extension(targetId, newSt);
                                            root.refreshExtensions();
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                MouseArea {
                    id: cardMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    z: -1
                    onClicked: {
                        root.extensionSelected(modelData);
                    }
                }
            }

            // Empty placeholder
            Item {
                anchors.centerIn: parent
                width: parent.width - 40
                height: 120
                visible: extListView.count === 0

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 8

                    VectorIcon {
                        name: "puzzle"
                        size: 28
                        color: (typeof theme !== "undefined" && theme) ? theme.textDisabled : "#555555"
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Text {
                        text: root.searchQuery ? "No matching extensions found." : "No extensions available."
                        font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                        font.pixelSize: 11
                        color: (typeof theme !== "undefined" && theme) ? theme.textDisabled : "#666666"
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }

        // 5. Bottom "Install from VSIX" Quick Action Bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            color: (typeof theme !== "undefined" && theme) ? theme.bgPanel : "#202020"
            border.color: (typeof theme !== "undefined" && theme) ? theme.borderSubtle : "#282828"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 6

                VectorIcon {
                    name: "puzzle"
                    size: 13
                    color: (typeof theme !== "undefined" && theme) ? theme.accent : "#0078d4"
                }

                Text {
                    text: "Install from VSIX..."
                    font.family: (typeof theme !== "undefined" && theme) ? theme.fontFamily : "Segoe UI"
                    font.pixelSize: 11
                    color: btmVsixMa.containsMouse ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                    Layout.fillWidth: true
                }
            }

            MouseArea {
                id: btmVsixMa
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: vsixFileDialog.open()
            }
        }
    }
}

