import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtGui import QGuiApplication
from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager
from main import EditorBackend

def test_all():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    
    em = ExtensionManager()
    fm = FormatterManager(em)
    backend = EditorBackend()
    
    print("=" * 60)
    print("COMPREHENSIVE FORMATTER VERIFICATION SUITE")
    print("=" * 60)
    
    # 1. HTML -> Prettier
    html_raw = "<div><p>Hello  <span>World</span> </p></div>"
    html_res = fm.format_code("html", "temp.html", html_raw)
    print(f"\n[1] HTML -> Prettier: success={html_res['success']}, available={html_res['available']}, msg='{html_res['message']}'")
    if html_res['success']:
        print("    Output:", repr(html_res['formatted'].strip()))
    
    # 2. JavaScript -> Prettier
    js_raw = "function   test(  a,b ){const  x = {foo:1,bar:  2};return   x;}"
    js_res = fm.format_code("javascript", "temp.js", js_raw)
    print(f"\n[2] JavaScript -> Prettier: success={js_res['success']}, available={js_res['available']}, msg='{js_res['message']}'")
    if js_res['success']:
        print("    Output:", repr(js_res['formatted'].strip()))

    # 3. JSON -> Built-in
    json_raw = '{"name":"Pod Studio","version":"1.0","tools":["formatter","editor","terminal"]}'
    json_res = fm.format_code("json", "temp.json", json_raw, tab_size=2)
    print(f"\n[3] JSON -> Built-in: success={json_res['success']}, available={json_res['available']}, msg='{json_res['message']}'")
    if json_res['success']:
        print("    Output lines:", len(json_res['formatted'].splitlines()))

    # 4. Python -> autopep8 / black
    py_raw = "def foo( x,  y ):\n    z=x+y\n    return z\n"
    py_res = fm.format_code("python", "temp.py", py_raw)
    print(f"\n[4] Python -> autopep8: success={py_res['success']}, available={py_res['available']}, msg='{py_res['message']}'")
    if py_res['success']:
        print("    Output:", repr(py_res['formatted'].strip()))

    # 5. C/C++ -> clang-format
    cpp_raw = "int main(){int x=1+2;for(int i=0;i<5;i++){printf(\"%d\",i);}return 0;}"
    cpp_res = fm.format_code("cpp", "temp.cpp", cpp_raw)
    print(f"\n[5] C/C++ -> clang-format: success={cpp_res['success']}, available={cpp_res['available']}, msg='{cpp_res['message']}'")
    if cpp_res['success']:
        print("    Output:", repr(cpp_res['formatted'].strip()))

    # 6. Go -> gofmt
    go_raw = "package main\nimport \"fmt\"\nfunc main() {\nfmt.Println( \"hello go\" )\n}"
    go_res = fm.format_code("go", "temp.go", go_raw)
    print(f"\n[6] Go -> gofmt: success={go_res['success']}, available={go_res['available']}, msg='{go_res['message']}'")
    if go_res['success']:
        print("    Output:", repr(go_res['formatted'].strip()))

    # 7. Rust -> rustfmt
    rs_raw = "fn main(){let mut x=vec![1,2,3];x.push(4);println!(\"{:?}\",x);}"
    rs_res = fm.format_code("rust", "temp.rs", rs_raw)
    print(f"\n[7] Rust -> rustfmt: success={rs_res['success']}, available={rs_res['available']}, msg='{rs_res['message']}'")
    if rs_res['success']:
        print("    Output:", repr(rs_res['formatted'].strip()))

    # 8. Async request_format_code test
    print("\n[8] Async request_format_code & signal emission test:")
    async_received = []
    
    def on_fmt_completed(req_id, file_path, success, formatted_code, message, available, ext_id):
        async_received.append({
            "req_id": req_id,
            "success": success,
            "message": message,
            "available": available,
            "len": len(formatted_code)
        })
        print(f"    -> Signal received for {req_id}: success={success}, available={available}, msg='{message}'")

    backend.formattingCompleted.connect(on_fmt_completed)
    backend.request_format_code("req_async_1", "html", "Untitled-1", "<div><h1>Hello Async</h1></div>", 4)
    backend.request_format_code("req_async_2", "json", "sample.json", '{"a": 1, "b": 2}', 2)
    
    start_time = time.time()
    while len(async_received) < 2 and time.time() - start_time < 5.0:
        app.processEvents()
        time.sleep(0.05)
    
    print(f"    Total async requests received: {len(async_received)}/2")

    # 9. Malformed input test (JSON error should not crash)
    print("\n[9] Malformed JSON syntax error test:")
    bad_json = '{"unclosed": "brace'
    bad_res = fm.format_code("json", "bad.json", bad_json)
    print(f"    Result: success={bad_res['success']}, preserved_code={bad_res['formatted'] == bad_json}, msg='{bad_res['message']}'")

    # 10. Large document safety test
    print("\n[10] Large document safety test (5,000 lines JSON):")
    large_json = "{\n" + ",\n".join([f'  "key_{i}": {i}' for i in range(5000)]) + "\n}"
    t0 = time.time()
    large_res = fm.format_code("json", "large.json", large_json, 2)
    t1 = time.time()
    print(f"    Large format time: {(t1 - t0)*1000:.2f}ms, success={large_res['success']}")

    print("\n" + "=" * 60)
    print("ALL FORMATTER TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_all()
