"""Alert system - configurable threshold notifications for system resources."""

import tkinter as tk
from tkinter import ttk
import psutil
import time
import subprocess
import platform

from system_monitor.widgets import COLORS, InfoRow, SectionHeader


class AlertRule:
    """A single alert rule with metric, threshold, and cooldown."""

    def __init__(self, name, metric, threshold, direction="above", cooldown=30, enabled=True):
        self.name = name
        self.metric = metric  # "cpu", "ram", "disk", "swap"
        self.threshold = threshold  # percentage
        self.direction = direction  # "above" or "below"
        self.cooldown = cooldown  # seconds between repeated alerts
        self.enabled = enabled
        self._last_triggered = 0
        self._triggered = False

    def check(self, value):
        """Check if value triggers the alert. Returns True if newly triggered."""
        if not self.enabled:
            return False

        now = time.time()
        if self.direction == "above":
            is_triggered = value >= self.threshold
        else:
            is_triggered = value <= self.threshold

        if is_triggered and not self._triggered:
            if now - self._last_triggered >= self.cooldown:
                self._triggered = True
                self._last_triggered = now
                return True
        elif not is_triggered:
            self._triggered = False

        return False


class AlertManager:
    """Manages alert rules and triggers notifications."""

    def __init__(self):
        self.rules = [
            AlertRule("CPU High", "cpu", 90, "above", cooldown=30),
            AlertRule("RAM High", "ram", 90, "above", cooldown=30),
            AlertRule("Disk Critical", "disk", 95, "above", cooldown=60),
            AlertRule("Swap High", "swap", 80, "above", cooldown=60),
        ]
        self._alert_log = []
        self._notification_callback = None
        self._system = platform.system()

    def set_notification_callback(self, callback):
        """Set a callback for when alerts fire: callback(alert_name, metric, value, threshold)."""
        self._notification_callback = callback

    def check_all(self, cpu_pct, ram_pct, disk_pct, swap_pct):
        """Check all rules against current values. Returns list of triggered alerts."""
        values = {
            "cpu": cpu_pct,
            "ram": ram_pct,
            "disk": disk_pct,
            "swap": swap_pct,
        }

        triggered = []
        for rule in self.rules:
            val = values.get(rule.metric, 0)
            if rule.check(val):
                triggered.append((rule, val))
                self._alert_log.append({
                    "time": time.strftime("%H:%M:%S"),
                    "name": rule.name,
                    "metric": rule.metric,
                    "value": val,
                    "threshold": rule.threshold,
                })
                # Keep log bounded
                if len(self._alert_log) > 100:
                    self._alert_log = self._alert_log[-100:]

                if self._notification_callback:
                    self._notification_callback(rule.name, rule.metric, val, rule.threshold)

                self._desktop_notify(rule.name, rule.metric, val, rule.threshold)

        return triggered

    def _desktop_notify(self, name, metric, value, threshold):
        """Send a desktop notification if possible."""
        title = f"System Monitor Alert: {name}"
        body = f"{metric.upper()} at {value:.1f}% (threshold: {threshold}%)"

        try:
            if self._system == "Linux":
                subprocess.Popen(
                    ["notify-send", "-u", "critical", title, body],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif self._system == "Darwin":
                subprocess.Popen(
                    ["osascript", "-e",
                     f'display notification "{body}" with title "{title}"'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass

    @property
    def alert_log(self):
        return list(self._alert_log)


class AlertConfigDialog(tk.Toplevel):
    """Dialog to configure alert thresholds."""

    def __init__(self, parent, alert_manager):
        super().__init__(parent)
        self.title("Alert Configuration")
        self.geometry("500x450")
        self.configure(bg=COLORS["bg_dark"])
        self.transient(parent)

        self._manager = alert_manager
        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self, bg=COLORS["bg_medium"], padx=10, pady=8)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Alert Thresholds",
            fg=COLORS["accent_blue"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 13, "bold"),
        ).pack(side="left")

        tk.Button(
            header,
            text="Close",
            command=self.destroy,
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
            font=("Helvetica", 9),
            relief="flat",
            padx=10,
        ).pack(side="right")

        # Rules editor
        container = tk.Frame(self, bg=COLORS["bg_dark"], padx=15, pady=10)
        container.pack(fill="both", expand=True)

        self._rule_widgets = []

        for rule in self._manager.rules:
            frame = tk.Frame(container, bg=COLORS["bg_medium"], padx=10, pady=8)
            frame.pack(fill="x", pady=4)

            # Enable checkbox
            enabled_var = tk.BooleanVar(value=rule.enabled)
            chk = tk.Checkbutton(
                frame,
                variable=enabled_var,
                bg=COLORS["bg_medium"],
                activebackground=COLORS["bg_medium"],
                command=lambda r=rule, v=enabled_var: setattr(r, "enabled", v.get()),
            )
            chk.pack(side="left")

            # Name
            tk.Label(
                frame,
                text=rule.name,
                fg=COLORS["text_primary"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 10, "bold"),
                width=15,
                anchor="w",
            ).pack(side="left", padx=(5, 10))

            # Threshold slider
            tk.Label(
                frame,
                text="Threshold:",
                fg=COLORS["text_secondary"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 9),
            ).pack(side="left")

            threshold_var = tk.IntVar(value=int(rule.threshold))
            threshold_label = tk.Label(
                frame,
                text=f"{int(rule.threshold)}%",
                fg=COLORS["accent_yellow"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 9, "bold"),
                width=5,
            )

            def make_updater(r, v, lbl):
                def update(val):
                    r.threshold = int(float(val))
                    lbl.config(text=f"{r.threshold}%")
                return update

            slider = tk.Scale(
                frame,
                from_=10,
                to=99,
                orient="horizontal",
                variable=threshold_var,
                command=make_updater(rule, threshold_var, threshold_label),
                bg=COLORS["bg_medium"],
                fg=COLORS["text_dim"],
                troughcolor=COLORS["bg_dark"],
                highlightthickness=0,
                font=("Helvetica", 7),
                showvalue=False,
                sliderlength=12,
                width=8,
                length=120,
            )
            slider.pack(side="left", padx=5)
            threshold_label.pack(side="left")

            # Cooldown
            tk.Label(
                frame,
                text="  CD:",
                fg=COLORS["text_secondary"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 8),
            ).pack(side="left")

            tk.Label(
                frame,
                text=f"{rule.cooldown}s",
                fg=COLORS["text_dim"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 8),
            ).pack(side="left")

        # Alert log
        log_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        log_frame.pack(fill="both", expand=True, pady=(10, 0))

        SectionHeader(log_frame, text="Alert Log").pack(fill="x", pady=(0, 5))

        log_text = tk.Text(
            log_frame,
            bg=COLORS["bg_dark"],
            fg=COLORS["text_primary"],
            font=("Courier", 8),
            height=8,
            wrap="word",
            relief="flat",
        )
        log_text.pack(fill="both", expand=True)

        for entry in reversed(self._manager.alert_log):
            log_text.insert("end",
                            f"[{entry['time']}] {entry['name']}: "
                            f"{entry['metric'].upper()} = {entry['value']:.1f}% "
                            f"(threshold: {entry['threshold']}%)\n")

        if not self._manager.alert_log:
            log_text.insert("end", "  No alerts triggered yet.")

        log_text.config(state="disabled")
