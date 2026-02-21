"""GPU monitoring tab - usage, VRAM, temperature, fans, clock speed."""

import tkinter as tk
from tkinter import ttk
from collections import deque

from system_monitor.widgets import (
    COLORS, ArcGauge, LineChart, InfoRow, SectionHeader, ScrollableFrame,
)


def fmt_bytes(b):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _try_import_nvidia():
    """Try to import pynvml for NVIDIA GPU monitoring."""
    try:
        import pynvml
        pynvml.nvmlInit()
        return pynvml
    except Exception:
        return None


def _try_import_gputil():
    """Try to import GPUtil as fallback."""
    try:
        import GPUtil
        return GPUtil
    except Exception:
        return None


class GPUTab(tk.Frame):
    """GPU monitoring - usage, VRAM, temperature, fan speed, clocks."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._pynvml = _try_import_nvidia()
        self._gputil = _try_import_gputil() if not self._pynvml else None
        self._gpu_count = 0
        self._gpu_handles = []
        self._gpu_widgets = []

        if self._pynvml:
            try:
                self._gpu_count = self._pynvml.nvmlDeviceGetCount()
                self._gpu_handles = [
                    self._pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(self._gpu_count)
                ]
            except Exception:
                self._gpu_count = 0

        self._build_ui()

    def _build_ui(self):
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        container = scroll.scrollable_frame

        if self._gpu_count == 0 and not self._gputil:
            # No GPU detected
            no_gpu_frame = tk.Frame(container, bg=COLORS["bg_dark"], padx=20, pady=40)
            no_gpu_frame.pack(fill="both", expand=True)

            tk.Label(
                no_gpu_frame,
                text="No GPU Detected",
                fg=COLORS["text_primary"],
                bg=COLORS["bg_dark"],
                font=("Helvetica", 16, "bold"),
            ).pack(pady=(20, 10))

            tk.Label(
                no_gpu_frame,
                text="GPU monitoring requires NVIDIA GPU with pynvml or GPUtil installed.",
                fg=COLORS["text_secondary"],
                bg=COLORS["bg_dark"],
                font=("Helvetica", 10),
            ).pack()

            tk.Label(
                no_gpu_frame,
                text="Install with:  pip install pynvml  or  pip install GPUtil",
                fg=COLORS["text_dim"],
                bg=COLORS["bg_dark"],
                font=("Courier", 9),
            ).pack(pady=(10, 0))

            tk.Label(
                no_gpu_frame,
                text="AMD GPUs: pip install pyamdgpuinfo",
                fg=COLORS["text_dim"],
                bg=COLORS["bg_dark"],
                font=("Courier", 9),
            ).pack(pady=(5, 0))

            return

        # Build per-GPU sections
        if self._pynvml:
            for i in range(self._gpu_count):
                gpu_frame = self._build_gpu_section_nvidia(container, i)
                self._gpu_widgets.append(gpu_frame)
        elif self._gputil:
            self._build_gpu_section_gputil(container)

    def _build_gpu_section_nvidia(self, parent, gpu_idx):
        """Build monitoring section for an NVIDIA GPU using pynvml."""
        handle = self._gpu_handles[gpu_idx]

        try:
            name = self._pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8")
        except Exception:
            name = f"GPU {gpu_idx}"

        frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        frame.pack(fill="x", padx=10, pady=10)

        SectionHeader(frame, text=f"GPU {gpu_idx}: {name}").pack(fill="x", pady=(0, 8))

        # Gauges row
        gauges_frame = tk.Frame(frame, bg=COLORS["bg_dark"])
        gauges_frame.pack(fill="x")

        gpu_gauge = ArcGauge(gauges_frame, size=130, label="GPU Usage")
        gpu_gauge.pack(side="left", padx=10)

        mem_gauge = ArcGauge(gauges_frame, size=130, label="VRAM Usage")
        mem_gauge.pack(side="left", padx=10)

        temp_gauge = ArcGauge(gauges_frame, size=130, label="Temperature")
        temp_gauge.pack(side="left", padx=10)

        # Usage history chart
        chart = LineChart(
            frame,
            width=750,
            height=140,
            max_points=60,
            y_min=0,
            y_max=100,
            y_label="%",
            series_colors=[COLORS["accent_green"], COLORS["accent_blue"], COLORS["accent_orange"]],
            series_labels=["GPU %", "VRAM %", "Temp %"],
        )
        chart.pack(fill="x", pady=(5, 5))

        # Info rows
        info = {}
        for key, label in [
            ("name", "GPU Name"),
            ("driver", "Driver Version"),
            ("gpu_util", "GPU Utilization"),
            ("mem_util", "Memory Utilization"),
            ("mem_used", "VRAM Used"),
            ("mem_total", "VRAM Total"),
            ("mem_free", "VRAM Free"),
            ("temperature", "Temperature"),
            ("fan_speed", "Fan Speed"),
            ("power_draw", "Power Draw"),
            ("power_limit", "Power Limit"),
            ("clock_gpu", "GPU Clock"),
            ("clock_mem", "Memory Clock"),
            ("pcie_gen", "PCIe Generation"),
            ("pcie_width", "PCIe Width"),
        ]:
            row = InfoRow(frame, label)
            row.pack(fill="x", pady=1)
            info[key] = row

        return {
            "handle": handle,
            "gpu_gauge": gpu_gauge,
            "mem_gauge": mem_gauge,
            "temp_gauge": temp_gauge,
            "chart": chart,
            "info": info,
        }

    def _build_gpu_section_gputil(self, parent):
        """Build monitoring section using GPUtil (simpler interface)."""
        frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        frame.pack(fill="x", padx=10, pady=10)

        SectionHeader(frame, text="GPU Monitoring (via GPUtil)").pack(fill="x", pady=(0, 8))

        # Simple treeview
        columns = ("id", "name", "gpu_util", "mem_util", "mem_used", "mem_total", "temp")
        self.gputil_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            style="Proc.Treeview",
            height=5,
        )

        headings = {
            "id": ("ID", 40),
            "name": ("Name", 200),
            "gpu_util": ("GPU %", 80),
            "mem_util": ("VRAM %", 80),
            "mem_used": ("VRAM Used", 100),
            "mem_total": ("VRAM Total", 100),
            "temp": ("Temp (C)", 80),
        }

        for col, (text, width) in headings.items():
            self.gputil_tree.heading(col, text=text)
            self.gputil_tree.column(col, width=width)

        self.gputil_tree.pack(fill="x")

    def update_data(self):
        """Refresh GPU data."""
        if self._pynvml:
            self._update_nvidia()
        elif self._gputil:
            self._update_gputil()

    def _update_nvidia(self):
        """Update NVIDIA GPU data via pynvml."""
        nvml = self._pynvml

        for widgets in self._gpu_widgets:
            handle = widgets["handle"]
            info = widgets["info"]

            try:
                # Name and driver
                try:
                    name = nvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode("utf-8")
                    info["name"].set_value(name)
                except Exception:
                    pass

                try:
                    driver = nvml.nvmlSystemGetDriverVersion()
                    if isinstance(driver, bytes):
                        driver = driver.decode("utf-8")
                    info["driver"].set_value(driver)
                except Exception:
                    pass

                # Utilization
                try:
                    util = nvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_pct = util.gpu
                    mem_util_pct = util.memory
                    widgets["gpu_gauge"].set_value(gpu_pct)
                    info["gpu_util"].set_value(f"{gpu_pct}%")
                    info["mem_util"].set_value(f"{mem_util_pct}%")
                except Exception:
                    gpu_pct = 0
                    mem_util_pct = 0

                # Memory
                try:
                    mem_info = nvml.nvmlDeviceGetMemoryInfo(handle)
                    mem_pct = (mem_info.used / mem_info.total * 100) if mem_info.total > 0 else 0
                    widgets["mem_gauge"].set_value(mem_pct)
                    info["mem_used"].set_value(fmt_bytes(mem_info.used))
                    info["mem_total"].set_value(fmt_bytes(mem_info.total))
                    info["mem_free"].set_value(fmt_bytes(mem_info.free))
                except Exception:
                    mem_pct = 0

                # Temperature
                try:
                    temp = nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU)
                    temp_pct = min(100, temp)  # Use raw temp as percentage of 100C
                    widgets["temp_gauge"].set_value(temp_pct)
                    info["temperature"].set_value(f"{temp} C")
                except Exception:
                    temp_pct = 0

                # Chart
                widgets["chart"].add_points([gpu_pct, mem_pct, temp_pct])

                # Fan
                try:
                    fan = nvml.nvmlDeviceGetFanSpeed(handle)
                    info["fan_speed"].set_value(f"{fan}%")
                except Exception:
                    info["fan_speed"].set_value("N/A")

                # Power
                try:
                    power = nvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                    info["power_draw"].set_value(f"{power:.1f} W")
                except Exception:
                    info["power_draw"].set_value("N/A")

                try:
                    power_limit = nvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
                    info["power_limit"].set_value(f"{power_limit:.1f} W")
                except Exception:
                    info["power_limit"].set_value("N/A")

                # Clocks
                try:
                    clock_gpu = nvml.nvmlDeviceGetClockInfo(handle, nvml.NVML_CLOCK_GRAPHICS)
                    info["clock_gpu"].set_value(f"{clock_gpu} MHz")
                except Exception:
                    info["clock_gpu"].set_value("N/A")

                try:
                    clock_mem = nvml.nvmlDeviceGetClockInfo(handle, nvml.NVML_CLOCK_MEM)
                    info["clock_mem"].set_value(f"{clock_mem} MHz")
                except Exception:
                    info["clock_mem"].set_value("N/A")

                # PCIe
                try:
                    pcie_gen = nvml.nvmlDeviceGetCurrPcieLinkGeneration(handle)
                    info["pcie_gen"].set_value(f"Gen {pcie_gen}")
                except Exception:
                    info["pcie_gen"].set_value("N/A")

                try:
                    pcie_width = nvml.nvmlDeviceGetCurrPcieLinkWidth(handle)
                    info["pcie_width"].set_value(f"x{pcie_width}")
                except Exception:
                    info["pcie_width"].set_value("N/A")

            except Exception:
                pass

    def _update_gputil(self):
        """Update GPU data via GPUtil."""
        try:
            gpus = self._gputil.getGPUs()
            self.gputil_tree.delete(*self.gputil_tree.get_children())

            for gpu in gpus:
                self.gputil_tree.insert("", "end", values=(
                    gpu.id,
                    gpu.name,
                    f"{gpu.load * 100:.1f}" if gpu.load else "N/A",
                    f"{gpu.memoryUtil * 100:.1f}" if gpu.memoryUtil else "N/A",
                    f"{gpu.memoryUsed:.0f} MB" if gpu.memoryUsed else "N/A",
                    f"{gpu.memoryTotal:.0f} MB" if gpu.memoryTotal else "N/A",
                    f"{gpu.temperature}" if gpu.temperature else "N/A",
                ))
        except Exception:
            pass
