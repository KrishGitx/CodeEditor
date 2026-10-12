import os
import sys
import shutil

# Add workspace root to sys.path
sys.path.insert(0, r"c:\Users\amazi\OneDrive\Documents\DGX")

from ExtensionManager import ExtensionManager
from FormatterManager import FormatterManager


def test_strict_formatter_resolution():
    print("\n--- TEST: Strict Language-Specific Formatter Resolution ---")
    ext_mgr = ExtensionManager()
    fmt_mgr = FormatterManager(ext_mgr)

    # 1. C++ (test.cpp) -> Should match dgx.cpp (clang-format)
    cpp_ext = ext_mgr.get_extension_for_language("cpp", "test.cpp", for_formatting=True)
    assert cpp_ext is not None, "Expected dgx.cpp to support C++"
    assert cpp_ext.id == "dgx.cpp", f"Expected dgx.cpp but got {cpp_ext.id}"
    print("PASS: C++ resolved to dgx.cpp (clang-format).")

    # 2. C# (test.cs) -> MUST NOT use clang-format / dgx.cpp
    cs_ext = ext_mgr.get_extension_for_language("csharp", "test.cs", for_formatting=True)
    assert cs_ext is None, f"C# MUST NOT resolve to any generic or C++ extension! Got: {cs_ext}"
    cs_res = fmt_mgr.format_code("csharp", "test.cs", "class Test { int x = 1; }")
    assert "clang-format" not in cs_res.get("message", "").lower(), "C# must never mention clang-format"
    if cs_res["available"]:
        assert "csharpier" in cs_res.get("message", "").lower()
        print("PASS: C# formatted via CSharpier without using clang-format.")
    else:
        assert cs_res["available"] is False, "C# without installed C# formatter must return available: False"
        print("PASS: C# does NOT use clang-format and triggers Smart Install flow.")

    # 3. Java (test.java) -> MUST NOT use clang-format / dgx.cpp
    java_ext = ext_mgr.get_extension_for_language("java", "test.java", for_formatting=True)
    assert java_ext is None, f"Java MUST NOT resolve to any generic or C++ extension! Got: {java_ext}"
    java_res = fmt_mgr.format_code("java", "test.java", "public class Main { public static void main(String[] args) {} }")
    assert java_res["available"] is False, "Java without installed Java formatter must return available: False"
    assert "clang-format" not in java_res.get("message", "").lower(), "Java must never mention clang-format"
    print("PASS: Java does NOT use clang-format and triggers Smart Install flow.")

    # 4. QML (test.qml) -> Must NOT silently format with fake internal formatter
    qml_ext = ext_mgr.get_extension_for_language("qml", "test.qml", for_formatting=True)
    assert qml_ext is not None and qml_ext.id == "dgx.qml", "Expected dgx.qml for QML"
    qml_real_p = qml_ext.get_executable_path()
    qml_res = fmt_mgr.format_code("qml", "test.qml", "import QtQuick 2.15\nItem { width: 100 }")
    if not qml_real_p:
        assert qml_res["available"] is False, "QML without real qmlformat must return available: False (no fake internal formatter)"
        print("PASS: QML without real qmlformat executable triggers Smart Install instead of faking format.")
    else:
        print(f"PASS: QML detected real qmlformat binary at {qml_real_p}.")

    # 5. Rust (test.rs) -> Must use rustfmt if present, else trigger Smart Install
    rs_ext = ext_mgr.get_extension_for_language("rust", "test.rs", for_formatting=True)
    assert rs_ext is not None and rs_ext.id == "dgx.rust", "Expected dgx.rust for Rust"
    rs_res = fmt_mgr.format_code("rust", "test.rs", "fn main() { println!(\"hello\"); }")
    rs_real_p = rs_ext.get_executable_path()
    if not rs_real_p:
        assert rs_res["available"] is False, "Rust without rustfmt must return available: False"
        print("PASS: Rust without rustfmt triggers Smart Install.")
    else:
        assert rs_res["available"] is True
        print(f"PASS: Rust uses real rustfmt at {rs_real_p}.")

    # 6. SQL (test.sql) -> MUST NOT use clang-format or built-in formatter
    sql_ext = ext_mgr.get_extension_for_language("sql", "test.sql", for_formatting=True)
    assert sql_ext is None, "SQL has no default fake extension and must trigger Smart Install"
    sql_res = fmt_mgr.format_code("sql", "test.sql", "SELECT id, name FROM users WHERE active = 1;")
    assert sql_res["available"] is False, "SQL must return available: False to trigger Smart Install"
    assert "clang-format" not in sql_res.get("message", "").lower()
    print("PASS: SQL does not use clang-format or fake formatters and triggers Smart Install.")


def mock_ai_strict(prompt):
    p = prompt.lower()
    if "missing dependency: sql" in p or "language/file type: sql" in p:
        return (
            "Tool: SQLFluff (SQL Formatter)\n"
            "Dependency Type: formatter\n"
            "Package: sqlfluff\n"
            "Executable: sqlfluff\n"
            "Resolution Type: single_command\n"
            f'Command: "{sys.executable}" -m pip install --no-warn-script-location sqlfluff\n'
            "Verify: sqlfluff --version\n"
            "Explanation: Installs SQLFluff, the standard SQL linter and code formatter via pip."
        )
    if "missing dependency: csharp" in p or "language/file type: csharp" in p:
        return (
            "Tool: CSharpier (C# Formatter)\n"
            "Dependency Type: formatter\n"
            "Package: csharpier\n"
            "Executable: dotnet-csharpier\n"
            "Resolution Type: single_command\n"
            "Command: dotnet tool install -g csharpier\n"
            "Verify: dotnet csharpier --version\n"
            "Explanation: Installs CSharpier."
        )
    if "missing dependency: java" in p or "language/file type: java" in p:
        return (
            "Tool: google-java-format (Java Formatter)\n"
            "Dependency Type: formatter\n"
            "Package: google-java-format\n"
            "Executable: google-java-format\n"
            "Resolution Type: single_command\n"
            "Command: npm install -g google-java-format\n"
            "Verify: google-java-format --version\n"
            "Explanation: Installs google-java-format."
        )
    if "missing dependency: qml" in p or "language/file type: qml" in p:
        return (
            "Tool: QML Formatter (qmlformat)\n"
            "Dependency Type: formatter\n"
            "Package: PySide6\n"
            "Executable: qmlformat\n"
            "Resolution Type: single_command\n"
            f'Command: "{sys.executable}" -m pip install --no-warn-script-location PySide6\n'
            "Verify: qmlformat --version\n"
            "Explanation: Installs qmlformat."
        )
    return ""


def test_package_validation_and_ai_smart_install():
    print("\n--- TEST: Package Name Validation & AI-First Smart Install ---")
    ExtensionManager.set_ai_provider(mock_ai_strict)
    try:
        ext_mgr = ExtensionManager()

        # 1. Reject hallucinated package names with spaces
        is_valid, msg = ext_mgr.validate_package_name("sql formatter")
        assert is_valid is False, "Must reject 'sql formatter' as an invalid package identifier"
        print("PASS: Correctly rejected hallucinated package name 'sql formatter'.")

        is_valid_real, _ = ext_mgr.validate_package_name("sqlfluff")
        assert is_valid_real is True, "Must accept 'sqlfluff'"
        print("PASS: Accepted valid package name 'sqlfluff'.")

        # 2. Smart Install for SQL -> Resolves to SQLFluff with active Python path and verification command
        prop_sql = ext_mgr.suggest_smart_install("formatter", "sql formatter", "sql", "sql", "test.sql")
        assert prop_sql["source"] == "ai", "Smart Install proposal source must be 'ai'"
        assert prop_sql["packageName"] == "sqlfluff" or "sqlfluff" in prop_sql["command"], f"Expected sqlfluff package, got: {prop_sql}"
        assert sys.executable in prop_sql["command"], f"Expected active Python '{sys.executable}' in command: {prop_sql['command']}"
        assert "sql formatter" not in prop_sql["command"], f"Must not contain hallucinated 'sql formatter': {prop_sql['command']}"
        assert "verifyCommand" in prop_sql and "sqlfluff" in prop_sql["verifyCommand"]
        print(f"PASS: SQL Smart Install resolved to verified package: {prop_sql['packageName']} | Command: {prop_sql['command']}")

        # 3. Smart Install for C#
        prop_cs = ext_mgr.suggest_smart_install("formatter", "csharp formatter", "csharp", "cs", "test.cs")
        assert "csharpier" in prop_cs["command"] or "dotnet" in prop_cs["command"], f"Expected C# formatter, got {prop_cs}"
        assert "clang-format" not in prop_cs["command"], "C# install command must never be clang-format"
        print(f"PASS: C# Smart Install resolved to: {prop_cs['toolName']} | Command: {prop_cs['command']}")

        # 4. Smart Install for Java
        prop_java = ext_mgr.suggest_smart_install("formatter", "java formatter", "java", "java", "test.java")
        assert "google-java-format" in prop_java["command"], f"Expected Java formatter, got {prop_java}"
        assert "clang-format" not in prop_java["command"], "Java install command must never be clang-format"
        print(f"PASS: Java Smart Install resolved to: {prop_java['toolName']} | Command: {prop_java['command']}")

        # 5. Smart Install for QML
        prop_qml = ext_mgr.suggest_smart_install("formatter", "qml formatter", "qml", "qml", "test.qml")
        assert "PySide6" in prop_qml["command"] or "qmlformat" in prop_qml["command"]
        assert sys.executable in prop_qml["command"]
        print(f"PASS: QML Smart Install resolved to: {prop_qml['toolName']} | Command: {prop_qml['command']}")
    finally:
        ExtensionManager.set_ai_provider(None)


def main():
    test_strict_formatter_resolution()
    test_package_validation_and_ai_smart_install()
    print("\n==================================================")
    print("ALL STRICT FORMATTER & SMART INSTALL TESTS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    main()
