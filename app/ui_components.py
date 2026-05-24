from __future__ import annotations

from .theme import (
    COLORS,
    FONT_MONO,
    FONT_REGULAR,
    FS_LG,
    FS_MD,
    FS_SM,
    FS_XS,
    RADIUS,
    RADIUS_SM,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
)

from pathlib import Path

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = _PROJECT_ROOT / "LogoSIEM.png"


_LAYOUT_KEYS = {
    "size_hint_x", "size_hint_y", "size_hint", "pos_hint",
    "height", "width", "size", "pos",
}


class Card(BoxLayout):
    bg_color = ListProperty(COLORS["panel"])
    border_color = ListProperty(COLORS["border"])
    radius = NumericProperty(RADIUS)
    border_width = NumericProperty(1.0)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("padding", [SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG])
        kwargs.setdefault("spacing", SPACE_SM)
        super().__init__(**kwargs)
        with self.canvas.before:
            self._bg_color_instr = Color(*self.bg_color)
            self._bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[(self.radius, self.radius)] * 4,
            )
            self._border_color_instr = Color(*self.border_color)
            self._border_line = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, self.radius
                ),
                width=self.border_width,
            )
        self.bind(
            pos=self._sync,
            size=self._sync,
            bg_color=self._sync_colors,
            border_color=self._sync_colors,
        )

    def _sync(self, *_args) -> None:
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._bg_rect.radius = [(self.radius, self.radius)] * 4
        self._border_line.rounded_rectangle = (
            self.x, self.y, self.width, self.height, self.radius
        )

    def _sync_colors(self, *_args) -> None:
        self._bg_color_instr.rgba = self.bg_color
        self._border_color_instr.rgba = self.border_color


class _BaseRoundedButton(ButtonBehavior, Label):
    radius = NumericProperty(RADIUS_SM)
    bg_color = ListProperty(COLORS["accent"])
    bg_press = ListProperty(COLORS["accent_press"])
    border_color = ListProperty([0, 0, 0, 0])
    border_width = NumericProperty(0)

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("color", COLORS["text"])
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", FS_MD)
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(44))
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        self.bind(size=lambda w, _v: setattr(w, "text_size", w.size))

        with self.canvas.before:
            self._bg_color_instr = Color(*self.bg_color)
            self._bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[(self.radius, self.radius)] * 4,
            )
            self._border_color_instr = Color(*self.border_color)
            self._border_line = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, self.radius
                ),
                width=self.border_width if self.border_width else 1.0,
            )
        self.bind(pos=self._sync, size=self._sync, state=self._on_state_change)

    def _sync(self, *_args) -> None:
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._bg_rect.radius = [(self.radius, self.radius)] * 4
        self._border_line.rounded_rectangle = (
            self.x, self.y, self.width, self.height, self.radius
        )

    def _on_state_change(self, _w, state: str) -> None:
        if state == "down":
            self._bg_color_instr.rgba = self.bg_press
            Animation.cancel_all(self, "opacity")
            Animation(opacity=0.82, d=0.06, t="out_quad").start(self)
        else:
            self._bg_color_instr.rgba = self.bg_color
            Animation.cancel_all(self, "opacity")
            Animation(opacity=1.0, d=0.12, t="out_quad").start(self)


class PrimaryButton(_BaseRoundedButton):


    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("bg_color", COLORS["accent"])
        kwargs.setdefault("bg_press", COLORS["accent_press"])
        kwargs.setdefault("color", (1, 1, 1, 1))
        super().__init__(**kwargs)


class SecondaryButton(_BaseRoundedButton):


    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("bg_color", COLORS["panel_alt"])
        kwargs.setdefault("bg_press", COLORS["panel_hover"])
        kwargs.setdefault("border_color", COLORS["border_strong"])
        kwargs.setdefault("border_width", 1.0)
        kwargs.setdefault("color", COLORS["text"])
        super().__init__(**kwargs)


class DangerButton(_BaseRoundedButton):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("bg_color", COLORS["crit"])
        kwargs.setdefault("bg_press", (0.78, 0.18, 0.18, 1))
        kwargs.setdefault("color", (1, 1, 1, 1))
        super().__init__(**kwargs)


class TagPill(Label):


    def __init__(self, text: str, color=None, bg_alpha: float = 0.18,
                 uppercase: bool = True, **kwargs) -> None:
        color = color or COLORS["accent"]
        bg_rgba = (*color[:3], bg_alpha)

        kwargs.setdefault("font_size", FS_XS)
        kwargs.setdefault("bold", True)
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("padding", [dp(10), dp(4)])
        kwargs["color"] = color

        super().__init__(text=(text.upper() if uppercase else text), **kwargs)

        with self.canvas.before:
            self._bg_color_instr = Color(*bg_rgba)
            self._bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[(dp(10), dp(10))] * 4,
            )
        self.bind(
            texture_size=self._on_texture_size,
            pos=self._sync,
            size=self._sync,
        )
        self.texture_update()
        self._on_texture_size()

    def _on_texture_size(self, *_args) -> None:
        if not self.texture_size:
            return
        tx, ty = self.texture_size
        pad_x = self.padding[0] if isinstance(self.padding, (list, tuple)) else dp(10)
        pad_y = self.padding[1] if isinstance(self.padding, (list, tuple)) else dp(4)
        self.width = tx + pad_x * 2
        self.height = ty + pad_y * 2

    def _sync(self, *_args) -> None:
        self._bg.pos = self.pos
        self._bg.size = self.size
        r = self.height / 2
        self._bg.radius = [(r, r)] * 4

    def set_color(self, color, bg_alpha: float = 0.18) -> None:
        self.color = color
        self._bg_color_instr.rgba = (*color[:3], bg_alpha)


class SectionHeader(BoxLayout):
    def __init__(self, number: str, title: str, right_widget=None,
                 **kwargs) -> None:
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(24))
        kwargs.setdefault("spacing", dp(8))
        super().__init__(**kwargs)


        indicator = Widget(size_hint=(None, None), size=(dp(4), dp(16)))
        indicator.pos_hint = {"center_y": 0.5}
        with indicator.canvas:
            Color(*COLORS["accent"])
            self._indicator_rect = RoundedRectangle(
                pos=indicator.pos,
                size=indicator.size,
                radius=[(dp(2), dp(2))] * 4,
            )
        indicator.bind(
            pos=lambda w, _v, r=self._indicator_rect: setattr(r, "pos", w.pos),
            size=lambda w, _v, r=self._indicator_rect: setattr(r, "size", w.size),
        )
        self.add_widget(indicator)

        title_label = Label(
            text=title,
            color=COLORS["text"],
            font_size=FS_SM,
            bold=True,
            halign="left",
            valign="middle",
        )
        title_label.bind(size=lambda w, _v: setattr(w, "text_size", w.size))
        self.add_widget(title_label)

        if right_widget is not None:
            self.add_widget(right_widget)


class MonitorToggle(ButtonBehavior, Widget):


    active = BooleanProperty(False)

    def __init__(self, active: bool = False, **kwargs) -> None:
        self._pad = dp(3)
        self._thumb_sz = dp(22)
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(56), dp(30)))
        super().__init__(**kwargs)

        with self.canvas.before:
            self._track_color = Color(*COLORS["border_strong"])
            self._track = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[(dp(15), dp(15))] * 4
            )
            self._thumb_color = Color(*COLORS["text_dim"])
            tr = self._thumb_sz / 2
            self._thumb = RoundedRectangle(
                pos=self.pos,
                size=(self._thumb_sz, self._thumb_sz),
                radius=[(tr, tr)] * 4,
            )

        self.bind(pos=self._redraw, size=self._redraw)
        self._ui_ready = True
        self.active = active
        self._redraw()

    def on_active(self, *_args) -> None:
        if getattr(self, "_ui_ready", False):
            self._redraw()

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            self.active = not self.active
            return True
        return super().on_touch_up(touch)

    def _redraw(self, *_args) -> None:
        if not hasattr(self, "_track"):
            return
        x, y = self.pos
        w, h = self.width, self.height
        r = h / 2 if h else dp(15)

        if self.active:
            self._track_color.rgba = COLORS["ok"]
            self._thumb_color.rgba = (1, 1, 1, 1)
        else:
            self._track_color.rgba = COLORS["border_strong"]
            self._thumb_color.rgba = (0.75, 0.78, 0.82, 1)

        self._track.pos = (x, y)
        self._track.size = (w, h)
        self._track.radius = [(r, r)] * 4

        pad = self._pad
        ts = self._thumb_sz
        tx = x + w - ts - pad if self.active else x + pad
        ty = y + (h - ts) / 2
        self._thumb.pos = (tx, ty)
        self._thumb.size = (ts, ts)
        self._thumb.radius = [(ts / 2, ts / 2)] * 4


NeoToggle = MonitorToggle


class StatusDot(Widget):
    state = StringProperty("idle")
    _pulse = NumericProperty(0.30)

    _STATE_COLORS = {
        "ok": COLORS["ok"],
        "error": COLORS["crit"],
        "idle": COLORS["text_muted"],
        "polling": COLORS["accent"],
    }

    def __init__(self, diameter=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self._diameter = diameter or dp(12)
        self.size = (self._diameter, self._diameter)
        with self.canvas:
            self._glow_color = Color(*self._STATE_COLORS["idle"][:3], 0.28)
            self._glow = Ellipse(
                pos=(self.x - dp(4), self.y - dp(4)),
                size=(self.width + dp(8), self.height + dp(8)),
            )
            self._color = Color(*self._STATE_COLORS["idle"])
            self._ellipse = Ellipse(pos=self.pos, size=self.size)
        self._anim: Animation | None = None
        self.bind(
            pos=self._sync,
            size=self._sync,
            state=self._sync_state,
            _pulse=self._sync_pulse,
        )

    def _sync(self, *_args) -> None:
        self._glow.pos = (self.x - dp(4), self.y - dp(4))
        self._glow.size = (self.width + dp(8), self.height + dp(8))
        self._ellipse.pos = self.pos
        self._ellipse.size = self.size

    def _sync_state(self, *_args) -> None:
        rgba = self._STATE_COLORS.get(self.state, self._STATE_COLORS["idle"])
        self._color.rgba = rgba
        self._glow_color.rgba = (*rgba[:3], self._pulse)
        self._restart_animation()

    def _sync_pulse(self, *_args) -> None:
        rgba = self._STATE_COLORS.get(self.state, self._STATE_COLORS["idle"])
        self._glow_color.rgba = (*rgba[:3], self._pulse)

    def _restart_animation(self) -> None:
        if self._anim is not None:
            self._anim.cancel(self)
            self._anim = None
        if self.state == "polling":
            anim = (
                Animation(_pulse=0.65, d=0.85, t="in_out_sine")
                + Animation(_pulse=0.18, d=0.85, t="in_out_sine")
            )
            anim.repeat = True
            self._anim = anim
            anim.start(self)
        elif self.state == "error":
            anim = (
                Animation(_pulse=0.55, d=0.45, t="in_out_quad")
                + Animation(_pulse=0.25, d=0.45, t="in_out_quad")
            )
            anim.repeat = True
            self._anim = anim
            anim.start(self)
        else:
            self._pulse = 0.30


class DarkInput(BoxLayout):
    def __init__(self, **kwargs) -> None:
        layout_kwargs = {
            k: kwargs.pop(k) for k in list(kwargs.keys()) if k in _LAYOUT_KEYS
        }
        layout_kwargs.setdefault("size_hint_y", None)
        layout_kwargs.setdefault("height", dp(44))
        super().__init__(orientation="vertical", **layout_kwargs)

        with self.canvas.before:
            self._bg_color = Color(*COLORS["panel_alt"])
            self._bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[(RADIUS_SM, RADIUS_SM)] * 4,
            )
            self._border_color = Color(*COLORS["border"])
            self._border_line = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, RADIUS_SM
                ),
                width=1.0,
            )
        self.bind(pos=self._sync, size=self._sync)

        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_active", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("foreground_color", COLORS["text"])
        kwargs.setdefault("cursor_color", COLORS["accent"])
        kwargs.setdefault("hint_text_color", COLORS["text_muted"])
        kwargs.setdefault("padding", [dp(14), dp(10), dp(14), dp(10)])
        kwargs.setdefault("multiline", False)
        kwargs.setdefault("font_size", FS_MD)
        kwargs.setdefault("selection_color", (*COLORS["accent"][:3], 0.35))
        kwargs.setdefault("write_tab", False)
        self._input = TextInput(**kwargs)
        self._input.bind(focus=self._on_focus)
        self.add_widget(self._input)

    @property
    def text(self): return self._input.text
    @text.setter
    def text(self, value): self._input.text = value
    @property
    def password(self): return self._input.password
    @password.setter
    def password(self, value): self._input.password = value
    @property
    def hint_text(self): return self._input.hint_text
    @hint_text.setter
    def hint_text(self, value): self._input.hint_text = value
    @property
    def multiline(self): return self._input.multiline
    @multiline.setter
    def multiline(self, value): self._input.multiline = value
    @property
    def focus(self): return self._input.focus
    @focus.setter
    def focus(self, value): self._input.focus = value

    def _sync(self, *_args) -> None:
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border_line.rounded_rectangle = (
            self.x, self.y, self.width, self.height, RADIUS_SM
        )

    def _on_focus(self, _w, focused: bool) -> None:
        if focused:
            self._border_color.rgba = COLORS["accent"]
            self._bg_color.rgba = COLORS["panel_hover"]
        else:
            self._border_color.rgba = COLORS["border"]
            self._bg_color.rgba = COLORS["panel_alt"]


class TerminalBlock(BoxLayout):
    def __init__(self, title: str = "bash", **kwargs) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("spacing", 0)
        super().__init__(**kwargs)

        bg = (0.043, 0.058, 0.094, 1)
        self.bg_color_value = bg
        self.radius_value = RADIUS_SM

        with self.canvas.before:
            self._bg_color = Color(*bg)
            self._bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[(self.radius_value, self.radius_value)] * 4,
            )
            self._border_color = Color(*COLORS["border"])
            self._border_line = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, self.radius_value
                ),
                width=1.0,
            )
        self.bind(pos=self._sync, size=self._sync)

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(28),
            padding=[dp(10), dp(6), dp(10), dp(2)],
            spacing=dp(6),
        )

        for color in ((0.96, 0.36, 0.36, 1),
                      (0.96, 0.74, 0.18, 1),
                      (0.31, 0.78, 0.47, 1)):
            dot = Widget(size_hint=(None, None), size=(dp(10), dp(10)))
            with dot.canvas:
                Color(*color)
                e = Ellipse(pos=dot.pos, size=dot.size)
            dot.bind(
                pos=lambda w, _v, e=e: setattr(e, "pos", w.pos),
                size=lambda w, _v, e=e: setattr(e, "size", w.size),
            )
            header.add_widget(dot)

        header.add_widget(Widget(size_hint_x=None, width=dp(6)))

        self.title_label = Label(
            text=title,
            color=COLORS["text_muted"],
            font_size=FS_XS,
            font_name=FONT_MONO,
            halign="left",
            valign="middle",
        )
        self.title_label.bind(size=lambda w, _v: setattr(w, "text_size", w.size))
        header.add_widget(self.title_label)
        self.add_widget(header)

        self.body_label = Label(
            text="",
            color=COLORS["ok"],
            font_size=FS_SM,
            font_name=FONT_MONO,
            halign="left",
            valign="top",
            size_hint_y=None,
            markup=True,
            padding=[dp(12), dp(6), dp(12), dp(12)],
        )
        self.body_label.bind(
            width=lambda w, _v: setattr(w, "text_size", (w.width - dp(24), None)),
            texture_size=lambda w, _v: setattr(w, "height", w.texture_size[1] + dp(18)),
        )
        self.add_widget(self.body_label)
        self.bind(minimum_height=self.setter("height"))

    def _sync(self, *_args) -> None:
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._bg.radius = [(self.radius_value, self.radius_value)] * 4
        self._border_line.rounded_rectangle = (
            self.x, self.y, self.width, self.height, self.radius_value
        )

    def set_lines(self, lines) -> None:
        out = []
        for line in lines:
            if isinstance(line, tuple):
                prompt, text = line
                out.append(
                    f"[color={_to_hex(COLORS['accent'])}]{prompt}[/color] "
                    f"[color={_to_hex(COLORS['text'])}]{_escape(text)}[/color]"
                )
            else:
                out.append(
                    f"[color={_to_hex(COLORS['text_dim'])}]{_escape(str(line))}[/color]"
                )
        self.body_label.text = "\n".join(out) if out else " "


class AppLogo(BoxLayout):
    LOGO_H = dp(64)
    LOGO_ASPECT = 1.85

    def __init__(self, subtitle: str = "SOC Dashboard", **kwargs) -> None:
        super().__init__(
            orientation="horizontal",
            spacing=dp(10),
            size_hint=(None, None),
            **kwargs,
        )

        logo_w = self.LOGO_H * self.LOGO_ASPECT
        logo_h = self.LOGO_H

        if LOGO_PATH.is_file():
            image_kwargs = dict(
                source=str(LOGO_PATH),
                mipmap=True,
                size_hint=(None, None),
                size=(logo_w, logo_h),
            )
            try:
                image_kwargs["fit_mode"] = "contain"
                self._image = KivyImage(**image_kwargs)
            except TypeError:
                image_kwargs.pop("fit_mode", None)
                image_kwargs["allow_stretch"] = True
                image_kwargs["keep_ratio"] = True
                self._image = KivyImage(**image_kwargs)
            self.add_widget(self._image)
        else:
            self._image = None
            fallback = Label(
                text="[b]SIEM[/b] Mobile",
                markup=True,
                font_size=FS_LG,
                color=COLORS["text"],
                halign="center",
                valign="middle",
                size_hint=(None, None),
                size=(logo_w, logo_h),
            )
            fallback.bind(size=lambda w, _v: setattr(w, "text_size", w.size))
            self.add_widget(fallback)

        sub_label = Label(
            text=subtitle.upper(),
            font_size=FS_XS,
            color=COLORS["accent"],
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(None, None),
            size=(dp(118), logo_h),
        )
        sub_label.bind(size=lambda w, _v: setattr(w, "text_size", w.size))
        self.add_widget(sub_label)
        self._subtitle_label = sub_label

        self.height = logo_h
        self.width = logo_w + dp(10) + sub_label.width

    def set_subtitle(self, text: str, color=None) -> None:
        if self._subtitle_label is not None:
            self._subtitle_label.text = text.upper()
            if color is not None:
                self._subtitle_label.color = color


def _to_hex(rgba) -> str:
    r, g, b = rgba[0], rgba[1], rgba[2]
    return f"{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("[", "&bl;")
        .replace("]", "&br;")
    )

def make_label(text: str, **kwargs) -> Label:
    kwargs.setdefault("color", COLORS["text"])
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    kwargs.setdefault("font_size", FS_MD)
    lbl = Label(text=text, **kwargs)
    lbl.bind(size=lambda w, _v: setattr(w, "text_size", w.size))
    return lbl


def measure_text_height(
    text: str,
    width_px: float,
    font_size=None,
    font_name=None,
    pad_y: float = None,
    max_height: float = None,
) -> float:

    pad_y = dp(8) if pad_y is None else pad_y
    font_size = font_size or FS_SM
    probe = Label(
        text=text or " ",
        font_size=font_size,
        font_name=font_name or FONT_REGULAR,
        size_hint=(None, None),
    )
    probe.text_size = (width_px, None)
    probe.texture_update()
    th = probe.texture_size[1] if probe.texture_size else dp(20)
    h = th + pad_y
    if max_height is not None:
        h = min(h, max_height)
    return h


def make_static_label(
    text: str,
    width_px: float,
    font_size=None,
    font_name=None,
    max_height: float = None,
    **kwargs,
) -> Label:

    font_size = font_size or FS_SM
    h = measure_text_height(
        text, width_px, font_size=font_size, font_name=font_name, max_height=max_height
    )
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "top")
    kwargs.setdefault("size_hint_y", None)
    kwargs.setdefault("height", h)
    lbl = Label(text=text, font_size=font_size, **kwargs)
    if font_name:
        lbl.font_name = font_name
    lbl.text_size = (max(width_px - dp(4), dp(80)), None)
    return lbl


class MonoLogLabel(Label):

    def __init__(
        self,
        text: str = "",
        max_height: float | None = None,
        font_name: str | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("font_name", font_name or FONT_MONO)
        kwargs.setdefault("font_size", FS_SM)
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "top")
        kwargs.setdefault("size_hint_x", 1)
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("text", text or " ")
        kwargs.setdefault("padding", (dp(4), dp(4)))
        super().__init__(**kwargs)
        self._max_height = max_height
        self.bind(width=self._reflow)
        Clock.schedule_once(lambda _dt: self._reflow(self, self.width), 0)

    def _reflow(self, _instance, width: float) -> None:
        if width <= dp(16):
            return
        pad_x = self.padding[0] + self.padding[2] if isinstance(
            self.padding, (list, tuple)
        ) else dp(8)
        inner = max(width - pad_x, dp(80))
        self.text_size = (inner, None)
        self.texture_update()
        if not self.texture_size:
            return
        h = self.texture_size[1] + dp(8)
        if self._max_height is not None:
            h = min(h, self._max_height)
        self.height = max(h, dp(22))


def log_text_card(
    text: str,
    *,
    font_size=None,
    color=None,
    max_height: float | None = None,
    bg_color=None,
) -> Card:
    card = Card(
        orientation="vertical",
        size_hint_x=1,
        size_hint_y=None,
        bg_color=bg_color or (0.043, 0.058, 0.094, 1),
        padding=[dp(14), dp(12), dp(14), dp(12)],
    )
    lbl = MonoLogLabel(
        text=text,
        font_size=font_size or FS_SM,
        color=color or COLORS["text_dim"],
        max_height=max_height,
    )
    card.add_widget(lbl)

    def _sync_card_height(*_args) -> None:
        card.height = lbl.height + dp(24)

    lbl.bind(height=_sync_card_height)
    Clock.schedule_once(lambda _dt: _sync_card_height(), 0)
    return card

def hairline(color=None, height=None) -> Widget:
    color = color or COLORS["border"]
    height = height or dp(1)
    w = Widget(size_hint_y=None, height=height)
    with w.canvas:
        Color(*color)
        rect = RoundedRectangle(pos=w.pos, size=w.size, radius=[(0, 0)] * 4)
    w.bind(
        pos=lambda x, _v, r=rect: setattr(r, "pos", x.pos),
        size=lambda x, _v, r=rect: setattr(r, "size", x.size),
    )
    return w
