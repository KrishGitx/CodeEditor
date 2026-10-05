import QtQuick 2.15

QtObject {
    id: root

    // Available themes: obsidian, midnight, dracula, nord, monokai, light, paper, glass
    property string currentTheme: "obsidian"

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
    property color accentMuted: "#0078d420"

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
        var themeName = name.toLowerCase().trim();
        currentTheme = themeName;

        if (themeName === "midnight") {
            bgRoot = "#0f131a";
            bgHeader = "#0f131a";
            bgPanel = "#0f131a";
            bgEditor = "#141824";
            bgSidebar = "#0f131a";
            bgTerminal = "#0d1117";
            bgSurface = "#1c2333";
            bgSurfaceHover = "#242d42";
            bgSurfaceActive = "#2e3a54";
            bgSelected = "#1d3557";
            bgInput = "#141824";
            bgPopup = "#1a2130";
            borderSubtle = "#1f2636";
            borderNormal = "#28334a";
            borderFocus = "#38bdf8";
            textPrimary = "#cbd5e1";
            textSecondary = "#7e92ad";
            textMuted = "#50627e";
            accent = "#38bdf8";
            accentHover = "#60a5fa";
            accentActive = "#0284c7";
            accentMuted = "#38bdf820";
            synKeyword = "#9d7cd8";
            synFunction = "#7aa2f7";
            synString = "#73daca";
            synNumber = "#ff9e64";
            synComment = "#4e567a";
            synType = "#2ac3de";
            synCurrentLine = "#1c2233";
            synSelection = "#263e68";
        }
        else if (themeName === "dracula") {
            bgRoot = "#21222c";
            bgHeader = "#21222c";
            bgPanel = "#21222c";
            bgEditor = "#282a36";
            bgSidebar = "#21222c";
            bgTerminal = "#1d1e26";
            bgSurface = "#343746";
            bgSurfaceHover = "#3e4254";
            bgSurfaceActive = "#44475a";
            bgSelected = "#44475a";
            bgInput = "#282a36";
            bgPopup = "#282a36";
            borderSubtle = "#2d303e";
            borderNormal = "#3d4052";
            borderFocus = "#bd93f9";
            textPrimary = "#f8f8f2";
            textSecondary = "#a0a4b8";
            textMuted = "#6272a4";
            accent = "#bd93f9";
            accentHover = "#ff79c6";
            accentActive = "#956bd6";
            accentMuted = "#bd93f920";
            synKeyword = "#ff79c6";
            synFunction = "#50fa7b";
            synString = "#f1fa8c";
            synNumber = "#bd93f9";
            synComment = "#6272a4";
            synType = "#8be9fd";
            synCurrentLine = "#303242";
            synSelection = "#44475a";
        }
        else if (themeName === "nord") {
            bgRoot = "#242933";
            bgHeader = "#242933";
            bgPanel = "#242933";
            bgEditor = "#2e3440";
            bgSidebar = "#242933";
            bgTerminal = "#1e222a";
            bgSurface = "#3b4252";
            bgSurfaceHover = "#434c5e";
            bgSurfaceActive = "#4c566a";
            bgSelected = "#3b4252";
            bgInput = "#2e3440";
            bgPopup = "#2e3440";
            borderSubtle = "#2e3542";
            borderNormal = "#3b4354";
            borderFocus = "#88c0d0";
            textPrimary = "#d8dee9";
            textSecondary = "#9aa5b8";
            textMuted = "#616e85";
            accent = "#88c0d0";
            accentHover = "#81a1c1";
            accentActive = "#5e81ac";
            accentMuted = "#88c0d020";
            synKeyword = "#81a1c1";
            synFunction = "#88c0d0";
            synString = "#a3be8c";
            synNumber = "#b48ead";
            synComment = "#616e85";
            synType = "#8fbcbb";
            synCurrentLine = "#353c4a";
            synSelection = "#434c5e";
        }
        else if (themeName === "monokai") {
            bgRoot = "#1e1f1c";
            bgHeader = "#1e1f1c";
            bgPanel = "#1e1f1c";
            bgEditor = "#272822";
            bgSidebar = "#1e1f1c";
            bgTerminal = "#171815";
            bgSurface = "#383830";
            bgSurfaceHover = "#44443a";
            bgSurfaceActive = "#49483e";
            bgSelected = "#49483e";
            bgInput = "#272822";
            bgPopup = "#272822";
            borderSubtle = "#2a2b27";
            borderNormal = "#3c3d36";
            borderFocus = "#a6e22e";
            textPrimary = "#f8f8f2";
            textSecondary = "#a6a69d";
            textMuted = "#75715e";
            accent = "#a6e22e";
            accentHover = "#fd971f";
            accentActive = "#8cc220";
            accentMuted = "#a6e22e20";
            synKeyword = "#f92672";
            synFunction = "#a6e22e";
            synString = "#e6db74";
            synNumber = "#ae81ff";
            synComment = "#75715e";
            synType = "#66d9ef";
            synCurrentLine = "#30312a";
            synSelection = "#49483e";
        }
        else if (themeName === "light") {
            bgRoot = "#f3f3f3";
            bgHeader = "#f3f3f3";
            bgPanel = "#f3f3f3";
            bgEditor = "#ffffff";
            bgSidebar = "#f3f3f3";
            bgTerminal = "#f8f8f8";
            bgSurface = "#e5e5e5";
            bgSurfaceHover = "#d8d8d8";
            bgSurfaceActive = "#c8c8c8";
            bgSelected = "#cce8ff";
            bgInput = "#ffffff";
            bgPopup = "#f0f0f0";
            borderSubtle = "#e5e5e5";
            borderNormal = "#cccccc";
            borderFocus = "#0078d4";
            textPrimary = "#1e1e1e";
            textSecondary = "#5a5a5a";
            textMuted = "#8a8a8a";
            accent = "#0078d4";
            accentHover = "#1f8ad2";
            accentActive = "#0062a3";
            accentMuted = "#0078d415";
            synKeyword = "#0000ff";
            synFunction = "#795e26";
            synString = "#a31515";
            synNumber = "#098658";
            synComment = "#008000";
            synType = "#267f99";
            synCurrentLine = "#f0f0f0";
            synSelection = "#add6ff";
        }
        else if (themeName === "paper") {
            bgRoot = "#f5f2eb";
            bgHeader = "#f5f2eb";
            bgPanel = "#f5f2eb";
            bgEditor = "#faf8f4";
            bgSidebar = "#f5f2eb";
            bgTerminal = "#ede8df";
            bgSurface = "#e8e2d5";
            bgSurfaceHover = "#ded6c5";
            bgSurfaceActive = "#d0c6b0";
            bgSelected = "#dfd3bc";
            bgInput = "#faf8f4";
            bgPopup = "#f2ede3";
            borderSubtle = "#e2d9c8";
            borderNormal = "#cfc3ad";
            borderFocus = "#8c5e3c";
            textPrimary = "#2c2820";
            textSecondary = "#62594a";
            textMuted = "#8c8270";
            accent = "#8c5e3c";
            accentHover = "#a6734c";
            accentActive = "#6f482d";
            accentMuted = "#8c5e3c15";
            synKeyword = "#8b5a2b";
            synFunction = "#2e6b4f";
            synString = "#6b5b3a";
            synNumber = "#8b4513";
            synComment = "#9a9288";
            synType = "#2f6b6b";
            synCurrentLine = "#f0eae0";
            synSelection = "#d8cbaf";
        }
        else if (themeName === "glass") {
            // Dark translucent graphite glassmorphism with high contrast and low-opacity borders
            bgRoot = "#12141a";
            bgHeader = "#161922ee";
            bgPanel = "#141720ee";
            bgEditor = "#101218f2";
            bgSidebar = "#141720ee";
            bgTerminal = "#0e1015f2";
            bgSurface = "#1e2230";
            bgSurfaceHover = "#262c3e";
            bgSurfaceActive = "#30374e";
            bgSelected = "#1b3052";
            bgInput = "#12141cf5";
            bgPopup = "#181b26fa";
            borderSubtle = "#ffffff0d";
            borderNormal = "#ffffff1a";
            borderFocus = "#0078d4";
            textPrimary = "#f1f5f9";
            textSecondary = "#94a3b8";
            textMuted = "#64748b";
            accent = "#0078d4";
            accentHover = "#38bdf8";
            accentActive = "#0284c7";
            accentMuted = "#0078d425";
            synKeyword = "#569cd6";
            synFunction = "#dcdcaa";
            synString = "#ce9178";
            synNumber = "#b5cea8";
            synComment = "#6a9955";
            synType = "#4ec9b0";
            synCurrentLine = "#1a1f2c";
            synSelection = "#1e3a68";
        }
        else {
            // Default Obsidian (Clean Dark IDE)
            bgRoot = "#181818";
            bgHeader = "#181818";
            bgPanel = "#181818";
            bgEditor = "#1e1e1e";
            bgSidebar = "#181818";
            bgTerminal = "#181818";
            bgSurface = "#252526";
            bgSurfaceHover = "#2a2d2e";
            bgSurfaceActive = "#37373d";
            bgSelected = "#04395e";
            bgInput = "#252526";
            bgPopup = "#252526";
            borderSubtle = "#282828";
            borderNormal = "#333333";
            borderFocus = "#0078d4";
            textPrimary = "#cccccc";
            textSecondary = "#858585";
            textMuted = "#656565";
            textDisabled = "#4d4d4d";
            textBright = "#ffffff";
            accent = "#0078d4";
            accentHover = "#1f8ad2";
            accentActive = "#0062a3";
            accentMuted = "#0078d420";
            synKeyword = "#569cd6";
            synFunction = "#dcdcaa";
            synString = "#ce9178";
            synNumber = "#b5cea8";
            synComment = "#6a9955";
            synType = "#4ec9b0";
            synCurrentLine = "#282828";
            synSelection = "#264f78";
        }

        if (typeof backend !== "undefined" && backend && backend.set_theme) {
            backend.set_theme(themeName);
        }
        root.saveSettings();
    }
}
