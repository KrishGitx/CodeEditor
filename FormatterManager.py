import os
import sys
import re
import json
import shutil
import subprocess
from typing import Optional, Dict, Any
from ExtensionManager import ExtensionManager, Extension, resolve_python_tool, resolve_dotnet_global_tool, locate_executable


LANG_TO_EXT = {
    "html": ".html", "htm": ".html",
    "javascript": ".js", "js": ".js",
    "typescript": ".ts", "ts": ".ts",
    "javascriptreact": ".jsx", "jsx": ".jsx",
    "typescriptreact": ".tsx", "tsx": ".tsx",
    "css": ".css", "scss": ".scss", "less": ".less",
    "json": ".json", "yaml": ".yaml", "yml": ".yaml",
    "markdown": ".md", "md": ".md",
    "python": ".py", "py": ".py", "pyw": ".pyw",
    "c": ".c", "cpp": ".cpp", "c++": ".cpp", "cxx": ".cpp", "h": ".h", "hpp": ".hpp",
    "csharp": ".cs", "cs": ".cs", "java": ".java",
    "go": ".go", "golang": ".go",
    "rust": ".rs", "rs": ".rs",
    "qml": ".qml",
    "sql": ".sql",
}


class FormatterManager:
    def __init__(self, extension_manager: ExtensionManager):
        self.extension_manager = extension_manager

    def invalidate_cache(self):
        """Invalidates all cached formatter availability states."""
        pass

    def format_code(self, lang_id: str, file_path: str, source_code: str, tab_size: int = 4) -> Dict[str, Any]:
        """
        Strict language-specific code formatting:
        1. Resolves language ID and extension.
        2. Looks up formatter provider that EXPLICITLY supports the language.
        3. Never allows cross-language fallbacks (e.g. clang-format for C# or Java).
        4. Verifies actual executable availability in the environment before executing.
        5. If unavailable, returns available: False to trigger Smart Install.
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

        # Normalize language aliases
        lang_map = {
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
        clean_lang = lang_map.get(lang, lang)

        # 1. Locate extension specifically registered for formatting this exact language
        extension = self.extension_manager.get_extension_for_language(clean_lang, file_path, for_formatting=True)

        if extension and extension.formatter and extension.supports_language_for_formatting(clean_lang, file_path):
            formatter_spec = extension.formatter
            fmt_type = formatter_spec.get("type", "cli") if isinstance(formatter_spec, dict) else "cli"

            # Built-in Python Formatter
            if fmt_type == "python":
                return self._format_python(source_code, tab_size, extension)

            # Built-in JSON Formatter
            if fmt_type == "json":
                return self._format_json(source_code, tab_size, extension)

            # External CLI Formatter (clang-format, prettier, rustfmt, gofmt, qmlformat, etc.)
            if fmt_type == "cli":
                return self._format_cli(source_code, tab_size, file_path, clean_lang, extension, formatter_spec)

        # 2. Dynamic environment resolution for languages with standard tools (e.g. SQL -> SQLFluff, C# -> CSharpier)
        if clean_lang == "sql" or ext_dot == ".sql":
            return self._format_sqlfluff(source_code, tab_size, file_path)

        if clean_lang == "csharp" or ext_dot == ".cs":
            return self._format_csharpier(source_code, tab_size, file_path)

        display_name = clean_lang or ext_dot.lstrip(".") or "this language"
        return {
            "success": False,
            "formatted": source_code,
            "message": f"No formatter installed for {display_name}.",
            "available": False
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

        for tool in ["autopep8", "black", "ruff"]:
            tool_info = resolve_python_tool(tool, tool, sys.executable)
            tool_path = extension.get_executable_path() or tool_info.get("executable") or locate_executable(tool)
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

    def _format_sqlfluff(self, source_code: str, tab_size: int, file_path: str) -> Dict[str, Any]:
        """
        Dynamically formats SQL using SQLFluff resolved from the active Python environment or system.
        """
        tool_info = resolve_python_tool("sqlfluff", "sqlfluff", sys.executable)
        tool_path = tool_info.get("executable") or locate_executable("sqlfluff")

        if not tool_path and not tool_info.get("package_installed"):
            return {
                "success": False,
                "formatted": source_code,
                "message": "No formatter installed for SQL.",
                "available": False,
                "dependency": "sqlfluff",
                "installCommand": f'"{sys.executable}" -m pip install --no-warn-script-location sqlfluff'
            }

        # Build execution command (either direct executable or python -m sqlfluff)
        cmd_prefix = [tool_path] if tool_path else [sys.executable, "-m", "sqlfluff"]

        is_win = sys.platform.startswith("win")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if is_win else 0

        import tempfile
        temp_file = None
        try:
            tf = tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False, encoding="utf-8")
            tf.write(source_code)
            tf.close()
            temp_file = tf.name

            cmd = cmd_prefix + ["format", "--dialect", "ansi", temp_file]

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=12,
                creationflags=creationflags
            )

            if os.path.exists(temp_file):
                with open(temp_file, "r", encoding="utf-8", errors="replace") as f:
                    formatted_content = f.read()

                if formatted_content is not None and proc.returncode in (0, 1):
                    clean_formatted = formatted_content.replace("\r\n", "\n")
                    if clean_formatted.strip() == source_code.strip():
                        return {
                            "success": True,
                            "formatted": source_code,
                            "message": "Document is already formatted",
                            "available": True
                        }
                    return {
                        "success": True,
                        "formatted": clean_formatted,
                        "message": "SQL formatted with SQLFluff",
                        "available": True
                    }

            err = (proc.stderr or proc.stdout or f"Exit code {proc.returncode}").strip()
            return {
                "success": False,
                "formatted": source_code,
                "message": f"SQLFluff format error: {err}",
                "available": True
            }

        except Exception as ex:
            return {
                "success": False,
                "formatted": source_code,
                "message": f"SQLFluff execution error: {ex}",
                "available": True
            }
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass

    def _format_csharpier(self, source_code: str, tab_size: int, file_path: str = "") -> Dict[str, Any]:
        """
        Formats C# source code using CSharpier .NET global tool.
        """
        dotnet_info = resolve_dotnet_global_tool("csharpier", "csharpier")
        csharpier_bin = dotnet_info.get("executable") or locate_executable("csharpier") or locate_executable("dotnet-csharpier")

        if not csharpier_bin or not os.path.isfile(csharpier_bin):
            return {
                "success": False,
                "formatted": source_code,
                "message": "No formatter installed for C#.",
                "available": False,
                "dependency": "csharpier",
                "installCommand": "dotnet tool install -g csharpier"
            }

        is_win = sys.platform.startswith("win")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if is_win else 0

        import tempfile
        temp_file = None
        try:
            tf = tempfile.NamedTemporaryFile(mode="w", suffix=".cs", delete=False, encoding="utf-8")
            tf.write(source_code)
            tf.close()
            temp_file = tf.name

            cmd = [csharpier_bin, "format", temp_file]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                creationflags=creationflags
            )

            # Fallback for legacy CSharpier versions where "format" subcommand wasn't present
            if proc.returncode != 0 and "Unrecognized command" in (proc.stderr or proc.stdout):
                cmd_legacy = [csharpier_bin, temp_file]
                proc = subprocess.run(
                    cmd_legacy,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                    creationflags=creationflags
                )

            if os.path.exists(temp_file):
                with open(temp_file, "r", encoding="utf-8", errors="replace") as f:
                    formatted_content = f.read()

                if formatted_content is not None and proc.returncode == 0:
                    clean_formatted = formatted_content.replace("\r\n", "\n")
                    if clean_formatted.strip() == source_code.strip():
                        return {
                            "success": True,
                            "formatted": source_code,
                            "message": "Document is already formatted",
                            "available": True
                        }
                    return {
                        "success": True,
                        "formatted": clean_formatted,
                        "message": "C# formatted with CSharpier",
                        "available": True
                    }

            err = (proc.stderr or proc.stdout or f"Exit code {proc.returncode}").strip()
            return {
                "success": False,
                "formatted": source_code,
                "message": f"CSharpier format error: {err}",
                "available": True
            }

        except Exception as ex:
            return {
                "success": False,
                "formatted": source_code,
                "message": f"CSharpier execution error: {ex}",
                "available": True
            }
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass

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
        temp_file_created = None
        cmd_file_path = effective_file_path

        # If tool requires a real file on disk (like qmlformat), write source_code to a temporary file
        if "qmlformat" in command_name.lower() or "qmlformat" in tool_path.lower():
            try:
                import tempfile
                tf = tempfile.NamedTemporaryFile(mode="w", suffix=".qml", delete=False, encoding="utf-8")
                tf.write(source_code)
                tf.close()
                temp_file_created = tf.name
                cmd_file_path = tf.name
            except Exception as tf_ex:
                print("[FormatterManager] Temp file creation error:", tf_ex)

        # Substitute arguments
        raw_args = spec.get("args", [])
        resolved_args = []
        for arg in raw_args:
            replaced = str(arg).replace("${tabSize}", str(tab_size))
            replaced = replaced.replace("${filePath}", cmd_file_path)
            resolved_args.append(replaced)

        # Normalize qmlformat flags (ensure no invalid options like --tab-size or -i)
        if "qmlformat" in command_name.lower() or "qmlformat" in tool_path.lower():
            resolved_args = ["-w", str(tab_size), cmd_file_path]

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
        finally:
            if temp_file_created and os.path.exists(temp_file_created):
                try:
                    os.unlink(temp_file_created)
                except Exception:
                    pass
