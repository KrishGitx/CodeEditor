# DGX Pure-Python Extension API Reference Manual

Welcome to the **DGX Extension Engine Language & API Reference**. 

DGX allows developers and power users to author rich, high-performance extensions using **100% Pure Python**. You do not need to learn QML, write HTML/CSS, or touch C++ Qt bindings. DGX provides a declarative Python SDK that automatically maps your components, floating mascots, custom tabs, modal dialogs, and multimedia to native GPU-accelerated Qt Quick items.

---

## Table of Contents

1. [Architecture & Lifecycle](#1-architecture--lifecycle)
   - [Directory Structure](#directory-structure)
   - [The Manifest (`extension.json`)](#the-manifest-extensionjson)
   - [Entrypoint & Hooks (`activate` / `deactivate`)](#entrypoint--hooks)
2. [The Extension Context (`ctx`)](#2-the-extension-context-ctx)
   - [Subsystem Index](#subsystem-index)
   - [`ctx.ui` (UI Primitives & Views)](#ctxui)
   - [`ctx.settings` (Preferences Integration)](#ctxsettings)
   - [`ctx.shortcuts` (Global Keyboard Shortcuts)](#ctxshortcuts)
   - [`ctx.editor` (Live Workspace & Text Inspection)](#ctxeditor)
   - [`ctx.theme` (Theme Colors & Styling)](#ctxtheme)
   - [`ctx.audio` (Sound Effects & Beeps)](#ctxaudio)
   - [`ctx.particles` (Particle Physics FX)](#ctxparticles)
   - [`ctx.dialogs` (Native OS File & Message Dialogs)](#ctxdialogs)
   - [`ctx.clipboard` (System Clipboard)](#ctxclipboard)
   - [`ctx.notifications` (Toast Alerts)](#ctxnotifications)
   - [`ctx.system` (Subprocesses & URLs)](#ctxsystem)
   - [`ctx.timers` (Async Timers)](#ctxtimers)
3. [View Hosts](#3-view-hosts)
   - [Floating Screen Mascots (`ctx.ui.create_floating_widget`)](#floating-screen-mascots)
   - [Custom Popups & Modals (`ctx.ui.create_popup`)](#custom-popups--modals)
   - [Custom Workspace Tabs (`ctx.ui.create_tab`)](#custom-workspace-tabs)
4. [Component Catalog (27 Pure-Python UI Elements)](#4-component-catalog)
   - [Layout Containers](#layout-containers)
   - [Typography & Indicators](#typography--indicators)
   - [Inputs & Forms](#inputs--forms)
   - [Buttons & Actions](#buttons--actions)
   - [Multimedia & Graphics](#multimedia--graphics)
5. [Settings & Preferences Integration](#5-settings--preferences-integration)
6. [Complete Code Examples](#6-complete-code-examples)
   - [Example 1: Interactive Desktop Pet / Screen Mascot](#example-1-interactive-desktop-pet--screen-mascot)
   - [Example 2: Quick-Actions Modal Dialog](#example-2-quick-actions-modal-dialog)
   - [Example 3: Multimedia Workspace Tab](#example-3-multimedia-workspace-tab)
   - [Example 4: Confetti & Sound Effects on File Save](#example-4-confetti--sound-effects-on-file-save)

---

## 1. Architecture & Lifecycle

DGX extensions run inside an isolated Python execution context managed by `ExtensionManager`. When an extension is loaded, its declarative UI objects are serialized into a lightweight virtual DOM tree and rendered by native QML components in the main IDE window.

### Directory Structure

Extensions live in either the user directory (`~/.dgx/extensions/<extension_name>/`) or the installation folder (`extensions/<extension_name>/`):

```text
my_companion_extension/
├── extension.json       # Required metadata manifest
├── main.py              # Required Python entrypoint
├── assets/              # Optional media assets (images, audio, video)
│   ├── mascot.gif
│   ├── chime.wav
│   └── icon.png
└── README.md            # Documentation
```

### The Manifest (`extension.json`)

Every extension must have an `extension.json` file in its root:

```json
{
  "id": "mycompany.screen_companion",
  "name": "Screen Companion & Mascots",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "An interactive floating assistant on your editor screen.",
  "main": "main.py",
  "icon": "assets/icon.png",
  "categories": ["Tools", "Fun"]
}
```

### Entrypoint & Hooks

`main.py` must define an `activate(ctx)` function and optionally a `deactivate(ctx)` function:

```python
# main.py

def activate(ctx):
    """
    Called when the extension is loaded or enabled.
    :param ctx: DGXExtensionContext instance providing access to all subsystems.
    """
    ctx.notifications.show("Companion", "Screen Companion has been activated!")
    
    # Initialize your widgets, settings, shortcuts, and hooks here

def deactivate(ctx):
    """
    Called when the extension is disabled or the IDE shuts down.
    Perform any custom resource cleanup here.
    """
    pass
```

---

## 2. The Extension Context (`ctx`)

The `ctx` object passed to `activate()` gives access to all IDE services.

### Subsystem Index

| Subsystem | Description |
| :--- | :--- |
| `ctx.ui` | Declarative UI builder (widgets, cards, inputs, tabs, floating views, dialogs). |
| `ctx.settings` | Register and read custom configuration in the IDE Preferences window. |
| `ctx.shortcuts` | Register global keyboard shortcuts (`Ctrl+Alt+...`). |
| `ctx.editor` | Query current file path, cursor position, selected text, or full buffer. |
| `ctx.theme` | Inspect current theme palette (colors, background, text, accent, mode). |
| `ctx.audio` | Play audio files (MP3/WAV) or synthesized tone beeps. |
| `ctx.particles` | Trigger GPU particle bursts (confetti, snow, stars, bubbles, hearts). |
| `ctx.dialogs` | Display native message boxes, confirm prompts, file & folder pickers. |
| `ctx.clipboard` | Read and write text to the OS clipboard. |
| `ctx.notifications` | Show non-intrusive toast messages in the IDE. |
| `ctx.system` | Run subprocess shell commands and open external URLs in the browser. |
| `ctx.timers` | Schedule one-shot timeouts or repeating interval callbacks. |

---

### `ctx.ui`

Factory for constructing all UI components, dialogs, and tabs.

```python
# Create window view hosts
widget = ctx.ui.create_floating_widget(id="my_pet", x=500, y=300, draggable=True)
popup = ctx.ui.create_popup(title="Toolbox", width=400, height=350, modal=True)
tab = ctx.ui.create_tab(id="analytics_tab", title="Stats", icon="chart")

# Instantiate any component
button = ctx.ui.Button("Click Me", on_click=lambda: print("Clicked!"))
input_box = ctx.ui.TextInput(placeholder="Enter search...", on_change=lambda val: print(val))
```

---

### `ctx.settings`

Seamlessly register custom settings in the **DGX Settings Dialog (Preferences -> Extensions)**.

#### `ctx.settings.register_setting(key, title, type, default, options=None, description="")`

* **`key`** (`str`): Unique identifier for this setting.
* **`title`** (`str`): Human-readable label displayed in the UI.
* **`type`** (`str`):
  * `"boolean"`: Rendered as a toggle Switch.
  * `"string"`: Rendered as a Text input.
  * `"select"`: Rendered as a Dropdown Select menu (requires `options`).
  * `"slider"`: Rendered as an interactive slider with range.
* **`default`** (`any`): Default value.
* **`options`** (`list`): List of choices for `"select"` type, or `{"min": 0, "max": 100, "step": 1}` for `"slider"`.
* **`description`** (`str`): Explanatory help text beneath the setting.

```python
# Register boolean switch
ctx.settings.register_setting(
    key="sound_enabled",
    title="Enable Sound Effects",
    type="boolean",
    default=True,
    description="Play chimes when coding milestones are reached."
)

# Register dropdown selection
ctx.settings.register_setting(
    key="mascot_skin",
    title="Mascot Avatar",
    type="select",
    default="cat",
    options=["cat", "dog", "robot", "wizard"],
    description="Choose your companion appearance."
)

# Register slider
ctx.settings.register_setting(
    key="speech_speed",
    title="Speech Bubble Speed (ms)",
    type="slider",
    default=3000,
    options={"min": 1000, "max": 10000, "step": 500},
    description="How long dialogue bubbles remain on screen."
)

# Read setting at runtime
is_sound_on = ctx.settings.get("sound_enabled", True)

# Update setting programmatically
ctx.settings.set("sound_enabled", False)
```

---

### `ctx.shortcuts`

Bind global keyboard shortcuts that trigger Python callback functions.

#### `ctx.shortcuts.register(key_sequence, callback, description="")`

* **`key_sequence`** (`str`): Key combo string (e.g. `"Ctrl+Alt+P"`, `"F9"`, `"Shift+Alt+M"`).
* **`callback`** (`callable`): Function with no arguments called when pressed.
* **`description`** (`str`): Short description of the shortcut.

```python
def toggle_companion():
    if widget.visible:
        widget.hide()
    else:
        widget.show()

ctx.shortcuts.register("Ctrl+Alt+C", toggle_companion, "Toggle Screen Companion")
```

---

### `ctx.editor`

Inspect the active editor file, cursor, and text content.

| Method | Return Type | Description |
| :--- | :--- | :--- |
| `ctx.editor.get_active_file()` | `str` | Full absolute path of currently opened file in the active tab. |
| `ctx.editor.get_text()` | `str` | Entire text contents of current editor buffer. |
| `ctx.editor.get_selected_text()` | `str` | Currently highlighted/selected text. |
| `ctx.editor.get_cursor_position()` | `dict` | Cursor location: `{"line": int, "column": int, "index": int}`. |
| `ctx.editor.get_line_count()` | `int` | Total number of lines in the active document. |
| `ctx.editor.on_change(callback)` | `None` | Hook called when the user types in the editor (`callback(text)`). |
| `ctx.editor.on_save(callback)` | `None` | Hook called when a file is saved (`callback(file_path)`). |

```python
def on_user_save(file_path):
    ctx.notifications.show("Companion", f"Saved {file_path}! Great job!")
    ctx.particles.emit("stars", {"x": 600, "y": 300}, count=30)
    ctx.audio.beep(880, 150)

ctx.editor.on_save(on_user_save)
```

---

### `ctx.theme`

Query the active IDE theme colors to make your UI seamlessly adapt to dark, light, or custom user themes.

| Method | Return Type | Description |
| :--- | :--- | :--- |
| `ctx.theme.get_palette()` | `dict` | Dictionary of color tokens (`background`, `surface`, `border`, `text_primary`, `text_secondary`, `accent`, `accent_hover`, `error`, `success`). |
| `ctx.theme.get_color(token_name)` | `str` | Hex color code for a specific token (e.g. `"accent"`, `"surface"`). |
| `ctx.theme.is_dark_mode()` | `bool` | `True` if active theme is dark mode; `False` if light. |

```python
palette = ctx.theme.get_palette()
my_card = ctx.ui.Card(
    title="Adaptive Card",
    background=palette["surface"],
    border_color=palette["accent"]
)
```

---

### `ctx.audio`

Play sound effects or generate tones.

#### `ctx.audio.play_sound(file_path, volume=1.0)`
Plays a local audio file (`.wav`, `.mp3`, `.ogg`). `file_path` can be relative to the extension folder or an absolute path.

#### `ctx.audio.beep(frequency=440, duration_ms=200)`
Emits a synthesized audio chime tone at the specified frequency (in Hz) and duration.

```python
# Play audio file
ctx.audio.play_sound("assets/meow.wav", volume=0.8)

# Play chime tone
ctx.audio.beep(523, 150) # C5
ctx.audio.beep(659, 150) # E5
ctx.audio.beep(784, 250) # G5
```

---

### `ctx.particles`

Spawn GPU-accelerated particle physics effects on top of the editor.

#### `ctx.particles.emit(effect_type, position, count=40, duration_ms=2000)`

* **`effect_type`** (`str`): `"confetti"`, `"snow"`, `"stars"`, `"bubbles"`, or `"hearts"`.
* **`position`** (`dict`): `{"x": int, "y": int}` coordinates.
* **`count`** (`int`): Number of particles to spawn (default: `40`).
* **`duration_ms`** (`int`): Lifetime in milliseconds (default: `2000`).

```python
# Burst of confetti at coordinates (500, 300)
ctx.particles.emit("confetti", {"x": 500, "y": 300}, count=60, duration_ms=2500)

# Floating hearts
ctx.particles.emit("hearts", {"x": 400, "y": 200}, count=25)
```

---

### `ctx.dialogs`

Show native OS message boxes and file selectors.

| Method | Parameters | Return Type | Description |
| :--- | :--- | :--- | :--- |
| `ctx.dialogs.alert(title, message)` | `title: str, message: str` | `None` | Display an OK message dialog. |
| `ctx.dialogs.confirm(title, message)` | `title: str, message: str` | `bool` | Display Yes/No confirmation dialog. |
| `ctx.dialogs.open_file(title, filters)` | `title: str, filters: str` | `str \| None` | Open file selector dialog. |
| `ctx.dialogs.save_file(title, filters)` | `title: str, filters: str` | `str \| None` | Save file selector dialog. |
| `ctx.dialogs.select_folder(title)` | `title: str` | `str \| None` | Select folder selector dialog. |

```python
if ctx.dialogs.confirm("Export Code", "Do you want to save current file as HTML?"):
    target_path = ctx.dialogs.save_file("Save HTML", "*.html")
    if target_path:
        with open(target_path, "w") as f:
            f.write("<h1>Code Export</h1>")
```

---

### `ctx.clipboard`

```python
# Read clipboard text
current_clipboard = ctx.clipboard.get_text()

# Write to clipboard
ctx.clipboard.set_text("Formatted snippet from extension")
```

---

### `ctx.notifications`

#### `ctx.notifications.show(title, message, level="info")`
* **`level`**: `"info"`, `"warning"`, or `"error"`.

```python
ctx.notifications.show("Success", "Build completed in 1.4s!", level="info")
```

---

### `ctx.terminal`

Interact directly with the built-in DGX Terminal panel.

```python
# Send a command to run in the user's active terminal panel
ctx.terminal.send("npm run build")
ctx.terminal.run("python manage.py runserver")

# Check working directory of the terminal
current_dir = ctx.terminal.get_cwd()

# Check if a command is currently executing
if not ctx.terminal.is_running():
    ctx.terminal.send("echo Ready!")

# Send Ctrl+C / Interrupt to stop a running command
ctx.terminal.interrupt()

# Clear terminal screen
ctx.terminal.clear()
```

---

### `ctx.system`

Execute background subprocesses or open URLs.

```python
# 1. Synchronous subprocess execution
result = ctx.system.run_command(["git", "status", "--short"])
print(result["stdout"], result["exit_code"])

# 2. Asynchronous execution (Runs in background thread without freezing the UI!)
def on_build_done(res):
    if res["exit_code"] == 0:
        ctx.notifications.show("Build Passed", "All unit tests succeeded!", level="info")
    else:
        ctx.notifications.show("Build Failed", res["stderr"], level="error")

ctx.system.run_command_async(["pytest", "-q"], callback=on_build_done)

# 3. Open URL in default browser
ctx.system.open_url("https://github.com")
```

---

### `ctx.timers`

```python
# Execute after 3 seconds once
timer_id = ctx.timers.set_timeout(lambda: print("3 seconds passed"), 3000)

# Repeat every 5 seconds
interval_id = ctx.timers.set_interval(lambda: print("Tick"), 5000)

# Clear a timer
ctx.timers.clear_timer(interval_id)
```

---

## 3. View Hosts

DGX provides 3 top-level view hosts for displaying your UI:

### Floating Screen Mascots

`widget = ctx.ui.create_floating_widget(id, x=100, y=100, draggable=True, always_on_top=True)`

A floating widget hovers directly over the editor viewport. It can be dragged anywhere on screen by the user, display animated speech bubbles, and animate across coordinates.

#### Properties & Methods:
* `widget.set_content(component)`: Set the UI tree rendered inside the floating item.
* `widget.say(text, duration_ms=4000)`: Show an animated speech bubble pointing at the mascot.
* `widget.dismiss_bubble()`: Close the speech bubble immediately.
* `widget.move_to(x, y)`: Move the mascot to new coordinates.
* `widget.animate(animation_type, duration_ms=500)`: Trigger animations (`"bounce"`, `"shake"`, `"pulse"`, `"fade_in"`, `"fade_out"`).
* `widget.on_click(callback)`: Hook called when the user clicks the mascot.
* `widget.on_drag(callback)`: Hook called when the user drags the mascot (`callback({"x": x, "y": y})`).
* `widget.show()` / `widget.hide()`: Toggle visibility.
* `widget.destroy()`: Remove the widget completely.

---

### Custom Popups & Modals

`popup = ctx.ui.create_popup(title="Toolbox", width=500, height=400, modal=True, closable=True)`

A high-elevation popup modal centered on screen with an automatic dark backdrop click-off overlay.

#### Properties & Methods:
* `popup.set_content(component)`: Mount any layout or component tree.
* `popup.show()`: Display the modal.
* `popup.close()`: Dismiss the modal.

---

### Custom Workspace Tabs

`tab = ctx.ui.create_tab(id="my_tab", title="Dashboard", icon="code", closable=True)`

Renders your custom UI as a first-class editor tab alongside code files.

#### Properties & Methods:
* `tab.set_content(component)`: Mount layout tree inside the tab.
* `tab.show()`: Open and focus the tab.
* `tab.close()`: Close the tab.

---

## 4. Component Catalog

DGX provides **27 declarative UI components** in `ctx.ui.*`.

### Layout Containers

#### 1. `ctx.ui.Row(items, spacing=8, alignment="left", padding=0)`
Arranges child elements horizontally.

#### 2. `ctx.ui.Column(items, spacing=8, alignment="top", padding=0)`
Arranges child elements vertically.

#### 3. `ctx.ui.Grid(items, columns=2, spacing=8, padding=0)`
Arranges children in a multi-column responsive grid.

#### 4. `ctx.ui.Card(title="", subtitle="", items=None, background=None, border_color=None, padding=16)`
A container with an optional title header, drop shadow elevation, and rounded corners.

#### 5. `ctx.ui.Box(content=None, width=None, height=None, background=None, border_color=None, border_width=1, radius=6, padding=8)`
A flexible container with custom dimensions, borders, and background styling.

#### 6. `ctx.ui.ScrollView(content, height=300, show_scrollbars=True)`
A scrollable container for long forms or dashboards.

#### 7. `ctx.ui.SplitView(left_item, right_item, orientation="horizontal", split_ratio=0.5)`
A resizable two-pane split layout.

#### 8. `ctx.ui.Spacer(size=12, orientation="vertical")`
Transparent spacing between elements.

#### 9. `ctx.ui.Divider(orientation="horizontal", color=None)`
Subtle separating hairline rule.

---

### Typography & Indicators

#### 10. `ctx.ui.Text(text, size=13, color=None, bold=False, italic=False, wrap=True)`
Standard text block.

#### 11. `ctx.ui.Header(text, level=2, color=None)`
Section header (`level`: `1`, `2`, `3`, `4`).

#### 12. `ctx.ui.Badge(text, color="#ffffff", background="#6366f1", size=11)`
Pill badge for statuses and tags.

#### 13. `ctx.ui.ProgressBar(value=50, max_value=100, label="", color="#6366f1", height=8)`
Interactive progress indicator bar.

#### 14. `ctx.ui.MarkdownViewer(markdown_text, background=None)`
Rich formatted Markdown renderer (headings, code blocks, bold, lists).

#### 15. `ctx.ui.CodeEditor(initial_code="", language="python", read_only=False, height=200)`
Syntax-highlighted code editing box inside your custom UI.

---

### Inputs & Forms

#### 16. `ctx.ui.TextInput(placeholder="", default="", password=False, on_change=None, on_submit=None)`
Single-line text input field.

#### 17. `ctx.ui.TextArea(placeholder="", default="", rows=4, on_change=None)`
Multi-line text editor field.

#### 18. `ctx.ui.Checkbox(label, checked=False, on_change=None)`
Standard checkable box with label.

#### 19. `ctx.ui.Switch(label, checked=False, on_change=None)`
Modern sliding toggle switch.

#### 20. `ctx.ui.Select(options, default=None, label="", on_change=None)`
Dropdown select menu. `options` can be a list of strings (`["A", "B", "C"]`) or tuples (`[("val_a", "Label A"), ...]`).

#### 21. `ctx.ui.Slider(min_value=0, max_value=100, step=1, value=50, label="", on_change=None)`
Numeric drag slider.

#### 22. `ctx.ui.ColorPicker(default="#6366f1", label="Select Color", on_change=None)`
Color selection tool.

---

### Buttons & Actions

#### 23. `ctx.ui.Button(label, on_click=None, variant="primary", icon=None, size="medium", disabled=False)`
Interactive push button.
* **`variant`**: `"primary"`, `"secondary"`, `"danger"`, `"outline"`, `"ghost"`.
* **`size`**: `"small"`, `"medium"`, `"large"`.

#### 24. `ctx.ui.IconButton(icon, on_click=None, tooltip="", size=32)`
Compact icon-only button with hover tooltip.

---

### Multimedia & Graphics

#### 25. `ctx.ui.Image(source, width=None, height=None, fill_mode="contain", radius=0)`
Renders PNG, JPG, SVG, and animated GIF files. `source` can be a local file path or remote URL.

#### 26. `ctx.ui.SpriteSheet(source, frame_width=32, frame_height=32, frame_count=8, fps=12, playing=True, loop=True)`
Renders animated 2D sprite sheets (ideal for game characters, floating pets, and mascots).

#### 27. `ctx.ui.Video(source, autoplay=True, loop=True, muted=False, controls=True, width=400, height=225)`
Embedded video player supporting MP4, WebM, and MKV formats.

#### 28. `ctx.ui.Canvas(width=300, height=200, drawing_commands=None)`
Custom 2D vector drawing surface for lines, circles, polygons, and charts.

#### 29. `ctx.ui.WebView(url="", html="", width=500, height=400)`
Full web browser viewport rendering remote websites or custom local HTML/CSS/JS.

---

## 5. Settings & Preferences Integration

Extensions integrate automatically into the IDE's **Settings Dialog** under the **Extensions** category.

Settings are persisted in `~/.dgx/extension_settings.json` and persist across IDE restarts.

```python
# Register
ctx.settings.register_setting(
    key="cat_color",
    title="Companion Skin",
    type="select",
    default="calico",
    options=["calico", "black", "orange", "siamese"]
)

# React to changes
def check_settings():
    chosen_skin = ctx.settings.get("cat_color", "calico")
    print(f"Active skin is {chosen_skin}")
```

---

## 6. Complete Code Examples

### Example 1: Interactive Desktop Pet / Screen Mascot

A draggable pet sitting on your editor screen that speaks when you save code and purrs when clicked:

```python
# main.py
def activate(ctx):
    # 1. Register mascot settings in Preferences
    ctx.settings.register_setting(
        key="pet_sound",
        title="Play Pet Chimes",
        type="boolean",
        default=True
    )
    
    # 2. Create draggable floating mascot
    pet = ctx.ui.create_floating_widget(
        id="desktop_pet",
        x=650,
        y=400,
        draggable=True
    )

    # 3. Build mascot appearance
    avatar = ctx.ui.Image("assets/mascot.gif", width=80, height=80)
    status_badge = ctx.ui.Badge("Happy", background="#10b981")
    
    pet.set_content(ctx.ui.Column(
        alignment="center",
        items=[avatar, status_badge]
    ))
    
    # 4. Reaction on mascot click
    def on_pet_click():
        pet.animate("bounce")
        pet.say("Purrrr! Keep up the good coding!")
        if ctx.settings.get("pet_sound", True):
            ctx.audio.beep(880, 120)
            
    pet.on_click(on_pet_click)
    pet.say("Hello! I am your coding companion!")
    
    # 5. React to editor file save
    def on_file_save(file_path):
        pet.animate("pulse")
        pet.say("Saved! Outstanding work!")
        ctx.particles.emit("stars", {"x": pet.x, "y": pet.y}, count=25)
        
    ctx.editor.on_save(on_file_save)
    
    # 6. Global shortcut to toggle mascot
    def toggle_pet():
        if pet.visible:
            pet.hide()
        else:
            pet.show()
            
    ctx.shortcuts.register("Ctrl+Alt+M", toggle_pet, "Toggle Mascot Pet")

def deactivate(ctx):
    pass
```

---

### Example 2: Quick-Actions Modal Dialog

A custom popup modal triggered via `Ctrl+Alt+T`:

```python
# main.py
def activate(ctx):
    popup = ctx.ui.create_popup(
        title="Developer Quick Toolbox",
        width=460,
        height=380,
        modal=True
    )
    
    url_input = ctx.ui.TextInput(placeholder="Enter API endpoint or search...")
    format_select = ctx.ui.Select(options=["JSON", "YAML", "XML"], default="JSON")
    status_label = ctx.ui.Text("Ready")
    
    def on_run_clicked():
        status_label.text = f"Executing query formatted as {format_select.value}..."
        ctx.particles.emit("confetti", {"x": 230, "y": 150}, count=30)
        ctx.notifications.show("Toolbox", "Operation executed successfully!")
        popup.close()

    popup.set_content(ctx.ui.Column(spacing=12, padding=16, items=[
        ctx.ui.Header("API Quick Query", level=2),
        ctx.ui.Text("Test external endpoints without leaving your editor."),
        url_input,
        format_select,
        ctx.ui.Row(spacing=10, items=[
            ctx.ui.Button("Execute", on_click=on_run_clicked, variant="primary"),
            ctx.ui.Button("Cancel", on_click=popup.close, variant="ghost")
        ]),
        status_label
    ]))
    
    ctx.shortcuts.register("Ctrl+Alt+T", popup.show, "Open Quick Toolbox Modal")
```

---

### Example 3: Multimedia Workspace Tab

A full workspace tab displaying analytics and media:

```python
# main.py
def activate(ctx):
    tab = ctx.ui.create_tab(
        id="dev_dashboard",
        title="Project Hub",
        icon="sparkles"
    )
    
    progress = ctx.ui.ProgressBar(value=75, label="Project Completion")
    
    tab.set_content(ctx.ui.ScrollView(
        height=600,
        content=ctx.ui.Column(spacing=16, padding=24, items=[
            ctx.ui.Header("Project Performance & Media Hub", level=1),
            ctx.ui.Grid(columns=3, items=[
                ctx.ui.Card("Files", items=[ctx.ui.Text("42 modules")]),
                ctx.ui.Card("Tests", items=[ctx.ui.Badge("100% Passed", background="#10b981")]),
                ctx.ui.Card("Engine", items=[ctx.ui.Text("DGX Pure-Python v2.0")])
            ]),
            progress,
            ctx.ui.Header("Documentation Walkthrough", level=3),
            ctx.ui.Video("assets/tutorial.mp4", width=520, height=292),
            ctx.ui.MarkdownViewer("### Notes\n- All systems running smoothly.\n- Pure Python extensions active.")
        ])
    ))
    
    # Register shortcut to open tab
    ctx.shortcuts.register("Ctrl+Alt+D", tab.show, "Open Project Hub Tab")
```

---

### Example 4: Confetti & Sound Effects on File Save

Reward yourself whenever you write code:

```python
# main.py
def activate(ctx):
    ctx.settings.register_setting("confetti_on_save", "Confetti on Save", "boolean", True)
    
    def on_save(file_path):
        if ctx.settings.get("confetti_on_save", True):
            # Particle burst across top of editor
            ctx.particles.emit("confetti", {"x": 600, "y": 200}, count=50, duration_ms=2500)
            # Melodic chime
            ctx.audio.beep(600, 100)
            ctx.audio.beep(800, 150)
            
    ctx.editor.on_save(on_save)
```

---

## Conclusion

With the **DGX Pure-Python Extension Engine**, extensions are:
1. **100% Pythonic**: No QML, no HTML/CSS required.
2. **GPU Accelerated**: Declarative trees render to native C++/Qt Quick primitives.
3. **Deeply Integrated**: Floating mascots, tabs, modals, settings, audio, and particles all work out-of-the-box.

