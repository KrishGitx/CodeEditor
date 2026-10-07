with open('qml/components/EditorArea.qml', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add dispatchEditorKey to root
root_target = "    function setActiveEditorCursorPosition(pos) {"
root_repl = """    function dispatchEditorKey(key, modifiers, text) {
        if (root.activeEditorPane && root.activeEditorPane.handleEditorKey) {
            var ev = {
                key: key,
                modifiers: modifiers !== undefined ? modifiers : Qt.NoModifier,
                text: text || "",
                accepted: false
            };
            root.activeEditorPane.handleEditorKey(ev);
            return ev.accepted;
        }
        return false;
    }

    function setActiveEditorCursorPosition(pos) {"""

content = content.replace(root_target, root_repl, 1)

# 2. Expose handleEditorKey on tabPane and wire in Keys.onPressed
pane_target = "                                        function updatePaneScopes() {"
pane_repl = """                                        function handleEditorKey(event) {
                                            if (codeTextArea && codeTextArea.handleKeyPressInternal) {
                                                return codeTextArea.handleKeyPressInternal(event);
                                            }
                                        }

                                        function updatePaneScopes() {"""

content = content.replace(pane_target, pane_repl, 1)

# 3. Inside codeTextArea, name the handler function handleKeyPressInternal
keys_target = "                                                        Keys.onPressed: function(event) {"
keys_repl = """                                                        function handleKeyPressInternal(event) {
                                                            // Whole-line copy / paste behavior"""

# Also wire Keys.onPressed to call handleKeyPressInternal
keys_wire_target = "                                                        Keys.onPressed: function(event) {"
# Let's replace the definition of Keys.onPressed
content = content.replace("                                                        Keys.onPressed: function(event) {",
"""                                                        Keys.onPressed: function(event) { handleKeyPressInternal(event); }

                                                        function handleKeyPressInternal(event) {""", 1)

with open('qml/components/EditorArea.qml', 'w', encoding='utf-8') as f:
    f.write(content)

print("WIRED DISPATCH KEY SUCCESSFULLY")
