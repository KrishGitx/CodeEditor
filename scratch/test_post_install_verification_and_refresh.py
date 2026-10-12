import os
import sys
import unittest
import subprocess

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from ExtensionManager import ExtensionManager, resolve_python_tool, locate_executable
from FormatterManager import FormatterManager

class TestPostInstallVerificationAndRefresh(unittest.TestCase):
    def setUp(self):
        self.ext_mgr = ExtensionManager()
        self.fmt_mgr = FormatterManager(extension_manager=self.ext_mgr)

    def test_01_resolve_python_tool_environment_awareness(self):
        """Verify resolve_python_tool identifies active python environment and console scripts."""
        # 1. Test with pip / python
        py_tool = resolve_python_tool("pip", "pip", sys.executable)
        self.assertEqual(py_tool["python"], sys.executable)
        self.assertTrue(py_tool["package_installed"])

        # 2. Test sqlfluff resolution structure
        sql_tool = resolve_python_tool("sqlfluff", "sqlfluff", sys.executable)
        self.assertEqual(sql_tool["package"], "sqlfluff")
        self.assertEqual(sql_tool["python"], sys.executable)
        self.assertIn("console_script_exists", sql_tool)

    def test_02_sqlfluff_formatter_resolution_and_refresh(self):
        """Verify FormatterManager handles SQL formatting dynamically without stale cache."""
        sql_input = "SELECT  id,name,   age  FROM students WHERE id=1;"
        res = self.fmt_mgr.format_code("sql", "test.sql", sql_input)

        # Check resolution structure
        self.assertIn("available", res)
        self.assertIn("formatted", res)

        # If sqlfluff is installed in test python environment, it should format successfully;
        # If not installed, it should cleanly return available=False with dependency='sqlfluff'
        if not res["available"]:
            self.assertIn("No formatter installed for SQL", res["message"])
            self.assertEqual(res["dependency"], "sqlfluff")
        else:
            self.assertTrue(res["success"])
            self.assertIn("SELECT", res["formatted"])

    def test_03_cache_invalidation(self):
        """Verify invalidate_cache reloads extensions and does not keep negative caches."""
        self.ext_mgr.invalidate_cache()
        self.fmt_mgr.invalidate_cache()
        # Ensure format_code runs cleanly after invalidation
        res = self.fmt_mgr.format_code("sql", "test.sql", "SELECT 1;")
        self.assertIsNotNone(res)

    def test_05_resolve_dotnet_global_tool_environment_awareness(self):
        """Verify resolve_dotnet_global_tool identifies .dotnet/tools directory and returns structured info."""
        from ExtensionManager import resolve_dotnet_global_tool
        
        # Test generic tool structure with csharpier
        dotnet_tool = resolve_dotnet_global_tool("csharpier", "csharpier")
        self.assertEqual(dotnet_tool["package"], "csharpier")
        self.assertIn("tools_directory", dotnet_tool)
        self.assertIn(".dotnet", dotnet_tool["tools_directory"].lower())
        self.assertIn("executable_exists", dotnet_tool)
        self.assertIn("global_tool_installed", dotnet_tool)

        # Test with another arbitrary dotnet global tool (dotnet-ef)
        ef_tool = resolve_dotnet_global_tool("dotnet-ef", "dotnet-ef")
        self.assertEqual(ef_tool["package"], "dotnet-ef")
        self.assertIn("tools_directory", ef_tool)

        # Verify dotnet tools dir was added to process PATH
        tools_dir = dotnet_tool["tools_directory"]
        if os.path.isdir(tools_dir):
            self.assertIn(tools_dir.lower(), os.environ.get("PATH", "").lower())

    def test_06_csharp_formatter_routing_and_structure(self):
        """Verify FormatterManager routes C# (.cs) files to csharpier without clang-format fallback."""
        cs_input = "public class Foo { public void Bar() { System.Console.WriteLine(\"Hello\"); } }"
        res = self.fmt_mgr.format_code("csharp", "Program.cs", cs_input)

        self.assertIn("available", res)
        self.assertIn("formatted", res)
        if not res["available"]:
            self.assertIn("No formatter installed for C#", res["message"])
            self.assertEqual(res["dependency"], "csharpier")
            self.assertEqual(res["installCommand"], "dotnet tool install -g csharpier")
        else:
            self.assertTrue(res["success"])
            self.assertIn("public class Foo", res["formatted"])

if __name__ == "__main__":
    unittest.main()

