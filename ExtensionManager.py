"""
ExtensionManager.py - Modular Extension Architecture for DGX Studio
Manages extension discovery, manifest loading, local installation, permissions inspection,
contributed features (commands, runners, formatters, file icons, radial actions, tool dependencies),
lifecycle activation, and Smart Install system for developer tools.
"""

import os
import sys
import time
import json
import shutil
import zipfile
import subprocess
import threading
import glob
import importlib.util
from typing import Dict, List, Optional, Any, Callable
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication


def get_current_os() -> str:
    s = sys.platform.lower()
    if s.startswith("win"):
        return "windows"
    elif s.startswith("darwin"):
        return "macos"
    return "linux"


def locate_executable(cmd: str, custom_path: Optional[str] = None) -> Optional[str]:
    """
    Comprehensive multi-location locator for executables across:
      1. User-configured custom path
      2. System PATH
      3. Active Python environment's Scripts / bin directory (where pip packages like clang-format, autopep8 install)
      4. AppData / Homebrew / npm / cargo / go bin directories
      5. Standard Visual Studio / LLVM / MinGW / MSYS2 locations on Windows
    """
    if not cmd:
        return None

    is_win = sys.platform.startswith("win")
    bin_name = f"{cmd}.exe" if is_win else cmd

    # 1. User configured custom path
    if custom_path and os.path.isfile(custom_path):
        if not is_win or custom_path.lower().endswith((".exe", ".cmd", ".bat", ".com")):
            return os.path.abspath(custom_path)

    # 2. Standard system PATH
    found = shutil.which(cmd)
    if found and os.path.isfile(found):
        return os.path.abspath(found)

    # 3. Python environment Scripts / bin directories
    candidates = []
    py_dir = os.path.dirname(sys.executable)

    candidates.append(os.path.join(py_dir, "Scripts", bin_name))
    candidates.append(os.path.join(py_dir, "bin", bin_name))
    candidates.append(os.path.join(sys.prefix, "Scripts", bin_name))
    candidates.append(os.path.join(sys.prefix, "bin", bin_name))
    candidates.append(os.path.join(os.path.expanduser("~"), ".dgx", "bin", bin_name))
    candidates.append(os.path.join(os.path.expanduser("~"), ".local", "bin", bin_name))
    candidates.append(os.path.join(os.path.expanduser("~"), ".cargo", "bin", bin_name))
    candidates.append(os.path.join(os.path.expanduser("~"), "go", "bin", bin_name))

    if is_win:
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        app_data = os.environ.get("APPDATA", "")
        if local_app_data:
            for p in glob.glob(os.path.join(local_app_data, "Python", "*", "Scripts", bin_name)):
                candidates.append(p)
            for p in glob.glob(os.path.join(local_app_data, "Programs", "Python", "*", "Scripts", bin_name)):
                candidates.append(p)
        if app_data:
            for p in glob.glob(os.path.join(app_data, "Python", "*", "Scripts", bin_name)):
                candidates.append(p)
            candidates.append(os.path.join(app_data, "npm", f"{cmd}.cmd"))
            candidates.append(os.path.join(app_data, "npm", bin_name))

    # 4. Common locations for clang-format and compilers on Windows
    if cmd.lower().startswith("clang-format") and is_win:
        vs_globs = [
            r"C:\Program Files\Microsoft Visual Studio\*\*\VC\Tools\Llvm\bin\clang-format.exe",
            r"C:\Program Files (x86)\Microsoft Visual Studio\*\*\VC\Tools\Llvm\bin\clang-format.exe",
            r"C:\Program Files\Microsoft Visual Studio\*\*\VC\Tools\Llvm\x64\bin\clang-format.exe",
            r"C:\Program Files\LLVM\bin\clang-format.exe",
            r"C:\Program Files (x86)\LLVM\bin\clang-format.exe",
            r"C:\msys64\mingw64\bin\clang-format.exe",
            r"C:\msys64\ucrt64\bin\clang-format.exe",
            r"C:\msys64\clang64\bin\clang-format.exe",
            r"C:\MinGW\bin\clang-format.exe"
        ]
        for pattern in vs_globs:
            for match in glob.glob(pattern):
                if os.path.isfile(match):
                    return os.path.abspath(match)

    # 5. Common locations for Unix / macOS
    if not is_win:
        unix_paths = [
            f"/opt/homebrew/bin/{cmd}",
            f"/usr/local/bin/{cmd}",
            f"/usr/bin/{cmd}",
            f"/bin/{cmd}",
            os.path.expanduser(f"~/.local/bin/{cmd}")
        ]
        for p in unix_paths:
            if os.path.isfile(p):
                return os.path.abspath(p)

    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)

    return None


class DGXExtensionContext:
    """Stable Extension API Context passed to extension entry points."""
    def __init__(self, extension_id: str, manager: 'ExtensionManager'):
        self.extension_id = extension_id
        self._manager = manager

    def register_command(self, command_id: str, callback: Callable):
        self._manager.register_extension_command(self.extension_id, command_id, callback)

    def register_formatter(self, lang: str, spec: dict):
        self._manager.register_extension_formatter(self.extension_id, lang, spec)

    def register_runner(self, ext: str, spec: dict):
        self._manager.register_extension_runner(self.extension_id, ext, spec)

    def register_file_icon(self, ext: str, spec: dict):
        self._manager.register_extension_file_icon(self.extension_id, ext, spec)

    def register_radial_action(self, action_spec: dict):
        self._manager.register_extension_radial_action(self.extension_id, action_spec)

    def register_tool_dependency(self, name: str, spec: dict):
        self._manager.register_extension_tool_dependency(self.extension_id, name, spec)

    def show_message(self, message: str, level: str = "info"):
        self._manager.extensionMessageEmitted.emit(self.extension_id, message, level)

    def get_active_editor_context(self) -> dict:
        return self._manager.get_active_editor_context()


class Extension:
    def __init__(self, manifest: dict, path: str, user_dir: str = "", custom_path: str = ""):
        self.manifest: dict = manifest
        self.id: str = manifest.get("id", manifest.get("name", "unknown"))
        self.name: str = manifest.get("name", self.id)
        self.displayName: str = manifest.get("displayName", self.name)
        self.version: str = manifest.get("version", "1.0.0")
        self.description: str = manifest.get("description", "")
        self.author: str = manifest.get("author", manifest.get("publisher", "DGX Community"))
        self.publisher: str = manifest.get("publisher", self.author)
        self.main: str = manifest.get("main", "")
        self.icon: str = manifest.get("icon", "")
        self.permissions: List[str] = manifest.get("permissions", [])
        self.activationEvents: List[str] = manifest.get("activationEvents", ["*"])
        self.contributes: dict = manifest.get("contributes", {})

        # Language / Extension Mappings
        self.languages: List[str] = [l.lower() for l in manifest.get("languages", self.contributes.get("languages", []))]
        self.extensions: List[str] = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in manifest.get("extensions", self.contributes.get("extensions", []))]

        # Formatter & LSP declarations
        self.formatter: Optional[dict] = manifest.get("formatter")
        if not self.formatter and "formatters" in self.contributes and self.contributes["formatters"]:
            self.formatter = self.contributes["formatters"][0]

        self.lsp: Optional[dict] = manifest.get("lsp")

        self.path: str = path
        self.user_dir: str = user_dir
        self.custom_path: str = custom_path
        self.enabled: bool = True
        self.activated: bool = False
        self.module_instance: Any = None

    def matches_language(self, lang_id: str, file_path: str = "") -> bool:
        if not self.enabled:
            return False
        clean_lang = (lang_id or "").lower().strip()
        if clean_lang and clean_lang in self.languages:
            return True
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext and ext in self.extensions:
                return True
        return False

    def get_executable_path(self) -> Optional[str]:
        if not self.formatter:
            return None
        fmt = self.formatter
        fmt_type = fmt.get("type", "cli") if isinstance(fmt, dict) else "cli"
        if fmt_type == "json":
            return "Built-in (Python Standard Library)"
        if fmt_type == "python":
            try:
                import autopep8
                return getattr(autopep8, "__file__", "Python autopep8 module")
            except ImportError:
                for t in ["black", "ruff", "autopep8"]:
                    p = locate_executable(t, self.custom_path)
                    if p:
                        return p
            return None

        cmd = (fmt.get("command") if isinstance(fmt, dict) else fmt) or (fmt.get("executable") if isinstance(fmt, dict) else "") or ""
        return locate_executable(cmd, self.custom_path)

    def check_formatter_status(self) -> dict:
        if not self.formatter:
            return {
                "hasFormatter": False,
                "provider": "",
                "type": "",
                "executable": "",
                "isInstalled": False,
                "detectedPath": "",
                "installCommand": "",
                "installInstructions": "",
                "docsUrl": "",
                "currentOs": get_current_os()
            }

        fmt = self.formatter
        if isinstance(fmt, str):
            fmt_type = "cli"
            provider = fmt
            executable = fmt
            install_guide = {}
        elif isinstance(fmt, dict):
            fmt_type = fmt.get("type", "cli")
            provider = fmt.get("provider", "")
            executable = fmt.get("executable") or fmt.get("command") or provider
            install_guide = fmt.get("installGuide", {})
        else:
            fmt_type = "cli"
            provider = ""
            executable = ""
            install_guide = {}
        cur_os = get_current_os()

        is_installed = False
        detected_path = ""

        if fmt_type == "json":
            is_installed = True
            detected_path = "Built-in (Python Standard Library)"
        elif fmt_type == "python":
            try:
                import autopep8
                is_installed = True
                detected_path = getattr(autopep8, "__file__", "Python autopep8 module")
            except ImportError:
                for t in ["black", "ruff", "autopep8"]:
                    p = locate_executable(t, self.custom_path)
                    if p:
                        is_installed = True
                        detected_path = p
                        break
        elif fmt_type == "cli":
            p = self.get_executable_path()
            if p:
                is_installed = True
                detected_path = p

        install_cmd = install_guide.get("lightweight", "") or install_guide.get(cur_os, "") or install_guide.get("all", "")
        install_inst = install_guide.get("instructions", "")
        docs_url = install_guide.get("docsUrl", "")
        has_lightweight = bool(self.id in ("dgx.cpp", "dgx.python", "dgx.javascript") or install_guide.get("lightweight") or install_cmd)

        return {
            "hasFormatter": True,
            "provider": provider,
            "type": fmt_type,
            "executable": executable,
            "isInstalled": is_installed,
            "detectedPath": detected_path,
            "installCommand": install_cmd,
            "installInstructions": install_inst,
            "docsUrl": docs_url,
            "currentOs": cur_os,
            "hasLightweightInstaller": has_lightweight
        }

    def to_dict(self) -> dict:
        fmt_status = self.check_formatter_status()
        is_user = bool(self.user_dir and os.path.normpath(self.path).startswith(os.path.normpath(self.user_dir)))
        return {
            "id": self.id,
            "name": self.name,
            "displayName": self.displayName,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "publisher": self.publisher,
            "main": self.main,
            "icon": self.icon,
            "permissions": self.permissions,
            "activationEvents": self.activationEvents,
            "contributes": self.contributes,
            "languages": self.languages,
            "extensions": self.extensions,
            "path": self.path,
            "location": self.path,
            "enabled": self.enabled,
            "activated": self.activated,
            "isBuiltIn": not is_user,
            "isUserInstalled": is_user,
            "hasFormatter": fmt_status["hasFormatter"],
            "formatter": fmt_status["provider"],
            "formatterProvider": fmt_status["provider"],
            "executable": fmt_status["executable"],
            "formatterDependency": fmt_status["executable"],
            "formatterInstalled": fmt_status["isInstalled"],
            "formatterDetectedPath": fmt_status["detectedPath"],
            "installCommand": fmt_status["installCommand"],
            "installInstructions": fmt_status["installInstructions"],
            "docsUrl": fmt_status["docsUrl"],
            "currentOs": fmt_status["currentOs"],
            "hasLightweightInstaller": fmt_status.get("hasLightweightInstaller", True)
        }


class ExtensionManager(QObject):
    extensionsChanged = Signal()
    extensionInstalled = Signal(str)  # extension_id
    extensionUninstalled = Signal(str)  # extension_id
    updateCheckCompleted = Signal(dict)
    formatterInstallProgress = Signal(str, str, str)  # extension_id, status, message
    smartInstallProgress = Signal(str, str, str)  # tool_name, status ("installing"|"success"|"failed"), message
    smartInstallCompleted = Signal(str, bool, str, str)  # tool_name, success, message, retry_action
    extensionMessageEmitted = Signal(str, str, str)  # extension_id, message, level
    commandExecuted = Signal(str, str)  # command_id, result_message

    def __init__(self, base_dir: Optional[str] = None):
        super().__init__()
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.built_in_dir = os.path.join(self.base_dir, "extensions")
        self.user_extensions_dir = os.path.join(os.path.expanduser("~"), ".dgx", "extensions")
        self.state_file = os.path.join(os.path.expanduser("~"), ".dgx", "disabled_extensions.json")
        self.custom_paths_file = os.path.join(os.path.expanduser("~"), ".dgx", "custom_formatter_paths.json")

        os.makedirs(self.built_in_dir, exist_ok=True)
        os.makedirs(self.user_extensions_dir, exist_ok=True)

        self._disabled_ids = self._load_disabled_state()
        self._custom_paths = self._load_custom_paths()
        self._installing_formatters = set()
        self._installing_tools = set()
        self._extensions: Dict[str, Extension] = {}

        # Contributed registries
        self._contributed_commands: Dict[str, dict] = {}
        self._contributed_runners: Dict[str, dict] = {}
        self._contributed_file_icons: List[dict] = []
        self._contributed_radial_actions: List[dict] = []
        self._contributed_tool_dependencies: Dict[str, dict] = {}

        self.editor_backend = None
        self.ai_backend = None

        self.reload_extensions()

    def _load_disabled_state(self) -> set:
        if os.path.isfile(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
            except Exception as e:
                print(f"[ExtensionManager] Notice reading {self.state_file}: {e}")
        return set()

    def _save_disabled_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(list(self._disabled_ids), f, indent=2)
        except Exception as e:
            print(f"[ExtensionManager] Notice saving {self.state_file}: {e}")

    def _load_custom_paths(self) -> dict:
        if os.path.isfile(self.custom_paths_file):
            try:
                with open(self.custom_paths_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                print(f"[ExtensionManager] Notice reading {self.custom_paths_file}: {e}")
        return {}

    def _save_custom_paths(self):
        try:
            with open(self.custom_paths_file, "w", encoding="utf-8") as f:
                json.dump(self._custom_paths, f, indent=2)
        except Exception as e:
            print(f"[ExtensionManager] Notice saving {self.custom_paths_file}: {e}")

    @Slot()
    def reload_extensions(self):
        """Scans both built-in and user extension directories for manifests and registers contributions."""
        self._extensions.clear()
        self._contributed_commands.clear()
        self._contributed_runners.clear()
        self._contributed_file_icons.clear()
        self._contributed_radial_actions.clear()
        self._contributed_tool_dependencies.clear()

        # 1. Load built-in extensions
        self._load_from_directory(self.built_in_dir, is_user=False)

        # 2. Load user-installed extensions
        self._load_from_directory(self.user_extensions_dir, is_user=True)

        # Apply disabled state and custom paths
        for ext_id, ext in self._extensions.items():
            ext.enabled = (ext_id not in self._disabled_ids)
            ext.custom_path = self._custom_paths.get(ext_id, "")

            if ext.enabled:
                self._register_declarative_contributes(ext)
                if ext.main and not ext.activated:
                    self.activate_extension(ext.id)

        print(f"[ExtensionManager] Loaded {len(self._extensions)} extensions: {list(self._extensions.keys())}")
        self.extensionsChanged.emit()

    def _load_from_directory(self, root_dir: str, is_user: bool):
        if not os.path.isdir(root_dir):
            return
        for item in os.listdir(root_dir):
            ext_path = os.path.join(root_dir, item)
            manifest_file = os.path.join(ext_path, "extension.json")
            if os.path.isfile(manifest_file):
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    ext_id = manifest.get("id", manifest.get("name", item))
                    if ext_id:
                        custom_p = self._custom_paths.get(ext_id, "")
                        self._extensions[ext_id] = Extension(
                            manifest, ext_path,
                            self.user_extensions_dir if is_user else "",
                            custom_path=custom_p
                        )
                except Exception as e:
                    print(f"[ExtensionManager] Notice loading manifest at {manifest_file}: {e}")

    def _register_declarative_contributes(self, ext: Extension):
        contribs = ext.contributes
        if not contribs or not isinstance(contribs, dict):
            return

        # Commands
        for cmd in contribs.get("commands", []):
            if isinstance(cmd, dict) and "command" in cmd:
                cid = cmd["command"]
                self._contributed_commands[cid] = {
                    "command": cid,
                    "title": cmd.get("title", cid),
                    "category": cmd.get("category", ext.displayName),
                    "extension_id": ext.id,
                    "callback": None
                }

        # Runners
        for r in contribs.get("runners", []):
            if isinstance(r, dict) and "extension" in r:
                r_ext = r["extension"].lower().lstrip(".")
                self._contributed_runners[r_ext] = {
                    "extension": r_ext,
                    "command": r.get("command", ""),
                    "name": r.get("name", f"{ext.name} Runner"),
                    "extension_id": ext.id
                }

        # File Icons
        for fi in contribs.get("fileIcons", []):
            if isinstance(fi, dict):
                item = dict(fi)
                item["extension_id"] = ext.id
                self._contributed_file_icons.append(item)

        # Radial Actions
        for ra in contribs.get("radialActions", []):
            if isinstance(ra, dict):
                item = dict(ra)
                item["extension_id"] = ext.id
                self._contributed_radial_actions.append(item)

        # Tool Dependencies
        for td in contribs.get("toolDependencies", []):
            if isinstance(td, dict) and "name" in td:
                self._contributed_tool_dependencies[td["name"]] = {
                    "name": td["name"],
                    "executable": td.get("executable", td["name"]),
                    "installGuide": td.get("installGuide", {}),
                    "extension_id": ext.id
                }

    @Slot(str, result=bool)
    def activate_extension(self, extension_id: str) -> bool:
        ext = self.get_extension(extension_id)
        if not ext or not ext.enabled or not ext.main:
            return False

        entry_path = os.path.join(ext.path, ext.main)
        if not os.path.isfile(entry_path):
            return False

        try:
            spec = importlib.util.spec_from_file_location(f"dgx_ext_{ext.id.replace('.', '_')}", entry_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                ext.module_instance = module
                ext.activated = True

                # Call activate(context) if implemented
                if hasattr(module, "activate"):
                    ctx = DGXExtensionContext(ext.id, self)
                    module.activate(ctx)
                print(f"[ExtensionManager] Activated extension '{ext.id}' successfully.")
                return True
        except Exception as e:
            print(f"[ExtensionManager] Error activating extension '{ext.id}': {e}")
        return False

    def register_extension_command(self, ext_id: str, command_id: str, callback: Callable):
        if command_id in self._contributed_commands:
            self._contributed_commands[command_id]["callback"] = callback
        else:
            self._contributed_commands[command_id] = {
                "command": command_id,
                "title": command_id,
                "category": ext_id,
                "extension_id": ext_id,
                "callback": callback
            }

    def register_extension_formatter(self, ext_id: str, lang: str, spec: dict):
        ext = self.get_extension(ext_id)
        if ext:
            ext.formatter = spec

    def register_extension_runner(self, ext_id: str, ext: str, spec: dict):
        clean_ext = ext.lower().lstrip(".")
        self._contributed_runners[clean_ext] = {
            "extension": clean_ext,
            "command": spec.get("command", ""),
            "name": spec.get("name", f"{ext_id} Runner"),
            "extension_id": ext_id
        }

    def register_extension_file_icon(self, ext_id: str, ext: str, spec: dict):
        item = dict(spec)
        item["extension"] = ext
        item["extension_id"] = ext_id
        self._contributed_file_icons.append(item)

    def register_extension_radial_action(self, ext_id: str, action_spec: dict):
        item = dict(action_spec)
        item["extension_id"] = ext_id
        self._contributed_radial_actions.append(item)

    def register_extension_tool_dependency(self, ext_id: str, name: str, spec: dict):
        self._contributed_tool_dependencies[name] = {
            "name": name,
            "executable": spec.get("executable", name),
            "installGuide": spec.get("installGuide", {}),
            "extension_id": ext_id
        }

    @Slot(result=list)
    def get_installed_extensions(self) -> List[dict]:
        return [ext.to_dict() for ext in self._extensions.values()]

    def get_extension(self, extension_id: str) -> Optional[Extension]:
        if not extension_id:
            return None
        if extension_id in self._extensions:
            return self._extensions[extension_id]
        if f"dgx.{extension_id}" in self._extensions:
            return self._extensions[f"dgx.{extension_id}"]
        for ext in self._extensions.values():
            if ext.id.lower() == extension_id.lower() or ext.name.lower() == extension_id.lower():
                return ext
        return None

    def get_extension_for_language(self, lang_id: str, file_path: str = "") -> Optional[Extension]:
        for ext in self._extensions.values():
            if ext.matches_language(lang_id, file_path):
                return ext
        return None

    @Slot(str, result="QVariantMap")
    def get_runner_for_extension(self, ext: str) -> dict:
        clean = (ext or "").lower().lstrip(".")
        if clean in self._contributed_runners:
            return self._contributed_runners[clean]
        return {}

    @Slot(result=list)
    def get_custom_file_icons(self) -> list:
        return list(self._contributed_file_icons)

    @Slot(result=list)
    def get_contributed_commands(self) -> list:
        return [
            {"command": v["command"], "title": v.get("title", v["command"]), "category": v.get("category", "")}
            for v in self._contributed_commands.values()
        ]

    @Slot(result=list)
    def get_contributed_radial_actions(self) -> list:
        return list(self._contributed_radial_actions)

    @Slot(str, result="QVariantMap")
    def get_tool_dependency(self, tool_name: str) -> dict:
        return self._contributed_tool_dependencies.get(tool_name, {})

    @Slot(str, result="QVariantMap")
    def execute_command(self, command_id: str) -> dict:
        if command_id not in self._contributed_commands:
            return {"success": False, "message": f"Command '{command_id}' not found."}
        info = self._contributed_commands[command_id]
        cb = info.get("callback")
        if callable(cb):
            try:
                res = cb()
                msg = str(res) if res is not None else f"Executed {command_id}"
                self.commandExecuted.emit(command_id, msg)
                return {"success": True, "message": msg}
            except Exception as e:
                return {"success": False, "message": f"Error executing {command_id}: {e}"}
        else:
            msg = f"Triggered command: {info.get('title', command_id)}"
            self.commandExecuted.emit(command_id, msg)
            return {"success": True, "message": msg}

    def get_active_editor_context(self) -> dict:
        if self.editor_backend and hasattr(self.editor_backend, "get_editor_context"):
            return self.editor_backend.get_editor_context()
        return {}

    # =========================================================================
    # PERMISSIONS & SECURITY INSPECTION
    # =========================================================================
    @Slot(str, result="QVariantMap")
    def inspect_extension_package(self, source_path: str) -> dict:
        """
        Inspects an extension folder, zip archive (.zip/.dgxext), or manifest file before installation.
        Returns parsed manifest, requested permissions, descriptions, and security risk level.
        """
        if not source_path:
            return {"valid": False, "message": "No path provided."}

        clean = source_path
        if clean.startswith("file:///"):
            clean = clean[8:]
            if sys.platform.startswith("win") and clean.startswith("/"):
                clean = clean[1:]
        clean = os.path.abspath(os.path.normpath(clean))

        if not os.path.exists(clean):
            return {"valid": False, "message": f"Path does not exist: {clean}"}

        manifest = None
        pkg_type = "folder"

        try:
            if os.path.isdir(clean):
                manifest_file = os.path.join(clean, "extension.json")
                if not os.path.isfile(manifest_file):
                    return {"valid": False, "message": "Missing extension.json in directory."}
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                pkg_type = "folder"
            elif os.path.isfile(clean) and clean.lower().endswith((".zip", ".dgxext", ".vsix")):
                with zipfile.ZipFile(clean, 'r') as z:
                    for name in z.namelist():
                        if name.endswith("extension.json"):
                            with z.open(name) as f:
                                manifest = json.loads(f.read().decode('utf-8'))
                            break
                pkg_type = "package"
            elif os.path.isfile(clean) and clean.lower().endswith(".json"):
                with open(clean, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                pkg_type = "manifest"

            if not manifest or not isinstance(manifest, dict):
                return {"valid": False, "message": "Invalid or unreadable extension.json manifest."}

            ext_id = manifest.get("id", manifest.get("name", ""))
            if not ext_id:
                return {"valid": False, "message": "Manifest missing required 'id' or 'name' field."}

            permissions = manifest.get("permissions", [])
            permission_descriptions = {
                "workspace": "Read and write files within the open workspace project.",
                "terminal": "Execute automated commands and scripts in terminal sessions.",
                "process": "Spawn background helper processes and developer tools.",
                "network": "Make network requests to download tools and packages.",
                "ai": "Interact with the configured AI provider to analyze code snippets.",
                "editor": "Read active editor selections and apply automated code formatting."
            }

            perm_details = []
            for p in permissions:
                perm_details.append({
                    "name": p,
                    "description": permission_descriptions.get(p.lower(), f"Access capability '{p}'.")
                })

            security_level = "Standard"
            if "terminal" in permissions or "process" in permissions:
                security_level = "Elevated (Process/Terminal Access)"
            if len(permissions) == 0:
                security_level = "Safe (No elevated permissions)"

            return {
                "valid": True,
                "id": ext_id,
                "name": manifest.get("name", ext_id),
                "displayName": manifest.get("displayName", manifest.get("name", ext_id)),
                "version": manifest.get("version", "1.0.0"),
                "author": manifest.get("author", manifest.get("publisher", "DGX Community")),
                "publisher": manifest.get("publisher", manifest.get("author", "DGX Community")),
                "description": manifest.get("description", "DGX Studio extension package."),
                "permissions": permissions,
                "permissionDetails": perm_details,
                "securityLevel": security_level,
                "packageType": pkg_type,
                "path": clean,
                "contributes": manifest.get("contributes", {}),
                "message": "Valid extension manifest ready for installation."
            }
        except Exception as e:
            return {"valid": False, "message": f"Inspection error: {e}"}

    @Slot(str, result=bool)
    def install_local_extension(self, source_path: str) -> bool:
        """Installs an extension from a local directory, .dgxext, .zip archive, or .json manifest."""
        if not source_path:
            return False

        clean_path = source_path
        if clean_path.startswith("file:///"):
            clean_path = clean_path[8:]
            if sys.platform.startswith("win") and clean_path.startswith("/"):
                clean_path = clean_path[1:]
        clean_path = os.path.abspath(os.path.normpath(clean_path))

        if not os.path.exists(clean_path):
            print(f"[ExtensionManager] Path not found: {clean_path}")
            return False

        try:
            # 1. Directory containing extension.json
            if os.path.isdir(clean_path):
                manifest_file = os.path.join(clean_path, "extension.json")
                if not os.path.isfile(manifest_file):
                    print(f"[ExtensionManager] Invalid extension folder (missing extension.json): {clean_path}")
                    return False
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                ext_id = manifest.get("id", manifest.get("name"))
                if not ext_id:
                    return False
                target_dir = os.path.join(self.user_extensions_dir, ext_id.replace(".", "_"))
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                shutil.copytree(clean_path, target_dir)
                self.reload_extensions()
                self.extensionInstalled.emit(ext_id)
                print(f"[ExtensionManager] Successfully installed extension '{ext_id}' into {target_dir}")
                return True

            # 2. Direct extension.json file
            elif os.path.isfile(clean_path) and clean_path.lower().endswith(".json"):
                with open(clean_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                ext_id = manifest.get("id", manifest.get("name"))
                if not ext_id:
                    return False
                target_dir = os.path.join(self.user_extensions_dir, ext_id.replace(".", "_"))
                os.makedirs(target_dir, exist_ok=True)
                shutil.copyfile(clean_path, os.path.join(target_dir, "extension.json"))
                self.reload_extensions()
                self.extensionInstalled.emit(ext_id)
                return True

            # 3. Zip package (.zip / .dgxext / .vsix)
            elif os.path.isfile(clean_path) and (clean_path.lower().endswith(".zip") or clean_path.lower().endswith(".dgxext") or clean_path.lower().endswith(".vsix")):
                with zipfile.ZipFile(clean_path, 'r') as z:
                    temp_extract = os.path.join(self.user_extensions_dir, "_temp_extract")
                    if os.path.exists(temp_extract):
                        shutil.rmtree(temp_extract, ignore_errors=True)
                    z.extractall(temp_extract)

                    found_manifest = None
                    source_dir = None
                    for root, _, files in os.walk(temp_extract):
                        if "extension.json" in files:
                            found_manifest = os.path.join(root, "extension.json")
                            source_dir = root
                            break

                    if not found_manifest or not source_dir:
                        shutil.rmtree(temp_extract, ignore_errors=True)
                        return False

                    with open(found_manifest, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    ext_id = manifest.get("id", manifest.get("name"))
                    if not ext_id:
                        shutil.rmtree(temp_extract, ignore_errors=True)
                        return False

                    target_dir = os.path.join(self.user_extensions_dir, ext_id.replace(".", "_"))
                    if os.path.exists(target_dir):
                        shutil.rmtree(target_dir)
                    shutil.move(source_dir, target_dir)
                    shutil.rmtree(temp_extract, ignore_errors=True)
                    self.reload_extensions()
                    self.extensionInstalled.emit(ext_id)
                    print(f"[ExtensionManager] Successfully installed package extension '{ext_id}' into {target_dir}")
                    return True

        except Exception as e:
            print(f"[ExtensionManager] Install error: {e}")
            return False
        return False

    @Slot(str, result=bool)
    def uninstall_extension(self, extension_id: str) -> bool:
        ext = self.get_extension(extension_id)
        if not ext:
            return False
        if ext.path.startswith(self.user_extensions_dir):
            try:
                shutil.rmtree(ext.path)
                self.reload_extensions()
                self.extensionUninstalled.emit(extension_id)
                print(f"[ExtensionManager] Uninstalled user extension: {extension_id}")
                return True
            except Exception as e:
                print(f"[ExtensionManager] Uninstall error: {e}")
                return False
        else:
            return self.toggle_extension(extension_id, False)

    @Slot(str, bool, result=bool)
    def toggle_extension(self, extension_id: str, enabled: bool) -> bool:
        ext = self.get_extension(extension_id)
        if not ext:
            return False
        ext.enabled = enabled
        if enabled:
            self._disabled_ids.discard(ext.id)
        else:
            self._disabled_ids.add(ext.id)
        self._save_disabled_state()
        self.reload_extensions()
        print(f"[ExtensionManager] Extension '{ext.id}' enabled set to {enabled}")
        return True

    @Slot(str, result=bool)
    def open_extension_folder(self, extension_id: str) -> bool:
        ext = self.get_extension(extension_id)
        if not ext or not os.path.exists(ext.path):
            return False
        try:
            if sys.platform.startswith("win"):
                os.startfile(ext.path)
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", ext.path])
            else:
                subprocess.run(["xdg-open", ext.path])
            return True
        except Exception as e:
            print(f"[ExtensionManager] Error opening folder {ext.path}: {e}")
            return False

    # =========================================================================
    # SMART INSTALL SYSTEM (For Formatters, Linters, Runners, Compilers)
    # =========================================================================
    @Slot(str, str, str, str, str, result="QVariantMap")
    def suggest_smart_install(self, tool_type: str, tool_name: str, lang_id: str, ext: str, file_path: str = "") -> dict:
        """
        Suggests an exact Smart Install command proposal based on:
        1. Known recipes / package managers (pip, npm, cargo, winget, etc.)
        2. Installed extension tool dependencies
        3. Configured AI suggestion fallback
        """
        cur_os = get_current_os()
        clean_lang = (lang_id or "").lower().strip()
        clean_ext = (ext or "").lower().lstrip(".")
        tool_lower = (tool_name or "").lower().strip()

        # Check if already installed
        exec_to_check = tool_name
        if "qml" in clean_lang or clean_ext == "qml" or "qml" in tool_lower:
            exec_to_check = "qmlformat"
        elif "python" in clean_lang or clean_ext in ("py", "pyw") or "autopep8" in tool_lower:
            exec_to_check = "autopep8"
        elif "cpp" in clean_lang or "c++" in clean_lang or clean_ext in ("cpp", "cxx", "cc", "h") or "clang" in tool_lower:
            exec_to_check = "clang-format"
        elif "js" in clean_lang or "javascript" in clean_lang or clean_ext in ("js", "ts", "jsx", "tsx") or "prettier" in tool_lower:
            exec_to_check = "prettier"
        elif "rust" in clean_lang or clean_ext == "rs" or "rustfmt" in tool_lower:
            exec_to_check = "rustfmt"
        elif "go" in clean_lang or clean_ext == "go" or "gofmt" in tool_lower:
            exec_to_check = "gofmt"

        existing_p = locate_executable(exec_to_check)
        if existing_p:
            return {
                "isInstalled": True,
                "detectedPath": existing_p,
                "toolName": tool_name or exec_to_check,
                "executable": exec_to_check,
                "message": f"{tool_name or exec_to_check} is already installed at {existing_p}."
            }

        # 1. Known Recipes
        known_recipes = {
            "qmlformat": {
                "toolName": "QML Formatter (qmlformat)",
                "toolType": "formatter",
                "executable": "qmlformat",
                "description": "Installs the official Qt QML code formatter (PySide6/qmlformat) for clean formatting.",
                "command": f'"{sys.executable}" -m pip install --no-warn-script-location PySide6',
                "source": "recipe",
                "verification": "qmlformat"
            },
            "autopep8": {
                "toolName": "Python Formatter (autopep8 / black)",
                "toolType": "formatter",
                "executable": "autopep8",
                "description": "Installs PEP 8 Python formatters (autopep8 & black) via pip.",
                "command": f'"{sys.executable}" -m pip install --no-warn-script-location autopep8 black',
                "source": "recipe",
                "verification": "autopep8"
            },
            "clang-format": {
                "toolName": "C/C++ Formatter (clang-format)",
                "toolType": "formatter",
                "executable": "clang-format",
                "description": "Installs official standalone LLVM clang-format binary (~3.5MB wheel) via pip.",
                "command": f'"{sys.executable}" -m pip install --no-warn-script-location clang-format',
                "source": "recipe",
                "verification": "clang-format"
            },
            "prettier": {
                "toolName": "Prettier Formatter (JS/TS/HTML/CSS)",
                "toolType": "formatter",
                "executable": "prettier",
                "description": "Installs global Prettier code formatter via Node.js npm.",
                "command": "npm install -g prettier",
                "source": "recipe",
                "verification": "prettier"
            },
            "rustfmt": {
                "toolName": "Rust Formatter (rustfmt)",
                "toolType": "formatter",
                "executable": "rustfmt",
                "description": "Adds the official rustfmt formatting component via rustup.",
                "command": "rustup component add rustfmt",
                "source": "recipe",
                "verification": "rustfmt"
            },
            "gofmt": {
                "toolName": "Go Formatter & Toolchain (gofmt)",
                "toolType": "formatter",
                "executable": "gofmt",
                "description": "Installs the official Go language distribution via winget.",
                "command": "winget install --id GoLang.Go -e --accept-source-agreements --accept-package-agreements" if cur_os == "windows" else "brew install go",
                "source": "recipe",
                "verification": "gofmt"
            }
        }

        # Match known recipe
        key = None
        for k in known_recipes:
            if k in exec_to_check.lower() or k in tool_lower:
                key = k
                break

        if key:
            prop = known_recipes[key]
            return {
                "isInstalled": False,
                "toolName": prop["toolName"],
                "toolType": tool_type or prop["toolType"],
                "executable": prop["executable"],
                "description": prop["description"],
                "command": prop["command"],
                "source": prop["source"],
                "needsConfirmation": True,
                "currentOs": cur_os,
                "retryAction": "format" if tool_type == "formatter" else "run",
                "filePath": file_path,
                "languageId": clean_lang
            }

        # 2. Check Extension Tool Dependencies
        if tool_name in self._contributed_tool_dependencies:
            dep = self._contributed_tool_dependencies[tool_name]
            guide = dep.get("installGuide", {})
            inst_cmd = guide.get(cur_os, "") or guide.get("all", "")
            if inst_cmd:
                return {
                    "isInstalled": False,
                    "toolName": dep.get("name", tool_name),
                    "toolType": tool_type or "tool",
                    "executable": dep.get("executable", tool_name),
                    "description": f"Installs {tool_name} tool dependency contributed by extension.",
                    "command": inst_cmd,
                    "source": "extension",
                    "needsConfirmation": True,
                    "currentOs": cur_os,
                    "retryAction": "format" if tool_type == "formatter" else "run",
                    "filePath": file_path,
                    "languageId": clean_lang
                }

        # 3. Fallback AI / Smart suggestion
        fallback_cmd = ""
        if cur_os == "windows":
            fallback_cmd = f"pip install {tool_name}" if "pip" in tool_lower or "py" in clean_lang else f"winget install {tool_name}"
        else:
            fallback_cmd = f"pip install {tool_name}" if "pip" in tool_lower else f"brew install {tool_name}"

        return {
            "isInstalled": False,
            "toolName": tool_name or f"{clean_lang or clean_ext} tool",
            "toolType": tool_type or "tool",
            "executable": exec_to_check,
            "description": f"Proposed installation command for {tool_name or clean_lang} on {cur_os.capitalize()}.",
            "command": fallback_cmd,
            "source": "ai",
            "needsConfirmation": True,
            "currentOs": cur_os,
            "retryAction": "format" if tool_type == "formatter" else "run",
            "filePath": file_path,
            "languageId": clean_lang
        }

    @Slot(str, str, str, str, str, result=bool)
    def execute_smart_install_command(self, tool_name: str, command: str, executable: str, retry_action: str = "", file_path: str = "") -> bool:
        """
        Executes an approved Smart Install command in the background,
        captures output, verifies the resulting executable, updates tool paths, and notifies completion.
        """
        if not command:
            return False

        if tool_name in self._installing_tools:
            return False

        self._installing_tools.add(tool_name)
        self.smartInstallProgress.emit(tool_name, "installing", f"Running: {command}")

        def _worker():
            try:
                is_win = sys.platform.startswith("win")
                use_shell = True
                proc = subprocess.run(command, shell=use_shell, capture_output=True, text=True, timeout=300)
                stdout = proc.stdout.strip()
                stderr = proc.stderr.strip()

                if proc.returncode == 0:
                    self.smartInstallProgress.emit(tool_name, "installing", "Verifying installed executable...")
                    time.sleep(0.5)

                    verified_path = locate_executable(executable) or locate_executable(tool_name)
                    if verified_path:
                        self.smartInstallCompleted.emit(
                            tool_name, True,
                            f"{tool_name} installed successfully! ({verified_path})",
                            retry_action
                        )
                        self.reload_extensions()
                    else:
                        # Success exit code but check if command was pip
                        self.smartInstallCompleted.emit(
                            tool_name, True,
                            f"Installation completed (exit code 0): {stdout or stderr or 'Success'}",
                            retry_action
                        )
                        self.reload_extensions()
                else:
                    err_msg = stderr or stdout or f"Process returned exit code {proc.returncode}"
                    self.smartInstallCompleted.emit(tool_name, False, f"Installation failed: {err_msg}", retry_action)

            except Exception as e:
                self.smartInstallCompleted.emit(tool_name, False, f"Execution error: {e}", retry_action)
            finally:
                self._installing_tools.discard(tool_name)

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(str)
    def install_formatter(self, extension_id: str):
        """Lightweight non-blocking background installer for formatters."""
        ext = self.get_extension(extension_id)
        if not ext:
            return
        status = ext.check_formatter_status()
        cmd = status.get("installCommand", "")
        exec_name = status.get("executable", extension_id)
        if cmd:
            self.execute_smart_install_command(ext.name, cmd, exec_name, "format")
        else:
            self.formatterInstallProgress.emit(extension_id, "failed", f"No install command found for {ext.name}")

    @Slot(str, str, result=bool)
    def set_custom_formatter_path(self, extension_id: str, custom_path: str) -> bool:
        if not custom_path:
            return False
        clean = custom_path
        if clean.startswith("file:///"):
            clean = clean[8:]
            if sys.platform.startswith("win") and clean.startswith("/"):
                clean = clean[1:]
        clean = os.path.abspath(os.path.normpath(clean))
        if not os.path.isfile(clean):
            return False

        self._custom_paths[extension_id] = clean
        self._save_custom_paths()
        self.reload_extensions()
        self.extensionsChanged.emit()
        return True

    @Slot(str, result=str)
    def get_custom_formatter_path(self, extension_id: str) -> str:
        return self._custom_paths.get(extension_id, "")

    def locate_executable(self, cmd: str, custom_path: Optional[str] = None) -> Optional[str]:
        return locate_executable(cmd, custom_path)

    @Slot(str)
    def copy_to_clipboard(self, text: str):
        try:
            cb = QGuiApplication.clipboard()
            if cb:
                cb.setText(text)
        except Exception as e:
            print(f"[ExtensionManager] Clipboard error: {e}")

    @Slot(result="QVariantMap")
    def check_for_updates(self) -> dict:
        result = {
            "app": {
                "name": "DGX Studio",
                "currentVersion": "1.0.0",
                "hasUpdate": False,
                "latestVersion": "1.0.0",
                "status": "You are on the latest version."
            },
            "extensions": [],
            "checkedAt": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        for ext in self._extensions.values():
            result["extensions"].append({
                "id": ext.id,
                "name": ext.name,
                "currentVersion": ext.version,
                "hasUpdate": False,
                "latestVersion": ext.version
            })
        self.updateCheckCompleted.emit(result)
        return result
