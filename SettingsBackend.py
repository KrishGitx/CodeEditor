"""
SettingsBackend.py - Persistent User Preferences Manager for Pod Studio
Automatically saves and restores settings (theme, volume, editor config, shortcuts, layout) to JSON.
"""

import os
import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot


class SettingsBackend(QObject):
    settingsLoaded = Signal(str)
    settingChanged = Signal(str, str)
    recentProjectsChanged = Signal(list)
    iconThemeChanged = Signal()
    availableThemesChanged = Signal(list)

    def __init__(self):
        super().__init__()
        # Store settings in user home directory under .pod_studio/settings.json (with migration from legacy .dgx_studio)
        legacy_dir = Path.home() / ".dgx_studio"
        self.config_dir = Path.home() / ".pod_studio"
        self.config_file = self.config_dir / "settings.json"
        self.icon_theme_file = self.config_dir / "icon_theme.json"

        if not self.config_file.exists() and (legacy_dir / "settings.json").exists():
            try:
                self.config_dir.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(legacy_dir / "settings.json", self.config_file)
            except Exception as e:
                print(f"[SettingsBackend] Migration notice: {e}")
        elif not self.config_file.exists() and legacy_dir.exists():
            self.config_dir = legacy_dir
            self.config_file = legacy_dir / "settings.json"
            self.icon_theme_file = legacy_dir / "icon_theme.json"

        self.settings = self._load_default_settings()
        self._load_from_disk()
        self._ensure_default_icon_theme()

    def _load_default_settings(self):
        return {
            "theme": "obsidian",
            "music_volume": 75,
            "music_loop": False,
            "music_shuffle": False,
            "editor_font_size": 13,
            "enable_word_wrap": False,
            "enable_minimap": True,
            "enable_line_numbers": True,
            "enable_ai": True,
            "html_run_target": "built_in",
            "tab_size": 4,
            "ui_density": "compact",
            "context_menu_style": "radial",
            "explorer_width": 260,
            "right_panel_width": 340,
            "explorer_visible": True,
            "terminal_visible": False,
            "ai_visible": False,
            "music_visible": True,
            "shortcuts": {
                "shortcutNewFile": "Ctrl+N",
                "shortcutOpenFile": "Ctrl+O",
                "shortcutOpenFolder": "Ctrl+Shift+O",
                "shortcutSave": "Ctrl+S",
                "shortcutSaveAs": "Ctrl+Shift+S",
                "shortcutCloseTab": "Ctrl+W",
                "shortcutFind": "Ctrl+F",
                "shortcutReplace": "Ctrl+H",
                "shortcutRun": "F5",
                "shortcutToggleExplorer": "Ctrl+B",
                "shortcutToggleTerminal": "Ctrl+`",
                "shortcutFormat": "Shift+Alt+F",
                "shortcutZenMode": "Ctrl+Shift+Z",
                "shortcutSettings": "Ctrl+,",
                "shortcutToggleAI": "Ctrl+Shift+A",
                "shortcutToggleMusic": "Ctrl+Shift+M",
                "shortcutComment": "Ctrl+/",
                "shortcutWhiteboard": "Ctrl+Alt+W"
            }
        }

    def _load_from_disk(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.settings.update(data)
            except Exception as e:
                print(f"[SettingsBackend] Error reading {self.config_file}: {e}")

    def _save_to_disk(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"[SettingsBackend] Error writing {self.config_file}: {e}")

    @Slot(str, str, result=str)
    def get_value(self, key, default=""):
        val = self.settings.get(key, default)
        if isinstance(val, (dict, list)):
            return json.dumps(val)
        return str(val)

    @Slot(str, str)
    def set_value(self, key, value):
        # Parse value if it is JSON structure or primitive
        try:
            parsed = json.loads(value)
            self.settings[key] = parsed
        except Exception:
            # Handle boolean strings and ints
            if value.lower() == "true":
                self.settings[key] = True
            elif value.lower() == "false":
                self.settings[key] = False
            else:
                try:
                    self.settings[key] = int(value)
                except ValueError:
                    try:
                        self.settings[key] = float(value)
                    except ValueError:
                        self.settings[key] = value

        self._save_to_disk()
        self.settingChanged.emit(key, str(self.settings[key]))

    @Slot(result=str)
    def get_all_settings_json(self):
        return json.dumps(self.settings)

    @Slot(str)
    def save_all_settings_json(self, json_str):
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                self.settings.update(data)
                self._save_to_disk()
        except Exception as e:
            print(f"[SettingsBackend] Failed to update settings from JSON: {e}")

    @Slot(str)
    def add_recent_project(self, folder_path):
        if not folder_path or not folder_path.strip():
            return
        clean_path = folder_path.replace("file:///", "").strip()
        if not os.path.exists(clean_path):
            return

        name = os.path.basename(os.path.normpath(clean_path)) or clean_path
        recent = self.settings.get("recent_projects", [])
        if not isinstance(recent, list):
            recent = []

        # Remove existing instance of same path
        recent = [p for p in recent if isinstance(p, dict) and os.path.normpath(p.get("path", "")) != os.path.normpath(clean_path)]
        recent.insert(0, {
            "name": name,
            "path": clean_path
        })
        recent = recent[:12]  # Keep up to 12 recent projects
        self.settings["recent_projects"] = recent
        self._save_to_disk()
        self.recentProjectsChanged.emit(recent)

    @Slot(result=list)
    def get_recent_projects(self):
        recent = self.settings.get("recent_projects", [])
        if not isinstance(recent, list):
            return []
        # Filter existing directories
        valid = []
        for p in recent:
            if isinstance(p, dict) and "path" in p and os.path.exists(p["path"]):
                valid.append(p)
        return valid

    @Slot(str)
    def save_session_state(self, session_json):
        try:
            data = json.loads(session_json)
            session_file = self.config_dir / "session_state.json"
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[SettingsBackend] Error saving session state: {e}")

    @Slot(result=str)
    def get_session_state(self):
        session_file = self.config_dir / "session_state.json"
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"[SettingsBackend] Error reading session state: {e}")
        return "{}"

    @Slot(str, str)
    def save_project_session(self, project_path: str, session_json: str):
        if not project_path or not session_json:
            return
        try:
            norm_key = os.path.normpath(project_path).lower()
            data = json.loads(session_json)
            sessions_file = self.config_dir / "workspace_sessions.json"
            all_sessions = {}
            if sessions_file.exists():
                try:
                    with open(sessions_file, "r", encoding="utf-8") as f:
                        all_sessions = json.load(f)
                except Exception:
                    all_sessions = {}
            all_sessions[norm_key] = data
            with open(sessions_file, "w", encoding="utf-8") as f:
                json.dump(all_sessions, f, indent=2)
        except Exception as e:
            print(f"[SettingsBackend] Error saving project session: {e}")

    @Slot(str, result=str)
    def get_project_session(self, project_path: str) -> str:
        if not project_path:
            return "{}"
        try:
            norm_key = os.path.normpath(project_path).lower()
            sessions_file = self.config_dir / "workspace_sessions.json"
            if sessions_file.exists():
                with open(sessions_file, "r", encoding="utf-8") as f:
                    all_sessions = json.load(f)
                if norm_key in all_sessions:
                    return json.dumps(all_sessions[norm_key])
        except Exception as e:
            print(f"[SettingsBackend] Error reading project session: {e}")
        return "{}"

    @Slot()
    def clear_session_state(self):
        session_file = self.config_dir / "session_state.json"
        if session_file.exists():
            try:
                session_file.unlink()
            except Exception as e:
                print(f"[SettingsBackend] Error clearing session state: {e}")

    @Slot(result=list)
    def get_radial_menu_config(self):
        default_items = [
            { "slot": 1, "id": "format", "label": "Formatter", "icon": "sparkles", "shortcut": "Shift+Alt+F", "custom": False, "action": "" },
            { "slot": 2, "id": "run", "label": "Run", "icon": "play", "shortcut": "F5", "custom": False, "action": "" },
            { "slot": 3, "id": "copy", "label": "Copy", "icon": "copy", "shortcut": "Ctrl+C", "custom": False, "action": "" },
            { "slot": 4, "id": "cut", "label": "Cut", "icon": "close", "shortcut": "Ctrl+X", "custom": False, "action": "" },
            { "slot": 5, "id": "paste", "label": "Paste", "icon": "file", "shortcut": "Ctrl+V", "custom": False, "action": "" },
            { "slot": 6, "id": "undo", "label": "Undo", "icon": "undo", "shortcut": "Ctrl+Z", "custom": False, "action": "" },
            { "slot": 7, "id": "find", "label": "Find", "icon": "search", "shortcut": "Ctrl+F", "custom": False, "action": "" }
        ]
        saved = self.settings.get("radial_menu_items")
        if isinstance(saved, list) and len(saved) == 7:
            return saved
        return default_items

    @Slot(str)
    def save_radial_menu_config(self, config_json):
        try:
            items = json.loads(config_json)
            if isinstance(items, list):
                self.settings["radial_menu_items"] = items
                self._save_to_disk()
                self.settingChanged.emit("radial_menu_items", config_json)
        except Exception as e:
            print(f"[SettingsBackend] Error saving radial menu config: {e}")

    @Slot(result=list)
    def reset_radial_menu_config(self):
        default_items = [
            { "slot": 1, "id": "format", "label": "Formatter", "icon": "sparkles", "shortcut": "Shift+Alt+F", "custom": False, "action": "" },
            { "slot": 2, "id": "run", "label": "Run", "icon": "play", "shortcut": "F5", "custom": False, "action": "" },
            { "slot": 3, "id": "copy", "label": "Copy", "icon": "copy", "shortcut": "Ctrl+C", "custom": False, "action": "" },
            { "slot": 4, "id": "cut", "label": "Cut", "icon": "close", "shortcut": "Ctrl+X", "custom": False, "action": "" },
            { "slot": 5, "id": "paste", "label": "Paste", "icon": "file", "shortcut": "Ctrl+V", "custom": False, "action": "" },
            { "slot": 6, "id": "undo", "label": "Undo", "icon": "undo", "shortcut": "Ctrl+Z", "custom": False, "action": "" },
            { "slot": 7, "id": "find", "label": "Find", "icon": "search", "shortcut": "Ctrl+F", "custom": False, "action": "" }
        ]
        self.settings["radial_menu_items"] = default_items
        self._save_to_disk()
        self.settingChanged.emit("radial_menu_items", json.dumps(default_items))
        return default_items

    @Slot(result=list)
    def get_custom_actions(self):
        saved = self.settings.get("radial_custom_actions")
        if isinstance(saved, list):
            normalized = []
            for item in saved:
                if isinstance(item, dict):
                    it = dict(item)
                    label_val = it.get("label") or it.get("name") or "Custom Action"
                    it["label"] = label_val
                    it["name"] = label_val

                    type_val = it.get("action_type") or it.get("type") or "bash"
                    it["action_type"] = type_val.lower()
                    it["type"] = type_val.lower()

                    # Extract commands list
                    raw_cmds = it.get("commands")
                    if isinstance(raw_cmds, list) and raw_cmds:
                        cmds = [str(c).strip() for c in raw_cmds if str(c).strip()]
                    elif "command" in it and isinstance(it["command"], str):
                        cmds = [it["command"].strip()]
                    elif "action" in it and isinstance(it["action"], str):
                        cmds = [line.strip() for line in it["action"].split("\n") if line.strip()]
                    else:
                        cmds = []

                    it["commands"] = cmds
                    it["action"] = "\n".join(cmds)
                    it["custom"] = True
                    it["shortcut"] = "CMD" if it["action_type"] == "cmd" else "Bash"
                    normalized.append(it)
            return normalized
        return []

    @Slot(str)
    def save_custom_actions(self, custom_actions_json):
        try:
            items = json.loads(custom_actions_json)
            if isinstance(items, list):
                normalized = []
                for item in items:
                    if isinstance(item, dict):
                        it = dict(item)
                        label_val = it.get("label") or it.get("name") or "Custom Action"
                        it["label"] = label_val
                        it["name"] = label_val
                        type_val = it.get("action_type") or it.get("type") or "bash"
                        it["action_type"] = type_val.lower()
                        it["type"] = type_val.lower()

                        raw_cmds = it.get("commands")
                        if isinstance(raw_cmds, list) and raw_cmds:
                            cmds = [str(c).strip() for c in raw_cmds if str(c).strip()]
                        elif "command" in it and isinstance(it["command"], str):
                            cmds = [it["command"].strip()]
                        elif "action" in it and isinstance(it["action"], str):
                            cmds = [line.strip() for line in it["action"].split("\n") if line.strip()]
                        else:
                            cmds = []

                        it["commands"] = cmds
                        it["action"] = "\n".join(cmds)
                        it["custom"] = True
                        it["shortcut"] = "CMD" if it["action_type"] == "cmd" else "Bash"
                        normalized.append(it)

                self.settings["radial_custom_actions"] = normalized
                self._save_to_disk()
                self.settingChanged.emit("radial_custom_actions", json.dumps(normalized))
        except Exception as e:
            print(f"[SettingsBackend] Error saving custom actions: {e}")

    def _get_theme_dirs(self):
        dirs = []
        app_themes = Path(__file__).parent / "themes"
        if app_themes.exists() and app_themes.is_dir():
            dirs.append(app_themes)
        user_themes = self.config_dir / "themes"
        if user_themes.exists() and user_themes.is_dir():
            dirs.append(user_themes)
        for extra in [Path.home() / ".pod_studio" / "themes", Path.home() / ".dgx_studio" / "themes"]:
            if extra.exists() and extra.is_dir() and extra not in dirs:
                dirs.append(extra)
        return dirs

    @Slot(result=str)
    def get_saved_theme_data(self):
        saved_theme = self.get_value("theme", "nord")
        return self.get_theme_data(saved_theme)

    @Slot(result=str)
    def get_saved_theme_name(self):
        return self.get_value("theme", "nord")

    @Slot(result=list)
    def get_available_themes(self):
        themes = []
        seen_ids = set()
        for tdir in self._get_theme_dirs():
            try:
                for file_path in sorted(tdir.glob("*.json")):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        tid = str(data.get("id", file_path.stem)).lower()
                        if tid in seen_ids:
                            continue
                        seen_ids.add(tid)
                        themes.append({
                            "id": tid,
                            "name": str(data.get("name", file_path.stem.capitalize())),
                            "color": str(data.get("color", data.get("bgRoot", "#181818"))),
                            "type": str(data.get("type", "dark"))
                        })
                    except Exception as err:
                        print(f"[SettingsBackend] Error reading theme file {file_path}: {err}")
            except Exception as e:
                print(f"[SettingsBackend] Error listing themes in {tdir}: {e}")
        return themes

    @Slot(str, result=str)
    def get_theme_data(self, name: str):
        if not name:
            name = "obsidian"
        target_name = name.lower().strip()
        for tdir in self._get_theme_dirs():
            direct_file = tdir / f"{target_name}.json"
            if direct_file.exists():
                try:
                    with open(direct_file, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception as err:
                    print(f"[SettingsBackend] Error reading {direct_file}: {err}")
            # Case-insensitive search
            try:
                for file_path in tdir.glob("*.json"):
                    if file_path.stem.lower() == target_name:
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                return f.read()
                        except Exception as err:
                            print(f"[SettingsBackend] Error reading {file_path}: {err}")
            except Exception:
                pass

        # Fallback to obsidian.json if not found
        for tdir in self._get_theme_dirs():
            fallback_file = tdir / "obsidian.json"
            if fallback_file.exists():
                try:
                    with open(fallback_file, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass
        return "{}"

    def _ensure_default_icon_theme(self):
        try:
            if not self.icon_theme_file.exists():
                self.config_dir.mkdir(parents=True, exist_ok=True)
                default_theme = {
                    "themeName": "Pod Material Colorful",
                    "description": "Customizable Icon Theme for Pod Studio. Add, edit, or customize folder and file colors/icons below.",
                    "folders": {
                        "assets": { "color": "#f59e0b", "icon": "folder" },
                        "scripts": { "color": "#06b6d4", "icon": "folder" },
                        "scenes": { "color": "#a855f7", "icon": "folder" },
                        "packages": { "color": "#3b82f6", "icon": "folder" },
                        ".vscode": { "color": "#38bdf8", "icon": "folder" },
                        "misc": { "color": "#f97316", "icon": "folder" },
                        "npc": { "color": "#10b981", "icon": "folder" },
                        "player": { "color": "#10b981", "icon": "folder" },
                        "behaviours": { "color": "#14b8a6", "icon": "folder" },
                        "core": { "color": "#6366f1", "icon": "folder" },
                        "prefabs": { "color": "#059669", "icon": "folder" },
                        "materials": { "color": "#ec4899", "icon": "folder" },
                        "audio": { "color": "#d946ef", "icon": "folder" },
                        "urp": { "color": "#9333ea", "icon": "folder" },
                        "editor": { "color": "#eab308", "icon": "folder" },
                        "tests": { "color": "#22c55e", "icon": "folder" },
                        "docs": { "color": "#0284c7", "icon": "folder" }
                    },
                    "files": {
                        "cs": { "color": "#38bdf8", "icon": "file-code" },
                        "sln": { "color": "#a855f7", "icon": "file-code" },
                        "slnx": { "color": "#a855f7", "icon": "file-code" },
                        "csproj": { "color": "#a855f7", "icon": "file-code" },
                        "unity": { "color": "#10b981", "icon": "file-code" },
                        "prefab": { "color": "#10b981", "icon": "file-code" },
                        "mat": { "color": "#10b981", "icon": "file-code" },
                        "shader": { "color": "#10b981", "icon": "file-code" },
                        "py": { "color": "#38bdf8", "icon": "file-code" },
                        "js": { "color": "#facc15", "icon": "file-code" },
                        "ts": { "color": "#3b82f6", "icon": "file-code" },
                        "cpp": { "color": "#60a5fa", "icon": "file-code" },
                        "json": { "color": "#facc15", "icon": "file-code" }
                    }
                }
                with open(self.icon_theme_file, "w", encoding="utf-8") as f:
                    json.dump(default_theme, f, indent=2)
        except Exception as e:
            print(f"[SettingsBackend] Error creating default icon_theme.json: {e}")

    @Slot(result=str)
    def get_icon_theme_json(self) -> str:
        if self.icon_theme_file.exists():
            try:
                with open(self.icon_theme_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"[SettingsBackend] Error reading icon_theme.json: {e}")
        return "{}"

    @Slot(str, result=bool)
    def save_icon_theme_json(self, content: str) -> bool:
        try:
            parsed = json.loads(content)
            with open(self.icon_theme_file, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2)
            self.iconThemeChanged.emit()
            return True
        except Exception as e:
            print(f"[SettingsBackend] Error saving icon_theme.json: {e}")
            return False

    @Slot(result=str)
    def get_icon_theme_file_path(self) -> str:
        return str(self.icon_theme_file).replace("\\", "/")


