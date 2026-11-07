import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

class ProjectCompletionEngine:
    """
    Universal multi-language project symbol indexer and completion engine.
    Supports: Rust, Godot (GDScript), C#, Python, C/C++, TypeScript, JavaScript, Go, Lua, Zig, etc.
    Extracts:
      - Types / Classes / Structs / Traits / Enums
      - Functions / Methods / Properties / Fields
      - Variable declarations and inferred types
      - Dynamic project-wide member accesses
      - Language-specific standard profiles (Godot, Rust std, Unity, Python, Web)
    """

    IGNORED_DIRS = {
        ".git", ".svn", ".hg", "node_modules", "target", "bin", "obj",
        ".godot", "build", "dist", ".idea", ".vscode", "__pycache__",
        "library", "temp", "logs", ".gradle"
    }

    SUPPORTED_EXTS = {
        ".rs", ".gd", ".cs", ".py", ".cpp", ".c", ".h", ".hpp",
        ".ts", ".js", ".tsx", ".jsx", ".go", ".lua", ".zig", ".qml"
    }

    # Dynamic Framework & Engine Ecosystem Profiles (Populated dynamically via extension manifests)
    STANDARD_PROFILES: Dict[str, Dict[str, Any]] = {}

    # High-precision type and class member registry across engines and languages (Populated dynamically via extension manifests)
    COMMON_TYPE_MEMBERS: Dict[str, Dict[str, List[tuple]]] = {}

    def __init__(self):
        self.lock = threading.Lock()
        self.workspace_path = ""
        # File path -> parsed file data
        self.file_symbols: Dict[str, Dict[str, Any]] = {}
        # Global symbol pool: name -> {kind, container, file}
        self.global_types: Dict[str, Dict[str, Any]] = {}
        self.global_functions: Dict[str, List[Dict[str, Any]]] = {}
        self.type_members: Dict[str, Set[str]] = {}
        self.project_dot_accesses: Dict[str, Set[str]] = {}
        self.is_indexing = False

        # Pre-seed DGX Extension SDK subsystems for instantaneous dot-completions
        dgx_ctx_members = [
            ("audio", "property"), ("shortcuts", "property"), ("notifications", "property"),
            ("editor", "property"), ("theme", "property"), ("ui", "property"),
            ("dialogs", "property"), ("clipboard", "property"), ("terminal", "property"),
            ("system", "property"), ("timers", "property"), ("particles", "property"),
            ("settings", "property")
        ]
        audio_members = [
            ("set_music_volume", "method"), ("get_music_volume", "method"),
            ("volume_up", "method"), ("volume_down", "method"),
            ("play_sound", "method"), ("beep", "method")
        ]
        shortcut_members = [("register", "method")]
        notification_members = [("show", "method")]
        editor_members = [
            ("get_active_file", "method"), ("get_text", "method"),
            ("get_selected_text", "method"), ("get_cursor_position", "method"),
            ("get_line_count", "method"), ("on_change", "method"), ("on_save", "method")
        ]
        theme_members = [("get_palette", "method"), ("get_color", "method")]
        ui_members = [
            ("create_floating_widget", "method"), ("create_popup", "method"),
            ("create_tab", "method"), ("create_column", "method"),
            ("create_row", "method"), ("create_button", "method"),
            ("create_text", "method"), ("create_slider", "method"),
            ("create_switch", "method"), ("create_image", "method")
        ]
        dialog_members = [
            ("alert", "method"), ("confirm", "method"), ("open_file", "method"),
            ("save_file", "method"), ("select_folder", "method")
        ]
        clipboard_members = [("get_text", "method"), ("set_text", "method")]
        terminal_members = [("send", "method"), ("run", "method"), ("clear", "method"), ("interrupt", "method")]
        system_members = [("open_url", "method"), ("run_command", "method"), ("get_env", "method"), ("get_platform", "method")]
        timer_members = [("set_timeout", "method"), ("set_interval", "method"), ("clear_timer", "method")]
        particle_members = [("emit", "method")]
        settings_members = [("get", "method"), ("set", "method"), ("register", "method")]

        for lang_key in ("python", "general"):
            if lang_key not in self.COMMON_TYPE_MEMBERS:
                self.COMMON_TYPE_MEMBERS[lang_key] = {}
            target_map = self.COMMON_TYPE_MEMBERS[lang_key]
            target_map["DGXExtensionContext"] = dgx_ctx_members
            target_map["ctx"] = dgx_ctx_members
            target_map["AudioEngine"] = audio_members
            target_map["audio"] = audio_members
            target_map["ShortcutEngine"] = shortcut_members
            target_map["shortcuts"] = shortcut_members
            target_map["NotificationEngine"] = notification_members
            target_map["notifications"] = notification_members
            target_map["EditorEngine"] = editor_members
            target_map["editor"] = editor_members
            target_map["ThemeEngine"] = theme_members
            target_map["theme"] = theme_members
            target_map["UIEngine"] = ui_members
            target_map["ui"] = ui_members
            target_map["DialogEngine"] = dialog_members
            target_map["dialogs"] = dialog_members
            target_map["ClipboardEngine"] = clipboard_members
            target_map["clipboard"] = clipboard_members
            target_map["TerminalEngine"] = terminal_members
            target_map["terminal"] = terminal_members
            target_map["SystemEngine"] = system_members
            target_map["system"] = system_members
            target_map["TimerEngine"] = timer_members
            target_map["timers"] = timer_members
            target_map["ParticleEngine"] = particle_members
            target_map["particles"] = particle_members
            target_map["SettingsEngine"] = settings_members
            target_map["settings"] = settings_members

    def register_extension_types(self, ext_id: str, lang: str, types_dict: Dict[str, Any]):
        """
        Dynamically registers framework / engine types from extensions (React, Astro, Unity, Godot, etc.).
        """
        if not types_dict or not isinstance(types_dict, dict):
            return
        clean_lang = (lang or "").lower().strip()
        lang_map = {
            "js": "javascript", "jsx": "javascriptreact", "ts": "typescript", "tsx": "typescriptreact",
            "cs": "csharp", "gd": "gdscript", "py": "python", "rs": "rust"
        }
        clean_lang = lang_map.get(clean_lang, clean_lang)

        with self.lock:
            if clean_lang not in self.COMMON_TYPE_MEMBERS:
                self.COMMON_TYPE_MEMBERS[clean_lang] = {}
            for type_name, members in types_dict.items():
                mem_tuples = []
                for m in members:
                    if isinstance(m, (list, tuple)) and len(m) >= 2:
                        mem_tuples.append((m[0], m[1]))
                    elif isinstance(m, dict):
                        mem_tuples.append((m.get("name", ""), m.get("kind", "method")))
                    elif isinstance(m, str):
                        kind = "method" if (m.endswith("()") or m.startswith("use") or m.startswith("get_") or m.startswith("set_")) else "property"
                        clean_name = m.replace("()", "")
                        mem_tuples.append((clean_name, kind))
                self.COMMON_TYPE_MEMBERS[clean_lang][type_name] = mem_tuples

    def index_workspace(self, folder_path: str):
        if not folder_path or not os.path.exists(folder_path):
            return
        self.workspace_path = os.path.normpath(folder_path)
        t = threading.Thread(target=self._index_worker, daemon=True)
        t.start()

    def _index_worker(self):
        with self.lock:
            self.is_indexing = True
        try:
            files_to_index = []
            for root, dirs, files in os.walk(self.workspace_path):
                dirs[:] = [d for d in dirs if d.lower() not in self.IGNORED_DIRS and not d.startswith(".")]
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in self.SUPPORTED_EXTS:
                        files_to_index.append(os.path.join(root, f))
                        if len(files_to_index) >= 500:
                            break
                if len(files_to_index) >= 500:
                    break

            for fpath in files_to_index:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read(80000)
                    self.parse_and_store_file(fpath, content)
                except Exception:
                    pass
        finally:
            with self.lock:
                self.is_indexing = False

    def parse_and_store_file(self, file_path: str, content: str):
        ext = os.path.splitext(file_path)[1].lower()
        types: Set[str] = set()
        functions: Set[str] = set()
        variables: Dict[str, str] = {} # var_name -> declared_type
        dot_accesses: Dict[str, Set[str]] = {} # obj -> set(members)

        # 1. Dot-access harvesting (Works universally across all languages)
        for m in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)', content):
            obj, mem = m.group(1), m.group(2)
            if obj not in dot_accesses:
                dot_accesses[obj] = set()
            dot_accesses[obj].add(mem)

        # 2. Language-specific AST/Regex Extraction
        if ext == ".rs":
            # Rust structs, enums, traits
            for s in re.findall(r'(?:pub(?:\(crate\))?\s+)?(?:struct|enum|trait)\s+([A-Za-z0-9_]+)', content):
                types.add(s)
            # Rust functions
            for f in re.findall(r'fn\s+([A-Za-z0-9_]+)', content):
                functions.add(f)
            # Rust let bindings with explicit types
            for var_name, var_type in re.findall(r'let\s+(?:mut\s+)?([a-zA-Z0-9_]+)\s*:\s*([A-Za-z0-9_]+)', content):
                variables[var_name] = var_type

        elif ext == ".gd":
            # Godot GDScript class_name, inner class
            for c in re.findall(r'class_name\s+([A-Za-z0-9_]+)', content):
                types.add(c)
            for c in re.findall(r'class\s+([A-Za-z0-9_]+)\s*:', content):
                types.add(c)
            # GDScript functions
            for f in re.findall(r'func\s+([a-zA-Z0-9_]+)', content):
                functions.add(f)
            # GDScript vars with explicit types
            for var_name, var_type in re.findall(r'(?:@export\s+)?var\s+([a-zA-Z0-9_]+)\s*:\s*([A-Za-z0-9_]+)', content):
                variables[var_name] = var_type

        elif ext == ".cs":
            # C# classes, structs, interfaces
            for c in re.findall(r'(?:class|struct|interface|record)\s+([A-Za-z0-9_]+)', content):
                types.add(c)
            # C# methods and properties
            for f in re.findall(r'(?:public|private|protected|internal|static)\s+[A-Za-z0-9_<>\[\]]+\s+([A-Za-z0-9_]+)\s*\(', content):
                functions.add(f)
            # C# field and variable declarations: Type name;
            for var_type, var_name in re.findall(r'([A-Za-z0-9_]+)\s+([a-zA-Z0-9_]+)\s*(?:=|;)', content):
                if var_type not in {"return", "new", "throw", "case", "if", "while", "for", "var"}:
                    variables[var_name] = var_type

        elif ext == ".py":
            for c in re.findall(r'class\s+([A-Za-z0-9_]+)', content):
                types.add(c)
            for f in re.findall(r'def\s+([a-zA-Z0-9_]+)', content):
                functions.add(f)
            for var_name, var_type in re.findall(r'([a-zA-Z0-9_]+)\s*:\s*([A-Za-z0-9_]+)', content):
                variables[var_name] = var_type

        elif ext in {".ts", ".js", ".tsx", ".jsx"}:
            for c in re.findall(r'(?:class|interface|type)\s+([A-Za-z0-9_]+)', content):
                types.add(c)
            for f in re.findall(r'(?:function\s+([A-Za-z0-9_]+)|([A-Za-z0-9_]+)\s*\([^)]*\)\s*[{:])', content):
                name = f[0] or f[1]
                if name and name not in {"if", "for", "while", "switch", "catch"}:
                    functions.add(name)
            for var_name, var_type in re.findall(r'(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*:\s*([A-Za-z0-9_]+)', content):
                variables[var_name] = var_type

        elif ext in {".cpp", ".c", ".h", ".hpp"}:
            for c in re.findall(r'(?:class|struct)\s+([A-Za-z0-9_]+)', content):
                types.add(c)
            for f in re.findall(r'[A-Za-z0-9_:<>&*]+\s+([A-Za-z0-9_]+)\s*\([^;{}]*\)\s*[{;]', content):
                if f not in {"if", "for", "while", "switch"}:
                    functions.add(f)

        file_lang = self._detect_language(ext, content)

        with self.lock:
            self.file_symbols[file_path] = {
                "language": file_lang,
                "types": types,
                "functions": functions,
                "variables": variables,
                "dot_accesses": dot_accesses
            }
            for t in types:
                self.global_types[t] = {"file": file_path, "language": file_lang}
            for obj, mems in dot_accesses.items():
                if obj not in self.project_dot_accesses:
                    self.project_dot_accesses[obj] = set()
                self.project_dot_accesses[obj].update(mems)

    def get_completions(self, file_path: str, line: int, col: int, target_obj: str, prefix: str, current_doc: str = "", force_lang: str = "") -> List[Dict[str, Any]]:
        """
        Calculates context-aware, language-adaptive completions dynamically.
        """
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""
        detected = self._detect_language(ext, current_doc)
        raw_lang = (force_lang or detected or "general").lower().strip()
        lang_alias = {
            "cs": "csharp", "c#": "csharp", "py": "python", "rs": "rust",
            "gd": "gdscript", "js": "javascript", "ts": "javascript", "tsx": "javascript", "jsx": "javascript"
        }
        lang = lang_alias.get(raw_lang, raw_lang)
        prefix_lower = prefix.lower() if prefix else ""
        obj_lower = target_obj.lower() if target_obj else ""

        results = []
        seen = set()

        norm_cur_file = os.path.normcase(os.path.abspath(file_path)) if (file_path and os.path.isabs(file_path)) else os.path.normcase(file_path or "")

        with self.lock:
            # Gather relevant language types (including aliases like js/ts/jsx/tsx)
            lang_types = dict(self.COMMON_TYPE_MEMBERS.get("general", {}))
            if lang in ("javascript", "typescript", "typescriptreact", "javascriptreact"):
                lang_types.update(self.COMMON_TYPE_MEMBERS.get("javascript", {}))
                lang_types.update(self.COMMON_TYPE_MEMBERS.get("typescript", {}))
            lang_types.update(self.COMMON_TYPE_MEMBERS.get(lang, {}))

            # If target object access (e.g. Physics. or cam1. or player. or main.)
            if target_obj:
                # 1. Determine effective type of target_obj
                effective_type = ""
                if target_obj in lang_types:
                    effective_type = target_obj
                else:
                    for kt in lang_types.keys():
                        if kt.lower() == obj_lower:
                            effective_type = kt
                            break

                # If not a known type name, infer type from variable declarations
                if not effective_type and current_doc:
                    patterns = [
                        rf'(?:let\s+(?:mut\s+)?)?{re.escape(target_obj)}\s*:\s*([A-Za-z0-9_]+)',
                        rf'(?:@export\s+)?var\s+{re.escape(target_obj)}\s*:\s*([A-Za-z0-9_]+)',
                        rf'([A-Za-z0-9_]+)\s+{re.escape(target_obj)}\s*(?:=|;|,|\))'
                    ]
                    for pat in patterns:
                        m = re.search(pat, current_doc)
                        if m:
                            effective_type = m.group(1)
                            break

                if not effective_type and file_path in self.file_symbols:
                    effective_type = self.file_symbols[file_path]["variables"].get(target_obj, "")

                # 2. Add members from COMMON_TYPE_MEMBERS if effective_type is known
                if effective_type:
                    # Check exact case and case-insensitive
                    type_mems = lang_types.get(effective_type)
                    if not type_mems:
                        for kt, kmems in lang_types.items():
                            if kt.lower() == effective_type.lower():
                                type_mems = kmems
                                break
                    if type_mems:
                        for mem_name, mem_kind in type_mems:
                            self._add_match(results, seen, mem_name, mem_kind, prefix_lower, 85)

                # 3. Add members from workspace indexed types if defined in project
                if effective_type and effective_type in self.type_members:
                    for mem_name in self.type_members[effective_type]:
                        self._add_match(results, seen, mem_name, "method", prefix_lower, 80)

                # 4. Add members harvested from workspace specifically on target_obj
                if target_obj in self.project_dot_accesses:
                    for mem in self.project_dot_accesses[target_obj]:
                        self._add_match(results, seen, mem, "property", prefix_lower, 70)

                # 5. Add members from active document dot accesses specifically on target_obj
                if current_doc:
                    doc_mems = re.findall(rf'{re.escape(target_obj)}\.([a-zA-Z_][a-zA-Z0-9_]*)', current_doc)
                    for dm in doc_mems:
                        self._add_match(results, seen, dm, "property", prefix_lower, 65)

                # 6. Universal object methods (ToString, Equals, etc.)
                universal_methods = ["ToString", "Equals", "GetHashCode", "GetType"] if lang == "csharp" else ["toString", "equals"]
                for um in universal_methods:
                    self._add_match(results, seen, um, "method", prefix_lower, 30)

            else:
                # Normal word completion (Types, Functions, Keywords)
                prof = self.STANDARD_PROFILES.get(lang)
                if prof:
                    for t in prof.get("types", []):
                        self._add_match(results, seen, t, "class", prefix_lower, 50)
                    for m in prof.get("members", []):
                        self._add_match(results, seen, m, "property", prefix_lower, 45)

                # Known ecosystem classes and dynamic extension functions/hooks as suggestions
                for kt, kmems in lang_types.items():
                    type_kind = "class" if (kt and kt[0].isupper()) else "property"
                    self._add_match(results, seen, kt, type_kind, prefix_lower, 52)
                    for m_name, m_kind in kmems:
                        self._add_match(results, seen, m_name, m_kind, prefix_lower, 51)

                # Workspace types strictly matching the file's language
                for t, t_info in self.global_types.items():
                    if t_info.get("language") == lang:
                        self._add_match(results, seen, t, "class", prefix_lower, 48)

                # Workspace functions and local file variables matching the language
                for f_file, f_data in self.file_symbols.items():
                    if f_data.get("language") != lang:
                        continue
                    # Only suggest variables from the active file itself (prevents variable leakage across files)
                    norm_f_file = os.path.normcase(os.path.abspath(f_file)) if os.path.isabs(f_file) else os.path.normcase(f_file)
                    if norm_cur_file and norm_f_file == norm_cur_file:
                        for var_name in f_data["variables"].keys():
                            self._add_match(results, seen, var_name, "variable", prefix_lower, 42)
                    for func_name in f_data["functions"]:
                        self._add_match(results, seen, func_name, "function", prefix_lower, 40)

        # Sort: priority DESC, label length ASC
        results.sort(key=lambda x: (-x["priority"], len(x["label"])))
        return results[:35]

    def _add_match(self, results: list, seen: set, label: str, kind: str, prefix_lower: str, base_priority: int):
        if not label:
            return
        key = (label, kind)
        if key in seen:
            return
        # Never suggest the exact prefix the user has already typed
        if label.lower() == prefix_lower:
            return

        priority = base_priority
        if prefix_lower:
            # Strict prefix matching: must start with what the user typed
            if label.lower().startswith(prefix_lower):
                priority = base_priority + 25
            else:
                return

        seen.add(key)
        results.append({
            "label": label,
            "insertText": label,
            "type": kind,
            "priority": priority
        })

    def _detect_language(self, ext: str, doc: str) -> str:
        clean_ext = ext.lower().lstrip(".")
        ext_map = {
            "gd": "gdscript",
            "rs": "rust",
            "cs": "csharp",
            "py": "python",
            "ts": "typescript", "tsx": "typescript",
            "js": "javascript", "jsx": "javascript",
            "cpp": "cpp", "cc": "cpp", "cxx": "cpp", "c": "c", "h": "cpp", "hpp": "cpp",
            "astro": "astro",
            "vue": "vue",
            "svelte": "svelte",
            "go": "go",
            "json": "json",
            "html": "html",
            "css": "css",
            "qml": "qml"
        }
        if clean_ext in ext_map:
            return ext_map[clean_ext]
        if clean_ext in self.COMMON_TYPE_MEMBERS:
            return clean_ext
        # Heuristic detection from document content
        if "extends CharacterBody" in doc or "class_name" in doc:
            return "gdscript"
        if "fn main()" in doc or "pub struct" in doc:
            return "rust"
        if "using UnityEngine;" in doc or "using System;" in doc or "MonoBehaviour" in doc:
            return "csharp"
        return "general"

