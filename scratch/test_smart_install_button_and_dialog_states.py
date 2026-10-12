import os
import sys
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager

class TestSmartInstallButtonAndDialogStates(unittest.TestCase):
    def setUp(self):
        self.ext_mgr = ExtensionManager()
        self.fmt_mgr = FormatterManager(extension_manager=self.ext_mgr)

    def tearDown(self):
        ExtensionManager.set_ai_provider(None)

    def test_01_ai_unavailable_returns_proposal_object_with_empty_command(self):
        """When AI is unavailable, suggest_smart_install returns a proposal object (not None) with command='', source='ai_unavailable'."""
        ExtensionManager.set_ai_provider(None)
        proposal = self.ext_mgr.suggest_smart_install("formatter", "unknown-lang formatter", "unknownlang", "ukl")
        
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal["source"], "ai_unavailable")
        self.assertEqual(proposal["resolutionType"], "cannot_resolve")
        self.assertEqual(proposal["command"], "")
        self.assertIn("AI is unavailable", proposal["description"])

    def test_02_ai_cannot_resolve_returns_proposal_with_empty_command_and_ai_source(self):
        """When AI explicitly reports cannot_resolve, proposal has source='ai', resolutionType='cannot_resolve', command=''."""
        def mock_ai_cannot_resolve(prompt):
            return (
                "Tool: Unknown Tool\n"
                "Dependency Type: cli\n"
                "Package: unknown-pkg\n"
                "Executable: unknown-tool\n"
                "Resolution Type: cannot_resolve\n"
                "Command: \n"
                "Verify: unknown-tool --version\n"
                "Explanation: Could not determine how to install this dependency."
            )
        ExtensionManager.set_ai_provider(mock_ai_cannot_resolve)
        proposal = self.ext_mgr.suggest_smart_install("cli", "unknown-tool", "custom", "xyz")

        self.assertIsNotNone(proposal)
        self.assertEqual(proposal["source"], "ai")
        self.assertEqual(proposal["resolutionType"], "cannot_resolve")
        self.assertEqual(proposal["command"], "")

    def test_03_ai_complex_setup_returns_proposal_with_plan(self):
        """When AI reports complex_setup, resolutionType='complex_setup' and source='ai'."""
        def mock_ai_complex(prompt):
            return (
                "Tool: Complex Toolchain\n"
                "Dependency Type: sdk\n"
                "Package: complex-sdk\n"
                "Executable: complextool\n"
                "Resolution Type: complex_setup\n"
                "Command: Step 1: Install runtime\nStep 2: Add to PATH\nStep 3: Run configure\n"
                "Verify: complextool --version\n"
                "Explanation: Requires multi-step setup environment configuration."
            )
        ExtensionManager.set_ai_provider(mock_ai_complex)
        proposal = self.ext_mgr.suggest_smart_install("sdk", "complextool", "custom", "xyz")

        self.assertIsNotNone(proposal)
        self.assertEqual(proposal["source"], "ai")
        self.assertEqual(proposal["resolutionType"], "complex_setup")
        self.assertIn("Step 1", proposal["command"])

    def test_04_ai_single_command_returns_valid_command(self):
        """When AI resolves with a single command, proposal has resolutionType='single_command'."""
        def mock_ai_single(prompt):
            return (
                "Tool: SQLFluff (SQL Formatter)\n"
                "Dependency Type: formatter\n"
                "Package: sqlfluff\n"
                "Executable: sqlfluff\n"
                "Resolution Type: single_command\n"
                f'Command: "{sys.executable}" -m pip install sqlfluff\n'
                "Verify: sqlfluff --version\n"
                "Explanation: Installs SQLFluff."
            )
        ExtensionManager.set_ai_provider(mock_ai_single)
        proposal = self.ext_mgr.suggest_smart_install("formatter", "sqlfluff", "sql", "sql")

        self.assertIsNotNone(proposal)
        self.assertEqual(proposal["source"], "ai")
        self.assertEqual(proposal["resolutionType"], "single_command")
        self.assertTrue(len(proposal["command"]) > 0)
        self.assertEqual(proposal["retryAction"], "format")

if __name__ == "__main__":
    unittest.main()
