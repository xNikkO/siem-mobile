from __future__ import annotations

import os
import threading
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config as KivyConfig
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, NoTransition


KivyConfig.set("graphics", "width", "440")
KivyConfig.set("graphics", "height", "820")
KivyConfig.set("graphics", "resizable", "1")
KivyConfig.set("input", "mouse", "mouse,disable_multitouch")

from app.alert_manager import AlertManager
from app.config import Config
from app.screens.alert_log import AlertLogScreen
from app.screens.dashboard import DashboardScreen
from app.screens.settings import SettingsScreen
from app.splunk_client import SplunkClient


def _create_splunk_client(cfg: Config):
    if os.environ.get("SIEM_DEMO_MODE") == "1":
        from app.demo_mode import DemoSplunkClient

        return DemoSplunkClient(cfg)
    return SplunkClient(cfg)
from app.theme import (
    COLORS,
    FONT_MONO,
    FS_SM,
    FS_XS,
    RADIUS_SM,
)
from app.ui_components import AppLogo, TagPill


try:
    from plyer import notification as _plyer_notification

    def _system_notify(title: str, message: str) -> None:
        try:
            _plyer_notification.notify(
                title=title,
                message=message,
                app_name="SIEM Mobile",
                timeout=4,
            )
        except Exception as exc:
            print(f"[notify] plyer failed: {exc}")
except Exception:
    def _system_notify(title: str, message: str) -> None:
        pass


class Toast(BoxLayout):


    def __init__(self, message: str, color=None, **kwargs) -> None:
        super().__init__(
            orientation="horizontal",
            padding=[dp(16), dp(10), dp(16), dp(10)],
            size_hint=(None, None),
            **kwargs,
        )
        fill = color or COLORS["panel_alt"]
        stripe = color or COLORS["accent"]

        with self.canvas.before:
            self._bg_color = Color(*fill)
            self._bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[(RADIUS_SM, RADIUS_SM)] * 4,
            )
            self._border_color = Color(*stripe)
            self._border = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, RADIUS_SM
                ),
                width=1.2,
            )
        self.bind(pos=self._sync, size=self._sync)


        self.label = Label(
            text=message,
            color=COLORS["text"],
            font_size=FS_SM,
            bold=True,
        )
        self.label.texture_update()
        tx, ty = self.label.texture_size or (dp(80), dp(20))
        self.size = (tx + dp(36), ty + dp(20))
        self.add_widget(self.label)

    def _sync(self, *_args) -> None:
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rounded_rectangle = (
            self.x, self.y, self.width, self.height, RADIUS_SM
        )


class NavButton(BoxLayout):


    def __init__(self, caption: str, on_press_cb, **kwargs) -> None:
        super().__init__(
            orientation="vertical",
            padding=[dp(6), dp(4), dp(6), dp(4)],
            **kwargs,
        )
        self._on_press_cb = on_press_cb
        self._active = False

        with self.canvas.before:
            self._bg_color = Color(*COLORS["transparent"])
            self._bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[(dp(10), dp(10))] * 4,
            )
            self._top_indicator_color = Color(*COLORS["transparent"])
            self._top_indicator = RoundedRectangle(
                pos=self.pos,
                size=(0, 0),
                radius=[(dp(2), dp(2))] * 4,
            )
        self.bind(pos=self._sync, size=self._sync)

        self.caption_label = Label(
            text=caption,
            font_size=FS_XS,
            color=COLORS["text_dim"],
            bold=True,
            halign="center",
            valign="middle",
        )
        self.caption_label.bind(
            size=lambda w, _v: setattr(w, "text_size", w.size)
        )
        self.add_widget(self.caption_label)

    def _sync(self, *_args) -> None:
        self._bg.pos = self.pos
        self._bg.size = self.size
        bw = dp(28)
        bh = dp(3)
        self._top_indicator.size = (bw, bh)
        self._top_indicator.pos = (
            self.center_x - bw / 2,
            self.top - bh,
        )

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self._bg_color.rgba = COLORS["accent_soft"]
            self._top_indicator_color.rgba = COLORS["accent"]
            self.caption_label.color = COLORS["accent"]
        else:
            self._bg_color.rgba = COLORS["transparent"]
            self._top_indicator_color.rgba = COLORS["transparent"]
            self.caption_label.color = COLORS["text_dim"]

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and self._on_press_cb:
            self._on_press_cb()
            return True
        return super().on_touch_up(touch)


class BottomNav(BoxLayout):
    NAV_ITEMS = (
        ("dashboard", "DASHBOARD"),
        ("alerts",    "EVENTS"),
        ("settings",  "SETTINGS"),
    )

    def __init__(self, on_select, **kwargs) -> None:
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(10), dp(8), dp(10), dp(8)],
            spacing=dp(6),
            **kwargs,
        )
        with self.canvas.before:
            self._bg_color = Color(*COLORS["panel"])
            self._bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[(0, 0)] * 4
            )
            self._top_border_color = Color(*COLORS["border"])
            self._top_border = Line(points=[0, 0, 0, 0], width=1.0)
        self.bind(pos=self._sync, size=self._sync)

        self.buttons = {}
        for screen_name, caption in self.NAV_ITEMS:
            btn = NavButton(
                caption=caption,
                on_press_cb=lambda n=screen_name: on_select(n),
            )
            self.add_widget(btn)
            self.buttons[screen_name] = btn

    def _sync(self, *_args) -> None:
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._top_border.points = [
            self.x, self.top, self.right, self.top,
        ]

    def set_active(self, screen_name: str) -> None:
        for name, btn in self.buttons.items():
            btn.set_active(name == screen_name)


class TopHeader(BoxLayout):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(72),
            padding=[dp(22), dp(4), dp(14), dp(4)],
            spacing=dp(10),
            **kwargs,
        )
        with self.canvas.before:
            self._bg_color = Color(*COLORS["panel"])
            self._bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[(0, 0)] * 4
            )
            self._border_color = Color(*COLORS["border"])
            self._border = Line(points=[0, 0, 0, 0], width=1.0)
        self.bind(pos=self._sync, size=self._sync)

        self.logo = AppLogo()
        self.logo.pos_hint = {"center_y": 0.5}
        self.add_widget(self.logo)

        from kivy.uix.widget import Widget as _W
        self.add_widget(_W())

        self.conn_badge = TagPill(
            "IDLE",
            color=COLORS["text_muted"],
            bg_alpha=0.2,
        )
        self.conn_badge.pos_hint = {"center_y": 0.5}
        self.add_widget(self.conn_badge)

        self.clock_label = Label(
            text="",
            color=COLORS["text_dim"],
            font_size=FS_XS,
            halign="right",
            valign="middle",
            font_name=FONT_MONO,
            size_hint_x=None,
            width=dp(150),
            pos_hint={"center_y": 0.5},
        )
        self.clock_label.bind(
            size=lambda w, _v: setattr(w, "text_size", w.size)
        )
        self.add_widget(self.clock_label)

        Clock.schedule_interval(self._update_clock, 1)
        self._update_clock(0)

    def _sync(self, *_args) -> None:
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.points = [self.x, self.y, self.right, self.y]

    def _update_clock(self, _dt) -> None:
        self.clock_label.text = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")


class SiemApp(App):
    title = "SIEM Mobile"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


        self.demo_mode = os.environ.get("SIEM_DEMO_MODE") == "1"
        self.cfg: Config = Config()
        if self.demo_mode:
            self.cfg.set("demo_mode", True)
            self.cfg.set("auto_monitor", True)
            self.cfg.set("poll_interval", 10)
        self.alerts: AlertManager = AlertManager()
        self.splunk = _create_splunk_client(self.cfg)

        self.dashboard_screen: DashboardScreen | None = None
        self.alerts_screen: AlertLogScreen | None = None
        self.settings_screen: SettingsScreen | None = None

        self._toast = None


    def build(self):
        Window.clearcolor = COLORS["bg"]

        root = BoxLayout(orientation="vertical")

        self.header = TopHeader()
        root.add_widget(self.header)

        self.sm = ScreenManager(transition=NoTransition(), size_hint_y=1)
        self.dashboard_screen = DashboardScreen(self)
        self.alerts_screen = AlertLogScreen(self)
        self.settings_screen = SettingsScreen(self)
        self.sm.add_widget(self.dashboard_screen)
        self.sm.add_widget(self.alerts_screen)
        self.sm.add_widget(self.settings_screen)
        root.add_widget(self.sm)

        self.bottom_nav = BottomNav(on_select=self._switch_screen)
        root.add_widget(self.bottom_nav)
        self.bottom_nav.set_active("dashboard")

        if self.demo_mode:
            self._set_header_conn("ok", "DEMO")
            self.header.logo.set_subtitle(
                "DEMO MODE", color=COLORS["warn"]
            )
            Clock.schedule_once(
                lambda _dt: self._show_toast(
                    "Demo mode - synthetic events (no Splunk)",
                    color=COLORS["warn"],
                ),
                0.8,
            )

        if self.cfg.get("auto_monitor"):
            Clock.schedule_once(lambda _dt: self.start_monitoring(), 0.5)

        if not self.demo_mode:
            Clock.schedule_interval(self._auto_monitor_watchdog, 10)

        return root

    def _auto_monitor_watchdog(self, _dt) -> None:

        if not self.cfg.get("auto_monitor"):
            return
        interval = max(5, int(self.cfg.get("poll_interval") or 30))
        stale_after = interval + 45
        if self.splunk.is_running() and not self.splunk.poll_is_stale(stale_after):
            return
        self.splunk.stop_polling()
        self.start_monitoring()

    def on_stop(self):
        self.splunk.stop_polling()


    def _switch_screen(self, screen_name: str) -> None:
        if screen_name not in self.sm.screen_names:
            return
        self.sm.current = screen_name
        self.bottom_nav.set_active(screen_name)


    def run_in_thread(self, fn) -> None:
        threading.Thread(target=fn, daemon=True).start()

    def trigger_manual_refresh(self) -> None:
        def _go():
            self.splunk.query_once(
                on_event=self._handle_event_threadsafe,
                on_status=self._handle_status_threadsafe,
            )
        self.run_in_thread(_go)
        self._show_toast("Refreshing...", color=COLORS["accent"])

    def start_monitoring(self) -> None:
        self._set_header_conn("polling", "POLLING")
        self.splunk.start_polling(
            on_event=self._handle_event_threadsafe,
            on_status=self._handle_status_threadsafe,
        )
        self._show_toast("Auto-monitor ON", color=COLORS["ok"])

    def stop_monitoring(self) -> None:
        self.splunk.stop_polling()
        self._set_header_conn("idle", "IDLE")
        self._show_toast("Auto-monitor OFF", color=COLORS["text_muted"])


    def _handle_event_threadsafe(self, result: dict) -> None:
        Clock.schedule_once(lambda _dt, r=result: self._on_event_ui(r), 0)

    def _handle_status_threadsafe(self, ok: bool, message: str) -> None:
        Clock.schedule_once(
            lambda _dt, o=ok, m=message: self._on_poll_status(o, m), 0
        )

    def _on_poll_status(self, ok: bool, message: str) -> None:
        if ok and "from Splunk)" in message:
            shown = self.alerts.total()
            message = f"{message} | {shown} on dashboard"
        self.alerts.set_poll_status(ok, message)
        self.set_connection_status(ok, message)
        if self.splunk.is_running():
            self._set_header_conn("polling", "POLLING")
        elif ok:
            self._set_header_conn("ok", "ONLINE")
        else:
            self._set_header_conn("error", "OFFLINE")

    def _set_header_conn(self, state: str, label: str) -> None:
        if not hasattr(self, "header"):
            return
        self.header.conn_badge.text = label
        color = {
            "ok": COLORS["ok"],
            "error": COLORS["crit"],
            "polling": COLORS["accent"],
        }.get(state, COLORS["text_muted"])
        self.header.conn_badge.set_color(color, bg_alpha=0.22)
        self.header.conn_badge.texture_update()
        self.header.conn_badge._on_texture_size()

    def _on_event_ui(self, result: dict) -> None:
        alert = self.alerts.add(result)
        if alert is None:
            return

        notify_crit = bool(self.cfg.get("notify_critical"))
        notify_warn = bool(self.cfg.get("notify_warning"))
        should_notify = (
            (alert.severity == "CRITICAL" and notify_crit)
            or (alert.severity == "WARNING" and notify_warn)
        )
        if should_notify:
            color = (
                COLORS["crit"] if alert.severity == "CRITICAL"
                else COLORS["warn"]
            )
            self._show_toast(
                f"[{alert.severity}] {alert.name} @ {alert.host}",
                color=color,
            )
            _system_notify(
                f"[SIEM] {alert.severity}: {alert.name}",
                f"{alert.host} / {alert.user}\n{alert.short_command(120)}",
            )


    def set_connection_status(self, ok: bool, message: str) -> None:
        if self.splunk.is_running() and ok:
            self._set_header_conn("polling", "POLLING")
        elif ok:
            self._set_header_conn("ok", "ONLINE")
        else:
            self._set_header_conn("error", "OFFLINE")
        if self.dashboard_screen is not None:
            self.dashboard_screen.set_connection_status(ok, message)


    def _show_toast(self, message: str, color=None) -> None:
        if self._toast is not None:
            try:
                Window.remove_widget(self._toast)
            except Exception:
                pass
            self._toast = None

        toast = Toast(message, color=color)
        toast.pos = (
            (Window.width - toast.width) / 2,
            dp(82),
        )
        Window.add_widget(toast)
        self._toast = toast

        def _dismiss(_dt):
            if self._toast is toast:
                try:
                    Window.remove_widget(toast)
                except Exception:
                    pass
                self._toast = None
        Clock.schedule_once(_dismiss, 3.0)


if __name__ == "__main__":
    SiemApp().run()
