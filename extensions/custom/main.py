"""
My First DGX Custom Extension (100% Pure Python)
"""

def activate(ctx):
    # -------------------------------------------------------------
    # 1. ADD A CUSTOM OPTION TO THE IDE SETTINGS MENU
    # -------------------------------------------------------------
    ctx.settings.register_setting(
        key="enable_confetti",
        title="Celebrate on Save",
        type="boolean",
        default=True,
        description="Emit confetti and play a chime whenever you save a file."
    )

    # -------------------------------------------------------------
    # 2. CREATE A DRAGGABLE FLOATING MASCOT ON THE EDITOR SCREEN
    # -------------------------------------------------------------
    mascot = ctx.ui.create_floating_widget(
        id="screen_mascot",
        x=550,
        y=280,
        draggable=True
    )

    # Mascot content (can be Text, Image, Badge, Card, etc.)
    badge = ctx.ui.Badge("Coding Buddy", background="#6366f1")
    mascot.set_content(badge)

    # When you click the mascot
    def on_mascot_click():
        mascot.animate("bounce")
        mascot.say("I'm right here! Keep up the great coding!")
        ctx.audio.beep(880, 150)

    mascot.on_click(on_mascot_click)
    mascot.say("Hey there! Drag me anywhere on your screen!")

    # -------------------------------------------------------------
    # 3. CREATE A CUSTOM POPUP MODAL DIALOG
    # -------------------------------------------------------------
    popup = ctx.ui.create_popup(
        title="My Quick Toolbox",
        width=420,
        height=320,
        modal=True
    )

    # Components inside the popup
    search_input = ctx.ui.TextInput(placeholder="Type something here...")
    slider = ctx.ui.Slider(min_value=0, max_value=100, value=75, label="Performance Boost")

    def on_submit():
        user_val = search_input.value
        ctx.notifications.show("Toolbox Result", f"You submitted: {user_val}")
        popup.close()

    popup.set_content(ctx.ui.Column(spacing=12, padding=16, items=[
        ctx.ui.Header("Quick Action Panel", level=2),
        ctx.ui.Text("Control your custom tools directly from Python:"),
        search_input,
        slider,
        ctx.ui.Row(spacing=8, items=[
            ctx.ui.Button("Submit", on_click=on_submit, variant="primary"),
            ctx.ui.Button("Close", on_click=popup.close, variant="ghost")
        ])
    ]))

    # -------------------------------------------------------------
    # 4. CREATE A CUSTOM WORKSPACE TAB
    # -------------------------------------------------------------
    tab = ctx.ui.create_tab(
        id="my_custom_tab",
        title="My Extension Tab",
        icon="sparkles"
    )

    tab.set_content(ctx.ui.Column(spacing=12, padding=20, items=[
        ctx.ui.Header("Welcome to My Custom Workspace Tab!"),
        ctx.ui.Text("This tab runs as a first-class editor tab beside your code files."),
        ctx.ui.Grid(columns=2, items=[
            ctx.ui.Card("Status", items=[ctx.ui.Badge("Active", background="#10b981")]),
            ctx.ui.Card("Files", items=[ctx.ui.Text("Monitoring current workspace")])
        ]),
        ctx.ui.ProgressBar(value=60, label="Daily Goal")
    ]))

    # -------------------------------------------------------------
    # 5. REGISTER KEYBOARD SHORTCUTS
    # -------------------------------------------------------------
    # Press Ctrl+Alt+P to open the popup modal
    ctx.shortcuts.register("Ctrl+Alt+P", popup.show, "Open Quick Toolbox Modal")

    # Press Ctrl+Alt+T to open the custom tab
    ctx.shortcuts.register("Ctrl+Alt+T", tab.show, "Open Custom Extension Tab")

    # -------------------------------------------------------------
    # 6. REACT TO FILE SAVE IN THE EDITOR
    # -------------------------------------------------------------
    def on_file_save(file_path):
        if ctx.settings.get("enable_confetti", True):
            # Particle burst where the mascot is
            ctx.particles.emit("confetti", {"x": mascot.x, "y": mascot.y}, count=40)
            mascot.say("Saved!")
            ctx.audio.beep(650, 100)

    ctx.editor.on_save(on_file_save)

    # Toast alert when starting
    ctx.notifications.show("Extension Loaded", "My Custom Extension is active!")


def deactivate(ctx):
    """Called when the extension is disabled or IDE closes."""
    pass