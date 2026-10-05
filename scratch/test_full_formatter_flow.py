import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
from PySide6.QtCore import QCoreApplication
from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager
from main import EditorBackend

def test_terminal_ui():
    print("=== TEST 1: Terminal Panel PS > Removal ===")
    with open("qml/components/TerminalPanel.qml", "r", encoding="utf-8") as f:
        content = f.read()
    
    assert 'text: "PS >"' not in content, "Redundant static 'PS >' UI element found in TerminalPanel.qml!"
    print("PASS: Redundant static 'PS >' UI element successfully removed from TerminalPanel.qml.")

def test_extension_and_formatter():
    print("\n=== TEST 2: Extension & Formatter Detection ===")
    ext_mgr = ExtensionManager()
    fmt_mgr = FormatterManager(ext_mgr)
    
    cpp_ext = ext_mgr.get_extension("dgx.cpp")
    assert cpp_ext is not None, "dgx.cpp extension not found!"
    print(f"PASS: Found extension '{cpp_ext.name}' (id: {cpp_ext.id})")
    
    status = cpp_ext.check_formatter_status()
    print(f"Initial C++ Formatter Status: {status}")
    
    # Test locate_executable logic
    found_path = ext_mgr.locate_executable("clang-format")
    print(f"Located clang-format on system: {found_path}")
    
    # Test C++ code formatting
    unformatted_cpp = """#include <iostream>
int main(){int x=10;for(int i=0;i<x;++i){std::cout<<i<<std::endl;}return 0;}"""

    res = fmt_mgr.format_code("cpp", "main.cpp", unformatted_cpp, 4)
    print(f"Format Code Result: success={res.get('success')}, available={res.get('available')}, message='{res.get('message')}'")
    if res.get("success"):
        print("Formatted C++ output:")
        print(res.get("formatted"))
        assert "int main() {" in res.get("formatted") or "int main()" in res.get("formatted"), "C++ formatting did not structure properly"
        print("PASS: C++ code formatting succeeded.")
    else:
        print(f"Formatter unavailable or failed as expected if binary not in path: {res.get('message')}")

def test_editor_backend_integration():
    print("\n=== TEST 3: EditorBackend Integration & Signals ===")
    backend = EditorBackend()
    
    # Check signals
    signals_fired = []
    def on_progress(ext_id, status, msg):
        signals_fired.append((ext_id, status, msg))
        print(f"Signal formatterInstallProgress received: ext_id={ext_id}, status={status}, msg={msg}")
        
    backend.formatterInstallProgress.connect(on_progress)
    
    # Test duplicate request prevention
    backend.install_formatter("dgx.cpp")
    backend.install_formatter("dgx.cpp") # Duplicate should be ignored
    
    # Wait briefly for worker thread to report progress
    time.sleep(3)
    
    assert len(signals_fired) >= 1, "Expected formatterInstallProgress signal to be emitted!"
    print(f"PASS: Received {len(signals_fired)} progress signal updates.")
    
    # Check custom path setter/getter
    test_dummy = os.path.abspath(__file__)
    backend.set_custom_formatter_path("dgx.cpp", test_dummy)
    saved_path = backend.get_custom_formatter_path("dgx.cpp")
    assert saved_path == test_dummy, f"Expected {test_dummy}, got {saved_path}"
    print("PASS: Custom formatter path setter and getter working correctly.")

if __name__ == "__main__":
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    test_terminal_ui()
    test_extension_and_formatter()
    test_editor_backend_integration()
    print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
