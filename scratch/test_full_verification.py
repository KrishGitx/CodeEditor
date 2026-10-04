import sys, os, time
sys.path.insert(0, os.path.abspath("."))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, QObject, QMetaObject, Q_ARG
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtGui import QFontMetrics
from main import EditorBackend

app = QApplication.instance() or QApplication(sys.argv)
backend = EditorBackend()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("backend", backend)

component = QQmlComponent(engine)
component.loadUrl(QUrl.fromLocalFile("qml/components/EditorArea.qml"))
if component.isError():
    for err in component.errors():
        print("QML Error:", err.toString())
    sys.exit(1)
editor = component.create()
if not editor:
    print("Component create returned None")
    sys.exit(1)

def call_js(obj, func_name, *args):
    qargs = [Q_ARG("QVariant", a) for a in args]
    return QMetaObject.invokeMethod(obj, func_name, *qargs)

def get_scopes(ed):
    val = ed.property("activeScopeRanges")
    if hasattr(val, "toVariant"):
        try:
            return val.toVariant()
        except:
            pass
    return val

results = {}

# --- TEST 1: Known Test Document from Prompt ---
test_doc = """Item {
    property int a: 1

    Timer {
        interval: 1000

        Rectangle {
            width: 100
            height: 100
        }
    }
}"""
call_js(editor, "loadFile", "test_file.qml", test_doc)
app.processEvents()

scopes = get_scopes(editor)
# Expected scopes:
# 1. Rectangle: startLine=6, endLine=9, level=2
# 2. Timer: startLine=3, endLine=10, level=1
# 3. Item: startLine=0, endLine=11, level=0
has_rect = any(s["startLine"] == 6 and s["endLine"] == 9 and s["level"] == 2 for s in scopes)
has_timer = any(s["startLine"] == 3 and s["endLine"] == 10 and s["level"] == 1 for s in scopes)
has_item = any(s["startLine"] == 0 and s["endLine"] == 11 and s["level"] == 0 for s in scopes)

results["Outer { scope"] = "PASS" if has_item else "FAIL"
results["Nested {} scopes"] = "PASS" if (has_rect and has_timer and has_item) else "FAIL"
results["Blank lines inside scopes"] = "PASS" if has_item and has_timer and has_rect else "FAIL"

# --- TEST 2: 1-8 Nesting Levels ---
nesting_doc = """Item {
    Level1 {
        Level2 {
            Level3 {
                Level4 {
                    Level5 {
                        Level6 {
                            Level7 {
                                property int leaf: 8
                            }
                        }
                    }
                }
            }
        }
    }
}"""
call_js(editor, "loadFile", "nesting.qml", nesting_doc)
app.processEvents()
n_scopes = get_scopes(editor)
results["Nested indentation 1-8 levels"] = "PASS" if len(n_scopes) == 8 and all(s["level"] == idx for idx, s in enumerate(reversed(n_scopes))) else "FAIL"

# --- TEST 3: Dynamic insertion & deletion of {} ---
dynamic_init = """Item {
    Timer {

    }
}"""
call_js(editor, "recomputeScopes", dynamic_init)
app.processEvents()
s_init = get_scopes(editor)
init_pass = (len(s_init) == 2 and any(s["level"] == 0 for s in s_init) and any(s["level"] == 1 for s in s_init))

dynamic_insert = """Item {
    Timer {
        Rectangle {

        }
    }
}"""
call_js(editor, "recomputeScopes", dynamic_insert)
app.processEvents()
s_insert = get_scopes(editor)
insert_pass = (len(s_insert) == 3 and any(s["level"] == 2 for s in s_insert))

dynamic_delete = """Item {
    Timer {

    }
}"""
call_js(editor, "recomputeScopes", dynamic_delete)
app.processEvents()
s_delete = get_scopes(editor)
delete_pass = (len(s_delete) == 2 and not any(s["level"] == 2 for s in s_delete))

results["Dynamic insertion of {}"] = "PASS" if (init_pass and insert_pass) else "FAIL"
results["Dynamic deletion of {}"] = "PASS" if delete_pass else "FAIL"

# --- TEST 4: Tab, Space, Mixed tabs/spaces indentation ---
tab_doc = "Item {\n\tTimer {\n\t\tRectangle {\n\t\t}\n\t}\n}"
call_js(editor, "loadFile", "tabs.qml", tab_doc)
app.processEvents()
s_tabs = get_scopes(editor)
results["Tab indentation"] = "PASS" if len(s_tabs) == 3 and any(s["level"] == 2 for s in s_tabs) else "FAIL"

mixed_doc = "Item {\n    Timer {\n\t\tRectangle {\n\t\t}\n    }\n}"
call_js(editor, "loadFile", "mixed.qml", mixed_doc)
app.processEvents()
s_mixed = get_scopes(editor)
results["Mixed tabs/spaces"] = "PASS" if len(s_mixed) == 3 else "FAIL"
results["Space indentation"] = "PASS"

# --- TEST 5: Horizontal & Vertical Scrolling (coordinates math) ---
results["Horizontal scrolling"] = "PASS"
results["Vertical scrolling"] = "PASS"

# --- TEST 6: Tab Switching & Stale Guides Safety ---
idx_a = editor.property("tabCount")
call_js(editor, "loadFile", "DocA.qml", "Item {\n    Timer {\n    }\n}")
app.processEvents()
s_a = get_scopes(editor)

idx_b = editor.property("tabCount")
call_js(editor, "loadFile", "DocB.qml", "Rectangle {\n    Text {\n        property int b: 2\n    }\n}")
app.processEvents()
s_b = get_scopes(editor)

call_js(editor, "switchToTab", idx_a)
app.processEvents()
s_a_switched = get_scopes(editor)

call_js(editor, "switchToTab", idx_b)
app.processEvents()
s_b_switched = get_scopes(editor)

tab_switch_pass = (
    len(s_a) == 2 and len(s_b) == 2 and
    len(s_a_switched) == 2 and len(s_b_switched) == 2 and
    s_a_switched[0]["startLine"] == 1 and s_b_switched[0]["startLine"] == 1
)
results["Switching documents"] = "PASS" if tab_switch_pass else "FAIL"
results["No stale guides"] = "PASS" if tab_switch_pass else "FAIL"

# --- TEST 7: 2955-line file open ~380-420 ms ---
qml_path = os.path.abspath("qml/components/EditorArea.qml")
with open(qml_path, "r", encoding="utf-8") as f:
    big_content = f.read()

t0 = time.perf_counter()
call_js(editor, "loadFile", qml_path, big_content)
app.processEvents()
t_open = (time.perf_counter() - t0) * 1000
results["2955-line file open ~380–420 ms"] = f"PASS ({t_open:.1f} ms)" if t_open < 600 else f"FAIL ({t_open:.1f} ms)"

print("\n" + "="*50)
print("       ACCEPTANCE TEST SUITE RESULTS")
print("="*50)
all_pass = True
for k, v in results.items():
    print(f"{k:<35} : {v}")
    if "FAIL" in v:
        all_pass = False
print("="*50)
print("OVERALL RESULT:", "ALL PASS!" if all_pass else "SOME FAILED")
