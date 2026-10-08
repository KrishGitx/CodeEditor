"""
SettingsBackend.py - Persistent User Preferences Manager for DGX Studio
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

    def __init__(self):
        super().__init__()
        # Store settings in user home directory under .dgx_studio/settings.json
        self.config_dir = Path.home() / ".dgx_studio"
        self.config_file = self.config_dir / "settings.json"
        self.settings = self._load_default_settings()
        self._load_from_disk()

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
            "terminal_visible": True,
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

