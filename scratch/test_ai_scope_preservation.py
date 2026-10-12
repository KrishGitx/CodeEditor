import os
import sys
from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QJSEngine

def main():
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    js_engine = QJSEngine()

    with open("qml/ai/CodeExtractor.js", "r", encoding="utf-8") as f:
        js_code = f.read()

    # Strip .pragma library for evaluation in QJSEngine
    clean_js = js_code.replace(".pragma library", "")
    val = js_engine.evaluate(clean_js)
    if val.isError():
        print(f"Error evaluating CodeExtractor.js: {val.toString()}")
        sys.exit(1)

    parse_fn = js_engine.globalObject().property("parseReplacementResponse")
    extract_fn = js_engine.globalObject().property("extractReplacementCode")

    # =========================================================================
    # TEST 1: CRITICAL JAVA SCENARIO — PARTIAL SNIPPET REJECTION
    # =========================================================================
    print("\n--- TEST 1: Java File Partial vs Complete Replacement ---")
    whole_java_file = """package com.example.db;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

public class DatabaseInit {
    private static final String URL = "jdbc:mysql://localhost:3306/school";
    private static final String USER = "root";
    private static final String PASS = "secret";

    public static void main(String[] args) {
        try (Connection conn = DriverManager.getConnection(URL, USER, PASS);
             Statement stmt = conn.createStatement()) {
            
            stmt.executeUpdate(
                "CREATE TABLE IF NOT EXISTS students (" +
                "id INT PRIMARY KEY AUTO_INCREMENT, " +
                "name VARCHAR(100), " +
                "age INT)" 9
            );
            
            System.out.println("Database initialized successfully.");
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }
}"""

    # 1A: AI returns ONLY the local statement fix (the bug reported by user)
    bad_ai_partial_resp = """The issue is the extra `9` after the SQL string literal.

[REPLACEMENT_CODE]
```java
stmt.executeUpdate(
    "CREATE TABLE IF NOT EXISTS students (" +
    "id INT PRIMARY KEY AUTO_INCREMENT, " +
    "name VARCHAR(100), " +
    "age INT)"
);
```

This fixes the syntax error."""

    res_partial = parse_fn.call([bad_ai_partial_resp, "java", whole_java_file]).toVariant()
    print("1A Partial Response Parse Result:", res_partial)
    assert res_partial.get("status") == "scope_mismatch", f"Expected 'scope_mismatch', got {res_partial.get('status')}"
    assert res_partial.get("code") is None, "Partial snippet must NOT produce replacement code!"
    extract_bad = extract_fn.call([bad_ai_partial_resp, "java", whole_java_file]).toString()
    assert extract_bad == "", "extractReplacementCode must return empty string for partial scope hazard!"
    print(" [PASS] 1A Partial snippet correctly rejected as scope mismatch! Prevents file destruction.")

    # 1B: AI returns the COMPLETE Java file with the fix applied
    corrected_java_file = """package com.example.db;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

public class DatabaseInit {
    private static final String URL = "jdbc:mysql://localhost:3306/school";
    private static final String USER = "root";
    private static final String PASS = "secret";

    public static void main(String[] args) {
        try (Connection conn = DriverManager.getConnection(URL, USER, PASS);
             Statement stmt = conn.createStatement()) {
            
            stmt.executeUpdate(
                "CREATE TABLE IF NOT EXISTS students (" +
                "id INT PRIMARY KEY AUTO_INCREMENT, " +
                "name VARCHAR(100), " +
                "age INT)"
            );
            
            System.out.println("Database initialized successfully.");
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }
}"""

    good_ai_complete_resp = f"""The issue was an invalid trailing `9` character on line 22 after the closing parenthesis of the SQL string.

[REPLACEMENT_CODE]
```java
{corrected_java_file}
```

The database initialization table definition is now correct."""

    res_good = parse_fn.call([good_ai_complete_resp, "java", whole_java_file]).toVariant()
    print("1B Complete Response Parse Result:", res_good.get("status"))
    assert res_good.get("status") == "replacement", f"Expected 'replacement', got {res_good.get('status')}"
    code_good = res_good.get("code")
    assert "package com.example.db;" in code_good, "Must preserve package declaration"
    assert "public class DatabaseInit" in code_good, "Must preserve class declaration"
    assert '"age INT)"' in code_good and '"age INT)" 9' not in code_good, "Must contain fixed SQL string without '9'"
    assert "System.out.println" in code_good, "Must preserve subsequent statements"
    print(" [PASS] 1B Complete scope replacement validated and accepted successfully!")

    # =========================================================================
    # TEST 2: SMALL LOCAL SELECTION (1-3 lines)
    # =========================================================================
    print("\n--- TEST 2: Small 3-Line Selection ---")
    small_selection = """            stmt.executeUpdate(
                "CREATE TABLE students (age INT)" 9
            );"""

    small_fix_resp = """Fixed the invalid trailing 9.

[REPLACEMENT_CODE]
```java
            stmt.executeUpdate(
                "CREATE TABLE students (age INT)"
            );
```"""

    res_small = parse_fn.call([small_fix_resp, "java", small_selection]).toVariant()
    assert res_small.get("status") == "replacement", f"Expected small selection fix to succeed, got {res_small.get('status')}"
    assert '"CREATE TABLE students (age INT)"' in res_small.get("code")
    print(" [PASS] 2. Small selection properly allows localized replacement!")

    # =========================================================================
    # TEST 3: WHOLE PYTHON FILE
    # =========================================================================
    print("\n--- TEST 3: Python File Scope Preservation ---")
    whole_py = """import os
import sys

def calculate_average(items):
    if not items:
        return 0.0
    total = sum(items)
    return total / len(items)

def process_file(filepath):
    print(f"Processing: {filepath}")
    data = [10, 20, 30, 40]
    avg = calculate_average(data)
    print(f"Average: {avg}")

if __name__ == "__main__":
    process_file("data.csv")"""

    good_py_resp = f"""[REPLACEMENT_CODE]
```python
{whole_py.replace("avg = calculate_average(data)", "avg = round(calculate_average(data), 2)")}
```"""

    res_py = parse_fn.call([good_py_resp, "python", whole_py]).toVariant()
    assert res_py.get("status") == "replacement"
    assert "def process_file" in res_py.get("code")
    print(" [PASS] 3. Python whole file scope preserved.")

    # =========================================================================
    # TEST 4: WHOLE C++ FILE
    # =========================================================================
    print("\n--- TEST 4: C++ File Scope Preservation ---")
    whole_cpp = """#include <iostream>
#include <vector>
#include <string>

class StudentRegistry {
public:
    void addStudent(const std::string& name, int age) {
        std::cout << "Added: " << name << " (" << age << ")\\n";
    }
};

int main() {
    StudentRegistry reg;
    reg.addStudent("Alice", 20);
    return 0;
}"""

    good_cpp_resp = f"""[REPLACEMENT_CODE]
```cpp
{whole_cpp.replace('("Alice", 20)', '("Alice", 21)')}
```"""

    res_cpp = parse_fn.call([good_cpp_resp, "cpp", whole_cpp]).toVariant()
    assert res_cpp.get("status") == "replacement"
    assert "#include <iostream>" in res_cpp.get("code")
    assert "class StudentRegistry" in res_cpp.get("code")
    print(" [PASS] 4. C++ whole file scope preserved.")

    # =========================================================================
    # TEST 5: WHOLE QML FILE
    # =========================================================================
    print("\n--- TEST 5: QML File Scope Preservation ---")
    whole_qml = """import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    width: 400
    height: 300
    color: "#1e1e1e"

    Text {
        anchors.centerIn: parent
        text: "Hello World"
        color: "#ffffff"
    }
}"""

    good_qml_resp = f"""[REPLACEMENT_CODE]
```qml
{whole_qml.replace('color: "#ffffff"', 'color: "#00ffcc"')}
```"""

    res_qml = parse_fn.call([good_qml_resp, "qml", whole_qml]).toVariant()
    assert res_qml.get("status") == "replacement"
    assert "import QtQuick 2.15" in res_qml.get("code")
    assert "Rectangle {" in res_qml.get("code")
    print(" [PASS] 5. QML whole file scope preserved.")

    print("\n==========================================")
    print("ALL AI SCOPE PRESERVATION TESTS PASSED! [SUCCESS]")
    print("==========================================\n")

if __name__ == "__main__":
    main()
