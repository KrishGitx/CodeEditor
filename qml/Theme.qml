import QtQuick 2.15

QtObject {
    id: themeRoot

    // ─── Theme Selector ───
    property string currentTheme: "Obsidian"

    // ─── Accent Palette ───
    property string accentColor: "#8b7cff"
    property string accentSecondary: "#5eead4"
    property string accentSuccess: "#10b981"
    property string accentWarning: "#f59e0b"
    property string accentError: "#ef4444"

    // ─── Feature Flags ───
    property bool animationsEnabled: true
    property bool musicVisualizationsEnabled: true
    property bool blurEnabled: false
    property bool transparencyEnabled: false
    property bool compactMode: false
    property bool focusMode: false
    property bool lineNumbersVisible: true
    property bool minimapVisible: false
    property bool wordWrap: false
    property bool bracketMatching: true

    // ─── Typography ───
    property string monoFont: "Consolas"
    property string uiFont: "Segoe UI"
    property int editorFontSize: 14
    property real editorLineHeight: 1.5
    property int editorTabSize: 4
    property bool editorUseTabs: false

    // ─── Font Size Scale ───
    readonly property int fontSizeXs: compactMode ? 8 : 9
    readonly property int fontSizeSm: compactMode ? 9 : 10
    readonly property int fontSizeMd: compactMode ? 10 : 11
    readonly property int fontSizeLg: compactMode ? 11 : 12
    readonly property int fontSizeXl: compactMode ? 12 : 13

    // ─── Spacing Scale ───
    readonly property int spacingXs: compactMode ? 1 : 2
    readonly property int spacingSm: compactMode ? 2 : 4
    readonly property int spacingMd: compactMode ? 4 : 8
    readonly property int spacingLg: compactMode ? 8 : 12
    readonly property int spacingXl: compactMode ? 12 : 16

    // ─── Border Radius Scale ───
    readonly property int radiusSm: 2
    readonly property int radiusMd: 4
    readonly property int radiusLg: 6

    // ─── Animation Durations ───
    readonly property int animFast: animationsEnabled ? 120 : 0
    readonly property int animNormal: animationsEnabled ? 200 : 0
    readonly property int animSlow: animationsEnabled ? 350 : 0

    // Backward compatibility aliases
    readonly property int animDurationFast: animFast
    readonly property int animDurationNormal: animNormal
    readonly property int animDurationSlow: animSlow

    // ═══════════════════════════════════════════════════════════════════
    //  THEME DEFINITIONS
    //  To add a new theme: add one object to _themes, done.
    // ═══════════════════════════════════════════════════════════════════
    readonly property var _themes: ({

        "Obsidian": {
            bgRoot:         "#0a0d12",
            bgHeader:       "#0d1118",
            bgSidebar:      "#10151e",
            bgEditor:       "#0b0f15",
            bgPanelRight:   "#10151e",
            bgBottomPanel:  "#0c1017",
            bgCard:         "#151b26",
            bgInput:        "#0c1119",
            bgHover:        "#1a2130",
            bgActive:       "#232c3d",
            bgSurface:      "#131924",
            borderSubtle:   "#242c3a",
            borderFocus:    "#8b7cff",
            textPrimary:    "#e7eaf0",
            textSecondary:  "#a4adbc",
            textMuted:      "#647085",
            gutterBg:       "#0a0e14",
            gutterText:     "#465166",
            gutterActiveTx: "#a4adbc",
            tabActiveBg:    "#0b0f15",
            tabInactiveBg:  "#10151e",
            tabHoverBg:     "#161d29",
            scrollThumb:    "#303a4c",
            scrollTrack:    "#10151e",
            splitterLine:   "#202837",
            splitterHover:  "#8b7cff",
            currentLineBg:  "#111824",
            selectionBg:    "#3c4275",
            matchBracketBg: "#303754",
            findMatchBg:    "#60431c",
            menuBg:         "#151b26",
            menuHover:      "#222b3b",
            menuSeparator:  "#252e3e",
            tooltipBg:      "#171e2a",
            tooltipText:    "#e7eaf0",
            dialogOverlay:  "#00000099",
            badgeBg:        "#252e3e",
            isDark:         true
        },

        "Midnight": {
            bgRoot:         "#080b14",
            bgHeader:       "#0c1020",
            bgSidebar:      "#0a0e1a",
            bgEditor:       "#090d18",
            bgPanelRight:   "#0b0f1c",
            bgBottomPanel:  "#080b14",
            bgCard:         "#111830",
            bgInput:        "#0d1224",
            bgHover:        "#162040",
            bgActive:       "#1d2b52",
            bgSurface:      "#101628",
            borderSubtle:   "#182040",
            borderFocus:    "#7aa2f7",
            textPrimary:    "#c8d3f5",
            textSecondary:  "#7982a9",
            textMuted:      "#4e567a",
            gutterBg:       "#070a12",
            gutterText:     "#3b4368",
            gutterActiveTx: "#7982a9",
            tabActiveBg:    "#090d18",
            tabInactiveBg:  "#0c1020",
            tabHoverBg:     "#101829",
            scrollThumb:    "#1d2848",
            scrollTrack:    "#0a0e1a",
            splitterLine:   "#182040",
            splitterHover:  "#7aa2f7",
            currentLineBg:  "#0d1222",
            selectionBg:    "#28366a",
            matchBracketBg: "#2c3760",
            findMatchBg:    "#5a3818",
            menuBg:         "#111830",
            menuHover:      "#182040",
            menuSeparator:  "#182040",
            tooltipBg:      "#101628",
            tooltipText:    "#b8c3e8",
            dialogOverlay:  "#000000aa",
            badgeBg:        "#182040",
            isDark:         true
        },

        "Dracula": {
            bgRoot:         "#1e1f29",
            bgHeader:       "#252636",
            bgSidebar:      "#21222e",
            bgEditor:       "#1e1f29",
            bgPanelRight:   "#232433",
            bgBottomPanel:  "#1e1f29",
            bgCard:         "#2a2b3d",
            bgInput:        "#252636",
            bgHover:        "#303147",
            bgActive:       "#383a54",
            bgSurface:      "#272838",
            borderSubtle:   "#343650",
            borderFocus:    "#bd93f9",
            textPrimary:    "#f8f8f2",
            textSecondary:  "#b0b4c8",
            textMuted:      "#6272a4",
            gutterBg:       "#1b1c26",
            gutterText:     "#4d5080",
            gutterActiveTx: "#b0b4c8",
            tabActiveBg:    "#1e1f29",
            tabInactiveBg:  "#252636",
            tabHoverBg:     "#2a2b3d",
            scrollThumb:    "#3e4068",
            scrollTrack:    "#21222e",
            splitterLine:   "#343650",
            splitterHover:  "#bd93f9",
            currentLineBg:  "#24253a",
            selectionBg:    "#44475a",
            matchBracketBg: "#504e78",
            findMatchBg:    "#614a18",
            menuBg:         "#2a2b3d",
            menuHover:      "#343650",
            menuSeparator:  "#343650",
            tooltipBg:      "#272838",
            tooltipText:    "#e8e8e0",
            dialogOverlay:  "#11111888",
            badgeBg:        "#343650",
            isDark:         true
        },

        "Nord": {
            bgRoot:         "#242933",
            bgHeader:       "#2a303c",
            bgSidebar:      "#272c36",
            bgEditor:       "#242933",
            bgPanelRight:   "#282e39",
            bgBottomPanel:  "#242933",
            bgCard:         "#2e3440",
            bgInput:        "#2a303c",
            bgHover:        "#353c4a",
            bgActive:       "#3e4656",
            bgSurface:      "#2c3240",
            borderSubtle:   "#3b4252",
            borderFocus:    "#88c0d0",
            textPrimary:    "#eceff4",
            textSecondary:  "#a3b1c8",
            textMuted:      "#6b7c96",
            gutterBg:       "#22272f",
            gutterText:     "#4c566a",
            gutterActiveTx: "#a3b1c8",
            tabActiveBg:    "#242933",
            tabInactiveBg:  "#2a303c",
            tabHoverBg:     "#303845",
            scrollThumb:    "#434c5e",
            scrollTrack:    "#272c36",
            splitterLine:   "#3b4252",
            splitterHover:  "#88c0d0",
            currentLineBg:  "#2a3040",
            selectionBg:    "#3b4b68",
            matchBracketBg: "#4c566a",
            findMatchBg:    "#5a4020",
            menuBg:         "#2e3440",
            menuHover:      "#3b4252",
            menuSeparator:  "#3b4252",
            tooltipBg:      "#2c3240",
            tooltipText:    "#d8dee9",
            dialogOverlay:  "#15191e88",
            badgeBg:        "#3b4252",
            isDark:         true
        },

        "Monokai": {
            bgRoot:         "#1e1f1c",
            bgHeader:       "#262720",
            bgSidebar:      "#222320",
            bgEditor:       "#272822",
            bgPanelRight:   "#242520",
            bgBottomPanel:  "#1e1f1c",
            bgCard:         "#2d2e28",
            bgInput:        "#262720",
            bgHover:        "#3e3f38",
            bgActive:       "#484940",
            bgSurface:      "#2a2b26",
            borderSubtle:   "#3a3b34",
            borderFocus:    "#a6e22e",
            textPrimary:    "#f8f8f2",
            textSecondary:  "#b8b8a8",
            textMuted:      "#75715e",
            gutterBg:       "#1c1d1a",
            gutterText:     "#585850",
            gutterActiveTx: "#b8b8a8",
            tabActiveBg:    "#272822",
            tabInactiveBg:  "#262720",
            tabHoverBg:     "#2d2e28",
            scrollThumb:    "#484940",
            scrollTrack:    "#222320",
            splitterLine:   "#3a3b34",
            splitterHover:  "#a6e22e",
            currentLineBg:  "#2e2f28",
            selectionBg:    "#494a3e",
            matchBracketBg: "#504e40",
            findMatchBg:    "#614a18",
            menuBg:         "#2d2e28",
            menuHover:      "#3a3b34",
            menuSeparator:  "#3a3b34",
            tooltipBg:      "#2a2b26",
            tooltipText:    "#e8e8da",
            dialogOverlay:  "#10100e88",
            badgeBg:        "#3a3b34",
            isDark:         true
        },

        "Light": {
            bgRoot:         "#f5f6f8",
            bgHeader:       "#e8eaef",
            bgSidebar:      "#eef0f4",
            bgEditor:       "#ffffff",
            bgPanelRight:   "#f0f2f6",
            bgBottomPanel:  "#f0f2f5",
            bgCard:         "#ffffff",
            bgInput:        "#ffffff",
            bgHover:        "#e3e6ed",
            bgActive:       "#d5dae4",
            bgSurface:      "#f8f9fb",
            borderSubtle:   "#d8dce6",
            borderFocus:    "#2563eb",
            textPrimary:    "#1a1d2b",
            textSecondary:  "#546080",
            textMuted:      "#8895ad",
            gutterBg:       "#f0f2f6",
            gutterText:     "#a0a8b8",
            gutterActiveTx: "#546080",
            tabActiveBg:    "#ffffff",
            tabInactiveBg:  "#e8eaef",
            tabHoverBg:     "#eceef3",
            scrollThumb:    "#c5cad5",
            scrollTrack:    "#eef0f4",
            splitterLine:   "#d8dce6",
            splitterHover:  "#2563eb",
            currentLineBg:  "#f5f7fb",
            selectionBg:    "#add6ff",
            matchBracketBg: "#c8e0f8",
            findMatchBg:    "#e8d090",
            menuBg:         "#ffffff",
            menuHover:      "#e3e6ed",
            menuSeparator:  "#e0e4eb",
            tooltipBg:      "#1a1d2b",
            tooltipText:    "#e8ecf4",
            dialogOverlay:  "#00000044",
            badgeBg:        "#e3e6ed",
            isDark:         false
        },

        "Paper": {
            bgRoot:         "#f4f1eb",
            bgHeader:       "#e8e4dc",
            bgSidebar:      "#ece8e0",
            bgEditor:       "#faf8f4",
            bgPanelRight:   "#eeeae2",
            bgBottomPanel:  "#eeebe4",
            bgCard:         "#faf8f4",
            bgInput:        "#faf8f4",
            bgHover:        "#e2ddd4",
            bgActive:       "#d5d0c5",
            bgSurface:      "#f5f2ec",
            borderSubtle:   "#d5d0c5",
            borderFocus:    "#8b6834",
            textPrimary:    "#2c2820",
            textSecondary:  "#6b6358",
            textMuted:      "#9a9288",
            gutterBg:       "#eeeae2",
            gutterText:     "#b0a898",
            gutterActiveTx: "#6b6358",
            tabActiveBg:    "#faf8f4",
            tabInactiveBg:  "#e8e4dc",
            tabHoverBg:     "#edeae3",
            scrollThumb:    "#c8c0b4",
            scrollTrack:    "#ece8e0",
            splitterLine:   "#d5d0c5",
            splitterHover:  "#8b6834",
            currentLineBg:  "#f2efe8",
            selectionBg:    "#d5c8a8",
            matchBracketBg: "#d0c4a8",
            findMatchBg:    "#e0c870",
            menuBg:         "#faf8f4",
            menuHover:      "#e2ddd4",
            menuSeparator:  "#d8d2c8",
            tooltipBg:      "#2c2820",
            tooltipText:    "#e8e4d8",
            dialogOverlay:  "#2c282044",
            badgeBg:        "#e2ddd4",
            isDark:         false
        },

        "Glass": {
            // Transparent charcoal/graphite glass — no blue cast.
            bgRoot:         "#101010cc",
            bgHeader:       "#181818b8",
            bgSidebar:      "#141414b8",
            bgEditor:       "#0e0e0eb0",
            bgPanelRight:   "#151515b8",
            bgBottomPanel:  "#101010c4",
            bgCard:         "#1d1d1dcc",
            bgInput:        "#171717cc",
            bgHover:        "#292929cc",
            bgActive:       "#353535d9",
            bgSurface:      "#1a1a1acc",
            borderSubtle:   "#ffffff10",
            borderFocus:    "#ffffff22",
            textPrimary:    "#f2f2f2",
            textSecondary:  "#a6a6a6",
            textMuted:      "#6f6f6f",
            gutterBg:       "#0c0c0ca8",
            gutterText:     "#505050",
            gutterActiveTx: "#a0a0a0",
            tabActiveBg:    "#0e0e0eb0",
            tabInactiveBg:  "#181818b8",
            tabHoverBg:     "#222222c4",
            scrollThumb:    "#4a4a4a70",
            scrollTrack:    "#14141430",
            splitterLine:   "#ffffff0b",
            splitterHover:  "#ffffff2a",
            currentLineBg:  "#20202070",
            selectionBg:    "#45454599",
            matchBracketBg: "#50505088",
            findMatchBg:    "#55503c88",
            menuBg:         "#1b1b1bd9",
            menuHover:      "#292929e0",
            menuSeparator:  "#ffffff10",
            tooltipBg:      "#1b1b1be8",
            tooltipText:    "#e8e8e8",
            dialogOverlay:  "#000000aa",
            badgeBg:        "#292929cc",
            isDark:         true
        }
    })

    // ═══════════════════════════════════════════════════════════════════
    //  RESOLVED COLOR TOKENS (read from current theme)
    // ═══════════════════════════════════════════════════════════════════
    readonly property var _t: _themes[currentTheme] || _themes["Obsidian"]

    readonly property color bgRoot:         _t.bgRoot
    readonly property color bgHeader:       _t.bgHeader
    readonly property color bgSidebar:      _t.bgSidebar
    readonly property color bgEditor:       _t.bgEditor
    readonly property color bgPanelRight:   _t.bgPanelRight
    readonly property color bgBottomPanel:  _t.bgBottomPanel
    readonly property color bgCard:         _t.bgCard
    readonly property color bgInput:        _t.bgInput
    readonly property color bgHover:        _t.bgHover
    readonly property color bgActive:       _t.bgActive
    readonly property color bgSurface:      _t.bgSurface

    readonly property color borderSubtle:   _t.borderSubtle
    readonly property color borderFocus:    borderSubtle
    readonly property color borderHairline: Qt.rgba(borderSubtle.r, borderSubtle.g, borderSubtle.b, Math.min(borderSubtle.a, 0.35))
    readonly property color divider:        splitterLine
    readonly property color focusRing:      accentColor
    readonly property int borderWidth:      1
    readonly property int dividerWidth:     1

    readonly property color textPrimary:    _t.textPrimary
    readonly property color textSecondary:  _t.textSecondary
    readonly property color textMuted:      _t.textMuted

    readonly property color gutterBg:       _t.gutterBg
    readonly property color gutterText:     _t.gutterText
    readonly property color gutterActiveTx: _t.gutterActiveTx

    readonly property color tabActiveBg:    _t.tabActiveBg
    readonly property color tabInactiveBg:  _t.tabInactiveBg
    readonly property color tabHoverBg:     _t.tabHoverBg

    readonly property color scrollThumb:    _t.scrollThumb
    readonly property color scrollTrack:    _t.scrollTrack

    readonly property color splitterLine:   _t.splitterLine
    readonly property color splitterHover:  _t.splitterHover

    readonly property color currentLineBg:  _t.currentLineBg
    readonly property color selectionBg:    _t.selectionBg
    readonly property color matchBracketBg: _t.matchBracketBg
    readonly property color findMatchBg:    _t.findMatchBg

    readonly property color menuBg:         _t.menuBg
    readonly property color menuHover:      _t.menuHover
    readonly property color menuSeparator:  _t.menuSeparator

    readonly property color tooltipBg:      _t.tooltipBg
    readonly property color tooltipText:    _t.tooltipText

    readonly property color dialogOverlay:  _t.dialogOverlay
    readonly property color badgeBg:        _t.badgeBg

    readonly property bool isDark:          _t.isDark !== undefined ? _t.isDark : true

    // ─── Available theme names (for settings UI) ───
    readonly property var themeNames: Object.keys(_themes)

    // ─── Highlighter theme name mapping ───
    function highlighterThemeName() {
        var map = {
            "Obsidian": "obsidian",
            "Midnight": "midnight",
            "Dracula": "dracula",
            "Nord": "nord",
            "Monokai": "monokai",
            "Light": "light",
            "Paper": "paper",
            "Glass": "glass"
        }
        return map[currentTheme] || "obsidian"
    }
}
