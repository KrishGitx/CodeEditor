# DGX Studio Extension Developer Guide

DGX Studio features a modular, manifest-driven extension system that allows developers to extend editor capabilities without modifying the core codebase.

---

## 1. Extension Structure

A standard DGX Studio extension resides in a folder or `.dgxext` / `.zip` archive containing:

```
my-extension/
├── extension.json      # Manifest defining identity, permissions & contributions
├── main.py             # Optional Python entry point
└── icon.png            # Optional 64x64 extension icon
```

---

## 2. Extension Manifest (`extension.json`)

The manifest specifies extension metadata, requested permissions, activation conditions, and contributed features:

```json
{
  "id": "author.my-extension",
  "name": "my-extension",
  "displayName": "My Awesome Extension",
  "version": "1.0.0",
  "publisher": "AuthorName",
  "description": "Adds custom language tooling and runners to DGX Studio.",
  "main": "main.py",
  "permissions": [
    "editor",
    "terminal",
    "process"
  ],
  "activationEvents": [
    "onLanguage:python",
    "*"
  ],
  "contributes": {
    "commands": [
      {
        "command": "myExtension.hello",
        "title": "Hello from Extension",
        "category": "My Extension"
      }
    ],
    "fileIcons": [
      {
        "extension": ".xyz",
        "icon": "file-code",
        "color": "#38bdf8",
        "badge": "XYZ"
      }
    ],
    "runners": [
      {
        "extension": "xyz",
        "name": "XYZ Script Runner",
        "command": "xyz-cli run \"${filePath}\""
      }
    ],
    "formatters": [
      {
        "type": "cli",
        "provider": "xyzfmt",
        "command": "xyzfmt",
        "args": ["--write", "${filePath}"],
        "installGuide": {
          "windows": "pip install xyzfmt",
          "all": "pip install xyzfmt"
        }
      }
    ],
    "radialActions": [
      {
        "id": "my_radial_action",
        "title": "Run XYZ",
        "icon": "lightning",
        "command": "myExtension.hello"
      }
    ]
  }
}
```

---

## 3. Permission Model

DGX Studio enforces a clear permission boundary. Available permissions:
- `workspace`: Read and write files inside the workspace directory.
- `terminal`: Execute commands in terminal sessions.
- `process`: Spawn background helper processes.
- `network`: Download tools and packages.
- `ai`: Send contextual prompts to the configured AI provider.
- `editor`: Read active editor context and apply automated formatting.

Before installing third-party extensions, users are shown an inspection dialog detailing all requested permissions.

---

## 4. Extension API Reference (`main.py`)

When an extension defines `"main": "main.py"`, DGX Studio loads the module and invokes `activate(api)`:

```python
def activate(api):
    # Register a callable command
    def hello_handler():
        api.show_message("Hello from extension!")
        return "Command completed successfully"

    api.register_command("myExtension.hello", hello_handler)

    # Register dynamic runner
    api.register_runner("xyz", {
        "command": "xyz-runner \"${filePath}\"",
        "name": "XYZ Runner"
    })

    # Register dynamic file icon
    api.register_file_icon(".xyz", {
        "icon": "file-code",
        "color": "#38bdf8",
        "badge": "XYZ"
    })

def deactivate():
    pass
```

---

## 5. Installing and Testing Extensions Locally

1. Open **Extensions** panel (`Ctrl+Shift+X` or App Header Menu `File -> Extensions`).
2. Click **Install from Folder...** to test an unpacked development extension.
3. Or package your extension into a `.dgxext` / `.zip` archive and choose **Install from File...**.
