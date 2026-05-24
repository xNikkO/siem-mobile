from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.uix.widget import Widget

from ..theme import (
    COLORS,
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
    DarkInput,
    PrimaryButton,
    SecondaryButton,
    SectionHeader,
    make_label,
)


def _form_field(caption: str, widget, helper: str = "") -> BoxLayout:

    box = BoxLayout(
        orientation="vertical",
        size_hint_y=None,
        spacing=dp(6),
    )

    cap = Label(
        text=caption.upper(),
        color=COLORS["text_muted"],
        font_size=FS_XS,
        bold=True,
        halign="left",
        valign="middle",
        size_hint_y=None,
        height=dp(16),
    )
    cap.bind(size=lambda w, _v: setattr(w, "text_size", w.size))
    box.add_widget(cap)

    widget.size_hint_y = None
    if not widget.height:
        widget.height = dp(44)
    box.add_widget(widget)

    total = cap.height + widget.height + dp(6)
    if helper:
        helper_lbl = make_label(
            helper,
            color=COLORS["text_muted"],
            font_size=FS_XS,
            size_hint_y=None,
            height=dp(16),
        )
        box.add_widget(helper_lbl)
        total += helper_lbl.height + dp(6)
    box.height = total
    return box


class SettingsScreen(Screen):
    def __init__(self, app, **kwargs) -> None:
        super().__init__(name="settings", **kwargs)
        self.app = app
        cfg = self.app.cfg

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


        root.add_widget(SectionHeader("01", "Connection"))
        conn_card = Card(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(18), dp(16), dp(18), dp(16)],
            spacing=dp(14),
        )
        conn_card.bind(minimum_height=conn_card.setter("height"))

        self.url_input = DarkInput(
            text=str(cfg.get("splunk_url")),
            hint_text="https://192.168.1.100:8089",
        )
        conn_card.add_widget(_form_field(
            "Splunk endpoint",
            self.url_input,
            helper="Splunkd REST port - usually 8089 (NOT the web 8000)",
        ))

        self.user_input = DarkInput(
            text=str(cfg.get("username") or ""),
            hint_text="Splunk Free: leave empty",
        )
        conn_card.add_widget(_form_field(
            "Username",
            self.user_input,
            helper="Splunk Free has no login - leave blank",
        ))

        self.pass_input = DarkInput(
            text=str(cfg.get("password") or ""),
            hint_text="Splunk Free: leave empty",
            password=True,
        )
        conn_card.add_widget(_form_field(
            "Password",
            self.pass_input,
            helper="Do not use admin here on Free license",
        ))

        root.add_widget(conn_card)


        root.add_widget(SectionHeader("02", "Polling"))
        poll_card = Card(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(18), dp(16), dp(18), dp(16)],
            spacing=dp(14),
        )
        poll_card.bind(minimum_height=poll_card.setter("height"))

        initial_interval = int(cfg.get("poll_interval") or 30)
        slider_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=dp(10),
        )
        self.interval_slider = Slider(
            min=5,
            max=300,
            value=initial_interval,
            step=5,
            cursor_size=(dp(22), dp(22)),
            value_track=True,
            value_track_color=COLORS["accent"],
            value_track_width=dp(3),
        )
        self.interval_value = Label(
            text=f"{initial_interval}s",
            color=COLORS["accent"],
            font_size=FS_LG,
            bold=True,
            size_hint_x=None,
            width=dp(60),
            halign="right",
            valign="middle",
        )
        self.interval_value.bind(
            size=lambda w, _v: setattr(w, "text_size", w.size)
        )
        self.interval_slider.bind(value=self._on_interval_change)
        slider_row.add_widget(self.interval_slider)
        slider_row.add_widget(self.interval_value)
        poll_card.add_widget(_form_field(
            "Poll interval (5 - 300 s)",
            slider_row,
        ))

        time_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=dp(10),
        )
        self.earliest_input = DarkInput(
            text=str(cfg.get("earliest_time")),
            hint_text="-15m",
        )
        self.latest_input = DarkInput(
            text=str(cfg.get("latest_time")),
            hint_text="now",
        )
        time_row.add_widget(self.earliest_input)
        time_row.add_widget(self.latest_input)
        poll_card.add_widget(_form_field(
            "Time window (earliest / latest)",
            time_row,
            helper="Splunk time modifiers - e.g. -1m, -15m, -1h, now",
        ))

        root.add_widget(poll_card)


        root.add_widget(SectionHeader("03", "Detection rules"))
        rules_card = Card(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(18), dp(16), dp(18), dp(16)],
            spacing=dp(14),
        )
        rules_card.bind(minimum_height=rules_card.setter("height"))

        self.spl_input = DarkInput(
            text=str(cfg.get("spl_query")),
            multiline=True,
            hint_text="search index=* sourcetype=*Sysmon* ...",
        )
        self.spl_input.height = dp(170)
        rules_card.add_widget(_form_field(
            "SPL query",
            self.spl_input,
            helper="Edit to tune Sysmon detections. Reset below for defaults.",
        ))

        self.reset_btn = SecondaryButton(
            text="RESET TO DEFAULT SPL",
            size_hint_y=None,
            height=dp(40),
            font_size=FS_SM,
        )
        self.reset_btn.bind(on_release=self._on_reset_spl)
        rules_card.add_widget(self.reset_btn)

        root.add_widget(rules_card)


        root.add_widget(SectionHeader("04", "Notifications"))
        notify_card = Card(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(18), dp(16), dp(18), dp(16)],
            spacing=dp(10),
        )
        notify_card.bind(minimum_height=notify_card.setter("height"))

        for key, title, helper in (
            ("notify_critical", "Critical alerts", "Toast + system notification"),
            ("notify_warning", "Warning alerts", "Toast + system notification"),
        ):
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(38),
                spacing=dp(10),
            )
            text_box = BoxLayout(orientation="vertical", spacing=dp(2))
            text_box.add_widget(make_label(
                title,
                color=COLORS["text"],
                font_size=FS_MD,
                bold=True,
            ))
            text_box.add_widget(make_label(
                helper,
                color=COLORS["text_muted"],
                font_size=FS_XS,
            ))
            sw = Switch(
                active=bool(cfg.get(key)),
                size_hint_x=None,
                width=dp(86),
            )
            sw.bind(active=lambda _s, val, k=key: self._on_notify_toggle(k, val))
            row.add_widget(text_box)
            row.add_widget(sw)
            notify_card.add_widget(row)

        root.add_widget(notify_card)


        root.add_widget(SectionHeader("05", "Actions"))

        actions_card = Card(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(18), dp(16), dp(18), dp(16)],
            spacing=dp(12),
        )
        actions_card.bind(minimum_height=actions_card.setter("height"))

        buttons_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(10),
        )
        self.save_btn = PrimaryButton(text="SAVE")
        self.save_btn.bind(on_release=self._on_save)
        self.test_btn = SecondaryButton(text="TEST CONNECTION")
        self.test_btn.bind(on_release=self._on_test)
        buttons_row.add_widget(self.save_btn)
        buttons_row.add_widget(self.test_btn)
        actions_card.add_widget(buttons_row)

        from kivy.uix.label import Label as _Label
        self.status_label = _Label(
            text="",
            color=COLORS["text_muted"],
            font_size=FS_SM,
            halign="left",
            valign="top",
            size_hint_y=None,
            height=dp(22),
        )
        self.status_label.bind(
            width=lambda w, _v: setattr(w, "text_size", (w.width, None)),
            texture_size=lambda w, _v: setattr(
                w, "height", max(dp(22), w.texture_size[1] + dp(4))
            ),
        )
        actions_card.add_widget(self.status_label)

        root.add_widget(actions_card)

        spacer = Widget(size_hint_y=None, height=dp(20))
        root.add_widget(spacer)

    def _on_interval_change(self, _slider, value: float) -> None:
        self.interval_value.text = f"{int(value)}s"

    def _on_notify_toggle(self, key: str, active: bool) -> None:
        self.app.cfg.set(key, bool(active))
        self.app.cfg.save()

    def _gather(self) -> dict:
        return {
            "splunk_url": self.url_input.text.strip(),
            "username": self.user_input.text.strip(),
            "password": self.pass_input.text,
            "poll_interval": int(self.interval_slider.value),
            "earliest_time": self.earliest_input.text.strip() or "-15m",
            "latest_time": self.latest_input.text.strip() or "now",
            "spl_query": self.spl_input.text.strip(),
        }

    def _on_save(self, *_args) -> None:
        cfg_data = self._gather()
        self.app.cfg.update(**cfg_data)
        self.app.cfg.save()
        self._set_status("Saved.", ok=True)
        if self.app.cfg.get("auto_monitor"):
            self.app.stop_monitoring()
            self.app.start_monitoring()

    def _on_test(self, *_args) -> None:
        self._on_save()
        self._set_status("Testing connection...", ok=None)
        self.app.run_in_thread(self._do_test)

    def _do_test(self) -> None:
        self.app.splunk.test_connection(self._on_test_result)

    def _on_test_result(self, ok: bool, message: str) -> None:
        from kivy.clock import Clock
        Clock.schedule_once(
            lambda _dt: self._set_status(message, ok=ok), 0
        )
        Clock.schedule_once(
            lambda _dt: self.app.set_connection_status(ok, message), 0
        )

    def _on_reset_spl(self, *_args) -> None:
        from ..config import DEFAULT_SPL
        self.spl_input.text = DEFAULT_SPL
        self._set_status("Default SPL restored. Don't forget to SAVE.", ok=None)

    def _set_status(self, message: str, ok) -> None:
        self.status_label.text = message
        if ok is True:
            self.status_label.color = COLORS["ok"]
        elif ok is False:
            self.status_label.color = COLORS["crit"]
        else:
            self.status_label.color = COLORS["text_muted"]
