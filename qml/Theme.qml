import QtQuick 2.15

QtObject {
    id: root

    // Available themes dynamically loaded from themes/*.json
    readonly property var initialThemeObj: {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_saved_theme_data) {
            try {
                var jsonStr = settingsBackend.get_saved_theme_data();
                if (jsonStr) return JSON.parse(jsonStr);
            } catch (e) {
                console.log("[Theme] Error parsing initial theme data:", e);
            }
        }
        return null;
    }

    property string currentTheme: (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_saved_theme_name) ? settingsBackend.get_saved_theme_name() : "nord"
    property var availableThemes: []

    function refreshAvailableThemes() {
        if (typeof settingsBackend !== "undefined" && settingsBackend && settingsBackend.get_available_themes) {
            var list = settingsBackend.get_available_themes();
            if (list && list.length > 0) {
                root.availableThemes = list;
            }
        }
    }

    property var _themeConnections: Connections {
        target: (typeof settingsBackend !== "undefined" && settingsBackend) ? settingsBackend : null
        function onAvailableThemesChanged(newList) {
            if (newList && newList.length > 0) {
                root.availableThemes = newList;
            } else {
                root.refreshAvailableThemes();
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
    property int editorFontSize: 14
    property string editorFontFamily: "Consolas"
    property int tabSize: 4
    property real editorWordSpacing: 3.5
    property real editorLetterSpacing: 0.5
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

    // Design Tokens & Colors - Preloaded from initialThemeObj on Frame 0
    property color bgRoot: (initialThemeObj && initialThemeObj.bgRoot) ? initialThemeObj.bgRoot : "#242933"
    property color bgHeader: (initialThemeObj && initialThemeObj.bgHeader) ? initialThemeObj.bgHeader : "#242933"
    property color bgPanel: (initialThemeObj && initialThemeObj.bgPanel) ? initialThemeObj.bgPanel : "#242933"
    property color bgEditor: (initialThemeObj && initialThemeObj.bgEditor) ? initialThemeObj.bgEditor : "#2e3440"
    property color bgSidebar: (initialThemeObj && initialThemeObj.bgSidebar) ? initialThemeObj.bgSidebar : "#242933"
    property color bgTerminal: (initialThemeObj && initialThemeObj.bgTerminal) ? initialThemeObj.bgTerminal : "#242933"
    property color bgSurface: (initialThemeObj && initialThemeObj.bgSurface) ? initialThemeObj.bgSurface : "#2e3440"
    property color bgSurfaceHover: (initialThemeObj && initialThemeObj.bgSurfaceHover) ? initialThemeObj.bgSurfaceHover : "#3b4252"
    property color bgSurfaceActive: (initialThemeObj && initialThemeObj.bgSurfaceActive) ? initialThemeObj.bgSurfaceActive : "#434c5e"
    property color bgSelected: (initialThemeObj && initialThemeObj.bgSelected) ? initialThemeObj.bgSelected : "#434c5e"
    property color bgInput: (initialThemeObj && initialThemeObj.bgInput) ? initialThemeObj.bgInput : "#2e3440"
    property color bgPopup: (initialThemeObj && initialThemeObj.bgPopup) ? initialThemeObj.bgPopup : "#2e3440"

    property color borderSubtle: (initialThemeObj && initialThemeObj.borderSubtle) ? initialThemeObj.borderSubtle : "#3b4252"
    property color borderNormal: (initialThemeObj && initialThemeObj.borderNormal) ? initialThemeObj.borderNormal : "#434c5e"
    property color borderFocus: (initialThemeObj && initialThemeObj.borderFocus) ? initialThemeObj.borderFocus : "#88c0d0"

    property color textPrimary: (initialThemeObj && initialThemeObj.textPrimary) ? initialThemeObj.textPrimary : "#d8dee9"
    property color textSecondary: (initialThemeObj && initialThemeObj.textSecondary) ? initialThemeObj.textSecondary : "#98a2b3"
    property color textMuted: (initialThemeObj && initialThemeObj.textMuted) ? initialThemeObj.textMuted : "#717d91"
    property color textDisabled: (initialThemeObj && initialThemeObj.textDisabled) ? initialThemeObj.textDisabled : "#4c566a"
    property color textBright: (initialThemeObj && initialThemeObj.textBright) ? initialThemeObj.textBright : "#eceff4"

    property color accent: (initialThemeObj && initialThemeObj.accent) ? initialThemeObj.accent : "#88c0d0"
    property color accentHover: (initialThemeObj && initialThemeObj.accentHover) ? initialThemeObj.accentHover : "#81a1c1"
    property color accentActive: (initialThemeObj && initialThemeObj.accentActive) ? initialThemeObj.accentActive : "#5e81ac"
    property color accentMuted: (initialThemeObj && initialThemeObj.accentMuted) ? initialThemeObj.accentMuted : "#2588c0d0"
    property color terminalPrompt: (initialThemeObj && initialThemeObj.terminalPrompt) ? initialThemeObj.terminalPrompt : "#b48ead"

    property color success: (initialThemeObj && initialThemeObj.success) ? initialThemeObj.success : "#a3be8c"
    property color warning: (initialThemeObj && initialThemeObj.warning) ? initialThemeObj.warning : "#ebcb8b"
    property color error: (initialThemeObj && initialThemeObj.error) ? initialThemeObj.error : "#bf616a"
    property color info: (initialThemeObj && initialThemeObj.info) ? initialThemeObj.info : "#81a1c1"

    // Syntax Highlighting Tokens
    property color synKeyword: (initialThemeObj && initialThemeObj.synKeyword) ? initialThemeObj.synKeyword : "#81a1c1"
    property color synFunction: (initialThemeObj && initialThemeObj.synFunction) ? initialThemeObj.synFunction : "#88c0d0"
    property color synString: (initialThemeObj && initialThemeObj.synString) ? initialThemeObj.synString : "#a3be8c"
    property color synNumber: (initialThemeObj && initialThemeObj.synNumber) ? initialThemeObj.synNumber : "#b48ead"
    property color synComment: (initialThemeObj && initialThemeObj.synComment) ? initialThemeObj.synComment : "#616e88"
    property color synType: (initialThemeObj && initialThemeObj.synType) ? initialThemeObj.synType : "#8fbcbb"
    property color synCurrentLine: (initialThemeObj && initialThemeObj.synCurrentLine) ? initialThemeObj.synCurrentLine : "#383f4d"
    property color borderCurrentLine: (initialThemeObj && initialThemeObj.borderCurrentLine) ? initialThemeObj.borderCurrentLine : "#282828"
    property color editorLineNumberForeground: (initialThemeObj && initialThemeObj.editorLineNumberForeground) ? initialThemeObj.editorLineNumberForeground : "#656565"
    property color editorLineNumberActiveForeground: (initialThemeObj && initialThemeObj.editorLineNumberActiveForeground) ? initialThemeObj.editorLineNumberActiveForeground : "#ffffff"
    property color editorIndentGuideBackground: (initialThemeObj && initialThemeObj.editorIndentGuideBackground) ? initialThemeObj.editorIndentGuideBackground : "#404040"
    property color editorIndentGuideActiveBackground: (initialThemeObj && initialThemeObj.editorIndentGuideActiveBackground) ? initialThemeObj.editorIndentGuideActiveBackground : "#707070"
    property color synSelection: (initialThemeObj && initialThemeObj.synSelection) ? initialThemeObj.synSelection : "#434c5e"

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
    readonly property alias fontFamily: root.fontFamilyUi

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
