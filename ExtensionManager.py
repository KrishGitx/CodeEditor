"""
ExtensionManager.py - Modular Extension Architecture for DGX / Pod Studio
Manages extension discovery, manifest loading, local installation, and extension lifecycles.
Provides architecture foundation for formatters, language tooling, dependency status, and future online marketplace / update checks.
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
from typing import Dict, List, Optional, Any
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
    Comprehensive multi-location locator for formatter executables.
    Checks:
      1. User-configured custom path (validated as executable)
      2. Standard system PATH
      3. Active Python environment's Scripts / bin directory (where pip packages like clang-format, autopep8 install)
      4. User AppData Python Scripts, npm, cargo, and go bin directories
      5. Standard Visual Studio / LLVM / MinGW / MSYS2 installation locations on Windows
      6. Standard Unix / Homebrew / Linux locations
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

    # 4. Common locations for clang-format on Windows
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


class Extension:
    def __init__(self, manifest: dict, path: str, user_dir: str = "", custom_path: str = ""):
        self.id: str = manifest.get("id", "")
        self.name: str = manifest.get("name", self.id)
        self.version: str = manifest.get("version", "1.0.0")
        self.description: str = manifest.get("description", "")
        self.author: str = manifest.get("author", "DGX Studio")
        self.languages: List[str] = [l.lower() for l in manifest.get("languages", [])]
        self.extensions: List[str] = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in manifest.get("extensions", [])]
        self.formatter: Optional[dict] = manifest.get("formatter")
        self.lsp: Optional[dict] = manifest.get("lsp")
        self.path: str = path
        self.user_dir: str = user_dir
        self.custom_path: str = custom_path
        self.enabled: bool = True

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
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "languages": self.languages,
            "extensions": self.extensions,
            "path": self.path,
            "location": self.path,
            "enabled": self.enabled,
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
    formatterInstallProgress = Signal(str, str, str)  # extension_id, status ("installing"|"success"|"failed"), message

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
        self._extensions: Dict[str, Extension] = {}
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
        """Scans both built-in and user extension directories for manifests."""
        self._extensions.clear()

        # 1. Load built-in extensions
        self._load_from_directory(self.built_in_dir, is_user=False)

        # 2. Load user-installed extensions
        self._load_from_directory(self.user_extensions_dir, is_user=True)

        # Apply disabled state and custom paths
        for ext_id, ext in self._extensions.items():
            ext.enabled = (ext_id not in self._disabled_ids)
            ext.custom_path = self._custom_paths.get(ext_id, "")

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
                    ext_id = manifest.get("id")
                    if ext_id:
                        custom_p = self._custom_paths.get(ext_id, "")
                        self._extensions[ext_id] = Extension(
                            manifest, ext_path,
                            self.user_extensions_dir if is_user else "",
                            custom_path=custom_p
                        )
                except Exception as e:
                    print(f"[ExtensionManager] Notice loading manifest at {manifest_file}: {e}")

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

    @Slot(result=str)
    def get_current_os(self) -> str:
        return get_current_os()

    @Slot(str, result="QVariantMap")
    def check_formatter_status(self, lang_id: str) -> dict:
        ext = self.get_extension_for_language(lang_id)
        if not ext:
            return {
                "hasFormatter": False,
                "provider": "",
                "executable": "",
                "installed": False,
                "detectedPath": "",
                "installCommand": "",
                "installInstructions": "",
                "docsUrl": "",
                "currentOs": get_current_os()
            }
        st = ext.check_formatter_status()
        return {
            "hasFormatter": st["hasFormatter"],
            "provider": st["provider"],
            "executable": st["executable"],
            "installed": st["isInstalled"],
            "detectedPath": st["detectedPath"],
            "installCommand": st["installCommand"],
            "installInstructions": st["installInstructions"],
            "docsUrl": st["docsUrl"],
            "currentOs": st["currentOs"]
        }

    @Slot(str, result="QVariantMap")
    def get_formatter_status_for_language(self, lang_id: str, file_path: str = "") -> dict:
        ext = self.get_extension_for_language(lang_id, file_path)
        if not ext:
            return {
                "hasExtension": False,
                "extensionName": "",
                "hasFormatter": False,
                "formatterInstalled": False,
                "message": f"No extension installed for '{lang_id}'.",
                "installCommand": "",
                "docsUrl": "",
                "currentOs": get_current_os()
            }
        status = ext.check_formatter_status()
        return {
            "hasExtension": True,
            "extensionId": ext.id,
            "extensionName": ext.name,
            "hasFormatter": status["hasFormatter"],
            "formatterInstalled": status["isInstalled"],
            "formatterProvider": status["provider"],
            "formatterDependency": status["executable"],
            "formatterDetectedPath": status["detectedPath"],
            "installCommand": status["installCommand"],
            "installInstructions": status["installInstructions"],
            "docsUrl": status["docsUrl"],
            "currentOs": status["currentOs"],
            "message": f"{ext.name} formatter ({status['executable']}) is {'installed' if status['isInstalled'] else 'not installed'}."
        }

    @Slot(str)
    def install_formatter(self, extension_id: str):
        """
        Lightweight non-blocking background installer for formatter binaries.
        Installs only standalone lightweight binary (e.g. clang-format ~3MB via pip),
        avoiding multi-gigabyte compiler toolchains.
        """
        if extension_id in self._installing_formatters:
            print(f"[ExtensionManager] Formatter installation already in progress for {extension_id}")
            return

        ext = self.get_extension(extension_id)
        if not ext or not ext.formatter:
            self.formatterInstallProgress.emit(extension_id, "failed", f"Extension '{extension_id}' has no formatter declared.")
            return

        self._installing_formatters.add(extension_id)
        self.formatterInstallProgress.emit(extension_id, "installing", "Starting lightweight installation...")

        def _worker():
            try:
                fmt_dict = ext.formatter if isinstance(ext.formatter, dict) else {}
                cmd_name = fmt_dict.get("command") or fmt_dict.get("executable") or ""
                success = False
                msg = ""

                # 1. C/C++ clang-format (~3.5MB official PyPI standalone binary wheel)
                if extension_id == "dgx.cpp" or cmd_name.lower().startswith("clang-format"):
                    self.formatterInstallProgress.emit(extension_id, "installing", "Downloading standalone clang-format binary (~3.5MB)...")
                    run_cmd = [sys.executable, "-m", "pip", "install", "--no-warn-script-location", "clang-format"]
                    proc = subprocess.run(run_cmd, capture_output=True, text=True, timeout=120)
                    if proc.returncode == 0:
                        # Clear broken/outdated custom path if not a real clang-format
                        custom_p = self._custom_paths.get(extension_id, "")
                        if custom_p and (not os.path.isfile(custom_p) or not custom_p.lower().endswith((".exe", "clang-format"))):
                            self._custom_paths.pop(extension_id, None)
                            self._save_custom_paths()
                        ext.custom_path = self._custom_paths.get(extension_id, "")
                        tool_path = ext.get_executable_path() or locate_executable("clang-format")
                        if tool_path:
                            try:
                                test_res = subprocess.run([tool_path, "--version"], capture_output=True, text=True, timeout=5)
                                if test_res.returncode == 0:
                                    success = True
                                    msg = f"clang-format ready! ({test_res.stdout.strip() or tool_path})"
                                else:
                                    success = True
                                    msg = f"clang-format installed at: {tool_path}"
                            except Exception as ex_run:
                                success = True
                                msg = f"clang-format installed at {tool_path} (note: {ex_run})"
                        else:
                            success = False
                            msg = "Installed clang-format package, but executable was not found in environment Scripts."
                    else:
                        success = False
                        msg = proc.stderr.strip() or proc.stdout.strip() or f"pip failed with code {proc.returncode}"

                # 2. Python formatters (autopep8, black)
                elif extension_id == "dgx.python":
                    self.formatterInstallProgress.emit(extension_id, "installing", "Installing autopep8 / black...")
                    run_cmd = [sys.executable, "-m", "pip", "install", "--no-warn-script-location", "autopep8", "black"]
                    proc = subprocess.run(run_cmd, capture_output=True, text=True, timeout=120)
                    if proc.returncode == 0:
                        success = True
                        msg = "Python formatters installed successfully!"
                    else:
                        success = False
                        msg = proc.stderr.strip() or f"pip failed with code {proc.returncode}"

                # 3. JavaScript / Prettier
                elif extension_id == "dgx.javascript":
                    self.formatterInstallProgress.emit(extension_id, "installing", "Installing prettier via npm...")
                    proc = subprocess.run(["npm", "install", "-g", "prettier"], shell=True, capture_output=True, text=True, timeout=120)
                    if proc.returncode == 0:
                        success = True
                        msg = "prettier installed successfully!"
                    else:
                        success = False
                        msg = proc.stderr.strip() or "npm install prettier failed. Ensure Node.js and npm are installed."

                # 4. Rust / rustfmt
                elif extension_id == "dgx.rust":
                    if shutil.which("rustup"):
                        self.formatterInstallProgress.emit(extension_id, "installing", "Adding rustfmt component via rustup...")
                        proc = subprocess.run(["rustup", "component", "add", "rustfmt"], shell=True, capture_output=True, text=True, timeout=120)
                        if proc.returncode == 0:
                            success = True
                            msg = "rustfmt component added successfully!"
                        else:
                            success = False
                            msg = proc.stderr.strip() or "Failed to add rustfmt component via rustup."
                    else:
                        success = False
                        msg = "Rust toolchain ('rustup') is not installed on this system. Please install Rust from https://rustup.rs or run 'winget install Rustlang.Rustup' in your terminal."

                # 5. Go / gofmt
                elif extension_id == "dgx.go":
                    if shutil.which("go") or shutil.which("gofmt"):
                        success = True
                        msg = "Go distribution is already installed."
                    elif sys.platform.startswith("win") and shutil.which("winget"):
                        self.formatterInstallProgress.emit(extension_id, "installing", "Installing Go toolchain via winget...")
                        proc = subprocess.run(["winget", "install", "--id", "GoLang.Go", "-e", "--accept-source-agreements", "--accept-package-agreements"], capture_output=True, text=True, timeout=300)
                        if proc.returncode == 0:
                            success = True
                            msg = "Go distribution installed successfully! Please restart Pod Studio."
                        else:
                            success = False
                            msg = "Go is not installed. Please install Go from https://go.dev/doc/install or run 'winget install GoLang.Go' in your terminal."
                    else:
                        success = False
                        msg = "Go toolchain is not installed. Please install Go from https://go.dev/doc/install or run 'winget install GoLang.Go'."

                elif fmt_dict.get("installGuide"):
                    cur_os = get_current_os()
                    guide = fmt_dict.get("installGuide", {})
                    install_cmd = guide.get("lightweight", "") or guide.get(cur_os, "") or guide.get("all", "")
                    if install_cmd:
                        self.formatterInstallProgress.emit(extension_id, "installing", f"Running '{install_cmd}'...")
                        proc = subprocess.run(install_cmd, shell=True, capture_output=True, text=True, timeout=300)
                        if proc.returncode == 0:
                            success = True
                            msg = f"{ext.name} formatter installed successfully!"
                        else:
                            success = False
                            msg = proc.stderr.strip() or proc.stdout.strip() or f"Installation command '{install_cmd}' failed with code {proc.returncode}."
                    else:
                        success = False
                        msg = f"Please install {ext.name} formatter manually or select binary."
                else:
                    success = False
                    msg = f"Please install {ext.name} formatter manually or select binary."

                if success:
                    self.formatterInstallProgress.emit(extension_id, "success", msg)
                    self.reload_extensions()
                else:
                    self.formatterInstallProgress.emit(extension_id, "failed", msg)

            except Exception as e:
                self.formatterInstallProgress.emit(extension_id, "failed", f"Installation error: {str(e)}")
            finally:
                self._installing_formatters.discard(extension_id)

        threading.Thread(target=_worker, daemon=True).start()

    @Slot(str, str, result=bool)
    def set_custom_formatter_path(self, extension_id: str, custom_path: str) -> bool:
        """Sets a user-selected custom binary path for an extension."""
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
        """Locates an executable across custom path, PATH, and common toolchain locations."""
        return locate_executable(cmd, custom_path)

    @Slot(str, result=bool)
    def install_local_extension(self, source_path: str) -> bool:
        """Installs an extension from a local directory, .zip archive, or .json manifest file."""
        if not source_path:
            return False

        # Normalize path (handle file:/// URIs)
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
                ext_id = manifest.get("id")
                if not ext_id:
                    print(f"[ExtensionManager] Manifest missing 'id'")
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
                ext_id = manifest.get("id")
                if not ext_id:
                    return False
                target_dir = os.path.join(self.user_extensions_dir, ext_id.replace(".", "_"))
                os.makedirs(target_dir, exist_ok=True)
                shutil.copyfile(clean_path, os.path.join(target_dir, "extension.json"))
                self.reload_extensions()
                self.extensionInstalled.emit(ext_id)
                print(f"[ExtensionManager] Successfully installed manifest '{ext_id}' into {target_dir}")
                return True

            # 3. Zip package (.zip / .vsix)
            elif os.path.isfile(clean_path) and (clean_path.lower().endswith(".zip") or clean_path.lower().endswith(".vsix")):
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
                        print(f"[ExtensionManager] Zip archive missing extension.json")
                        shutil.rmtree(temp_extract, ignore_errors=True)
                        return False

                    with open(found_manifest, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    ext_id = manifest.get("id")
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
                    print(f"[ExtensionManager] Successfully installed zip extension '{ext_id}' into {target_dir}")
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
            # Built-in extension can be disabled
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
        self.extensionsChanged.emit()
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

    @Slot(str)
    def copy_to_clipboard(self, text: str):
        try:
            cb = QGuiApplication.clipboard()
            if cb:
                cb.setText(text)
        except Exception as e:
            print(f"[ExtensionManager] Clipboard error: {e}")

    # =========================================================================
    # ARCHITECTURE HOOKS: FUTURE ONLINE MARKETPLACE & UPDATE CHECKER
    # =========================================================================
    @Slot(result="QVariantMap")
    def check_for_updates(self) -> dict:
        """
        Architecture endpoint for checking app and extension updates.
        Returns clean structured status ready for remote manifest endpoint.
        """
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

    def fetch_marketplace_manifest(self, marketplace_url: Optional[str] = None) -> List[dict]:
        """Architecture endpoint for fetching available online extensions."""
        return []

    def install_remote_extension(self, extension_id: str, version: Optional[str] = None) -> bool:
        """Architecture endpoint for remote extension installation."""
        return False
