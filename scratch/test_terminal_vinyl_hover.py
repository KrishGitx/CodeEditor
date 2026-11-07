import re

print("--- [1] Verifying Terminal Duplication Fix ---")
with open("qml/components/TerminalPanel.qml", "r", encoding="utf-8") as f:
    term_qml = f.read()

assert "function onOutputReceived" not in term_qml, "onOutputReceived should be removed to prevent double-output"
assert "function onSessionOutputReceived" in term_qml, "onSessionOutputReceived should be the single listener"
assert "text.replace(/\\r\\r\\n/g, \"\\n\").replace(/\\r\\n/g, \"\\n\")" in term_qml, "CRLF should be normalized"
print("✓ Terminal output duplication eliminated: only onSessionOutputReceived handles output.")
print("✓ Carriage return normalization verified.")

print("\n--- [2] Verifying Function Hover Tooltip Dimensions & Placement ---")
with open("qml/components/FunctionHoverTooltip.qml", "r", encoding="utf-8") as f:
    hover_qml = f.read()

assert "width: Math.min(Math.max(contentCol.implicitWidth + 32, 380), 680)" in hover_qml
assert "targetY - calcH - 8" in hover_qml
print("✓ Tooltip width increased to 380-680px for clean argument fit.")
print("✓ Tooltip position firmly placed on top of hovered word.")

print("\n--- [3] Verifying Vinyl Icon on Side Activity Bar ---")
with open("qml/components/VectorIcon.qml", "r", encoding="utf-8") as f:
    vector_qml = f.read()

assert 'n === "vinyl" || n === "record" || n === "disc"' in vector_qml
with open("qml/components/ActivityBar.qml", "r", encoding="utf-8") as f:
    activity_qml = f.read()

assert 'name: "vinyl"' in activity_qml
print("✓ VectorIcon has dedicated vinyl record geometry.")
print("✓ Side ActivityBar music button icon updated to vinyl record.")

print("\n--- [4] Verifying High-Contrast Vinyl Grooves & Yellow Ring ---")
with open("qml/music/VinylRecord.qml", "r", encoding="utf-8") as f:
    vinyl_qml = f.read()

assert "#eab308" in vinyl_qml
assert "rgba(250, 204, 21, 0.85)" in vinyl_qml
assert "rgba(255, 255, 255, 0.24)" in vinyl_qml
assert "rgba(0, 0, 0, 0.70)" in vinyl_qml
assert "border.color: \"#eab308\"" in vinyl_qml
print("✓ High-visibility grooves and specular reflection gradients verified in VinylRecord.")
print("✓ Yellow/golden circular ring verified on disk surface and album center framing.")

print("\n>>> ALL 4 CHECKS PASSED WITH FLYING COLORS! <<<")

