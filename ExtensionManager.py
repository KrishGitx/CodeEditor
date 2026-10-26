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
import datetime
import urllib.request
import urllib.error
import hashlib
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


def _sanitize_secrets(text: str) -> str:
    """Redacts tokens, API keys, credentials, and passwords from logs."""
    if not text:
        return ""
    sanitized = re.sub(r'(Bearer\s+)[a-zA-Z0-9_\-\.]{10,}', r'\1[REDACTED]', text, flags=re.IGNORECASE)
    sanitized = re.sub(r'(sk-[a-zA-Z0-9_\-\.]{15,})', r'[REDACTED_API_KEY]', sanitized)
    sanitized = re.sub(r'((?:api[_-]?key|password|secret|token)\s*[:=]\s*["\']?)([^"\'\s,;]{4,})(["\']?)', r'\1[REDACTED]\3', sanitized, flags=re.IGNORECASE)
    return sanitized


def _log_si(stage: str, message: str, run_id: str = "", details: Optional[Dict[str, Any]] = None) -> None:
    """Emits structured, timestamped Smart Install console logs with stage labels."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    run_str = f"[{run_id}] " if run_id else ""
    clean_msg = _sanitize_secrets(message)
    print(f"[SmartInstall] [{ts}] {run_str}[{stage}] {clean_msg}")
    if details:
        for k, v in details.items():
            val_str = _sanitize_secrets(str(v))
            if len(val_str) > 400:
                val_str = val_str[:400] + "... (truncated)"
            print(f"[SmartInstall] [{ts}] {run_str}  -> {k}: {val_str}")


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
        elif cmd_l in ("sqlcmd", "sqlcmd.exe"):
            sqlcmd_globs = [
                r"C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\*\Tools\Binn\sqlcmd.exe",
                r"C:\Program Files (x86)\Microsoft SQL Server\Client SDK\ODBC\*\Tools\Binn\sqlcmd.exe",
                r"C:\Program Files\Microsoft SQL Server\*\Tools\Binn\sqlcmd.exe",
                r"C:\Program Files (x86)\Microsoft SQL Server\*\Tools\Binn\sqlcmd.exe",
                r"C:\Program Files\SqlCmd\sqlcmd.exe",
                r"C:\Program Files (x86)\SqlCmd\sqlcmd.exe",
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "sqlcmd", "sqlcmd.exe"),
            ]
            for pattern in sqlcmd_globs:
                for match in glob.glob(pattern):
                    if os.path.isfile(match):
                        return os.path.abspath(match)
        elif cmd_l in ("psql", "psql.exe"):
            psql_globs = [
                r"C:\Program Files\PostgreSQL\*\bin\psql.exe",
                r"C:\Program Files (x86)\PostgreSQL\*\bin\psql.exe",
            ]
            for pattern in psql_globs:
                for match in glob.glob(pattern):
                    if os.path.isfile(match):
                        return os.path.abspath(match)
        elif cmd_l in ("sqlite3", "sqlite3.exe"):
            sqlite_paths = [
                r"C:\sqlite\sqlite3.exe",
                r"C:\Program Files\SQLite\sqlite3.exe",
                r"C:\Program Files (x86)\SQLite\sqlite3.exe",
            ]
            for sp in sqlite_paths:
                if os.path.isfile(sp):
                    return os.path.abspath(sp)
        elif cmd_l in ("mysql", "mysql.exe"):
            mysql_globs = [
                r"C:\Program Files\MySQL\MySQL Server *\bin\mysql.exe",
                r"C:\Program Files\MySQL\MySQL Workbench *\mysql.exe",
            ]
            for pattern in mysql_globs:
                for match in glob.glob(pattern):
                    if os.path.isfile(match):
                        return os.path.abspath(match)

        # Check Windows Registry Machine/User PATH for newly installed tools not yet in current process PATH
        try:
            import winreg
            for root_key, subkey in [
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                (winreg.HKEY_CURRENT_USER, r"Environment")
            ]:
                try:
                    with winreg.OpenKey(root_key, subkey) as key:
                        val, _ = winreg.QueryValueEx(key, "Path")
                        for dir_path in val.split(";"):
                            dir_path = dir_path.strip()
                            if dir_path and os.path.isdir(dir_path):
                                target = os.path.join(dir_path, bin_name)
                                if os.path.isfile(target):
                                    return os.path.abspath(target)
                except Exception:
                    pass
        except Exception:
            pass

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

_test_discovered_jdks: Optional[List[Dict[str, Any]]] = None
_test_active_java_info: Optional[Dict[str, Any]] = None


def set_test_java_environment(active_info: Optional[Dict[str, Any]] = None, discovered_jdks: Optional[List[Dict[str, Any]]] = None):
    """Allows regression and unit tests to inject deterministic runtime environments."""
    global _test_active_java_info, _test_discovered_jdks
    _test_active_java_info = active_info
    _test_discovered_jdks = list(discovered_jdks) if discovered_jdks is not None else None


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
    if _test_discovered_jdks is not None:
        return list(_test_discovered_jdks)

    discovered = []
    seen_dirs = set()

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
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"),
            os.path.join(os.path.expanduser("~"), ".dgx", "tools")
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

    # 4. Database-related tools and diagnostics
    elif l_lower == "sql" or any(k in t_lower for k in ("sqlcmd", "psql", "sqlite", "mysql", "sql")):
        info["runtime_type"] = "Database"
        db_target = ExtensionManager.detect_target_database_engine({"language": language, "toolName": tool_name, "executable": executable}, "")
        info["database_engine"] = db_target.get("engine")
        info["database_client"] = db_target.get("client_tool") or tool_name
        found_db_exe = locate_executable(executable or tool_name or db_target.get("client_tool", ""))
        info["runtime_executable"] = found_db_exe or "Not found in PATH"
        if found_db_exe and os.path.isfile(found_db_exe):
            info["in_path"] = bool(shutil.which(tool_name) or shutil.which(executable))
            info["executable_path"] = found_db_exe
            info["executable_dir"] = os.path.dirname(found_db_exe)

    return info


# ==============================================================================
# COMMAND-FIRST INSTALLATION POLICY & PORTABLE RUNTIME INFRASTRUCTURE
# ==============================================================================

OFFICIAL_TOOL_DOCUMENTATION: Dict[str, Dict[str, str]] = {
    "google-java-format": {
        "tool": "google-java-format",
        "official_url": "https://github.com/google/google-java-format",
        "download_url": "https://github.com/google/google-java-format/releases",
        "runtime_name": "Microsoft OpenJDK 21",
        "runtime_url": "https://learn.microsoft.com/en-us/java/openjdk/download#openjdk-21",
        "action_required": "Install JDK 21+ and ensure google-java-format is available in your environment.",
        "verification_cmd": "google-java-format --version",
        "resume_note": "Smart Install will automatically detect the installed JDK 21 or google-java-format and resume formatting."
    },
    "openjdk": {
        "tool": "openjdk",
        "official_url": "https://learn.microsoft.com/en-us/java/openjdk/",
        "download_url": "https://learn.microsoft.com/en-us/java/openjdk/download#openjdk-21",
        "runtime_name": "Microsoft OpenJDK 21",
        "runtime_url": "https://learn.microsoft.com/en-us/java/openjdk/download#openjdk-21",
        "action_required": "Download and run the official Microsoft OpenJDK 21 installer or extract the zip archive.",
        "verification_cmd": "java -version",
        "resume_note": "Smart Install will automatically detect the compatible JDK and resume the operation."
    },
    "rustfmt": {
        "tool": "rustfmt",
        "official_url": "https://github.com/rust-lang/rustfmt",
        "download_url": "https://rustup.rs/",
        "runtime_name": "Rust toolchain",
        "runtime_url": "https://rustup.rs/",
        "action_required": "Install rustup from the official website and run 'rustup component add rustfmt'.",
        "verification_cmd": "rustfmt --version",
        "resume_note": "Smart Install will detect rustfmt as soon as it is installed."
    },
    "clang-format": {
        "tool": "clang-format",
        "official_url": "https://clang.llvm.org/docs/ClangFormat.html",
        "download_url": "https://github.com/llvm/llvm-project/releases",
        "runtime_name": "LLVM",
        "runtime_url": "https://github.com/llvm/llvm-project/releases",
        "action_required": "Install LLVM from the official release page or via your package manager.",
        "verification_cmd": "clang-format --version",
        "resume_note": "Smart Install will detect clang-format on PATH."
    },
    "csharpier": {
        "tool": "csharpier",
        "official_url": "https://csharpier.com/",
        "download_url": "https://csharpier.com/docs/Installation",
        "runtime_name": ".NET SDK",
        "runtime_url": "https://dotnet.microsoft.com/download",
        "action_required": "Install the .NET SDK and run 'dotnet tool install -g csharpier'.",
        "verification_cmd": "dotnet-csharpier --version",
        "resume_note": "Smart Install will format C# code once CSharpier is installed."
    },
    "prettier": {
        "tool": "prettier",
        "official_url": "https://prettier.io/",
        "download_url": "https://prettier.io/docs/en/install.html",
        "runtime_name": "Node.js",
        "runtime_url": "https://nodejs.org/",
        "action_required": "Install Node.js and run 'npm install -g prettier'.",
        "verification_cmd": "prettier --version",
        "resume_note": "Smart Install will detect Prettier once npm installation completes."
    },
    "black": {
        "tool": "black",
        "official_url": "https://black.readthedocs.io/",
        "download_url": "https://pypi.org/project/black/",
        "runtime_name": "Python",
        "runtime_url": "https://www.python.org/downloads/",
        "action_required": "Run 'pip install black' in your active Python environment.",
        "verification_cmd": "black --version",
        "resume_note": "Smart Install will detect Black in your active Python environment."
    },
    "sqlcmd": {
        "tool": "sqlcmd",
        "official_url": "https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility",
        "download_url": "https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility#download-and-install-sqlcmd",
        "runtime_name": "Microsoft Command Line Utilities for SQL Server",
        "action_required": "Install Microsoft sqlcmd client and configure target SQL Server connection.",
        "verification_cmd": "sqlcmd -?",
        "resume_note": "Smart Install will detect sqlcmd and retry the SQL operation against configured SQL Server."
    },
    "psql": {
        "tool": "psql",
        "official_url": "https://www.postgresql.org/docs/current/app-psql.html",
        "download_url": "https://www.postgresql.org/download/",
        "runtime_name": "PostgreSQL Client Utilities",
        "action_required": "Install PostgreSQL client (psql) and configure target database connection.",
        "verification_cmd": "psql --version",
        "resume_note": "Smart Install will detect psql and retry the SQL operation against PostgreSQL database."
    },
    "sqlite3": {
        "tool": "sqlite3",
        "official_url": "https://www.sqlite.org/",
        "download_url": "https://www.sqlite.org/download.html",
        "runtime_name": "SQLite Command-Line Shell",
        "action_required": "Install SQLite command line shell (sqlite3).",
        "verification_cmd": "sqlite3 --version",
        "resume_note": "Smart Install will detect sqlite3 and execute the SQL file."
    },
    "mysql": {
        "tool": "mysql",
        "official_url": "https://dev.mysql.com/doc/refman/8.0/en/mysql.html",
        "download_url": "https://dev.mysql.com/downloads/installer/",
        "runtime_name": "MySQL Client Utilities",
        "action_required": "Install MySQL client (mysql) and configure database connection.",
        "verification_cmd": "mysql --version",
        "resume_note": "Smart Install will detect mysql and retry the SQL operation."
    }
}


def get_official_manual_fallback(tool_name: str, reason: str = "") -> Dict[str, Any]:
    """
    Returns verified official vendor documentation, download link, required user actions,
    and verification commands. Never fabricates URLs.
    """
    clean_t = (tool_name or "").lower().strip()
    info = OFFICIAL_TOOL_DOCUMENTATION.get(clean_t)
    if not info:
        for k, v in OFFICIAL_TOOL_DOCUMENTATION.items():
            if k in clean_t:
                info = v
                break
    if not info:
        info = {
            "tool": tool_name,
            "official_url": f"https://github.com/search?q={tool_name}",
            "download_url": "",
            "action_required": f"Install {tool_name} using your system's package manager or official installer.",
            "verification_cmd": f"{tool_name} --version",
            "resume_note": f"DGX Studio will automatically detect {tool_name} once it is available on PATH."
        }

    return {
        "toolName": tool_name,
        "resolutionType": "manual_installation_required",
        "resolution_type": "manual_installation_required",
        "title": f"Manual Installation Required: {tool_name}",
        "reason": reason or "No automated command-line installation is available or automated install was blocked.",
        "explanation": reason or "Interactive installer or administrator privileges required.",
        "officialUrl": info.get("official_url", ""),
        "downloadUrl": info.get("download_url", ""),
        "runtimeUrl": info.get("runtime_url", ""),
        "actionRequired": info.get("action_required", ""),
        "verificationCommand": info.get("verification_cmd", f"{tool_name} --version"),
        "resumeNote": info.get("resume_note", "Smart Install will automatically detect the dependency once available."),
        "command": "",
        "steps": [],
        "source": "manual_fallback"
    }


def make_command_non_interactive(command: str) -> str:
    """
    Ensures package manager commands include documented silent or non-interactive flags.
    Only uses documented options supported by the specific package manager.
    """
    if not command:
        return ""
    cmd = command.strip()
    cmd_lower = cmd.lower()

    # winget: official non-interactive & silent flags
    if "winget install" in cmd_lower:
        if "--accept-source-agreements" not in cmd_lower:
            cmd += " --accept-source-agreements"
        if "--accept-package-agreements" not in cmd_lower:
            cmd += " --accept-package-agreements"
        if "--silent" not in cmd_lower and "--disable-interactivity" not in cmd_lower:
            cmd += " --silent"

    # choco: official non-interactive flags
    elif "choco install" in cmd_lower:
        if "-y" not in cmd.split() and "--yes" not in cmd.split():
            cmd += " -y"
        if "--no-progress" not in cmd_lower:
            cmd += " --no-progress"

    # pip: official quiet & no-input flags
    elif "pip install" in cmd_lower or "pip3 install" in cmd_lower:
        if "--no-input" not in cmd_lower:
            cmd += " --no-input"

    return cmd


_test_installer_in_progress_fn: Optional[Callable[[], bool]] = None


def set_test_installer_in_progress(fn: Optional[Callable[[], bool]]):
    """Allows unit/regression tests to simulate an active Windows Installer lock."""
    global _test_installer_in_progress_fn
    _test_installer_in_progress_fn = fn


def is_installer_in_progress() -> bool:
    """Checks whether another Windows Installer process (msiexec.exe) is currently active."""
    global _test_installer_in_progress_fn
    if _test_installer_in_progress_fn is not None:
        try:
            if callable(_test_installer_in_progress_fn):
                return bool(_test_installer_in_progress_fn())
            return bool(_test_installer_in_progress_fn)
        except Exception:
            return False

    if sys.platform != "win32":
        return False
    try:
        proc = subprocess.run(["tasklist", "/FI", "IMAGENAME eq msiexec.exe", "/NH"], capture_output=True, text=True, timeout=5)
        return "msiexec.exe" in proc.stdout.lower()
    except Exception:
        return False


def wait_for_installer_lock(timeout: int = 60, progress_cb: Optional[Callable[[str], None]] = None, run_id: str = "") -> bool:
    """
    Waits for an existing Windows Installer process to release without terminating unrelated processes.
    Keeps application responsive by polling in 1s intervals with progress updates.
    Returns True if installer cleared within timeout, False if timed out.
    """
    if not is_installer_in_progress():
        return True

    print(f"[SmartInstall] Windows Installer is currently active. Waiting up to {timeout}s for lock release...")
    _log_si("INSTALLER_LOCK", f"Detected active Windows Installer process. Waiting up to {timeout}s for release without terminating unrelated processes.", run_id=run_id, details={"timeout_seconds": timeout})
    if progress_cb:
        progress_cb(f"Another installation is currently in progress. Waiting for Windows Installer (up to {timeout}s)...")

    waited = 0
    while is_installer_in_progress() and waited < timeout:
        time.sleep(1.0)
        waited += 1
        if waited % 5 == 0 and progress_cb:
            progress_cb(f"Waiting for Windows Installer to finish ({waited}/{timeout}s)...")

    cleared = not is_installer_in_progress()
    if cleared:
        print(f"[SmartInstall] Windows Installer lock released after {waited}s.")
        _log_si("INSTALLER_RELEASED", f"Windows Installer lock cleared after {waited}s.", run_id=run_id, details={"wait_duration": waited})
    else:
        print(f"[SmartInstall] Windows Installer lock wait timed out after {timeout}s.")
        _log_si("INSTALLER_TIMEOUT", f"Windows Installer lock wait timed out after {timeout}s. Halting without terminating unrelated processes.", run_id=run_id, details={"timeout_seconds": timeout})
    return cleared


_test_portable_download_hook: Optional[Callable[[str, str], bool]] = None


def set_test_portable_download_hook(hook: Optional[Callable[[str, str], bool]]):
    """Allows unit/regression tests to inject portable archive download mocks."""
    global _test_portable_download_hook
    _test_portable_download_hook = hook


def get_managed_tools_dir() -> str:
    """Returns the dedicated managed tools directory (~/.dgx/tools/)."""
    path = os.path.join(os.path.expanduser("~"), ".dgx", "tools")
    os.makedirs(path, exist_ok=True)
    return path


def install_portable_runtime(
    tool_name: str,
    min_version: int = 21,
    run_id: str = "",
    download_url_override: Optional[str] = None
) -> Tuple[bool, str, str, str]:
    """
    Downloads and extracts an official portable archive into a managed directory.
    Verifies source, target architecture, and archive integrity.
    Configures tool runtime explicitly without changing global system PATH or JAVA_HOME.
    Returns (success, executable_path, version_str, error_message).
    """
    arch = platform.machine()
    is_win = sys.platform.startswith("win")
    if not is_win or arch not in ("AMD64", "x86_64", "arm64"):
        return False, "", "", f"Portable installation not supported for {sys.platform} on {arch}."

    # Official Microsoft OpenJDK 21 portable zip URL for Windows x64
    official_url = download_url_override or "https://aka.ms/download-jdk/microsoft-jdk-21.0.6-windows-x64.zip"

    tools_dir = get_managed_tools_dir()
    target_extract_dir = os.path.join(tools_dir, f"{tool_name}-{min_version}")
    temp_zip = os.path.join(tools_dir, f"{tool_name}_{min_version}_temp.zip")

    _log_si(
        "PORTABLE_DOWNLOAD_START",
        f"Starting download of official portable archive for '{tool_name}'",
        run_id=run_id,
        details={"tool": tool_name, "url": official_url, "architecture": arch, "target_dir": target_extract_dir}
    )

    try:
        # Download archive
        if _test_portable_download_hook is not None:
            ok = _test_portable_download_hook(official_url, temp_zip)
            if not ok:
                raise RuntimeError("Portable download hook reported failure or blocked network.")
        else:
            req = urllib.request.Request(
                official_url,
                headers={"User-Agent": "DGX-Studio-SmartInstall/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp, open(temp_zip, "wb") as out_f:
                shutil.copyfileobj(resp, out_f)

        # Integrity verification
        if not os.path.isfile(temp_zip) or os.path.getsize(temp_zip) < 100:
            return False, "", "", "Archive integrity verification failed: downloaded file is empty or corrupted."

        if not zipfile.is_zipfile(temp_zip):
            return False, "", "", "Archive integrity verification failed: not a valid zip archive."

        # Safe extraction
        os.makedirs(target_extract_dir, exist_ok=True)
        with zipfile.ZipFile(temp_zip, "r") as zf:
            for member in zf.infolist():
                # Prevent zip slip path traversal
                dest_path = os.path.normpath(os.path.join(target_extract_dir, member.filename))
                if not dest_path.startswith(os.path.abspath(target_extract_dir)):
                    raise RuntimeError(f"Zip slip path traversal hazard detected in archive: {member.filename}")
            zf.extractall(target_extract_dir)

        # Clean temp zip
        try:
            if os.path.isfile(temp_zip):
                os.remove(temp_zip)
        except Exception:
            pass

        # Locate executable inside extracted directory
        exe_name = "java.exe" if is_win else "java"
        resolved_exe = ""
        bin_dir = ""
        for root, dirs, files in os.walk(target_extract_dir):
            if exe_name in files and os.path.basename(root).lower() == "bin":
                candidate = os.path.join(root, exe_name)
                if os.path.isfile(candidate):
                    resolved_exe = os.path.abspath(candidate)
                    bin_dir = os.path.abspath(root)
                    break

        if not resolved_exe:
            return False, "", "", f"Failed to locate {exe_name} inside extracted portable directory."

        # Verify executable and version
        ver_proc = subprocess.run([resolved_exe, "-version"], capture_output=True, text=True, timeout=10)
        ver_out = (ver_proc.stderr or ver_proc.stdout or "").strip()
        ver_match = re.search(r'version\s+"([0-9]+(?:\.[0-9]+)*)', ver_out, re.IGNORECASE)
        version_str = ver_match.group(1) if ver_match else "21.0.0"
        major_ver = int(version_str.split(".")[0]) if version_str else 21

        if major_ver < min_version:
            return False, "", "", f"Extracted runtime version ({version_str}) does not satisfy required minimum {min_version}."

        home_dir = os.path.dirname(bin_dir)
        _log_si(
            "PORTABLE_INSTALL_SUCCESS",
            f"Successfully installed and verified portable runtime for '{tool_name}' ({version_str})",
            run_id=run_id,
            details={"executable": resolved_exe, "version": version_str, "location": home_dir, "non_interactive": True}
        )
        return True, resolved_exe, version_str, ""

    except Exception as e:
        err_msg = str(e)
        _log_si("PORTABLE_ERROR", f"Portable runtime installation failed: {err_msg}", run_id=run_id, details={"error": err_msg})
        try:
            if os.path.isfile(temp_zip):
                os.remove(temp_zip)
        except Exception:
            pass
        return False, "", "", err_msg


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



# =============================================================================
# SMART AI ENGINE & RECOVERY ARCHITECTURE INTEGRATION
# =============================================================================
from smart_engine import (
    SmartEngine,
    RecoverySession,
    SmartAction,
    CommandRecord,
    SmartSafetyGuard,
    ActionRegistry,
    SMART_AI_SYSTEM_PROMPT,
    build_smart_prompt,
    parse_smart_response,
    validate_ai_plan_response
)


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
    smartFixAvailable = Signal("QVariantMap")  # structured Smart Fix proposal for background error recovery
    recoveryPlanUpdated = Signal("QVariantMap")  # structured session data, current batch, total steps, status
    recoveryCommandStarted = Signal(str, str, str)  # session_id, command_id, command
    recoveryCommandCompleted = Signal(str, str, int, str)  # session_id, command_id, exit_code, formatted_output
    recoverySessionEnded = Signal(str, bool, str)  # session_id, success, final_report
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
        self._formatter_manager = None
        self._attempted_fix_commands: Dict[str, List[str]] = {}
        self._active_run_ids: Dict[str, str] = {}
        self._recent_failure_fingerprints: Dict[str, float] = {}
        self._smart_engine = SmartEngine(extension_manager=self)
        self._recovery_sessions = self._smart_engine._sessions
        self._active_recovery_session_id: Optional[str] = None

        self.reload_extensions()

    def set_formatter_manager(self, formatter_manager) -> None:
        """Injects the FormatterManager instance into the extension manager."""
        self._formatter_manager = formatter_manager

    def _get_run_id(self, tool_name: str, fallback_prefix: str = "si") -> str:
        if not hasattr(self, "_active_run_ids") or not isinstance(self._active_run_ids, dict):
            self._active_run_ids = {}
        return self._active_run_ids.get(tool_name) or f"{fallback_prefix}_{tool_name}_{int(time.time()*1000)%1000000}"

    def _set_run_id(self, tool_name: str, run_id: str):
        if not hasattr(self, "_active_run_ids") or not isinstance(self._active_run_ids, dict):
            self._active_run_ids = {}
        self._active_run_ids[tool_name] = run_id

    @property
    def formatter_manager(self):
        """Returns the configured FormatterManager or attempts fallback via editor_backend."""
        if self._formatter_manager is not None:
            return self._formatter_manager
        if self.editor_backend is not None and hasattr(self.editor_backend, "formatter_manager"):
            return self.editor_backend.formatter_manager
        return None

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
    def execute_command_steps(
        self,
        command_str: str,
        tool_name: str = "",
        timeout: int = 300,
        working_dir: Optional[str] = None,
        run_id: str = ""
    ) -> Tuple[int, str, str, List[dict]]:
        """
        Executes a command or multi-step command sequence safely and sequentially.
        Supports multi-line commands and '&&' chained commands.
        Preserves environment updates (such as newly activated virtualenvs or path additions)
        across sequential steps.
        Stops immediately on the first failed step and returns detailed execution info.
        """
        if isinstance(command_str, list):
            raw_lines = [str(x) for x in command_str]
        else:
            raw = (command_str or "").strip()
            raw_lines = raw.splitlines()
        steps: List[str] = []
        for line in raw_lines:
            substeps = [s.strip() for s in line.split("&&") if s.strip()]
            steps.extend(substeps)

        if not steps:
            return 1, "", "No executable commands provided.", []

        # Validate each individual step for safety
        for step in steps:
            is_safe, reason = self.validate_command_safety(step, tool_name)
            if not is_safe:
                return 1, "", f"Command rejected: {reason}", []

        env = os.environ.copy()
        aggregated_stdout: List[str] = []
        aggregated_stderr: List[str] = []
        step_results: List[dict] = []
        final_exit = 0

        for idx, orig_step in enumerate(steps):
            step = make_command_non_interactive(orig_step)
            print(f"[SmartInstall] Executing step {idx + 1}/{len(steps)}: {step}")
            _log_si(
                "CMD_PREPARE",
                f"Preparing command step {idx + 1}/{len(steps)}: '{step}'",
                run_id=run_id,
                details={
                    "step_index": idx + 1,
                    "total_steps": len(steps),
                    "command": step,
                    "working_directory": working_dir or os.getcwd(),
                    "timeout_seconds": timeout,
                    "non_interactive": True
                }
            )

            # Check for Windows Installer mutex before launching installer tools
            if sys.platform == "win32" and any(k in step.lower() for k in ("winget", "msiexec", "choco")):
                if is_installer_in_progress():
                    def _prog_cb(m):
                        if self and hasattr(self, "smartInstallProgress"):
                            self.smartInstallProgress.emit(tool_name, "installing", m)
                    cleared = wait_for_installer_lock(timeout=60, progress_cb=_prog_cb, run_id=run_id)
                    if not cleared:
                        err_msg = "Another installation is in progress and held the Windows Installer lock for over 60s. Halting without terminating unrelated processes."
                        step_results.append({"step": step, "exit_code": 1618, "stdout": "", "stderr": err_msg})
                        aggregated_stderr.append(err_msg)
                        return 1618, "\n".join(aggregated_stdout), "\n".join(aggregated_stderr), step_results

            step_t0 = time.time()
            _log_si("CMD_START", f"Starting step {idx + 1}/{len(steps)}: '{step}'", run_id=run_id)
            try:
                def _run_step_proc():
                    call_match = re.match(r"^\s*&\s*", step)
                    if call_match:
                        rest_cmd = step[call_match.end():].strip()
                        try:
                            parts = shlex.split(rest_cmd, posix=(sys.platform != "win32"))
                        except Exception:
                            parts = rest_cmd.split()
                        cleaned_parts = []
                        for p in parts:
                            if (p.startswith('"') and p.endswith('"')) or (p.startswith("'") and p.endswith("'")):
                                p = p[1:-1]
                            cleaned_parts.append(p)
                        exe_name = cleaned_parts[0] if cleaned_parts else ""
                        args = cleaned_parts[1:] if len(cleaned_parts) > 1 else []

                        # Prefer validated executable paths and separate arguments through process infrastructure
                        verified_exe = locate_executable(exe_name) or shutil.which(exe_name)
                        if not verified_exe and os.path.isfile(exe_name):
                            verified_exe = os.path.abspath(exe_name)

                        if verified_exe:
                            return subprocess.run(
                                [verified_exe] + args,
                                shell=False,
                                capture_output=True,
                                text=True,
                                timeout=timeout,
                                env=env,
                                cwd=working_dir
                            )
                        ps_exe = locate_executable("powershell") or shutil.which("powershell") or "powershell.exe"
                        return subprocess.run(
                            [ps_exe, "-NoProfile", "-NonInteractive", "-Command", step],
                            shell=False,
                            capture_output=True,
                            text=True,
                            timeout=timeout,
                            env=env,
                            cwd=working_dir
                        )
                    return subprocess.run(
                        step,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        env=env,
                        cwd=working_dir
                    )

                proc = _run_step_proc()
                duration = time.time() - step_t0
                out = proc.stdout.strip()
                err = proc.stderr.strip()
                code = proc.returncode

                # Handle Windows Installer busy error code 1618 (ERROR_INSTALL_ALREADY_RUNNING)
                if code == 1618 or ("1618" in err and "already in progress" in err.lower()):
                    print(f"[SmartInstall] Step exited with code 1618 (ERROR_INSTALL_ALREADY_RUNNING). Waiting for installer lock to release...")
                    _log_si("INSTALLER_BUSY", "Received exit code 1618. Waiting for active installer to complete before retrying step...", run_id=run_id)
                    def _retry_prog_cb(m):
                        if self and hasattr(self, "smartInstallProgress"):
                            self.smartInstallProgress.emit(tool_name, "installing", m)
                    if wait_for_installer_lock(timeout=60, progress_cb=_retry_prog_cb, run_id=run_id):
                        print(f"[SmartInstall] Installer lock released. Retrying step: '{step}'")
                        _log_si("RETRY", f"Retrying step '{step}' after installer lock released", run_id=run_id)
                        step_t0_retry = time.time()
                        proc = _run_step_proc()
                        duration = time.time() - step_t0_retry
                        out = proc.stdout.strip()
                        err = proc.stderr.strip()
                        code = proc.returncode

                _log_si(
                    "CMD_FINISH",
                    f"Step {idx + 1}/{len(steps)} finished with exit code {code} ({duration:.3f}s)",
                    run_id=run_id,
                    details={
                        "step": step,
                        "exit_code": code,
                        "duration_seconds": f"{duration:.3f}",
                        "stdout": out[:300],
                        "stderr": err[:300],
                        "non_interactive": True
                    }
                )

                step_results.append({
                    "step": step,
                    "exit_code": code,
                    "stdout": out,
                    "stderr": err
                })

                if out:
                    aggregated_stdout.append(out)
                if err:
                    aggregated_stderr.append(err)

                # Track venv creations or path additions
                if "venv" in step.lower() or "virtualenv" in step.lower():
                    base = working_dir or os.getcwd()
                    for venv_name in (".venv", "venv", "env"):
                        venv_bin = os.path.join(base, venv_name, "Scripts" if sys.platform == "win32" else "bin")
                        if os.path.isdir(venv_bin) and venv_bin not in env.get("PATH", ""):
                            env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
                            print(f"[SmartInstall] Preserving virtualenv environment PATH: {venv_bin}")

                if code != 0:
                    final_exit = code
                    print(f"[SmartInstall] Step {idx + 1} failed with exit code {code}. Halting dependent steps.")
                    break

            except subprocess.TimeoutExpired:
                duration = time.time() - step_t0
                err_msg = f"Command timed out after {timeout} seconds: {step}"
                _log_si(
                    "CMD_FINISH",
                    f"Step {idx + 1}/{len(steps)} timed out after {timeout}s",
                    run_id=run_id,
                    details={"step": step, "exit_code": 124, "duration_seconds": f"{duration:.3f}", "error": err_msg}
                )
                step_results.append({
                    "step": step,
                    "exit_code": 124,
                    "stdout": "",
                    "stderr": err_msg
                })
                aggregated_stderr.append(err_msg)
                final_exit = 124
                break
            except Exception as e:
                duration = time.time() - step_t0
                err_msg = f"Command execution exception on '{step}': {e}"
                _log_si(
                    "CMD_EXCEPTION",
                    f"Step {idx + 1}/{len(steps)} encountered exception: {e}",
                    run_id=run_id,
                    details={"step": step, "exit_code": 1, "duration_seconds": f"{duration:.3f}", "error": err_msg}
                )
                step_results.append({
                    "step": step,
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": err_msg
                })
                aggregated_stderr.append(err_msg)
                final_exit = 1
                break

        return final_exit, "\n".join(aggregated_stdout), "\n".join(aggregated_stderr), step_results

    def retry_formatting_operation(
        self,
        tool_name: str,
        file_path: str = "",
        executable: str = "",
        verified_path: str = ""
    ) -> Tuple[int, str, str]:
        """
        Retries the actual formatting operation on the target file with language awareness.
        Uses the FormatterManager if available, otherwise invokes the verified executable CLI directly.
        Returns (exit_code, stdout, stderr).
        """
        # Determine language from file_path or tool_name
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""
        lang_map = {
            ".rs": "rust",
            ".py": "python",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".go": "go",
            ".js": "javascript",
            ".ts": "typescript",
            ".json": "json",
            ".sql": "sql"
        }
        lang_id = lang_map.get(ext, "")
        if not lang_id:
            if "rust" in tool_name.lower():
                lang_id = "rust"
            elif "java" in tool_name.lower():
                lang_id = "java"
            elif "python" in tool_name.lower() or tool_name.lower() in ("black", "ruff", "autopep8"):
                lang_id = "python"
            elif "csharp" in tool_name.lower() or "csharpier" in tool_name.lower():
                lang_id = "csharp"
            elif "clang" in tool_name.lower():
                lang_id = "cpp"
            elif "go" in tool_name.lower():
                lang_id = "go"

        # Read actual file content or create valid sample content
        sample_code = ""
        target_file = file_path
        if file_path and os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    sample_code = f.read()
            except Exception as e:
                print(f"[SmartInstall] Notice reading {file_path}: {e}")

        if not sample_code:
            samples = {
                "rust": "fn main(){println!(\"DGX\");}",
                "java": "class Test{public static void main(String[] args){System.out.println(1);}}",
                "python": "def test():\n    return 42\n",
                "csharp": "class Test{static void Main(){System.Console.WriteLine(1);}}",
                "cpp": "int main(){return 0;}",
                "go": "package main\nfunc main(){}\n"
            }
            sample_code = samples.get(lang_id, "fn main(){}\n")
            if not target_file:
                exts = {"rust": "main.rs", "java": "Test.java", "python": "test.py", "csharp": "Program.cs", "cpp": "main.cpp", "go": "main.go"}
                target_file = exts.get(lang_id, "test.tmp")

        # Try FormatterManager
        fmt_mgr = self.formatter_manager
        if fmt_mgr is not None and hasattr(fmt_mgr, "format_code"):
            try:
                # Correct FormatterManager.format_code signature: (lang_id, file_path, source_code, tab_size=4)
                fmt_res = fmt_mgr.format_code(lang_id, target_file, sample_code, 4)
                if fmt_res.get("success"):
                    return 0, fmt_res.get("message", "Formatted successfully"), ""
                else:
                    return 1, "", fmt_res.get("message", "Formatting failed")
            except Exception as e:
                print(f"[SmartInstall] FormatterManager invocation error: {e}")
                return 1, "", f"FormatterManager error: {e}"

        # Direct CLI fallback
        f_exe = verified_path or locate_executable(executable) or locate_executable(tool_name)
        if f_exe:
            try:
                cmd = [f_exe, "--version"]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
            except Exception as e:
                return 1, "", str(e)

        return 1, "", "No operational formatter could be invoked."

    @staticmethod
    def detect_target_database_engine(context: Optional[dict] = None, file_path: str = "") -> Dict[str, Any]:
        """
        Determines the target database engine from reliable existing configuration or execution context.
        If the engine cannot be determined, identifies the target as ambiguous and requires user decision.
        Distinguishes database clients from database servers.
        """
        ctx = context or {}
        fp = file_path or ctx.get("filePath") or ctx.get("file_path") or ""

        # 1. Direct engine specification in context
        raw_engine = (
            ctx.get("database_engine") or ctx.get("databaseEngine") or
            ctx.get("db_engine") or ctx.get("dbEngine") or
            ctx.get("dialect") or ctx.get("database_type") or ""
        ).lower().strip()

        # 2. Connection configuration in context or workspace
        conn = ctx.get("connection") or ctx.get("connectionSettings") or ctx.get("database_config") or {}
        if not raw_engine and isinstance(conn, dict):
            raw_engine = (conn.get("type") or conn.get("engine") or conn.get("driver") or "").lower().strip()
            if not raw_engine:
                url = str(conn.get("url") or conn.get("connectionString") or "").lower()
                if "sqlserver" in url or "mssql" in url or "1433" in url:
                    raw_engine = "sqlserver"
                elif "postgres" in url or "5432" in url:
                    raw_engine = "postgresql"
                elif "mysql" in url or "3306" in url:
                    raw_engine = "mysql"
                elif "sqlite" in url or url.endswith(".db") or url.endswith(".sqlite"):
                    raw_engine = "sqlite"

        # 3. Check workspace configuration files
        if not raw_engine:
            workspace_dir = os.path.dirname(os.path.abspath(fp)) if fp and os.path.exists(fp) else os.getcwd()
            for fname in ("dgx.json", "database.json", "connections.json", "application.properties", ".env"):
                cf_path = os.path.join(workspace_dir, fname)
                if os.path.isfile(cf_path):
                    try:
                        with open(cf_path, "r", encoding="utf-8", errors="ignore") as f:
                            txt = f.read().lower()
                            if "sqlserver" in txt or "mssql" in txt:
                                raw_engine = "sqlserver"
                                break
                            elif "postgres" in txt or "postgresql" in txt:
                                raw_engine = "postgresql"
                                break
                            elif "mysql" in txt or "mariadb" in txt:
                                raw_engine = "mysql"
                                break
                            elif "sqlite" in txt:
                                raw_engine = "sqlite"
                                break
                    except Exception:
                        pass

        # 4. Check file content / dialect headers
        if not raw_engine and fp and os.path.isfile(fp):
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    header = "".join([f.readline() for _ in range(30)]).lower()
                    if "-- dialect: sqlserver" in header or "-- engine: sqlserver" in header or "-- target: sqlserver" in header or "\ngo\n" in f"\n{header}\n" or "use [" in header:
                        raw_engine = "sqlserver"
                    elif "-- dialect: postgres" in header or "-- engine: postgres" in header or "plpgsql" in header:
                        raw_engine = "postgresql"
                    elif "-- dialect: sqlite" in header or "-- engine: sqlite" in header or "pragma " in header:
                        raw_engine = "sqlite"
                    elif "-- dialect: mysql" in header or "-- engine: mysql" in header or "engine=innodb" in header:
                        raw_engine = "mysql"
            except Exception:
                pass

        # Engine normalization and tool mapping
        engine_map = {
            "sqlserver": ("sqlserver", "sqlcmd", "Microsoft SQL Server"),
            "mssql": ("sqlserver", "sqlcmd", "Microsoft SQL Server"),
            "sql server": ("sqlserver", "sqlcmd", "Microsoft SQL Server"),
            "postgres": ("postgresql", "psql", "PostgreSQL"),
            "postgresql": ("postgresql", "psql", "PostgreSQL"),
            "sqlite": ("sqlite", "sqlite3", "SQLite"),
            "sqlite3": ("sqlite", "sqlite3", "SQLite"),
            "mysql": ("mysql", "mysql", "MySQL"),
            "mariadb": ("mysql", "mysql", "MariaDB"),
            "oracle": ("oracle", "sqlplus", "Oracle Database"),
        }

        if raw_engine in engine_map:
            engine_id, client_tool, display_name = engine_map[raw_engine]
            return {
                "engine": engine_id,
                "is_ambiguous": False,
                "client_tool": client_tool,
                "display_name": display_name,
                "connection_available": bool(conn),
                "connection_info": conn if isinstance(conn, dict) else {},
                "reason": f"Target database engine identified as {display_name}."
            }

        return {
            "engine": None,
            "is_ambiguous": True,
            "client_tool": None,
            "display_name": "Unspecified Database",
            "connection_available": False,
            "connection_info": {},
            "reason": "Target database engine cannot be determined from file, configuration, or execution context."
        }

    def retry_sql_operation(
        self,
        tool_name: str,
        file_path: str = "",
        executable: str = "",
        verified_path: str = "",
        context: Optional[dict] = None
    ) -> Tuple[int, str, str]:
        """
        Retries the original SQL file execution operation against the target database.
        Checks for required connection and execution context before attempting execution.
        Captures real exit codes and stderr for AI recovery planning if execution fails.
        """
        ctx = context or {}
        db_target = self.detect_target_database_engine(ctx, file_path)
        client_exe = verified_path or locate_executable(executable) or locate_executable(tool_name) or locate_executable(db_target.get("client_tool", ""))

        if not client_exe or not os.path.isfile(client_exe):
            return 1, "", f"Cannot retry SQL execution: database client executable '{executable or tool_name}' not found."

        # Check for required connection context
        conn = db_target.get("connection_info") or ctx.get("connection") or ctx.get("connectionSettings") or ctx.get("database_config") or {}
        engine = db_target.get("engine")

        # For SQLite, a local db file can be used or inferred from file directory
        if engine == "sqlite":
            db_file = conn.get("database") or conn.get("file") or (os.path.splitext(file_path)[0] + ".db" if file_path else "test.db")
            try:
                proc = subprocess.run([client_exe, db_file, f".read {file_path}"], capture_output=True, text=True, timeout=30)
                return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
            except Exception as e:
                return 1, "", str(e)

        # For server-based databases (SQL Server, Postgres, MySQL): connection settings are required!
        if not conn or not (conn.get("host") or conn.get("server") or conn.get("connectionString") or conn.get("url")):
            err_msg = (
                f"Cannot execute SQL script: Database connection settings (server/host, database, credentials) "
                f"for {db_target.get('display_name', 'database')} are not configured. "
                "Installing the database client does not establish a connection or provide a running database server."
            )
            return 1, "", err_msg

        # If connection settings exist, execute with appropriate client flags
        cmd_args = [client_exe]
        server = conn.get("server") or conn.get("host", "localhost")
        database = conn.get("database", "")
        user = conn.get("user") or conn.get("username", "")
        password = conn.get("password", "")

        if engine == "sqlserver":
            cmd_args.extend(["-S", server])
            if database:
                cmd_args.extend(["-d", database])
            if user:
                cmd_args.extend(["-U", user])
                if password:
                    cmd_args.extend(["-P", password])
            else:
                cmd_args.append("-E")
            if file_path:
                cmd_args.extend(["-i", file_path])
        elif engine == "postgresql":
            cmd_args.extend(["-h", server])
            if database:
                cmd_args.extend(["-d", database])
            if user:
                cmd_args.extend(["-U", user])
            if file_path:
                cmd_args.extend(["-f", file_path])
        elif engine == "mysql":
            cmd_args.extend(["-h", server])
            if database:
                cmd_args.extend(["-D", database])
            if user:
                cmd_args.extend(["-u", user])
            if password:
                cmd_args.append(f"-p{password}")
            if file_path:
                cmd_args.extend(["-e", f"source {file_path}"])

        try:
            proc = subprocess.run(cmd_args, capture_output=True, text=True, timeout=30)
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except Exception as e:
            return 1, "", str(e)


    @staticmethod
    def validate_command_safety(command: str, tool_name: str = "") -> tuple:
        """Validates command safety using SmartSafetyGuard."""
        return SmartSafetyGuard.validate_command_safety(command, tool_name)

        # Validate that command uses known package managers, standard tools, or diagnostic queries
        allowed_installers = [
            "pip", "npm", "yarn", "pnpm", "cargo", "winget", "choco", "scoop",
            "brew", "apt", "apt-get", "pacman", "yum", "dnf", "rustup", "dotnet",
            "go install", "gem", "setup.py", "python -m pip", "python3 -m pip", "pyside6",
            "python", "python3", "py", "venv", "virtualenv", "rustfmt", "clang-format",
            "google-java-format", "csharpier", "gofmt", "black", "ruff", "autopep8",
            "shfmt", "prettier", "eslint", "flake8", "mypy", "isort", "git",
            "gcc", "g++", "clang", "clang++", "make", "cmake", "ninja", "java", "javac",
            "sqlcmd", "psql", "sqlite3", "mysql", "setx"
        ]
        has_installer = any(mgr in cmd_clean for mgr in allowed_installers)

        diagnostic_query = (
            any(q in cmd_clean for q in ("--version", "-version", "-v", "--help", "-h", "-?", "version", "status", "info")) or
            cmd_clean.startswith(("where ", "which ", "type ", "get-command ")) or
            (tool_name and tool_name.lower().strip() in cmd_clean)
        )

        if not (has_installer or diagnostic_query):
            if not any(k in cmd_clean for k in ("install", "add", "setup", "get", "activate", "update", "upgrade")):
                return False, "Command rejected: Command is not a recognized developer tool installation or diagnostic command."

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
        if res_type in ("cannot_resolve", "awaiting_user_decision", "recovery_session") or res.get("needs_user_decision") or res.get("status") == "awaiting_user_decision":
            return True, "Valid resolution type"

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

        run_id = kwargs.get("runId") or f"si_{int(time.time()*1000) % 1000000}"
        ctx["runId"] = run_id

        print(f"[SmartInstall] Entry point created: {ctx.get('operation')}")
        print(f"[SmartInstall] Entry point shown")

        _log_si(
            "START",
            f"Smart Install initiated for: '{operation or executable or detected_missing_dependency or 'tool'}'",
            run_id=run_id,
            details={
                "tool": executable or detected_missing_dependency or operation,
                "operation_type": operation_type,
                "target_file": file_path,
                "run_id": run_id
            }
        )
        _log_si(
            "ENVIRONMENT",
            f"Detected OS={cur_os}, language={clean_lang or clean_ext or 'general'}, arch={platform.machine()}",
            run_id=run_id,
            details={
                "operating_system": cur_os,
                "language": clean_lang or clean_ext or "general",
                "python_executable": sys.executable,
                "working_directory": ctx.get("workingDirectory") or os.getcwd()
            }
        )
        _log_si(
            "ERROR_TRIGGER",
            f"Diagnostic trigger: {error_message or stderr or detected_problem or 'Missing dependency'}",
            run_id=run_id,
            details={
                "error_message": error_message,
                "stderr": stderr,
                "exit_code": exit_code,
                "command_attempted": command_attempted
            }
        )
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
            "5. COMMAND-FIRST NON-INTERACTIVE INSTALLATION POLICY:\n"
            "   - Provide executable, non-interactive commands whenever a reliable CLI installation is available.\n"
            "   - Prefer documented silent options (winget: --silent --accept-package-agreements --accept-source-agreements; choco: -y --no-progress; pip: --no-input).\n"
            "   - Do NOT invent flags or URLs.\n"
            "   - If manual intervention is genuinely required, return cannot_resolve with explanation, official vendor URL, and verificationCommand.\n\n"
            "6. RESPONSE CONTRACT (VALID JSON ONLY):\n"
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
            '  "officialUrl": "<official vendor documentation or download URL>",\n'
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
            cmd = data.get("command", "")
            steps = data.get("steps", [])
            if isinstance(steps, str):
                steps = [s.strip() for s in steps.splitlines() if s.strip()]
            v_cmd = data.get("verificationCommand") or data.get("verify") or ""
            t_name = data.get("tool") or data.get("toolName") or fallback_tool
            pkg_name = data.get("package") or data.get("packageName") or fallback_exec or fallback_tool
            exec_name = data.get("executable") or fallback_exec or fallback_tool

            decision_req = data.get("decision_request") or data.get("decisionRequest")
            needs_user_dec = bool(data.get("needs_user_decision", data.get("needsUserDecision", False))) or data.get("status") == "awaiting_user_decision"
            if not decision_req and (needs_user_dec or "question" in data or "choices" in data or "options" in data):
                q = data.get("question") or data.get("title") or "Clarification required"
                decision_req = {
                    "question": q,
                    "why_necessary": data.get("why_necessary", data.get("whyNecessary", data.get("explanation", data.get("diagnosis", "")))),
                    "whyNecessary": data.get("why_necessary", data.get("whyNecessary", data.get("explanation", data.get("diagnosis", "")))),
                    "choices": data.get("choices", data.get("options", [])),
                    "options": data.get("choices", data.get("options", [])),
                    "allow_custom_answer": bool(data.get("allow_custom_answer", data.get("allowCustomAnswer", True))),
                    "allowCustomAnswer": bool(data.get("allow_custom_answer", data.get("allowCustomAnswer", True))),
                    "resume_key": data.get("resume_key", data.get("resumeKey", "user_choice")),
                    "resumeKey": data.get("resume_key", data.get("resumeKey", "user_choice")),
                    "default_choice": data.get("default_choice", data.get("defaultChoice", ""))
                }
                needs_user_dec = True
            elif decision_req and isinstance(decision_req, dict):
                needs_user_dec = True
                if "why_necessary" in decision_req and "whyNecessary" not in decision_req:
                    decision_req["whyNecessary"] = decision_req["why_necessary"]
                elif "whyNecessary" in decision_req and "why_necessary" not in decision_req:
                    decision_req["why_necessary"] = decision_req["whyNecessary"]
                if "allow_custom_answer" in decision_req and "allowCustomAnswer" not in decision_req:
                    decision_req["allowCustomAnswer"] = decision_req["allow_custom_answer"]
                if "resume_key" in decision_req and "resumeKey" not in decision_req:
                    decision_req["resumeKey"] = decision_req["resume_key"]
                if "choices" in decision_req and "options" not in decision_req:
                    decision_req["options"] = decision_req["choices"]

            if needs_user_dec or decision_req:
                r_type = "awaiting_user_decision"
            else:
                r_type = data.get("resolutionType") or data.get("resolution_type") or ("single_command" if data.get("command") else "cannot_resolve")

            parsed_res = {
                "tool": t_name,
                "toolName": t_name,
                "title": data.get("title") or (decision_req.get("question") if decision_req else f"Install {t_name}"),
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
                "officialUrl": data.get("officialUrl") or data.get("official_url") or "",
                "diagnosis": data.get("diagnosis", ""),
                "explanation": data.get("explanation", ""),
                "source": "ai",
                "retryOperation": data.get("retryOperation", True)
            }
            if needs_user_dec or decision_req:
                parsed_res["needs_user_decision"] = True
                parsed_res["needsUserDecision"] = True
                parsed_res["decision_request"] = decision_req
                parsed_res["decisionRequest"] = decision_req
                parsed_res["status"] = "awaiting_user_decision"
                parsed_res["options"] = decision_req.get("choices", []) if decision_req else []
                parsed_res["choices"] = decision_req.get("choices", []) if decision_req else []
            return parsed_res

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
        AI-driven Smart Recovery & Install resolver powered by SmartEngine.
        Ingests real failure context and capabilities, queries the AI backend,
        and returns an authoritative proposal with attached recovery session.
        """
        if not hasattr(self, "_smart_engine") or self._smart_engine is None:
            self._smart_engine = SmartEngine(extension_manager=self)
            self._recovery_sessions = self._smart_engine._sessions

        # Add detected diagnostic capabilities to context
        if "installed_jdks" not in context:
            try:
                jdks = discover_installed_jdks()
                if jdks:
                    context["installed_jdks"] = [f"{j['version']} ({j['path']})" for j in jdks[:3]]
            except Exception:
                pass

        if "available_extensions" not in context:
            try:
                context["available_extensions"] = [eid for eid in self._extensions.keys() if eid not in self._disabled_ids]
            except Exception:
                pass

        proposal = self._smart_engine.resolve_context(context)
        return proposal

    def _attach_command_recovery_session_if_needed(self, context: dict, proposal: dict) -> dict:
        """
        Connects recovery proposals to the RecoverySession workflow.
        Maintains sessions for action plans and interactive user decisions.
        """
        if not proposal or not isinstance(proposal, dict):
            return proposal

        if not hasattr(self, "_smart_engine") or self._smart_engine is None:
            self._smart_engine = SmartEngine(extension_manager=self)
            self._recovery_sessions = self._smart_engine._sessions

        session_id = proposal.get("sessionId") or proposal.get("session_id")
        session = self._recovery_sessions.get(session_id) if session_id else None

        if not session:
            if session_id and self._smart_engine.get_session(session_id):
                session = self._smart_engine.get_session(session_id)
                self._recovery_sessions[session_id] = session
            else:
                session = self._smart_engine.create_session(context, maximum_commands=10)
                session_id = session.session_id
                self._recovery_sessions[session_id] = session

        proposal["sessionId"] = session_id
        proposal["session_id"] = session_id

        # User decision needed
        if proposal.get("status") == "awaiting_user_decision" or proposal.get("needs_user_decision") or proposal.get("decision_request"):
            session.status = "awaiting_user_decision"
            dec_req = proposal.get("decision_request") or proposal.get("decisionRequest")
            session.decision_request = dec_req
            proposal["decision_request"] = dec_req
            proposal["decisionRequest"] = dec_req
            proposal["status"] = "awaiting_user_decision"
            proposal["resolutionType"] = "recovery_session"
            self.recoveryPlanUpdated.emit(session.to_dict())
            return proposal

        # Actions / Commands
        if proposal.get("commands") or session.active_batch:
            if proposal.get("commands") and not session.active_batch and not session.command_history:
                session.accept_new_batch(proposal["commands"], proposal.get("proposed_total_steps"))
            s_dict = session.to_dict()
            proposal["commands"] = s_dict.get("active_batch", [])
            proposal["total_steps"] = session.total_steps
            proposal["totalSteps"] = session.total_steps
            proposal["total_steps_display"] = s_dict.get("total_steps_display", "")
            proposal["totalStepsDisplay"] = s_dict.get("totalStepsDisplay", "")
            proposal["commands_remaining"] = session.commands_remaining
            proposal["commandsRemaining"] = session.commands_remaining
            proposal["resolutionType"] = "recovery_session"
            proposal["status"] = session.status
            self.recoveryPlanUpdated.emit(session.to_dict())
            return proposal

        if proposal.get("status") == "cannot_resolve" or proposal.get("resolutionType") == "cannot_resolve":
            session.status = "cannot_resolve"
            proposal["status"] = "cannot_resolve"
            return proposal

        return proposal

    @Slot("QVariantMap")
    def start_smart_install_analysis(self, context: dict):
        """Asynchronously runs AI resolution in a background thread."""
        def _worker():
            try:
                proposal = self.resolve_smart_install_context(context)
                proposal = self._attach_command_recovery_session_if_needed(context, proposal)
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
        proposal = self.resolve_smart_install_context(ctx)
        return self._attach_command_recovery_session_if_needed(ctx, proposal)

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
        proposal = self.resolve_smart_install_context(ctx)
        return self._attach_command_recovery_session_if_needed(ctx, proposal)

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
    def normalize_command(cmd: str) -> str:
        """
        Normalizes command string by stripping comments, collapsing whitespace, and lowercasing for retry comparison.
        """
        if not cmd:
            return ""
        lines = [
            l.strip()
            for l in cmd.strip().splitlines()
            if l.strip() and not l.strip().startswith(("#", "//", "REM ", "rem "))
        ]
        single = " ".join(" ".join(lines).split())
        return single.lower()

    @staticmethod
    def parse_post_install_ai_response(response_text: str) -> Tuple[str, str, str]:
        """
        Parses post-install AI diagnosis response into (status, fix_command, explanation).
        status: 'SUCCESS' | 'FAILED' | 'FIX' | 'MANUAL_INSTALLATION_REQUIRED' | 'INVALID'
        """
        if not response_text or not response_text.strip():
            return "INVALID", "", "Empty AI response"

        text = response_text.strip()
        if text.lower().startswith("chatgpt said:"):
            text = text[13:].strip()

        shell_labels = {
            "powershell", "pwsh", "cmd", "batch", "bat", "bash", "sh", "zsh", "shell", "terminal", "console"
        }

        # Check for [FIX] command
        fix_match = re.search(r'\[FIX\]\s*(.*)', text, re.IGNORECASE | re.DOTALL)
        if fix_match:
            pre_fix = text[:fix_match.start()].strip()
            after_fix = fix_match.group(1).strip()

            # Check for fenced code block (e.g. ```powershell\n<command>\n```)
            fence_regex = re.compile(
                r'(?:`{3,}|~{3,})([a-zA-Z0-9_\+#\.\-]*)[ \t]*(?:\r?\n)?([\s\S]*?)(?:\r?\n)?(?:`{3,}|~{3,}|\Z)'
            )
            fence_match = fence_regex.search(after_fix)

            fix_cmd = ""
            post_explanation = ""

            if fence_match and fence_match.group(2) and fence_match.group(2).strip():
                code_inside = fence_match.group(2).strip()
                # Clean comment lines from command block
                cmd_lines = [
                    l.strip()
                    for l in code_inside.splitlines()
                    if l.strip() and not l.strip().startswith(("#", "//", "REM ", "rem "))
                ]
                candidate_cmd = "\n".join(cmd_lines).strip()

                text_before_fence = after_fix[:fence_match.start()].strip()
                if text_before_fence.lower() in shell_labels:
                    text_before_fence = ""

                text_after_fence = after_fix[fence_match.end():].strip()
                explanation_parts = [p for p in (pre_fix, text_before_fence, text_after_fence) if p]
                post_explanation = "\n\n".join(explanation_parts)

                if candidate_cmd:
                    fix_cmd = candidate_cmd
            else:
                lines = after_fix.splitlines()
                first_line = lines[0].strip() if lines else ""
                if first_line.lower() in shell_labels:
                    rem_lines = [l.strip() for l in lines[1:] if l.strip()]
                    if rem_lines:
                        fix_cmd = rem_lines[0].strip("`").strip()
                        post_explanation = "\n".join(rem_lines[1:]).strip() if len(rem_lines) > 1 else ""
                    else:
                        fix_cmd = ""
                        post_explanation = first_line
                else:
                    fix_cmd = first_line.strip("`").strip()
                    post_explanation = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

                explanation_parts = [p for p in (pre_fix, post_explanation) if p]
                post_explanation = "\n\n".join(explanation_parts)

            # Separate embedded explanation headers if AI omitted a newline (e.g. command followed immediately by Root cause:)
            split_m = re.search(r'(?i)(Root\s*cause|Explanation|Reason|Note)\s*:\s*', fix_cmd)
            if split_m and split_m.start(1) > 0:
                split_idx = split_m.start(1)
                extra_exp = fix_cmd[split_idx:].strip()
                fix_cmd = fix_cmd[:split_idx].strip()
                post_explanation = (extra_exp + "\n" + post_explanation).strip()

            # Ensure shell labels alone are not accepted as executable fix commands
            if not fix_cmd or fix_cmd.lower() in shell_labels:
                return "INVALID", "", post_explanation or text

            explanation = post_explanation or text
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

        run_id = self._active_run_ids.get(tool_name) or f"si_{tool_name}_{int(time.time()*1000)%1000000}"
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

        _log_si(
            "AI_INPUT",
            f"Sending post-install diagnostic prompt to AI for '{tool_name}'",
            run_id=run_id,
            details={
                "tool": tool_name,
                "install_exit": install_exit_code,
                "verify_exit": verify_exit_code,
                "operation_exit": operation_exit_code,
                "prompt_length": len(prompt),
                "prompt_content": prompt
            }
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
                    # Step 1 & 2: Detect available JDKs and identify if a compatible JDK is already installed
                    compat_jdk = find_compatible_jdk(min_version=21)
                    if compat_jdk:
                        jdk_path = compat_jdk["path"]
                        java_exe = compat_jdk["java_exe"]
                        jdk_ver = compat_jdk.get("version", "21+")
                        print(f"[SmartInstall] Found compatible JDK ({jdk_ver}) already installed at {jdk_path}")
                        self.set_tool_runtime_config(tool_name, {
                            "JAVA_HOME": jdk_path,
                            "java_path": java_exe,
                            "version": jdk_ver,
                            "PATH_PREPEND": os.path.dirname(java_exe)
                        })
                        try:
                            v_proc = subprocess.run([java_exe, "-version"], capture_output=True, text=True, timeout=5)
                            v_txt = (v_proc.stderr or v_proc.stdout or "").strip()
                            print(f"[SmartInstall] Verified compatible installed JDK {jdk_ver}: {v_txt.splitlines()[0] if v_txt else 'OK'}")
                        except Exception as e_v:
                            print(f"[SmartInstall] Verification notice: {e_v}")

                        op_exit, op_out, op_err = self.retry_formatting_operation(
                            tool_name=tool_name,
                            file_path=file_path,
                            executable=executable,
                            verified_path=verified_path
                        )
                        print(f"[SmartInstall] Auto-retried formatting with compatible installed JDK: exit {op_exit}")
                        if op_exit == 0:
                            print("[SmartInstall] Post-install AI result: SUCCESS (resolved using existing installed compatible JDK)")
                            return "SUCCESS", "", f"Selected compatible installed JDK ({jdk_ver}) for formatter. Formatting succeeded."

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
                found_exe = verified_path or locate_executable(executable) or locate_executable(tool_name)
                if found_exe and os.path.isfile(found_exe):
                    v_direct_cmd = [found_exe, "-?"] if "sqlcmd" in (found_exe.lower() + tool_name.lower()) else [found_exe, "--version"]
                    try:
                        v_direct_proc = subprocess.run(v_direct_cmd, capture_output=True, text=True, timeout=5)
                        if v_direct_proc.returncode == 0:
                            tool_dir = os.path.dirname(os.path.abspath(found_exe))
                            self.set_tool_runtime_config(tool_name, {
                                "PATH_PREPEND": tool_dir,
                                "executable_path": found_exe
                            })
                            os.environ["PATH"] = tool_dir + os.pathsep + os.environ.get("PATH", "")
                            self._custom_paths[tool_name] = found_exe
                            if executable:
                                self._custom_paths[executable] = found_exe

                            if (file_path and file_path.lower().endswith(".sql")) or tool_name.lower() in ("sqlcmd", "psql", "sqlite3", "mysql") or retry_action in ("run", "sql", "execute"):
                                op_ret_exit, op_ret_out, op_ret_err = self.retry_sql_operation(
                                    tool_name=tool_name,
                                    file_path=file_path,
                                    executable=found_exe,
                                    verified_path=found_exe,
                                    context={"filePath": file_path, "toolName": tool_name}
                                )
                                if op_ret_exit == 0:
                                    return "SUCCESS", "", f"{tool_name} verified at actual path '{found_exe}'. SQL execution succeeded."
                                else:
                                    return "FAILED", "", f"{tool_name} verified at actual path '{found_exe}', but SQL file execution failed: {op_ret_err}"
                            return "SUCCESS", "", f"{tool_name} was found installed at '{found_exe}' and verified."
                    except Exception:
                        pass
                err = install_stderr or install_stdout or verify_stderr or verify_stdout or f"Exit code {install_exit_code}"
                print("[SmartInstall] Post-install AI result: FAILED")
                return "FAILED", "", err

        print("[SmartInstall] Post-install AI response received")
        print(f"[SmartInstall] Post-install AI raw response: {ai_response_text}")

        status, fix_cmd, explanation = self.parse_post_install_ai_response(ai_response_text)
        print(f"[SmartInstall] Post-install AI parsed status: {status}")
        print(f"[SmartInstall] Post-install AI parsed fix command: {fix_cmd}")
        print(f"[SmartInstall] Post-install AI parsed explanation: {explanation}")

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

        # CRITICAL GUARD: Do not confuse successful installation with verification or operational success
        if (verify_exit_code != 0 or has_operational_failure) and status == "SUCCESS":
            print("[SmartInstall] AI incorrectly reported SUCCESS despite active verification or operational failure. Rejecting false success.")
            if has_operational_failure:
                status = "FAILED"
                explanation = operation_error or operation_stderr or f"Operation failed with exit code {operation_exit_code}"
            elif verify_exit_code != 0:
                found_exe = verified_path or locate_executable(executable) or locate_executable(tool_name)
                if found_exe and os.path.isfile(found_exe):
                    status = "FIX"
                    explanation = f"{tool_name} was found at '{found_exe}' but is missing from PATH. Environment PATH update required."
                    fix_cmd = f'setx PATH "$env:PATH;{os.path.dirname(found_exe)}"'
                else:
                    status = "FAILED"
                    explanation = verify_stderr or verify_stdout or f"Verification command failed with exit code {verify_exit_code}"
            elif runtime_info.get("incompatibility_detected"):
                compat_jdk = find_compatible_jdk(min_version=21)
                if compat_jdk:
                    jdk_path = compat_jdk["path"]
                    java_exe = compat_jdk["java_exe"]
                    jdk_ver = compat_jdk.get("version", "21+")
                    self.set_tool_runtime_config(tool_name, {
                        "JAVA_HOME": jdk_path,
                        "java_path": java_exe,
                        "version": jdk_ver,
                        "PATH_PREPEND": os.path.dirname(java_exe)
                    })
                    op_exit, op_out, op_err = self.retry_formatting_operation(
                        tool_name=tool_name,
                        file_path=file_path,
                        executable=executable,
                        verified_path=verified_path
                    )
                    if op_exit == 0:
                        return "SUCCESS", "", f"Selected compatible installed JDK ({jdk_ver}) for formatter. Formatting succeeded."
                status = "FIX"
                fix_cmd = make_command_non_interactive("winget install --id Microsoft.OpenJDK.21 --exact --silent --accept-package-agreements --accept-source-agreements")
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
            compat_jdk = find_compatible_jdk(min_version=21)
            if compat_jdk:
                jdk_path = compat_jdk["path"]
                java_exe = compat_jdk["java_exe"]
                jdk_ver = compat_jdk.get("version", "21+")
                self.set_tool_runtime_config(tool_name, {
                    "JAVA_HOME": jdk_path,
                    "java_path": java_exe,
                    "version": jdk_ver,
                    "PATH_PREPEND": os.path.dirname(java_exe)
                })
                op_exit, op_out, op_err = self.retry_formatting_operation(
                    tool_name=tool_name,
                    file_path=file_path,
                    executable=executable,
                    verified_path=verified_path
                )
                if op_exit == 0:
                    return "SUCCESS", "", f"Selected compatible installed JDK ({jdk_ver}) for formatter. Formatting succeeded."

            # If previous package manager install was already attempted or failed, try portable archive installation
            if fix_attempt_count >= 1 or is_post_fix:
                p_ok, p_java, p_ver, p_err = install_portable_runtime("openjdk", min_version=21, run_id=run_id)
                if p_ok:
                    jdk_dir = os.path.dirname(os.path.dirname(p_java))
                    self.set_tool_runtime_config(tool_name, {
                        "JAVA_HOME": jdk_dir,
                        "java_path": p_java,
                        "version": p_ver,
                        "PATH_PREPEND": os.path.dirname(p_java)
                    })
                    op_exit, op_out, op_err = self.retry_formatting_operation(
                        tool_name=tool_name,
                        file_path=file_path,
                        executable=executable,
                        verified_path=verified_path
                    )
                    if op_exit == 0:
                        return "SUCCESS", "", f"Installed portable OpenJDK ({p_ver}) into managed directory and verified formatting. Formatting succeeded."

            t_lower = tool_name.lower()
            fc_lower = fix_cmd.lower()
            if (t_lower in fc_lower or "google-java-format" in fc_lower) and not any(k in fc_lower for k in ("openjdk", "jdk", "java")):
                print(f"[SmartInstall] Overriding ineffective reinstall recommendation '{fix_cmd}' with runtime upgrade.")
                fix_cmd = make_command_non_interactive("winget install --id Microsoft.OpenJDK.21 --exact --silent --accept-package-agreements --accept-source-agreements")
                explanation = (
                    "The formatter is installed, but its execution is incompatible with the Java runtime currently being used. "
                    "The current JDK is Java 17, while the installed google-java-format version requires a newer JDK. "
                    "Install a compatible JDK and ensure the formatter actually uses it."
                )

        if fix_cmd:
            fix_cmd = make_command_non_interactive(fix_cmd)

        if status == "MANUAL_INSTALLATION_REQUIRED" and "http" not in explanation:
            m_info = get_official_manual_fallback(tool_name, reason=explanation)
            explanation = (
                f"{explanation}\n\n"
                f"Official Download: {m_info.get('downloadUrl') or m_info.get('officialUrl')}\n"
                f"Action Required: {m_info.get('actionRequired')}\n"
                f"Verification Command: {m_info.get('verificationCommand')}\n"
                f"Resume: {m_info.get('resumeNote')}"
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
        _log_si(
            "AI_RESPONSE",
            f"Post-install AI diagnosis evaluated: status={status}, has_fix={bool(fix_cmd)}",
            run_id=run_id,
            details={
                "status": status,
                "fix_command": fix_cmd,
                "explanation": explanation,
                "raw_response": ai_response_text
            }
        )
        if status == "FIX":
            _log_si(
                "RETRY",
                f"Post-install AI proposed corrective fix: '{fix_cmd}'",
                run_id=run_id,
                details={
                    "fix_command": fix_cmd,
                    "reason": explanation,
                    "attempt_count": fix_attempt_count + 1
                }
            )

        return status, fix_cmd, explanation

    @Slot(str, str, str, str, str, str, result=bool)
    @Slot(str, str, str, str, str, result=bool)
    @Slot(str, str, str, str, result=bool)
    @Slot(str, str, str, result=bool)
    @Slot(str, str, str, str, str, str, result=bool)
    @Slot(str, str, str, str, str, result=bool)
    @Slot(str, str, str, str, result=bool)
    @Slot(str, str, str, result=bool)
    def execute_smart_install_command(self, tool_name: str, command: str, executable: str = "", retry_action: str = "", file_path: str = "", verify_command: str = "") -> bool:
        """
        Executes an approved Smart Install command only after explicit user approval:
        1. Logs user approval and validates command safety.
        2. Executes approved command sequence using execute_command_steps.
        3. Verifies installation via verifyCommand or resolved executable.
        4. If installation and verification succeed, independently retries the original operation.
        5. Sends real execution outputs to AI for post-install verification diagnosis only if needed.
        6. Clearly separates internal IDE errors from process failures.
        """
        run_id = self._active_run_ids.get(tool_name) or f"si_{tool_name}_{int(time.time()*1000)%1000000}"
        print(f"[SmartInstall] User approved install")
        _log_si(
            "USER_APPROVAL",
            f"User approved Smart Install execution for '{tool_name}'",
            run_id=run_id,
            details={"tool": tool_name, "command": command, "retry_action": retry_action, "file_path": file_path}
        )

        if not command:
            print(f"[SmartInstall] Execution failed: empty command")
            _log_si("TERMINAL", f"Installation failed: command is empty", run_id=run_id, details={"success": False, "reason": "empty command"})
            self.smartInstallCompleted.emit(tool_name, False, "Cannot execute: installation command is empty.", retry_action)
            return False

        if command.startswith("dgx:extension") or command.startswith("dgx_extension"):
            parts = command.split()
            act = "enable" if any(x in parts for x in ("enable", "activate")) else "install"
            ext_id = parts[-1]
            return self.execute_extension_recovery(ext_id, act, tool_name, retry_action, file_path)

        # Command safety validation
        is_safe, reason = self.validate_command_safety(command, tool_name)
        if not is_safe:
            print(f"[SmartInstall] Execution blocked: {reason}")
            _log_si("TERMINAL", f"Execution blocked: {reason}", run_id=run_id, details={"success": False, "reason": reason})
            self.smartInstallCompleted.emit(tool_name, False, f"Execution halted: {reason}", retry_action)
            return False

        is_elevated = any(k in command.lower() for k in ("winget", "choco", "sudo", "apt", "npm install -g", "pnpm add -g", "yarn global add"))
        _log_si(
            "PRIVILEGE_CHECK",
            f"Privilege check for '{tool_name}': requires_elevation={is_elevated}, approval_status='approved_by_user'",
            run_id=run_id,
            details={"requires_elevation": is_elevated, "command": command, "approval_status": "approved_by_user"}
        )

        pre_path = locate_executable(executable) or locate_executable(tool_name)
        _log_si(
            "DETECTION",
            f"Pre-install detection for '{tool_name}': {'Discovered at ' + pre_path if pre_path else 'Not found in environment'}",
            run_id=run_id,
            details={"phase": "pre_install", "tool": tool_name, "executable": executable, "detected_path": pre_path or "None"}
        )

        if tool_name in self._installing_tools:
            return False

        self._installing_tools.add(tool_name)
        print(f"[SmartInstall] Installation started: {command}")
        _log_si("STATE_TRANSITION", f"State transitioned to 'installing': Running approved command", run_id=run_id, details={"state": "installing", "command": command})
        self.smartInstallProgress.emit(tool_name, "installing", f"Running approved command: {command}")

        working_dir = os.path.dirname(os.path.abspath(file_path)) if file_path and os.path.exists(file_path) else os.getcwd()

        def _worker():
            try:
                install_exit, stdout, stderr, step_results = self.execute_command_steps(
                    command_str=command,
                    tool_name=tool_name,
                    timeout=300,
                    working_dir=working_dir,
                    run_id=run_id
                )

                print(f"[SmartInstall] Installation exit code: {install_exit}")
                _log_si("STATE_TRANSITION", "State transitioned to 'verifying': Verifying installed executable and environment", run_id=run_id, details={"state": "verifying"})
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

                _log_si(
                    "DETECTION",
                    f"Post-install detection for '{tool_name}': {'Discovered at ' + verified_path if verified_path else 'Not found in environment'}",
                    run_id=run_id,
                    details={"phase": "post_install", "tool": tool_name, "executable": executable, "verified_path": verified_path or "None"}
                )

                if verified_path:
                    if tool_name.lower() in ("sqlcmd", "sqlcmd.exe") or (executable and executable.lower() in ("sqlcmd", "sqlcmd.exe")):
                        v_cmd = f'"{verified_path}" -?'
                    else:
                        v_cmd = f'"{verified_path}" --version'
                elif verify_command:
                    v_cmd = verify_command
                elif executable:
                    if executable.lower() in ("sqlcmd", "sqlcmd.exe"):
                        v_cmd = f'"{executable}" -?'
                    else:
                        v_cmd = f'"{executable}" --version'
                else:
                    if tool_name.lower() in ("sqlcmd", "sqlcmd.exe"):
                        v_cmd = f'"{tool_name}" -?'
                    else:
                        v_cmd = f'"{tool_name}" --version'

                print(f"[SmartInstall] Verification started: {v_cmd}")
                v_proc = subprocess.run(v_cmd, shell=True, capture_output=True, text=True, timeout=15)
                v_exit = v_proc.returncode
                v_stdout = v_proc.stdout.strip()
                v_stderr = v_proc.stderr.strip()
                print(f"[SmartInstall] Verification exit code: {v_exit}")

                _log_si(
                    "VERIFICATION",
                    f"Verification command '{v_cmd}' exited with code {v_exit}",
                    run_id=run_id,
                    details={"command": v_cmd, "exit_code": v_exit, "stdout": v_stdout[:300], "stderr": v_stderr[:300]}
                )

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

                # Update environment paths if verified
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

                # CRITICAL SEPARATION: Check if installation & verification succeeded
                if install_exit == 0 and v_exit == 0 and verified_path and os.path.exists(verified_path):
                    # Tool is installed and verified. Now independently retry original operation if requested.
                    op_exit = 0
                    op_err = ""
                    if retry_action == "format":
                        _log_si("STATE_TRANSITION", f"State transitioned to 'retrying': Retrying actual operation", run_id=run_id, details={"state": "retrying"})
                        self.smartInstallProgress.emit(tool_name, "retrying", "Retrying actual operation...")
                        _log_si(
                            "OPERATION_RETRY",
                            f"Retrying original operation '{retry_action}' for '{tool_name}'",
                            run_id=run_id,
                            details={"operation": retry_action, "file_path": file_path, "tool": tool_name}
                        )
                        op_exit, op_out, op_err = self.retry_formatting_operation(
                            tool_name=tool_name,
                            file_path=file_path,
                            executable=executable,
                            verified_path=verified_path
                        )
                        print(f"[SmartInstall] Operation retry exit: {op_exit}, err: {op_err}")
                        _log_si(
                            "OPERATION_RETRY",
                            f"Original operation retry {'succeeded' if op_exit == 0 else 'failed with exit code ' + str(op_exit)}",
                            run_id=run_id,
                            details={"exit_code": op_exit, "error": op_err, "resolved": (op_exit == 0)}
                        )
                        self.originalOperationRetried.emit(tool_name, (op_exit == 0), op_err)
                    elif (
                        retry_action in ("run", "sql", "execute") or
                        (file_path and file_path.lower().endswith(".sql")) or
                        tool_name.lower() in ("sqlcmd", "psql", "sqlite3", "mysql")
                    ):
                        _log_si("STATE_TRANSITION", f"State transitioned to 'retrying': Retrying actual SQL operation", run_id=run_id, details={"state": "retrying"})
                        self.smartInstallProgress.emit(tool_name, "retrying", "Retrying SQL operation against database...")
                        _log_si(
                            "OPERATION_RETRY",
                            f"Retrying original SQL operation for '{tool_name}'",
                            run_id=run_id,
                            details={"operation": retry_action, "file_path": file_path, "tool": tool_name}
                        )
                        op_exit, op_out, op_err = self.retry_sql_operation(
                            tool_name=tool_name,
                            file_path=file_path,
                            executable=executable,
                            verified_path=verified_path,
                            context=getattr(self, "_last_install_context", {}) or {"filePath": file_path, "toolName": tool_name}
                        )
                        print(f"[SmartInstall] SQL operation retry exit: {op_exit}, err: {op_err}")
                        _log_si(
                            "OPERATION_RETRY",
                            f"Original SQL operation retry {'succeeded' if op_exit == 0 else 'failed with exit code ' + str(op_exit)}",
                            run_id=run_id,
                            details={"exit_code": op_exit, "error": op_err, "resolved": (op_exit == 0)}
                        )
                        self.originalOperationRetried.emit(tool_name, (op_exit == 0), op_err)

                    if op_exit == 0:
                        ver_str = (v_stdout or v_stderr or "OK").splitlines()[0] if (v_stdout or v_stderr) else "OK"
                        msg = f"{tool_name} installed and verified successfully! ({ver_str})"
                        if verified_path:
                            msg += f"\nLocation: {verified_path}"
                        print(f"[SmartInstall] Overall success confirmed for {tool_name}")
                        _log_si("TERMINAL", f"Smart Install completed successfully for '{tool_name}'", run_id=run_id, details={"success": True, "message": msg})
                        self.smartInstallPostInstallVerified.emit(tool_name, "success", msg, retry_action, file_path, "")
                        self.smartInstallCompleted.emit(tool_name, True, msg, retry_action)
                        return

                # If we reach here, either installation failed, verification failed, or the original operation failed.
                # Now invoke AI post-install diagnosis with accurate operational context.
                _log_si("STATE_TRANSITION", "State transitioned to 'post_install_analyzing': Running post-install AI verification", run_id=run_id, details={"state": "post_install_analyzing"})
                self.smartInstallProgress.emit(tool_name, "post_install_analyzing", "Running post-install AI verification...")

                op_exit_code = 0
                op_stderr_str = ""
                if op_exit != 0:
                    op_exit_code = op_exit
                    op_stderr_str = op_err
                elif retry_action == "format" and (install_exit == 0 and v_exit == 0):
                    op_exit_code = 1
                    op_stderr_str = "Operation failed during retry"

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
                    is_post_fix=False,
                    operation_attempted=retry_action,
                    operation_exit_code=op_exit_code,
                    operation_stderr=op_stderr_str,
                    operation_error=op_stderr_str
                )

                if status == "SUCCESS":
                    ver_str = (v_stdout or v_stderr or "OK").splitlines()[0] if (v_stdout or v_stderr) else "OK"
                    msg = f"{tool_name} installed and verified successfully! ({ver_str})"
                    if verified_path:
                        msg += f"\nLocation: {verified_path}"
                    _log_si("TERMINAL", f"Smart Install completed successfully for '{tool_name}'", run_id=run_id, details={"success": True, "message": msg})
                    self.smartInstallPostInstallVerified.emit(tool_name, "success", msg, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, True, msg, retry_action)

                elif status == "FIX":
                    # Initialize attempted fix commands tracking
                    if tool_name not in self._attempted_fix_commands:
                        self._attempted_fix_commands[tool_name] = []
                    _log_si("STATE_TRANSITION", f"Corrective fix proposed: '{fix_cmd}'", run_id=run_id, details={"state": "fix_proposed", "fix_command": fix_cmd})
                    self.smartInstallFixProposed.emit(tool_name, fix_cmd, explanation, retry_action, file_path, v_cmd, 1)
                    self.smartInstallPostInstallVerified.emit(tool_name, "fix_available", explanation, retry_action, file_path, "")

                elif status == "MANUAL_INSTALLATION_REQUIRED":
                    print(f"[SmartInstall] Manual installation required for {tool_name}")
                    msg = explanation or "Manual installation is required."
                    _log_si("TERMINAL", f"Manual installation required for '{tool_name}': {msg}", run_id=run_id, details={"success": False, "message": msg})
                    self.smartInstallPostInstallVerified.emit(tool_name, "manual_installation_required", msg, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, False, msg, retry_action)

                else:
                    err_msg = explanation or stderr or stdout or f"Process exited with code {install_exit}"
                    print(f"[SmartInstall] Installation failed with exit code {install_exit}:\n{err_msg}")
                    _log_si("TERMINAL", f"Installation failed for '{tool_name}': {err_msg}", run_id=run_id, details={"success": False, "message": err_msg})
                    self.smartInstallPostInstallVerified.emit(tool_name, "failed", err_msg, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, False, err_msg, retry_action)

            except Exception as e:
                import traceback
                traceback.print_exc()
                is_internal = isinstance(e, (AttributeError, TypeError, KeyError, NameError, UnboundLocalError, IndexError))
                err_prefix = f"Internal IDE error ({type(e).__name__})" if is_internal else "Execution error"
                err_str = f"{err_prefix}: {e}"
                print(f"[SmartInstall] {err_str}")
                _log_si("TERMINAL", f"Smart Install halted with error: {err_str}", run_id=run_id, details={"success": False, "error": err_str})
                self.smartInstallCompleted.emit(tool_name, False, err_str, retry_action)
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
        Enforces maximum 2 fix attempts per session and detects repeated commands to prevent infinite loops.
        """
        run_id = self._active_run_ids.get(tool_name) or f"si_{tool_name}_{int(time.time()*1000)%1000000}"
        print("[SmartInstall] User approved AI fix")
        _log_si(
            "USER_APPROVAL",
            f"User approved AI corrective fix for '{tool_name}' (attempt {fix_attempt_count})",
            run_id=run_id,
            details={"tool": tool_name, "fix_command": fix_command, "attempt_count": fix_attempt_count}
        )

        if not fix_command:
            _log_si("TERMINAL", f"Fix execution aborted: fix command is empty", run_id=run_id, details={"success": False, "reason": "empty command"})
            self.smartInstallCompleted.emit(tool_name, False, "Cannot execute fix: fix command is empty.", retry_action)
            return False

        if fix_attempt_count > 2:
            print("[SmartInstall] Maximum fix attempts (2) reached -> manual installation required")
            _log_si("RETRY_HALT", f"Maximum fix attempts (2) reached for '{tool_name}'", run_id=run_id, details={"attempt_count": fix_attempt_count})
            _log_si("TERMINAL", "Maximum fix attempts reached -> manual installation required", run_id=run_id, details={"success": False})
            self.smartInstallPostInstallVerified.emit(
                tool_name, "manual_installation_required",
                "Automated fix attempts reached the maximum limit (2). Manual installation is required.",
                retry_action, file_path, ""
            )
            self.smartInstallCompleted.emit(tool_name, False, "Maximum fix attempts reached.", retry_action)
            return False

        # 1. Validate command safety and structure before approval or loop checks
        is_safe, reason = self.validate_command_safety(fix_command, tool_name)
        print(f"[SmartInstall] Validated fix command: {fix_command} (is_safe={is_safe}, reason={reason})")
        _log_si(
            "COMMAND_VALIDATION",
            f"Fix command safety validation: {'PASS' if is_safe else 'FAIL'} - {reason}",
            run_id=run_id,
            details={"fix_command": fix_command, "is_safe": is_safe, "reason": reason}
        )
        if not is_safe:
            print(f"[SmartInstall] Execution blocked: {reason}")
            _log_si("TERMINAL", f"Fix execution blocked: {reason}", run_id=run_id, details={"success": False, "reason": reason})
            self.smartInstallCompleted.emit(tool_name, False, f"Execution halted: {reason}", retry_action)
            return False

        # 2. Loop prevention: check if this normalized command was already attempted
        if tool_name not in self._attempted_fix_commands:
            self._attempted_fix_commands[tool_name] = []

        norm_fix_cmd = self.normalize_command(fix_command)
        if norm_fix_cmd in self._attempted_fix_commands[tool_name]:
            print(f"[SmartInstall] Repeated failing fix command detected: {fix_command}. Halting loop.")
            msg = f"Repeated fix command '{fix_command}' detected. Manual intervention is required."
            _log_si("RETRY_HALT", f"Repeated fix command halted: '{fix_command}'", run_id=run_id, details={"command": fix_command, "normalized": norm_fix_cmd})
            _log_si("TERMINAL", f"Fix halted: {msg}", run_id=run_id, details={"success": False, "reason": msg})
            self.smartInstallPostInstallVerified.emit(tool_name, "manual_installation_required", msg, retry_action, file_path, "")
            self.smartInstallCompleted.emit(tool_name, False, msg, retry_action)
            return False

        self._attempted_fix_commands[tool_name].append(norm_fix_cmd)

        is_elevated = any(k in fix_command.lower() for k in ("winget", "choco", "sudo", "apt", "npm install -g", "pnpm add -g", "yarn global add"))
        _log_si(
            "PRIVILEGE_CHECK",
            f"Privilege check for fix command '{tool_name}': requires_elevation={is_elevated}",
            run_id=run_id,
            details={"requires_elevation": is_elevated, "fix_command": fix_command}
        )

        pre_path = locate_executable(executable) or locate_executable(tool_name)
        _log_si(
            "DETECTION",
            f"Pre-fix detection for '{tool_name}': {'Found at ' + pre_path if pre_path else 'Not found'}",
            run_id=run_id,
            details={"phase": "pre_fix", "tool": tool_name, "detected_path": pre_path or "None"}
        )

        print(f"[SmartInstall] Executing fix command: {fix_command}")
        print("[SmartInstall] AI fix execution started")
        _log_si("STATE_TRANSITION", f"State transitioned to 'installing': Running AI suggested fix", run_id=run_id, details={"state": "installing", "fix_command": fix_command, "executed_command": fix_command})
        self.smartInstallProgress.emit(tool_name, "installing", f"Running AI suggested fix: {fix_command}")

        working_dir = os.path.dirname(os.path.abspath(file_path)) if file_path and os.path.exists(file_path) else os.getcwd()

        def _fix_worker():
            try:
                fix_exit_code, fix_stdout, fix_stderr, step_results = self.execute_command_steps(
                    command_str=fix_command,
                    tool_name=tool_name,
                    timeout=300,
                    working_dir=working_dir,
                    run_id=run_id
                )

                print(f"[SmartInstall] AI fix exit code: {fix_exit_code}")
                print("[SmartInstall] Re-verification started")
                _log_si("STATE_TRANSITION", "State transitioned to 're-verifying': Re-verifying tool after fix", run_id=run_id, details={"state": "re_verifying"})
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

                _log_si(
                    "DETECTION",
                    f"Post-fix detection for '{tool_name}': {'Discovered at ' + verified_path if verified_path else 'Not found'}",
                    run_id=run_id,
                    details={"phase": "post_fix", "tool": tool_name, "verified_path": verified_path or "None"}
                )

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

                _log_si(
                    "VERIFICATION",
                    f"Post-fix verification command '{v_cmd}' completed with exit code {v_exit_code}",
                    run_id=run_id,
                    details={"command": v_cmd, "exit_code": v_exit_code, "stdout": v_stdout[:300], "stderr": v_stderr[:300]}
                )

                # Post-fix runtime resolution for Java / OpenJDK if applicable
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
                        try:
                            v_jdk = subprocess.run([java_exe, "-version"], capture_output=True, text=True, timeout=10)
                            v_jdk_txt = (v_jdk.stderr or v_jdk.stdout or "").strip()
                            print(f"[SmartInstall] Directly verified installed runtime: {v_jdk_txt}")
                        except Exception as ej:
                            print(f"[SmartInstall] Direct verification notice: {ej}")

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

                # Retry actual operation and capture real result
                op_exit_code = 0
                op_stdout = ""
                op_stderr = ""
                if retry_action == "format":
                    _log_si("STATE_TRANSITION", "State transitioned to 'retrying': Retrying actual operation with updated runtime", run_id=run_id, details={"state": "retrying"})
                    self.smartInstallProgress.emit(tool_name, "retrying", "Retrying actual operation with updated runtime...")
                    _log_si(
                        "OPERATION_RETRY",
                        f"Retrying original operation '{retry_action}' for '{tool_name}' after fix",
                        run_id=run_id,
                        details={"operation": retry_action, "file_path": file_path, "tool": tool_name}
                    )
                    op_exit_code, op_stdout, op_stderr = self.retry_formatting_operation(
                        tool_name=tool_name,
                        file_path=file_path,
                        executable=executable,
                        verified_path=verified_path
                    )
                    _log_si(
                        "OPERATION_RETRY",
                        f"Post-fix operation retry {'succeeded' if op_exit_code == 0 else 'failed with exit code ' + str(op_exit_code)}",
                        run_id=run_id,
                        details={"exit_code": op_exit_code, "error": op_stderr, "resolved": (op_exit_code == 0)}
                    )
                    self.originalOperationRetried.emit(tool_name, (op_exit_code == 0), op_stderr)

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
                    _log_si("TERMINAL", f"Fix operation succeeded for '{tool_name}'", run_id=run_id, details={"success": True, "message": msg})
                    self.smartInstallPostInstallVerified.emit(tool_name, "success", msg, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, True, msg, retry_action)
                elif status == "FIX":
                    if fix_attempt_count >= 2:
                        print("[SmartInstall] Maximum fix attempts (2) reached -> manual installation required")
                        msg = "Automated fix attempts reached the maximum limit (2). Manual installation is required."
                        _log_si("RETRY_HALT", f"Maximum fix attempts reached (attempt {fix_attempt_count})", run_id=run_id)
                        _log_si("TERMINAL", f"Manual installation required: {msg}", run_id=run_id, details={"success": False, "message": msg})
                        self.smartInstallPostInstallVerified.emit(tool_name, "manual_installation_required", msg, retry_action, file_path, "")
                        self.smartInstallCompleted.emit(tool_name, False, msg, retry_action)
                    else:
                        _log_si("STATE_TRANSITION", f"Next fix proposed: '{next_fix_cmd}'", run_id=run_id, details={"state": "fix_proposed", "next_fix": next_fix_cmd})
                        self.smartInstallFixProposed.emit(tool_name, next_fix_cmd, explanation, retry_action, file_path, v_cmd, fix_attempt_count + 1)
                        self.smartInstallPostInstallVerified.emit(tool_name, "fix_available", explanation, retry_action, file_path, "")
                elif status == "MANUAL_INSTALLATION_REQUIRED":
                    _log_si("TERMINAL", f"Manual installation required: {explanation}", run_id=run_id, details={"success": False, "message": explanation})
                    self.smartInstallPostInstallVerified.emit(tool_name, "manual_installation_required", explanation, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, False, explanation, retry_action)
                else:
                    err_msg = explanation or op_stderr or fix_stderr or f"Operation failed with code {op_exit_code}"
                    _log_si("TERMINAL", f"Fix failed for '{tool_name}': {err_msg}", run_id=run_id, details={"success": False, "message": err_msg})
                    self.smartInstallPostInstallVerified.emit(tool_name, "failed", err_msg, retry_action, file_path, "")
                    self.smartInstallCompleted.emit(tool_name, False, err_msg, retry_action)

            except Exception as e:
                import traceback
                traceback.print_exc()
                is_internal = isinstance(e, (AttributeError, TypeError, KeyError, NameError, UnboundLocalError, IndexError))
                err_prefix = f"Internal IDE error ({type(e).__name__})" if is_internal else "Fix error"
                err_str = f"{err_prefix}: {e}"
                print(f"[SmartInstall] Fix execution exception: {err_str}")
                _log_si("TERMINAL", f"Fix execution halted with error: {err_str}", run_id=run_id, details={"success": False, "error": err_str})
                self.smartInstallCompleted.emit(tool_name, False, err_str, retry_action)
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

    # =========================================================================
    # GENERAL BACKGROUND SMART FIX & ERROR RECOVERY
    # =========================================================================

    @Slot(str, str, str, str, int, str, str, str, result="QVariantMap")
    @Slot(str, str, str, str, int, str, str, result="QVariantMap")
    @Slot(str, str, str, str, result="QVariantMap")
    @Slot(str, str, result="QVariantMap")
    def classify_workflow_failure(
        self,
        operation: str,
        error_message: str,
        stderr: str = "",
        stdout: str = "",
        exit_code: int = 1,
        command: str = "",
        file_path: str = "",
        language: str = ""
    ) -> dict:
        """Classifies a workflow failure into one of 12 structured error categories."""
        return self.classify_failure(
            operation=operation,
            error_message=error_message,
            stderr=stderr,
            stdout=stdout,
            exit_code=exit_code,
            command=command,
            file_path=file_path,
            language=language
        )

    @staticmethod
    def classify_failure(
        operation: str = "",
        error_message: str = "",
        stderr: str = "",
        stdout: str = "",
        exit_code: int = 1,
        command: str = "",
        file_path: str = "",
        language: str = ""
    ) -> Dict[str, Any]:
        """
        Classifies an operational failure across 12 structured error categories:
        1. timeout_or_cancellation
        2. transient
        3. permission_failure
        4. network_failure
        5. unsupported_runtime_version
        6. syntax_error
        7. test_failure
        8. runtime_exception
        9. invalid_configuration
        10. missing_dependency
        11. missing_or_incompatible_extension
        12. unknown
        """
        combined = f"{operation} {command} {error_message} {stderr} {stdout}".lower()

        # 1. Timeout or cancellation
        if exit_code in (-2, 130, 124) or any(k in combined for k in ("timeoutexpired", "timed out", "operation timed out", "cancelled by user", "sigint", "keyboardinterrupt", "interrupted")):
            return {
                "category": "timeout_or_cancellation",
                "likely_cause": "Process execution timed out or was interrupted by user",
                "is_transient": True
            }

        # 2. Transient locks / environment
        if "1618" in combined or any(k in combined for k in ("another installation is in progress", "resource temporarily unavailable", "ebusy", "file is locked", "port already in use")):
            return {
                "category": "transient",
                "likely_cause": "Transient file lock or active concurrent process in progress",
                "is_transient": True
            }

        # 3. Permission / privilege
        if exit_code in (13, 126) or any(k in combined for k in ("permissionerror", "permission denied", "access is denied", "eacces", "operation not permitted", "requires elevation", "run as administrator")):
            return {
                "category": "permission_failure",
                "likely_cause": "Permission or access rights denied by operating system",
                "is_transient": False
            }

        # 4. Network / package-manager
        if any(k in combined for k in ("connectionrefusederror", "socket.timeout", "connection timed out", "could not resolve host", "failed to fetch", "getaddrinfo failed", "network is unreachable", "etimedout", "enotfound", "temporary failure in name resolution")):
            return {
                "category": "network_failure",
                "likely_cause": "Network connection unreachable, timeout, or DNS resolution failure",
                "is_transient": True
            }

        # 5. Unsupported runtime version
        if any(k in combined for k in ("unsupportedclassversionerror", "has been compiled by a more recent version of the java runtime", "requires java 21", "python 3.10+ required", "unsupported runtime", "unsupported version", "incompatible java version")):
            return {
                "category": "unsupported_runtime_version",
                "likely_cause": "Installed runtime version does not meet minimum requirements for tool/program",
                "is_transient": False
            }

        # 6. Syntax or compilation error
        if any(k in combined for k in ("syntaxerror", "indentationerror", "expected ';'", "expected '}'", "unexpected token", "parse error", "syntax error:", "error: expected expression", "error: unknown type name", "cannot parse", "syntax error")):
            return {
                "category": "syntax_error",
                "likely_cause": "Syntax or parse error in user code / source files",
                "is_transient": False
            }

        # 7. Test failure / assertion
        if operation in ("test", "pytest", "unittest") or "test" in command.lower() or any(k in combined for k in ("assertionerror", "failed (failures=", "test failed", "fail: test", "assertion failure", "failed (errors=", "tests failed")):
            return {
                "category": "test_failure",
                "likely_cause": "Unit test or assertion condition failed in user program",
                "is_transient": False
            }

        # 8. User-code runtime exception
        if any(k in combined for k in ("zerodivisionerror", "indexerror", "keyerror", "attributeerror", "typeerror", "valueerror", "nullpointerexception", "segmentation fault", "core dumped", "panic!", "fatal error:", "traceback (most recent call last)")):
            return {
                "category": "runtime_exception",
                "likely_cause": "Unhandled exception or crash in application logic",
                "is_transient": False
            }

        # 9. Invalid configuration
        if any(k in combined for k in ("invalidconfiguration", "configuration error", "invalid config", "missing required configuration", "bad option:", "unrecognized argument", "config error")):
            return {
                "category": "invalid_configuration",
                "likely_cause": "Invalid configuration file, option, or missing setting",
                "is_transient": False
            }

        # 10. Missing dependency / executable / runner
        if any(k in combined for k in (
            "command not found", "is not recognized as an internal or external command",
            "no such file or directory", "modulenotfounderror", "importerror: no module named",
            "executable file not found", "cannot find", "package was not found",
            "not installed", "missing executable", "no runner configured", "no runner",
            "missing runner", "no sql runner"
        )):
            return {
                "category": "missing_dependency",
                "likely_cause": "Required tool, executable, or runner is not installed or not in PATH",
                "is_transient": False
            }

        return {
            "category": "unknown",
            "likely_cause": "Unclassified operational error",
            "is_transient": False
        }

    @Slot(str, str, str, result="QVariantMap")
    @Slot(str, str, result="QVariantMap")
    @Slot(str, result="QVariantMap")
    def find_compatible_marketplace_extension(self, tool_or_lang: str, file_ext: str = "", file_path: str = "") -> dict:
        """
        Checks whether a compatible extension exists in DGX Studio Extensions marketplace
        or local installed extensions. Prefers activation of installed disabled extensions.
        """
        clean_t = (tool_or_lang or "").lower().strip()
        clean_e = (file_ext or "").lower().strip()
        if not clean_e and file_path:
            clean_e = os.path.splitext(file_path)[1].lower()
        if clean_e and not clean_e.startswith("."):
            clean_e = f".{clean_e}"

        cur_os = get_current_os()
        cur_arch = platform.machine().lower()

        # 1. Check if matching extension is already installed
        for ext_id, ext in self._extensions.items():
            entry = DGX_MARKETPLACE_EXTENSIONS.get(ext_id, {})
            tools = [x.lower() for x in entry.get("tools", [])]
            langs = [x.lower() for x in (ext.languages or entry.get("languages", []))]
            exts = [x.lower() for x in (ext.extensions or entry.get("extensions", []))]

            matches = (
                clean_t in tools or
                clean_t in langs or
                (clean_e and clean_e in exts) or
                clean_t in (ext_id.lower(), ext.name.lower())
            )
            if matches:
                if not ext.enabled or ext_id in self._disabled_ids:
                    return {
                        "compatible": True,
                        "action": "activate",
                        "extension_id": ext_id,
                        "name": ext.displayName or ext.name,
                        "description": ext.description,
                        "extension": ext.to_dict(),
                        "entry": entry
                    }
                else:
                    return {}

        # 2. Check marketplace catalog
        for ext_id, entry in DGX_MARKETPLACE_EXTENSIONS.items():
            tools = [x.lower() for x in entry.get("tools", [])]
            langs = [x.lower() for x in entry.get("languages", [])]
            exts = [x.lower() for x in entry.get("extensions", [])]

            matches = (
                clean_t in tools or
                clean_t in langs or
                (clean_e and clean_e in exts) or
                clean_t in (ext_id.lower(), entry.get("name", "").lower())
            )
            if matches:
                supported_os = entry.get("supported_os", ["windows", "macos", "linux"])
                supported_arch = entry.get("supported_arch", ["x86_64", "arm64", "amd64", "x86", "aarch64"])
                os_ok = cur_os in supported_os or "all" in supported_os
                arch_ok = any(a in cur_arch for a in supported_arch) or "all" in supported_arch

                if os_ok and arch_ok:
                    return {
                        "compatible": True,
                        "action": "install",
                        "extension_id": ext_id,
                        "name": entry["name"],
                        "description": entry["description"],
                        "entry": entry
                    }

        return {}

    @Slot(str, str, str, str, str, result=bool)
    @Slot(str, str, str, str, result=bool)
    @Slot(str, str, str, result=bool)
    @Slot(str, str, result=bool)
    def execute_extension_recovery(
        self,
        extension_id: str,
        action: str = "install",
        tool_name: str = "",
        retry_action: str = "",
        file_path: str = ""
    ) -> bool:
        """
        Executes extension installation or activation as part of background error recovery,
        verifies the capability is available, and retries the original operation.
        """
        run_id = self._get_run_id(tool_name or extension_id)
        _log_si(
            "MARKETPLACE_EXECUTION",
            f"Executing extension recovery: action='{action}', extension_id='{extension_id}'",
            run_id=run_id,
            details={"extension_id": extension_id, "action": action, "tool": tool_name, "retry_action": retry_action}
        )
        self.smartInstallProgress.emit(tool_name or extension_id, "installing", f"{'Enabling' if action in ('enable', 'activate') else 'Installing'} extension {extension_id}...")

        success = False
        msg = ""
        if action in ("enable", "activate"):
            success = self.toggle_extension(extension_id, True)
            if success:
                msg = f"Extension '{extension_id}' enabled successfully."
            else:
                msg = f"Failed to enable extension '{extension_id}'."
        else:
            ext_entry = DGX_MARKETPLACE_EXTENSIONS.get(extension_id, {})
            folder_name = ext_entry.get("folder", extension_id.split(".")[-1]) if ext_entry else extension_id.split(".")[-1]
            candidate_paths = [
                os.path.join(self.built_in_dir, folder_name),
                os.path.join(self.base_dir, "extensions", folder_name),
            ]
            ext_path = None
            for cp in candidate_paths:
                if os.path.isdir(cp):
                    ext_path = cp
                    break

            if ext_path:
                success = self.install_local_extension(ext_path)
                if success:
                    msg = f"Extension '{extension_id}' installed from marketplace."
                else:
                    msg = f"Failed to install extension package from {ext_path}."
            else:
                if extension_id in self._extensions:
                    success = self.toggle_extension(extension_id, True)
                    msg = f"Extension '{extension_id}' activated."
                else:
                    success = False
                    msg = f"Extension '{extension_id}' not found in local marketplace repository."

        _log_si(
            "MARKETPLACE_EXECUTION",
            f"Extension recovery outcome: success={success}, message='{msg}'",
            run_id=run_id,
            details={"success": success, "message": msg}
        )

        if not success:
            self.smartInstallCompleted.emit(tool_name or extension_id, False, msg, retry_action)
            return False

        # Post-install verification: Verify extension is loaded and active
        self.reload_extensions()
        ext_obj = self.get_extension(extension_id)
        if not ext_obj or not ext_obj.enabled:
            err = f"Extension '{extension_id}' installed but not active."
            self.smartInstallCompleted.emit(tool_name or extension_id, False, err, retry_action)
            return False

        # Now independently retry original operation if requested
        if retry_action:
            self.smartInstallProgress.emit(tool_name or extension_id, "retrying", "Retrying original operation...")
            op_exit = 0
            op_err = ""
            if retry_action == "format":
                op_exit, op_out, op_err = self.retry_formatting_operation(
                    tool_name=tool_name,
                    file_path=file_path,
                    executable="",
                    verified_path=""
                )
            elif retry_action in ("run", "build", "test", "compile"):
                op_exit, op_out, op_err = self.retry_operation(
                    operation=retry_action,
                    command="",
                    file_path=file_path
                )

            self.originalOperationRetried.emit(tool_name or extension_id, (op_exit == 0), op_err)
            if op_exit == 0:
                full_msg = f"{msg}\nOriginal {retry_action} operation succeeded!"
                self.smartInstallCompleted.emit(tool_name or extension_id, True, full_msg, retry_action)
                self.smartInstallPostInstallVerified.emit(tool_name or extension_id, "success", full_msg, retry_action, file_path, "")
                return True
            else:
                full_err = f"{msg}, but original operation failed on retry: {op_err}"
                self.smartInstallCompleted.emit(tool_name or extension_id, False, full_err, retry_action)
                return False
        else:
            self.smartInstallCompleted.emit(tool_name or extension_id, True, msg, retry_action)
            return True

    def retry_operation(
        self,
        operation: str,
        command: str = "",
        file_path: str = "",
        working_dir: str = "",
        timeout: int = 30
    ) -> Tuple[int, str, str]:
        """
        Executes a retry of the original failed operation (run, build, test, etc.)
        and returns (exit_code, stdout, stderr).
        """
        cmd = command
        cwd = working_dir
        if not cwd and file_path and os.path.exists(file_path):
            cwd = os.path.dirname(os.path.abspath(file_path))
        if not cwd:
            cwd = os.getcwd()

        if not cmd and file_path:
            ext = os.path.splitext(file_path)[1].lower().lstrip(".")
            runner = self.get_runner_for_extension(ext)
            if runner and runner.get("command"):
                cmd = runner["command"].replace("${filePath}", file_path)
            elif ext == "py":
                cmd = f'"{sys.executable}" "{file_path}"'
            elif ext in ("js", "mjs"):
                cmd = f'node "{file_path}"'
            elif ext == "go":
                cmd = f'go run "{file_path}"'
            elif ext == "rs":
                cmd = f'rustc "{file_path}" -o output.exe'

        if not cmd:
            return 1, "", f"No command available to retry {operation} operation."

        print(f"[SmartInstall] Retrying original operation [{operation}]: {cmd} (cwd: {cwd})")
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=timeout)
            print(f"[SmartInstall] Retry exit code: {proc.returncode}")
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Operation timed out after {timeout} seconds."
        except Exception as e:
            return 1, "", str(e)

    def _diagnose_code_failure(self, category: str, error_msg: str, file_path: str = "", language: str = "") -> str:
        """
        Generates contextual code diagnosis for syntax, runtime, and test errors
        without attempting to modify files or install tools.
        """
        if ExtensionManager._custom_ai_resolver and callable(ExtensionManager._custom_ai_resolver):
            try:
                diag_prompt = (
                    f"Diagnose this {category} error concisely without suggesting tool installations:\n"
                    f"File: {file_path}\n"
                    f"Language: {language}\n"
                    f"Error: {error_msg[:400]}\n"
                    f"Provide: 1. Root cause. 2. Safe fix in code."
                )
                ai_diag = ExtensionManager._custom_ai_resolver(diag_prompt)
                if ai_diag and ai_diag.strip():
                    return ai_diag.strip()
            except Exception:
                pass

        err_lower = error_msg.lower()
        if "zerodivisionerror" in err_lower:
            return "ZeroDivisionError: Division by zero encountered. Validate the divisor value before arithmetic operations."
        if "indexerror" in err_lower:
            return "IndexError: Sequence index out of range. Check list/array bounds before accessing elements."
        if "keyerror" in err_lower:
            return "KeyError: Key not found in mapping. Check dictionary keys or use .get() with a default value."
        if "syntaxerror" in err_lower or "indentationerror" in err_lower:
            return f"SyntaxError in {os.path.basename(file_path) if file_path else 'code'}: Check closing parentheses, indentation, or missing syntax tokens."
        if "assertionerror" in err_lower or category == "test_failure":
            return f"Assertion failure during testing: Test condition evaluated to False. Review expected vs actual test values."
        if "nullpointerexception" in err_lower:
            return "NullPointerException: Object reference is null. Ensure object is instantiated before dereferencing."

        return f"{category.replace('_', ' ').title()}: {error_msg.strip()[:300]}"

    @Slot("QVariantMap", result="QVariantMap")
    def diagnose_and_recover_workflow_failure(self, context: dict) -> dict:
        """
        AI-driven workflow failure recovery across all DGX Studio workflows.
        Collects failure context, diagnoses with SmartEngine, and returns actionable proposal.
        """
        operation = context.get("operation") or "run"
        tool_name = context.get("toolName") or context.get("executable") or ""
        command = context.get("command") or context.get("commandAttempted") or ""
        exit_code = context.get("exitCode", context.get("exit_code", 1))
        error_msg = context.get("errorMessage") or context.get("stderr") or context.get("error_message") or ""
        file_path = context.get("filePath") or context.get("file_path") or ""
        language = (context.get("language") or context.get("languageId") or "").lower().strip()
        retry_act = context.get("retryAction") or operation
        run_id = context.get("runId") or f"sf_{int(time.time()*1000)%1000000}"
        context["runId"] = run_id

        # Deduplication check
        fp = f"{operation}:{tool_name}:{command}:{exit_code}:{error_msg[:80]}"
        now = time.time()
        if hasattr(self, "_recent_failure_fingerprints"):
            last_time = self._recent_failure_fingerprints.get(fp, 0)
            if now - last_time < 5.0:
                pass
        else:
            self._recent_failure_fingerprints = {}
        self._recent_failure_fingerprints[fp] = now

        # Add diagnostic hints to context without bypassing AI
        classification = self.classify_failure(
            operation=operation,
            error_message=error_msg,
            stderr=context.get("stderr", ""),
            stdout=context.get("stdout", ""),
            exit_code=exit_code,
            command=command,
            file_path=file_path,
            language=language
        )
        context["category"] = classification.get("category", "unknown")
        context["likelyCause"] = classification.get("likely_cause", "")

        # AI-driven recovery resolution
        proposal = self.resolve_smart_install_context(context)
        proposal = self._attach_command_recovery_session_if_needed(context, proposal)
        return proposal

    @Slot("QVariantMap")
    def start_background_workflow_recovery(self, context: dict):
        """Dispatches workflow failure diagnosis and recovery to a background worker thread."""
        def _worker():
            try:
                self.diagnose_and_recover_workflow_failure(context)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[SmartInstall] Background workflow recovery error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    @Slot(str, str, str, str, str, str, result=bool)
    @Slot(str, str, str, str, str, result=bool)
    @Slot(str, str, str, str, result=bool)
    @Slot(str, str, str, result=bool)
    def execute_smart_fix(
        self,
        fix_type: str,
        target_id: str,
        command: str = "",
        retry_action: str = "",
        file_path: str = "",
        run_id: str = ""
    ) -> bool:
        """
        Executes a user-approved Smart Fix action:
        - "extension_install" / "extension_activate"
        - "command"
        - "runtime_config"
        """
        if fix_type in ("extension_install", "extension_activate"):
            action = "activate" if fix_type == "extension_activate" else "install"
            return self.execute_extension_recovery(target_id, action, target_id, retry_action, file_path)
        elif fix_type == "runtime_config":
            if target_id == "java" or "google-java-format" in target_id.lower():
                compat = find_compatible_jdk(min_version=21)
                if compat:
                    self.set_tool_runtime_config(target_id, {
                        "JAVA_HOME": compat["path"],
                        "java_path": compat["java_exe"],
                        "version": compat.get("version", "21+")
                    })
                    if retry_action == "format":
                        op_exit, op_out, op_err = self.retry_formatting_operation(
                            tool_name=target_id,
                            file_path=file_path,
                            executable="",
                            verified_path=""
                        )
                        self.originalOperationRetried.emit(target_id, (op_exit == 0), op_err)
                        self.smartInstallCompleted.emit(target_id, (op_exit == 0), "Runtime configured.", retry_action)
                        return op_exit == 0
            return True
        else:
            return self.execute_smart_install_command(target_id, command, target_id, retry_action, file_path)

    # =============================================================================
    # AI COMMAND PLANNING & EXECUTION TRACKING
    # =============================================================================

    def _query_ai_backend(self, prompt: str) -> Tuple[bool, str, str]:
        """
        Reuses existing AI backend pipeline to query the model.
        Returns: (success: bool, response_text: str, error_msg: str)
        """
        response_text = ""
        error_msg = ""
        
        # 1. Custom AI resolver (used by tests or custom providers)
        if ExtensionManager._custom_ai_resolver and callable(ExtensionManager._custom_ai_resolver):
            try:
                response_text = ExtensionManager._custom_ai_resolver(prompt)
                if response_text:
                    return True, response_text, ""
            except Exception as e:
                error_msg = str(e)
                
        # 2. AIBackend instance
        if not response_text:
            try:
                from AIBackend import AIBackend
                ai_backend = self.ai_backend or AIBackend.get_instance()
                if ai_backend:
                    response_text = ai_backend.ask(prompt)
                    if response_text:
                        return True, response_text, ""
            except Exception as ex:
                if not error_msg:
                    error_msg = str(ex)
                    
        # 3. ChatGPTClient
        if not response_text:
            try:
                from CustomApi import ChatGPTClient
                client = ChatGPTClient(headless=True)
                if hasattr(client, "is_connected") and client.is_connected:
                    response_text = client.ask(prompt, timeout=15)
                    if response_text:
                        return True, response_text, ""
            except Exception as ex:
                if not error_msg:
                    error_msg = str(ex)

        if response_text:
            return True, response_text, ""
        return False, "", error_msg or "AI backend returned empty response or is unavailable."

    def _create_fallback_commands(self, proposal: dict, context: dict) -> List[dict]:
        """
        Generates safe, deterministic fallback commands when AI planner is offline or unavailable.
        """
        cmd_str = proposal.get("command", "")
        tool_name = context.get("toolName") or context.get("executable") or "tool"
        v_cmd = proposal.get("verifyCommand") or f"{tool_name} --version"
        commands = []
        if v_cmd:
            commands.append({
                "command": v_cmd,
                "purpose": f"Check if {tool_name} is already available and verified",
                "requires_approval": False,
                "expected_result": "Version string printed",
                "failure_handling": "continue"
            })
        if cmd_str:
            commands.append({
                "command": cmd_str,
                "purpose": f"Install {tool_name}",
                "requires_approval": True,
                "expected_result": "Exit code 0",
                "failure_handling": "abort"
            })
        if v_cmd and cmd_str:
            commands.append({
                "command": v_cmd,
                "purpose": f"Verify {tool_name} after installation",
                "requires_approval": False,
                "expected_result": "Version string printed",
                "failure_handling": "abort"
            })
        return commands

    def _build_ai_command_planner_prompt(self, session: RecoverySession, proposal: Optional[dict] = None) -> str:
        ctx = session.context
        tool_name = ctx.get("toolName") or ctx.get("executable") or "tool"
        op = ctx.get("operation", "operation")
        cat = ctx.get("category", "missing_dependency")
        err = ctx.get("error_message") or ctx.get("stderr") or ""
        
        history_str = ""
        if session.command_history:
            history_items = [c.format_result() for c in session.command_history]
            history_str = "\n\n".join(history_items)
        else:
            history_str = "(No commands executed yet)"

        user_decisions_str = ""
        if session.user_decisions:
            user_decisions_str = "\n".join([f"- {k}: {v}" for k, v in session.user_decisions.items()])
        else:
            user_decisions_str = "(No prior user decisions)"

        prop_info = f"{proposal.get('title', '')} - {proposal.get('explanation', '')}" if proposal else "Recovery strategy in progress"

        prompt = f"""You are DGX Studio's AI Command Planner and Error Recovery Engine.
Your job is to analyze the operational failure and propose a structured sequence of safe, individual commands to diagnose, install, configure, or verify developer tools and dependencies.

CONTEXT:
Operation: {op}
Tool: {tool_name}
Category: {cat}
Error: {err}
Initial Strategy: {prop_info}
Current OS: {get_current_os()}
Available Command Budget Remaining: {session.commands_remaining} / {session.maximum_commands}

USER DECISIONS AND CLARIFICATIONS:
{user_decisions_str}

PREVIOUS EXECUTED COMMANDS AND ACTUAL RESULTS:
{history_str}

RULES:
1. One command execution equals one step. Do NOT combine multiple commands using '&&', ';', '|', or shell scripts.
2. Propose AT MOST 4 commands in a single batch.
3. Only batch commands that are safe to propose together without assuming unverified outcomes.
   - Check availability or version first.
   - Installing a missing tool requires user approval and depends on whether it is actually missing.
   - Verification depends on the installation result.
4. Mark 'requires_approval: true' for any command that installs packages, modifies system files, or changes environment settings. Mark 'requires_approval: false' for harmless query/read commands (like --version or which).
5. If clarification or user choice is needed (e.g. ambiguous toolchain, missing configuration, multiple recovery strategies), set 'needs_user_decision: true' and provide a structured 'decision_request' object:
   {{
     "question": "The question to ask the user",
     "why_necessary": "Why this choice is necessary",
     "choices": ["Choice 1", "Choice 2"],
     "allow_custom_answer": true,
     "resume_key": "parameter_name"
   }}
6. If the issue is already resolved (e.g. verified tool is working), set 'recovery_complete: true' and provide 'final_report'.
7. If recovery cannot proceed with available information or capabilities, set 'cannot_resolve: true' and provide 'final_report'.
8. If no more commands are needed or can be run, set 'recovery_complete: true' and provide 'final_report'.

RESPONSE FORMAT (JSON ONLY, NO MARKDOWN OUTSIDE JSON):
{{
  "plan_changed": true,
  "proposed_total_steps": 3,
  "commands": [
    {{
      "command": "{tool_name} --version",
      "purpose": "Check if {tool_name} is already installed on PATH",
      "requires_approval": false,
      "expected_result": "Version printed",
      "failure_handling": "continue"
    }}
  ],
  "needs_user_decision": false,
  "decision_request": null,
  "cannot_resolve": false,
  "recovery_complete": false,
  "final_report": ""
}}
"""
        return prompt

    def create_recovery_session(self, context: dict, maximum_commands: int = 10) -> RecoverySession:
        if not hasattr(self, "_smart_engine") or self._smart_engine is None:
            self._smart_engine = SmartEngine(extension_manager=self)
            self._recovery_sessions = self._smart_engine._sessions
        session = self._smart_engine.create_session(context, maximum_commands=maximum_commands)
        self._recovery_sessions[session.session_id] = session
        self._active_recovery_session_id = session.session_id
        return session

    def query_ai_command_plan(self, session: RecoverySession, proposal: Optional[dict] = None) -> Tuple[bool, dict, str]:
        if not hasattr(self, "_smart_engine") or self._smart_engine is None:
            self._smart_engine = SmartEngine(extension_manager=self)
            self._recovery_sessions = self._smart_engine._sessions
        prompt = build_smart_prompt(session, session.context)
        success, response_text, err = self._smart_engine._query_ai(prompt)
        if not success or not response_text:
            return False, {}, err or "AI service returned empty response"
        ok, parsed, p_err = parse_smart_response(response_text, fallback_tool=session.context.get("toolName", ""))
        return ok, parsed, p_err

    def start_command_recovery_session(
        self,
        context: dict,
        proposal: Optional[dict] = None,
        maximum_commands: int = 10
    ) -> RecoverySession:
        if not hasattr(self, "_smart_engine") or self._smart_engine is None:
            self._smart_engine = SmartEngine(extension_manager=self)
            self._recovery_sessions = self._smart_engine._sessions
        session = self.create_recovery_session(context, maximum_commands=maximum_commands)
        if proposal:
            if proposal.get("needs_user_decision") or proposal.get("status") == "awaiting_user_decision":
                session.status = "awaiting_user_decision"
                session.decision_request = proposal.get("decision_request")
            elif proposal.get("commands"):
                session.accept_new_batch(proposal["commands"], proposal.get("proposed_total_steps"))
                first_cmd = session.active_batch[0] if session.active_batch else None
                if first_cmd and first_cmd.requires_approval and not first_cmd.approved:
                    session.status = "awaiting_approval"
                    session.waiting_for_approval_cmd = first_cmd
                else:
                    session.status = "ready"
            elif proposal.get("cannot_resolve"):
                session.status = "cannot_resolve"
                session.final_report = proposal.get("final_report", "Cannot resolve.")
        self.recoveryPlanUpdated.emit(session.to_dict())
        return session

    def execute_session_command(
        self,
        session_id: str,
        command_id: str,
        executor_fn: Optional[Callable] = None
    ) -> Tuple[bool, str]:
        if not hasattr(self, "_smart_engine") or self._smart_engine is None:
            self._smart_engine = SmartEngine(extension_manager=self)
            self._recovery_sessions = self._smart_engine._sessions
        return self._smart_engine.execute_session_action(session_id, command_id)

    @Slot(str, str, result=bool)
    def approve_recovery_command(self, session_id: str, command_id: str, executor_fn=None) -> bool:
        if not hasattr(self, "_smart_engine") or self._smart_engine is None:
            self._smart_engine = SmartEngine(extension_manager=self)
            self._recovery_sessions = self._smart_engine._sessions
        return self._smart_engine.approve_action(session_id, command_id)

    @Slot(str, result=bool)
    def replan_recovery_session(self, session_id: str, executor_fn=None) -> bool:
        if not hasattr(self, "_smart_engine") or self._smart_engine is None:
            self._smart_engine = SmartEngine(extension_manager=self)
            self._recovery_sessions = self._smart_engine._sessions
        return self._smart_engine.replan_session(session_id)

    @Slot(str, str, result=bool)
    @Slot(str, str, str, result=bool)
    def submit_user_decision(self, session_id: str, decision: str, key: str = "", executor_fn=None) -> bool:
        if not hasattr(self, "_smart_engine") or self._smart_engine is None:
            self._smart_engine = SmartEngine(extension_manager=self)
            self._recovery_sessions = self._smart_engine._sessions
        return self._smart_engine.submit_user_decision(session_id, decision, key)

    @Slot(str, result=bool)
    def step_recovery_session(self, session_id: str, executor_fn=None) -> bool:
        session = self._recovery_sessions.get(session_id)
        if not session or not session.active_batch:
            return False
        first_act = session.active_batch[0]
        if first_act.requires_approval and not first_act.approved:
            session.status = "awaiting_approval"
            session.waiting_for_approval_cmd = first_act
            self.recoveryPlanUpdated.emit(session.to_dict())
            return False
        success, _ = self.execute_session_command(session_id, first_act.action_id, executor_fn=executor_fn)
        return success

    @Slot(str, result=bool)
    def execute_recovery_plan(self, session_id: str, executor_fn=None) -> bool:
        if not hasattr(self, "_smart_engine") or self._smart_engine is None:
            self._smart_engine = SmartEngine(extension_manager=self)
            self._recovery_sessions = self._smart_engine._sessions
        return self._smart_engine.execute_plan(session_id)

    @Slot(str, result=bool)
    def cancel_recovery_session(self, session_id: str) -> bool:
        session = self._recovery_sessions.get(session_id)
        if not session:
            return False
        session.status = "cancelled"
        session.final_report = "Recovery session cancelled by user."
        self.recoverySessionEnded.emit(session_id, False, session.final_report)
        self.recoveryPlanUpdated.emit(session.to_dict())
        return True

    @Slot(str, result="QVariantMap")
    def get_recovery_session(self, session_id: str) -> dict:
        """Returns the dictionary representation of a recovery session."""
        session = self._recovery_sessions.get(session_id) or (self._smart_engine.get_session(session_id) if hasattr(self, "_smart_engine") and self._smart_engine else None)
        return session.to_dict() if session else {}

    @Slot(result=list)
    def get_marketplace_extensions(self) -> list:
        """Returns the list of DGX Studio marketplace catalog extensions."""
        return list(DGX_MARKETPLACE_EXTENSIONS.values())


# =============================================================================
# DGX STUDIO EXTENSIONS MARKETPLACE CATALOG
# =============================================================================
DGX_MARKETPLACE_EXTENSIONS: Dict[str, Dict[str, Any]] = {
    "dgx.python": {
        "id": "dgx.python",
        "name": "Python Language Extension",
        "version": "1.0.0",
        "description": "Python language support, interpreter configuration, and PEP 8 formatters (autopep8, black, ruff).",
        "author": "DGX Studio",
        "languages": ["python"],
        "extensions": [".py", ".pyw"],
        "tools": ["python", "autopep8", "black", "ruff", "pip", "pytest"],
        "supported_os": ["windows", "macos", "linux"],
        "supported_arch": ["x86_64", "arm64", "amd64", "x86", "aarch64"],
        "folder": "python"
    },
    "dgx.cpp": {
        "id": "dgx.cpp",
        "name": "C/C++ Language Extension",
        "version": "1.0.0",
        "description": "C and C++ language support, compiler integrations (g++, gcc, clang), and clang-format provider.",
        "author": "DGX Studio",
        "languages": ["c", "cpp", "c++", "cuda"],
        "extensions": [".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".cu"],
        "tools": ["clang-format", "g++", "gcc", "clang", "clang++", "make", "cmake"],
        "supported_os": ["windows", "macos", "linux"],
        "supported_arch": ["x86_64", "arm64", "amd64", "x86", "aarch64"],
        "folder": "cpp"
    },
    "dgx.rust": {
        "id": "dgx.rust",
        "name": "Rust Language Extension",
        "version": "1.0.0",
        "description": "Rust language support, cargo runner, rustc compiler integration, and rustfmt formatter.",
        "author": "DGX Studio",
        "languages": ["rust"],
        "extensions": [".rs"],
        "tools": ["rustfmt", "rustc", "cargo"],
        "supported_os": ["windows", "macos", "linux"],
        "supported_arch": ["x86_64", "arm64", "amd64", "x86", "aarch64"],
        "folder": "rust"
    },
    "dgx.go": {
        "id": "dgx.go",
        "name": "Go Language Extension",
        "version": "1.0.0",
        "description": "Go language support, go build/run integration, and gofmt provider.",
        "author": "DGX Studio",
        "languages": ["go"],
        "extensions": [".go"],
        "tools": ["go", "gofmt"],
        "supported_os": ["windows", "macos", "linux"],
        "supported_arch": ["x86_64", "arm64", "amd64", "x86", "aarch64"],
        "folder": "go"
    },
    "dgx.javascript": {
        "id": "dgx.javascript",
        "name": "JavaScript / TypeScript Extension",
        "version": "1.0.0",
        "description": "JavaScript & TypeScript runtimes (Node.js, npx tsx) and Prettier code formatting.",
        "author": "DGX Studio",
        "languages": ["javascript", "typescript", "jsx", "tsx"],
        "extensions": [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"],
        "tools": ["node", "npx", "npm", "prettier", "tsx"],
        "supported_os": ["windows", "macos", "linux"],
        "supported_arch": ["x86_64", "arm64", "amd64", "x86", "aarch64"],
        "folder": "javascript"
    },
    "dgx.json": {
        "id": "dgx.json",
        "name": "JSON Language Extension",
        "version": "1.0.0",
        "description": "JSON formatting and validation.",
        "author": "DGX Studio",
        "languages": ["json"],
        "extensions": [".json"],
        "tools": [],
        "supported_os": ["windows", "macos", "linux"],
        "supported_arch": ["x86_64", "arm64", "amd64", "x86", "aarch64"],
        "folder": "json"
    },
    "dgx.qml": {
        "id": "dgx.qml",
        "name": "QML Language Extension",
        "version": "1.0.0",
        "description": "Qt Quick / QML language support and qmlformat.",
        "author": "DGX Studio",
        "languages": ["qml"],
        "extensions": [".qml"],
        "tools": ["qmlformat", "qmlscene"],
        "supported_os": ["windows", "macos", "linux"],
        "supported_arch": ["x86_64", "arm64", "amd64", "x86", "aarch64"],
        "folder": "qml"
    }
}

classify_failure = ExtensionManager.classify_failure

__all__ = [
    "ExtensionManager",
    "CommandRecord",
    "RecoverySession",
    "validate_ai_plan_response",
    "classify_failure",
    "DGX_MARKETPLACE_EXTENSIONS"
]


