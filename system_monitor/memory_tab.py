"""Memory monitoring tab - RAM and swap usage details."""

import tkinter as tk
from tkinter import ttk
import psutil

from system_monitor.widgets import (
    COLORS, ArcGauge, LineChart, BarMeter, InfoRow, SectionHeader, ScrollableFrame,
)


def fmt_bytes(b):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


class MemoryTab(tk.Frame):
    """Detailed memory (RAM + swap) monitoring."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._build_ui()

    def _build_ui(self):
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        container = scroll.scrollable_frame

        # -- Gauges --
        gauge_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        gauge_frame.pack(fill="x", padx=10, pady=10)

        self.ram_gauge = ArcGauge(gauge_frame, size=180, thickness=16, label="RAM")
        self.ram_gauge.pack(side="left", expand=True)

        self.swap_gauge = ArcGauge(gauge_frame, size=180, thickness=16, label="Swap")
        self.swap_gauge.pack(side="left", expand=True)

        # -- RAM Details --
        ram_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        ram_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(ram_frame, text="RAM Details").pack(fill="x", pady=(0, 5))

        self.ram_info = {}
        for key, label in [
            ("total", "Total"),
            ("available", "Available"),
            ("used", "Used"),
            ("free", "Free"),
            ("cached", "Cached"),
            ("buffers", "Buffers"),
            ("shared", "Shared"),
            ("active", "Active"),
            ("inactive", "Inactive"),
        ]:
            row = InfoRow(ram_frame, label)
            row.pack(fill="x", pady=1)
            self.ram_info[key] = row

        # -- RAM visual bar --
        self.ram_bar = BarMeter(ram_frame, width=700, height=28, label="")
        self.ram_bar.pack(fill="x", pady=(5, 0))

        # -- Memory History Chart --
        chart_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        chart_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(chart_frame, text="Memory Usage History (60s)").pack(fill="x", pady=(0, 5))

        self.mem_chart = LineChart(
            chart_frame,
            width=750,
            height=150,
            max_points=60,
            y_min=0,
            y_max=100,
            y_label="%",
            series_colors=[COLORS["accent_green"], COLORS["accent_purple"]],
            series_labels=["RAM %", "Swap %"],
        )
        self.mem_chart.pack(fill="x")

        # -- Swap Details --
        swap_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        swap_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(swap_frame, text="Swap Details").pack(fill="x", pady=(0, 5))

        self.swap_info = {}
        for key, label in [
            ("total", "Total"),
            ("used", "Used"),
            ("free", "Free"),
            ("sin", "Swapped In"),
            ("sout", "Swapped Out"),
        ]:
            row = InfoRow(swap_frame, label)
            row.pack(fill="x", pady=1)
            self.swap_info[key] = row

        self.swap_bar = BarMeter(swap_frame, width=700, height=28, label="")
        self.swap_bar.pack(fill="x", pady=(5, 10))

    def update_data(self):
        """Refresh memory data."""
        mem = psutil.virtual_memory()
        self.ram_gauge.set_value(mem.percent)
        self.ram_bar.set_value(mem.percent, f"{fmt_bytes(mem.used)} / {fmt_bytes(mem.total)}")

        self.ram_info["total"].set_value(fmt_bytes(mem.total))
        self.ram_info["available"].set_value(fmt_bytes(mem.available))
        self.ram_info["used"].set_value(fmt_bytes(mem.used))
        self.ram_info["free"].set_value(fmt_bytes(mem.free))

        for attr in ["cached", "buffers", "shared", "active", "inactive"]:
            val = getattr(mem, attr, None)
            if val is not None:
                self.ram_info[attr].set_value(fmt_bytes(val))
            else:
                self.ram_info[attr].set_value("N/A")

        swap = psutil.swap_memory()
        self.swap_gauge.set_value(swap.percent)
        self.swap_bar.set_value(swap.percent, f"{fmt_bytes(swap.used)} / {fmt_bytes(swap.total)}")

        self.swap_info["total"].set_value(fmt_bytes(swap.total))
        self.swap_info["used"].set_value(fmt_bytes(swap.used))
        self.swap_info["free"].set_value(fmt_bytes(swap.free))
        self.swap_info["sin"].set_value(fmt_bytes(getattr(swap, "sin", 0)))
        self.swap_info["sout"].set_value(fmt_bytes(getattr(swap, "sout", 0)))

        self.mem_chart.add_points([mem.percent, swap.percent])
