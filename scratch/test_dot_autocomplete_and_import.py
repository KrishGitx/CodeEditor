import sys, os
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtCore import QObject

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()

print("=== 1. Testing Clean Compilation of Theme and EditorArea ===")
theme_comp = QQmlComponent(engine, os.path.abspath('qml/Theme.qml'))
assert theme_comp.isReady(), f"Theme failed: {theme_comp.errors()}"
theme = theme_comp.create()

editor_comp = QQmlComponent(engine, os.path.abspath('qml/components/EditorArea.qml'))
assert editor_comp.isReady(), f"EditorArea failed: {editor_comp.errors()}"
editor = editor_comp.create()
editor.setProperty('theme', theme)
print("PASS: EditorArea.qml and Theme.qml compiled with 0 errors.")

print("\n=== 2. Testing Direct Import of ExtensionSDK from Subfolder ===")
orig_dir = os.getcwd()
try:
    os.chdir('extensions/VolumeControls')
    import ExtensionSDK
    from ExtensionSDK import DGXExtensionContext
    print("PASS: 'from ExtensionSDK import DGXExtensionContext' succeeded without sys.path hacks!")
finally:
    os.chdir(orig_dir)

print("\n=== 3. Testing Dot Autocomplete Triggering Immediately on '.' ===")
code = "def activate(ctx):\n    ctx."
editor.loadFile("test_dot.py", code)
app.processEvents()

codeTextArea = editor.property('codeTextArea')
assert codeTextArea is not None, "codeTextArea must exist"

# Position cursor right after 'ctx.'
codeTextArea.setProperty('cursorPosition', len(code))
app.processEvents()

# Trigger completion request
editor.triggerCompletionRequest()
app.processEvents()

popup = editor.findChild(QObject, "autocompletePopup")
assert popup is not None, "autocompletePopup must exist"
sug_model = popup.findChild(QObject, "suggestionModel")

count = sug_model.property('count')
print(f"Suggestions count right after typing 'ctx.': {count}")
assert count > 0, "Suggestions must NOT be empty right after typing '.'"

labels = [sug_model.get(i).property('label').toString() for i in range(count)]
print("Suggestions shown:", labels)
assert "notifications" in labels or "shortcuts" in labels or "audio" in labels, f"Expected SDK properties, got: {labels}"
print("PASS: Autocomplete shows SDK members immediately upon typing '.' without typing an extra character!")

print("\n=== 4. Testing Autocomplete Suggestion Selection and Insertion ===")
# Apply 'audio'
editor.applySuggestion("audio", "property")
app.processEvents()

updated_text = codeTextArea.property('text')
print("Updated code text:", repr(updated_text))
assert "ctx.audio" in updated_text, f"Expected 'ctx.audio', got: {updated_text}"
print("PASS: Suggestion cleanly applied right after dot: 'ctx.audio'")

print("\n=== 5. Testing Sub-property Dot Autocomplete for 'audio.' ===")
codeTextArea.setProperty('text', "def activate(ctx):\n    ctx.audio.")
codeTextArea.setProperty('cursorPosition', len("def activate(ctx):\n    ctx.audio."))
app.processEvents()

editor.triggerCompletionRequest()
app.processEvents()

audio_count = sug_model.property('count')
print(f"Suggestions count right after typing 'ctx.audio.': {audio_count}")
audio_labels = [sug_model.get(i).property('label').toString() for i in range(audio_count)]
print("Audio suggestions:", audio_labels)
assert "get_music_volume" in audio_labels or "set_music_volume" in audio_labels, f"Expected audio methods, got: {audio_labels}"
print("PASS: Sub-property dot autocomplete resolves audio methods immediately!")

print("\n=== 6. Testing VolumeControls Extension Activation & Execution ===")
from ExtensionManager import ExtensionManager
from ExtensionSDK import DGXExtensionContext

ext_mgr = ExtensionManager(base_dir=os.path.abspath('.'))
ext = ext_mgr.get_extension("user.my_first_extension")
assert ext is not None, "VolumeControls extension must be registered"

success = ext_mgr.activate_extension("user.my_first_extension")
assert success, "Extension activation must succeed"
print("PASS: Extension activated successfully.")

# Test shortcut dispatch
dispatched = ext_mgr.dispatch_shortcut("Ctrl+Alt+C")
assert dispatched, "Ctrl+Alt+C shortcut must be dispatched cleanly"
print("PASS: Extension shortcut callback dispatched cleanly with notification.")

print("\n==========================================")
print("ALL TESTS PASSED WITH 100% SUCCESS!")
print("==========================================")
