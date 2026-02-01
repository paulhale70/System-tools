"""CPU monitoring tab - detailed CPU metrics and per-core usage."""

import tkinter as tk
from tkinter import ttk
import psutil

from system_monitor.widgets import (
    COLORS, ArcGauge, LineChart, BarMeter, InfoRow, SectionHeader, ScrollableFrame,
)


class CPUTab(tk.Frame):
    """Detailed CPU monitoring with per-core usage and history."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.core_bars = []
        self._build_ui()

    def _build_ui(self):
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        container = scroll.scrollable_frame

        # -- Top: Overall CPU gauge + info --
        top = tk.Frame(container, bg=COLORS["bg_dark"])
        top.pack(fill="x", padx=10, pady=10)

        left = tk.Frame(top, bg=COLORS["bg_dark"])
        left.pack(side="left")

        self.cpu_gauge = ArcGauge(left, size=180, thickness=16, label="Overall CPU")
        self.cpu_gauge.pack(padx=10)

        right = tk.Frame(top, bg=COLORS["bg_dark"])
        right.pack(side="left", fill="x", expand=True, padx=(20, 0))

        self.info_rows = {}
        labels = [
            ("model", "CPU Model"),
            ("cores_phys", "Physical Cores"),
            ("cores_log", "Logical Cores"),
            ("freq_current", "Current Frequency"),
            ("freq_min", "Min Frequency"),
            ("freq_max", "Max Frequency"),
            ("ctx_switches", "Context Switches"),
            ("interrupts", "Interrupts"),
        ]
        for key, label in labels:
            row = InfoRow(right, label)
            row.pack(fill="x", pady=1)
            self.info_rows[key] = row

        # -- CPU Usage History --
        chart_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        chart_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(chart_frame, text="CPU Usage History (60s)").pack(fill="x", pady=(0, 5))

        self.cpu_chart = LineChart(
            chart_frame,
            width=750,
            height=150,
            max_points=60,
            y_min=0,
            y_max=100,
            y_label="%",
            series_colors=[COLORS["accent_blue"], COLORS["accent"]],
            series_labels=["User+System", "IOWait"],
            show_legend=True,
        )
        self.cpu_chart.pack(fill="x")

        # -- Per-Core Usage --
        core_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        core_frame.pack(fill="x", padx=10, pady=10)

        SectionHeader(core_frame, text="Per-Core Usage").pack(fill="x", pady=(0, 5))

        self.cores_container = tk.Frame(core_frame, bg=COLORS["bg_dark"])
        self.cores_container.pack(fill="x")

        # Build core bars
        num_cores = psutil.cpu_count(logical=True) or 1
        for i in range(num_cores):
            bar = BarMeter(self.cores_container, width=700, height=20, label=f"Core {i}")
            bar.pack(fill="x", pady=1)
            self.core_bars.append(bar)

        # -- Load Average --
        load_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        load_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(load_frame, text="Load Average").pack(fill="x", pady=(0, 5))

        self.load_info = {}
        load_grid = tk.Frame(load_frame, bg=COLORS["bg_dark"])
        load_grid.pack(fill="x")

        for i, period in enumerate(["1 min", "5 min", "15 min"]):
            row = InfoRow(load_grid, period)
            row.grid(row=0, column=i, sticky="ew", padx=5)
            self.load_info[period] = row
            load_grid.columnconfigure(i, weight=1)

        # -- CPU Times --
        times_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        times_frame.pack(fill="x", padx=10, pady=(5, 15))

        SectionHeader(times_frame, text="CPU Times").pack(fill="x", pady=(0, 5))

        self.times_bars = {}
        for label in ["User", "System", "Idle", "IOWait", "Nice"]:
            bar = BarMeter(times_frame, width=700, height=20, label=label)
            bar.pack(fill="x", pady=1)
            self.times_bars[label] = bar

        # Populate static info
        self._populate_static()

    def _populate_static(self):
        try:
            import subprocess
            result = subprocess.run(
                ["cat", "/proc/cpuinfo"],
                capture_output=True, text=True, timeout=2,
            )
            for line in result.stdout.split("\n"):
                if "model name" in line:
                    self.info_rows["model"].set_value(line.split(":")[1].strip())
                    break
            else:
                self.info_rows["model"].set_value("N/A")
        except Exception:
            try:
                import platform
                self.info_rows["model"].set_value(platform.processor() or "N/A")
            except Exception:
                self.info_rows["model"].set_value("N/A")

        self.info_rows["cores_phys"].set_value(str(psutil.cpu_count(logical=False) or "N/A"))
        self.info_rows["cores_log"].set_value(str(psutil.cpu_count(logical=True) or "N/A"))

    def update_data(self):
        """Refresh CPU data."""
        # Overall CPU
        cpu_pct = psutil.cpu_percent(interval=0)
        self.cpu_gauge.set_value(cpu_pct)

        # CPU times percent for chart
        try:
            times_pct = psutil.cpu_times_percent(interval=0)
            user_sys = getattr(times_pct, "user", 0) + getattr(times_pct, "system", 0)
            iowait = getattr(times_pct, "iowait", 0)
            self.cpu_chart.add_points([user_sys, iowait])

            # CPU Times bars
            total = sum([
                getattr(times_pct, "user", 0),
                getattr(times_pct, "system", 0),
                getattr(times_pct, "idle", 0),
                getattr(times_pct, "iowait", 0),
                getattr(times_pct, "nice", 0),
            ])
            if total > 0:
                self.times_bars["User"].set_value(getattr(times_pct, "user", 0), f"{getattr(times_pct, 'user', 0):.1f}%")
                self.times_bars["System"].set_value(getattr(times_pct, "system", 0), f"{getattr(times_pct, 'system', 0):.1f}%")
                self.times_bars["Idle"].set_value(getattr(times_pct, "idle", 0), f"{getattr(times_pct, 'idle', 0):.1f}%")
                self.times_bars["IOWait"].set_value(getattr(times_pct, "iowait", 0), f"{getattr(times_pct, 'iowait', 0):.1f}%")
                self.times_bars["Nice"].set_value(getattr(times_pct, "nice", 0), f"{getattr(times_pct, 'nice', 0):.1f}%")
        except Exception:
            self.cpu_chart.add_points([cpu_pct, 0])

        # Frequency
        try:
            freq = psutil.cpu_freq()
            if freq:
                self.info_rows["freq_current"].set_value(f"{freq.current:.0f} MHz")
                self.info_rows["freq_min"].set_value(f"{freq.min:.0f} MHz")
                self.info_rows["freq_max"].set_value(f"{freq.max:.0f} MHz")
        except Exception:
            pass

        # Per-core usage
        per_core = psutil.cpu_percent(interval=0, percpu=True)
        for i, pct in enumerate(per_core):
            if i < len(self.core_bars):
                self.core_bars[i].set_value(pct, f"{pct:.1f}%")

        # Context switches and interrupts
        try:
            stats = psutil.cpu_stats()
            self.info_rows["ctx_switches"].set_value(f"{stats.ctx_switches:,}")
            self.info_rows["interrupts"].set_value(f"{stats.interrupts:,}")
        except Exception:
            pass

        # Load average
        try:
            load = psutil.getloadavg()
            num_cores = psutil.cpu_count(logical=True) or 1
            for i, period in enumerate(["1 min", "5 min", "15 min"]):
                val = load[i]
                pct = (val / num_cores) * 100
                self.load_info[period].set_value(f"{val:.2f} ({pct:.0f}%)")
        except Exception:
            pass
