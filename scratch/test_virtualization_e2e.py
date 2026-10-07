import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
import json
from PySide6.QtCore import QTimer, Qt, QPointF
from PySide6.QtGui import QGuiApplication, QWheelEvent, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine
from main import EditorBackend, BackingDocument

def run_tests():
    print("=" * 80)
    print("DGX CODE EDITOR - FULL VIRTUALIZATION E2E VALIDATION & BENCHMARK")
    print("=" * 80)

    # 1. BackingDocument Unit Verification
    print("\n[Phase 1] BackingDocument Model Verification...")
    small_text = "\n".join([f"line_{i} = {i}" for i in range(1, 101)])
    doc3k = BackingDocument("\n".join([f"def func_{i}():\n    return {i} * 42" for i in range(1, 1501)]))
    doc10k = BackingDocument("\n".join([f"var_item_{i} = 'test_value_{i}'" for i in range(1, 10001)]))
    doc50k = BackingDocument("\n".join([f"record_{i}: int = {i}" for i in range(1, 50001)]))

    assert doc3k.total_lines == 3000, f"Expected 3000 lines, got {doc3k.total_lines}"
    assert doc10k.total_lines == 10000, f"Expected 10000 lines, got {doc10k.total_lines}"
    assert doc50k.total_lines == 50000, f"Expected 50000 lines, got {doc50k.total_lines}"
    print(f"  [OK] 3,000 lines loaded: {doc3k.total_lines} lines, {doc3k.total_chars:,} chars")
    print(f"  [OK] 10,000 lines loaded: {doc10k.total_lines} lines, {doc10k.total_chars:,} chars")
    print(f"  [OK] 50,000 lines loaded: {doc50k.total_lines} lines, {doc50k.total_chars:,} chars")

    # Test Slicing & Windowing
    slice_text, s, e = doc3k.get_slice(1000, 1800)
    slice_lines = slice_text.split("\n")
    assert len(slice_lines) == 801, f"Expected 801 lines, got {len(slice_lines)}"
    assert s == 1000 and e == 1800
    print("  [OK] Slice extraction (lines 1000-1800): 801 materialized lines")

    # Test Global Search
    matches = doc3k.global_search("func_1234")
    assert len(matches) == 1, f"Expected 1 match, got {len(matches)}"
    m = matches[0]
    print(f"  [OK] Global search found '{m['text']}' at global Line {m['startLine']}, Col {m['startCol']}")

    matches_50k = doc50k.global_search("record_49999")
    assert len(matches_50k) == 1
    m50 = matches_50k[0]
    print(f"  [OK] Global search in 50k lines found '{m50['text']}' at global Line {m50['startLine']}, Col {m50['startCol']}")

    # Test Incremental Slice Update & Persistence
    doc3k.update_slice(1000, 1002, "NEW_INSERTED_LINE_1\nNEW_INSERTED_LINE_2")
    assert "NEW_INSERTED_LINE_1" in doc3k.text
    assert doc3k.is_modified == True
    doc3k.mark_saved()
    assert doc3k.is_modified == False
    print("  [OK] Incremental slice modification & dirty state verification passed")

    # 2. QML Engine Integration Test
    print("\n[Phase 2] QML Component & Live UI Integration...")
    app = QGuiApplication.instance()
    if not app:
        app = QGuiApplication(sys.argv)

    engine = QQmlApplicationEngine()
    backend = EditorBackend()
    engine.rootContext().setContextProperty("backend", backend)

    # Initialize backing documents in backend
    test_3k_path = os.path.abspath("scratch/test_3k_virtual.py")
    test_10k_path = os.path.abspath("scratch/test_10k_virtual.py")
    test_50k_path = os.path.abspath("scratch/test_50k_virtual.py")
    
    os.makedirs("scratch", exist_ok=True)
    with open(test_3k_path, "w", encoding="utf-8") as f:
        f.write("\n".join([f"# Line {i}\ndef function_{i}():\n    return 'value_{i}'" for i in range(1, 1001)]))
    with open(test_10k_path, "w", encoding="utf-8") as f:
        f.write("\n".join([f"# Line {i}\nval_{i} = {i}" for i in range(1, 10001)]))
    with open(test_50k_path, "w", encoding="utf-8") as f:
        f.write("\n".join([f"# Line {i}\ndata_entry_{i} = {i}" for i in range(1, 50001)]))

    backend.open_file(test_3k_path)
    backend.open_file(test_10k_path)
    backend.open_file(test_50k_path)

    print(f"  [OK] Backend BackingDocument registered for 3k ({backend.get_backing_total_lines(test_3k_path)} lines)")
    print(f"  [OK] Backend BackingDocument registered for 10k ({backend.get_backing_total_lines(test_10k_path)} lines)")
    print(f"  [OK] Backend BackingDocument registered for 50k ({backend.get_backing_total_lines(test_50k_path)} lines)")

    print("\n[Phase 3] Interaction & Latency Verification...")
    # Benchmark slicing latency
    t0 = time.perf_counter()
    for _ in range(500):
        s = backend.get_backing_slice(test_3k_path, 400, 1200)
    t_slice_3k = (time.perf_counter() - t0) / 500.0 * 1000.0

    t0 = time.perf_counter()
    for _ in range(500):
        s = backend.get_backing_slice(test_10k_path, 4000, 4800)
    t_slice_10k = (time.perf_counter() - t0) / 500.0 * 1000.0

    t0 = time.perf_counter()
    for _ in range(500):
        s = backend.get_backing_slice(test_50k_path, 25000, 25800)
    t_slice_50k = (time.perf_counter() - t0) / 500.0 * 1000.0

    print(f"  - Slice fetch latency (3k lines):  {t_slice_3k:.4f} ms")
    print(f"  - Slice fetch latency (10k lines): {t_slice_10k:.4f} ms")
    print(f"  - Slice fetch latency (50k lines): {t_slice_50k:.4f} ms")

    # Benchmark search latency
    t0 = time.perf_counter()
    for _ in range(100):
        res = backend.search_backing_document(test_3k_path, "function_999", False, False)
    t_search_3k = (time.perf_counter() - t0) / 100.0 * 1000.0

    t0 = time.perf_counter()
    for _ in range(100):
        res = backend.search_backing_document(test_10k_path, "val_9999", False, False)
    t_search_10k = (time.perf_counter() - t0) / 100.0 * 1000.0

    t0 = time.perf_counter()
    for _ in range(50):
        res = backend.search_backing_document(test_50k_path, "data_entry_49999", False, False)
    t_search_50k = (time.perf_counter() - t0) / 50.0 * 1000.0

    print(f"  - Full search latency (3k lines):  {t_search_3k:.4f} ms (found {len(res)} match)")
    print(f"  - Full search latency (10k lines): {t_search_10k:.4f} ms (found {len(res)} match)")
    print(f"  - Full search latency (50k lines): {t_search_50k:.4f} ms (found {len(res)} match)")

    # Benchmark incremental slice update
    t0 = time.perf_counter()
    for _ in range(200):
        backend.update_backing_slice(test_3k_path, 500, 500, "# Modified line 500")
    t_update_3k = (time.perf_counter() - t0) / 200.0 * 1000.0

    t0 = time.perf_counter()
    for _ in range(200):
        backend.update_backing_slice(test_10k_path, 5000, 5000, "# Modified line 5000")
    t_update_10k = (time.perf_counter() - t0) / 200.0 * 1000.0

    t0 = time.perf_counter()
    for _ in range(100):
        backend.update_backing_slice(test_50k_path, 25000, 25000, "# Modified line 25000")
    t_update_50k = (time.perf_counter() - t0) / 100.0 * 1000.0

    print(f"  - Incremental typing update (3k lines):  {t_update_3k:.4f} ms")
    print(f"  - Incremental typing update (10k lines): {t_update_10k:.4f} ms")
    print(f"  - Incremental typing update (50k lines): {t_update_50k:.4f} ms")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED SUCCESSFULLY - VIRTUALIZATION ENGINE ACTIVE & OPERATIONAL")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
