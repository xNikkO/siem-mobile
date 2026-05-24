from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from ..alert_manager import Alert
from ..config import CONFIG_DIR
from ..theme import (
    COLORS,
    FONT_MONO,
    FONT_REGULAR,
    FS_LG,
    FS_MD,
    FS_SM,
    FS_XS,
    RADIUS,
    SPACE_LG,
    SPACE_MD,
    severity_color,
)
from ..ui_components import (
    Card,
    DarkInput,
    MonoLogLabel,
    PrimaryButton,
    SecondaryButton,
    SectionHeader,
    TagPill,
    _BaseRoundedButton,
    log_text_card,
    make_label,
)


class FilterChip(_BaseRoundedButton):
    def __init__(self, filter_key: str, **kwargs) -> None:
        self.filter_key = filter_key
        kwargs.setdefault("radius", dp(10))
        kwargs.setdefault("bg_color", COLORS["panel_alt"])
        kwargs.setdefault("bg_press", COLORS["panel_hover"])
        kwargs.setdefault("border_color", COLORS["border"])
        kwargs.setdefault("border_width", 1.0)
        kwargs.setdefault("color", COLORS["text_dim"])
        kwargs.setdefault("font_size", FS_XS)
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("height", dp(30))
        super().__init__(**kwargs)
        self._active = False

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self.bg_color = COLORS["accent_soft"]
            self.color = COLORS["accent"]
            self.border_color = COLORS["accent"]
            self._bg_color_instr.rgba = COLORS["accent_soft"]
            self._border_color_instr.rgba = COLORS["accent"]
        else:
            self.bg_color = COLORS["panel_alt"]
            self.color = COLORS["text_dim"]
            self.border_color = COLORS["border"]
            self._bg_color_instr.rgba = COLORS["panel_alt"]
            self._border_color_instr.rgba = COLORS["border"]

    def set_label(self, text: str) -> None:
        self.text = text


class EventCard(ButtonBehavior, BoxLayout):
    ROW_H = dp(108)

    def __init__(self, alert: Alert, on_open, **kwargs) -> None:
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=self.ROW_H,
            spacing=0,
            **kwargs,
        )
        self.alert = alert
        self._on_open = on_open
        sev_col = severity_color(alert.severity)

        with self.canvas.before:
            self._bg_color = Color(*COLORS["panel"])
            self._bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[(RADIUS, RADIUS)] * 4,
            )
            self._border_color = Color(*COLORS["border"])
            self._border = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, RADIUS
                ),
                width=1.0,
            )
        self.bind(pos=self._sync, size=self._sync)

        stripe = Widget(size_hint_x=None, width=dp(5))
        with stripe.canvas.before:
            Color(*sev_col)
            self._stripe = RoundedRectangle(
                pos=stripe.pos,
                size=stripe.size,
                radius=[(dp(2), dp(2))] * 4,
            )
        stripe.bind(
            pos=lambda w, _v, r=self._stripe: setattr(
                r, "pos", (w.x + dp(6), w.y + dp(10))
            ),
            size=lambda w, _v, r=self._stripe: setattr(
                r, "size", (w.width - dp(12), w.height - dp(20))
            ),
        )
        self.add_widget(stripe)

        body = BoxLayout(
            orientation="vertical",
            padding=[dp(12), dp(10), dp(12), dp(10)],
            spacing=dp(5),
        )
        row1 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(22),
            spacing=dp(8),
        )
        row1.add_widget(TagPill(alert.severity, color=sev_col))
        title = Label(
            text=alert.name,
            color=COLORS["text"],
            font_size=FS_MD,
            bold=True,
            halign="left",
            valign="middle",
        )
        title.bind(size=lambda w, _v: setattr(w, "text_size", w.size))
        row1.add_widget(title)
        when = Label(
            text=alert.pretty_time(),
            color=COLORS["text_muted"],
            font_size=FS_XS,
            font_name=FONT_MONO,
            size_hint_x=None,
            width=dp(140),
            halign="right",
        )
        when.bind(size=lambda w, _v: setattr(w, "text_size", w.size))
        row1.add_widget(when)
        body.add_widget(row1)

        meta = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(22),
            spacing=dp(6),
        )
        for txt, col in (
            (f"HOST: {alert.host}", COLORS["accent"]),
            (f"USER: {alert.user}", COLORS["purple"]),
            (f"CODE: {alert.event_code or '?'}", COLORS["text_dim"]),
        ):
            meta.add_widget(TagPill(txt, color=col, bg_alpha=0.14))
        meta.add_widget(Widget())
        body.add_widget(meta)

        cmd = Label(
            text=alert.short_command(120) or "(no command line)",
            color=COLORS["text_dim"],
            font_size=FS_SM,
            font_name=FONT_MONO,
            halign="left",
            valign="middle",
            shorten=True,
            shorten_from="right",
        )
        cmd.bind(size=lambda w, _v: setattr(w, "text_size", w.size))
        body.add_widget(cmd)
        self.add_widget(body)

    def _sync(self, *_args) -> None:
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rounded_rectangle = (
            self.x, self.y, self.width, self.height, RADIUS
        )

    def on_release(self) -> None:
        if self._on_open:
            self._on_open(self.alert)


class AlertLogScreen(Screen):
    FILTER_ALL = "ALL"
    FILTER_CRITICAL = "CRITICAL"
    FILTER_WARNING = "WARNING"
    FILTER_INFO = "INFO"

    def __init__(self, app, **kwargs) -> None:
        super().__init__(name="alerts", **kwargs)
        self.app = app
        self._filter = self.FILTER_ALL
        self._search = ""

        outer = BoxLayout(orientation="vertical", size_hint_y=1)

        top = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[SPACE_LG, SPACE_LG, SPACE_MD, SPACE_MD],
            spacing=SPACE_MD,
        )
        top.bind(minimum_height=top.setter("height"))

        header_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(24),
        )
        header_row.add_widget(SectionHeader("01", "Events"))
        header_row.add_widget(Widget())
        self.count_label = Label(
            text="0",
            color=COLORS["text_muted"],
            font_size=FS_XS,
            bold=True,
            font_name=FONT_MONO,
            size_hint_x=None,
            width=dp(100),
            halign="right",
        )
        self.count_label.bind(
            size=lambda w, _v: setattr(w, "text_size", w.size)
        )
        header_row.add_widget(self.count_label)
        top.add_widget(header_row)

        self.search_input = DarkInput(
            hint_text="Search events (host, user, command)...",
            size_hint_y=None,
            height=dp(42),
        )
        self.search_input._input.bind(text=self._on_search_change)
        top.add_widget(self.search_input)

        chips_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(34),
            spacing=dp(6),
        )
        self._chips: dict[str, FilterChip] = {}
        for key, label in (
            (self.FILTER_ALL, "All"),
            (self.FILTER_CRITICAL, "Critical"),
            (self.FILTER_WARNING, "Warning"),
            (self.FILTER_INFO, "Info"),
        ):
            chip = FilterChip(key, text=label)
            chip.bind(on_release=lambda _b, k=key: self._set_filter(k))
            chips_row.add_widget(chip)
            self._chips[key] = chip
        chips_row.add_widget(Widget())
        top.add_widget(chips_row)

        actions = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(38),
            spacing=dp(8),
        )
        refresh_btn = SecondaryButton(
            text="REFRESH",
            size_hint_x=None,
            width=dp(100),
            height=dp(34),
            font_size=FS_XS,
        )
        refresh_btn.bind(on_release=lambda *_: self.app.trigger_manual_refresh())
        export_btn = SecondaryButton(
            text="EXPORT",
            size_hint_x=None,
            width=dp(100),
            height=dp(34),
            font_size=FS_XS,
        )
        export_btn.bind(on_release=self._on_export)
        actions.add_widget(refresh_btn)
        actions.add_widget(export_btn)
        actions.add_widget(Widget())
        top.add_widget(actions)

        outer.add_widget(top)

        self.scroll = ScrollView(
            size_hint_y=1,
            bar_width=dp(4),
            bar_color=(*COLORS["accent"][:3], 0.55),
            bar_inactive_color=(*COLORS["panel_alt"][:3], 0.4),
            do_scroll_x=False,
        )
        self.feed = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(10),
            padding=[SPACE_LG, 0, SPACE_LG, SPACE_LG],
        )
        self.feed.bind(minimum_height=self.feed.setter("height"))
        self.scroll.add_widget(self.feed)

        self.empty_label = make_label(
            "No events yet.\nRun a detection on Dashboard → REFRESH NOW.",
            color=COLORS["text_muted"],
            halign="center",
            font_size=FS_MD,
            size_hint_y=None,
            height=dp(120),
        )

        outer.add_widget(self.scroll)
        self.add_widget(outer)

        self._set_filter(self.FILTER_ALL, refresh=False)
        self.app.alerts.subscribe(self.refresh_list)
        Clock.schedule_once(lambda _dt: self.refresh_list(), 0)

    def on_enter(self, *_args) -> None:
        self.refresh_list()

    def _set_filter(self, key: str, refresh: bool = True) -> None:
        self._filter = key
        for k, chip in self._chips.items():
            chip.set_active(k == key)
        if refresh:
            self.refresh_list()

    def _on_search_change(self, _instance, text: str) -> None:
        self._search = (text or "").strip().lower()
        self.refresh_list()

    def _severity_counts(self) -> dict[str, int]:
        counts = {
            self.FILTER_ALL: 0,
            self.FILTER_CRITICAL: 0,
            self.FILTER_WARNING: 0,
            self.FILTER_INFO: 0,
        }
        for a in self.app.alerts.alerts:
            counts[self.FILTER_ALL] += 1
            if a.severity == Alert.SEVERITY_CRITICAL:
                counts[self.FILTER_CRITICAL] += 1
            elif a.severity == Alert.SEVERITY_WARNING:
                counts[self.FILTER_WARNING] += 1
            else:
                counts[self.FILTER_INFO] += 1
        return counts

    def _update_chip_labels(self) -> None:
        c = self._severity_counts()
        labels = {
            self.FILTER_ALL: "All",
            self.FILTER_CRITICAL: "Critical",
            self.FILTER_WARNING: "Warning",
            self.FILTER_INFO: "Info",
        }
        for key, chip in self._chips.items():
            n = c.get(key, 0)
            chip.set_label(f"{labels[key]} ({n})")

    def _passes_filter(self, alert: Alert) -> bool:
        if self._filter != self.FILTER_ALL and alert.severity != self._filter:
            return False
        if not self._search:
            return True
        hay = " ".join([
            alert.name,
            alert.host,
            alert.user,
            alert.command_line,
            alert.parent_command_line,
            alert.image,
            alert.event_code,
        ]).lower()
        return self._search in hay

    def refresh_list(self, *_args) -> None:
        self._update_chip_labels()
        filtered: list[Alert] = [
            a for a in self.app.alerts.alerts if self._passes_filter(a)
        ]
        total = len(self.app.alerts.alerts)
        shown = len(filtered)
        if shown == total:
            self.count_label.text = f"{total} events"
        else:
            self.count_label.text = f"{shown} / {total}"

        self.feed.clear_widgets()
        if not filtered:
            self.feed.add_widget(self.empty_label)
            return

        for alert in filtered:
            card = EventCard(alert, on_open=self._show_details_modal)
            self.feed.add_widget(card)

    def open_details(self, index: int) -> None:

        alerts = list(self.app.alerts.alerts)
        if 0 <= index < len(alerts):
            self._show_details_modal(alerts[index])

    def _on_export(self, *_args) -> None:
        alerts = list(self.app.alerts.alerts)
        if not alerts:
            self.app._show_toast("Nothing to export", color=COLORS["text_muted"])
            return
        export_dir = CONFIG_DIR / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = export_dir / f"alerts_{stamp}.json"
        payload = [
            {
                "time": a.pretty_time(),
                "severity": a.severity,
                "name": a.name,
                "host": a.host,
                "user": a.user,
                "event_code": a.event_code,
                "command_line": a.command_line,
                "image": a.image,
                "raw": a.raw,
            }
            for a in alerts
        ]
        try:
            path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self.app._show_toast(
                f"Exported {len(alerts)} events",
                color=COLORS["ok"],
            )
        except OSError as exc:
            self.app._show_toast(f"Export failed: {exc}", color=COLORS["crit"])

    def _show_details_modal(self, alert: Alert) -> None:
        modal = ModalView(
            size_hint=(0.94, 0.88),
            background_color=(0, 0, 0, 0),
            overlay_color=(0, 0, 0, 0.78),
        )

        cmd_body = alert.display_command()
        if alert.parent_command_line and alert.parent_command_line != cmd_body:
            cmd_body = f"{cmd_body}\n\nParent: {alert.parent_command_line}"

        outer = Card(
            orientation="vertical",
            padding=[dp(16), dp(14), dp(16), dp(14)],
            spacing=dp(10),
            size_hint=(1, 1),
        )

        header_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(36),
            spacing=dp(10),
        )
        sev_pill = TagPill(alert.severity, color=severity_color(alert.severity))
        title_label = Label(
            text=alert.name,
            color=COLORS["text"],
            font_size=FS_LG,
            bold=True,
            halign="left",
            valign="middle",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(36),
        )
        title_label.bind(
            width=lambda w, v: setattr(w, "text_size", (max(v, dp(80)), None))
        )
        close_btn = SecondaryButton(
            text="CLOSE",
            size_hint=(None, None),
            width=dp(96),
            height=dp(34),
        )
        close_btn.bind(on_release=lambda *_: modal.dismiss())
        header_row.add_widget(sev_pill)
        header_row.add_widget(title_label)
        header_row.add_widget(close_btn)
        outer.add_widget(header_row)

        pills_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(28),
            spacing=dp(6),
        )
        for cap, val, col in (
            ("HOST", alert.host, COLORS["accent"]),
            ("USER", alert.user, COLORS["purple"]),
            ("CODE", alert.event_code or "?", COLORS["text_dim"]),
        ):
            pills_row.add_widget(TagPill(f"{cap}: {val}", color=col))
        pills_row.add_widget(Widget())
        outer.add_widget(pills_row)

        meta = MonoLogLabel(
            text=(
                f"Time:   {alert.pretty_time()}\n"
                f"Image:  {alert.image or '(unknown)'}"
            ),
            font_name=FONT_REGULAR,
            font_size=FS_SM,
            color=COLORS["text_dim"],
            max_height=dp(80),
        )
        outer.add_widget(meta)

        scroll = ScrollView(
            size_hint_y=1,
            bar_width=dp(4),
            bar_color=(*COLORS["accent"][:3], 0.5),
            do_scroll_x=False,
        )
        body = BoxLayout(
            orientation="vertical",
            size_hint_x=1,
            size_hint_y=None,
            spacing=dp(10),
        )

        body.add_widget(SectionHeader("A", "Command line"))
        cmd_card = log_text_card(
            cmd_body,
            font_size=FS_SM,
            color=COLORS["warn"],
            max_height=dp(200),
        )
        body.add_widget(cmd_card)

        ack_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(8),
        )
        copy_btn = SecondaryButton(
            text="COPY CMD",
            size_hint_x=None,
            width=dp(110),
            height=dp(36),
            font_size=FS_XS,
        )
        copy_btn.bind(
            on_release=lambda *_: self._copy_to_clipboard(cmd_body, modal)
        )
        ack_btn = PrimaryButton(
            text="DISMISS",
            size_hint_x=None,
            width=dp(110),
            height=dp(36),
            font_size=FS_XS,
        )
        ack_btn.bind(on_release=lambda *_: modal.dismiss())
        ack_row.add_widget(copy_btn)
        ack_row.add_widget(ack_btn)
        ack_row.add_widget(Widget())
        body.add_widget(ack_row)

        body.add_widget(SectionHeader("B", "Raw event (JSON)"))
        json_text = json.dumps(alert.raw, indent=2, ensure_ascii=False)
        json_card = log_text_card(json_text, max_height=dp(4000))
        body.add_widget(json_card)

        def _sync_scroll_height(*_args) -> None:
            body.height = (
                sum(c.height for c in body.children)
                + dp(10) * max(0, len(body.children) - 1)
            )

        for child in (cmd_card, json_card):
            child.bind(height=_sync_scroll_height)
        Clock.schedule_once(lambda _dt: _sync_scroll_height(), 0)

        scroll.add_widget(body)
        outer.add_widget(scroll)

        modal.add_widget(outer)
        modal.open()

    def _copy_to_clipboard(self, text: str, modal: ModalView) -> None:
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(text)
            self.app._show_toast("Copied", color=COLORS["ok"])
        except Exception:
            self.app._show_toast("Clipboard unavailable", color=COLORS["warn"])
        modal.dismiss()
