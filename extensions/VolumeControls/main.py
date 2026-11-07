from ExtensionSDK import DGXExtensionContext
from pynput import mouse

_ctx = None
nm = 50
listener = None

def activate(ctx: DGXExtensionContext):
    global _ctx, nm, listener
    _ctx = ctx

    ctx.shortcuts.register("Ctrl+Alt+C", say, "toggle")
    nm = ctx.audio.get_music_volume()
    ctx.notifications.show("Volume Control", f"Volume Control extension activated! Volume: {nm}%")

    listener = mouse.Listener(on_scroll=on_scroll)
    listener.start()
    print("Listening for mouse scroll...")

def on_scroll(x, y, dx, dy):
    """
    Callback triggered whenever a scroll event occurs.
    dy > 0 means scrolling UP
    dy < 0 means scrolling DOWN
    """
    if dy > 0:
        print(f"Scrolled UP at position ({x}, {y})")
    elif dy < 0:
        print(f"Scrolled DOWN at position ({x}, {y})")

def deactivate(ctx: DGXExtensionContext):
    global listener, _ctx
    if listener:
        listener.stop()
        listener = None
    _ctx = None

def say():
    global _ctx, nm
    if _ctx:
        curr_vol = _ctx.audio.get_music_volume()
        _ctx.notifications.show("Volume Control", f"Custom extension triggered! Music volume: {curr_vol}%")
        print(f"Custom extension shortcut triggered. Volume: {curr_vol}")