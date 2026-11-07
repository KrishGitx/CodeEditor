import os
import sys
import json
import re

print("--- [1] Checking Terminal Prompt & Font Boldness ---")
with open("qml/components/TerminalPanel.qml", "r", encoding="utf-8") as f:
    terminal_qml = f.read()

# Check regex for prompt matching
assert "PS " in terminal_qml
assert "font.bold: false" in terminal_qml
assert "font-weight: 500;" in terminal_qml
print("✓ Terminal prompt regex and reduced bold weight verified.")

print("\n--- [2] Checking Terminal Non-blocking Output Streaming ---")
with open("TerminalBackend.py", "r", encoding="utf-8") as f:
    term_backend = f.read()

assert "PeekNamedPipe" in term_backend
assert "self.process.stdout.buffer.read" in term_backend
print("✓ PeekNamedPipe and chunked buffer reads verified in TerminalBackend.")

print("\n--- [3] Checking ExtensionSDK In IDE & Site-Packages ---")
import ExtensionSDK
from ExtensionSDK import DGXExtensionContext
print("✓ ExtensionSDK imported successfully:", ExtensionSDK.__file__)

import ExtensionManager
mgr = ExtensionManager.ExtensionManager()
assert hasattr(mgr, "create_custom_extension")
assert hasattr(mgr, "get_music_volume")
assert hasattr(mgr, "set_music_volume")
print("✓ ExtensionManager has create_custom_extension, get_music_volume, set_music_volume.")

# Test custom extension creation
test_ext_name = "test_verify_ext"
main_py_path = mgr.create_custom_extension(test_ext_name)
print("✓ Created custom extension at:", main_py_path)
assert os.path.isfile(main_py_path)
with open(main_py_path, "r", encoding="utf-8") as f:
    snippet_code = f.read()
assert "from ExtensionSDK import DGXExtensionContext" in snippet_code
assert "def activate(ctx: DGXExtensionContext):" in snippet_code
assert "ctx.notifications.show" in snippet_code
assert "ctx.shortcuts.register" in snippet_code

manifest_path = os.path.join(os.path.dirname(main_py_path), "extension.json")
assert os.path.isfile(manifest_path)
with open(manifest_path, "r", encoding="utf-8") as f:
    manifest_data = json.load(f)
assert manifest_data["id"] == f"user.{test_ext_name}"
print("✓ Scaffolded folder, extension.json, and main.py snippet verified.")

print("\n--- [4] Checking Ctrl+P Commands in QuickOpenPalette ---")
with open("qml/components/QuickOpenPalette.qml", "r", encoding="utf-8") as f:
    quick_palette = f.read()

assert "Developer: Reload Window" in quick_palette
assert "Extensions: Create Custom Extension" in quick_palette
assert "signal reloadWindowRequested()" in quick_palette
assert "signal createCustomExtensionRequested()" in quick_palette
assert "openCommands()" in quick_palette
print("✓ QuickOpenPalette contains Developer: Reload Window and Extensions: Create Custom Extension.")

print("\n--- [5] Checking Function Signature Hover Inspection ---")
import main
backend = main.EditorBackend()

py_code = """def connect_database(host: str, port: int = 5432, timeout: float = 10.0) -> bool:
    \"\"\"Establishes a connection to the primary database server.\"\"\"
    return True
"""
hover_res = backend.get_hover_info("db.py", 1, 10, py_code)
print("✓ Hover info result:", hover_res)
assert hover_res["found"] is True
assert hover_res["symbol"] == "connect_database"
assert "def connect_database(host: str, port: int = 5432, timeout: float = 10.0) -> bool" in hover_res["title"]
assert "Establishes a connection to the primary database server." in hover_res["doc"]

with open("qml/components/EditorArea.qml", "r", encoding="utf-8") as f:
    editor_qml = f.read()

assert "FunctionHoverTooltip" in editor_qml
assert "editorHoverHandler" in editor_qml
assert "backend.get_hover_info" in editor_qml
print("✓ FunctionHoverTooltip and HoverHandler integrated in EditorArea.")

print("\n--- [6] Checking Auto-redirect to Terminal on Run ---")
with open("qml/main.qml", "r", encoding="utf-8") as f:
    main_qml = f.read()

assert 'terminalPanel.activeTab = "TERMINAL"' in main_qml
print("✓ Run active file automatically redirects to Terminal tab.")

print("\n>>> ALL CHECKS PASSED PERFECTLY! <<<")
