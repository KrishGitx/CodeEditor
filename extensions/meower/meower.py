"""
meower.py - Sample DGX Studio Extension
Demonstrates:
- Activation lifecycle
- Command registration
- Local analysis without sending whole files to AI
- Contributed runner & tool dependency
"""

import time


def meow_command():
    return "Meow! 🐱 Your code looks purr-fectly formatted."


def suggest_tip_command():
    return "Meower Tip: Keep functions under 30 lines and prefer descriptive names over abbreviations! 🐾"


def activate(api):
    """Entry point called when extension is activated by DGX Studio."""
    print("[Meower] Extension activated! Initializing companion hooks...")

    api.register_command("meower.meow", meow_command)
    api.register_command("meower.suggestTip", suggest_tip_command)

    api.show_message("Meower Companion is ready to assist! 🐱", level="info")


def deactivate():
    print("[Meower] Extension deactivated.")
