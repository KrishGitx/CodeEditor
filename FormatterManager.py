import os
import sys
import re
import json
import shutil
import subprocess
from typing import Optional, Dict, Any
from ExtensionManager import ExtensionManager, Extension


LANG_TO_EXT = {
    "html": ".html", "htm": ".html",
    "javascript": ".js", "js": ".js",
    "typescript": ".ts", "ts": ".ts",
    "javascriptreact": ".jsx", "jsx": ".jsx",
    "typescriptreact": ".tsx", "tsx": ".tsx",
    "css": ".css", "scss": ".scss", "less": ".less",
    "json": ".json", "yaml": ".yaml", "yml": ".yaml",
    "markdown": ".md", "md": ".md",
    "python": ".py", "py": ".py",
    "c": ".c", "cpp": ".cpp", "c++": ".cpp", "cxx": ".cpp", "h": ".h", "hpp": ".hpp",
    "csharp": ".cs", "cs": ".cs", "java": ".java",
    "go": ".go", "golang": ".go",
    "rust": ".rs", "rs": ".rs",
}


class FormatterManager:
    def __init__(self, extension_manager: ExtensionManager):
        self.extension_manager = extension_manager

    def format_code(self, lang_id: str, file_path: str, source_code: str, tab_size: int = 4) -> Dict[str, Any]:
        """
        Formats source code using the registered extension for the target language.
        Returns a dictionary:
            {
                "success": bool,
                "formatted": str,
                "message": str,
                "available": bool,
                "extension_id": str (optional)
            }
        """
        if not source_code or not source_code.strip():
            return {
                "success": True,
                "formatted": source_code,
                "message": "Document is empty",
                "available": True
            }

        lang = (lang_id or "").lower().strip()
        ext_dot = os.path.splitext(file_path)[1].lower() if file_path else ""

        # Locate extension
        extension = self.extension_manager.get_extension_for_language(lang, file_path)

        if not extension or not extension.formatter:
            display_name = lang or ext_dot or "this language"
            return {
                "success": False,
                "formatted": source_code,
                "message": f"No formatter installed for {display_name}.",
                "available": False
            }

        formatter_spec = extension.formatter
        fmt_type = formatter_spec.get("type", "cli")

        # 1. Built-in Python Formatter
        if fmt_type == "python":
            return self._format_python(source_code, tab_size, extension)

        # 2. Built-in JSON Formatter
        if fmt_type == "json":
            return self._format_json(source_code, tab_size, extension)

        # 3. External CLI Formatter (clang-format, prettier, rustfmt, gofmt, etc.)
        if fmt_type == "cli":
            return self._format_cli(source_code, tab_size, file_path, lang, extension, formatter_spec)

        return {
            "success": False,
            "formatted": source_code,
            "message": f"Unsupported formatter provider type: {fmt_type}",
            "available": False,
            "extension_id": extension.id
        }

    def _format_python(self, source_code: str, tab_size: int, extension: Extension) -> Dict[str, Any]:
        # Priority 1: autopep8 module
        try:
            import autopep8
            formatted = autopep8.fix_code(source_code, options={"indent_size": tab_size})
            if formatted is not None:
                if formatted.strip() == source_code.strip():
                    return {
                        "success": True,
                        "formatted": source_code,
                        "message": "Python code is already formatted (PEP 8)",
                        "available": True,
                        "extension_id": extension.id
                    }
                return {
                    "success": True,
                    "formatted": formatted.rstrip() + "\n",
                    "message": "Python formatted (PEP 8)",
                    "available": True,
                    "extension_id": extension.id
                }
        except Exception as e:
            print("[FormatterManager] autopep8 notice:", e)

        # Priority 2: External black / ruff / autopep8 CLI
        is_win = sys.platform.startswith("win")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if is_win else 0

        for tool in ["black", "ruff", "autopep8"]:
            tool_path = extension.get_executable_path() or shutil.which(tool)
            if tool_path and os.path.exists(tool_path):
                try:
                    if tool == "black":
                        cmd = [tool_path, "-"]
                    elif tool == "ruff":
                        cmd = [tool_path, "format", "-"]
                    else:
                        cmd = [tool_path, f"--indent-size={tab_size}", "-"]
                    
                    proc = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        shell=is_win and tool_path.lower().endswith((".cmd", ".bat")),
                        creationflags=creationflags
                    )
                    stdout, stderr = proc.communicate(input=source_code, timeout=6)
                    if proc.returncode == 0 and stdout:
                        return {
                            "success": True,
                            "formatted": stdout.replace("\r\n", "\n"),
                            "message": f"Python formatted with {tool}",
                            "available": True,
                            "extension_id": extension.id
                        }
                except Exception as ex:
                    print(f"[FormatterManager] {tool} execution error:", ex)

        return {
            "success": False,
            "formatted": source_code,
            "message": "Python formatter (autopep8) is not installed. Run 'pip install autopep8' to enable.",
            "available": False,
            "extension_id": extension.id,
            "dependency": "autopep8",
            "installCommand": "pip install autopep8",
            "docsUrl": "https://pypi.org/project/autopep8/"
        }

    def _format_json(self, source_code: str, tab_size: int, extension: Extension) -> Dict[str, Any]:
        try:
            parsed = json.loads(source_code)
            formatted = json.dumps(parsed, indent=tab_size)
            return {
                "success": True,
                "formatted": formatted,
                "message": "JSON formatted successfully",
                "available": True,
                "extension_id": extension.id
            }
        except Exception as e:
            return {
                "success": False,
                "formatted": source_code,
                "message": f"JSON syntax error: {e}",
                "available": True,
                "extension_id": extension.id
            }

    def _resolve_effective_filepath(self, file_path: str, lang_id: str, extension: Extension) -> str:
        if file_path:
            _, ext = os.path.splitext(file_path)
            if ext and len(ext) > 1:
                return file_path

        lang = (lang_id or "").lower().strip()
        ext = LANG_TO_EXT.get(lang)
        if not ext and extension.extensions:
            ext = extension.extensions[0]
        if not ext:
            ext = ".txt"
        return f"temp{ext}"

    def _format_cli(self, source_code: str, tab_size: int, file_path: str, lang_id: str, extension: Extension, spec: dict) -> Dict[str, Any]:
        command_name = spec.get("command", "")
        if not command_name:
            return {
                "success": False,
                "formatted": source_code,
                "message": f"Extension '{extension.name}' has no command specified.",
                "available": False,
                "extension_id": extension.id
            }

        tool_path = extension.get_executable_path() or shutil.which(command_name)
        if not tool_path:
            cur_os = sys.platform.lower()
            os_key = "windows" if cur_os.startswith("win") else ("macos" if cur_os.startswith("darwin") else "linux")
            guide = spec.get("installGuide", {})
            install_cmd = guide.get(os_key, "") or guide.get("all", "")
            docs_url = guide.get("docsUrl", "")
            dep_name = spec.get("executable") or command_name
            return {
                "success": False,
                "formatted": source_code,
                "message": f"{extension.name} formatter ({dep_name}) is not installed.",
                "available": False,
                "extension_id": extension.id,
                "dependency": dep_name,
                "installCommand": install_cmd,
                "docsUrl": docs_url,
                "currentOs": os_key
            }

        effective_file_path = self._resolve_effective_filepath(file_path, lang_id, extension)

        # Substitute arguments
        raw_args = spec.get("args", [])
        resolved_args = []
        for arg in raw_args:
            replaced = str(arg).replace("${tabSize}", str(tab_size))
            replaced = replaced.replace("${filePath}", effective_file_path)
            resolved_args.append(replaced)

        cmd = [tool_path] + resolved_args

        is_win = sys.platform.startswith("win")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if is_win else 0
        use_shell = is_win and tool_path.lower().endswith((".cmd", ".bat"))

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                shell=use_shell,
                creationflags=creationflags
            )

            try:
                stdout, stderr = proc.communicate(input=source_code, timeout=6)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                return {
                    "success": False,
                    "formatted": source_code,
                    "message": f"{command_name} timed out after 6 seconds.",
                    "available": True,
                    "extension_id": extension.id
                }

            if proc.returncode == 0:
                if stdout:
                    clean_stdout = stdout.replace("\r\n", "\n")
                    if clean_stdout.strip() == source_code.strip():
                        return {
                            "success": True,
                            "formatted": source_code,
                            "message": "Document is already formatted",
                            "available": True,
                            "extension_id": extension.id
                        }
                    return {
                        "success": True,
                        "formatted": clean_stdout,
                        "message": f"Formatted with {command_name}",
                        "available": True,
                        "extension_id": extension.id
                    }
                else:
                    return {
                        "success": True,
                        "formatted": source_code,
                        "message": "Document is already formatted",
                        "available": True,
                        "extension_id": extension.id
                    }
            else:
                err_msg = (stderr or "").strip()
                err_msg = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', err_msg)
                err_msg = err_msg or f"{command_name} failed with exit code {proc.returncode}"
                return {
                    "success": False,
                    "formatted": source_code,
                    "message": f"{command_name} error: {err_msg}",
                    "available": True,
                    "extension_id": extension.id
                }
        except Exception as ex:
            return {
                "success": False,
                "formatted": source_code,
                "message": f"Formatter execution error: {ex}",
                "available": True,
                "extension_id": extension.id
            }
