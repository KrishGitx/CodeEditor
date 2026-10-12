import os
import sys
import unittest
import json

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from ExtensionManager import ExtensionManager, locate_executable
from FormatterManager import FormatterManager

def mock_ai_general(prompt):
    p = prompt.lower()
    if "missing dependency: java" in p or "missing executable / tool: java" in p or "install java" in p:
        return (
            "{\n"
            '  "resolutionType": "single_command",\n'
            '  "source": "ai",\n'
            '  "title": "Install Java Development Kit",\n'
            '  "tool": "Java Development Kit (JDK)",\n'
            '  "dependencyType": "runtime",\n'
            '  "package": "Oracle.JDK.21",\n'
            '  "executable": "java",\n'
            '  "command": "winget install --id Oracle.JDK.21 -e",\n'
            '  "verificationCommand": "java --version",\n'
            '  "explanation": "Installs Java Development Kit for executing Java applications."\n'
            "}"
        )
    if "missing dependency: g++" in p or "missing executable / tool: g++" in p or "install g++" in p:
        return (
            "{\n"
            '  "resolutionType": "single_command",\n'
            '  "source": "ai",\n'
            '  "title": "Install GCC/G++ Compiler",\n'
            '  "tool": "GCC / G++ C/C++ Compiler Toolchain",\n'
            '  "dependencyType": "compiler",\n'
            '  "package": "MSYS2.MSYS2",\n'
            '  "executable": "g++",\n'
            '  "command": "winget install --id MSYS2.MSYS2 -e",\n'
            '  "verificationCommand": "g++ --version",\n'
            '  "explanation": "Installs GCC / G++ compiler."\n'
            "}"
        )
    if "missing dependency: go" in p or "missing executable / tool: go" in p or "install go" in p:
        return (
            "{\n"
            '  "resolutionType": "single_command",\n'
            '  "source": "ai",\n'
            '  "title": "Install Go SDK",\n'
            '  "tool": "Go SDK",\n'
            '  "dependencyType": "sdk",\n'
            '  "package": "GoLang.Go",\n'
            '  "executable": "go",\n'
            '  "command": "winget install --id GoLang.Go -e",\n'
            '  "verificationCommand": "go version",\n'
            '  "explanation": "Installs Go SDK."\n'
            "}"
        )
    if "missing dependency: dotnet" in p or "missing executable / tool: dotnet" in p or "install dotnet" in p:
        return (
            "{\n"
            '  "resolutionType": "single_command",\n'
            '  "source": "ai",\n'
            '  "title": "Install .NET SDK",\n'
            '  "tool": ".NET SDK",\n'
            '  "dependencyType": "sdk",\n'
            '  "package": "Microsoft.DotNet.SDK.8",\n'
            '  "executable": "dotnet",\n'
            '  "command": "winget install --id Microsoft.DotNet.SDK.8 -e",\n'
            '  "verificationCommand": "dotnet --version",\n'
            '  "explanation": "Installs .NET SDK."\n'
            "}"
        )
    if "missing dependency: sqlfluff" in p or "missing executable / tool: sqlfluff" in p or "install sqlfluff" in p:
        return (
            "{\n"
            '  "resolutionType": "single_command",\n'
            '  "source": "ai",\n'
            '  "title": "Install SQLFluff",\n'
            '  "tool": "SQLFluff",\n'
            '  "dependencyType": "formatter",\n'
            '  "package": "sqlfluff",\n'
            '  "executable": "sqlfluff",\n'
            f'  "command": {json.dumps(f"\"{sys.executable}\" -m pip install --no-warn-script-location sqlfluff")},\n'
            '  "verificationCommand": "sqlfluff --version",\n'
            '  "explanation": "Installs SQLFluff."\n'
            "}"
        )
    if "missing dependency: clang-format" in p or "missing executable / tool: clang-format" in p or "install clang-format" in p:
        return (
            "{\n"
            '  "resolutionType": "single_command",\n'
            '  "source": "ai",\n'
            '  "title": "Install clang-format",\n'
            '  "tool": "clang-format",\n'
            '  "dependencyType": "formatter",\n'
            '  "package": "clang-format",\n'
            '  "executable": "clang-format",\n'
            f'  "command": {json.dumps(f"\"{sys.executable}\" -m pip install --no-warn-script-location clang-format")},\n'
            '  "verificationCommand": "clang-format --version",\n'
            '  "explanation": "Installs clang-format."\n'
            "}"
        )
    if "missing dependency: autopep8" in p or "missing executable / tool: autopep8" in p or "install autopep8" in p:
        return (
            "{\n"
            '  "resolutionType": "single_command",\n'
            '  "source": "ai",\n'
            '  "title": "Install autopep8",\n'
            '  "tool": "autopep8",\n'
            '  "dependencyType": "formatter",\n'
            '  "package": "autopep8",\n'
            '  "executable": "autopep8",\n'
            f'  "command": {json.dumps(f"\"{sys.executable}\" -m pip install --no-warn-script-location autopep8 black")},\n'
            '  "verificationCommand": "autopep8 --version",\n'
            '  "explanation": "Installs autopep8."\n'
            "}"
        )
    return (
        "{\n"
        '  "resolutionType": "cannot_resolve",\n'
        '  "source": "ai",\n'
        '  "title": "Cannot Resolve custom-cli-tool-xyz",\n'
        '  "tool": "custom-cli-tool-xyz",\n'
        '  "dependencyType": "cli",\n'
        '  "package": "custom-cli-tool-xyz",\n'
        '  "executable": "custom-cli-tool-xyz",\n'
        '  "command": "",\n'
        '  "verificationCommand": "custom-cli-tool-xyz --version",\n'
        '  "explanation": "Could not determine how to install this dependency."\n'
        "}"
    )


class TestGeneralSmartInstallSystem(unittest.TestCase):
    def setUp(self):
        ExtensionManager.set_ai_provider(mock_ai_general)
        self.ext_mgr = ExtensionManager()
        self.fmt_mgr = FormatterManager(extension_manager=self.ext_mgr)

    def tearDown(self):
        ExtensionManager.set_ai_provider(None)

    def test_01_general_dependency_resolution_runtimes_compilers_sdks(self):
        """Verify Smart Install resolves runtimes (Java), compilers (g++), SDKs (Go, .NET)."""
        # 1. Java Runtime missing
        java_prop = self.ext_mgr.suggest_smart_install("runtime", "java", "java", "java", "C:\\test\\App.java")
        self.assertIsNotNone(java_prop)
        self.assertEqual(java_prop["dependencyType"], "runtime")
        self.assertEqual(java_prop["retryAction"], "run")
        self.assertTrue("java" in java_prop["executable"].lower())
        self.assertTrue("jdk" in java_prop["toolName"].lower() or "java" in java_prop["toolName"].lower())
        self.assertTrue(len(java_prop["command"]) > 0)
        self.assertEqual(java_prop["verifyCommand"], "java --version")

        # 2. C++ Compiler (g++) missing
        cpp_prop = self.ext_mgr.suggest_smart_install("compiler", "g++", "cpp", "cpp", "C:\\test\\main.cpp")
        self.assertIsNotNone(cpp_prop)
        self.assertEqual(cpp_prop["dependencyType"], "compiler")
        self.assertEqual(cpp_prop["retryAction"], "run")
        self.assertTrue("g++" in cpp_prop["executable"].lower() or "gcc" in cpp_prop["executable"].lower())
        self.assertTrue(len(cpp_prop["command"]) > 0)

        # 3. Go SDK missing
        go_prop = self.ext_mgr.suggest_smart_install("sdk", "go", "go", "go", "C:\\test\\main.go")
        self.assertIsNotNone(go_prop)
        self.assertEqual(go_prop["dependencyType"], "sdk")
        self.assertEqual(go_prop["retryAction"], "run")
        self.assertEqual(go_prop["executable"], "go")

        # 4. .NET SDK missing
        net_prop = self.ext_mgr.suggest_smart_install("sdk", "dotnet", "csharp", "cs", "C:\\test\\Program.cs")
        self.assertIsNotNone(net_prop)
        self.assertEqual(net_prop["dependencyType"], "sdk")
        self.assertEqual(net_prop["retryAction"], "run")
        self.assertEqual(net_prop["executable"], "dotnet")

    def test_02_formatters_as_one_case_of_general_dependencies(self):
        """Verify formatters are handled as general dependencies with retryAction='format'."""
        # 1. C++ Formatter (clang-format)
        clang_prop = self.ext_mgr.suggest_smart_install("formatter", "clang-format", "cpp", "cpp")
        self.assertEqual(clang_prop["dependencyType"], "formatter")
        self.assertEqual(clang_prop["retryAction"], "format")
        self.assertEqual(clang_prop["executable"], "clang-format")

        # 2. SQL Formatter (sqlfluff)
        sql_prop = self.ext_mgr.suggest_smart_install("formatter", "sqlfluff", "sql", "sql")
        self.assertEqual(sql_prop["dependencyType"], "formatter")
        self.assertEqual(sql_prop["retryAction"], "format")
        self.assertEqual(sql_prop["executable"], "sqlfluff")
        self.assertEqual(sql_prop["packageName"], "sqlfluff")

        # 3. Python Formatter (autopep8)
        py_prop = self.ext_mgr.suggest_smart_install("formatter", "autopep8", "python", "py")
        self.assertEqual(py_prop["dependencyType"], "formatter")
        self.assertEqual(py_prop["retryAction"], "format")

    def test_03_strict_formatter_safety_and_no_cross_language_fallbacks(self):
        """Verify formatters only format explicitly supported languages."""
        # clang-format extension must NOT support C#, Java, QML, Python, SQL, Rust, Go
        cpp_ext = self.ext_mgr.get_extension("dgx.cpp")
        self.assertIsNotNone(cpp_ext)
        self.assertTrue(cpp_ext.supports_language_for_formatting("cpp"))
        self.assertTrue(cpp_ext.supports_language_for_formatting("c"))
        self.assertFalse(cpp_ext.supports_language_for_formatting("csharp"))
        self.assertFalse(cpp_ext.supports_language_for_formatting("java"))
        self.assertFalse(cpp_ext.supports_language_for_formatting("qml"))
        self.assertFalse(cpp_ext.supports_language_for_formatting("python"))
        self.assertFalse(cpp_ext.supports_language_for_formatting("sql"))
        self.assertFalse(cpp_ext.supports_language_for_formatting("rust"))
        self.assertFalse(cpp_ext.supports_language_for_formatting("go"))

        # FormatterManager check: formatting C# or Java must not use clang-format
        cs_res = self.fmt_mgr.format_code("csharp", "C:\\test\\Program.cs", "class Program { int a; }")
        self.assertNotIn("clang-format", cs_res.get("message", "").lower())
        if not cs_res["available"]:
            self.assertFalse(cs_res["success"])
            self.assertIn("No formatter installed", cs_res["message"])
        else:
            self.assertTrue(cs_res["success"])
            self.assertIn("csharpier", cs_res.get("message", "").lower())

        java_res = self.fmt_mgr.format_code("java", "C:\\test\\App.java", "public class App { int a; }")
        self.assertNotIn("clang-format", java_res.get("message", "").lower())
        if not java_res["available"]:
            self.assertFalse(java_res["success"])
            self.assertIn("No formatter installed", java_res["message"])

    def test_04_unknown_tool_safe_resolution(self):
        """Unknown tool returns structured proposal without crashing or generating unsafe commands."""
        unk_prop = self.ext_mgr.suggest_smart_install("cli", "custom-cli-tool-xyz", "custom", "xyz")
        self.assertIsNotNone(unk_prop)
        self.assertEqual(unk_prop["executable"], "custom-cli-tool-xyz")
        # Empty or safe command
        if not unk_prop["command"]:
            self.assertTrue("could not determine" in unk_prop["description"].lower() or "install" in unk_prop["description"].lower())

    def test_05_package_name_and_command_validation(self):
        """Verify validation blocks hallucinated package names and destructive commands."""
        # 1. Reject space-separated hallucinated package
        valid, reason = self.ext_mgr.validate_package_name("sql formatter")
        self.assertFalse(valid)
        self.assertTrue("contains spaces" in reason)

        # 2. Accept valid single-word packages
        valid, _ = self.ext_mgr.validate_package_name("sqlfluff")
        self.assertTrue(valid)
        valid, _ = self.ext_mgr.validate_package_name("clang-format")
        self.assertTrue(valid)
        valid, _ = self.ext_mgr.validate_package_name("@angular/cli")
        self.assertTrue(valid)

        # 3. Block destructive commands
        safe, msg = self.ext_mgr.validate_command_safety("rm -rf / --no-preserve-root")
        self.assertFalse(safe)
        safe, msg = self.ext_mgr.validate_command_safety("del /f /s /q C:\\Windows")
        self.assertFalse(safe)

        # 4. Allow standard pip/npm/winget/cargo commands
        safe, _ = self.ext_mgr.validate_command_safety(f'"{sys.executable}" -m pip install sqlfluff')
        self.assertTrue(safe)
        safe, _ = self.ext_mgr.validate_command_safety('winget install --id Oracle.JDK.21 -e')
        self.assertTrue(safe)

    def test_06_prompt_generator_contains_all_environment_context(self):
        """Verify generate_smart_install_prompt includes OS, shell, python path, dependency type, etc."""
        prompt = self.ext_mgr.generate_smart_install_prompt(
            tool_name="java",
            tool_type="runtime",
            lang_id="java",
            ext="java",
            cur_os="windows",
            shell_name="PowerShell",
            python_env=sys.executable
        )
        self.assertIn("Missing dependency: java", prompt)
        self.assertIn("Operation type: runtime", prompt)
        self.assertIn("Operating system: windows", prompt)
        self.assertIn("Shell: PowerShell", prompt)
        self.assertIn(sys.executable, prompt)
        self.assertIn("Return structured JSON", prompt)

    def test_07_ai_response_parser(self):
        """Verify parse_ai_install_response accurately parses all required fields."""
        mock_ai_output = (
            "Tool: Java Development Kit (JDK)\n"
            "Dependency Type: runtime\n"
            "Package: Oracle.JDK.21\n"
            "Executable: java\n"
            "Command: winget install --id Oracle.JDK.21 -e --accept-source-agreements\n"
            "Verify: java --version\n"
            "Explanation: Installs Java 21 JDK."
        )
        parsed = self.ext_mgr.parse_ai_install_response(mock_ai_output)
        self.assertEqual(parsed["tool"], "Java Development Kit (JDK)")
        self.assertEqual(parsed["dependency_type"], "runtime")
        self.assertEqual(parsed["package"], "Oracle.JDK.21")
        self.assertEqual(parsed["executable"], "java")
        self.assertEqual(parsed["command"], "winget install --id Oracle.JDK.21 -e --accept-source-agreements")
        self.assertEqual(parsed["verify"], "java --version")
        self.assertEqual(parsed["explanation"], "Installs Java 21 JDK.")

if __name__ == "__main__":
    unittest.main()
