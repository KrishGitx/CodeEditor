import json
import os
import re
from pathlib import Path

def convert_vscode_theme(src_json_path, label="Orange Ocean", ui_theme="vs-dark"):
    with open(src_json_path, "r", encoding="utf-8") as f:
        text = f.read()
    # Strip comments and trailing commas
    text = re.sub(r'//.*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    data = json.loads(text)

    theme_name = label or data.get("name", "Custom Theme")
    theme_id = re.sub(r'[^a-z0-9_-]', '_', theme_name.lower().strip())
    
    is_light = "light" in ui_theme.lower() or "light" in data.get("type", "").lower()
    theme_type = "light" if is_light else "dark"
    
    colors = data.get("colors", {})
    base_vars = data.get("colorVars", {}).get("base", {})
    
    bg_root = colors.get("editor.background") or base_vars.get("bg") or ("#ffffff" if is_light else "#1e1e1e")
    bg_editor = colors.get("editor.background") or bg_root
    bg_header = colors.get("titleBar.activeBackground") or colors.get("activityBar.background") or bg_root
    bg_sidebar = colors.get("sideBar.background") or bg_root
    bg_terminal = colors.get("terminal.background") or bg_editor
    bg_surface = colors.get("editorWidget.background") or colors.get("input.background") or ("#f0f0f0" if is_light else "#2a2d2e")
    bg_selected = colors.get("list.activeSelectionBackground") or colors.get("selection.background") or "#04395e"
    
    text_primary = colors.get("editor.foreground") or colors.get("foreground") or base_vars.get("fg") or ("#000000" if is_light else "#d4d4d4")
    accent = colors.get("activityBarBadge.background") or colors.get("focusBorder") or colors.get("button.background") or "#0078d4"
    border_subtle = colors.get("sideBar.border") or colors.get("editorGroup.border") or ("#e0e0e0" if is_light else "#282828")
    
    # Syntax tokens
    syn_kw = "#0000ff" if is_light else "#569cd6"
    syn_fn = "#795e26" if is_light else "#dcdcaa"
    syn_str = "#a31515" if is_light else "#ce9178"
    syn_num = "#098658" if is_light else "#b5cea8"
    syn_comment = "#008000" if is_light else "#6a9955"
    syn_type = "#267f99" if is_light else "#4ec9b0"
    
    for tc in data.get("tokenColors", []):
        scope = tc.get("scope", "")
        if isinstance(scope, list):
            scope = " ".join(scope)
        scope = scope.lower()
        fg = tc.get("settings", {}).get("foreground")
        if fg and fg != "None":
            if "keyword" in scope and "syn_kw" not in locals():
                syn_kw = fg
            elif ("entity.name.function" in scope or "support.function" in scope) and syn_fn == ("#795e26" if is_light else "#dcdcaa"):
                syn_fn = fg
            elif "string" in scope and syn_str == ("#a31515" if is_light else "#ce9178"):
                syn_str = fg
            elif ("constant.numeric" in scope or "number" in scope) and syn_num == ("#098658" if is_light else "#b5cea8"):
                syn_num = fg
            elif "comment" in scope and syn_comment == ("#008000" if is_light else "#6a9955"):
                syn_comment = fg
            elif ("entity.name.type" in scope or "storage.type" in scope) and syn_type == ("#267f99" if is_light else "#4ec9b0"):
                syn_type = fg

    dgx_theme = {
        "id": theme_id,
        "name": theme_name,
        "type": theme_type,
        "color": bg_editor,
        "bgRoot": bg_root,
        "bgHeader": bg_header,
        "bgPanel": bg_sidebar,
        "bgEditor": bg_editor,
        "bgSidebar": bg_sidebar,
        "bgTerminal": bg_terminal,
        "bgSurface": bg_surface,
        "bgSurfaceHover": colors.get("list.hoverBackground", "#333333"),
        "bgSurfaceActive": bg_selected,
        "bgSelected": bg_selected,
        "bgInput": colors.get("input.background", bg_surface),
        "bgPopup": colors.get("menu.background", bg_surface),
        "borderSubtle": border_subtle,
        "borderNormal": colors.get("focusBorder", border_subtle),
        "borderFocus": colors.get("focusBorder", accent),
        "textPrimary": text_primary,
        "textSecondary": colors.get("descriptionForeground", "#858585"),
        "textMuted": "#656565",
        "textDisabled": colors.get("disabledForeground", "#555555"),
        "textBright": "#ffffff",
        "accent": accent,
        "accentHover": colors.get("button.hoverBackground", accent),
        "accentActive": accent,
        "accentMuted": accent + "40" if len(accent) == 7 else accent,
        "terminalPrompt": syn_kw,
        "success": "#4ade80",
        "warning": "#facc15",
        "error": "#ef4444",
        "info": accent,
        "synKeyword": syn_kw,
        "synFunction": syn_fn,
        "synString": syn_str,
        "synNumber": syn_num,
        "synComment": syn_comment,
        "synType": syn_type,
        "synCurrentLine": colors.get("editor.lineHighlightBackground", "#2a2d2e"),
        "synSelection": colors.get("editor.selectionBackground", "#264f78"),
        "background": bg_editor,
        "foreground": text_primary,
        "keywords": syn_kw,
        "functions": syn_fn,
        "strings": syn_str,
        "numbers": syn_num,
        "comments": syn_comment,
        "types": syn_type,
        "operators": syn_kw,
        "preprocessor": accent,
        "current_line": colors.get("editor.lineHighlightBackground", "#2a2d2e"),
        "selection": colors.get("editor.selectionBackground", "#264f78")
    }
    return dgx_theme

src = r"C:\Users\amazi\.dgx\extensions\enbonnet_orange-ocean\theme\orange-ocean-theme.json"
out = convert_vscode_theme(src, "Orange Ocean", "vs-dark")
print(json.dumps(out, indent=2)[:600])

dest = Path.home() / ".pod_studio" / "themes" / f"{out['id']}.json"
with open(dest, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("Saved converted theme to:", dest)

