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
import re
import platform
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


def resolve_python_tool(package_name: str, executable_name: Optional[str] = None, python_executable: Optional[str] = None) -> Dict[str, Any]:
    """
    Identifies the active Python interpreter and its environment,
    checks whether package_name is installed in THAT environment,
    and resolves the console-script executable from that environment.
    Caches nothing that can become stale after installation.
    """
    py_exec = python_executable or sys.executable
    if not py_exec or not os.path.exists(py_exec):
        py_exec = sys.executable

    exec_name = executable_name or package_name
    is_win = sys.platform.startswith("win")
    bin_name = f"{exec_name}.exe" if is_win else exec_name

    py_dir = os.path.dirname(os.path.abspath(py_exec))
    env_root = os.path.dirname(py_dir) if os.path.basename(py_dir).lower() in ("scripts", "bin") else py_dir

    candidate_dirs = [
        # 1. Scripts/bin in same dir as python
        py_dir,
        os.path.join(py_dir, "Scripts"),
        os.path.join(py_dir, "bin"),
        # 2. Virtualenv / prefix root
        os.path.join(env_root, "Scripts"),
        os.path.join(env_root, "bin"),
        os.path.join(sys.prefix, "Scripts"),
        os.path.join(sys.prefix, "bin"),
        os.path.join(sys.base_prefix, "Scripts"),
        os.path.join(sys.base_prefix, "bin"),
    ]

    if is_win:
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidate_dirs.append(os.path.join(local_app_data, "Programs", "Python", "*", "Scripts"))
            candidate_dirs.append(os.path.join(local_app_data, "Python", "*", "Scripts"))
            candidate_dirs.append(os.path.join(local_app_data, "Programs", "Python", "*"))
        app_data = os.environ.get("APPDATA", "")
        if app_data:
            candidate_dirs.append(os.path.join(app_data, "Python", "*", "Scripts"))

    resolved_path = ""
    for c_dir in candidate_dirs:
        if "*" in c_dir:
            for g_dir in glob.glob(c_dir):
                p = os.path.join(g_dir, bin_name)
                if os.path.isfile(p):
                    resolved_path = os.path.abspath(p)
                    break
        else:
            p = os.path.join(c_dir, bin_name)
            if os.path.isfile(p):
                resolved_path = os.path.abspath(p)
                break
        if resolved_path:
            break

    # If not found directly in candidate dirs, check system PATH
    if not resolved_path:
        w = shutil.which(exec_name)
        if w and os.path.isfile(w):
            resolved_path = os.path.abspath(w)

    # Check whether package is installed in active Python environment
    package_installed = False
    clean_pkg_id = package_name.lower().replace("-", "_")
    try:
        import importlib.util
        if importlib.util.find_spec(clean_pkg_id) is not None:
            package_installed = True
        else:
            check_proc = subprocess.run(
                [py_exec, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            if check_proc.returncode == 0:
                package_installed = True
    except Exception:
        pass

    return {
        "package": package_name,
        "python": py_exec,
        "package_installed": package_installed,
        "executable": resolved_path,
        "console_script_exists": bool(resolved_path and os.path.isfile(resolved_path))
    }


def resolve_dotnet_global_tool(package_name: str, executable_name: Optional[str] = None, dotnet_executable: Optional[str] = None) -> Dict[str, Any]:
    """
    Generic environment-aware resolver for .NET global tools.
    1. Checks if dotnet CLI exists.
    2. Identifies .NET global tool directory (%USERPROFILE%\\.dotnet\\tools on Windows, ~/.dotnet/tools on Unix).
    3. Resolves the executable path (e.g. csharpier.exe, dotnet-csharpier.exe, dotnet-ef.exe).
    4. Queries `dotnet tool list --global` to check if package is installed.
    5. Returns structured information including resolved absolute executable path.
    """
    dotnet_bin = dotnet_executable or locate_executable("dotnet") or shutil.which("dotnet")
    is_win = sys.platform.startswith("win")

    # Determine .NET global tools directory
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    dotnet_tools_dir = os.environ.get("DOTNET_TOOLS_PATH") or os.path.join(user_home, ".dotnet", "tools")

    # Ensure dotnet tools dir is added to current process PATH
    if os.path.isdir(dotnet_tools_dir) and dotnet_tools_dir.lower() not in os.environ.get("PATH", "").lower():
        os.environ["PATH"] = dotnet_tools_dir + os.pathsep + os.environ.get("PATH", "")

    clean_pkg = (package_name or "").strip()
    exec_candidates = []
    if executable_name:
        exec_candidates.append(executable_name)
    if clean_pkg:
        exec_candidates.append(clean_pkg)
        if not clean_pkg.startswith("dotnet-"):
            exec_candidates.append(f"dotnet-{clean_pkg}")
        else:
            exec_candidates.append(clean_pkg[7:])

    resolved_path = ""
    for candidate in exec_candidates:
        bin_name = f"{candidate}.exe" if is_win else candidate
        p = os.path.join(dotnet_tools_dir, bin_name)
        if os.path.isfile(p):
            resolved_path = os.path.abspath(p)
            break
        w = shutil.which(candidate)
        if w and os.path.isfile(w):
            resolved_path = os.path.abspath(w)
            break

    # Query dotnet global tool list
    global_tool_installed = False
    if dotnet_bin:
        try:
            proc = subprocess.run(
                [dotnet_bin, "tool", "list", "--global"],
                capture_output=True,
                text=True,
                timeout=8
            )
            if proc.returncode == 0:
                output_lower = proc.stdout.lower()
                clean_pkg_lower = clean_pkg.lower()
                for line in output_lower.splitlines():
                    parts = line.split()
                    if parts and parts[0] == clean_pkg_lower:
                        global_tool_installed = True
                        break
        except Exception:
            pass

    if resolved_path and os.path.isfile(resolved_path):
        global_tool_installed = True

    return {
        "package": clean_pkg,
        "dotnet": dotnet_bin or "",
        "global_tool_installed": global_tool_installed,
        "package_installed": global_tool_installed,
        "executable": resolved_path,
        "executable_exists": bool(resolved_path and os.path.isfile(resolved_path)),
        "tools_directory": dotnet_tools_dir
    }


def locate_executable(cmd: str, custom_path: Optional[str] = None) -> Optional[str]:
    """
    Comprehensive multi-location locator for executables across:
      1. User-configured custom path
      2. System PATH
      3. Active Python environment's Scripts / bin directory (where pip packages like clang-format, autopep8 install)
      4. AppData / Homebrew / npm / cargo / go / .dotnet tool directories
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

    # 3. Environment-specific tool directories
    candidates = []
    py_dir = os.path.dirname(sys.executable)
    user_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))

    candidates.append(os.path.join(py_dir, "Scripts", bin_name))
    candidates.append(os.path.join(py_dir, "bin", bin_name))
    candidates.append(os.path.join(sys.prefix, "Scripts", bin_name))
    candidates.append(os.path.join(sys.prefix, "bin", bin_name))
    candidates.append(os.path.join(user_home, ".dotnet", "tools", bin_name))
    candidates.append(os.path.join(os.path.expanduser("~"), ".dotnet", "tools", bin_name))
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

    # 4. Common locations on Windows
    if is_win:
        cmd_l = cmd.lower()
        if cmd_l.startswith("clang-format"):
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
        elif cmd_l in ("g++", "gcc", "clang", "clang++"):
            cpp_globs = [
                os.path.join(r"C:\msys64\mingw64\bin", bin_name),
                os.path.join(r"C:\msys64\ucrt64\bin", bin_name),
                os.path.join(r"C:\msys64\clang64\bin", bin_name),
                os.path.join(r"C:\MinGW\bin", bin_name),
                os.path.join(r"C:\TDM-GCC-64\bin", bin_name),
                os.path.join(r"C:\Program Files\LLVM\bin", bin_name)
            ]
            for pattern in cpp_globs:
                for match in glob.glob(pattern):
                    if os.path.isfile(match):
                        return os.path.abspath(match)
        elif cmd_l in ("java", "javac", "javaw"):
            java_home = os.environ.get("JAVA_HOME", "")
            if java_home:
                jp = os.path.join(java_home, "bin", bin_name)
                if os.path.isfile(jp):
                    return os.path.abspath(jp)
            java_globs = [
                os.path.join(r"C:\Program Files\Java", "*", "bin", bin_name),
                os.path.join(r"C:\Program Files (x86)\Java", "*", "bin", bin_name),
                os.path.join(r"C:\Program Files\Eclipse Adoptium", "*", "bin", bin_name),
                os.path.join(r"C:\Program Files\Microsoft", "jdk-*", "bin", bin_name),
                os.path.join(r"C:\Program Files\Amazon Corretto", "*", "bin", bin_name),
                os.path.join(r"C:\Program Files\BellSoft", "*", "bin", bin_name),
                os.path.join(r"C:\Program Files\Zulu", "*", "bin", bin_name)
            ]
            for pattern in java_globs:
                for match in glob.glob(pattern):
                    if os.path.isfile(match):
                        return os.path.abspath(match)
        elif cmd_l in ("node", "npm", "npx"):
            node_paths = [
                os.path.join(r"C:\Program Files\nodejs", bin_name),
                os.path.join(r"C:\Program Files (x86)\nodejs", bin_name)
            ]
            for np in node_paths:
                if os.path.isfile(np):
                    return os.path.abspath(np)
        elif cmd_l in ("go", "gofmt"):
            goroot = os.environ.get("GOROOT", "")
            if goroot:
                gp = os.path.join(goroot, "bin", bin_name)
                if os.path.isfile(gp):
                    return os.path.abspath(gp)
            go_paths = [os.path.join(r"C:\Program Files\Go\bin", bin_name)]
            for gp in go_paths:
                if os.path.isfile(gp):
                    return os.path.abspath(gp)
        elif cmd_l in ("dotnet", "csharpier"):
            dotnet_paths = [
                os.path.join(r"C:\Program Files\dotnet", bin_name),
                os.path.join(r"C:\Program Files (x86)\dotnet", bin_name)
            ]
            for dp in dotnet_paths:
                if os.path.isfile(dp):
                    return os.path.abspath(dp)

    # 5. Common locations for Unix / macOS
    if not is_win:
        unix_paths = [
            f"/opt/homebrew/bin/{cmd}",
            f"/usr/local/bin/{cmd}",
            f"/usr/bin/{cmd}",
            f"/bin/{cmd}",
            os.path.expanduser(f"~/.local/bin/{cmd}"),
            os.path.expanduser(f"~/.cargo/bin/{cmd}"),
            os.path.expanduser(f"~/go/bin/{cmd}")
        ]
        for p in unix_paths:
            if os.path.isfile(p):
                return os.path.abspath(p)

    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)

    return None


# ==============================================================================
# RUNTIME COMPATIBILITY & ENVIRONMENT DISCOVERY (Java, Python, Node, etc.)
# ==============================================================================

_test_discovered_jdks: List[Dict[str, Any]] = []
_test_active_java_info: Optional[Dict[str, Any]] = None


def set_test_java_environment(active_info: Optional[Dict[str, Any]] = None, discovered_jdks: Optional[List[Dict[str, Any]]] = None):
    """Allows regression and unit tests to inject deterministic runtime environments."""
    global _test_active_java_info, _test_discovered_jdks
    _test_active_java_info = active_info
    _test_discovered_jdks = list(discovered_jdks) if discovered_jdks is not None else []


def get_active_java_info() -> Dict[str, Any]:
    """
    Inspects the active Java runtime environment, executable path, and version.
    """
    global _test_active_java_info
    if _test_active_java_info is not None:
        return dict(_test_active_java_info)

    java_exe = shutil.which("java")
    version_str = ""
    major_ver = 0
    full_output = ""

    # Common Windows Oracle javapath fallback if not resolved
    if not java_exe and sys.platform.startswith("win"):
        oracle_path = r"C:\Program Files\Common Files\Oracle\Java\javapath\java.exe"
        if os.path.isfile(oracle_path):
            java_exe = oracle_path

    if java_exe:
        try:
            res = subprocess.run([java_exe, "-version"], capture_output=True, text=True, timeout=5)
            full_output = (res.stderr or res.stdout or "").strip()
            # e.g. 'java version "17.0.12"' or 'openjdk version "21.0.2"'
            m = re.search(r'version\s+"([0-9]+(?:\.[0-9]+)*)', full_output, re.IGNORECASE)
            if m:
                version_str = m.group(1)
                parts = version_str.split(".")
                major_ver = int(parts[0]) if parts else 0
        except Exception:
            pass

    java_home = os.environ.get("JAVA_HOME", "")

    return {
        "executable": java_exe or "",
        "version": version_str,
        "major_version": major_ver,
        "java_home": java_home,
        "output": full_output
    }


def discover_installed_jdks() -> List[Dict[str, Any]]:
    """
    Scans filesystem for installed JDKs and resolves their actual directories,
    java executables, and major versions.
    """
    global _test_discovered_jdks
    discovered = list(_test_discovered_jdks)
    seen_dirs = {os.path.normpath(d.get("path", "")) for d in discovered if d.get("path")}

    search_dirs = []
    if sys.platform.startswith("win"):
        base_locations = [
            r"C:\Program Files\Microsoft",
            r"C:\Program Files\Java",
            r"C:\Program Files\Eclipse Adoptium",
            r"C:\Program Files\Amazon Corretto",
            r"C:\Program Files\Zulu",
            r"C:\Program Files\BellSoft",
            r"C:\Program Files\Semeru",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
        ]
        for base in base_locations:
            if os.path.isdir(base):
                try:
                    for entry in os.listdir(base):
                        full = os.path.join(base, entry)
                        if os.path.isdir(full):
                            search_dirs.append(full)
                except Exception:
                    pass
    elif sys.platform.startswith("darwin"):
        mac_base = "/Library/Java/JavaVirtualMachines"
        if os.path.isdir(mac_base):
            try:
                for entry in os.listdir(mac_base):
                    home = os.path.join(mac_base, entry, "Contents", "Home")
                    if os.path.isdir(home):
                        search_dirs.append(home)
            except Exception:
                pass
    else:
        linux_base = "/usr/lib/jvm"
        if os.path.isdir(linux_base):
            try:
                for entry in os.listdir(linux_base):
                    full = os.path.join(linux_base, entry)
                    if os.path.isdir(full):
                        search_dirs.append(full)
            except Exception:
                pass

    exe_name = "java.exe" if sys.platform.startswith("win") else "java"

    for d in search_dirs:
        norm = os.path.normpath(d)
        if norm in seen_dirs:
            continue
        seen_dirs.add(norm)

        bin_java = os.path.join(d, "bin", exe_name)
        if not os.path.isfile(bin_java):
            nested_home = os.path.join(d, "Contents", "Home")
            if os.path.isfile(os.path.join(nested_home, "bin", exe_name)):
                d = nested_home
                bin_java = os.path.join(d, "bin", exe_name)
            else:
                continue

        ver_str = ""
        major_ver = 0

        release_file = os.path.join(d, "release")
        if os.path.isfile(release_file):
            try:
                with open(release_file, "r", encoding="utf-8", errors="ignore") as rf:
                    content = rf.read()
                    m = re.search(r'JAVA_VERSION="([0-9]+(?:\.[0-9]+)*)', content)
                    if m:
                        ver_str = m.group(1)
                        major_ver = int(ver_str.split(".")[0])
            except Exception:
                pass

        if not major_ver:
            try:
                res = subprocess.run([bin_java, "-version"], capture_output=True, text=True, timeout=5)
                out = res.stderr or res.stdout or ""
                m = re.search(r'version\s+"([0-9]+(?:\.[0-9]+)*)', out, re.IGNORECASE)
                if m:
                    ver_str = m.group(1)
                    major_ver = int(ver_str.split(".")[0])
            except Exception:
                pass

        if major_ver:
            discovered.append({
                "path": os.path.abspath(d),
                "java_exe": os.path.abspath(bin_java),
                "version": ver_str,
                "major_version": major_ver
            })

    discovered.sort(key=lambda x: x.get("major_version", 0), reverse=True)
    return discovered


def find_compatible_jdk(min_version: int = 21) -> Optional[Dict[str, Any]]:
    jdks = discover_installed_jdks()
    for jdk in jdks:
        if jdk.get("major_version", 0) >= min_version:
            return jdk
    return None


def collect_runtime_environment_info(
    tool_name: str = "",
    language: str = "",
    executable: str = "",
    verified_path: str = "",
    operation_error: str = ""
) -> Dict[str, Any]:
    """
    Collects comprehensive factual environment and runtime context for post-install AI diagnosis.
    """
    import platform

    cur_os = get_current_os()
    arch = platform.machine() or "x64"
    os_detail = platform.platform()
    sh_name = "PowerShell" if cur_os == "windows" else os.environ.get("SHELL", "bash").split("/")[-1]

    info: Dict[str, Any] = {
        "os_name": cur_os,
        "arch": arch,
        "os_detail": os_detail,
        "shell": sh_name,
        "runtime_type": "general",
        "runtime_version": "",
        "runtime_executable": "",
        "runtime_env_vars": {},
        "available_runtimes": [],
        "min_runtime_required": "",
        "incompatibility_detected": False,
        "incompatibility_details": ""
    }

    t_lower = (tool_name or "").lower()
    e_lower = (executable or "").lower()
    err_lower = (operation_error or "").lower()
    l_lower = (language or "").lower()

    # 1. Java-related tools and diagnostics
    is_java = (
        l_lower == "java" or
        "java" in t_lower or
        "java" in e_lower or
        "jcanypattern" in err_lower or
        "classnotfoundexception" in err_lower or
        "javac" in err_lower
    )

    if is_java:
        info["runtime_type"] = "Java"
        java_info = get_active_java_info()
        info["runtime_executable"] = java_info.get("executable") or "Not found in PATH"
        info["runtime_version"] = java_info.get("version") or (java_info.get("output") or "Unknown")
        major = java_info.get("major_version", 0)

        # Relevant env vars
        j_env = {}
        if "JAVA_HOME" in os.environ:
            j_env["JAVA_HOME"] = os.environ["JAVA_HOME"]
        if "_JAVA_OPTIONS" in os.environ:
            j_env["_JAVA_OPTIONS"] = os.environ["_JAVA_OPTIONS"]
        if "JAVA_TOOL_OPTIONS" in os.environ:
            j_env["JAVA_TOOL_OPTIONS"] = os.environ["JAVA_TOOL_OPTIONS"]
        info["runtime_env_vars"] = j_env

        # Discovered JDKs
        jdks = discover_installed_jdks()
        info["available_runtimes"] = [
            f"{jdk.get('path')} (Java {jdk.get('version')})" for jdk in jdks
        ]

        if "google-java-format" in t_lower or "google-java-format" in e_lower or "java" in l_lower:
            info["min_runtime_required"] = "JDK 21 or newer (LTS recommended: JDK 21 or JDK 25)"
            # Check for ClassNotFoundException com.sun.tools.javac.tree.JCTree$JCAnyPattern or Java 17
            if "jcanypattern" in err_lower or (major > 0 and major < 21):
                info["incompatibility_detected"] = True
                info["incompatibility_details"] = (
                    f"Active Java runtime is Java {major} ({info['runtime_executable']}), "
                    f"while {tool_name or 'google-java-format'} requires JDK 21+ compiler internals. "
                    f"Execution under Java {major} throws ClassNotFoundException: com.sun.tools.javac.tree.JCTree$JCAnyPattern."
                )

    # 2. Python-related tools and diagnostics
    elif l_lower in ("python", "py") or "python" in t_lower or "pip" in t_lower:
        info["runtime_type"] = "Python"
        info["runtime_executable"] = sys.executable
        info["runtime_version"] = platform.python_version()
        p_env = {}
        for var in ("VIRTUAL_ENV", "CONDA_PREFIX", "PYTHONPATH"):
            if var in os.environ:
                p_env[var] = os.environ[var]
        info["runtime_env_vars"] = p_env

    # 3. Node-related tools and diagnostics
    elif l_lower in ("javascript", "typescript") or any(k in t_lower for k in ("npm", "node", "prettier", "eslint")):
        info["runtime_type"] = "Node.js"
        node_exe = shutil.which("node")
        info["runtime_executable"] = node_exe or "Not found in PATH"
        if node_exe:
            try:
                res = subprocess.run([node_exe, "--version"], capture_output=True, text=True, timeout=5)
                info["runtime_version"] = (res.stdout or res.stderr or "").strip()
            except Exception:
                pass

    return info


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
        lang_aliases = {
            "py": "python", "pyw": "python",
            "js": "javascript", "mjs": "javascript", "cjs": "javascript", "jsx": "javascriptreact",
            "ts": "typescript", "tsx": "typescriptreact",
            "c++": "cpp", "cxx": "cpp", "cc": "cpp",
            "cs": "csharp",
            "rs": "rust",
            "golang": "go",
            "htm": "html",
            "yml": "yaml"
        }
        clean_lang = lang_aliases.get(clean_lang, clean_lang)
        if clean_lang and clean_lang in self.languages:
            return True
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext and ext in self.extensions:
                return True
        return False

    def supports_language_for_formatting(self, lang_id: str, file_path: str = "") -> bool:
        """
        Strictly verifies whether this extension's formatter provider explicitly supports
        the given language or file extension. Never allows cross-language fallbacks.
        """
        if not self.enabled or not self.formatter:
            return False
        clean_lang = (lang_id or "").lower().strip()
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""

        lang_aliases = {
            "py": "python", "pyw": "python",
            "js": "javascript", "mjs": "javascript", "cjs": "javascript", "jsx": "javascriptreact",
            "ts": "typescript", "tsx": "typescriptreact",
            "c++": "cpp", "cxx": "cpp", "cc": "cpp",
            "cs": "csharp",
            "rs": "rust",
            "golang": "go",
            "htm": "html",
            "yml": "yaml"
        }
        clean_lang = lang_aliases.get(clean_lang, clean_lang)

        fmt_spec = self.formatter if isinstance(self.formatter, dict) else {}
        supported_langs = [l.lower() for l in fmt_spec.get("supportedLanguages", [])]

        if supported_langs:
            if clean_lang and clean_lang in supported_langs:
                return True
            ext_to_lang = {
                ".c": "c", ".h": "c",
                ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".cu": "cuda",
                ".py": "python", ".pyw": "python",
                ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascriptreact",
                ".ts": "typescript", ".tsx": "typescriptreact",
                ".html": "html", ".htm": "html",
                ".css": "css", ".scss": "scss", ".less": "less",
                ".json": "json", ".yaml": "yaml", ".yml": "yaml",
                ".rs": "rust",
                ".go": "go",
                ".qml": "qml",
                ".cs": "csharp",
                ".java": "java",
                ".sql": "sql"
            }
            mapped_lang = ext_to_lang.get(ext, "")
            if mapped_lang and mapped_lang in supported_langs:
                return True
            return False

        # Fallback to extension language definitions ONLY if explicit formatter spec omitted
        if clean_lang and clean_lang in self.languages:
            return True
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
    smartInstallAnalysisStarted = Signal(str)  # tool_name / operation
    smartInstallResolved = Signal("QVariantMap")  # resolved proposal
    smartInstallAnalysisFailed = Signal(str, str)  # tool_name, reason
    smartInstallProgress = Signal(str, str, str)  # tool_name, status ("installing"|"success"|"failed"), message
    smartInstallCompleted = Signal(str, bool, str, str)  # tool_name, success, message, retry_action
    smartInstallPostInstallVerified = Signal(str, str, str, str, str, str)  # tool_name, status ("success"|"fix_available"|"manual_installation_required"|"failed"), message, retry_action, file_path, lang_id
    smartInstallFixProposed = Signal(str, str, str, str, str, str, int)  # tool_name, fix_command, fix_explanation, retry_action, file_path, verify_command, fix_attempt_count
    originalOperationRetried = Signal(str, bool, str)  # tool_name, success, error_message
    extensionMessageEmitted = Signal(str, str, str)  # extension_id, message, level
    commandExecuted = Signal(str, str)  # command_id, result_message

    _custom_ai_resolver: Optional[Callable[[str], str]] = None

    @classmethod
    def set_ai_provider(cls, provider_fn: Optional[Callable[[str], str]]):
        cls._custom_ai_resolver = provider_fn
        try:
            from AIBackend import AIBackend
            AIBackend.set_ai_provider(provider_fn)
        except Exception:
            pass

    def __init__(self, base_dir: Optional[str] = None):
        super().__init__()
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.built_in_dir = os.path.join(self.base_dir, "extensions")
        self.user_extensions_dir = os.path.join(os.path.expanduser("~"), ".dgx", "extensions")
        self.state_file = os.path.join(os.path.expanduser("~"), ".dgx", "disabled_extensions.json")
        self.custom_paths_file = os.path.join(os.path.expanduser("~"), ".dgx", "custom_formatter_paths.json")
        self.tool_runtimes_file = os.path.join(os.path.expanduser("~"), ".dgx", "tool_runtimes.json")

        os.makedirs(self.built_in_dir, exist_ok=True)
        os.makedirs(self.user_extensions_dir, exist_ok=True)

        self._disabled_ids = self._load_disabled_state()
        self._custom_paths = self._load_custom_paths()
        self._tool_runtime_configs = self._load_tool_runtimes()
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

    def _load_tool_runtimes(self) -> dict:
        if hasattr(self, "tool_runtimes_file") and os.path.isfile(self.tool_runtimes_file):
            try:
                with open(self.tool_runtimes_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                print(f"[ExtensionManager] Notice reading {self.tool_runtimes_file}: {e}")
        return {}

    def _save_tool_runtimes(self):
        if not hasattr(self, "tool_runtimes_file"):
            return
        try:
            with open(self.tool_runtimes_file, "w", encoding="utf-8") as f:
                json.dump(self._tool_runtime_configs, f, indent=2)
        except Exception as e:
            print(f"[ExtensionManager] Notice saving {self.tool_runtimes_file}: {e}")

    def get_tool_runtime_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        if not tool_name or not hasattr(self, "_tool_runtime_configs"):
            return None
        return self._tool_runtime_configs.get(tool_name) or self._tool_runtime_configs.get(tool_name.lower())

    def set_tool_runtime_config(self, tool_name: str, config: Dict[str, Any]):
        if not tool_name:
            return
        if not hasattr(self, "_tool_runtime_configs"):
            self._tool_runtime_configs = {}
        self._tool_runtime_configs[tool_name] = config
        self._tool_runtime_configs[tool_name.lower()] = config
        self._save_tool_runtimes()

    def get_java_runtime_config(self) -> Optional[Dict[str, Any]]:
        return self.get_tool_runtime_config("java") or self.get_tool_runtime_config("google-java-format")

    def set_java_runtime_config(self, config: Dict[str, Any]):
        self.set_tool_runtime_config("java", config)
        self.set_tool_runtime_config("google-java-format", config)

    def ensure_tool_runtime_compatibility(self, tool_name: str, language: str = "") -> Tuple[bool, str]:
        """
        Detects whether a tool requires a newer runtime than the active system runtime,
        and if a compatible runtime is available on disk, automatically configures the tool to use it.
        """
        t_lower = (tool_name or "").lower()
        l_lower = (language or "").lower()

        if l_lower == "java" or "google-java-format" in t_lower:
            java_info = get_active_java_info()
            active_major = java_info.get("major_version", 0)
            if active_major > 0 and active_major < 21:
                compat_jdk = find_compatible_jdk(min_version=21)
                if compat_jdk:
                    jdk_path = compat_jdk["path"]
                    jdk_java = compat_jdk["java_exe"]
                    jdk_ver = compat_jdk.get("version", "21+")
                    print(f"[SmartInstall] Runtime mismatch detected: active Java is {active_major}, but {tool_name} requires JDK 21+.")
                    print(f"[SmartInstall] Configuring {tool_name} to use installed compatible JDK at {jdk_path}")
                    self.set_tool_runtime_config(tool_name, {
                        "JAVA_HOME": jdk_path,
                        "java_path": jdk_java,
                        "version": jdk_ver
                    })
                    self.set_java_runtime_config({
                        "JAVA_HOME": jdk_path,
                        "java_path": jdk_java,
                        "version": jdk_ver
                    })
                    return True, f"Configured {tool_name} to use compatible JDK {jdk_ver} at {jdk_path}"
                else:
                    return False, f"Tool {tool_name} requires JDK 21+, but active Java is {active_major} and no compatible JDK was found on disk."

        return True, "Compatible"

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

    def get_extension_for_language(self, lang_id: str, file_path: str = "", for_formatting: bool = False) -> Optional[Extension]:
        for ext in self._extensions.values():
            if for_formatting:
                if ext.supports_language_for_formatting(lang_id, file_path):
                    return ext
            else:
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
    # SMART INSTALL SYSTEM (AI-POWERED ISSUE RESOLUTION ENGINE)
    # =========================================================================
    _custom_ai_resolver = None

    @classmethod
    def set_ai_provider(cls, provider_func):
        """Allows injecting custom or mock AI resolver for testing / pluggable providers."""
        cls._custom_ai_resolver = provider_func
        try:
            from AIBackend import AIBackend
            AIBackend.set_ai_provider(provider_func)
        except Exception:
            pass

    @staticmethod
    def validate_command_safety(command: str, tool_name: str = "") -> tuple:
        """
        Validates that the command is safe, non-destructive, and appropriate for tool installation.
        """
        if not command or not command.strip():
            return False, "Installation command is empty."

        cmd_clean = command.strip().lower()

        # Blacklist destructive operations
        destructive_patterns = [
            r"\brm\s+-[a-zA-Z]*r",
            r"\bdel\s+/[a-zA-Z]*f",
            r"\bformat\s+[a-zA-Z]:",
            r"\bmkfs\b",
            r"\bdd\s+if=",
            r"\bshutdown\b",
            r"\breboot\b",
            r":\(\)\s*\{\s*:\|:&\s*\};:",
            r">\s*/dev/sd",
            r"\bdrop\s+database\b",
            r"\bchmod\s+-[a-zA-Z]*R\s+777\s+/",
        ]
        for pat in destructive_patterns:
            if re.search(pat, cmd_clean):
                return False, "Command rejected: Destructive or unsafe system operation detected."

        # Validate that command uses known package managers or standard installation mechanisms
        allowed_installers = [
            "pip", "npm", "yarn", "pnpm", "cargo", "winget", "choco", "scoop",
            "brew", "apt", "apt-get", "pacman", "yum", "dnf", "rustup", "dotnet",
            "go install", "gem", "setup.py", "python -m pip", "python3 -m pip", "pyside6",
            "python", "python3", "py"
        ]
        has_installer = any(mgr in cmd_clean for mgr in allowed_installers)
        if not has_installer:
            if not any(k in cmd_clean for k in ("install", "add", "setup", "get")):
                return False, "Command rejected: Command is not a recognized developer tool installation command."

        return True, "Valid"

    @staticmethod
    def validate_package_name(package_name: str, install_cmd: str = "", lang_id: str = "") -> tuple:
        """
        Validates that a package or tool name is real, single-word/syntactically valid,
        and not a hallucinated phrase like 'sql formatter'.
        """
        if not package_name or not package_name.strip():
            return False, "Package name is empty."

        clean_pkg = package_name.strip()

        # Reject multi-word hallucinated names (e.g. "sql formatter", "python pep8 tool")
        if " " in clean_pkg and not clean_pkg.startswith(("@", "-")):
            return False, f"Invalid package name '{clean_pkg}': contains spaces and is not a valid package identifier."

        # Syntactic checks
        if not re.match(r"^(@[a-zA-Z0-9_\-\.]+\/)?[a-zA-Z0-9_\-\.:#]+$", clean_pkg):
            return False, f"Invalid package name syntax: '{clean_pkg}'."

        return True, "Valid package identifier"

    def validate_resolution(self, res: dict, context: dict) -> tuple:
        """
        Validates the AI resolution against command safety, package validity,
        strict language isolation, and working software checks.
        """
        res_type = res.get("resolutionType") or res.get("resolution_type", "cannot_resolve")
        if res_type == "cannot_resolve":
            return True, "Cannot resolve is valid"

        cmd = res.get("command", "")
        steps = res.get("steps", [])
        tool = res.get("toolName") or res.get("tool", "")
        pkg = res.get("packageName") or res.get("package", "")
        lang = (context.get("language") or context.get("languageId") or "").lower().strip()
        stderr = (context.get("stderr") or context.get("errorMessage") or "").lower()

        if res_type == "single_command":
            if not cmd or not cmd.strip():
                return False, "Empty command provided for single_command resolution."
            is_safe, s_msg = self.validate_command_safety(cmd, tool)
            if not is_safe:
                return False, s_msg
            if pkg:
                pkg_valid, p_msg = self.validate_package_name(pkg, cmd, lang)
                if not pkg_valid:
                    return False, p_msg
        elif res_type == "complex_setup":
            if not steps and not cmd:
                return False, "No steps provided for complex_setup resolution."

        # Strict language isolation validation
        cmd_lower = (cmd or "").lower()
        if lang in ("csharp", "cs"):
            if "clang-format" in cmd_lower or "pip install" in cmd_lower:
                return False, "Cross-language mismatch: C# tooling cannot use clang-format or Python pip."
        elif lang in ("cpp", "c", "c++"):
            if "csharpier" in cmd_lower or "dotnet tool" in cmd_lower:
                return False, "Cross-language mismatch: C/C++ cannot use C# .NET tooling."
        elif lang == "java":
            if "clang-format" in cmd_lower or "autopep8" in cmd_lower or "csharpier" in cmd_lower:
                return False, "Cross-language mismatch: Java cannot use C++/Python/C# formatters."
        elif lang in ("python", "py"):
            if "csharpier" in cmd_lower or "gofmt" in cmd_lower:
                return False, "Cross-language mismatch: Python cannot use C# or Go tooling."
        elif lang == "sql":
            if "clang-format" in cmd_lower or "gofmt" in cmd_lower:
                return False, "Cross-language mismatch: SQL cannot use C++ or Go formatters."

        # Database connection errors (e.g. SQLException, missing JDBC driver) do not warrant reinstalling JDK
        if ("sqlexception" in stderr or "driver" in stderr) and ("install --id oracle.jdk" in cmd_lower or "install openjdk" in cmd_lower) and "jcanypattern" not in stderr and "javac" not in stderr:
            return False, "Misdiagnosis: Application error indicates Java runtime is already installed; missing JDBC dependency, not JDK runtime."

        return True, "Valid"

    @Slot(str, str, str, str, str, str, int, str, str, str, str, str, str, result="QVariantMap")
    @Slot(str, str, str, str, str, str, int, str, str, str, result="QVariantMap")
    @Slot(str, str, str, str, str, str, result="QVariantMap")
    @Slot(str, str, str, str, result="QVariantMap")
    @Slot(str, str, str, result="QVariantMap")
    @Slot(str, str, result="QVariantMap")
    @Slot(str, result="QVariantMap")
    def create_smart_install_context(
        self,
        operation: str = "",
        operation_type: str = "",
        language: str = "",
        file_path: str = "",
        command_attempted: str = "",
        executable: str = "",
        exit_code: int = 0,
        stdout: str = "",
        stderr: str = "",
        error_message: str = "",
        detected_problem: str = "",
        detected_missing_dependency: str = "",
        retry_action: str = "",
        **kwargs
    ) -> dict:
        """
        Creates a structured SmartInstallContext containing real failure information.
        This represents the entry point for Smart Install investigation.
        """
        cur_os = get_current_os()
        clean_lang = (language or "").lower().strip()
        clean_ext = os.path.splitext(file_path)[1].lower().lstrip(".") if file_path else ""

        # Collect available package managers
        avail_pms = []
        for pm in ("winget", "pip", "npm", "cargo", "dotnet", "choco", "scoop", "brew", "apt"):
            if locate_executable(pm):
                avail_pms.append(pm)

        resolved_retry = retry_action
        if not resolved_retry:
            if operation_type == "formatter" or "format" in (operation or "").lower():
                resolved_retry = "format"
            elif operation_type in ("runner", "compiler", "runtime", "sdk", "interpreter") or "run" in (operation or "").lower():
                resolved_retry = "run"
            else:
                resolved_retry = "command"

        ctx = {
            "operation": operation or "Issue Resolution",
            "operationType": operation_type or "dependency",
            "language": clean_lang or clean_ext,
            "languageId": clean_lang or clean_ext,
            "filePath": file_path or "",
            "operatingSystem": cur_os,
            "architecture": platform.machine(),
            "pythonExecutable": sys.executable,
            "pythonVersion": platform.python_version(),
            "availablePackageManagers": avail_pms,
            "retryAction": resolved_retry
        }

        if command_attempted:
            ctx["commandAttempted"] = command_attempted
        if executable:
            ctx["executable"] = executable
        if exit_code != 0:
            ctx["exitCode"] = exit_code
        if stdout:
            ctx["stdout"] = stdout
        if stderr:
            ctx["stderr"] = stderr
        if error_message:
            ctx["errorMessage"] = error_message
        if detected_problem:
            ctx["detectedProblem"] = detected_problem
        if detected_missing_dependency:
            ctx["detectedMissingDependency"] = detected_missing_dependency
        if kwargs.get("failureType") or kwargs.get("failure_type"):
            ctx["failureType"] = kwargs.get("failureType") or kwargs.get("failure_type")
        if kwargs.get("formatterAvailable") is not None or kwargs.get("formatter_available") is not None:
            ctx["formatterAvailable"] = kwargs.get("formatterAvailable") if kwargs.get("formatterAvailable") is not None else kwargs.get("formatter_available")
        if kwargs.get("dependencyMissing") is not None or kwargs.get("dependency_missing") is not None:
            ctx["dependencyMissing"] = kwargs.get("dependencyMissing") if kwargs.get("dependencyMissing") is not None else kwargs.get("dependency_missing")
        if kwargs.get("formatter"):
            ctx["formatter"] = kwargs.get("formatter")
        if file_path:
            ctx["projectDirectory"] = os.path.dirname(os.path.abspath(file_path))
            ctx["workingDirectory"] = os.path.dirname(os.path.abspath(file_path))

        print(f"[SmartInstall] Entry point created: {ctx.get('operation')}")
        print(f"[SmartInstall] Entry point shown")
        return ctx

    def generate_smart_install_prompt(
        self,
        context: Optional[dict] = None,
        tool_name: str = "",
        tool_type: str = "",
        missing_dependency: str = "",
        lang_id: str = "",
        ext: str = "",
        cur_os: str = "",
        shell_name: str = "",
        python_env: str = "",
        operation: str = "",
        failure_context: str = ""
    ) -> str:
        """
        Constructs the structured prompt sent to the AI backend for environment/dependency setup resolution.
        Enforces authoritative trust of backend facts, distinct failure classification, and actionable resolution.
        """
        if context is None:
            context = {}

        op = context.get("operation") or operation or "Environment/Dependency Resolution"
        op_type = context.get("operationType") or tool_type or "dependency"
        lang = context.get("language") or context.get("languageId") or lang_id or ext or "general"
        target_file = context.get("filePath") or ""
        cmd_att = context.get("commandAttempted") or ""
        exec_name = context.get("executable") or tool_name or ""
        exit_c = context.get("exitCode", "")
        out_txt = context.get("stdout") or ""
        err_txt = context.get("stderr") or context.get("errorMessage") or failure_context or ""
        os_name = context.get("operatingSystem") or cur_os or get_current_os()
        sh_name = shell_name or ("PowerShell" if os_name == "windows" else os.environ.get("SHELL", "bash").split("/")[-1])
        py_path = context.get("pythonExecutable") or python_env or sys.executable
        pms = ", ".join(context.get("availablePackageManagers", [])) or "standard system package managers"

        missing_dep = context.get("detectedMissingDependency") or missing_dependency or exec_name or tool_name
        formatter_name = context.get("formatter") or context.get("toolName") or (exec_name if op_type == "formatter" or "format" in op.lower() else "")
        formatter_avail = context.get("formatterAvailable") if context.get("formatterAvailable") is not None else context.get("formatter_available")
        dep_missing = context.get("dependencyMissing") if context.get("dependencyMissing") is not None else context.get("dependency_missing")
        failure_type = context.get("failureType") or context.get("failure_type")

        if dep_missing is None and (missing_dep or (op_type in ("dependency", "formatter", "runner") and not locate_executable(exec_name or tool_name))):
            dep_missing = True

        if formatter_avail is None and formatter_name:
            formatter_avail = bool(locate_executable(formatter_name))

        if not failure_type:
            if dep_missing:
                failure_type = "missing_dependency"
            elif "syntax" in err_txt.lower() or "parse error" in err_txt.lower() or "invalid syntax" in err_txt.lower() or "unexpected token" in err_txt.lower():
                failure_type = "source_error"
            else:
                failure_type = "missing_dependency" if (missing_dep or not locate_executable(exec_name)) else "runtime_error"

        details = []
        if target_file:
            details.append(f"Target file: {target_file}")
        if cmd_att:
            details.append(f"Command attempted: {cmd_att}")
        if missing_dep:
            details.append(f"Missing dependency: {missing_dep}")
        if exec_name and exec_name != missing_dep:
            details.append(f"Missing executable / tool: {exec_name}")
        if exit_c:
            details.append(f"Exit code: {exit_c}")
        if out_txt:
            details.append(f"Stdout:\n{out_txt}")
        if err_txt:
            details.append(f"Stderr / Error:\n{err_txt}")

        details_block = "\n".join(details) if details else "No additional error output available."

        return (
            "You are an AI developer environment resolver for DGX Studio.\n"
            "Your job is to SOLVE the detected environment or dependency problem. You must NOT merely repeat or echo the error.\n\n"
            "BACKEND VERIFIED FACTS (AUTHORITATIVE):\n"
            f"- Formatter / Tool: {formatter_name or exec_name or tool_name or 'Unspecified'}\n"
            f"- Executable: {exec_name or formatter_name or 'Unspecified'}\n"
            f"- Formatter available: {str(bool(formatter_avail)).lower() if formatter_avail is not None else 'unknown'}\n"
            f"- Dependency missing: {str(bool(dep_missing)).lower() if dep_missing is not None else 'unknown'}\n"
            f"- Failure type: {failure_type}\n"
            f"- Operation: {op}\n"
            f"- Operation type: {op_type}\n"
            f"- Language: {lang}\n"
            f"- Operating system: {os_name}\n"
            f"- Shell: {sh_name}\n"
            f"- Active Python interpreter: {py_path}\n"
            f"- Available package managers: {pms}\n\n"
            f"FAILURE CONTEXT:\n{details_block}\n\n"
            "CORE RESOLUTION RULES:\n"
            "1. TRUST BACKEND FACTS:\n"
            "   The Smart Install backend has already determined important facts. Treat backend facts as authoritative.\n"
            "   If Dependency missing is true or Failure type is 'missing_dependency', the tool is missing. You MUST determine the appropriate installation command for the target OS (" + os_name + ") and shell (" + sh_name + ") and return it (e.g. `npm install -g prettier` with verification `prettier --version`).\n"
            "   Do NOT reinterpret this as invalid JSON, invalid source, unknown formatter, or configuration error unless the supplied backend facts explicitly say that.\n\n"
            "2. DO NOT CONFUSE FAILURE TYPES:\n"
            "   - missing_dependency: The required tool does not exist -> resolve installation.\n"
            "   - source_error: The tool exists and reports invalid source / syntax error -> explain the source error; do NOT recommend installing another formatter.\n"
            "   - configuration_error: Tool exists but configuration is wrong -> determine whether configuration can safely be fixed.\n"
            "   - runtime_error: Tool exists but operation failed -> analyze the real failure. Do NOT recommend software that is already proven to be installed (e.g. if Java threw an application error, Java is installed).\n"
            "   - environment_error: PATH/tool/environment resolution is broken -> determine whether it can safely be repaired.\n\n"
            "3. JAVA & UNSPECIFIED FORMATTER BEHAVIOR:\n"
            "   If Language is Java and operation is formatting and formatter is unspecified/unknown with dependency missing: do NOT immediately say 'The required formatter is unspecified'. Instead, identify a reasonable standard Java formatter (such as google-java-format) and provide the installation/verification resolution. Only return cannot_resolve when there genuinely is not enough information to safely choose a solution.\n\n"
            "4. SMART INSTALL MUST ACTUALLY SOLVE (RESOLVER, NOT ECHOER):\n"
            "   Bad: 'The formatter is missing.'\n"
            "   Good: 'Prettier is not installed. Install it with: npm install -g prettier. Verify with: prettier --version'\n"
            "   - Strict language isolation: NEVER recommend cross-language tools (e.g. do not suggest clang-format for C#, do not suggest Python tools for Java).\n"
            "   - If using Python pip, use active Python interpreter path: \"" + py_path + "\" -m pip install <package_name>\n\n"
            "5. RESPONSE CONTRACT (VALID JSON ONLY):\n"
            "Return valid JSON only matching this schema:\n"
            "{\n"
            '  "resolutionType": "single_command" | "complex_setup" | "cannot_resolve",\n'
            '  "source": "ai",\n'
            '  "title": "<concise title>",\n'
            '  "diagnosis": "<concise root cause>",\n'
            '  "explanation": "<actionable explanation of solution>",\n'
            '  "command": "<exact single install command if single_command, else empty string>",\n'
            '  "steps": ["<step 1>", "<step 2>"],\n'
            '  "verificationCommand": "<verification command e.g. tool --version>",\n'
            '  "tool": "<tool name>",\n'
            '  "package": "<package identifier>",\n'
            '  "executable": "<executable name>",\n'
            '  "retryOperation": true\n'
            "}"
        )

    @staticmethod
    def parse_ai_install_response(response_text: str, fallback_tool: str = "", fallback_exec: str = "", fallback_type: str = "tool") -> dict:
        """
        Parses AI JSON or structured text response into normalized dictionary.
        """
        if not response_text:
            return {
                "tool": fallback_tool,
                "dependency_type": fallback_type,
                "package": fallback_exec or fallback_tool,
                "executable": fallback_exec or fallback_tool,
                "resolutionType": "cannot_resolve",
                "resolution_type": "cannot_resolve",
                "command": "",
                "verify": f"{fallback_exec or fallback_tool} --version",
                "verificationCommand": f"{fallback_exec or fallback_tool} --version",
                "explanation": "",
                "diagnosis": "",
                "source": "ai"
            }

        text = response_text.strip()
        if text.lower().startswith("chatgpt said:"):
            text = text[13:].strip()

        # 1. Try parsing JSON block (including markdown fences)
        json_cand = text
        if "```json" in text or "```" in text:
            m = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text, re.IGNORECASE)
            if m:
                json_cand = m.group(1).strip()
        elif "{" in text and "}" in text:
            m = re.search(r'(\{[\s\S]+\})', text)
            if m:
                json_cand = m.group(1).strip()

        data = None
        try:
            data = json.loads(json_cand)
        except Exception:
            try:
                # Repair unescaped Windows backslashes in JSON string
                repaired = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', json_cand)
                data = json.loads(repaired)
            except Exception:
                pass

        if isinstance(data, dict):
            r_type = data.get("resolutionType") or data.get("resolution_type") or ("single_command" if data.get("command") else "cannot_resolve")
            cmd = data.get("command", "")
            steps = data.get("steps", [])
            if isinstance(steps, str):
                steps = [s.strip() for s in steps.splitlines() if s.strip()]
            v_cmd = data.get("verificationCommand") or data.get("verify") or ""
            t_name = data.get("tool") or data.get("toolName") or fallback_tool
            pkg_name = data.get("package") or data.get("packageName") or fallback_exec or fallback_tool
            exec_name = data.get("executable") or fallback_exec or fallback_tool

            return {
                "tool": t_name,
                "toolName": t_name,
                "title": data.get("title") or f"Install {t_name}",
                "dependency_type": data.get("dependencyType") or data.get("dependency_type") or fallback_type,
                "dependencyType": data.get("dependencyType") or data.get("dependency_type") or fallback_type,
                "package": pkg_name,
                "packageName": pkg_name,
                "executable": exec_name,
                "resolutionType": r_type,
                "resolution_type": r_type,
                "command": cmd,
                "steps": steps,
                "verify": v_cmd or f"{exec_name} --version",
                "verificationCommand": v_cmd or f"{exec_name} --version",
                "diagnosis": data.get("diagnosis", ""),
                "explanation": data.get("explanation", ""),
                "source": "ai",
                "retryOperation": data.get("retryOperation", True)
            }

        # 2. Key-value fallback parsing
        tool_val = ""
        type_val = ""
        pkg_val = ""
        exec_val = ""
        res_type_val = ""
        cmd_val = ""
        ver_val = ""
        exp_val = ""
        diag_val = ""
        steps_val = []

        tool_m = re.search(r'(?:^|\n)\s*Tool\s*:\s*(.+)', text, re.IGNORECASE)
        type_m = re.search(r'(?:^|\n)\s*Dependency\s*Type\s*:\s*(.+)', text, re.IGNORECASE)
        pkg_m = re.search(r'(?:^|\n)\s*Package\s*:\s*(.+)', text, re.IGNORECASE)
        exec_m = re.search(r'(?:^|\n)\s*Executable\s*:\s*(.+)', text, re.IGNORECASE)
        res_m = re.search(r'(?:^|\n)\s*Resolution\s*Type\s*:\s*(.+)', text, re.IGNORECASE)
        cmd_m = re.search(r'(?:^|\n)\s*(?:Command|Install)\s*:\s*(.+)', text, re.IGNORECASE)
        ver_m = re.search(r'(?:^|\n)\s*Verify\s*:\s*(.+)', text, re.IGNORECASE)
        diag_m = re.search(r'(?:^|\n)\s*Diagnosis\s*:\s*(.+)', text, re.IGNORECASE)
        exp_m = re.search(r'(?:^|\n)\s*Explanation\s*:\s*([\s\S]+?)(?=\n\s*(?:Tool|Dependency|Package|Executable|Resolution|Command|Install|Verify|Diagnosis)|$)', text, re.IGNORECASE)

        if tool_m:
            tool_val = tool_m.group(1).strip()
        if type_m:
            type_val = type_m.group(1).strip().lower()
        if pkg_m:
            pkg_val = pkg_m.group(1).strip()
        if exec_m:
            exec_val = exec_m.group(1).strip()
        if res_m:
            res_type_val = res_m.group(1).strip().lower()
        if cmd_m:
            cmd_val = cmd_m.group(1).strip()
        if ver_m:
            ver_val = ver_m.group(1).strip()
        if diag_m:
            diag_val = diag_m.group(1).strip()
        if exp_m:
            exp_val = exp_m.group(1).strip()

        if not cmd_val:
            code_m = re.search(r'```(?:bash|sh|shell|powershell|cmd|batch|text)?\s*([\s\S]+?)```', text, re.IGNORECASE)
            if code_m:
                lines = [l.strip() for l in code_m.group(1).strip().splitlines() if l.strip() and not l.strip().startswith("#")]
                if lines:
                    cmd_val = lines[0]

        if cmd_val:
            cmd_val = cmd_val.strip("`").strip()
            if cmd_val.lower() in ("none", "n/a", "null", "cannot_resolve", "") or cmd_val.lower().startswith("verify:"):
                cmd_val = ""

        if not res_type_val:
            if not cmd_val:
                res_type_val = "cannot_resolve"
            elif "\n" in cmd_val or "step 1" in text.lower():
                res_type_val = "complex_setup"
            else:
                res_type_val = "single_command"

        if res_type_val == "cannot_resolve":
            cmd_val = ""
            steps_val = []

        if res_type_val == "complex_setup" and cmd_val and "\n" in cmd_val:
            steps_val = [s.strip() for s in cmd_val.splitlines() if s.strip()]

        if not exp_val and text:
            clean_lines = [l for l in text.splitlines() if not l.lower().startswith(("tool:", "dependency", "package:", "executable:", "resolution", "command:", "install:", "verify:", "diagnosis:")) and l.strip()]
            if clean_lines:
                exp_val = " ".join(clean_lines)[:300]

        t_name = tool_val or fallback_tool
        exec_name = exec_val or pkg_val or fallback_exec or fallback_tool
        pkg_name = pkg_val or exec_val or fallback_exec or fallback_tool

        return {
            "tool": t_name,
            "toolName": t_name,
            "title": f"Install {t_name}",
            "dependency_type": type_val or fallback_type,
            "dependencyType": type_val or fallback_type,
            "package": pkg_name,
            "packageName": pkg_name,
            "executable": exec_name,
            "resolutionType": res_type_val,
            "resolution_type": res_type_val,
            "command": cmd_val,
            "steps": steps_val,
            "verify": ver_val or f"{exec_name} --version",
            "verificationCommand": ver_val or f"{exec_name} --version",
            "diagnosis": diag_val or f"Missing dependency {t_name}",
            "explanation": exp_val or f"Installs {t_name}.",
            "source": "ai",
            "retryOperation": True
        }

    @Slot("QVariantMap", result="QVariantMap")
    def resolve_smart_install_context(self, context: dict) -> dict:
        """
        NOW actually invokes the AI resolver:
        1. Emits smartInstallAnalysisStarted and logs lifecycle.
        2. Sends structured failure context to configured AI backend.
        3. Parses response and validates command safety, package syntax, and domain isolation.
        4. If validation fails, performs ONE corrective retry before falling back.
        5. Returns structured recommendation for explicit user approval.
        """
        cur_os = get_current_os()
        tool_name = context.get("toolName") or context.get("executable") or context.get("operation", "Developer Tool")
        clean_lang = (context.get("language") or context.get("languageId") or "").lower().strip()
        retry_act = context.get("retryAction", "run")
        file_path = context.get("filePath", "")

        print(f"[SmartInstall] ==================================================")
        print(f"[SmartInstall] AI analysis started")
        self.smartInstallAnalysisStarted.emit(tool_name)

        # 1. Generate prompt from context
        prompt = self.generate_smart_install_prompt(context=context)
        print(f"[SmartInstall] AI request sent")

        # 2. Query configured AI backend through centralized AI pipeline
        print(f"[SmartInstall] Sending request through existing AI backend")
        ai_response_text = ""
        is_ai_available = False
        ai_failure_reason = ""

        try:
            from AIBackend import AIBackend
            ai_backend = self.ai_backend or AIBackend.get_instance()
            ai_response_text = ai_backend.ask(prompt)
            if ai_response_text:
                is_ai_available = True
            else:
                ai_failure_reason = "AI backend returned empty response"
        except Exception as ex:
            ai_failure_reason = str(ex)
            is_ai_available = False

        # Check for manifest-contributed recipe if AI failed
        manifest_recipe = self._contributed_tool_dependencies.get(tool_name, {})
        recipe_cmd = ""
        if manifest_recipe:
            guide = manifest_recipe.get("installGuide", {})
            recipe_cmd = guide.get(cur_os, "") or guide.get("all", "")

        if is_ai_available and ai_response_text:
            print(f"[SmartInstall] AI request completed")
            print(f"[SmartInstall] Raw AI response received: {ai_response_text}")

            parsed = self.parse_ai_install_response(ai_response_text, fallback_tool=tool_name, fallback_exec=tool_name, fallback_type=context.get("operationType", "tool"))
            print(f"[SmartInstall] AI response parsed")

            # Validate resolution
            is_valid, val_reason = self.validate_resolution(parsed, context)
            print(f"[SmartInstall] AI response validation result: is_safe={is_valid}, pkg_valid={is_valid}")

            # Corrective AI retry if invalid
            if not is_valid:
                print(f"[SmartInstall] Corrective AI retry started: {val_reason}")
                reprompt = (
                    f"Your previous recommendation had an issue: {val_reason}.\n"
                    f"Please provide a valid, safe, official package identifier and installation command on {cur_os} in valid JSON format.\n\n"
                    + prompt
                )
                corr_text = ""
                try:
                    from AIBackend import AIBackend
                    ai_backend = self.ai_backend or AIBackend.get_instance()
                    print(f"[SmartInstall] Sending request through existing AI backend")
                    corr_text = ai_backend.ask(reprompt)
                    if corr_text:
                        parsed_corr = self.parse_ai_install_response(corr_text, fallback_tool=tool_name, fallback_exec=tool_name, fallback_type=context.get("operationType", "tool"))
                        c_valid, c_msg = self.validate_resolution(parsed_corr, context)
                        if c_valid:
                            parsed = parsed_corr
                            is_valid = True
                        else:
                            val_reason = c_msg
                except Exception as rex:
                    print(f"[SmartInstall] Re-prompt error: {rex}")

            if not is_valid:
                parsed["resolutionType"] = "cannot_resolve"
                parsed["resolution_type"] = "cannot_resolve"
                parsed["command"] = ""
                parsed["explanation"] = f"Validation blocked command: {val_reason}"

            final_res_type = parsed.get("resolutionType", "single_command")
            final_source = "ai"
            final_cmd = parsed.get("command", "")

            proposal = {
                "toolName": parsed.get("tool") or tool_name,
                "toolType": parsed.get("dependencyType", "tool"),
                "dependencyType": parsed.get("dependencyType", "tool"),
                "packageName": parsed.get("package", tool_name),
                "executable": parsed.get("executable", tool_name),
                "resolutionType": final_res_type,
                "title": parsed.get("title") or f"Install {parsed.get('tool', tool_name)}",
                "diagnosis": parsed.get("diagnosis") or f"Missing {parsed.get('tool', tool_name)}",
                "description": parsed.get("explanation") or parsed.get("diagnosis") or f"Installs {parsed.get('tool', tool_name)}",
                "explanation": parsed.get("explanation", ""),
                "command": final_cmd,
                "steps": parsed.get("steps", []),
                "verifyCommand": parsed.get("verificationCommand") or parsed.get("verify") or f"{parsed.get('executable', tool_name)} --version",
                "source": final_source,
                "needsConfirmation": True,
                "currentOs": cur_os,
                "retryAction": retry_act,
                "filePath": file_path,
                "languageId": clean_lang,
                "isInstalled": False
            }

        elif recipe_cmd:
            print(f"[SmartInstall] AI request failed: {ai_failure_reason or 'offline'}")
            print(f"[SmartInstall] Resolution source: Built-in Recipe")
            final_res_type = "single_command"
            final_source = "built_in_recipe"
            final_cmd = recipe_cmd

            proposal = {
                "toolName": tool_name,
                "toolType": context.get("operationType", "tool"),
                "dependencyType": context.get("operationType", "tool"),
                "packageName": tool_name,
                "executable": manifest_recipe.get("executable", tool_name),
                "resolutionType": final_res_type,
                "title": f"Install {tool_name}",
                "diagnosis": f"Built-in recipe for {tool_name}",
                "description": f"Installs {tool_name} from extension recipe.",
                "explanation": f"Installs {tool_name} tool dependency.",
                "command": final_cmd,
                "steps": [],
                "verifyCommand": f"{manifest_recipe.get('executable', tool_name)} --version",
                "source": final_source,
                "needsConfirmation": True,
                "currentOs": cur_os,
                "retryAction": retry_act,
                "filePath": file_path,
                "languageId": clean_lang,
                "isInstalled": False
            }
        else:
            print(f"[SmartInstall] AI request failed: {ai_failure_reason or 'offline'}")
            print(f"[SmartInstall] Resolution source: AI Unavailable")
            final_res_type = "cannot_resolve"
            final_source = "ai_unavailable"
            final_cmd = ""

            proposal = {
                "toolName": tool_name,
                "toolType": context.get("operationType", "tool"),
                "dependencyType": context.get("operationType", "tool"),
                "packageName": tool_name,
                "executable": tool_name,
                "resolutionType": final_res_type,
                "title": f"AI Unavailable for {tool_name}",
                "diagnosis": "AI could not analyze this issue.",
                "description": f"Smart Install could not generate a verified recommendation because AI is unavailable ({ai_failure_reason or 'provider unreachable'}).",
                "explanation": f"AI could not analyze this issue: {ai_failure_reason or 'provider unreachable'}",
                "command": "",
                "steps": [],
                "verifyCommand": f"{tool_name} --version",
                "source": final_source,
                "needsConfirmation": True,
                "currentOs": cur_os,
                "retryAction": retry_act,
                "filePath": file_path,
                "languageId": clean_lang,
                "isInstalled": False
            }

        print(f"[SmartInstall] Final resolution type: {proposal.get('resolutionType', final_res_type)}")
        print(f"[SmartInstall] Source: {proposal.get('source', final_source)}")
        print(f"[SmartInstall] Command availability: {bool(proposal.get('command', ''))}")
        print(f"[SmartInstall] ==================================================")
        return proposal

    @Slot("QVariantMap")
    def start_smart_install_analysis(self, context: dict):
        """Asynchronously runs AI resolution in a background thread."""
        def _worker():
            try:
                proposal = self.resolve_smart_install_context(context)
                self.smartInstallResolved.emit(proposal)
            except Exception as e:
                print(f"[SmartInstall] Async analysis error: {e}")
                self.smartInstallAnalysisFailed.emit(str(context.get("toolName", "tool")), str(e))

        threading.Thread(target=_worker, daemon=True).start()

    @Slot(str, str, str, str, str, result="QVariantMap")
    def suggest_smart_install(self, tool_type: str, tool_name: str, lang_id: str, ext: str, file_path: str = "") -> dict:
        """
        Convenience resolution entry point (creates context and resolves).
        """
        ctx = self.create_smart_install_context(
            operation=f"Install {tool_name}",
            operation_type=tool_type,
            language=lang_id,
            file_path=file_path,
            executable=tool_name,
            detected_missing_dependency=tool_name
        )
        return self.resolve_smart_install_context(ctx)

    @Slot(str, str, int, str, str, str, str, result="QVariantMap")
    def suggest_smart_install_for_failure(self, operation: str, error_output: str, exit_code: int, failed_command: str, lang_id: str = "", ext: str = "", file_path: str = "") -> dict:
        """
        Convenience resolution entry point for command / runtime failures.
        """
        ctx = self.create_smart_install_context(
            operation=operation,
            operation_type="failure",
            language=lang_id,
            file_path=file_path,
            command_attempted=failed_command,
            exit_code=exit_code,
            stderr=error_output,
            error_message=error_output
        )
        return self.resolve_smart_install_context(ctx)

    def _classify_install_method(self, command: str, executable: str, package_name: str) -> str:
        cmd_lower = (command or "").lower().strip()
        if "dotnet tool install" in cmd_lower:
            return "dotnet_global_tool"
        if "pip install" in cmd_lower or "pip3 install" in cmd_lower or " -m pip " in cmd_lower:
            return "python_package"
        if "npm install -g" in cmd_lower or "pnpm add -g" in cmd_lower or "yarn global add" in cmd_lower:
            return "npm_global"
        if "cargo install" in cmd_lower or "rustup " in cmd_lower:
            return "cargo"
        if "winget install" in cmd_lower:
            return "winget"
        if any(pm in cmd_lower for pm in ("brew install", "apt-get install", "apt install", "pacman -s", "choco install")):
            return "system_package"
        return "direct_cli"

    def _extract_package_from_command(self, command: str, fallback: str = "") -> str:
        if not command:
            return fallback
        parts = command.strip().split()
        if "dotnet" in parts and "tool" in parts and "install" in parts:
            for i, p in enumerate(parts):
                if p == "install" and i + 1 < len(parts):
                    rest = [x for x in parts[i+1:] if not x.startswith("-")]
                    if rest:
                        return rest[-1]
        if "-m" in parts and "pip" in parts and "install" in parts:
            try:
                idx = parts.index("install")
                pkgs = [p for p in parts[idx+1:] if not p.startswith("-")]
                if pkgs:
                    return pkgs[0]
            except ValueError:
                pass
        if "npm" in parts and "install" in parts:
            try:
                idx = parts.index("install")
                pkgs = [p for p in parts[idx+1:] if not p.startswith("-")]
                if pkgs:
                    return pkgs[0]
            except ValueError:
                pass
        return fallback

    def generate_post_install_prompt(
        self,
        tool_name: str,
        command: str,
        install_exit_code: int,
        install_stdout: str,
        install_stderr: str,
        verify_cmd: str,
        verify_exit_code: int,
        verify_stdout: str,
        verify_stderr: str,
        executable: str = "",
        package_name: str = "",
        language: str = "",
        os_name: str = "",
        shell_name: str = "",
        working_dir: str = "",
        verified_path: str = "",
        original_diagnosis: str = "",
        fix_attempt_count: int = 0,
        is_post_fix: bool = False,
        operation_attempted: str = "",
        operation_exit_code: int = 0,
        operation_stdout: str = "",
        operation_stderr: str = "",
        operation_error: str = "",
        tool_version: str = "",
        runtime_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Constructs the dedicated prompt sent to AI for post-install execution output and runtime diagnosis.
        """
        import platform

        cur_os = os_name or get_current_os()
        arch = platform.machine() or "x64"
        sh_name = shell_name or ("PowerShell" if cur_os == "windows" else os.environ.get("SHELL", "bash").split("/")[-1])
        cwd_dir = working_dir or os.getcwd()
        exec_str = executable or tool_name
        pkg_str = package_name or exec_str

        if runtime_info is None:
            runtime_info = collect_runtime_environment_info(
                tool_name=tool_name,
                language=language,
                executable=exec_str,
                verified_path=verified_path,
                operation_error=operation_error or operation_stderr or install_stderr
            )

        # Build factual environment and runtime summaries
        r_type = runtime_info.get("runtime_type", "general")
        r_ver = runtime_info.get("runtime_version", "Unknown")
        r_exe = runtime_info.get("runtime_executable", "Unknown")
        r_env = runtime_info.get("runtime_env_vars", {})
        env_vars_formatted = ", ".join([f"{k}={v}" for k, v in r_env.items()]) if r_env else "None"
        avail_runtimes = runtime_info.get("available_runtimes", [])
        avail_runtimes_str = "; ".join(avail_runtimes) if avail_runtimes else "None discovered"

        installed_ver = tool_version or (verify_stdout.splitlines()[0] if verify_stdout else "Installed")
        op_err_str = operation_error or operation_stderr or "(none)"

        # Preamble requested in Section 2
        preamble = (
            "You are DGX Studio's post-install diagnostic and recovery AI.\n\n"
            "A dependency may have installed successfully but still fail during its\n"
            "actual operation.\n\n"
            "Your responsibility is to diagnose the underlying cause using the actual\n"
            "execution output, error messages, executable paths, runtime versions,\n"
            "and verification results.\n\n"
            "Do not confuse successful installation with successful operation.\n\n"
            "Do not merely repeat the error.\n\n"
            "Identify the likely root cause and recommend the safest appropriate fix.\n\n"
            "When a compatible runtime or dependency is missing or outdated, recommend\n"
            "installing or selecting a compatible version.\n\n"
            "Prefer a concrete, executable command over vague instructions.\n\n"
            "If a safe automated fix exists, return [FIX] followed by the exact command.\n\n"
            "If the problem requires manual intervention, return\n"
            "MANUAL_INSTALLATION_REQUIRED.\n\n"
            "If the operation genuinely succeeded and the required functionality has\n"
            "been verified, return SUCCESS.\n\n"
            "If no reliable solution can be determined, return FAILED.\n\n"
            "Never fabricate a diagnosis or claim that an untested fix is guaranteed\n"
            "to work.\n\n"
        )

        facts = (
            "FACTUAL EXECUTION & INSTALLATION CONTEXT:\n"
            f"- Original installation command: {command}\n"
            f"- Tool name and installed version: {tool_name} ({installed_ver})\n"
            f"- Package name: {pkg_str}\n"
            f"- Actual executable path: {verified_path or exec_str}\n"
            f"- Installation exit code: {install_exit_code}\n"
            f"- Installation stdout:\n{install_stdout or '(empty)'}\n"
            f"- Installation stderr:\n{install_stderr or '(empty)'}\n\n"
            "FACTUAL VERIFICATION CONTEXT:\n"
            f"- Verification command: {verify_cmd}\n"
            f"- Verification exit code: {verify_exit_code}\n"
            f"- Verification stdout:\n{verify_stdout or '(empty)'}\n"
            f"- Verification stderr:\n{verify_stderr or '(empty)'}\n"
            f"- Detected Executable Path: {verified_path or 'None'}\n\n"
            "FACTUAL ORIGINAL OPERATION CONTEXT:\n"
            f"- Original operation attempted: {operation_attempted or 'Run tool'}\n"
            f"- Original operation exit code: {operation_exit_code}\n"
            f"- Original operation stdout:\n{operation_stdout or '(empty)'}\n"
            f"- Original operation stderr:\n{operation_stderr or '(empty)'}\n"
            f"- Relevant stack trace / underlying error:\n{op_err_str}\n\n"
            "FACTUAL ENVIRONMENT & RUNTIME CONTEXT:\n"
            f"- Operating system and architecture: {cur_os} ({arch})\n"
            f"- Shell: {sh_name}\n"
            f"- Working directory: {cwd_dir}\n"
            f"- Runtime type: {r_type}\n"
            f"- Runtime or interpreter version: {r_ver}\n"
            f"- Runtime executable path: {r_exe}\n"
            f"- Environment variables relevant to the tool: {env_vars_formatted}\n"
            f"- Previous installation or repair attempts: {fix_attempt_count}\n"
            f"- Execution Phase: {'Post-fix verification' if is_post_fix else 'Initial post-install verification'}\n"
        )

        # Java-specific factual context if relevant
        java_facts = ""
        is_java_context = (
            r_type == "Java" or
            language == "java" or
            "java" in tool_name.lower() or
            "google-java-format" in tool_name.lower() or
            "jcanypattern" in op_err_str.lower()
        )
        if is_java_context:
            min_runtime = runtime_info.get("min_runtime_required", "JDK 21 or newer")
            incompat_flag = runtime_info.get("incompatibility_detected", False)
            incompat_desc = runtime_info.get("incompatibility_details", "")
            java_facts = (
                "\nJAVA-SPECIFIC RUNTIME CONTEXT:\n"
                f"- java -version: {r_ver}\n"
                f"- The resolved Java executable path: {r_exe}\n"
                f"- Available JDK installations: {avail_runtimes_str}\n"
                f"- JAVA_HOME, when configured: {r_env.get('JAVA_HOME', 'Not configured')}\n"
                f"- The Java executable actually used by failing formatter: {r_exe}\n"
                f"- The formatter version: {installed_ver}\n"
                f"- The formatter's documented minimum runtime version: {min_runtime}\n"
            )
            if incompat_flag and incompat_desc:
                java_facts += f"- Runtime Incompatibility Evidence: {incompat_desc}\n"

        response_contract = (
            "\nRESPONSE PROTOCOL:\n"
            "Return EXACTLY one of the following responses:\n"
            "SUCCESS\n"
            "FAILED\n"
            "[FIX] <exact safe command>\n"
            "MANUAL_INSTALLATION_REQUIRED\n\n"
            "If returning [FIX], supply the exact executable command on the line immediately following [FIX], "
            "followed by a concise explanation of the diagnosed root cause and recommended runtime upgrade."
        )

        return preamble + facts + java_facts + response_contract

    @staticmethod
    def parse_post_install_ai_response(response_text: str) -> Tuple[str, str, str]:
        """
        Parses post-install AI diagnosis response into (status, fix_command, explanation).
        status: 'SUCCESS' | 'FAILED' | 'FIX' | 'MANUAL_INSTALLATION_REQUIRED' | 'INVALID'
        """
        if not response_text:
            return "INVALID", "", "Empty AI response"

        text = response_text.strip()
        if text.lower().startswith("chatgpt said:"):
            text = text[13:].strip()

        # Remove surrounding markdown fences if present
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            if len(lines) >= 2:
                text = "\n".join(lines[1:-1]).strip()

        # Check for [FIX] command
        fix_match = re.search(r'\[FIX\]\s*(.+)', text, re.IGNORECASE | re.DOTALL)
        if fix_match:
            pre_fix = text[:fix_match.start()].strip()
            full_fix = fix_match.group(1).strip()
            fix_lines = full_fix.splitlines()
            fix_cmd = fix_lines[0].strip("`").strip()
            post_explanation = "\n".join(fix_lines[1:]).strip() if len(fix_lines) > 1 else ""
            explanation = pre_fix or post_explanation or text
            return "FIX", fix_cmd, explanation

        # Check for MANUAL_INSTALLATION_REQUIRED
        if re.search(r'\bMANUAL_INSTALLATION_REQUIRED\b', text, re.IGNORECASE):
            return "MANUAL_INSTALLATION_REQUIRED", "", text

        # Check for SUCCESS
        first_word = text.split()[0].upper() if text.split() else ""
        if first_word == "SUCCESS" or re.search(r'^\s*SUCCESS\b', text, re.MULTILINE):
            return "SUCCESS", "", text

        # Check for FAILED
        if first_word == "FAILED" or re.search(r'^\s*FAILED\b', text, re.MULTILINE):
            return "FAILED", "", text

        return "INVALID", "", text

    def diagnose_post_install_result(
        self,
        tool_name: str,
        command: str,
        install_exit_code: int,
        install_stdout: str,
        install_stderr: str,
        verify_cmd: str,
        verify_exit_code: int,
        verify_stdout: str,
        verify_stderr: str,
        executable: str = "",
        package_name: str = "",
        language: str = "",
        retry_action: str = "",
        file_path: str = "",
        verified_path: str = "",
        original_diagnosis: str = "",
        fix_attempt_count: int = 0,
        is_post_fix: bool = False,
        operation_attempted: str = "",
        operation_exit_code: int = 0,
        operation_stdout: str = "",
        operation_stderr: str = "",
        operation_error: str = "",
        tool_version: str = "",
        runtime_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, str]:
        """
        Queries the real AI backend with full execution outputs to diagnose post-install state.
        Returns (status, fix_command, explanation).
        """
        print("[SmartInstall] Post-install AI analysis started")
        print(f"[SmartInstall] Installation exit code: {install_exit_code}")
        print(f"[SmartInstall] Verification exit code: {verify_exit_code}")
        if operation_exit_code != 0 or operation_error:
            print(f"[SmartInstall] Operational failure noted: exit {operation_exit_code}, error: {operation_error or operation_stderr}")
        print("[SmartInstall] Sending installation output to AI")

        if runtime_info is None:
            runtime_info = collect_runtime_environment_info(
                tool_name=tool_name,
                language=language,
                executable=executable or verified_path,
                verified_path=verified_path,
                operation_error=operation_error or operation_stderr or install_stderr
            )

        prompt = self.generate_post_install_prompt(
            tool_name=tool_name,
            command=command,
            install_exit_code=install_exit_code,
            install_stdout=install_stdout,
            install_stderr=install_stderr,
            verify_cmd=verify_cmd,
            verify_exit_code=verify_exit_code,
            verify_stdout=verify_stdout,
            verify_stderr=verify_stderr,
            executable=executable,
            package_name=package_name,
            language=language,
            working_dir=os.path.dirname(os.path.abspath(file_path)) if file_path else os.getcwd(),
            verified_path=verified_path,
            original_diagnosis=original_diagnosis,
            fix_attempt_count=fix_attempt_count,
            is_post_fix=is_post_fix,
            operation_attempted=operation_attempted,
            operation_exit_code=operation_exit_code,
            operation_stdout=operation_stdout,
            operation_stderr=operation_stderr,
            operation_error=operation_error,
            tool_version=tool_version,
            runtime_info=runtime_info
        )

        ai_response_text = ""
        if ExtensionManager._custom_ai_resolver and callable(ExtensionManager._custom_ai_resolver):
            try:
                ai_response_text = ExtensionManager._custom_ai_resolver(prompt)
            except Exception as e:
                print(f"[SmartInstall] Custom AI request exception: {e}")

        if not ai_response_text:
            try:
                from AIBackend import AIBackend
                ai_backend = self.ai_backend or AIBackend.get_instance()
                ai_response_text = ai_backend.ask(prompt)
            except Exception as e:
                print(f"[SmartInstall] Post-install AI request exception: {e}")

        if not ai_response_text:
            try:
                from CustomApi import ChatGPTClient
                client = ChatGPTClient(headless=True)
                if hasattr(client, "is_connected") and client.is_connected:
                    ai_response_text = client.ask(prompt, timeout=12)
            except Exception as e:
                print(f"[SmartInstall] ChatGPTClient post-install request exception: {e}")

        has_operational_failure = (operation_exit_code != 0) or bool(operation_error)

        if not ai_response_text:
            print("[SmartInstall] AI unavailable for post-install analysis -> evaluating factual evidence")
            if has_operational_failure:
                if runtime_info.get("incompatibility_detected"):
                    compat_winget = "winget install --id Microsoft.OpenJDK.25 -e --accept-source-agreements --accept-package-agreements"
                    exp = (
                        "The formatter is installed, but its execution is incompatible with the Java runtime currently being used. "
                        "The current JDK is Java 17, while the installed google-java-format version requires a newer JDK. "
                        "Install a compatible JDK and ensure the formatter actually uses it."
                    )
                    print("[SmartInstall] Post-install AI result: FIX (runtime compatibility diagnosis)")
                    return "FIX", compat_winget, exp
                else:
                    err = operation_error or operation_stderr or f"Operation exited with code {operation_exit_code}"
                    print("[SmartInstall] Post-install AI result: FAILED (operational failure)")
                    return "FAILED", "", err
            elif install_exit_code == 0 and verify_exit_code == 0 and verified_path and os.path.exists(verified_path):
                print("[SmartInstall] Post-install AI result: SUCCESS")
                return "SUCCESS", "", "Tool installed and verified successfully."
            else:
                err = install_stderr or install_stdout or verify_stderr or verify_stdout or f"Exit code {install_exit_code}"
                print("[SmartInstall] Post-install AI result: FAILED")
                return "FAILED", "", err

        print("[SmartInstall] Post-install AI response received")
        print(f"[SmartInstall] Post-install AI raw response: {ai_response_text}")

        status, fix_cmd, explanation = self.parse_post_install_ai_response(ai_response_text)

        # Corrective request if invalid format
        if status == "INVALID":
            print("[SmartInstall] Post-install AI response invalid format -> running corrective request")
            reprompt = (
                "The previous post-install response did not follow the required protocol.\n"
                "Return exactly one of:\n\n"
                "SUCCESS\n"
                "FAILED\n"
                "[FIX] <safe command>\n"
                "MANUAL_INSTALLATION_REQUIRED\n\n"
                + prompt
            )
            try:
                second_resp = ""
                if ExtensionManager._custom_ai_resolver and callable(ExtensionManager._custom_ai_resolver):
                    second_resp = ExtensionManager._custom_ai_resolver(reprompt)
                if not second_resp:
                    from AIBackend import AIBackend
                    ai_backend = self.ai_backend or AIBackend.get_instance()
                    second_resp = ai_backend.ask(reprompt)
                if not second_resp:
                    from CustomApi import ChatGPTClient
                    client = ChatGPTClient(headless=True)
                    if hasattr(client, "is_connected") and client.is_connected:
                        second_resp = client.ask(reprompt, timeout=12)
                print(f"[SmartInstall] Post-install AI corrective response: {second_resp}")
                status, fix_cmd, explanation = self.parse_post_install_ai_response(second_resp)
                if status == "INVALID":
                    status = "FAILED"
                    explanation = second_resp or "Invalid AI format"
            except Exception as e:
                status = "FAILED"
                explanation = str(e)

        # CRITICAL GUARD: Do not confuse successful installation with operational success
        if has_operational_failure and status == "SUCCESS":
            print("[SmartInstall] AI incorrectly reported SUCCESS despite active operational failure. Rejecting false success.")
            if runtime_info.get("incompatibility_detected"):
                status = "FIX"
                fix_cmd = "winget install --id Microsoft.OpenJDK.25 -e --accept-source-agreements --accept-package-agreements"
                explanation = (
                    "The formatter is installed, but its execution is incompatible with the Java runtime currently being used. "
                    "The current JDK is Java 17, while the installed google-java-format version requires a newer JDK. "
                    "Install a compatible JDK and ensure the formatter actually uses it."
                )
            else:
                status = "FAILED"
                explanation = operation_error or operation_stderr or f"Operation failed with exit code {operation_exit_code}"

        # GUARD: When runtime incompatibility is detected, do not allow recommending reinstalling the same tool without addressing runtime
        if status == "FIX" and runtime_info.get("incompatibility_detected"):
            t_lower = tool_name.lower()
            fc_lower = fix_cmd.lower()
            if (t_lower in fc_lower or "google-java-format" in fc_lower) and not any(k in fc_lower for k in ("openjdk", "jdk", "java")):
                print(f"[SmartInstall] Overriding ineffective reinstall recommendation '{fix_cmd}' with runtime upgrade.")
                fix_cmd = "winget install --id Microsoft.OpenJDK.25 -e --accept-source-agreements --accept-package-agreements"
                explanation = (
                    "The formatter is installed, but its execution is incompatible with the Java runtime currently being used. "
                    "The current JDK is Java 17, while the installed google-java-format version requires a newer JDK. "
                    "Install a compatible JDK and ensure the formatter actually uses it."
                )

        if status == "SUCCESS":
            print("[SmartInstall] Post-install AI result: SUCCESS")
        elif status == "FIX":
            print("[SmartInstall] Post-install AI result: FIX")
            print(f"[SmartInstall] AI suggested fix: {fix_cmd}")
        elif status == "MANUAL_INSTALLATION_REQUIRED":
            print("[SmartInstall] Post-install AI result: MANUAL_INSTALLATION_REQUIRED")
        else:
            print("[SmartInstall] Post-install AI result: FAILED")

        return status, fix_cmd, explanation

    @Slot(str, str, str, str, str, str, result=bool)
    @Slot(str, str, str, str, str, result=bool)
    @Slot(str, str, str, str, result=bool)
    @Slot(str, str, str, result=bool)
    def execute_smart_install_command(self, tool_name: str, command: str, executable: str = "", retry_action: str = "", file_path: str = "", verify_command: str = "") -> bool:
        """
        Executes an approved Smart Install command only after explicit user approval:
        1. Logs user approval and starts installation.
        2. Validates command safety.
        3. Executes approved command.
        4. Verifies installation via verifyCommand or resolved executable.
        5. Sends real execution outputs to AI for post-install verification diagnosis.
        6. Handles SUCCESS, FIX, MANUAL_INSTALLATION_REQUIRED, or FAILED.
        """
        print(f"[SmartInstall] User approved install")
        if not command:
            print(f"[SmartInstall] Execution failed: empty command")
            self.smartInstallCompleted.emit(tool_name, False, "Cannot execute: installation command is empty.", retry_action)
            return False

        # Command safety validation
        is_safe, reason = self.validate_command_safety(command, tool_name)
        if not is_safe:
            print(f"[SmartInstall] Execution blocked: {reason}")
            self.smartInstallCompleted.emit(tool_name, False, f"Execution halted: {reason}", retry_action)
            return False

        if tool_name in self._installing_tools:
            return False

        self._installing_tools.add(tool_name)
        print(f"[SmartInstall] Installation started: {command}")
        self.smartInstallProgress.emit(tool_name, "installing", f"Running approved command: {command}")

        def _worker():
            try:
                use_shell = True
                proc = subprocess.run(command, shell=use_shell, capture_output=True, text=True, timeout=300)
                stdout = proc.stdout.strip()
                stderr = proc.stderr.strip()
                install_exit = proc.returncode

                print(f"[SmartInstall] Installation exit code: {install_exit}")
                self.smartInstallProgress.emit(tool_name, "installing", "Verifying installed executable and environment...")
                time.sleep(0.3)

                pkg_ident = self._extract_package_from_command(command, executable or tool_name)
                install_method = self._classify_install_method(command, executable, pkg_ident)

                verified_path = ""
                if install_method == "dotnet_global_tool":
                    dotnet_info = resolve_dotnet_global_tool(pkg_ident, executable)
                    verified_path = dotnet_info.get("executable") or locate_executable(executable) or locate_executable(tool_name)
                elif install_method == "python_package":
                    py_tool_info = resolve_python_tool(pkg_ident, executable, sys.executable)
                    verified_path = py_tool_info.get("executable") or locate_executable(executable) or locate_executable(tool_name)
                else:
                    verified_path = locate_executable(executable) or locate_executable(tool_name)

                if verified_path:
                    v_cmd = f'"{verified_path}" --version'
                elif verify_command:
                    v_cmd = verify_command
                elif executable:
                    v_cmd = f'"{executable}" --version'
                else:
                    v_cmd = f'"{tool_name}" --version'

                print(f"[SmartInstall] Verification started: {v_cmd}")
                v_proc = subprocess.run(v_cmd, shell=True, capture_output=True, text=True, timeout=15)
                v_exit = v_proc.returncode
                v_stdout = v_proc.stdout.strip()
                v_stderr = v_proc.stderr.strip()
                print(f"[SmartInstall] Verification exit code: {v_exit}")

                self._last_installed_info = {
                    "tool_name": tool_name,
                    "command": command,
                    "executable": executable,
                    "package_name": pkg_ident,
                    "retry_action": retry_action,
                    "file_path": file_path,
                    "verify_command": v_cmd,
                    "verified_path": verified_path,
                    "install_exit": install_exit,
                    "install_stdout": stdout,
                    "install_stderr": stderr,
                    "verify_exit": v_exit,
                    "verify_stdout": v_stdout,
                    "verify_stderr": v_stderr
                }

                self.smartInstallProgress.emit(tool_name, "post_install_analyzing", "Running post-install AI verification...")

                status, fix_cmd, explanation = self.diagnose_post_install_result(
                    tool_name=tool_name,
                    command=command,
                    install_exit_code=install_exit,
                    install_stdout=stdout,
                    install_stderr=stderr,
                    verify_cmd=v_cmd,
                    verify_exit_code=v_exit,
                    verify_stdout=v_stdout,
                    verify_stderr=v_stderr,
                    executable=executable,
                    package_name=pkg_ident,
                    language="",
                    retry_action=retry_action,
                    file_path=file_path,
                    verified_path=verified_path,
                    fix_attempt_count=0,
                    is_post_fix=False
                )

                if status == "SUCCESS":
                    ver_str = (v_stdout or v_stderr or "OK").splitlines()[0] if (v_stdout or v_stderr) else "OK"
                    print(f"[SmartInstall] Verification result: success ({ver_str})")
                    print(f"[SmartInstall] Cache invalidation")
                    print(f"[SmartInstall] Environment refresh")
                    print(f"[SmartInstall] Original operation retry: {retry_action or 'none'}")

                    if verified_path and os.path.exists(verified_path):
                        tool_dir = os.path.dirname(os.path.abspath(verified_path))
                        if tool_dir and tool_dir not in os.environ.get("PATH", ""):
                            os.environ["PATH"] = tool_dir + os.pathsep + os.environ.get("PATH", "")
                        self._custom_paths[tool_name] = verified_path
                        if executable:
                            self._custom_paths[executable] = verified_path
                        self._save_custom_paths()
                        if hasattr(shutil, "_which_cache"):
                            shutil._which_cache.clear()
                        for ext in self._extensions.values():
                            if ext.formatter and isinstance(ext.formatter, dict):
                                cmd = ext.formatter.get("command") or ext.formatter.get("executable") or ""
                                if cmd in (tool_name, executable) or ext.name == tool_name:
                                    ext.custom_path = verified_path

                    self.invalidate_cache()
                    self.reload_extensions()

                    msg = f"{tool_name} installed and verified successfully! ({ver_str})"
                    if verified_path:
                        msg += f"\nLocation: {verified_path}"

                    print(f"[SmartInstall] Retry result: triggered")
                    self.smartInstallPostInstallVerified.emit(tool_name, "success", msg, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, True, msg, retry_action)

                elif status == "FIX":
                    # Prompt user with proposed fix
                    self.smartInstallFixProposed.emit(tool_name, fix_cmd, explanation, retry_action, file_path, v_cmd, 1)
                    self.smartInstallPostInstallVerified.emit(tool_name, "fix_available", explanation, retry_action, file_path, "")

                elif status == "MANUAL_INSTALLATION_REQUIRED":
                    print(f"[SmartInstall] Manual installation required for {tool_name}")
                    msg = explanation or "Manual installation is required."
                    self.smartInstallPostInstallVerified.emit(tool_name, "manual_installation_required", msg, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, False, msg, retry_action)

                else:
                    err_msg = explanation or stderr or stdout or f"Process exited with code {install_exit}"
                    print(f"[SmartInstall] Installation failed with exit code {install_exit}:\n{err_msg}")
                    self.smartInstallPostInstallVerified.emit(tool_name, "failed", err_msg, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, False, err_msg, retry_action)

            except Exception as e:
                print(f"[SmartInstall] Execution exception: {e}")
                self.smartInstallCompleted.emit(tool_name, False, f"Execution error: {e}", retry_action)
            finally:
                self._installing_tools.discard(tool_name)

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(str, str, str, str, str, str, int, result=bool)
    @Slot(str, str, str, str, str, str, result=bool)
    def execute_smart_install_fix(
        self,
        tool_name: str,
        fix_command: str,
        executable: str = "",
        retry_action: str = "",
        file_path: str = "",
        verify_command: str = "",
        fix_attempt_count: int = 1
    ) -> bool:
        """
        Executes an AI-suggested fix command after explicit user approval,
        re-verifies, refreshes subprocess runtime configuration, retries actual operation,
        and sends real execution results back to GPT for post-fix diagnosis.
        Enforces maximum 2 fix attempts per session to prevent infinite loops.
        """
        print("[SmartInstall] User approved AI fix")
        if not fix_command:
            self.smartInstallCompleted.emit(tool_name, False, "Cannot execute fix: fix command is empty.", retry_action)
            return False

        if fix_attempt_count > 2:
            print("[SmartInstall] Maximum fix attempts (2) reached -> manual installation required")
            self.smartInstallPostInstallVerified.emit(
                tool_name, "manual_installation_required",
                "Automated fix attempts reached the maximum limit (2). Manual installation is required.",
                retry_action, file_path, ""
            )
            self.smartInstallCompleted.emit(tool_name, False, "Maximum fix attempts reached.", retry_action)
            return False

        # Validate command safety
        is_safe, reason = self.validate_command_safety(fix_command, tool_name)
        if not is_safe:
            print(f"[SmartInstall] Execution blocked: {reason}")
            self.smartInstallCompleted.emit(tool_name, False, f"Execution halted: {reason}", retry_action)
            return False

        print("[SmartInstall] AI fix execution started")
        self.smartInstallProgress.emit(tool_name, "installing", f"Running AI suggested fix: {fix_command}")

        def _fix_worker():
            try:
                proc = subprocess.run(fix_command, shell=True, capture_output=True, text=True, timeout=300)
                fix_stdout = proc.stdout.strip()
                fix_stderr = proc.stderr.strip()
                fix_exit_code = proc.returncode

                print(f"[SmartInstall] AI fix exit code: {fix_exit_code}")
                print("[SmartInstall] Re-verification started")
                self.smartInstallProgress.emit(tool_name, "installing", "Re-verifying tool after fix...")

                pkg_ident = self._extract_package_from_command(fix_command, executable or tool_name)
                install_method = self._classify_install_method(fix_command, executable, pkg_ident)
                verified_path = ""
                if install_method == "dotnet_global_tool":
                    dotnet_info = resolve_dotnet_global_tool(pkg_ident, executable)
                    verified_path = dotnet_info.get("executable") or locate_executable(executable) or locate_executable(tool_name)
                elif install_method == "python_package":
                    py_tool_info = resolve_python_tool(pkg_ident, executable, sys.executable)
                    verified_path = py_tool_info.get("executable") or locate_executable(executable) or locate_executable(tool_name)
                else:
                    verified_path = locate_executable(executable) or locate_executable(tool_name)

                if verified_path:
                    v_cmd = f'"{verified_path}" --version'
                elif verify_command:
                    v_cmd = verify_command
                elif executable:
                    v_cmd = f'"{executable}" --version'
                else:
                    v_cmd = f'"{tool_name}" --version'

                v_proc = subprocess.run(v_cmd, shell=True, capture_output=True, text=True, timeout=15)
                v_exit_code = v_proc.returncode
                v_stdout = v_proc.stdout.strip()
                v_stderr = v_proc.stderr.strip()

                # Step 1-4: Post-fix runtime resolution for Java / OpenJDK if applicable
                is_java_fix = (
                    "openjdk" in fix_command.lower() or
                    "jdk" in fix_command.lower() or
                    "java" in tool_name.lower() or
                    "google-java-format" in tool_name.lower()
                )
                configured_new_runtime = False
                compat_jdk = None
                if is_java_fix:
                    print("[SmartInstall] Discovering newly installed compatible JDK directory...")
                    compat_jdk = find_compatible_jdk(min_version=21)
                    if compat_jdk:
                        jdk_path = compat_jdk["path"]
                        java_exe = compat_jdk["java_exe"]
                        jdk_ver = compat_jdk.get("version", "21+")
                        # Verify directly
                        try:
                            v_jdk = subprocess.run([java_exe, "-version"], capture_output=True, text=True, timeout=10)
                            v_jdk_txt = (v_jdk.stderr or v_jdk.stdout or "").strip()
                            print(f"[SmartInstall] Directly verified installed runtime: {v_jdk_txt}")
                        except Exception as ej:
                            print(f"[SmartInstall] Direct verification notice: {ej}")

                        # Refresh DGX subprocess runtime environment
                        self.set_java_runtime_config({
                            "JAVA_HOME": jdk_path,
                            "java_path": java_exe,
                            "version": jdk_ver
                        })
                        self.set_tool_runtime_config(tool_name, {
                            "JAVA_HOME": jdk_path,
                            "java_path": java_exe,
                            "version": jdk_ver,
                            "PATH_PREPEND": os.path.dirname(java_exe)
                        })
                        configured_new_runtime = True
                        print(f"[SmartInstall] Refreshed formatter environment to use compatible JDK at {jdk_path}")

                # Step 5: Retry actual operation and capture real result
                op_exit_code = 0
                op_stdout = ""
                op_stderr = ""
                if retry_action == "format" or tool_name == "google-java-format":
                    self.smartInstallProgress.emit(tool_name, "retrying", "Retrying actual operation with updated runtime...")
                    sample_java = "class Test { public static void main(String[] args){ System.out.println(1); }}"
                    if self._formatter_manager:
                        fmt_res = self._formatter_manager.format_code(sample_java, "java", 4, file_path or "Test.java")
                        if fmt_res.get("success"):
                            op_exit_code = 0
                            op_stdout = fmt_res.get("message", "Formatted successfully")
                            op_stderr = ""
                        else:
                            op_exit_code = 1
                            op_stderr = fmt_res.get("message", "Formatting failed")
                    else:
                        f_exe = verified_path or locate_executable(executable) or locate_executable(tool_name)
                        if f_exe:
                            test_env = os.environ.copy()
                            if configured_new_runtime and compat_jdk:
                                test_env["JAVA_HOME"] = compat_jdk["path"]
                                test_env["PATH"] = os.path.dirname(compat_jdk["java_exe"]) + os.pathsep + test_env.get("PATH", "")
                            f_proc = subprocess.run([f_exe, "--version"], capture_output=True, text=True, env=test_env, timeout=10)
                            op_exit_code = f_proc.returncode
                            op_stdout = f_proc.stdout.strip()
                            op_stderr = f_proc.stderr.strip()

                print(f"[SmartInstall] Retried operation real result: exit {op_exit_code}, error: {op_stderr or 'none'}")
                print("[SmartInstall] Post-fix AI analysis started")
                status, next_fix_cmd, explanation = self.diagnose_post_install_result(
                    tool_name=tool_name,
                    command=fix_command,
                    install_exit_code=fix_exit_code,
                    install_stdout=fix_stdout,
                    install_stderr=fix_stderr,
                    verify_cmd=v_cmd,
                    verify_exit_code=v_exit_code,
                    verify_stdout=v_stdout,
                    verify_stderr=v_stderr,
                    executable=executable,
                    package_name=pkg_ident,
                    retry_action=retry_action,
                    file_path=file_path,
                    verified_path=verified_path,
                    fix_attempt_count=fix_attempt_count,
                    is_post_fix=True,
                    operation_attempted=retry_action or "format",
                    operation_exit_code=op_exit_code,
                    operation_stdout=op_stdout,
                    operation_stderr=op_stderr,
                    operation_error=op_stderr
                )
                print(f"[SmartInstall] Post-fix AI result: {status}")

                if status == "SUCCESS":
                    if verified_path and os.path.exists(verified_path):
                        tool_dir = os.path.dirname(os.path.abspath(verified_path))
                        if tool_dir and tool_dir not in os.environ.get("PATH", ""):
                            os.environ["PATH"] = tool_dir + os.pathsep + os.environ.get("PATH", "")
                        self._custom_paths[tool_name] = verified_path
                        if executable:
                            self._custom_paths[executable] = verified_path
                        self._save_custom_paths()
                        if hasattr(shutil, "_which_cache"):
                            shutil._which_cache.clear()
                        for ext in self._extensions.values():
                            if ext.formatter and isinstance(ext.formatter, dict):
                                cmd = ext.formatter.get("command") or ext.formatter.get("executable") or ""
                                if cmd in (tool_name, executable) or ext.name == tool_name:
                                    ext.custom_path = verified_path

                    self.invalidate_cache()
                    self.reload_extensions()
                    ver_str = (v_stdout or v_stderr or "OK").splitlines()[0] if (v_stdout or v_stderr) else "OK"
                    msg = f"{tool_name} installed, configured, and operational after fix! ({ver_str})"
                    self.smartInstallPostInstallVerified.emit(tool_name, "success", msg, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, True, msg, retry_action)
                elif status == "FIX":
                    if fix_attempt_count >= 2:
                        print("[SmartInstall] Maximum fix attempts (2) reached -> manual installation required")
                        msg = "Automated fix attempts reached the maximum limit (2). Manual installation is required."
                        self.smartInstallPostInstallVerified.emit(tool_name, "manual_installation_required", msg, retry_action, file_path, "")
                        self.smartInstallCompleted.emit(tool_name, False, msg, retry_action)
                    else:
                        self.smartInstallFixProposed.emit(tool_name, next_fix_cmd, explanation, retry_action, file_path, v_cmd, fix_attempt_count + 1)
                        self.smartInstallPostInstallVerified.emit(tool_name, "fix_available", explanation, retry_action, file_path, "")
                elif status == "MANUAL_INSTALLATION_REQUIRED":
                    self.smartInstallPostInstallVerified.emit(tool_name, "manual_installation_required", explanation, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, False, explanation, retry_action)
                else:
                    err_msg = explanation or op_stderr or fix_stderr or f"Operation failed with code {op_exit_code}"
                    self.smartInstallPostInstallVerified.emit(tool_name, "failed", err_msg, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, False, err_msg, retry_action)

            except Exception as e:
                print(f"[SmartInstall] Fix execution exception: {e}")
                self.smartInstallCompleted.emit(tool_name, False, f"Fix error: {e}", retry_action)
            finally:
                self._installing_tools.discard(tool_name)

        threading.Thread(target=_fix_worker, daemon=True).start()
        return True

    @Slot(str, str, str, str, str)
    @Slot(str, str, str, str)
    @Slot(str, str, str)
    @Slot(str, str)
    def diagnose_operation_failure(
        self,
        tool_name: str,
        error_message: str,
        retry_action: str = "",
        file_path: str = "",
        language: str = ""
    ):
        """
        Diagnoses operational failure of an installed & verified tool.
        Identifies runtime incompatibilities and recommends safe fixes (e.g. compatible JDK).
        """
        print(f"[SmartInstall] Diagnosing operational failure for {tool_name}: {error_message}")
        self.smartInstallAnalysisStarted.emit(tool_name)

        # 1. First check if a compatible runtime is ALREADY installed on disk
        reconfigured, reconf_msg = self.ensure_tool_runtime_compatibility(tool_name, language)
        if reconfigured and "Configured" in reconf_msg:
            print(f"[SmartInstall] Auto-resolved runtime mismatch: {reconf_msg}")
            msg = f"{tool_name} configured to use compatible runtime on disk ({reconf_msg}). Retrying operation..."
            self.smartInstallProgress.emit(tool_name, "retrying", msg)
            self.smartInstallPostInstallVerified.emit(tool_name, "success", msg, retry_action, file_path, language)
            return

        def _diag_worker():
            try:
                last_info = getattr(self, "_last_installed_info", {})
                last_cmd = last_info.get("command", f"install {tool_name}")
                v_cmd = last_info.get("verify_command", f"{tool_name} --version")
                v_path = last_info.get("verified_path", "")

                status, fix_cmd, explanation = self.diagnose_post_install_result(
                    tool_name=tool_name,
                    command=last_cmd,
                    install_exit_code=0,
                    install_stdout="Successfully installed",
                    install_stderr="",
                    verify_cmd=v_cmd,
                    verify_exit_code=0,
                    verify_stdout=f"{tool_name} verified",
                    verify_stderr="",
                    executable=tool_name,
                    package_name=last_info.get("package_name", tool_name),
                    language=language,
                    retry_action=retry_action,
                    file_path=file_path,
                    verified_path=v_path,
                    fix_attempt_count=0,
                    is_post_fix=False,
                    operation_attempted=retry_action or "format",
                    operation_exit_code=1,
                    operation_stderr=error_message,
                    operation_error=error_message
                )

                if status == "FIX":
                    self.smartInstallFixProposed.emit(tool_name, fix_cmd, explanation, retry_action, file_path, v_cmd, 1)
                    self.smartInstallPostInstallVerified.emit(tool_name, "fix_available", explanation, retry_action, file_path, "")
                elif status == "MANUAL_INSTALLATION_REQUIRED":
                    self.smartInstallPostInstallVerified.emit(tool_name, "manual_installation_required", explanation, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, False, explanation, retry_action)
                elif status == "SUCCESS":
                    self.smartInstallCompleted.emit(tool_name, True, explanation, retry_action)
                else:
                    self.smartInstallPostInstallVerified.emit(tool_name, "failed", explanation or error_message, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, False, explanation or error_message, retry_action)
            except Exception as e:
                print(f"[SmartInstall] Diagnosis error: {e}")
                self.smartInstallPostInstallVerified.emit(tool_name, "failed", str(e), retry_action, file_path, "")
                self.smartInstallCompleted.emit(tool_name, False, str(e), retry_action)

        threading.Thread(target=_diag_worker, daemon=True).start()

    @Slot(str, bool, str, str, str, str)
    @Slot(str, bool, str, str, str)
    @Slot(str, bool, str, str)
    @Slot(str, bool, str)
    @Slot(str, bool)
    def report_retry_result(self, tool_name: str, success: bool, error_message: str = "", retry_action: str = "", file_path: str = "", language: str = ""):
        """Reports whether the original operation succeeded or failed after post-install verification."""
        print(f"[SmartInstall] Retry result: {'success' if success else 'failed'} ({error_message})")
        self.originalOperationRetried.emit(tool_name, success, error_message)
        if not success:
            self.diagnose_operation_failure(tool_name, error_message, retry_action, file_path, language)

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

    @Slot(str, result=str)
    @Slot(str, str, result=str)
    def locate_executable(self, cmd: str, custom_path: Optional[str] = None) -> str:
        res = locate_executable(cmd, custom_path)
        return res if res else ""

    @Slot(str, result=bool)
    @Slot(str, str, result=bool)
    def is_executable_installed(self, cmd: str, custom_path: Optional[str] = None) -> bool:
        return bool(locate_executable(cmd, custom_path))

    @Slot(str, str, str, result="QVariantMap")
    @Slot(str, str, result="QVariantMap")
    @Slot(str, result="QVariantMap")
    def resolve_python_tool(self, package_name: str, executable_name: str = "", python_executable: str = "") -> dict:
        return resolve_python_tool(package_name, executable_name, python_executable or sys.executable)

    @Slot(str, str, str, result="QVariantMap")
    @Slot(str, str, result="QVariantMap")
    @Slot(str, result="QVariantMap")
    def resolve_dotnet_global_tool(self, package_name: str, executable_name: str = "", dotnet_executable: str = "") -> dict:
        return resolve_dotnet_global_tool(package_name, executable_name, dotnet_executable or "")

    @Slot()
    def invalidate_cache(self):
        """Invalidates all cached executable paths and reloads extensions."""
        self._custom_paths = self._load_custom_paths()
        self.reload_extensions()

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
