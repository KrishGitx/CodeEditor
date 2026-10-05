import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property int activeCategoryIndex: 0
    property string searchQuery: ""

    function matchesSearch(title, subtitle) {
        if (!root.searchQuery || !root.searchQuery.trim()) return true;
        var q = root.searchQuery.toLowerCase().trim();
        var t = (title || "").toLowerCase();
        var s = (subtitle || "").toLowerCase();
        return t.indexOf(q) !== -1 || s.indexOf(q) !== -1;
    }

    signal closeRequested()
    signal themeSelected(string themeName)
    signal extensionsRequested()

    width: 760
    height: 560
    radius: theme ? theme.radiusMd : 6
    color: theme ? theme.bgPopup : "#252526"
    border.color: theme ? theme.borderNormal : "#333333"
    border.width: 1

    property var categories: [
        { name: "General", icon: "settings" },
        { name: "Appearance", icon: "sparkles" },
        { name: "Editor", icon: "file" },
        { name: "Terminal", icon: "code" },
        { name: "Shortcuts", icon: "keyboard" },
        { name: "Radial Menu", icon: "zen" }
    ]

    property var radialConfigItems: []

    function loadRadialConfig() {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_radial_menu_config) {
            radialConfigItems = settingsBackend.get_radial_menu_config() || [];
        }
    }

    function saveRadialConfig() {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.save_radial_menu_config) {
            settingsBackend.save_radial_menu_config(JSON.stringify(radialConfigItems));
        }
    }

    function resetRadialConfig() {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.reset_radial_menu_config) {
            radialConfigItems = settingsBackend.reset_radial_menu_config() || [];
        }
    }

    property var themeList: [
        { id: "obsidian", name: "Obsidian Dark", color: "#181818" },
        { id: "midnight", name: "Midnight Navy", color: "#0f131a" },
        { id: "dracula", name: "Dracula", color: "#282a36" },
        { id: "nord", name: "Nord Arctic", color: "#2e3440" },
        { id: "monokai", name: "Monokai Pro", color: "#272822" },
        { id: "light", name: "Clean Light", color: "#f8f9fa" },
        { id: "paper", name: "Paper Warm", color: "#f5f2eb" },
        { id: "glass", name: "Frosted Glass", color: "#141822" }
    ]

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 1. Settings Header Bar (Draggable)
        Rectangle {
            id: headerRect
            Layout.fillWidth: true
            height: 42
            color: theme ? theme.bgHeader : "#181818"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 12
                spacing: 8
                z: 0

                VectorIcon {
                    name: "settings"
                    size: 14
                    color: theme ? theme.accent : "#0078d4"
                }

                Text {
                    text: "Preferences"
                    color: theme ? theme.textBright : "#ffffff"
                    font.pixelSize: 13
                    font.bold: true
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                    Layout.fillWidth: true
                }

                Item {
                    width: 26
                    height: 26
                    z: 10

                    Rectangle {
                        anchors.fill: parent
                        radius: 3
                        color: closeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"

                        VectorIcon {
                            anchors.centerIn: parent
                            name: "close"
                            size: 10
                            color: theme ? theme.textSecondary : "#858585"
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

            // Draggable Header Area
            MouseArea {
                anchors.fill: parent
                anchors.rightMargin: 44
                drag.target: root
                drag.axis: Drag.XAndYAxis
                cursorShape: Qt.SizeAllCursor
                acceptedButtons: Qt.LeftButton
                z: 5
            }
        }

        // Header Divider
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: theme ? theme.borderSubtle : "#282828"
        }

        // 1.5 Interactive Search Bar
        Rectangle {
            Layout.fillWidth: true
            height: 42
            color: theme ? theme.bgSidebar : "#1b1b1d"
            border.color: theme ? theme.borderSubtle : "#282828"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 10

                VectorIcon {
                    name: "search"
                    size: 12
                    color: searchInput.activeFocus ? (theme ? theme.accent : "#0078d4") : (theme ? theme.textMuted : "#656565")
                }

                TextInput {
                    id: searchInput
                    Layout.fillWidth: true
                    text: root.searchQuery
                    color: theme ? theme.textBright : "#ffffff"
                    font.pixelSize: 12
                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                    selectByMouse: true
                    clip: true

                    Text {
                        anchors.fill: parent
                        verticalAlignment: Text.AlignVCenter
                        text: "Search settings, themes, AI, shortcuts, runner..."
                        color: theme ? theme.textMuted : "#656565"
                        font.pixelSize: 12
                        font.italic: true
                        visible: !searchInput.text && !searchInput.activeFocus
                    }

                    onTextChanged: {
                        root.searchQuery = text;
                    }
                }

                Rectangle {
                    width: 20
                    height: 20
                    radius: 10
                    color: clearSearchMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent"
                    visible: root.searchQuery.length > 0

                    VectorIcon {
                        anchors.centerIn: parent
                        name: "close"
                        size: 8
                        color: theme ? theme.textSecondary : "#858585"
                    }

                    MouseArea {
                        id: clearSearchMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            searchInput.text = "";
                            root.searchQuery = "";
                        }
                    }
                }
            }
        }

        // 2. Main Content Split
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // Category Sidebar
            Rectangle {
                Layout.preferredWidth: 170
                Layout.fillHeight: true
                color: theme ? theme.bgSidebar : "#181818"

                ListView {
                    anchors.fill: parent
                    anchors.margins: 8
                    model: root.categories
                    spacing: 4

                    delegate: Rectangle {
                        width: parent ? parent.width : 154
                        height: 36
                        radius: theme ? theme.radiusSm : 4
                        color: (root.searchQuery.length === 0 && index === root.activeCategoryIndex) ? (theme ? theme.bgSelected : "#04395e") : (catMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : "transparent")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 10

                            VectorIcon {
                                name: modelData.icon
                                size: 13
                                color: (root.searchQuery.length === 0 && index === root.activeCategoryIndex) ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textSecondary : "#858585")
                            }

                            Text {
                                text: modelData.name
                                color: (root.searchQuery.length === 0 && index === root.activeCategoryIndex) ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                font.pixelSize: 12
                                font.bold: (root.searchQuery.length === 0 && index === root.activeCategoryIndex)
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                Layout.fillWidth: true
                            }
                        }

                        MouseArea {
                            id: catMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                searchInput.text = "";
                                root.searchQuery = "";
                                root.activeCategoryIndex = index;
                            }
                        }
                    }
                }
            }

            // Vertical Sidebar Divider
            Rectangle {
                Layout.fillHeight: true
                width: 1
                color: theme ? theme.borderSubtle : "#282828"
            }

            // Detail Settings View with StackLayout
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: theme ? theme.bgEditor : "#1e1e1e"

                StackLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    currentIndex: root.searchQuery.length > 0 ? 6 : root.activeCategoryIndex

                    // =========================================================
                    // 0. GENERAL TAB
                    // =========================================================
                    ScrollView {
                        id: generalScroll
                        clip: true
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Column {
                            width: Math.max(380, generalScroll.availableWidth)
                            spacing: 14

                            Text {
                                text: "General Settings"
                                color: theme ? theme.textBright : "#ffffff"
                                font.pixelSize: 15
                                font.bold: true
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            }

                            Item { width: 1; height: 6 }


                            // AI Assistant (Beta) Toggle
                            SettingToggleItem {
                                width: parent.width
                                title: "AI Assistant (Beta)"
                                subtitle: "Enable ChatGPT AI code assistant, smart debugging, and workspace panel"
                                checked: theme ? theme.enableAI : true
                                onToggled: function(c) {
                                    if (theme) {
                                        theme.enableAI = c;
                                        theme.saveSettings();
                                    }
                                }
                            }

                            // HTML File Run Target Selector
                            Rectangle {
                                width: parent.width
                                height: 72
                                radius: theme ? theme.radiusSm : 4
                                color: theme ? theme.bgSurface : "#252526"
                                border.color: theme ? theme.borderSubtle : "#282828"
                                border.width: 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 6

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text {
                                            text: "HTML File Run Action (Radial Menu / F5)"
                                            color: theme ? theme.textPrimary : "#cccccc"
                                            font.pixelSize: 12
                                            font.bold: true
                                        }
                                        Item { Layout.fillWidth: true }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        // Built-in Live Preview Button
                                        Rectangle {
                                            Layout.fillWidth: true
                                            height: 28
                                            radius: 3
                                            color: (!theme || theme.htmlRunTarget === "built_in") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgInput : "#1e1e1e")
                                            border.color: (!theme || theme.htmlRunTarget === "built_in") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderNormal : "#333333")

                                            Row {
                                                anchors.centerIn: parent
                                                spacing: 6
                                                VectorIcon { anchors.verticalCenter: parent.verticalCenter; name: "sparkles"; size: 10; color: "#ffffff" }
                                                Text {
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text: "Built-in Live Preview Tab"
                                                    color: (!theme || theme.htmlRunTarget === "built_in") ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                                    font.pixelSize: 11
                                                    font.bold: (!theme || theme.htmlRunTarget === "built_in")
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    if (theme) {
                                                        theme.htmlRunTarget = "built_in";
                                                        theme.saveSettings();
                                                    }
                                                }
                                            }
                                        }

                                        // External Browser Button
                                        Rectangle {
                                            Layout.fillWidth: true
                                            height: 28
                                            radius: 3
                                            color: (theme && theme.htmlRunTarget === "browser") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgInput : "#1e1e1e")
                                            border.color: (theme && theme.htmlRunTarget === "browser") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderNormal : "#333333")

                                            Row {
                                                anchors.centerIn: parent
                                                spacing: 6
                                                VectorIcon { anchors.verticalCenter: parent.verticalCenter; name: "code"; size: 10; color: "#ffffff" }
                                                Text {
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text: "Default Web Browser"
                                                    color: (theme && theme.htmlRunTarget === "browser") ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                                    font.pixelSize: 11
                                                    font.bold: (theme && theme.htmlRunTarget === "browser")
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    if (theme) {
                                                        theme.htmlRunTarget = "browser";
                                                        theme.saveSettings();
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            SettingToggleItem {
                                width: parent.width
                                title: "Smooth UI Animations"
                                subtitle: "Enable smooth state transitions and micro-interactions"
                                checked: theme ? theme.enableAnimations : true
                                onToggled: function(c) { if (theme) theme.enableAnimations = c; }
                            }

                            SettingToggleItem {
                                width: parent.width
                                title: "Vinyl Spin Animation"
                                subtitle: "Rotate vinyl record cover during music playback"
                                checked: theme ? theme.enableVinylAnimation : true
                                onToggled: function(c) { if (theme) theme.enableVinylAnimation = c; }
                            }
                        }
                    }

                    // =========================================================
                    // 1. APPEARANCE TAB
                    // =========================================================
                    ScrollView {
                        id: appearanceScroll
                        clip: true
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Column {
                            width: Math.max(380, appearanceScroll.availableWidth)
                            spacing: 14

                            Text {
                                text: "Appearance & Themes"
                                color: theme ? theme.textBright : "#ffffff"
                                font.pixelSize: 15
                                font.bold: true
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            }

                            Item { width: 1; height: 6 }

                            Text {
                                text: "Color Theme"
                                color: theme ? theme.textSecondary : "#858585"
                                font.pixelSize: 11
                                font.bold: true
                            }

                            Grid {
                                width: parent.width
                                columns: 2
                                spacing: 10

                                Repeater {
                                    model: root.themeList

                                    delegate: Rectangle {
                                        width: (parent.width - 10) / 2
                                        height: 44
                                        radius: theme ? theme.radiusSm : 4
                                        color: (theme && theme.currentTheme === modelData.id) ? (theme ? theme.bgSelected : "#04395e") : (themeItemMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : (theme ? theme.bgSurface : "#252526"))
                                        border.color: (theme && theme.currentTheme === modelData.id) ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderNormal : "#333333")
                                        border.width: 1

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 12
                                            anchors.rightMargin: 12
                                            spacing: 10

                                            Rectangle {
                                                width: 16
                                                height: 16
                                                radius: 8
                                                color: modelData.color
                                                border.color: "#555555"
                                                border.width: 1
                                            }

                                            Text {
                                                text: modelData.name
                                                color: (theme && theme.currentTheme === modelData.id) ? (theme ? theme.textBright : "#ffffff") : (theme ? theme.textPrimary : "#cccccc")
                                                font.pixelSize: 12
                                                font.bold: (theme && theme.currentTheme === modelData.id)
                                                Layout.fillWidth: true
                                            }
                                        }

                                        MouseArea {
                                            id: themeItemMa
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (theme) {
                                                    theme.setTheme(modelData.id);
                                                    root.themeSelected(modelData.id);
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // =========================================================
                    // 2. EDITOR TAB
                    // =========================================================
                    ScrollView {
                        id: editorScroll
                        clip: true
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Column {
                            width: Math.max(380, editorScroll.availableWidth)
                            spacing: 14

                            Text {
                                text: "Editor Preferences"
                                color: theme ? theme.textBright : "#ffffff"
                                font.pixelSize: 15
                                font.bold: true
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            }

                            Item { width: 1; height: 6 }

                            // Context Menu Style Selector (Radial vs Standard)
                            Rectangle {
                                width: parent.width
                                height: 56
                                radius: theme ? theme.radiusSm : 4
                                color: theme ? theme.bgSurface : "#252526"
                                border.color: theme ? theme.borderSubtle : "#282828"
                                border.width: 1

                                Column {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 3

                                    Text {
                                        text: "Right-Click Context Menu"
                                        color: theme ? theme.textPrimary : "#cccccc"
                                        font.pixelSize: 12
                                        font.bold: true
                                    }

                                    Text {
                                        text: "Choose radial hold-and-drag gesture or classic popup menu"
                                        color: theme ? theme.textMuted : "#656565"
                                        font.pixelSize: 10
                                    }
                                }

                                Row {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 8

                                    // Radial Button
                                    Rectangle {
                                        width: 82
                                        height: 30
                                        radius: 3
                                        color: (theme && theme.contextMenuStyle === "radial") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgSurfaceHover : "#2a2d2e")

                                        Text {
                                            anchors.centerIn: parent
                                            text: "Radial"
                                            color: (theme && theme.contextMenuStyle === "radial") ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                            font.pixelSize: 11
                                            font.bold: (theme && theme.contextMenuStyle === "radial")
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (theme) theme.contextMenuStyle = "radial";
                                            }
                                        }
                                    }

                                    // Standard Button
                                    Rectangle {
                                        width: 82
                                        height: 30
                                        radius: 3
                                        color: (theme && theme.contextMenuStyle === "standard") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgSurfaceHover : "#2a2d2e")

                                        Text {
                                            anchors.centerIn: parent
                                            text: "Standard"
                                            color: (theme && theme.contextMenuStyle === "standard") ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                            font.pixelSize: 11
                                            font.bold: (theme && theme.contextMenuStyle === "standard")
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (theme) theme.contextMenuStyle = "standard";
                                            }
                                        }
                                    }
                                }
                            }

                            SettingToggleItem {
                                width: parent.width
                                title: "Code Minimap"
                                subtitle: "Display live code overview scroll minimap on the right edge"
                                checked: theme ? theme.enableMinimap : true
                                onToggled: function(c) { if (theme) theme.enableMinimap = c; }
                            }

                            SettingToggleItem {
                                width: parent.width
                                title: "Line Numbers Gutter"
                                subtitle: "Display line numbers in editor gutter"
                                checked: theme ? theme.enableLineNumbers : true
                                onToggled: function(c) { if (theme) theme.enableLineNumbers = c; }
                            }

                            SettingToggleItem {
                                width: parent.width
                                title: "Bracket Matching & Auto-Closing"
                                subtitle: "Automatically insert closing brackets and quotes"
                                checked: theme ? theme.enableBracketMatching : true
                                onToggled: function(c) { if (theme) theme.enableBracketMatching = c; }
                            }

                            SettingToggleItem {
                                width: parent.width
                                title: "Word Wrap"
                                subtitle: "Wrap long lines to fit within editor width"
                                checked: theme ? theme.enableWordWrap : false
                                onToggled: function(c) { if (theme) theme.enableWordWrap = c; }
                            }

                            // Font Size Stepper with Explicit Anchors
                            Rectangle {
                                width: parent.width
                                height: 52
                                radius: theme ? theme.radiusSm : 4
                                color: theme ? theme.bgSurface : "#252526"
                                border.color: theme ? theme.borderSubtle : "#282828"
                                border.width: 1

                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Editor Font Size"
                                    color: theme ? theme.textPrimary : "#cccccc"
                                    font.pixelSize: 12
                                    font.bold: true
                                }

                                Row {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 8

                                    Rectangle {
                                        width: 28
                                        height: 28
                                        radius: 3
                                        color: theme ? theme.bgSurfaceHover : "#2a2d2e"

                                        Text {
                                            anchors.centerIn: parent
                                            text: "−"
                                            color: theme ? theme.textBright : "#ffffff"
                                            font.pixelSize: 14
                                            font.bold: true
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (theme) theme.editorFontSize = Math.max(10, theme.editorFontSize - 1);
                                            }
                                        }
                                    }

                                    Rectangle {
                                        width: 50
                                        height: 28
                                        color: "transparent"

                                        Text {
                                            anchors.centerIn: parent
                                            text: (theme ? theme.editorFontSize : 13) + " px"
                                            color: theme ? theme.textBright : "#ffffff"
                                            font.pixelSize: 12
                                            font.bold: true
                                        }
                                    }

                                    Rectangle {
                                        width: 28
                                        height: 28
                                        radius: 3
                                        color: theme ? theme.bgSurfaceHover : "#2a2d2e"

                                        Text {
                                            anchors.centerIn: parent
                                            text: "+"
                                            color: theme ? theme.textBright : "#ffffff"
                                            font.pixelSize: 14
                                            font.bold: true
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                if (theme) theme.editorFontSize = Math.min(24, theme.editorFontSize + 1);
                                            }
                                        }
                                    }
                                }
                            }

                            // Setting: Mouse Wheel Zoom
                            Rectangle {
                                width: parent.width
                                height: 50
                                color: "transparent"

                                Column {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 3

                                    Text {
                                        text: "Mouse Wheel Zoom"
                                        color: theme ? theme.textPrimary : "#cccccc"
                                        font.pixelSize: 13
                                        font.bold: true
                                    }

                                    Text {
                                        text: "Zoom font size when scrolling with mouse wheel and holding Ctrl"
                                        color: theme ? theme.textMuted : "#858585"
                                        font.pixelSize: 11
                                    }
                                }

                                Switch {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    checked: (typeof theme !== "undefined" && theme) ? theme.enableMouseWheelZoom : true
                                    onToggled: {
                                        if (typeof theme !== "undefined" && theme) {
                                            theme.enableMouseWheelZoom = checked;
                                            theme.saveSettings();
                                        }
                                    }
                                }
                            }
                            // Setting: Enable Breadcrumbs
                            SettingToggleItem {
                                width: parent.width
                                title: "Enable Breadcrumbs"
                                subtitle: "Show file path and document symbol navigation bar above editor"
                                checked: (typeof theme !== "undefined" && theme && typeof theme.enableBreadcrumbs !== "undefined") ? theme.enableBreadcrumbs : true
                                onToggled: function(c) {
                                    if (typeof theme !== "undefined" && theme) {
                                        theme.enableBreadcrumbs = c;
                                        if (theme.saveSettings) theme.saveSettings();
                                    }
                                }
                            }
                        }
                    }

                    // =========================================================
                    // 3. TERMINAL TAB
                    // =========================================================
                    ScrollView {
                        id: terminalScroll
                        clip: true
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Column {
                            width: Math.max(380, terminalScroll.availableWidth)
                            spacing: 14

                            Text {
                                text: "Terminal Settings"
                                color: theme ? theme.textBright : "#ffffff"
                                font.pixelSize: 15
                                font.bold: true
                                font.family: theme ? theme.fontFamilyUi : "sans-serif"
                            }

                            Item { width: 1; height: 6 }

                            Rectangle {
                                width: parent.width
                                height: 64
                                radius: theme ? theme.radiusSm : 4
                                color: theme ? theme.bgSurface : "#252526"
                                border.color: theme ? theme.borderSubtle : "#282828"
                                border.width: 1

                                Column {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 4

                                    Text {
                                        text: "Integrated Terminal: PowerShell / Windows Shell"
                                        color: theme ? theme.textPrimary : "#cccccc"
                                        font.pixelSize: 12
                                        font.bold: true
                                    }

                                    Text {
                                        text: "Shortcut: Ctrl+` | Split terminal with Split button"
                                        color: theme ? theme.textMuted : "#656565"
                                        font.pixelSize: 11
                                    }
                                }
                            }
                        }
                    }

                    // =========================================================
                    // 4. SHORTCUTS TAB
                    // =========================================================
                    ScrollView {
                        id: shortcutsScroll
                        clip: true
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Column {
                            width: Math.max(380, shortcutsScroll.availableWidth)
                            spacing: 10

                            RowLayout {
                                width: parent.width
                                spacing: 8

                                Text {
                                    text: "Keyboard Shortcuts"
                                    color: theme ? theme.textBright : "#ffffff"
                                    font.pixelSize: 15
                                    font.bold: true
                                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                    Layout.fillWidth: true
                                }

                                // Reset All Shortcuts Button
                                Rectangle {
                                    width: 130
                                    height: 26
                                    radius: theme ? theme.radiusSm : 3
                                    color: resetScMa.containsMouse ? (theme ? theme.bgSurfaceActive : "#37373d") : (theme ? theme.bgSurface : "#252526")
                                    border.color: theme ? theme.borderNormal : "#333333"
                                    border.width: 1

                                    RowLayout {
                                        anchors.centerIn: parent
                                        spacing: 6

                                        VectorIcon {
                                            name: "undo"
                                            size: 11
                                            color: theme ? theme.accent : "#0078d4"
                                        }

                                        Text {
                                            text: "Reset Defaults"
                                            color: theme ? theme.textPrimary : "#cccccc"
                                            font.pixelSize: 11
                                            font.bold: true
                                        }
                                    }

                                    MouseArea {
                                        id: resetScMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (theme && theme.resetShortcuts) {
                                                theme.resetShortcuts();
                                            }
                                        }
                                    }
                                }
                            }

                            Text {
                                text: "Click any shortcut box to edit its keybinding."
                                color: theme ? theme.textMuted : "#656565"
                                font.pixelSize: 11
                            }

                            Item { width: 1; height: 4 }

                            // Navigation Shortcuts Section Header
                            Text {
                                text: "Navigation & Search"
                                color: theme ? theme.accent : "#38bdf8"
                                font.pixelSize: 12
                                font.bold: true
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Quick Open File"
                                subtitle: "Search files by name/path and open instantly"
                                currentShortcut: theme ? theme.shortcutQuickOpen : "Ctrl+P"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutQuickOpen = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Go to Line"
                                subtitle: "Jump directly to a specific line number"
                                currentShortcut: theme ? theme.shortcutGoToLine : "Ctrl+G"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutGoToLine = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Rename Symbol"
                                subtitle: "Semantic symbol rename across the document"
                                currentShortcut: theme ? theme.shortcutRenameSymbol : "F2"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutRenameSymbol = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Find in Buffer"
                                subtitle: "Search for text matching query in active editor"
                                currentShortcut: theme ? theme.shortcutFind : "Ctrl+F"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutFind = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Find & Replace"
                                subtitle: "Search and replace occurrences in active editor"
                                currentShortcut: theme ? theme.shortcutReplace : "Ctrl+H"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutReplace = val; }
                            }

                            Item { width: 1; height: 4 }

                            // Editing & Multi-Cursor Section Header
                            Text {
                                text: "Editing & Multi-Cursor"
                                color: theme ? theme.accent : "#38bdf8"
                                font.pixelSize: 12
                                font.bold: true
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Undo"
                                subtitle: "Undo last edit in active buffer"
                                currentShortcut: theme ? theme.shortcutUndo : "Ctrl+Z"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutUndo = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Redo"
                                subtitle: "Redo previously undone edit"
                                currentShortcut: theme ? theme.shortcutRedo : "Ctrl+Y"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutRedo = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Copy / Copy Line"
                                subtitle: "Copy selection, or copy entire line when no selection"
                                currentShortcut: theme ? theme.shortcutCopy : "Ctrl+C"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutCopy = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Paste"
                                subtitle: "Paste clipboard contents at cursor"
                                currentShortcut: theme ? theme.shortcutPaste : "Ctrl+V"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutPaste = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Add Next Occurrence (Multi-Cursor)"
                                subtitle: "Select next matching word occurrence and add a cursor"
                                currentShortcut: theme ? theme.shortcutMultiCursor : "Ctrl+D"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutMultiCursor = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Add Cursor (Mouse)"
                                subtitle: "Add another cursor at clicked position"
                                currentShortcut: theme ? theme.shortcutAddCursor : "Alt+Click"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutAddCursor = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Toggle Line Comment"
                                subtitle: "Comment or uncomment current line / selection"
                                currentShortcut: theme ? theme.shortcutComment : "Ctrl+/"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutComment = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Format Document"
                                subtitle: "Auto-format active code buffer according to language standard"
                                currentShortcut: theme ? theme.shortcutFormat : "Shift+Alt+F"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutFormat = val; }
                            }

                            Item { width: 1; height: 4 }

                            // General Shortcuts
                            Text {
                                text: "General & Workspace"
                                color: theme ? theme.accent : "#38bdf8"
                                font.pixelSize: 12
                                font.bold: true
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Run Active File"
                                subtitle: "Compile / execute active file in integrated terminal"
                                currentShortcut: theme ? theme.shortcutRun : "F5"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutRun = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Save File"
                                subtitle: "Save modifications in active buffer to disk"
                                currentShortcut: theme ? theme.shortcutSave : "Ctrl+S"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutSave = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Save As"
                                subtitle: "Save active buffer with a new filename"
                                currentShortcut: theme ? theme.shortcutSaveAs : "Ctrl+Shift+S"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutSaveAs = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Toggle Integrated Terminal"
                                subtitle: "Show or hide bottom PowerShell / CMD terminal"
                                currentShortcut: theme ? theme.shortcutToggleTerminal : "Ctrl+`"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutToggleTerminal = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Toggle Explorer Panel"
                                subtitle: "Show or hide left project file tree"
                                currentShortcut: theme ? theme.shortcutToggleExplorer : "Ctrl+B"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutToggleExplorer = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "New File"
                                subtitle: "Create an empty unsaved document tab"
                                currentShortcut: theme ? theme.shortcutNewFile : "Ctrl+N"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutNewFile = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Open File"
                                subtitle: "Open an existing source code file"
                                currentShortcut: theme ? theme.shortcutOpenFile : "Ctrl+O"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutOpenFile = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Open Workspace Folder"
                                subtitle: "Open directory in project explorer tree"
                                currentShortcut: theme ? theme.shortcutOpenFolder : "Ctrl+Shift+O"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutOpenFolder = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Close Tab"
                                subtitle: "Close currently active document tab"
                                currentShortcut: theme ? theme.shortcutCloseTab : "Ctrl+W"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutCloseTab = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Toggle Zen Focus Mode"
                                subtitle: "Hide all sidebars and chrome for distraction-free coding"
                                currentShortcut: theme ? theme.shortcutZenMode : "Ctrl+Shift+Z"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutZenMode = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Toggle AI Assistant"
                                subtitle: "Open or close AI coding assistant panel"
                                currentShortcut: theme ? theme.shortcutToggleAI : "Ctrl+Shift+A"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutToggleAI = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Toggle Music Player"
                                subtitle: "Open or close music player streaming panel"
                                currentShortcut: theme ? theme.shortcutToggleMusic : "Ctrl+Shift+M"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutToggleMusic = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Whiteboard Architecture Canvas"
                                subtitle: "Open or close visual architecture design & plan canvas"
                                currentShortcut: theme ? theme.shortcutWhiteboard : "Ctrl+Alt+W"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutWhiteboard = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                title: "Preferences / Settings"
                                subtitle: "Open IDE Preferences modal"
                                currentShortcut: theme ? theme.shortcutSettings : "Ctrl+,"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutSettings = val; }
                            }

                            Item { width: 1; height: 16 }
                        }
                    }

                    // =========================================================
                    // 5. RADIAL CONTEXT MENU TAB (Live Visual Preview & Customizer)
                    // =========================================================
                    Item {
                        id: radialSettingsTab
                        clip: true

                        RowLayout {
                            anchors.fill: parent
                            spacing: 16

                            // Left Column: Configuration List & Controls
                            ColumnLayout {
                                Layout.fillHeight: true
                                Layout.preferredWidth: 370
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        text: "Radial Context Menu"
                                        color: theme ? theme.textBright : "#ffffff"
                                        font.pixelSize: 15
                                        font.bold: true
                                        font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                        Layout.fillWidth: true
                                    }

                                    // Add Button
                                    Rectangle {
                                        width: 86
                                        height: 24
                                        radius: 4
                                        color: addMa.containsMouse ? (theme ? theme.accentHover : "#1084d8") : (theme ? theme.accent : "#0078d4")

                                        Text {
                                            anchors.centerIn: parent
                                            text: "+ Add Action"
                                            color: "#ffffff"
                                            font.pixelSize: 11
                                            font.bold: true
                                        }

                                        MouseArea {
                                            id: addMa
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                var arr = root.radialConfigItems.slice();
                                                arr.push({
                                                    id: "custom_" + Date.now(),
                                                    label: "Custom " + (arr.length + 1),
                                                    icon: "code",
                                                    shortcut: "CMD",
                                                    action_type: "bash",
                                                    enabled: true,
                                                    custom: true,
                                                    action: "echo 'Custom action executed'"
                                                });
                                                root.radialConfigItems = arr;
                                                root.saveRadialConfig();
                                            }
                                        }
                                    }

                                    // Reset Button
                                    Rectangle {
                                        width: 60
                                        height: 24
                                        radius: 4
                                        color: resetMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#333333") : (theme ? theme.bgSurface : "#252526")
                                        border.color: theme ? theme.borderNormal : "#3c3c3c"
                                        border.width: 1

                                        Text {
                                            anchors.centerIn: parent
                                            text: "Reset"
                                            color: theme ? theme.textSecondary : "#cccccc"
                                            font.pixelSize: 11
                                        }

                                        MouseArea {
                                            id: resetMa
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.resetRadialConfig()
                                        }
                                    }
                                }

                                Text {
                                    text: "Configure radial buttons, reorder, toggle, and add custom Bash / CMD commands."
                                    color: theme ? theme.textMuted : "#888888"
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }

                                ScrollView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                                    ListView {
                                        id: radialConfigListView
                                        width: parent.width
                                        model: root.radialConfigItems
                                        spacing: 6

                                        delegate: Rectangle {
                                            width: radialConfigListView.width - 8
                                            height: modelData.custom ? 70 : 48
                                            radius: 6
                                            color: theme ? theme.bgSurface : "#252526"
                                            border.color: modelData.custom ? (theme ? theme.accent : "#38bdf8") : (theme ? theme.borderNormal : "#333333")
                                            border.width: 1

                                            ColumnLayout {
                                                anchors.fill: parent
                                                anchors.margins: 6
                                                spacing: 4

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 6

                                                    // Reorder Buttons (Up / Down)
                                                    Column {
                                                        spacing: 2
                                                        Rectangle {
                                                            width: 16
                                                            height: 14
                                                            radius: 2
                                                            color: upMa.containsMouse ? (theme ? theme.accent : "#0078d4") : "transparent"
                                                            Text { anchors.centerIn: parent; text: "▲"; font.pixelSize: 8; color: "#cccccc" }
                                                            MouseArea {
                                                                id: upMa
                                                                anchors.fill: parent
                                                                hoverEnabled: true
                                                                cursorShape: Qt.PointingHandCursor
                                                                onClicked: {
                                                                    if (index > 0) {
                                                                        var arr = root.radialConfigItems.slice();
                                                                        var tmp = arr[index];
                                                                        arr[index] = arr[index - 1];
                                                                        arr[index - 1] = tmp;
                                                                        root.radialConfigItems = arr;
                                                                        root.saveRadialConfig();
                                                                    }
                                                                }
                                                            }
                                                        }
                                                        Rectangle {
                                                            width: 16
                                                            height: 14
                                                            radius: 2
                                                            color: downMa.containsMouse ? (theme ? theme.accent : "#0078d4") : "transparent"
                                                            Text { anchors.centerIn: parent; text: "▼"; font.pixelSize: 8; color: "#cccccc" }
                                                            MouseArea {
                                                                id: downMa
                                                                anchors.fill: parent
                                                                hoverEnabled: true
                                                                cursorShape: Qt.PointingHandCursor
                                                                onClicked: {
                                                                    if (index < root.radialConfigItems.length - 1) {
                                                                        var arr = root.radialConfigItems.slice();
                                                                        var tmp = arr[index];
                                                                        arr[index] = arr[index + 1];
                                                                        arr[index + 1] = tmp;
                                                                        root.radialConfigItems = arr;
                                                                        root.saveRadialConfig();
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }

                                                    // Enabled Checkbox
                                                    CheckBox {
                                                        checked: modelData.enabled !== false
                                                        onToggled: {
                                                            var arr = root.radialConfigItems.slice();
                                                            arr[index].enabled = checked;
                                                            root.radialConfigItems = arr;
                                                            root.saveRadialConfig();
                                                        }
                                                    }

                                                    // Icon
                                                    VectorIcon {
                                                        name: modelData.icon || "file"
                                                        size: 14
                                                        color: modelData.custom ? (theme ? theme.accent : "#38bdf8") : (theme ? theme.textPrimary : "#cccccc")
                                                    }

                                                    // Label and Badge
                                                    ColumnLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 2

                                                        RowLayout {
                                                            Layout.fillWidth: true
                                                            spacing: 6

                                                            TextInput {
                                                                Layout.fillWidth: true
                                                                text: modelData.label || ""
                                                                color: theme ? theme.textPrimary : "#ffffff"
                                                                font.pixelSize: 12
                                                                font.bold: true
                                                                onEditingFinished: {
                                                                    var arr = root.radialConfigItems.slice();
                                                                    arr[index].label = text;
                                                                    root.radialConfigItems = arr;
                                                                    root.saveRadialConfig();
                                                                }
                                                            }

                                                            // Distinguishing badge (Built-in vs Custom)
                                                            Rectangle {
                                                                height: 16
                                                                width: badgeText.implicitWidth + 8
                                                                radius: 3
                                                                color: modelData.custom ? "#0c4a6e" : "#1e293b"
                                                                border.color: modelData.custom ? "#38bdf8" : "#475569"
                                                                border.width: 1

                                                                Text {
                                                                    id: badgeText
                                                                    anchors.centerIn: parent
                                                                    text: modelData.custom ? ((modelData.action_type === "bash" ? "Bash" : (modelData.action_type === "cmd" ? "CMD" : "Custom"))) : "Built-in"
                                                                    color: modelData.custom ? "#7dd3fc" : "#94a3b8"
                                                                    font.pixelSize: 9
                                                                    font.bold: true
                                                                }
                                                            }
                                                        }
                                                    }

                                                    // Delete button (for custom buttons)
                                                    Rectangle {
                                                        width: 20
                                                        height: 20
                                                        radius: 3
                                                        visible: modelData.custom === true
                                                        color: delMa.containsMouse ? (theme ? theme.error : "#f14c4c") : "transparent"
                                                        VectorIcon { anchors.centerIn: parent; name: "close"; size: 9; color: delMa.containsMouse ? "#ffffff" : "#888888" }
                                                        MouseArea {
                                                            id: delMa
                                                            anchors.fill: parent
                                                            hoverEnabled: true
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: {
                                                                var arr = root.radialConfigItems.slice();
                                                                arr.splice(index, 1);
                                                                root.radialConfigItems = arr;
                                                                root.saveRadialConfig();
                                                            }
                                                        }
                                                    }
                                                }

                                                // Custom button action configuration row
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    visible: modelData.custom === true
                                                    spacing: 6

                                                    // Action type selector (Bash / CMD)
                                                    Rectangle {
                                                        width: 80
                                                        height: 20
                                                        radius: 3
                                                        color: theme ? theme.bgInput : "#181818"
                                                        border.color: theme ? theme.borderSubtle : "#333333"

                                                        Text {
                                                            anchors.centerIn: parent
                                                            text: (modelData.action_type || "bash").toUpperCase() + " ▼"
                                                            color: theme ? theme.textSecondary : "#aaaaaa"
                                                            font.pixelSize: 10
                                                        }

                                                        MouseArea {
                                                            anchors.fill: parent
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: {
                                                                var arr = root.radialConfigItems.slice();
                                                                arr[index].action_type = (arr[index].action_type === "bash") ? "cmd" : "bash";
                                                                root.radialConfigItems = arr;
                                                                root.saveRadialConfig();
                                                            }
                                                        }
                                                    }

                                                    TextInput {
                                                        Layout.fillWidth: true
                                                        text: modelData.action || ""
                                                        color: theme ? theme.textSecondary : "#cccccc"
                                                        font.pixelSize: 10
                                                        font.family: "Consolas, monospace"
                                                        onEditingFinished: {
                                                            var arr = root.radialConfigItems.slice();
                                                            arr[index].action = text;
                                                            root.radialConfigItems = arr;
                                                            root.saveRadialConfig();
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Right Column: LIVE VISUAL RADIAL PREVIEW
                            Rectangle {
                                Layout.fillHeight: true
                                Layout.fillWidth: true
                                radius: 8
                                color: theme ? theme.bgApp : "#141822"
                                border.color: theme ? theme.borderNormal : "#2a3145"
                                border.width: 1

                                Text {
                                    anchors.top: parent.top
                                    anchors.left: parent.left
                                    anchors.margins: 12
                                    text: "LIVE RADIAL MENU PREVIEW"
                                    color: theme ? theme.textMuted : "#64748b"
                                    font.pixelSize: 10
                                    font.bold: true
                                    font.letterSpacing: 1
                                }

                                Item {
                                    id: radialPreviewContainer
                                    anchors.centerIn: parent
                                    width: 240
                                    height: 240

                                    // Filter enabled items for preview
                                    readonly property var activeItems: {
                                        var list = [];
                                        if (root.radialConfigItems) {
                                            for (var i = 0; i < root.radialConfigItems.length; i++) {
                                                if (root.radialConfigItems[i].enabled !== false) {
                                                    list.push(root.radialConfigItems[i]);
                                                }
                                            }
                                        }
                                        return list;
                                    }
                                    readonly property real previewRadius: 75

                                    // Center Disc
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 64
                                        height: 64
                                        radius: 32
                                        color: theme ? theme.bgPopup : "#151824"
                                        border.color: theme ? theme.borderNormal : "#2a3145"
                                        border.width: 2

                                        Column {
                                            anchors.centerIn: parent
                                            spacing: 2
                                            VectorIcon {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                name: "zen"
                                                size: 14
                                                color: theme ? theme.accent : "#3b82f6"
                                            }
                                            Text {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                text: "DGX"
                                                color: theme ? theme.textPrimary : "#f1f5f9"
                                                font.pixelSize: 9
                                                font.bold: true
                                            }
                                        }
                                    }

                                    // Radial Bubbles
                                    Repeater {
                                        model: radialPreviewContainer.activeItems

                                        delegate: Item {
                                            readonly property real angle: (index / Math.max(1, radialPreviewContainer.activeItems.length)) * (2 * Math.PI) - (Math.PI / 2)
                                            readonly property real nodeX: (radialPreviewContainer.width / 2) + Math.cos(angle) * radialPreviewContainer.previewRadius - 20
                                            readonly property real nodeY: (radialPreviewContainer.height / 2) + Math.sin(angle) * radialPreviewContainer.previewRadius - 20

                                            x: nodeX
                                            y: nodeY
                                            width: 40
                                            height: 40

                                            Rectangle {
                                                anchors.fill: parent
                                                radius: 20
                                                color: prevMa.containsMouse ? (theme ? theme.accent : "#3b82f6") : (theme ? theme.bgSurface : "#181c28")
                                                border.color: modelData.custom ? "#38bdf8" : (prevMa.containsMouse ? "#ffffff" : (theme ? theme.borderNormal : "#2a3145"))
                                                border.width: 1

                                                scale: prevMa.containsMouse ? 1.15 : 1.0
                                                Behavior on scale { NumberAnimation { duration: 100 } }

                                                Column {
                                                    anchors.centerIn: parent
                                                    spacing: 1
                                                    VectorIcon {
                                                        anchors.horizontalCenter: parent.horizontalCenter
                                                        name: modelData.icon || "file"
                                                        size: 11
                                                        color: prevMa.containsMouse ? "#ffffff" : (theme ? theme.textPrimary : "#e2e8f0")
                                                    }
                                                    Text {
                                                        anchors.horizontalCenter: parent.horizontalCenter
                                                        text: modelData.label || ""
                                                        color: prevMa.containsMouse ? "#ffffff" : (theme ? theme.textSecondary : "#94a3b8")
                                                        font.pixelSize: 8
                                                        font.bold: prevMa.containsMouse
                                                    }
                                                }

                                                ToolTip.visible: prevMa.containsMouse
                                                ToolTip.text: (modelData.label || "") + (modelData.action ? " [" + modelData.action + "]" : "")

                                                MouseArea {
                                                    id: prevMa
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        if (typeof mainWindow !== "undefined" && mainWindow.showNotification) {
                                                            mainWindow.showNotification("Radial action: " + modelData.label, "info", "Radial Menu");
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // =========================================================
                    // 6. SEARCH RESULTS TAB
                    // =========================================================
                    ScrollView {
                        id: searchScroll
                        clip: true
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Column {
                            width: Math.max(380, searchScroll.availableWidth)
                            spacing: 12

                            RowLayout {
                                width: parent.width
                                spacing: 8

                                Text {
                                    text: "Search Results"
                                    color: theme ? theme.textBright : "#ffffff"
                                    font.pixelSize: 15
                                    font.bold: true
                                    font.family: theme ? theme.fontFamilyUi : "sans-serif"
                                }

                                Text {
                                    text: "for '" + root.searchQuery + "'"
                                    color: theme ? theme.accent : "#0078d4"
                                    font.pixelSize: 13
                                    font.italic: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }

                            Item { width: 1; height: 4 }

                            // 1. AI Assistant (Beta)
                            SettingToggleItem {
                                width: parent.width
                                visible: root.matchesSearch("AI Assistant (Beta)", "ChatGPT AI code assistant smart debugging inline chat workspace")
                                title: "AI Assistant (Beta)"
                                subtitle: "Enable ChatGPT AI code assistant, smart debugging, and workspace panel"
                                checked: theme ? theme.enableAI : true
                                onToggled: function(c) {
                                    if (theme) {
                                        theme.enableAI = c;
                                        theme.saveSettings();
                                    }
                                }
                            }

                            // 2. HTML File Run Target
                            Rectangle {
                                width: parent.width
                                height: 72
                                visible: root.matchesSearch("HTML File Run Target", "html htm run action radial menu f5 browser built-in live preview sandbox")
                                radius: theme ? theme.radiusSm : 4
                                color: theme ? theme.bgSurface : "#252526"
                                border.color: theme ? theme.borderSubtle : "#282828"
                                border.width: 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 6

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text {
                                            text: "HTML File Run Action (Radial Menu / F5)"
                                            color: theme ? theme.textPrimary : "#cccccc"
                                            font.pixelSize: 12
                                            font.bold: true
                                        }
                                        Item { Layout.fillWidth: true }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        Rectangle {
                                            Layout.fillWidth: true
                                            height: 28
                                            radius: 3
                                            color: (!theme || theme.htmlRunTarget === "built_in") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgInput : "#1e1e1e")
                                            border.color: (!theme || theme.htmlRunTarget === "built_in") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderNormal : "#333333")

                                            Row {
                                                anchors.centerIn: parent
                                                spacing: 6
                                                VectorIcon { anchors.verticalCenter: parent.verticalCenter; name: "sparkles"; size: 10; color: "#ffffff" }
                                                Text {
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text: "Built-in Live Preview Tab"
                                                    color: (!theme || theme.htmlRunTarget === "built_in") ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                                    font.pixelSize: 11
                                                    font.bold: (!theme || theme.htmlRunTarget === "built_in")
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    if (theme) {
                                                        theme.htmlRunTarget = "built_in";
                                                        theme.saveSettings();
                                                    }
                                                }
                                            }
                                        }

                                        Rectangle {
                                            Layout.fillWidth: true
                                            height: 28
                                            radius: 3
                                            color: (theme && theme.htmlRunTarget === "browser") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgInput : "#1e1e1e")
                                            border.color: (theme && theme.htmlRunTarget === "browser") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderNormal : "#333333")

                                            Row {
                                                anchors.centerIn: parent
                                                spacing: 6
                                                VectorIcon { anchors.verticalCenter: parent.verticalCenter; name: "code"; size: 10; color: "#ffffff" }
                                                Text {
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text: "Default Web Browser"
                                                    color: (theme && theme.htmlRunTarget === "browser") ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                                    font.pixelSize: 11
                                                    font.bold: (theme && theme.htmlRunTarget === "browser")
                                                }
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    if (theme) {
                                                        theme.htmlRunTarget = "browser";
                                                        theme.saveSettings();
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // 3. Right-Click Context Menu Style
                            Rectangle {
                                width: parent.width
                                height: 56
                                visible: root.matchesSearch("Right-Click Context Menu", "radial hold and drag gesture standard popup menu mouse")
                                radius: theme ? theme.radiusSm : 4
                                color: theme ? theme.bgSurface : "#252526"
                                border.color: theme ? theme.borderSubtle : "#282828"
                                border.width: 1

                                Column {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 3

                                    Text {
                                        text: "Right-Click Context Menu"
                                        color: theme ? theme.textPrimary : "#cccccc"
                                        font.pixelSize: 12
                                        font.bold: true
                                    }

                                    Text {
                                        text: "Choose radial gesture or classic popup menu"
                                        color: theme ? theme.textMuted : "#656565"
                                        font.pixelSize: 10
                                    }
                                }

                                Row {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 8

                                    Rectangle {
                                        width: 82
                                        height: 30
                                        radius: 3
                                        color: (theme && theme.contextMenuStyle === "radial") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgSurfaceHover : "#2a2d2e")

                                        Text {
                                            anchors.centerIn: parent
                                            text: "Radial"
                                            color: (theme && theme.contextMenuStyle === "radial") ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                            font.pixelSize: 11
                                            font.bold: (theme && theme.contextMenuStyle === "radial")
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: { if (theme) theme.contextMenuStyle = "radial"; }
                                        }
                                    }

                                    Rectangle {
                                        width: 82
                                        height: 30
                                        radius: 3
                                        color: (theme && theme.contextMenuStyle === "standard") ? (theme ? theme.accent : "#0078d4") : (theme ? theme.bgSurfaceHover : "#2a2d2e")

                                        Text {
                                            anchors.centerIn: parent
                                            text: "Standard"
                                            color: (theme && theme.contextMenuStyle === "standard") ? "#ffffff" : (theme ? theme.textSecondary : "#858585")
                                            font.pixelSize: 11
                                            font.bold: (theme && theme.contextMenuStyle === "standard")
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: { if (theme) theme.contextMenuStyle = "standard"; }
                                        }
                                    }
                                }
                            }

                            // 4. Smooth Animations
                            SettingToggleItem {
                                width: parent.width
                                visible: root.matchesSearch("Smooth UI Animations", "state transitions micro-interactions speed")
                                title: "Smooth UI Animations"
                                subtitle: "Enable smooth state transitions and micro-interactions"
                                checked: theme ? theme.enableAnimations : true
                                onToggled: function(c) { if (theme) theme.enableAnimations = c; }
                            }

                            // 5. Vinyl Spin Animation
                            SettingToggleItem {
                                width: parent.width
                                visible: root.matchesSearch("Vinyl Spin Animation", "rotate record cover music playback spinning")
                                title: "Vinyl Spin Animation"
                                subtitle: "Rotate vinyl record cover during music playback"
                                checked: theme ? theme.enableVinylAnimation : true
                                onToggled: function(c) { if (theme) theme.enableVinylAnimation = c; }
                            }

                            // 6. Code Minimap
                            SettingToggleItem {
                                width: parent.width
                                visible: root.matchesSearch("Code Minimap", "overview scroll minimap right edge code preview")
                                title: "Code Minimap"
                                subtitle: "Display live code overview scroll minimap on the right edge"
                                checked: theme ? theme.enableMinimap : true
                                onToggled: function(c) { if (theme) theme.enableMinimap = c; }
                            }

                            // 7. Line Numbers
                            SettingToggleItem {
                                width: parent.width
                                visible: root.matchesSearch("Line Numbers Gutter", "display line numbers in editor gutter margin")
                                title: "Line Numbers Gutter"
                                subtitle: "Display line numbers in editor gutter"
                                checked: theme ? theme.enableLineNumbers : true
                                onToggled: function(c) { if (theme) theme.enableLineNumbers = c; }
                            }

                            // 8. Bracket Matching
                            SettingToggleItem {
                                width: parent.width
                                visible: root.matchesSearch("Bracket Matching", "auto-closing quotes parenthesis curly brackets tags")
                                title: "Bracket Matching & Auto-Closing"
                                subtitle: "Automatically insert closing brackets and quotes"
                                checked: theme ? theme.enableBracketMatching : true
                                onToggled: function(c) { if (theme) theme.enableBracketMatching = c; }
                            }

                            // 9. Word Wrap
                            SettingToggleItem {
                                width: parent.width
                                visible: root.matchesSearch("Word Wrap", "wrap long lines fit editor width")
                                title: "Word Wrap"
                                subtitle: "Wrap long lines to fit within editor width"
                                checked: theme ? theme.enableWordWrap : false
                                onToggled: function(c) { if (theme) theme.enableWordWrap = c; }
                            }

                            // 10. Searchable Keyboard Shortcuts
                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Run Active File", "execute compile terminal runner f5")
                                title: "Run Active File"
                                subtitle: "Compile / execute active file in integrated terminal"
                                currentShortcut: theme ? theme.shortcutRun : "F5"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutRun = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Format Document", "prettify beautify indent language code formatting")
                                title: "Format Document"
                                subtitle: "Auto-format active code buffer according to language standard"
                                currentShortcut: theme ? theme.shortcutFormat : "Shift+Alt+F"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutFormat = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Save File", "save buffer to disk write")
                                title: "Save File"
                                subtitle: "Save modifications in active buffer to disk"
                                currentShortcut: theme ? theme.shortcutSave : "Ctrl+S"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutSave = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Save As", "save active buffer new filename")
                                title: "Save As"
                                subtitle: "Save active buffer with a new filename"
                                currentShortcut: theme ? theme.shortcutSaveAs : "Ctrl+Shift+S"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutSaveAs = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Toggle Integrated Terminal", "terminal powershell bash prompt")
                                title: "Toggle Integrated Terminal"
                                subtitle: "Show or hide bottom PowerShell / CMD terminal"
                                currentShortcut: theme ? theme.shortcutToggleTerminal : "Ctrl+`"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutToggleTerminal = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Toggle Explorer Panel", "file tree project sidebar")
                                title: "Toggle Explorer Panel"
                                subtitle: "Show or hide left project file tree"
                                currentShortcut: theme ? theme.shortcutToggleExplorer : "Ctrl+B"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutToggleExplorer = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Find in Buffer", "search find text occurrences")
                                title: "Find in Buffer"
                                subtitle: "Search for text matching query in active editor"
                                currentShortcut: theme ? theme.shortcutFind : "Ctrl+F"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutFind = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Find & Replace", "replace text occurrences buffer")
                                title: "Find & Replace"
                                subtitle: "Search and replace occurrences in active editor"
                                currentShortcut: theme ? theme.shortcutReplace : "Ctrl+H"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutReplace = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("New File", "create unsaved empty document")
                                title: "New File"
                                subtitle: "Create an empty unsaved document tab"
                                currentShortcut: theme ? theme.shortcutNewFile : "Ctrl+N"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutNewFile = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Open File", "open existing source code document")
                                title: "Open File"
                                subtitle: "Open an existing source code file"
                                currentShortcut: theme ? theme.shortcutOpenFile : "Ctrl+O"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutOpenFile = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Toggle AI Assistant", "chatgpt ai coding assistant smart chat")
                                title: "Toggle AI Assistant"
                                subtitle: "Open or close AI coding assistant panel"
                                currentShortcut: theme ? theme.shortcutToggleAI : "Ctrl+Shift+A"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutToggleAI = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Toggle Music Player", "music audio stream lo-fi synthwave")
                                title: "Toggle Music Player"
                                subtitle: "Open or close music player streaming panel"
                                currentShortcut: theme ? theme.shortcutToggleMusic : "Ctrl+Shift+M"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutToggleMusic = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Toggle Line Comment", "comment uncomment code lines")
                                title: "Toggle Line Comment"
                                subtitle: "Comment or uncomment current line / selection"
                                currentShortcut: theme ? theme.shortcutComment : "Ctrl+/"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutComment = val; }
                            }

                            ShortcutSettingRow {
                                width: parent.width
                                visible: root.matchesSearch("Whiteboard Architecture Canvas", "visual diagram architecture canvas plan drawings")
                                title: "Whiteboard Architecture Canvas"
                                subtitle: "Open or close visual architecture design & plan canvas"
                                currentShortcut: theme ? theme.shortcutWhiteboard : "Ctrl+Alt+W"
                                onShortcutChanged: function(val) { if (theme) theme.shortcutWhiteboard = val; }
                            }

                            Item { width: 1; height: 16 }
                        }
                    }
                }
            }
        }
    }

    // Component: SettingToggleItem with Clean Spacing & Anchors
    component SettingToggleItem: Rectangle {
        property string title: ""
        property string subtitle: ""
        property bool checked: false
        signal toggled(bool c)

        height: subtitle ? 54 : 44
        radius: theme ? theme.radiusSm : 4
        color: theme ? theme.bgSurface : "#252526"
        border.color: theme ? theme.borderSubtle : "#282828"
        border.width: 1

        Column {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.right: pillSwitch.left
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 3

            Text {
                text: title
                color: theme ? theme.textPrimary : "#cccccc"
                font.pixelSize: 12
                font.bold: true
                elide: Text.ElideRight
                width: parent.width
            }

            Text {
                text: subtitle
                color: theme ? theme.textMuted : "#656565"
                font.pixelSize: 10
                visible: subtitle.length > 0
                elide: Text.ElideRight
                width: parent.width
            }
        }

        // Animated Pill Switch
        Rectangle {
            id: pillSwitch
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            width: 40
            height: 22
            radius: 11
            color: checked ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderNormal : "#333333")

            Behavior on color {
                ColorAnimation { duration: 120 }
            }

            Rectangle {
                width: 18
                height: 18
                radius: 9
                color: "#ffffff"
                x: checked ? 20 : 2
                anchors.verticalCenter: parent.verticalCenter

                Behavior on x {
                    NumberAnimation { duration: 120 }
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: toggled(!checked)
            }
        }
    }

    // Component: ShortcutSettingRow with Interactive Keybinding Recorder & Manual Input
    component ShortcutSettingRow: Rectangle {
        id: scRow
        property string title: ""
        property string subtitle: ""
        property string currentShortcut: ""
        property bool isRecording: false
        signal shortcutChanged(string val)

        height: 52
        radius: theme ? theme.radiusSm : 4
        color: scRow.isRecording ? (theme ? theme.bgSurfaceActive : "#2a2d3e") : (theme ? theme.bgSurface : "#252526")
        border.color: scRow.isRecording ? (theme ? theme.accent : "#0078d4") : (theme ? theme.borderSubtle : "#282828")
        border.width: scRow.isRecording ? 1.5 : 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            spacing: 12

            Column {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: scRow.title
                    color: theme ? theme.textPrimary : "#cccccc"
                    font.pixelSize: 12
                    font.bold: true
                    elide: Text.ElideRight
                }

                Text {
                    text: scRow.subtitle
                    color: theme ? theme.textMuted : "#656565"
                    font.pixelSize: 10
                    elide: Text.ElideRight
                }
            }

            // Key Recording Badge / Button
            Rectangle {
                id: recorderBadge
                width: Math.max(120, scBadgeText.contentWidth + 20)
                height: 28
                radius: 4
                color: scRow.isRecording ? (theme ? theme.accent : "#0078d4") : (badgeMa.containsMouse ? (theme ? theme.bgSurfaceHover : "#2a2d2e") : (theme ? theme.bgInput : "#181818"))
                border.color: scRow.isRecording ? "#ffffff" : (theme ? theme.borderNormal : "#333333")
                border.width: 1
                focus: scRow.isRecording

                Row {
                    anchors.centerIn: parent
                    spacing: 6

                    VectorIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: scRow.isRecording ? "sparkles" : "keyboard"
                        size: 11
                        color: scRow.isRecording ? "#ffffff" : (theme ? theme.accent : "#0078d4")
                    }

                    Text {
                        id: scBadgeText
                        anchors.verticalCenter: parent.verticalCenter
                        text: scRow.isRecording ? "Press Keys..." : (scRow.currentShortcut || "Not Set")
                        color: scRow.isRecording ? "#ffffff" : (theme ? theme.textBright : "#ffffff")
                        font.pixelSize: 11
                        font.bold: true
                        font.family: theme ? theme.fontFamilyMono : "monospace"
                    }
                }

                MouseArea {
                    id: badgeMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        scRow.isRecording = !scRow.isRecording;
                        if (scRow.isRecording) {
                            recorderBadge.forceActiveFocus();
                        }
                    }
                }

                Keys.onPressed: function(event) {
                    if (!scRow.isRecording) return;

                    // Allow Escape to cancel recording without modifying shortcut
                    if (event.key === Qt.Key_Escape && !event.modifiers) {
                        scRow.isRecording = false;
                        event.accepted = true;
                        return;
                    }

                    // Ignore standalone modifier presses (wait for key combo)
                    if (event.key === Qt.Key_Control || event.key === Qt.Key_Shift ||
                        event.key === Qt.Key_Alt || event.key === Qt.Key_Meta) {
                        event.accepted = true;
                        return;
                    }

                    var keyStr = "";
                    if (event.key >= Qt.Key_F1 && event.key <= Qt.Key_F12) {
                        keyStr = "F" + (event.key - Qt.Key_F1 + 1);
                    } else if (event.key >= Qt.Key_A && event.key <= Qt.Key_Z) {
                        keyStr = String.fromCharCode(event.key);
                    } else if (event.key >= Qt.Key_0 && event.key <= Qt.Key_9) {
                        keyStr = String.fromCharCode(event.key);
                    } else if (event.key === Qt.Key_QuoteLeft || event.key === Qt.Key_AsciiTilde) {
                        keyStr = "`";
                    } else if (event.key === Qt.Key_Slash) {
                        keyStr = "/";
                    } else if (event.key === Qt.Key_Backslash) {
                        keyStr = "\\";
                    } else if (event.key === Qt.Key_Minus) {
                        keyStr = "-";
                    } else if (event.key === Qt.Key_Equal || event.key === Qt.Key_Plus) {
                        keyStr = "=";
                    } else if (event.key === Qt.Key_Comma) {
                        keyStr = ",";
                    } else if (event.key === Qt.Key_Period) {
                        keyStr = ".";
                    } else if (event.key === Qt.Key_Semicolon) {
                        keyStr = ";";
                    } else if (event.key === Qt.Key_Apostrophe) {
                        keyStr = "'";
                    } else if (event.key === Qt.Key_BracketLeft) {
                        keyStr = "[";
                    } else if (event.key === Qt.Key_BracketRight) {
                        keyStr = "]";
                    } else if (event.key === Qt.Key_Tab) {
                        keyStr = "Tab";
                    } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                        keyStr = "Return";
                    } else if (event.key === Qt.Key_Space) {
                        keyStr = "Space";
                    } else if (event.key === Qt.Key_Delete) {
                        keyStr = "Del";
                    } else if (event.key === Qt.Key_Backspace) {
                        keyStr = "Backspace";
                    } else if (event.text && event.text.length > 0) {
                        keyStr = event.text.toUpperCase();
                    }

                    if (keyStr.length > 0) {
                        var parts = [];
                        if (event.modifiers & Qt.ControlModifier) parts.push("Ctrl");
                        if (event.modifiers & Qt.AltModifier) parts.push("Alt");
                        if (event.modifiers & Qt.ShiftModifier) parts.push("Shift");
                        if (event.modifiers & Qt.MetaModifier) parts.push("Meta");
                        parts.push(keyStr);

                        var fullCombo = parts.join("+");
                        scRow.currentShortcut = fullCombo;
                        scRow.shortcutChanged(fullCombo);
                        if (theme && theme.saveSettings) {
                            theme.saveSettings();
                        }
                        scRow.isRecording = false;
                        event.accepted = true;
                    }
                }
            }
        }
    }
}
