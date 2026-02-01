"""Overview dashboard tab - shows summary of all system resources."""

import tkinter as tk
from tkinter import ttk
import psutil
import platform
import time
from datetime import datetime, timedelta

from system_monitor.widgets import (
    COLORS, ArcGauge, LineChart, InfoRow, SectionHeader, ScrollableFrame,
)


class OverviewTab(tk.Frame):
    """Main overview dashboard showing all key metrics at a glance."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._build_ui()

    def _build_ui(self):
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        container = scroll.scrollable_frame

        # -- System Info Header --
        info_frame = tk.Frame(container, bg=COLORS["bg_medium"], padx=15, pady=10)
        info_frame.pack(fill="x", padx=10, pady=(10, 5))

        uname = platform.uname()
        hostname = uname.node
        os_info = f"{uname.system} {uname.release}"
        arch = uname.machine
        boot_time = datetime.fromtimestamp(psutil.boot_time())

        tk.Label(
            info_frame,
            text=f"  {hostname}",
            fg=COLORS["text_primary"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 16, "bold"),
        ).pack(anchor="w")

        tk.Label(
            info_frame,
            text=f"{os_info}  |  {arch}  |  Boot: {boot_time.strftime('%Y-%m-%d %H:%M')}",
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 10),
        ).pack(anchor="w", pady=(2, 0))

        self.uptime_label = tk.Label(
            info_frame,
            text="",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 9),
        )
        self.uptime_label.pack(anchor="w", pady=(2, 0))

        # -- Gauges Row --
        gauge_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        gauge_frame.pack(fill="x", padx=10, pady=10)

        self.cpu_gauge = ArcGauge(gauge_frame, size=160, thickness=14, label="CPU")
        self.cpu_gauge.pack(side="left", expand=True)

        self.mem_gauge = ArcGauge(gauge_frame, size=160, thickness=14, label="Memory")
        self.mem_gauge.pack(side="left", expand=True)

        self.disk_gauge = ArcGauge(gauge_frame, size=160, thickness=14, label="Disk")
        self.disk_gauge.pack(side="left", expand=True)

        self.swap_gauge = ArcGauge(gauge_frame, size=160, thickness=14, label="Swap")
        self.swap_gauge.pack(side="left", expand=True)

        # -- CPU History Chart --
        chart_section = tk.Frame(container, bg=COLORS["bg_dark"])
        chart_section.pack(fill="x", padx=10, pady=5)

        SectionHeader(chart_section, text="CPU Usage History").pack(fill="x", pady=(0, 5))
        self.cpu_chart = LineChart(
            chart_section,
            width=750,
            height=120,
            max_points=60,
            y_min=0,
            y_max=100,
            y_label="%",
            series_colors=[COLORS["accent_blue"]],
            series_labels=["CPU %"],
        )
        self.cpu_chart.pack(fill="x")

        # -- Memory History Chart --
        mem_section = tk.Frame(container, bg=COLORS["bg_dark"])
        mem_section.pack(fill="x", padx=10, pady=5)

        SectionHeader(mem_section, text="Memory Usage History").pack(fill="x", pady=(0, 5))
        self.mem_chart = LineChart(
            mem_section,
            width=750,
            height=120,
            max_points=60,
            y_min=0,
            y_max=100,
            y_label="%",
            series_colors=[COLORS["accent_green"], COLORS["accent_purple"]],
            series_labels=["RAM %", "Swap %"],
        )
        self.mem_chart.pack(fill="x")

        # -- Quick Stats Grid --
        stats_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        stats_frame.pack(fill="x", padx=10, pady=10)

        SectionHeader(stats_frame, text="Quick Stats").pack(fill="x", pady=(0, 5))

        grid = tk.Frame(stats_frame, bg=COLORS["bg_dark"])
        grid.pack(fill="x")

        self.info_rows = {}
        labels = [
            ("cpu_cores", "CPU Cores"),
            ("cpu_freq", "CPU Frequency"),
            ("ram_total", "Total RAM"),
            ("ram_used", "Used RAM"),
            ("disk_total", "Total Disk"),
            ("disk_used", "Used Disk"),
            ("net_sent", "Net Sent"),
            ("net_recv", "Net Received"),
            ("processes", "Processes"),
            ("battery", "Battery"),
        ]

        for i, (key, label) in enumerate(labels):
            row = InfoRow(grid, label)
            row.grid(row=i // 2, column=i % 2, sticky="ew", padx=5, pady=2)
            self.info_rows[key] = row

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

    def update_data(self):
        """Refresh all overview data."""
        # Uptime
        boot = psutil.boot_time()
        uptime_sec = time.time() - boot
        uptime = timedelta(seconds=int(uptime_sec))
        days = uptime.days
        hours, rem = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(rem, 60)
        self.uptime_label.config(text=f"Uptime: {days}d {hours}h {minutes}m")

        # CPU
        cpu_percent = psutil.cpu_percent(interval=0)
        self.cpu_gauge.set_value(cpu_percent)
        self.cpu_chart.add_point(cpu_percent)

        # Memory
        mem = psutil.virtual_memory()
        self.mem_gauge.set_value(mem.percent)

        swap = psutil.swap_memory()
        self.swap_gauge.set_value(swap.percent)

        self.mem_chart.add_points([mem.percent, swap.percent])

        # Disk (root partition)
        try:
            disk = psutil.disk_usage("/")
            self.disk_gauge.set_value(disk.percent)
        except Exception:
            pass

        # Quick stats
        cpu_count_phys = psutil.cpu_count(logical=False) or "N/A"
        cpu_count_log = psutil.cpu_count(logical=True) or "N/A"
        self.info_rows["cpu_cores"].set_value(f"{cpu_count_phys} physical / {cpu_count_log} logical")

        try:
            freq = psutil.cpu_freq()
            if freq:
                self.info_rows["cpu_freq"].set_value(f"{freq.current:.0f} MHz (max: {freq.max:.0f} MHz)")
            else:
                self.info_rows["cpu_freq"].set_value("N/A")
        except Exception:
            self.info_rows["cpu_freq"].set_value("N/A")

        self.info_rows["ram_total"].set_value(self._fmt_bytes(mem.total))
        self.info_rows["ram_used"].set_value(
            f"{self._fmt_bytes(mem.used)} ({mem.percent}%)"
        )

        try:
            disk = psutil.disk_usage("/")
            self.info_rows["disk_total"].set_value(self._fmt_bytes(disk.total))
            self.info_rows["disk_used"].set_value(
                f"{self._fmt_bytes(disk.used)} ({disk.percent}%)"
            )
        except Exception:
            pass

        net = psutil.net_io_counters()
        self.info_rows["net_sent"].set_value(self._fmt_bytes(net.bytes_sent))
        self.info_rows["net_recv"].set_value(self._fmt_bytes(net.bytes_recv))

        self.info_rows["processes"].set_value(str(len(psutil.pids())))

        battery = psutil.sensors_battery()
        if battery:
            plug = "Plugged in" if battery.power_plugged else "On battery"
            self.info_rows["battery"].set_value(f"{battery.percent:.0f}% ({plug})")
        else:
            self.info_rows["battery"].set_value("No battery detected")

    @staticmethod
    def _fmt_bytes(b):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} PB"
