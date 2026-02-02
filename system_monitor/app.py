"""Main application - System Resource Monitor with tabbed interface."""

import tkinter as tk
from tkinter import ttk
import psutil
import platform
import sys

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


class SystemMonitorApp:
    """Main application window for the System Resource Monitor."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("System Resource Monitor")
        self.root.geometry("900x750")
        self.root.minsize(700, 500)
        self.root.configure(bg=COLORS["bg_dark"])

        # Set window icon title
        self.root.wm_iconname("SysMonitor")

        # Detached tab windows
        self._detached_windows = {}

        # Refresh interval
        self._refresh_ms = 1000

        self._configure_styles()
        self._build_ui()

        # Register theme callback
        register_theme_callback(self._on_theme_change)

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

        # Scale style
        style.configure(
            "TScale",
            background=COLORS["bg_dark"],
            troughcolor=COLORS["bg_medium"],
        )

    def _build_ui(self):
        """Build the main UI layout."""
        # -- Status bar at the top --
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

        # Theme toggle button
        self.theme_btn = tk.Button(
            self.status_bar,
            text="Light Mode",
            command=self._toggle_theme,
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
            font=("Helvetica", 9),
            relief="flat",
            padx=8,
            pady=1,
        )
        self.theme_btn.pack(side="right", padx=5)

        # Quick stats in status bar
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
        self.processes_tab = ProcessesTab(self.notebook)

        self._tab_config = [
            (self.overview_tab, "  Overview  "),
            (self.cpu_tab, "  CPU  "),
            (self.memory_tab, "  Memory  "),
            (self.disk_tab, "  Disk  "),
            (self.network_tab, "  Network  "),
            (self.power_tab, "  Power  "),
            (self.wifi_tab, "  WiFi  "),
            (self.processes_tab, "  Processes  "),
        ]

        for tab, label in self._tab_config:
            self.notebook.add(tab, text=label)

        # Map tab indices to tabs for selective updating
        self.tabs = [t for t, _ in self._tab_config]

        # Right-click on tab to detach
        self.notebook.bind("<Button-3>", self._on_tab_right_click)

        # Tab context menu
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

        # Refresh rate controls
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

    def _on_refresh_change(self, value):
        """Handle refresh rate slider change."""
        self._refresh_ms = int(float(value))
        self.refresh_label.config(text=f"Refresh: {self._refresh_ms}ms")

    def _toggle_theme(self):
        """Toggle between dark and light themes."""
        current = get_current_theme()
        new_theme = "light" if current == "dark" else "dark"
        set_theme(new_theme)

    def _on_theme_change(self):
        """Callback when theme changes - reconfigure styles and rebuild."""
        self._configure_styles()

        # Update root and status bar colors
        self.root.configure(bg=COLORS["bg_dark"])
        self.status_bar.configure(bg=COLORS["bg_medium"])
        self.bottom_bar.configure(bg=COLORS["bg_medium"])

        # Update all direct children labels/buttons
        for widget in self.status_bar.winfo_children():
            try:
                if isinstance(widget, tk.Label):
                    widget.configure(bg=COLORS["bg_medium"])
                    current_fg = str(widget.cget("fg"))
                    # Keep accent colors, update text colors
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

        # Update theme button text
        theme = get_current_theme()
        self.theme_btn.config(
            text="Dark Mode" if theme == "light" else "Light Mode",
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
        )

        self.quick_cpu.configure(bg=COLORS["bg_medium"])
        self.quick_mem.configure(bg=COLORS["bg_medium"])
        self.status_label.configure(bg=COLORS["bg_medium"], fg=COLORS["text_dim"])

    # -- Tab detach/reattach --
    def _on_tab_right_click(self, event):
        """Handle right-click on tab headers."""
        try:
            clicked_tab = self.notebook.identify(event.x, event.y)
            if clicked_tab:
                # Select the tab that was right-clicked
                tab_index = self.notebook.index(f"@{event.x},{event.y}")
                self.notebook.select(tab_index)
                self._right_clicked_tab_index = tab_index
                self.tab_context_menu.tk_popup(event.x_root, event.y_root)
        except (tk.TclError, ValueError):
            pass

    def _detach_selected_tab(self):
        """Detach the right-clicked tab into its own Toplevel window."""
        try:
            idx = self._right_clicked_tab_index
        except AttributeError:
            return

        if idx < 0 or idx >= len(self.tabs):
            return

        tab_widget = self.tabs[idx]
        tab_name = self._tab_config[idx][1].strip()

        # Don't detach if already detached
        if tab_name in self._detached_windows:
            return

        # Remove from notebook
        self.notebook.forget(idx)

        # Create Toplevel
        window = tk.Toplevel(self.root)
        window.title(f"System Monitor - {tab_name}")
        window.geometry("850x650")
        window.configure(bg=COLORS["bg_dark"])

        # Reparent the tab widget
        tab_widget.pack_forget()
        tab_widget.pack(in_=window, fill="both", expand=True)

        self._detached_windows[tab_name] = {
            "window": window,
            "tab": tab_widget,
            "index": idx,
        }

        # On close, reattach
        window.protocol("WM_DELETE_WINDOW", lambda n=tab_name: self._reattach_tab(n))

    def _reattach_tab(self, tab_name):
        """Reattach a detached tab back to the notebook."""
        if tab_name not in self._detached_windows:
            return

        info = self._detached_windows.pop(tab_name)
        window = info["window"]
        tab_widget = info["tab"]
        original_idx = info["index"]

        # Reparent back to notebook
        tab_widget.pack_forget()

        # Insert at original position (or end if positions shifted)
        current_count = self.notebook.index("end")
        insert_idx = min(original_idx, current_count)

        self.notebook.insert(insert_idx, tab_widget, text=f"  {tab_name}  ")

        window.destroy()

    def _update_loop(self):
        """Periodic data refresh - update visible tab and detached windows."""
        try:
            # Always update status bar quick stats
            cpu_pct = psutil.cpu_percent(interval=0)
            mem_pct = psutil.virtual_memory().percent
            self.quick_cpu.config(text=f"CPU: {cpu_pct:.1f}%")
            self.quick_mem.config(text=f"RAM: {mem_pct:.1f}%")

            # Update the currently visible tab in the notebook
            if self.notebook.index("end") > 0:
                current_idx = self.notebook.index(self.notebook.select())
                # Find which tab widget is at this index
                current_tab_id = self.notebook.tabs()[current_idx]
                for tab in self.tabs:
                    if str(tab) == current_tab_id:
                        tab.update_data()
                        break

            # Update all detached tab windows
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
    """Entry point for the System Resource Monitor."""
    app = SystemMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
