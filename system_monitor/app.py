"""Main application - System Resource Monitor with tabbed interface."""

import tkinter as tk
from tkinter import ttk
import psutil
import platform
import sys

from system_monitor.widgets import COLORS
from system_monitor.overview_tab import OverviewTab
from system_monitor.cpu_tab import CPUTab
from system_monitor.memory_tab import MemoryTab
from system_monitor.disk_tab import DiskTab
from system_monitor.network_tab import NetworkTab
from system_monitor.power_tab import PowerTab
from system_monitor.processes_tab import ProcessesTab


class SystemMonitorApp:
    """Main application window for the System Resource Monitor."""

    REFRESH_INTERVAL_MS = 1000  # Update every 1 second

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("System Resource Monitor")
        self.root.geometry("850x700")
        self.root.minsize(700, 500)
        self.root.configure(bg=COLORS["bg_dark"])

        # Set window icon title
        self.root.wm_iconname("SysMonitor")

        self._configure_styles()
        self._build_ui()

        # Start the initial data collection pass
        psutil.cpu_percent(interval=0)
        psutil.cpu_percent(interval=0, percpu=True)
        try:
            psutil.cpu_times_percent(interval=0)
        except Exception:
            pass

        # Begin periodic refresh
        self._update_loop()

    def _configure_styles(self):
        """Configure ttk styles for the dark theme."""
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Notebook (tabs) style
        style.configure("TNotebook", background=COLORS["bg_dark"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=COLORS["bg_medium"],
            foreground=COLORS["text_secondary"],
            padding=[16, 8],
            font=("Helvetica", 10),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", COLORS["bg_light"]),
                ("active", COLORS["bg_light"]),
            ],
            foreground=[
                ("selected", COLORS["text_primary"]),
                ("active", COLORS["text_primary"]),
            ],
        )

        # Scrollbar style
        style.configure(
            "TScrollbar",
            background=COLORS["bg_medium"],
            troughcolor=COLORS["bg_dark"],
            borderwidth=0,
            arrowsize=14,
        )

        # Frame style
        style.configure("TFrame", background=COLORS["bg_dark"])

    def _build_ui(self):
        """Build the main UI layout."""
        # -- Status bar at the top --
        status_bar = tk.Frame(self.root, bg=COLORS["bg_medium"], padx=10, pady=5)
        status_bar.pack(fill="x")

        tk.Label(
            status_bar,
            text="System Resource Monitor",
            fg=COLORS["accent_blue"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 13, "bold"),
        ).pack(side="left")

        self.status_label = tk.Label(
            status_bar,
            text="",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 9),
        )
        self.status_label.pack(side="right")

        # Quick stats in status bar
        self.quick_cpu = tk.Label(
            status_bar,
            text="CPU: ---%",
            fg=COLORS["accent_blue"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 9, "bold"),
        )
        self.quick_cpu.pack(side="right", padx=10)

        self.quick_mem = tk.Label(
            status_bar,
            text="RAM: ---%",
            fg=COLORS["accent_green"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 9, "bold"),
        )
        self.quick_mem.pack(side="right", padx=10)

        # -- Notebook (tabs) --
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Create tabs
        self.overview_tab = OverviewTab(self.notebook)
        self.cpu_tab = CPUTab(self.notebook)
        self.memory_tab = MemoryTab(self.notebook)
        self.disk_tab = DiskTab(self.notebook)
        self.network_tab = NetworkTab(self.notebook)
        self.power_tab = PowerTab(self.notebook)
        self.processes_tab = ProcessesTab(self.notebook)

        self.notebook.add(self.overview_tab, text="  Overview  ")
        self.notebook.add(self.cpu_tab, text="  CPU  ")
        self.notebook.add(self.memory_tab, text="  Memory  ")
        self.notebook.add(self.disk_tab, text="  Disk  ")
        self.notebook.add(self.network_tab, text="  Network  ")
        self.notebook.add(self.power_tab, text="  Power  ")
        self.notebook.add(self.processes_tab, text="  Processes  ")

        # Map tab indices to tabs for selective updating
        self.tabs = [
            self.overview_tab,
            self.cpu_tab,
            self.memory_tab,
            self.disk_tab,
            self.network_tab,
            self.power_tab,
            self.processes_tab,
        ]

        # -- Bottom status --
        bottom = tk.Frame(self.root, bg=COLORS["bg_medium"], padx=10, pady=3)
        bottom.pack(fill="x")

        uname = platform.uname()
        tk.Label(
            bottom,
            text=f"{uname.system} {uname.release} | {uname.machine} | Python {sys.version.split()[0]}",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 8),
        ).pack(side="left")

        self.refresh_label = tk.Label(
            bottom,
            text=f"Refresh: {self.REFRESH_INTERVAL_MS}ms",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 8),
        )
        self.refresh_label.pack(side="right")

    def _update_loop(self):
        """Periodic data refresh - only update the currently visible tab."""
        try:
            # Always update status bar quick stats
            cpu_pct = psutil.cpu_percent(interval=0)
            mem_pct = psutil.virtual_memory().percent
            self.quick_cpu.config(text=f"CPU: {cpu_pct:.1f}%")
            self.quick_mem.config(text=f"RAM: {mem_pct:.1f}%")

            # Update only the visible tab for efficiency
            current_idx = self.notebook.index(self.notebook.select())
            current_tab = self.tabs[current_idx]
            current_tab.update_data()

            self.status_label.config(text="Live")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)[:50]}")

        self.root.after(self.REFRESH_INTERVAL_MS, self._update_loop)

    def run(self):
        """Start the application main loop."""
        self.root.mainloop()


def main():
    """Entry point for the System Resource Monitor."""
    app = SystemMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
