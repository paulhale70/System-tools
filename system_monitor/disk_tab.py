"""Disk monitoring tab - partitions, usage, and I/O stats."""

import tkinter as tk
from tkinter import ttk
import psutil

from system_monitor.widgets import (
    COLORS, BarMeter, LineChart, InfoRow, SectionHeader, ScrollableFrame,
)


def fmt_bytes(b):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


class DiskTab(tk.Frame):
    """Disk partition usage and I/O monitoring."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.partition_widgets = []
        self._prev_io = None
        self._build_ui()

    def _build_ui(self):
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        container = scroll.scrollable_frame

        # -- Partitions --
        part_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        part_frame.pack(fill="x", padx=10, pady=10)

        SectionHeader(part_frame, text="Disk Partitions").pack(fill="x", pady=(0, 5))

        self.partitions_container = tk.Frame(part_frame, bg=COLORS["bg_dark"])
        self.partitions_container.pack(fill="x")

        self._build_partitions()

        # -- Disk I/O Chart --
        io_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        io_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(io_frame, text="Disk I/O (bytes/sec)").pack(fill="x", pady=(0, 5))

        self.io_chart = LineChart(
            io_frame,
            width=750,
            height=150,
            max_points=60,
            y_min=0,
            y_max=1024 * 1024,
            y_label="B/s",
            series_colors=[COLORS["accent_blue"], COLORS["accent"]],
            series_labels=["Read B/s", "Write B/s"],
        )
        self.io_chart.pack(fill="x")

        # -- I/O Stats --
        stats_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        stats_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(stats_frame, text="Disk I/O Statistics").pack(fill="x", pady=(0, 5))

        self.io_info = {}
        for key, label in [
            ("read_bytes", "Total Read"),
            ("write_bytes", "Total Written"),
            ("read_count", "Read Operations"),
            ("write_count", "Write Operations"),
            ("read_speed", "Read Speed"),
            ("write_speed", "Write Speed"),
        ]:
            row = InfoRow(stats_frame, label)
            row.pack(fill="x", pady=1)
            self.io_info[key] = row

    def _build_partitions(self):
        for w in self.partition_widgets:
            w["frame"].destroy()
        self.partition_widgets.clear()

        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except PermissionError:
                continue

            frame = tk.Frame(self.partitions_container, bg=COLORS["bg_medium"], padx=10, pady=8)
            frame.pack(fill="x", pady=3)

            header = tk.Frame(frame, bg=COLORS["bg_medium"])
            header.pack(fill="x")

            tk.Label(
                header,
                text=f"{part.device}  ({part.mountpoint})",
                fg=COLORS["text_primary"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 10, "bold"),
            ).pack(side="left")

            tk.Label(
                header,
                text=f"  {part.fstype}",
                fg=COLORS["text_dim"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 9),
            ).pack(side="left")

            bar = BarMeter(frame, width=700, height=22, label="")
            bar.pack(fill="x", pady=(4, 0))

            info_frame = tk.Frame(frame, bg=COLORS["bg_medium"])
            info_frame.pack(fill="x", pady=(4, 0))

            total_label = tk.Label(
                info_frame,
                text=f"Total: {fmt_bytes(usage.total)}",
                fg=COLORS["text_secondary"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 9),
            )
            total_label.pack(side="left", padx=(0, 15))

            used_label = tk.Label(
                info_frame,
                text=f"Used: {fmt_bytes(usage.used)}",
                fg=COLORS["text_secondary"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 9),
            )
            used_label.pack(side="left", padx=(0, 15))

            free_label = tk.Label(
                info_frame,
                text=f"Free: {fmt_bytes(usage.free)}",
                fg=COLORS["text_secondary"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 9),
            )
            free_label.pack(side="left")

            self.partition_widgets.append({
                "frame": frame,
                "bar": bar,
                "mountpoint": part.mountpoint,
                "total_label": total_label,
                "used_label": used_label,
                "free_label": free_label,
            })

    def update_data(self):
        """Refresh disk data."""
        # Update partition usage
        for pw in self.partition_widgets:
            try:
                usage = psutil.disk_usage(pw["mountpoint"])
                pw["bar"].set_value(usage.percent, f"{fmt_bytes(usage.used)} / {fmt_bytes(usage.total)}")
                pw["total_label"].config(text=f"Total: {fmt_bytes(usage.total)}")
                pw["used_label"].config(text=f"Used: {fmt_bytes(usage.used)}")
                pw["free_label"].config(text=f"Free: {fmt_bytes(usage.free)}")
            except Exception:
                pass

        # Disk I/O
        try:
            io = psutil.disk_io_counters()
            if io:
                self.io_info["read_bytes"].set_value(fmt_bytes(io.read_bytes))
                self.io_info["write_bytes"].set_value(fmt_bytes(io.write_bytes))
                self.io_info["read_count"].set_value(f"{io.read_count:,}")
                self.io_info["write_count"].set_value(f"{io.write_count:,}")

                if self._prev_io:
                    read_speed = io.read_bytes - self._prev_io.read_bytes
                    write_speed = io.write_bytes - self._prev_io.write_bytes
                    self.io_info["read_speed"].set_value(f"{fmt_bytes(read_speed)}/s")
                    self.io_info["write_speed"].set_value(f"{fmt_bytes(write_speed)}/s")

                    # Auto-scale chart
                    max_val = max(read_speed, write_speed, 1024)
                    current_max = self.io_chart.y_max
                    if max_val > current_max * 0.9 or max_val < current_max * 0.3:
                        self.io_chart.set_y_range(0, max(max_val * 1.3, 1024))

                    self.io_chart.add_points([read_speed, write_speed])

                self._prev_io = io
        except Exception:
            pass
