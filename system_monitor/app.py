"""Main application - System Resource Monitor with tabbed interface."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import psutil
import platform
import sys
import time
import datetime

from system_monitor.widgets import (
    COLORS, set_theme, get_current_theme, register_theme_callback,
)
from system_monitor.overview_tab import OverviewTab
from system_monitor.cpu_tab import CPUTab
from system_monitor.memory_tab import MemoryTab
from system_monitor.disk_tab import DiskTab
from system_monitor.network_tab import NetworkTab
from system_monitor.power_tab import PowerTab
from system_monitor.processes_tab import ProcessesTab
from system_monitor.wifi_tab import WifiTab
from system_monitor.gpu_tab import GPUTab
from system_monitor.security_tab import SecurityTab
from system_monitor.alerts import AlertManager, AlertConfigDialog
from system_monitor.data_export import DataLogger, generate_snapshot


class SystemMonitorApp:
    """Main application window for the System Resource Monitor."""

    def __init__(self, theme="dark", refresh_ms=1000):
        self.root = tk.Tk()
        self.root.title("System Resource Monitor")
        self.root.geometry("900x750")
        self.root.minsize(700, 500)

        # Apply initial theme
        if theme != "dark":
            set_theme(theme)

        self.root.configure(bg=COLORS["bg_dark"])
        self.root.wm_iconname("SysMonitor")

        # Detached tab windows
        self._detached_windows = {}

        # Refresh interval
        self._refresh_ms = refresh_ms

        # Uptime tracking
        self._boot_time = psutil.boot_time()

        # Data logger
        self._data_logger = DataLogger()

        # Alert manager
        self._alert_manager = AlertManager()
        self._alert_indicator_flash = False

        self._configure_styles()
        self._build_ui()
        self._bind_shortcuts()

        # Register theme callback
        register_theme_callback(self._on_theme_change)

        # Alert notification callback (flash indicator in status bar)
        self._alert_manager.set_notification_callback(self._on_alert_triggered)

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
        """Configure ttk styles for the current theme."""
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

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
        style.configure(
            "TScrollbar",
            background=COLORS["bg_medium"],
            troughcolor=COLORS["bg_dark"],
            borderwidth=0,
            arrowsize=14,
        )
        style.configure("TFrame", background=COLORS["bg_dark"])
        style.configure(
            "TScale",
            background=COLORS["bg_dark"],
            troughcolor=COLORS["bg_medium"],
        )

    def _build_ui(self):
        """Build the main UI layout."""
        # -- Top status bar --
        self.status_bar = tk.Frame(self.root, bg=COLORS["bg_medium"], padx=10, pady=5)
        self.status_bar.pack(fill="x")

        tk.Label(
            self.status_bar,
            text="System Resource Monitor",
            fg=COLORS["accent_blue"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 13, "bold"),
        ).pack(side="left")

        self.status_label = tk.Label(
            self.status_bar,
            text="",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 9),
        )
        self.status_label.pack(side="right")

        # Alert indicator
        self.alert_indicator = tk.Label(
            self.status_bar,
            text="",
            fg=COLORS["accent"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 9, "bold"),
        )
        self.alert_indicator.pack(side="right", padx=3)

        # Theme toggle button
        theme = get_current_theme()
        self.theme_btn = tk.Button(
            self.status_bar,
            text="Dark Mode" if theme == "light" else "Light Mode",
            command=self._toggle_theme,
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
            font=("Helvetica", 9),
            relief="flat",
            padx=8,
            pady=1,
        )
        self.theme_btn.pack(side="right", padx=5)

        # Export / Snapshot / Alerts buttons
        self.alerts_btn = tk.Button(
            self.status_bar,
            text="Alerts",
            command=self._open_alert_config,
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
            font=("Helvetica", 9),
            relief="flat",
            padx=6,
            pady=1,
        )
        self.alerts_btn.pack(side="right", padx=2)

        self.snapshot_btn = tk.Button(
            self.status_bar,
            text="Snapshot",
            command=self._save_snapshot,
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
            font=("Helvetica", 9),
            relief="flat",
            padx=6,
            pady=1,
        )
        self.snapshot_btn.pack(side="right", padx=2)

        self.log_btn = tk.Button(
            self.status_bar,
            text="Start Log",
            command=self._toggle_logging,
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
            font=("Helvetica", 9),
            relief="flat",
            padx=6,
            pady=1,
        )
        self.log_btn.pack(side="right", padx=2)

        # Quick stats
        self.quick_cpu = tk.Label(
            self.status_bar,
            text="CPU: ---%",
            fg=COLORS["accent_blue"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 9, "bold"),
        )
        self.quick_cpu.pack(side="right", padx=10)

        self.quick_mem = tk.Label(
            self.status_bar,
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
        self.wifi_tab = WifiTab(self.notebook)
        self.gpu_tab = GPUTab(self.notebook)
        self.processes_tab = ProcessesTab(self.notebook)
        self.security_tab = SecurityTab(self.notebook)

        self._tab_config = [
            (self.overview_tab, "  Overview  "),
            (self.cpu_tab, "  CPU  "),
            (self.memory_tab, "  Memory  "),
            (self.disk_tab, "  Disk  "),
            (self.network_tab, "  Network  "),
            (self.power_tab, "  Power  "),
            (self.wifi_tab, "  WiFi  "),
            (self.gpu_tab, "  GPU  "),
            (self.processes_tab, "  Processes  "),
            (self.security_tab, "  Security  "),
        ]

        for tab, label in self._tab_config:
            self.notebook.add(tab, text=label)

        self.tabs = [t for t, _ in self._tab_config]

        # Right-click on tab to detach
        self.notebook.bind("<Button-3>", self._on_tab_right_click)

        self.tab_context_menu = tk.Menu(self.root, tearoff=0)
        self.tab_context_menu.add_command(label="Detach Tab to Window", command=self._detach_selected_tab)

        # -- Bottom status bar --
        self.bottom_bar = tk.Frame(self.root, bg=COLORS["bg_medium"], padx=10, pady=3)
        self.bottom_bar.pack(fill="x")

        uname = platform.uname()
        self.system_label = tk.Label(
            self.bottom_bar,
            text=f"{uname.system} {uname.release} | {uname.machine} | Python {sys.version.split()[0]}",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 8),
        )
        self.system_label.pack(side="left")

        # Uptime counter
        self.uptime_label = tk.Label(
            self.bottom_bar,
            text="Uptime: ...",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 8),
        )
        self.uptime_label.pack(side="left", padx=(15, 0))

        # Refresh rate controls (right side)
        refresh_frame = tk.Frame(self.bottom_bar, bg=COLORS["bg_medium"])
        refresh_frame.pack(side="right")

        self.refresh_label = tk.Label(
            refresh_frame,
            text=f"Refresh: {self._refresh_ms}ms",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 8),
        )
        self.refresh_label.pack(side="right")

        self.refresh_slider = tk.Scale(
            refresh_frame,
            from_=500,
            to=5000,
            resolution=100,
            orient="horizontal",
            length=150,
            command=self._on_refresh_change,
            bg=COLORS["bg_medium"],
            fg=COLORS["text_dim"],
            troughcolor=COLORS["bg_dark"],
            highlightthickness=0,
            font=("Helvetica", 7),
            showvalue=False,
            sliderlength=15,
            width=10,
        )
        self.refresh_slider.set(self._refresh_ms)
        self.refresh_slider.pack(side="right", padx=5)

        tk.Label(
            refresh_frame,
            text="Refresh Rate:",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 8),
        ).pack(side="right", padx=(0, 2))

        # Shortcut help
        self.shortcut_label = tk.Label(
            self.bottom_bar,
            text="Ctrl+1-0: tabs | F5: refresh | Ctrl+Q: quit",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 7),
        )
        self.shortcut_label.pack(side="right", padx=(0, 15))

    # -- Keyboard Shortcuts --
    def _bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        # Tab switching: Ctrl+1 through Ctrl+0 (0 = tab 10)
        for i in range(1, 10):
            self.root.bind(f"<Control-Key-{i}>", lambda e, idx=i - 1: self._switch_tab(idx))
        self.root.bind("<Control-Key-0>", lambda e: self._switch_tab(9))

        # Ctrl+Q to quit
        self.root.bind("<Control-q>", lambda e: self._quit())
        self.root.bind("<Control-Q>", lambda e: self._quit())

        # F5 to force refresh
        self.root.bind("<F5>", lambda e: self._force_refresh())

        # Ctrl+S for snapshot
        self.root.bind("<Control-s>", lambda e: self._save_snapshot())
        self.root.bind("<Control-S>", lambda e: self._save_snapshot())

        # Ctrl+L to toggle logging
        self.root.bind("<Control-l>", lambda e: self._toggle_logging())
        self.root.bind("<Control-L>", lambda e: self._toggle_logging())

    def _switch_tab(self, idx):
        """Switch to tab by index."""
        if self.notebook.index("end") > idx:
            self.notebook.select(idx)

    def _quit(self):
        """Clean quit."""
        if self._data_logger.is_running:
            self._data_logger.stop()
        self.root.quit()

    def _force_refresh(self):
        """Force an immediate data refresh of the current tab."""
        try:
            if self.notebook.index("end") > 0:
                current_idx = self.notebook.index(self.notebook.select())
                current_tab_id = self.notebook.tabs()[current_idx]
                for tab in self.tabs:
                    if str(tab) == current_tab_id:
                        tab.update_data()
                        break
        except Exception:
            pass

    # -- Data Export --
    def _toggle_logging(self):
        """Start or stop CSV/JSON logging."""
        if self._data_logger.is_running:
            self._data_logger.stop()
            self.log_btn.config(text="Start Log", bg=COLORS["bg_light"])
        else:
            filepath = filedialog.asksaveasfilename(
                title="Save Log File",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("JSON Lines", "*.jsonl"), ("All files", "*.*")],
                parent=self.root,
            )
            if filepath:
                fmt = "json" if filepath.endswith(".jsonl") else "csv"
                self._data_logger.fmt = fmt
                self._data_logger.interval = self._refresh_ms / 1000.0
                actual_path = self._data_logger.start(filepath)
                self.log_btn.config(text="Stop Log", bg=COLORS["accent"])

    def _save_snapshot(self):
        """Save a session snapshot to HTML or text."""
        filepath = filedialog.asksaveasfilename(
            title="Save Snapshot",
            defaultextension=".html",
            filetypes=[("HTML report", "*.html"), ("Text report", "*.txt"), ("All files", "*.*")],
            parent=self.root,
        )
        if filepath:
            fmt = "text" if filepath.endswith(".txt") else "html"
            actual_path = generate_snapshot(filepath, fmt=fmt)
            messagebox.showinfo("Snapshot Saved", f"Snapshot saved to:\n{actual_path}", parent=self.root)

    # -- Alerts --
    def _open_alert_config(self):
        """Open alert configuration dialog."""
        AlertConfigDialog(self.root, self._alert_manager)

    def _on_alert_triggered(self, name, metric, value, threshold):
        """Callback when an alert fires - flash indicator."""
        self.alert_indicator.config(text=f"ALERT: {name}")
        self._alert_indicator_flash = True
        # Clear after 10 seconds
        self.root.after(10000, self._clear_alert_indicator)

    def _clear_alert_indicator(self):
        self.alert_indicator.config(text="")
        self._alert_indicator_flash = False

    # -- Theme --
    def _on_refresh_change(self, value):
        self._refresh_ms = int(float(value))
        self.refresh_label.config(text=f"Refresh: {self._refresh_ms}ms")

    def _toggle_theme(self):
        current = get_current_theme()
        new_theme = "light" if current == "dark" else "dark"
        set_theme(new_theme)

    def _on_theme_change(self):
        self._configure_styles()

        self.root.configure(bg=COLORS["bg_dark"])
        self.status_bar.configure(bg=COLORS["bg_medium"])
        self.bottom_bar.configure(bg=COLORS["bg_medium"])

        for widget in self.status_bar.winfo_children():
            try:
                if isinstance(widget, tk.Label):
                    widget.configure(bg=COLORS["bg_medium"])
                    current_fg = str(widget.cget("fg"))
                    if current_fg in ("#636e72", "#8a8a9a"):
                        widget.configure(fg=COLORS["text_dim"])
                elif isinstance(widget, tk.Button):
                    widget.configure(bg=COLORS["bg_light"], fg=COLORS["text_primary"])
            except tk.TclError:
                pass

        for widget in self.bottom_bar.winfo_children():
            try:
                widget.configure(bg=COLORS["bg_medium"])
                if isinstance(widget, tk.Label):
                    widget.configure(fg=COLORS["text_dim"])
                elif isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        try:
                            child.configure(bg=COLORS["bg_medium"])
                            if isinstance(child, tk.Label):
                                child.configure(fg=COLORS["text_dim"])
                            elif isinstance(child, tk.Scale):
                                child.configure(
                                    bg=COLORS["bg_medium"],
                                    fg=COLORS["text_dim"],
                                    troughcolor=COLORS["bg_dark"],
                                )
                        except tk.TclError:
                            pass
            except tk.TclError:
                pass

        theme = get_current_theme()
        self.theme_btn.config(
            text="Dark Mode" if theme == "light" else "Light Mode",
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
        )

        self.quick_cpu.configure(bg=COLORS["bg_medium"])
        self.quick_mem.configure(bg=COLORS["bg_medium"])
        self.status_label.configure(bg=COLORS["bg_medium"], fg=COLORS["text_dim"])
        self.alert_indicator.configure(bg=COLORS["bg_medium"])

    # -- Tab detach/reattach --
    def _on_tab_right_click(self, event):
        try:
            clicked_tab = self.notebook.identify(event.x, event.y)
            if clicked_tab:
                tab_index = self.notebook.index(f"@{event.x},{event.y}")
                self.notebook.select(tab_index)
                self._right_clicked_tab_index = tab_index
                self.tab_context_menu.tk_popup(event.x_root, event.y_root)
        except (tk.TclError, ValueError):
            pass

    def _detach_selected_tab(self):
        try:
            idx = self._right_clicked_tab_index
        except AttributeError:
            return

        if idx < 0 or idx >= len(self.tabs):
            return

        tab_widget = self.tabs[idx]
        tab_name = self._tab_config[idx][1].strip()

        if tab_name in self._detached_windows:
            return

        self.notebook.forget(idx)

        window = tk.Toplevel(self.root)
        window.title(f"System Monitor - {tab_name}")
        window.geometry("850x650")
        window.configure(bg=COLORS["bg_dark"])

        tab_widget.pack_forget()
        tab_widget.pack(in_=window, fill="both", expand=True)

        self._detached_windows[tab_name] = {
            "window": window,
            "tab": tab_widget,
            "index": idx,
        }

        window.protocol("WM_DELETE_WINDOW", lambda n=tab_name: self._reattach_tab(n))

    def _reattach_tab(self, tab_name):
        if tab_name not in self._detached_windows:
            return

        info = self._detached_windows.pop(tab_name)
        window = info["window"]
        tab_widget = info["tab"]
        original_idx = info["index"]

        tab_widget.pack_forget()

        current_count = self.notebook.index("end")
        insert_idx = min(original_idx, current_count)

        self.notebook.insert(insert_idx, tab_widget, text=f"  {tab_name}  ")

        window.destroy()

    # -- Update Loop --
    def _update_loop(self):
        try:
            # Quick stats
            cpu_pct = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            mem_pct = mem.percent
            self.quick_cpu.config(text=f"CPU: {cpu_pct:.1f}%")
            self.quick_mem.config(text=f"RAM: {mem_pct:.1f}%")

            # Uptime
            uptime_secs = time.time() - self._boot_time
            uptime_str = str(datetime.timedelta(seconds=int(uptime_secs)))
            self.uptime_label.config(text=f"Uptime: {uptime_str}")

            # Check alerts
            try:
                disk = psutil.disk_usage("/")
                disk_pct = disk.percent
            except Exception:
                disk_pct = 0
            swap_pct = psutil.swap_memory().percent
            self._alert_manager.check_all(cpu_pct, mem_pct, disk_pct, swap_pct)

            # Update visible tab
            if self.notebook.index("end") > 0:
                current_idx = self.notebook.index(self.notebook.select())
                current_tab_id = self.notebook.tabs()[current_idx]
                for tab in self.tabs:
                    if str(tab) == current_tab_id:
                        tab.update_data()
                        break

            # Update detached tabs
            for name, info in self._detached_windows.items():
                try:
                    info["tab"].update_data()
                except Exception:
                    pass

            self.status_label.config(text="Live")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)[:50]}")

        self.root.after(self._refresh_ms, self._update_loop)

    def run(self):
        """Start the application main loop."""
        self.root.mainloop()


def main():
    """Entry point - parse CLI arguments and launch."""
    import argparse

    parser = argparse.ArgumentParser(
        description="System Resource Monitor - real-time system monitoring desktop application",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run in headless mode (no GUI) - log metrics to stdout or file",
    )
    parser.add_argument(
        "--theme", choices=["dark", "light"], default="dark",
        help="UI color theme (default: dark)",
    )
    parser.add_argument(
        "--refresh", type=int, default=1000,
        help="Refresh interval in milliseconds (default: 1000, range: 500-5000)",
    )
    parser.add_argument(
        "--format", choices=["csv", "json"], default="csv",
        help="Output format for headless mode (default: csv)",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output file for headless mode (default: stdout)",
    )
    parser.add_argument(
        "--duration", type=int, default=None,
        help="Duration in seconds for headless mode (default: unlimited)",
    )
    parser.add_argument(
        "--snapshot", type=str, default=None,
        help="Generate a snapshot report and exit. Specify output file path.",
    )

    args = parser.parse_args()

    # Snapshot mode
    if args.snapshot:
        fmt = "text" if args.snapshot.endswith(".txt") else "html"
        path = generate_snapshot(args.snapshot, fmt=fmt)
        print(f"Snapshot saved to: {path}")
        return

    # Headless mode
    if args.headless:
        from system_monitor.data_export import headless_log
        interval = max(0.5, args.refresh / 1000.0)
        headless_log(
            fmt=args.format,
            interval=interval,
            output=args.output,
            duration=args.duration,
        )
        return

    # GUI mode
    refresh = max(500, min(5000, args.refresh))
    app = SystemMonitorApp(theme=args.theme, refresh_ms=refresh)
    app.run()


if __name__ == "__main__":
    main()
