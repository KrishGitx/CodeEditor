"""
ExtensionSDK.py - Pure-Python Extension SDK for DGX Studio
Provides a comprehensive, declarative UI and capability framework allowing extension authors
to build custom floating widgets, popups, editor tabs, multimedia audio/video players,
interactive canvas drawings, custom settings, and keyboard shortcuts in 100% pure Python.
"""

import os
import sys
import time
import json
import uuid
import threading
import subprocess
from typing import Dict, List, Optional, Any, Callable, Union

# Global registry of active SDK instances
_active_contexts: Dict[str, 'DGXExtensionContext'] = {}


class UIComponent:
    """Base class for all pure-Python UI components."""
    def __init__(self, component_type: str, component_id: Optional[str] = None, **kwargs):
        self.id = component_id or f"cmp_{uuid.uuid4().hex[:8]}"
        self.type = component_type
        self.props: Dict[str, Any] = kwargs
        self._events: Dict[str, Callable] = {}
        self._parent: Optional['UIComponent'] = None
        self._context: Optional['DGXExtensionContext'] = None

    def set_prop(self, key: str, value: Any) -> 'UIComponent':
        self.props[key] = value
        self._notify_update()
        return self

    def get_prop(self, key: str, default: Any = None) -> Any:
        return self.props.get(key, default)

    def on(self, event_name: str, callback: Callable) -> 'UIComponent':
        self._events[event_name] = callback
        return self

    def trigger_event(self, event_name: str, payload: Any = None) -> Any:
        cb = self._events.get(event_name)
        if callable(cb):
            try:
                if payload is not None:
                    return cb(payload)
                return cb()
            except Exception as e:
                print(f"[ExtensionSDK] Error in event '{event_name}' on component '{self.id}': {e}")
        return None

    def _notify_update(self):
        if self._context:
            self._context._notify_component_update(self)
        elif self._parent:
            self._parent._notify_update()

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "type": self.type,
            "props": {}
        }
        for k, v in self.props.items():
            if callable(v):
                continue
            if isinstance(v, UIComponent):
                data["props"][k] = v.to_dict()
            elif isinstance(v, list):
                data["props"][k] = [item.to_dict() if isinstance(item, UIComponent) else item for item in v]
            else:
                data["props"][k] = v
        return data


# ==============================================================================
# LAYOUT & CONTAINER COMPONENTS
# ==============================================================================

class Container(UIComponent):
    """Base container holding child components."""
    def __init__(self, component_type: str, items: Optional[List[UIComponent]] = None, **kwargs):
        super().__init__(component_type, **kwargs)
        self.children: List[UIComponent] = []
        if items:
            for item in items:
                self.add(item)

    def add(self, component: UIComponent) -> 'Container':
        if isinstance(component, UIComponent):
            component._parent = self
            component._context = self._context
            self.children.append(component)
            self._notify_update()
        return self

    def remove(self, component_or_id: Union[UIComponent, str]) -> 'Container':
        cid = component_or_id.id if isinstance(component_or_id, UIComponent) else component_or_id
        self.children = [c for c in self.children if c.id != cid]
        self._notify_update()
        return self

    def clear(self) -> 'Container':
        self.children.clear()
        self._notify_update()
        return self

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["children"] = [child.to_dict() for child in self.children]
        return d


class Row(Container):
    """Horizontal linear layout."""
    def __init__(self, items: Optional[List[UIComponent]] = None, spacing: int = 8, align: str = "center", **kwargs):
        super().__init__("row", items=items, spacing=spacing, align=align, **kwargs)


class Column(Container):
    """Vertical linear layout."""
    def __init__(self, items: Optional[List[UIComponent]] = None, spacing: int = 8, align: str = "left", **kwargs):
        super().__init__("column", items=items, spacing=spacing, align=align, **kwargs)


class Grid(Container):
    """Grid layout with specified columns."""
    def __init__(self, items: Optional[List[UIComponent]] = None, columns: int = 2, spacing: int = 8, **kwargs):
        super().__init__("grid", items=items, columns=columns, spacing=spacing, **kwargs)


class Card(Container):
    """Styled elevated container card with background, padding, and subtle border."""
    def __init__(self, title_or_items: Any = None, items: Optional[List[UIComponent]] = None, title: str = "", subtitle: str = "",
                 background: str = "", border_color: str = "", border_radius: int = 6, padding: int = 12, **kwargs):
        if isinstance(title_or_items, str):
            actual_title = title_or_items or title
            actual_items = items
        elif isinstance(title_or_items, list):
            actual_title = title
            actual_items = title_or_items if items is None else items
        else:
            actual_title = title
            actual_items = items
        super().__init__("card", items=actual_items, title=actual_title, subtitle=subtitle,
                         background=background, border_color=border_color, border_radius=border_radius,
                         padding=padding, **kwargs)


class Box(Container):
    """Generic box container with custom width, height, padding, margin, and borders."""
    def __init__(self, content_or_items: Any = None, items: Optional[List[UIComponent]] = None, width: Optional[int] = None, height: Optional[int] = None,
                 background: str = "", border_radius: int = 4, padding: int = 0, **kwargs):
        if content_or_items is not None:
            if isinstance(content_or_items, list):
                actual_items = content_or_items
            elif isinstance(content_or_items, UIComponent):
                actual_items = [content_or_items]
            else:
                actual_items = items
        else:
            actual_items = items
        super().__init__("box", items=actual_items, width=width, height=height,
                         background=background, border_radius=border_radius, padding=padding, **kwargs)


class ScrollView(Container):
    """Scrollable view area for long or wide content."""
    def __init__(self, content: Any = None, items: Optional[List[UIComponent]] = None, scroll_x: bool = False, scroll_y: bool = True,
                 height: Optional[int] = None, **kwargs):
        if content is not None:
            if isinstance(content, list):
                actual_items = content
            elif isinstance(content, UIComponent):
                actual_items = [content]
            else:
                actual_items = items
        else:
            actual_items = items
        super().__init__("scrollview", items=actual_items, scroll_x=scroll_x, scroll_y=scroll_y, height=height, **kwargs)


class SplitView(UIComponent):
    """Resizable split pane layout."""
    def __init__(self, left: UIComponent, right: UIComponent, orientation: str = "horizontal",
                 split_ratio: float = 0.5, **kwargs):
        super().__init__("splitview", **kwargs)
        self.left = left
        self.right = right
        self.orientation = orientation
        self.split_ratio = split_ratio

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["left"] = self.left.to_dict() if self.left else None
        d["right"] = self.right.to_dict() if self.right else None
        d["orientation"] = self.orientation
        d["split_ratio"] = self.split_ratio
        return d


class Spacer(UIComponent):
    """Expanding flex space or fixed gap."""
    def __init__(self, size: Optional[int] = None, **kwargs):
        super().__init__("spacer", size=size, **kwargs)


class Divider(UIComponent):
    """Horizontal or vertical subtle divider line."""
    def __init__(self, orientation: str = "horizontal", color: str = "", **kwargs):
        super().__init__("divider", orientation=orientation, color=color, **kwargs)


# ==============================================================================
# PRESENTATION & TYPOGRAPHY COMPONENTS
# ==============================================================================

class Text(UIComponent):
    """Styled text label."""
    def __init__(self, text: str = "", size: int = 12, bold: bool = False, italic: bool = False,
                 color: str = "", align: str = "left", selectable: bool = False, wrap: bool = True, **kwargs):
        super().__init__("text", text=text, size=size, bold=bold, italic=italic,
                         color=color, align=align, selectable=selectable, wrap=wrap, **kwargs)

    def set_text(self, text: str) -> 'Text':
        self.props["text"] = text
        self._notify_update()
        return self

    @property
    def value(self) -> str:
        return self.props.get("text", "")

    @value.setter
    def value(self, val: str):
        self.set_text(val)


class Header(UIComponent):
    """Header block with title and optional subtitle."""
    def __init__(self, title: str = "", subtitle: str = "", size: int = 16, **kwargs):
        super().__init__("header", title=title, subtitle=subtitle, size=size, **kwargs)

    def set_title(self, title: str) -> 'Header':
        self.props["title"] = title
        self._notify_update()
        return self


class Badge(UIComponent):
    """Colored status badge or chip."""
    def __init__(self, text: str = "", color: str = "#ffffff", background: str = "#0078d4",
                 border_radius: int = 3, **kwargs):
        super().__init__("badge", text=text, color=color, background=background,
                         border_radius=border_radius, **kwargs)


class ProgressBar(UIComponent):
    """Progress bar indicator."""
    def __init__(self, value: float = 0.0, max_value: float = 100.0, label: str = "",
                 show_percentage: bool = True, color: str = "", **kwargs):
        super().__init__("progressbar", value=value, max_value=max_value, label=label,
                         show_percentage=show_percentage, color=color, **kwargs)

    def set_value(self, val: float) -> 'ProgressBar':
        self.props["value"] = val
        self._notify_update()
        return self


class MarkdownViewer(UIComponent):
    """Renders formatted GitHub Flavored Markdown with code syntax highlighting."""
    def __init__(self, content: str = "", **kwargs):
        super().__init__("markdown", content=content, **kwargs)

    def set_content(self, content: str) -> 'MarkdownViewer':
        self.props["content"] = content
        self._notify_update()
        return self


class CodeEditor(UIComponent):
    """Embedded syntax-highlighted code editor."""
    def __init__(self, code: str = "", language: str = "python", line_numbers: bool = True,
                 height: int = 180, read_only: bool = False, **kwargs):
        super().__init__("codeeditor", code=code, language=language, line_numbers=line_numbers,
                         height=height, read_only=read_only, **kwargs)

    def get_code(self) -> str:
        return self.props.get("code", "")

    def set_code(self, code: str) -> 'CodeEditor':
        self.props["code"] = code
        self._notify_update()
        return self


# ==============================================================================
# INPUTS & INTERACTION COMPONENTS
# ==============================================================================

class Button(UIComponent):
    """Interactive button with icon, label, and variant styling."""
    def __init__(self, label: str = "", on_click: Optional[Callable] = None, icon: str = "",
                 variant: str = "primary", disabled: bool = False, width: Optional[int] = None, **kwargs):
        super().__init__("button", label=label, icon=icon, variant=variant, disabled=disabled, width=width, **kwargs)
        if on_click:
            self.on("click", on_click)

    def set_label(self, label: str) -> 'Button':
        self.props["label"] = label
        self._notify_update()
        return self

    def set_disabled(self, disabled: bool) -> 'Button':
        self.props["disabled"] = disabled
        self._notify_update()
        return self


class IconButton(UIComponent):
    """Compact button with a vector icon."""
    def __init__(self, icon: str, on_click: Optional[Callable] = None, tooltip: str = "",
                 size: int = 14, **kwargs):
        super().__init__("iconbutton", icon=icon, tooltip=tooltip, size=size, **kwargs)
        if on_click:
            self.on("click", on_click)


class TextInput(UIComponent):
    """Single-line text input field."""
    def __init__(self, placeholder: str = "", default: str = "", on_change: Optional[Callable] = None,
                 on_submit: Optional[Callable] = None, password: bool = False, **kwargs):
        super().__init__("textinput", placeholder=placeholder, text=default, password=password, **kwargs)
        if on_change:
            self.on("change", on_change)
        if on_submit:
            self.on("submit", on_submit)

    @property
    def value(self) -> str:
        return self.props.get("text", "")

    @value.setter
    def value(self, val: str):
        self.props["text"] = str(val)
        self._notify_update()


class TextArea(UIComponent):
    """Multi-line text editor input."""
    def __init__(self, placeholder: str = "", default: str = "", lines: int = 4,
                 on_change: Optional[Callable] = None, **kwargs):
        super().__init__("textarea", placeholder=placeholder, text=default, lines=lines, **kwargs)
        if on_change:
            self.on("change", on_change)

    @property
    def value(self) -> str:
        return self.props.get("text", "")

    @value.setter
    def value(self, val: str):
        self.props["text"] = str(val)
        self._notify_update()


class Checkbox(UIComponent):
    """Checkbox toggle with label."""
    def __init__(self, label: str = "", checked: bool = False, on_change: Optional[Callable] = None, **kwargs):
        super().__init__("checkbox", label=label, checked=checked, **kwargs)
        if on_change:
            self.on("change", on_change)

    @property
    def checked(self) -> bool:
        return bool(self.props.get("checked", False))

    @checked.setter
    def checked(self, val: bool):
        self.props["checked"] = bool(val)
        self._notify_update()


class Switch(UIComponent):
    """Modern slider toggle switch with label."""
    def __init__(self, label: str = "", checked: bool = False, on_change: Optional[Callable] = None, **kwargs):
        super().__init__("switch", label=label, checked=checked, **kwargs)
        if on_change:
            self.on("change", on_change)

    @property
    def checked(self) -> bool:
        return bool(self.props.get("checked", False))

    @checked.setter
    def checked(self, val: bool):
        self.props["checked"] = bool(val)
        self._notify_update()


class Select(UIComponent):
    """Dropdown selector for options."""
    def __init__(self, label: str = "", options: Optional[List[str]] = None, default: str = "",
                 on_change: Optional[Callable] = None, **kwargs):
        opts = options or []
        sel = default if default in opts else (opts[0] if opts else "")
        super().__init__("select", label=label, options=opts, selected=sel, **kwargs)
        if on_change:
            self.on("change", on_change)

    @property
    def selected(self) -> str:
        return self.props.get("selected", "")

    @selected.setter
    def selected(self, val: str):
        self.props["selected"] = str(val)
        self._notify_update()


class Slider(UIComponent):
    """Numeric slider control."""
    def __init__(self, label: str = "", min_value: float = 0, max_value: float = 100, default: float = 50,
                 step: float = 1, on_change: Optional[Callable] = None, value: Optional[float] = None, **kwargs):
        val = value if value is not None else default
        super().__init__("slider", label=label, min_value=min_value, max_value=max_value,
                         value=val, step=step, **kwargs)
        if on_change:
            self.on("change", on_change)

    @property
    def value(self) -> float:
        return float(self.props.get("value", 0))

    @value.setter
    def value(self, val: float):
        self.props["value"] = float(val)
        self._notify_update()


class ColorPicker(UIComponent):
    """Color selection component."""
    def __init__(self, default: str = "#0078d4", on_change: Optional[Callable] = None, **kwargs):
        super().__init__("colorpicker", color=default, **kwargs)
        if on_change:
            self.on("change", on_change)

    @property
    def color(self) -> str:
        return self.props.get("color", "#0078d4")

    @color.setter
    def color(self, val: str):
        self.props["color"] = str(val)
        self._notify_update()


# ==============================================================================
# MULTIMEDIA, GRAPHICS & CANVAS
# ==============================================================================

class Image(UIComponent):
    """Image display supporting PNG, JPG, SVG, WebP, and animated GIFs."""
    def __init__(self, source: str, width: Optional[int] = None, height: Optional[int] = None,
                 fill_mode: str = "preserve_aspect_fit", border_radius: int = 0, **kwargs):
        super().__init__("image", source=source, width=width, height=height,
                         fill_mode=fill_mode, border_radius=border_radius, **kwargs)

    def set_source(self, source: str) -> 'Image':
        self.props["source"] = source
        self._notify_update()
        return self


class SpriteSheet(UIComponent):
    """Animated sprite-sheet character or mascot frame player."""
    def __init__(self, source: str, frame_width: int, frame_height: int, total_frames: int,
                 fps: int = 12, loop: bool = True, playing: bool = True, **kwargs):
        super().__init__("spritesheet", source=source, frame_width=frame_width, frame_height=frame_height,
                         total_frames=total_frames, fps=fps, loop=loop, playing=playing,
                         current_frame=0, **kwargs)

    def play(self):
        self.props["playing"] = True
        self._notify_update()

    def pause(self):
        self.props["playing"] = False
        self._notify_update()

    def set_frame(self, frame_idx: int):
        self.props["current_frame"] = max(0, min(self.props["total_frames"] - 1, frame_idx))
        self._notify_update()


class Video(UIComponent):
    """Media video player component for MP4, WebM, and animated loops."""
    def __init__(self, source: str, width: int = 400, height: int = 240, autoplay: bool = True,
                 loop: bool = False, muted: bool = False, show_controls: bool = True,
                 on_finish: Optional[Callable] = None, **kwargs):
        super().__init__("video", source=source, width=width, height=height, autoplay=autoplay,
                         loop=loop, muted=muted, show_controls=show_controls, **kwargs)
        if on_finish:
            self.on("finish", on_finish)

    def play(self):
        if self._context:
            self._context._execute_component_action(self.id, "play")

    def pause(self):
        if self._context:
            self._context._execute_component_action(self.id, "pause")

    def seek(self, ms: int):
        if self._context:
            self._context._execute_component_action(self.id, "seek", {"position": ms})


class WebView(UIComponent):
    """Embedded interactive HTML5/CSS/JavaScript WebEngine view."""
    def __init__(self, url: str = "", html: str = "", width: Optional[int] = None,
                 height: Optional[int] = None, on_message: Optional[Callable] = None, **kwargs):
        super().__init__("webview", url=url, html=html, width=width, height=height, **kwargs)
        if on_message:
            self.on("message", on_message)

    def evaluate_js(self, script: str, callback: Optional[Callable] = None):
        if self._context:
            self._context._evaluate_webview_js(self.id, script, callback)


class Canvas(UIComponent):
    """2D vector drawing canvas with painter instructions."""
    def __init__(self, width: int = 300, height: int = 200, **kwargs):
        super().__init__("canvas", width=width, height=height, commands=[], **kwargs)
        self._paint_callback: Optional[Callable] = None

    def on_paint(self, callback: Callable):
        self._paint_callback = callback
        self.repaint()

    def repaint(self):
        if callable(self._paint_callback):
            ctx = CanvasContext()
            self._paint_callback(ctx)
            self.props["commands"] = ctx.commands
            self._notify_update()


class CanvasContext:
    """Helper recording vector drawing primitives for Canvas."""
    def __init__(self):
        self.commands: List[Dict[str, Any]] = []

    def clear(self):
        self.commands.clear()

    def draw_line(self, x1: float, y1: float, x2: float, y2: float, color: str = "#ffffff", width: float = 1):
        self.commands.append({"cmd": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "color": color, "width": width})

    def draw_rect(self, x: float, y: float, w: float, h: float, fill: str = "", border: str = "", radius: float = 0):
        self.commands.append({"cmd": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, "border": border, "radius": radius})

    def draw_circle(self, cx: float, cy: float, radius: float, fill: str = "", border: str = ""):
        self.commands.append({"cmd": "circle", "cx": cx, "cy": cy, "radius": radius, "fill": fill, "border": border})

    def draw_text(self, text: str, x: float, y: float, color: str = "#ffffff", size: int = 12, bold: bool = False):
        self.commands.append({"cmd": "text", "text": text, "x": x, "y": y, "color": color, "size": size, "bold": bold})


# ==============================================================================
# HIGH-LEVEL WINDOW & VIEW CONTROLLERS
# ==============================================================================

class FloatingWidget:
    """A floating, draggable widget overlay sitting on top of the editor."""
    def __init__(self, widget_id: str, context: 'DGXExtensionContext', x: int = 700, y: int = 350,
                 width: int = 140, height: int = 140, draggable: bool = True, keep_on_top: bool = True):
        self.id = widget_id
        self._context = context
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.draggable = draggable
        self.keep_on_top = keep_on_top
        self.visible = True
        self.opacity = 1.0
        self.bubble_text = ""
        self.bubble_visible = False
        self._content: Optional[UIComponent] = None
        self._click_handler: Optional[Callable] = None
        self._drag_handler: Optional[Callable] = None

    def set_content(self, component: UIComponent) -> 'FloatingWidget':
        self._content = component
        component._context = self._context
        self._context._sync_floating_widget(self)
        return self

    def set_position(self, x: int, y: int) -> 'FloatingWidget':
        self.x = x
        self.y = y
        self._context._sync_floating_widget(self)
        return self

    def set_visible(self, visible: bool) -> 'FloatingWidget':
        self.visible = visible
        self._context._sync_floating_widget(self)
        return self

    def say(self, text: str, duration_ms: int = 4000) -> 'FloatingWidget':
        """Display an animated comic speech bubble over the widget."""
        self.bubble_text = text
        self.bubble_visible = True
        self._context._sync_floating_widget(self)

        if duration_ms > 0:
            def hide():
                self.bubble_visible = False
                self._context._sync_floating_widget(self)
            self._context.timers.set_timeout(hide, duration_ms)
        return self

    def on_click(self, callback: Callable) -> 'FloatingWidget':
        self._click_handler = callback
        return self

    def on_drag_end(self, callback: Callable) -> 'FloatingWidget':
        self._drag_handler = callback
        return self

    def animate(self, properties: Dict[str, Any], duration_ms: int = 300, easing: str = "ease_out_quad"):
        """Animate widget geometry (x, y, opacity, scale) with hardware easing."""
        self._context._animate_widget(self.id, properties, duration_ms, easing)

    def destroy(self):
        self._context._remove_floating_widget(self.id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "draggable": self.draggable,
            "keep_on_top": self.keep_on_top,
            "visible": self.visible,
            "opacity": self.opacity,
            "bubble_text": self.bubble_text,
            "bubble_visible": self.bubble_visible,
            "content": self._content.to_dict() if self._content else None
        }


class Popup:
    """A custom styled modal popup or floating dialog."""
    def __init__(self, popup_id: str, context: 'DGXExtensionContext', title: str = "Dialog",
                 width: int = 460, height: int = 320, modal: bool = True, closable: bool = True,
                 style: Optional[Dict[str, Any]] = None):
        self.id = popup_id
        self._context = context
        self.title = title
        self.width = width
        self.height = height
        self.modal = modal
        self.closable = closable
        self.style = style or {}
        self._content: Optional[UIComponent] = None
        self._close_handler: Optional[Callable] = None

    def set_content(self, component: UIComponent) -> 'Popup':
        self._content = component
        component._context = self._context
        return self

    def show(self):
        self._context._show_popup(self)

    def close(self):
        self._context._close_popup(self.id)
        if callable(self._close_handler):
            self._close_handler()

    def on_close(self, callback: Callable):
        self._close_handler = callback

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "width": self.width,
            "height": self.height,
            "modal": self.modal,
            "closable": self.closable,
            "style": self.style,
            "content": self._content.to_dict() if self._content else None
        }


class Tab:
    """A custom workspace tab inside the editor area."""
    def __init__(self, tab_id: str, context: 'DGXExtensionContext', title: str = "Custom Tab",
                 icon: str = "sparkles", closable: bool = True):
        self.id = tab_id
        self._context = context
        self.title = title
        self.icon = icon
        self.closable = closable
        self._content: Optional[UIComponent] = None
        self._close_handler: Optional[Callable] = None

    def set_content(self, component: UIComponent) -> 'Tab':
        self._content = component
        component._context = self._context
        return self

    def show(self):
        self._context._show_tab(self)

    def close(self):
        self._context._close_tab(self.id)
        if callable(self._close_handler):
            self._close_handler()

    def on_close(self, callback: Callable):
        self._close_handler = callback

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "icon": self.icon,
            "closable": self.closable,
            "content": self._content.to_dict() if self._content else None
        }


# ==============================================================================
# SUBSYSTEM MODULE MANAGERS
# ==============================================================================

class AudioEngine:
    """Audio playback engine for sound effects, streams, and chimes."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

    def play_sound(self, source: str, volume: float = 1.0):
        """Play a one-shot audio sound effect (WAV, MP3, OGG)."""
        abs_src = self._ctx._resolve_path(source)
        self._ctx._manager.play_audio_clip(abs_src, volume)

    def beep(self, frequency: int = 440, duration_ms: int = 150):
        """Produce a procedural audio chime / tone."""
        if sys.platform == "win32":
            try:
                import winsound
                threading.Thread(target=winsound.Beep, args=(frequency, duration_ms), daemon=True).start()
                return
            except Exception:
                pass
        # Fallback to play tone via manager
        self._ctx._manager.play_tone(frequency, duration_ms)


class ParticleEngine:
    """Particle effects emitter for editor overlays (confetti, snow, stars, bubbles, hearts)."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

    def emit(self, particle_type: str = "confetti", origin: Optional[Dict[str, int]] = None,
             count: int = 50, duration_ms: int = 1500):
        org = origin or {"x": 500, "y": 300}
        self._ctx._manager.emit_particles(particle_type, org.get("x", 500), org.get("y", 300), count, duration_ms)


class SettingsEngine:
    """Manages extension settings injected into the IDE's Preferences dialog."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context
        self._callbacks: Dict[str, Callable] = {}

    def register_setting(self, key: str, title: str, subtitle: str = "", type: str = "boolean",
                         default: Any = False, options: Optional[Any] = None,
                         min_value: float = 0, max_value: float = 100, on_change: Optional[Callable] = None,
                         description: str = "", **kwargs):
        """
        Registers a setting in the IDE Preferences dialog.
        type: 'boolean' (switch), 'string' (text), 'select' (dropdown), 'slider' (range)
        """
        sub = subtitle or description or kwargs.get("desc", "")
        opt_list = []
        if isinstance(options, dict):
            min_value = options.get("min", min_value)
            max_value = options.get("max", max_value)
        elif isinstance(options, list):
            opt_list = options

        spec = {
            "extension_id": self._ctx.extension_id,
            "key": key,
            "title": title,
            "subtitle": sub,
            "type": type,
            "default": default,
            "value": default,
            "options": opt_list,
            "min_value": min_value,
            "max_value": max_value
        }
        if on_change:
            self._callbacks[key] = on_change
        self._ctx._manager.register_extension_setting(self._ctx.extension_id, spec)

    def get(self, key: str, default: Any = None) -> Any:
        return self._ctx._manager.get_extension_setting(self._ctx.extension_id, key, default)

    def set(self, key: str, value: Any):
        self._ctx._manager.set_extension_setting(self._ctx.extension_id, key, value)
        cb = self._callbacks.get(key)
        if callable(cb):
            try:
                cb(value)
            except Exception as e:
                print(f"[ExtensionSDK] Setting callback error for '{key}': {e}")


class ShortcutEngine:
    """Manages keyboard shortcut bindings."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

    def register(self, key: str, callback: Callable, description: str = ""):
        """Register a keyboard shortcut (e.g. 'Ctrl+Alt+K', 'F8', 'Shift+Alt+P')."""
        self._ctx._manager.register_extension_shortcut(self._ctx.extension_id, key, callback, description)


class DialogEngine:
    """Native OS file and prompt dialogs."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

    def open_file_dialog(self, title: str = "Open File", filters: Optional[List[str]] = None) -> str:
        return self._ctx._manager.open_file_dialog(title, filters or ["All Files (*.*)"])

    def save_file_dialog(self, title: str = "Save File", default_name: str = "") -> str:
        return self._ctx._manager.save_file_dialog(title, default_name)

    def pick_folder_dialog(self, title: str = "Select Folder") -> str:
        return self._ctx._manager.pick_folder_dialog(title)

    def confirm(self, title: str, message: str) -> bool:
        return self._ctx._manager.confirm_dialog(title, message)


class ClipboardEngine:
    """System clipboard interactions."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

    def get_text(self) -> str:
        return self._ctx._manager.get_clipboard_text()

    def set_text(self, text: str):
        self._ctx._manager.copy_to_clipboard(text)


class NotificationEngine:
    """Desktop & IDE toast notifications."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

    def show(self, title: str, message: str, icon: str = "sparkles", sound: Optional[str] = None,
             actions: Optional[List[Dict[str, Any]]] = None):
        self._ctx._manager.show_notification(self._ctx.extension_id, title, message, icon, sound, actions or [])


class TerminalEngine:
    """Provides direct access to the DGX IDE Terminal panel."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

    def send(self, command: str) -> bool:
        """Send and execute a command directly in the active IDE terminal panel."""
        return self._ctx._manager.send_terminal_command(command)

    def run(self, command: str) -> bool:
        """Alias for send(). Executes command in the IDE terminal."""
        return self.send(command)

    def clear(self):
        """Clear terminal output."""
        self._ctx._manager.clear_terminal()

    def interrupt(self):
        """Send SIGINT / Ctrl+C to stop running terminal command."""
        self._ctx._manager.interrupt_terminal()

    def get_cwd(self) -> str:
        """Get the current working directory of the terminal session."""
        return self._ctx._manager.get_terminal_cwd()

    def is_running(self) -> bool:
        """Check if terminal is currently busy executing a command."""
        tb = getattr(self._ctx._manager, "_terminal_backend", None)
        return tb.is_running_cmd() if tb and hasattr(tb, "is_running_cmd") else False


class SystemEngine:
    """Shell execution and subprocess supervisor."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

    def run_command_async(self, command: Union[str, List[str]], cwd: Optional[str] = None, callback: Optional[Callable] = None):
        """Execute a shell command asynchronously in a background thread without freezing UI."""
        def worker():
            res = self.run_command(command, cwd=cwd)
            if callable(callback):
                try:
                    callback(res)
                except Exception as e:
                    print(f"[ExtensionSDK] async callback error: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def run_command(self, cmd: Union[str, List[str]], on_output: Optional[Callable] = None,
                    on_exit: Optional[Callable] = None) -> subprocess.Popen:
        return self._ctx._manager.run_subprocess(cmd, on_output, on_exit)


class TimerEngine:
    """Asynchronous timers and delayed calls."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context
        self._timers: Dict[int, threading.Timer] = {}
        self._id_counter = 0

    def set_timeout(self, callback: Callable, delay_ms: int) -> int:
        self._id_counter += 1
        tid = self._id_counter
        t = threading.Timer(delay_ms / 1000.0, callback)
        self._timers[tid] = t
        t.daemon = True
        t.start()
        return tid

    def set_interval(self, callback: Callable, interval_ms: int) -> int:
        self._id_counter += 1
        tid = self._id_counter
        active = [True]

        def loop():
            while active[0]:
                time.sleep(interval_ms / 1000.0)
                if not active[0]:
                    break
                try:
                    callback()
                except Exception as e:
                    print(f"[ExtensionSDK] Interval callback error: {e}")
                    break

        th = threading.Thread(target=loop, daemon=True)
        th.start()
        return tid

    def clear_timer(self, timer_id: int):
        t = self._timers.pop(timer_id, None)
        if t:
            t.cancel()


class EditorBridge:
    """Inspection and modification of open editor documents."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

    def get_text(self) -> str:
        return self._ctx._manager.get_active_editor_text()

    def get_selection(self) -> str:
        return self._ctx._manager.get_active_editor_selection()

    def insert_text(self, text: str):
        self._ctx._manager.insert_active_editor_text(text)

    def get_active_file(self) -> Dict[str, Any]:
        return self._ctx._manager.get_active_editor_context()

    def on_change(self, callback: Callable):
        self._ctx._manager.register_editor_change_listener(self._ctx.extension_id, callback)

    def on_save(self, callback: Callable):
        self._ctx._manager.register_editor_save_listener(self._ctx.extension_id, callback)


class ThemeBridge:
    """Access to IDE design tokens and colors."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

    def get_color(self, token: str) -> str:
        return self._ctx._manager.get_theme_color(token)

    def on_theme_changed(self, callback: Callable):
        self._ctx._manager.register_theme_listener(self._ctx.extension_id, callback)


# ==============================================================================
# UI FACADE (api.ui)
# ==============================================================================

class UIEngine:
    """Main UI builder facade exposed as api.ui."""
    def __init__(self, context: 'DGXExtensionContext'):
        self._ctx = context

        # Expose primitives directly on api.ui
        self.Row = Row
        self.Column = Column
        self.Grid = Grid
        self.Card = Card
        self.Box = Box
        self.ScrollView = ScrollView
        self.SplitView = SplitView
        self.Spacer = Spacer
        self.Divider = Divider

        self.Text = Text
        self.Header = Header
        self.Badge = Badge
        self.ProgressBar = ProgressBar
        self.MarkdownViewer = MarkdownViewer
        self.CodeEditor = CodeEditor

        self.Button = Button
        self.IconButton = IconButton
        self.TextInput = TextInput
        self.TextArea = TextArea
        self.Checkbox = Checkbox
        self.Switch = Switch
        self.Select = Select
        self.Slider = Slider
        self.ColorPicker = ColorPicker

        self.Image = Image
        self.SpriteSheet = SpriteSheet
        self.Video = Video
        self.WebView = WebView
        self.Canvas = Canvas

    def create_floating_widget(self, id: str, x: int = 700, y: int = 350, width: int = 140,
                               height: int = 140, draggable: bool = True, keep_on_top: bool = True) -> FloatingWidget:
        widget = FloatingWidget(id, self._ctx, x, y, width, height, draggable, keep_on_top)
        self._ctx._floating_widgets[id] = widget
        self._ctx._sync_floating_widget(widget)
        return widget

    def create_popup(self, title: str = "Dialog", width: int = 460, height: int = 320,
                     modal: bool = True, closable: bool = True, style: Optional[Dict[str, Any]] = None) -> Popup:
        pid = f"popup_{uuid.uuid4().hex[:6]}"
        popup = Popup(pid, self._ctx, title, width, height, modal, closable, style)
        self._ctx._popups[pid] = popup
        return popup

    def create_tab(self, id: str, title: str = "Custom Tab", icon: str = "sparkles",
                   closable: bool = True) -> Tab:
        tab = Tab(id, self._ctx, title, icon, closable)
        self._ctx._tabs[id] = tab
        return tab


# ==============================================================================
# MASTER EXTENSION CONTEXT (api)
# ==============================================================================

class DGXExtensionContext:
    """The master API context passed to module.activate(api)."""
    def __init__(self, extension_id: str, manager: Any):
        self.extension_id = extension_id
        self._manager = manager
        self.path = manager.get_extension(extension_id).path if hasattr(manager, "get_extension") and manager.get_extension(extension_id) else ""

        # Subsystems
        self.ui = UIEngine(self)
        self.audio = AudioEngine(self)
        self.particles = ParticleEngine(self)
        self.settings = SettingsEngine(self)
        self.shortcuts = ShortcutEngine(self)
        self.dialogs = DialogEngine(self)
        self.clipboard = ClipboardEngine(self)
        self.notifications = NotificationEngine(self)
        self.system = SystemEngine(self)
        self.terminal = TerminalEngine(self)
        self.timers = TimerEngine(self)
        self.editor = EditorBridge(self)
        self.theme = ThemeBridge(self)

        # Internal registries
        self._floating_widgets: Dict[str, FloatingWidget] = {}
        self._popups: Dict[str, Popup] = {}
        self._tabs: Dict[str, Tab] = {}
        _active_contexts[extension_id] = self

    def register_command(self, command_id: str, callback: Callable):
        self._manager.register_extension_command(self.extension_id, command_id, callback)

    def show_message(self, message: str, level: str = "info"):
        self._manager.extensionMessageEmitted.emit(self.extension_id, message, level)

    def _resolve_path(self, rel_or_abs_path: str) -> str:
        if os.path.isabs(rel_or_abs_path):
            return rel_or_abs_path
        return os.path.join(self.path, rel_or_abs_path)

    def _sync_floating_widget(self, widget: FloatingWidget):
        self._manager.sync_floating_widget(self.extension_id, widget.to_dict())

    def _animate_widget(self, widget_id: str, properties: Dict[str, Any], duration_ms: int, easing: str):
        self._manager.animate_floating_widget(widget_id, properties, duration_ms, easing)

    def _remove_floating_widget(self, widget_id: str):
        self._floating_widgets.pop(widget_id, None)
        self._manager.remove_floating_widget(widget_id)

    def _show_popup(self, popup: Popup):
        self._manager.show_extension_popup(self.extension_id, popup.to_dict())

    def _close_popup(self, popup_id: str):
        self._manager.close_extension_popup(popup_id)

    def _show_tab(self, tab: Tab):
        self._manager.show_extension_tab(self.extension_id, tab.to_dict())

    def _close_tab(self, tab_id: str):
        self._manager.close_extension_tab(tab_id)

    def _notify_component_update(self, component: UIComponent):
        self._manager.update_extension_component(component.id, component.to_dict())


# Module level exports for convenience
ui = None
settings = None
shortcuts = None
audio = None
particles = None
dialogs = None
clipboard = None
notifications = None
system = None
timers = None
editor = None
theme = None

