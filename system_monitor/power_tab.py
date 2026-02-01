"""Power/Battery monitoring tab - battery status, charge history, thermal sensors."""

import tkinter as tk
from tkinter import ttk
import psutil
from datetime import timedelta

from system_monitor.widgets import (
    COLORS, ArcGauge, LineChart, InfoRow, SectionHeader, ScrollableFrame,
)


class PowerTab(tk.Frame):
    """Battery, power, and thermal sensor monitoring."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._build_ui()

    def _build_ui(self):
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        container = scroll.scrollable_frame

        # -- Battery Section --
        battery_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        battery_frame.pack(fill="x", padx=10, pady=10)

        SectionHeader(battery_frame, text="Battery").pack(fill="x", pady=(0, 5))

        top = tk.Frame(battery_frame, bg=COLORS["bg_dark"])
        top.pack(fill="x")

        self.battery_gauge = ArcGauge(top, size=180, thickness=16, label="Charge")
        self.battery_gauge.pack(side="left", padx=20)

        info = tk.Frame(top, bg=COLORS["bg_dark"])
        info.pack(side="left", fill="x", expand=True, padx=(20, 0))

        self.battery_info = {}
        for key, label in [
            ("percent", "Charge Level"),
            ("status", "Status"),
            ("plugged", "Power Source"),
            ("time_left", "Time Remaining"),
            ("power_profile", "Estimated Profile"),
        ]:
            row = InfoRow(info, label)
            row.pack(fill="x", pady=1)
            self.battery_info[key] = row

        # -- Battery History Chart --
        chart_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        chart_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(chart_frame, text="Battery Level History").pack(fill="x", pady=(0, 5))

        self.battery_chart = LineChart(
            chart_frame,
            width=750,
            height=150,
            max_points=60,
            y_min=0,
            y_max=100,
            y_label="%",
            series_colors=[COLORS["accent_green"]],
            series_labels=["Battery %"],
        )
        self.battery_chart.pack(fill="x")

        # -- Temperature Sensors --
        temp_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        temp_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(temp_frame, text="Temperature Sensors").pack(fill="x", pady=(0, 5))

        self.temp_container = tk.Frame(temp_frame, bg=COLORS["bg_dark"])
        self.temp_container.pack(fill="x")

        self.temp_widgets = []

        # -- Fan Speeds --
        fan_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        fan_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(fan_frame, text="Fan Speeds").pack(fill="x", pady=(0, 5))

        self.fan_container = tk.Frame(fan_frame, bg=COLORS["bg_dark"])
        self.fan_container.pack(fill="x")

        self.fan_widgets = []

        # -- Temperature History --
        temp_chart_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        temp_chart_frame.pack(fill="x", padx=10, pady=(5, 15))

        SectionHeader(temp_chart_frame, text="Temperature History").pack(fill="x", pady=(0, 5))

        self.temp_chart = LineChart(
            temp_chart_frame,
            width=750,
            height=150,
            max_points=60,
            y_min=20,
            y_max=100,
            y_label="C",
            series_colors=[COLORS["accent_orange"], COLORS["accent"]],
            series_labels=["Avg Temp", "Max Temp"],
        )
        self.temp_chart.pack(fill="x")

        # -- No battery message --
        self.no_battery_label = tk.Label(
            container,
            text="",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_dark"],
            font=("Helvetica", 11),
        )

    def update_data(self):
        """Refresh power and sensor data."""
        # Battery
        battery = psutil.sensors_battery()
        if battery:
            self.battery_gauge.set_value(battery.percent)
            self.battery_info["percent"].set_value(f"{battery.percent:.1f}%")

            if battery.power_plugged:
                self.battery_info["plugged"].set_value("AC Power (Plugged In)")
                if battery.percent >= 99:
                    self.battery_info["status"].set_value("Fully Charged")
                else:
                    self.battery_info["status"].set_value("Charging")
                self.battery_info["time_left"].set_value("N/A (Charging)")
            else:
                self.battery_info["plugged"].set_value("Battery")
                self.battery_info["status"].set_value("Discharging")
                if battery.secsleft > 0 and battery.secsleft != psutil.POWER_TIME_UNLIMITED:
                    remaining = timedelta(seconds=battery.secsleft)
                    hours = remaining.seconds // 3600
                    minutes = (remaining.seconds % 3600) // 60
                    self.battery_info["time_left"].set_value(f"{hours}h {minutes}m")
                else:
                    self.battery_info["time_left"].set_value("Calculating...")

            # Estimated profile
            if battery.percent > 80:
                self.battery_info["power_profile"].set_value("High Performance")
            elif battery.percent > 30:
                self.battery_info["power_profile"].set_value("Balanced")
            else:
                self.battery_info["power_profile"].set_value("Power Saver")

            self.battery_chart.add_point(battery.percent)
        else:
            self.battery_gauge.set_value(0)
            self.battery_info["percent"].set_value("N/A")
            self.battery_info["status"].set_value("No Battery Detected")
            self.battery_info["plugged"].set_value("AC Power (Desktop)")
            self.battery_info["time_left"].set_value("N/A")
            self.battery_info["power_profile"].set_value("Always On")
            self.no_battery_label.config(
                text="No battery detected - this system runs on AC power."
            )
            self.no_battery_label.pack(fill="x", padx=20, pady=5)

        # Temperature sensors
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Clear old widgets
                for w in self.temp_widgets:
                    w.destroy()
                self.temp_widgets.clear()

                all_temps = []
                for sensor_name, entries in temps.items():
                    for entry in entries:
                        label_text = f"{sensor_name}"
                        if entry.label:
                            label_text += f" - {entry.label}"
                        current = entry.current
                        high = entry.high or 0
                        critical = entry.critical or 0

                        all_temps.append(current)

                        if current > 0:
                            frame = tk.Frame(self.temp_container, bg=COLORS["bg_medium"], padx=10, pady=4)
                            frame.pack(fill="x", pady=1)

                            tk.Label(
                                frame,
                                text=label_text,
                                fg=COLORS["text_secondary"],
                                bg=COLORS["bg_medium"],
                                font=("Helvetica", 9),
                                width=30,
                                anchor="w",
                            ).pack(side="left")

                            color = COLORS["accent_green"]
                            if critical > 0 and current > critical * 0.9:
                                color = COLORS["accent"]
                            elif high > 0 and current > high * 0.9:
                                color = COLORS["accent_orange"]
                            elif current > 70:
                                color = COLORS["accent_yellow"]

                            temp_text = f"{current:.1f} C"
                            if high > 0:
                                temp_text += f"  (high: {high:.0f} C)"
                            if critical > 0:
                                temp_text += f"  (crit: {critical:.0f} C)"

                            tk.Label(
                                frame,
                                text=temp_text,
                                fg=color,
                                bg=COLORS["bg_medium"],
                                font=("Helvetica", 9, "bold"),
                            ).pack(side="left")

                            self.temp_widgets.append(frame)

                if all_temps:
                    avg_temp = sum(all_temps) / len(all_temps)
                    max_temp = max(all_temps)
                    self.temp_chart.add_points([avg_temp, max_temp])
            else:
                if not self.temp_widgets:
                    label = tk.Label(
                        self.temp_container,
                        text="No temperature sensors detected",
                        fg=COLORS["text_dim"],
                        bg=COLORS["bg_dark"],
                        font=("Helvetica", 10),
                    )
                    label.pack(anchor="w", pady=5)
                    self.temp_widgets.append(label)
        except Exception:
            pass

        # Fan speeds
        try:
            fans = psutil.sensors_fans()
            if fans:
                for w in self.fan_widgets:
                    w.destroy()
                self.fan_widgets.clear()

                for fan_name, entries in fans.items():
                    for entry in entries:
                        frame = tk.Frame(self.fan_container, bg=COLORS["bg_medium"], padx=10, pady=4)
                        frame.pack(fill="x", pady=1)

                        label_text = f"{fan_name}"
                        if entry.label:
                            label_text += f" - {entry.label}"

                        tk.Label(
                            frame,
                            text=label_text,
                            fg=COLORS["text_secondary"],
                            bg=COLORS["bg_medium"],
                            font=("Helvetica", 9),
                            width=30,
                            anchor="w",
                        ).pack(side="left")

                        tk.Label(
                            frame,
                            text=f"{entry.current} RPM",
                            fg=COLORS["accent_blue"],
                            bg=COLORS["bg_medium"],
                            font=("Helvetica", 9, "bold"),
                        ).pack(side="left")

                        self.fan_widgets.append(frame)
            else:
                if not self.fan_widgets:
                    label = tk.Label(
                        self.fan_container,
                        text="No fan sensors detected",
                        fg=COLORS["text_dim"],
                        bg=COLORS["bg_dark"],
                        font=("Helvetica", 10),
                    )
                    label.pack(anchor="w", pady=5)
                    self.fan_widgets.append(label)
        except Exception:
            pass
