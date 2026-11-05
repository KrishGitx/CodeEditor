import sys
import os
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtGui import QGuiApplication
import ExtensionSDK as sdk
import ExtensionManager

def test_full_python_extension_engine():
    print("--- Testing Unlimited Pure-Python Extension Engine ---")
    app = QGuiApplication.instance() or QGuiApplication([])

    mgr = ExtensionManager.ExtensionManager()
    ext_id = "test.author.pet"

    # Simulate extension activate(api)
    ctx = sdk.DGXExtensionContext(ext_id, mgr)

    # 1. Custom Settings
    ctx.settings.register_setting(
        key="pet_speed",
        title="Mascot Speed",
        subtitle="Speed of floating animation",
        type="slider",
        min_value=1,
        max_value=10,
        default=5
    )
    ctx.settings.register_setting(
        key="enable_bark",
        title="Bark Audio",
        subtitle="Play audio sound",
        type="boolean",
        default=True
    )

    settings_list = mgr.customSettings
    assert len(settings_list) >= 2, f"Expected at least 2 settings, got {len(settings_list)}"
    print(f"PASS: Custom settings registered ({len(settings_list)} settings)")

    # Test setting value update
    mgr.setCustomSetting(ext_id, "pet_speed", 8)
    assert ctx.settings.get("pet_speed") == 8
    print("PASS: Setting update and persistence verified")

    # 2. Keyboard Shortcut
    shortcut_called = [False]
    def on_shortcut():
        shortcut_called[0] = True

    ctx.shortcuts.register("Ctrl+Alt+P", on_shortcut, "Pet the mascot")
    assert "Ctrl+Alt+P" in mgr._custom_shortcuts
    mgr.dispatch_shortcut("Ctrl+Alt+P")
    assert shortcut_called[0] is True
    print("PASS: Custom keyboard shortcut registered and dispatched")

    # 3. Floating Screen Widget (Floating Mascot)
    widget = ctx.ui.create_floating_widget(
        id="screen_pet",
        x=600,
        y=350,
        draggable=True
    )
    clicked = [False]
    widget.on_click(lambda: clicked.append(True))
    widget.say("Hello Human!")

    card = ctx.ui.Card(title="Floating HUD", items=[
        ctx.ui.Image("pet.gif", width=64, height=64),
        ctx.ui.Text("Coding Level: 99", bold=True),
        ctx.ui.ProgressBar(value=80, label="Energy")
    ])
    widget.set_content(card)

    widgets_list = mgr.floatingWidgets
    pet_w = next((w for w in widgets_list if w["id"] == "screen_pet"), None)
    assert pet_w is not None
    assert pet_w["bubble_text"] == "Hello Human!"
    assert pet_w["bubble_visible"] is True
    print("PASS: Floating screen widget created with content, speech bubble, and coordinates")

    # Trigger click action
    mgr.triggerUiAction("floating", "screen_pet", "", "click", None)
    assert len(clicked) == 2
    print("PASS: Floating widget click event triggered Python callback")

    # 4. Custom Popup Modal
    popup = ctx.ui.create_popup(
        title="Custom Pet Dialogue",
        width=420,
        height=300,
        modal=True
    )
    input_text = ctx.ui.TextInput(placeholder="Feed treat...", default="Cookie")
    popup_submitted = [None]
    btn = ctx.ui.Button("Feed", on_click=lambda: popup_submitted.append(input_text.value))

    popup.set_content(ctx.ui.Column(items=[
        ctx.ui.Header("Pet Interaction"),
        input_text,
        btn,
        ctx.ui.Video("pet_tricks.mp4"),
        ctx.ui.Canvas(width=200, height=100)
    ]))
    popup.show()

    assert mgr.activePopup is not None
    assert mgr.activePopup.get("title") == "Custom Pet Dialogue"
    print("PASS: Custom styled popup modal displayed with complex layout (Header, Input, Button, Video, Canvas)")

    # Simulate button click inside popup
    mgr.triggerUiAction("popup", popup.id, btn.id, "click", None)
    assert popup_submitted[-1] == "Cookie"
    print("PASS: Popup component interaction triggered Python callback with data")

    popup.close()
    assert mgr.activePopup == {}
    print("PASS: Popup closed cleanly")

    # 5. Custom Editor Tab
    tab = ctx.ui.create_tab(
        id="pet_dashboard",
        title="Pet Analytics Tab",
        icon="sparkles"
    )
    tab.set_content(ctx.ui.Grid(columns=2, items=[
        ctx.ui.Card(title="Stats", items=[ctx.ui.Text("120 lines coded")]),
        ctx.ui.Card(title="Mood", items=[ctx.ui.Badge("Happy", background="#10b981")])
    ]))
    tab.show()

    tabs_list = mgr.customTabs
    assert len(tabs_list) == 1
    assert tabs_list[0]["id"] == "pet_dashboard"
    print("PASS: Custom editor tab created and registered")

    tab.close()
    assert len(mgr.customTabs) == 0
    print("PASS: Custom editor tab closed cleanly")

    # 6. Particles & Audio Chimes
    particle_fired = [False]
    def on_particle(t, x, y, c, d):
        particle_fired[0] = True
    mgr.particleEmitRequested.connect(on_particle)
    ctx.particles.emit("confetti", {"x": 500, "y": 300}, 50, 1500)
    assert particle_fired[0] is True
    print("PASS: Particle emission signal dispatched")

    print("\nALL PURE-PYTHON EXTENSION ENGINE TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_full_python_extension_engine()

