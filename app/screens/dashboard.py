from __future__ import annotations

from datetime import datetime

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from ..theme import (
    COLORS,
    FS_DISPLAY,
    FS_LG,
    FS_MD,
    FS_SM,
    FS_XS,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
)
from ..ui_components import (
    Card,
    MonitorToggle,
    PrimaryButton,
    SecondaryButton,
    SectionHeader,
    StatusDot,
    TagPill,
    TerminalBlock,
    make_label,
)


class StatCard(Card):
    animated_value = NumericProperty(0)

    def __init__(self, caption: str, color, **kwargs) -> None:
        super().__init__(
            orientation="vertical",
            padding=[dp(18), dp(14), dp(16), dp(14)],
            spacing=dp(4),
            **kwargs,
        )
        self._accent = color
        with self.canvas.after:
            self._accent_color = Color(*color[:3], 0.95)
            self._accent_stripe = RoundedRectangle(
                pos=self.pos,
                size=(dp(3), self.height),
                radius=[(dp(1.5), dp(1.5))] * 4,
            )
        self.bind(pos=self._sync_stripe, size=self._sync_stripe)

        caption_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(16),
            spacing=dp(6),
        )
        self.caption_label = Label(
            text=caption.upper(),
            color=COLORS["text_muted"],
            font_size=FS_XS,
            bold=True,
            halign="left",
            valign="middle",
        )
        self.caption_label.bind(
            size=lambda w, _v: setattr(w, "text_size", w.size)
        )
        caption_row.add_widget(self.caption_label)
        self.add_widget(caption_row)

        self.value_label = Label(
            text="0",
            color=color,
            font_size=FS_DISPLAY,
            bold=True,
            halign="left",
            valign="middle",
        )
        self.value_label.bind(
            size=lambda w, _v: setattr(w, "text_size", w.size)
        )
        self.add_widget(self.value_label)

        self._value = 0
        self._anim: Animation | None = None
        self.bind(animated_value=self._on_animated_value)

    def _sync_stripe(self, *_args) -> None:
        self._accent_stripe.pos = (self.x + dp(6), self.y + dp(14))
        self._accent_stripe.size = (dp(3), self.height - dp(28))

    def _on_animated_value(self, _w, value: float) -> None:
        self.value_label.text = str(int(round(value)))

    def set_value(self, value: int) -> None:
        if value == self._value:
            return
        if self._anim is not None:
            self._anim.cancel(self)
        self._anim = Animation(
            animated_value=float(value), d=0.35, t="out_quad"
        )
        self._anim.start(self)
        self._value = value


class DashboardScreen(Screen):
    def __init__(self, app, **kwargs) -> None:
        super().__init__(name="dashboard", **kwargs)
        self.app = app

        scroll = ScrollView(
            bar_color=(*COLORS["accent"][:3], 0.5),
            bar_inactive_color=(*COLORS["panel_alt"][:3], 0.4),
            bar_width=dp(3),
            do_scroll_x=False,
        )
        self.add_widget(scroll)

        root = BoxLayout(
            orientation="vertical",
            padding=[SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG],
            spacing=SPACE_LG,
            size_hint_y=None,
        )
        root.bind(minimum_height=root.setter("height"))
        scroll.add_widget(root)


        root.add_widget(SectionHeader("00", "Status"))

        status_card = Card(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(88),
            padding=[dp(16), dp(14), dp(16), dp(14)],
            spacing=dp(12),
        )

        dot_wrap = BoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(22),
        )
        dot_wrap.add_widget(Widget())
        self.status_dot = StatusDot(diameter=dp(12))
        dot_wrap.add_widget(self.status_dot)
        dot_wrap.add_widget(Widget())
        status_card.add_widget(dot_wrap)

        status_text = BoxLayout(
            orientation="vertical",
            spacing=dp(3),
            size_hint_x=1,
        )
        self.status_label = make_label(
            "OFFLINE",
            color=COLORS["text_muted"],
            font_size=FS_LG,
            bold=True,
        )
        self.status_sub = make_label(
            "Splunk: not contacted yet",
            color=COLORS["text_dim"],
            font_size=FS_XS,
        )
        self.poll_sub = make_label(
            "Last poll: -",
            color=COLORS["text_muted"],
            font_size=FS_XS,
        )
        status_text.add_widget(self.status_label)
        status_text.add_widget(self.status_sub)
        status_text.add_widget(self.poll_sub)
        status_card.add_widget(status_text)

        self.status_badge = TagPill(
            "IDLE",
            color=COLORS["text_muted"],
            bg_alpha=0.18,
        )
        badge_wrap = BoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(88),
        )
        badge_wrap.add_widget(Widget())
        badge_wrap.add_widget(self.status_badge)
        badge_wrap.add_widget(Widget())
        status_card.add_widget(badge_wrap)

        root.add_widget(status_card)


        root.add_widget(SectionHeader("01", "Overview"))

        counters_grid = GridLayout(
            cols=2,
            spacing=SPACE_MD,
            size_hint_y=None,
        )
        counters_grid.bind(minimum_height=counters_grid.setter("height"))

        self.card_critical = StatCard("Critical", COLORS["crit"])
        self.card_critical.size_hint_y = None
        self.card_critical.height = dp(108)

        self.card_warning = StatCard("Warnings", COLORS["warn"])
        self.card_warning.size_hint_y = None
        self.card_warning.height = dp(108)

        self.card_info = StatCard("Info", COLORS["info"])
        self.card_info.size_hint_y = None
        self.card_info.height = dp(108)

        self.card_total = StatCard("Total", COLORS["accent"])
        self.card_total.size_hint_y = None
        self.card_total.height = dp(108)

        for c in (self.card_critical, self.card_warning,
                  self.card_info, self.card_total):
            counters_grid.add_widget(c)

        root.add_widget(counters_grid)


        root.add_widget(SectionHeader("02", "Latest event"))

        self.latest_card = Card(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(16), dp(14), dp(16), dp(16)],
            spacing=dp(10),
        )
        self.latest_card.bind(minimum_height=self.latest_card.setter("height"))

        self.latest_title_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(28),
            spacing=dp(10),
        )
        self.latest_severity_pill = TagPill("INFO", color=COLORS["info"])
        self.latest_name_label = make_label(
            "No alerts yet",
            color=COLORS["text"],
            font_size=FS_LG,
            bold=True,
        )
        self.latest_title_row.add_widget(self.latest_severity_pill)
        self.latest_title_row.add_widget(self.latest_name_label)
        self.latest_card.add_widget(self.latest_title_row)

        self.latest_meta_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(24),
            spacing=dp(6),
        )
        self.latest_meta_row.add_widget(make_label(
            "Waiting for first detection from Splunk...",
            color=COLORS["text_dim"],
            font_size=FS_SM,
        ))
        self.latest_card.add_widget(self.latest_meta_row)

        self.latest_terminal = TerminalBlock(title="cmdline")
        self.latest_terminal.set_lines([
            ("$", "awaiting events from splunk..."),
        ])
        self.latest_card.add_widget(self.latest_terminal)

        root.add_widget(self.latest_card)


        root.add_widget(SectionHeader("03", "Controls"))

        controls_card = Card(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(18), dp(16), dp(18), dp(16)],
            spacing=dp(14),
        )
        controls_card.bind(minimum_height=controls_card.setter("height"))

        auto_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=dp(12),
        )
        toggle_text_box = BoxLayout(orientation="vertical", spacing=dp(2))
        toggle_text_box.add_widget(make_label(
            "Auto monitor",
            color=COLORS["text"],
            font_size=FS_MD,
            bold=True,
        ))
        self.interval_caption = make_label(
            self._interval_caption(),
            color=COLORS["text_muted"],
            font_size=FS_XS,
        )
        toggle_text_box.add_widget(self.interval_caption)
        auto_row.add_widget(toggle_text_box)

        toggle_right = BoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(72),
            spacing=dp(4),
        )
        self.monitor_state_label = make_label(
            "OFF",
            color=COLORS["text_muted"],
            font_size=FS_XS,
            bold=True,
            halign="center",
        )
        self.monitor_switch = MonitorToggle(
            active=bool(app.cfg.get("auto_monitor")),
        )
        self.monitor_switch.bind(active=self._on_monitor_toggle)
        toggle_right.add_widget(self.monitor_state_label)
        toggle_right.add_widget(self.monitor_switch)
        auto_row.add_widget(toggle_right)
        controls_card.add_widget(auto_row)
        if self.monitor_switch.active:
            self.monitor_state_label.text = "ON"
            self.monitor_state_label.color = COLORS["ok"]

        buttons_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(10),
        )
        self.refresh_btn = PrimaryButton(text="REFRESH NOW")
        self.refresh_btn.bind(on_release=self._on_refresh)
        self.clear_btn = SecondaryButton(text="CLEAR ALERTS")
        self.clear_btn.bind(on_release=self._on_clear)
        buttons_row.add_widget(self.refresh_btn)
        buttons_row.add_widget(self.clear_btn)
        controls_card.add_widget(buttons_row)

        root.add_widget(controls_card)

        spacer = BoxLayout(size_hint_y=None, height=dp(12))
        root.add_widget(spacer)

        self.app.alerts.subscribe(self._refresh_counters)
        self._refresh_counters()

        Clock.schedule_interval(self._tick, 5)

    def _interval_caption(self) -> str:
        interval = self.app.cfg.get("poll_interval") or 30
        return f"Poll every {interval}s when ON"

    def _refresh_counters(self, *_args) -> None:
        am = self.app.alerts
        self.card_critical.set_value(am.critical_count())
        self.card_warning.set_value(am.warning_count())
        self.card_info.set_value(am.info_count())
        self.card_total.set_value(am.total())

        if am.alerts:
            a = am.alerts[0]
            from ..theme import severity_color
            color = severity_color(a.severity)

            self.latest_severity_pill.text = a.severity
            self.latest_severity_pill.set_color(color)
            self.latest_severity_pill.texture_update()
            self.latest_severity_pill._on_texture_size()

            self.latest_name_label.text = a.name

            self.latest_meta_row.clear_widgets()
            for cap, val, col in (
                ("HOST", a.host, COLORS["accent"]),
                ("USER", a.user, COLORS["purple"]),
                ("CODE", a.event_code or "?", COLORS["text_dim"]),
            ):
                pill = TagPill(f"{cap}: {val}", color=col, bg_alpha=0.15)
                self.latest_meta_row.add_widget(pill)
            self.latest_meta_row.add_widget(Widget())

            self.latest_terminal.title_label.text = f"cmdline  ({a.pretty_time()})"
            self.latest_terminal.set_lines([
                ("$", a.short_command(220) or "(no commandline)"),
                f"image  : {a.image or '(unknown)'}",
                f"eventID: {a.event_code or '?'}",
            ])
        else:
            self.latest_severity_pill.text = "INFO"
            self.latest_severity_pill.set_color(COLORS["info"])
            self.latest_name_label.text = "No alerts yet"
            self.latest_meta_row.clear_widgets()
            self.latest_meta_row.add_widget(make_label(
                "Waiting for first detection from Splunk...",
                color=COLORS["text_dim"],
                font_size=FS_SM,
            ))
            self.latest_terminal.title_label.text = "cmdline"
            self.latest_terminal.set_lines([
                ("$", "awaiting events from splunk..."),
            ])

        am = self.app.alerts
        if am.last_poll_message:
            ts = datetime.now().strftime("%H:%M:%S")
            ok = am.last_poll_ok
            prefix = "OK" if ok else "ERR"
            self.poll_sub.text = f"Last poll ({prefix}): {am.last_poll_message[:60]}  ·  {ts}"
            self.poll_sub.color = COLORS["ok"] if ok else COLORS["crit"]

    def _tick(self, _dt) -> None:
        self.interval_caption.text = self._interval_caption()

    def _on_monitor_toggle(self, _switch, active: bool) -> None:
        self.monitor_state_label.text = "ON" if active else "OFF"
        self.monitor_state_label.color = COLORS["ok"] if active else COLORS["text_muted"]
        self.app.cfg.set("auto_monitor", bool(active))
        self.app.cfg.save()
        if active:
            self.app.start_monitoring()
        else:
            self.app.stop_monitoring()

    def _on_refresh(self, *_args) -> None:
        self.app.trigger_manual_refresh()

    def _on_clear(self, *_args) -> None:
        self.app.alerts.clear()

    def set_connection_status(self, ok: bool, message: str) -> None:
        if self.app.splunk.is_running():
            self.status_dot.state = "polling"
        else:
            self.status_dot.state = "ok" if ok else "error"

        if ok:
            self.status_label.text = "CONNECTED"
            self.status_label.color = COLORS["ok"]
            self.status_badge.text = "ONLINE"
            self.status_badge.set_color(COLORS["ok"])
        else:
            self.status_label.text = "DISCONNECTED"
            self.status_label.color = COLORS["crit"]
            self.status_badge.text = "ERROR"
            self.status_badge.set_color(COLORS["crit"])

        self.status_badge.texture_update()
        self.status_badge._on_texture_size()

        self.status_sub.text = (
            f"{message}  ·  {datetime.now().strftime('%H:%M:%S')}"
        )
