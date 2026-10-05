import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
from PySide6.QtCore import QCoreApplication
from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager

def test_install_and_format():
    print("=== Testing Automated Lightweight clang-format Installation & C++ Formatting ===")
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    
    ext_mgr = ExtensionManager()
    fmt_mgr = FormatterManager(ext_mgr)
    
    events = []
    def on_progress(ext_id, status, msg):
        events.append((ext_id, status, msg))
        print(f"[INSTALL EVENT] {ext_id} -> {status}: {msg}")
        
    ext_mgr.formatterInstallProgress.connect(on_progress)
    
    # 1. Trigger install_formatter
    print("Starting install_formatter('dgx.cpp')...")
    ext_mgr.install_formatter("dgx.cpp")
    
    # Wait for installation worker thread to complete (up to 30s)
    for _ in range(60):
        app.processEvents()
        time.sleep(0.5)
        if any(e[1] in ("success", "failed") for e in events):
            break
            
    print(f"Total events received: {len(events)}")
    for e in events:
        print(f" - {e}")
        
    # Check if installed
    cpp_ext = ext_mgr.get_extension("dgx.cpp")
    status = cpp_ext.check_formatter_status()
    print("Post-install status:", status)
    
    if status["isInstalled"]:
        print(f"SUCCESS: clang-format detected at: {status['detectedPath']}")
        # Format C++ code
        raw_code = """
#include <iostream>
#include <vector>

int main() {
int x=5;
for(int i=0;i<x;++i){
std::cout<<"Number: "<<i<<std::endl;
}
return 0;
}
"""
        res = fmt_mgr.format_code("cpp", "test.cpp", raw_code, 4)
        print("Formatting result:", res.get("message"))
        print("Formatted code output:")
        print("--- START ---")
        print(res.get("formatted"))
        print("--- END ---")
        assert res.get("success"), f"Formatting failed: {res.get('message')}"
        print("PASS: End-to-end C++ formatting test passed completely!")
    else:
        print(f"Installation did not finish or failed: {events}")

if __name__ == "__main__":
    test_install_and_format()
