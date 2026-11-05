import QtQuick 2.15

QtObject {
    id: root

    // Available themes dynamically loaded from themes/*.json
    property string currentTheme: "obsidian"
    property var availableThemes: []

    function refreshAvailableThemes() {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_available_themes) {
            var list = settingsBackend.get_available_themes();
            if (list && list.length > 0) {
                root.availableThemes = list;
            }
        }
    }

    // IDE Settings & Preferences
    property bool enableAnimations: true
    property bool enableTransparency: true
    property bool enableVinylAnimation: true
    property bool enableMinimap: true
    property bool enableLineNumbers: true
    property bool enableBreadcrumbs: true
    property bool enableAutocomplete: true
    property bool enableWordWrap: false
    property bool enableMouseWheelZoom: true
    property int editorFontSize: 13
    property string editorFontFamily: "Consolas, 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace"
    property int tabSize: 4
    property string uiDensity: "compact" // "compact", "normal", "relaxed"
    property string contextMenuStyle: "radial" // "radial", "standard"
    property bool enableAI: true
    property bool autoCloseBracketsQuotes: true
    property alias enableBracketMatching: root.autoCloseBracketsQuotes
    property string htmlRunTarget: "built_in" // "built_in", "browser"

    // Keyboard Shortcuts Configuration (Customizable)
    property string shortcutNewFile: "Ctrl+N"
    property string shortcutOpenFile: "Ctrl+O"
    property string shortcutOpenFolder: "Ctrl+Shift+O"
    property string shortcutSave: "Ctrl+S"
    property string shortcutSaveAs: "Ctrl+Shift+S"
    property string shortcutCloseTab: "Ctrl+W"
    property string shortcutFind: "Ctrl+F"
    property string shortcutReplace: "Ctrl+H"
    property string shortcutRun: "F5"
    property string shortcutToggleExplorer: "Ctrl+B"
    property string shortcutToggleTerminal: "Ctrl+`"
    property string shortcutFormat: "Shift+Alt+F"
    property string shortcutZenMode: "Ctrl+Shift+Z"
    property string shortcutSettings: "Ctrl+,"
    property string shortcutToggleAI: "Ctrl+Shift+A"
    property string shortcutToggleMusic: "Ctrl+Shift+M"
    property string shortcutComment: "Ctrl+/"
    property string shortcutWhiteboard: "Ctrl+Alt+W"
    property string shortcutQuickOpen: "Ctrl+P"
    property string shortcutGoToLine: "Ctrl+G"
    property string shortcutRenameSymbol: "F2"
    property string shortcutUndo: "Ctrl+Z"
    property string shortcutRedo: "Ctrl+Y"
    property string shortcutCopy: "Ctrl+C"
    property string shortcutPaste: "Ctrl+V"
    property string shortcutMultiCursor: "Ctrl+D"
    property string shortcutAddCursor: "Alt+Click"

    Component.onCompleted: {
        root.refreshAvailableThemes();
        if (typeof settingsBackend !== "undefined" && settingsBackend) {
            var rawJson = settingsBackend.get_all_settings_json();
            if (rawJson) {
                try {
                    var s = JSON.parse(rawJson);
                    if (s.theme) root.setTheme(s.theme);
                    if (s.editor_font_size) root.editorFontSize = parseInt(s.editor_font_size);
                    if (s.enable_mouse_wheel_zoom !== undefined) root.enableMouseWheelZoom = (s.enable_mouse_wheel_zoom === true || s.enable_mouse_wheel_zoom === "true");
                    if (s.enable_word_wrap !== undefined) root.enableWordWrap = (s.enable_word_wrap === true || s.enable_word_wrap === "true");
                    if (s.enable_minimap !== undefined) root.enableMinimap = (s.enable_minimap === true || s.enable_minimap === "true");
                    if (s.enable_line_numbers !== undefined) root.enableLineNumbers = (s.enable_line_numbers === true || s.enable_line_numbers === "true");
                    if (s.enable_breadcrumbs !== undefined) root.enableBreadcrumbs = (s.enable_breadcrumbs === true || s.enable_breadcrumbs === "true");
                    if (s.auto_close_brackets_quotes !== undefined) root.autoCloseBracketsQuotes = (s.auto_close_brackets_quotes === true || s.auto_close_brackets_quotes === "true");
                    if (s.enable_ai !== undefined) root.enableAI = (s.enable_ai === true || s.enable_ai === "true");
                    if (s.html_run_target) root.htmlRunTarget = s.html_run_target;
                    if (s.tab_size) root.tabSize = parseInt(s.tab_size);
                    if (s.ui_density) root.uiDensity = s.ui_density;
                    if (s.context_menu_style) root.contextMenuStyle = s.context_menu_style;
                    if (s.shortcuts && typeof s.shortcuts === "object") {
                        for (var k in s.shortcuts) {
                            if (root.hasOwnProperty(k)) {
                                root[k] = s.shortcuts[k];
                            }
                        }
                    }
                } catch(e) {
                    console.log("[Theme] Settings load notice:", e);
                }
            }
        }
    }

    function saveSettings() {
        if (typeof settingsBackend !== "undefined" && settingsBackend) {
            settingsBackend.set_value("theme", root.currentTheme);
            settingsBackend.set_value("editor_font_size", "" + root.editorFontSize);
            settingsBackend.set_value("enable_mouse_wheel_zoom", "" + root.enableMouseWheelZoom);
            settingsBackend.set_value("enable_word_wrap", "" + root.enableWordWrap);
            settingsBackend.set_value("enable_minimap", "" + root.enableMinimap);
            settingsBackend.set_value("enable_line_numbers", "" + root.enableLineNumbers);
            settingsBackend.set_value("enable_breadcrumbs", "" + root.enableBreadcrumbs);
            settingsBackend.set_value("auto_close_brackets_quotes", "" + root.autoCloseBracketsQuotes);
            settingsBackend.set_value("enable_ai", "" + root.enableAI);
            settingsBackend.set_value("html_run_target", root.htmlRunTarget);
            settingsBackend.set_value("tab_size", "" + root.tabSize);
            settingsBackend.set_value("ui_density", root.uiDensity);
            settingsBackend.set_value("context_menu_style", root.contextMenuStyle);
            var sc = {
                shortcutNewFile: root.shortcutNewFile,
                shortcutOpenFile: root.shortcutOpenFile,
                shortcutOpenFolder: root.shortcutOpenFolder,
                shortcutSave: root.shortcutSave,
                shortcutSaveAs: root.shortcutSaveAs,
                shortcutCloseTab: root.shortcutCloseTab,
                shortcutFind: root.shortcutFind,
                shortcutReplace: root.shortcutReplace,
                shortcutRun: root.shortcutRun,
                shortcutToggleExplorer: root.shortcutToggleExplorer,
                shortcutToggleTerminal: root.shortcutToggleTerminal,
                shortcutFormat: root.shortcutFormat,
                shortcutZenMode: root.shortcutZenMode,
                shortcutSettings: root.shortcutSettings,
                shortcutToggleAI: root.shortcutToggleAI,
                shortcutToggleMusic: root.shortcutToggleMusic,
                shortcutComment: root.shortcutComment,
                shortcutWhiteboard: root.shortcutWhiteboard,
                shortcutQuickOpen: root.shortcutQuickOpen,
                shortcutGoToLine: root.shortcutGoToLine,
                shortcutRenameSymbol: root.shortcutRenameSymbol,
                shortcutUndo: root.shortcutUndo,
                shortcutRedo: root.shortcutRedo,
                shortcutCopy: root.shortcutCopy,
                shortcutPaste: root.shortcutPaste,
                shortcutMultiCursor: root.shortcutMultiCursor,
                shortcutAddCursor: root.shortcutAddCursor
            };
            settingsBackend.set_value("shortcuts", JSON.stringify(sc));
        }
    }

    function resetShortcuts() {
        shortcutNewFile = "Ctrl+N";
        shortcutOpenFile = "Ctrl+O";
        shortcutOpenFolder = "Ctrl+Shift+O";
        shortcutSave = "Ctrl+S";
        shortcutSaveAs = "Ctrl+Shift+S";
        shortcutCloseTab = "Ctrl+W";
        shortcutFind = "Ctrl+F";
        shortcutReplace = "Ctrl+H";
        shortcutRun = "F5";
        shortcutToggleExplorer = "Ctrl+B";
        shortcutToggleTerminal = "Ctrl+`";
        shortcutFormat = "Shift+Alt+F";
        shortcutZenMode = "Ctrl+Shift+Z";
        shortcutSettings = "Ctrl+,";
        shortcutToggleAI = "Ctrl+Shift+A";
        shortcutToggleMusic = "Ctrl+Shift+M";
        shortcutComment = "Ctrl+/";
        shortcutWhiteboard = "Ctrl+Alt+W";
        shortcutQuickOpen = "Ctrl+P";
        shortcutGoToLine = "Ctrl+G";
        shortcutRenameSymbol = "F2";
        shortcutUndo = "Ctrl+Z";
        shortcutRedo = "Ctrl+Y";
        shortcutCopy = "Ctrl+C";
        shortcutPaste = "Ctrl+V";
        shortcutMultiCursor = "Ctrl+D";
        shortcutAddCursor = "Alt+Click";
        saveSettings();
    }

    readonly property int animationDurationFast: enableAnimations ? 80 : 0
    readonly property int animationDurationNormal: enableAnimations ? 150 : 0

    // Design Tokens & Colors - Default Obsidian (Clean Dark IDE)
    property color bgRoot: "#181818"
    property color bgHeader: "#181818"
    property color bgPanel: "#181818"
    property color bgEditor: "#1e1e1e"
    property color bgSidebar: "#181818"
    property color bgTerminal: "#181818"
    property color bgSurface: "#252526"
    property color bgSurfaceHover: "#2a2d2e"
    property color bgSurfaceActive: "#37373d"
    property color bgSelected: "#04395e"
    property color bgInput: "#252526"
    property color bgPopup: "#252526"

    property color borderSubtle: "#282828"
    property color borderNormal: "#333333"
    property color borderFocus: "#0078d4"

    property color textPrimary: "#cccccc"
    property color textSecondary: "#858585"
    property color textMuted: "#656565"
    property color textDisabled: "#4d4d4d"
    property color textBright: "#ffffff"

    property color accent: "#0078d4"
    property color accentHover: "#1f8ad2"
    property color accentActive: "#0062a3"
    property color accentMuted: "#200078d4"
    property color terminalPrompt: "#a855f7"

    property color success: "#4ec9b0"
    property color warning: "#cca700"
    property color error: "#f14c4c"
    property color info: "#3794ff"

    // Syntax Highlighting Tokens
    property color synKeyword: "#569cd6"
    property color synFunction: "#dcdcaa"
    property color synString: "#ce9178"
    property color synNumber: "#b5cea8"
    property color synComment: "#6a9955"
    property color synType: "#4ec9b0"
    property color synCurrentLine: "#282828"
    property color synSelection: "#264f78"

    // Spacing & Sizing Tokens (Minimal & Dense IDE spacing)
    readonly property int radiusXs: 2
    readonly property int radiusSm: 3
    readonly property int radiusMd: 4
    readonly property int radiusLg: 6

    readonly property int spaceXs: 4
    readonly property int spaceSm: 8
    readonly property int spaceMd: 12
    readonly property int spaceLg: 16

    readonly property int fontSizeXs: 11
    readonly property int fontSizeSm: 12
    readonly property int fontSizeMd: 13
    readonly property int fontSizeBase: 13
    readonly property int fontSizeLg: 14

    readonly property string fontFamilyUi: "Segoe UI"
    readonly property string fontFamilyMono: "Consolas"

    function setTheme(name) {
        var themeName = (name || "obsidian").toLowerCase().trim();
        currentTheme = themeName;

        var themeData = null;
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_theme_data) {
            var raw = settingsBackend.get_theme_data(themeName);
            if (raw && raw !== "{}") {
                try {
                    themeData = JSON.parse(raw);
                } catch(e) {
                    console.log("[Theme] Failed to parse theme JSON:", e);
                }
            }
        }

        if (themeData) {
            applyThemeData(themeData);
        }

        if (typeof backend !== "undefined" && backend && backend.set_theme) {
            backend.set_theme(themeName);
        }
        root.saveSettings();
    }

    function applyThemeData(data) {
        if (!data || typeof data !== "object") return;
        var skipKeys = { "id": true, "name": true, "type": true, "color": true, "currentTheme": true };
        for (var key in data) {
            if (skipKeys[key]) continue;
            if (root.hasOwnProperty(key)) {
                root[key] = data[key];
            }
        }
    }
}
