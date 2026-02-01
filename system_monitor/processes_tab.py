"""Processes monitoring tab - running process list with sorting and details."""

import tkinter as tk
from tkinter import ttk
import psutil

from system_monitor.widgets import COLORS


def fmt_bytes(b):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


class ProcessesTab(tk.Frame):
    """Process list with sorting, search, and resource usage."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._sort_col = "cpu_percent"
        self._sort_reverse = True
        self._search_text = ""
        self._build_ui()

    def _build_ui(self):
        # -- Top bar: search + info --
        top_bar = tk.Frame(self, bg=COLORS["bg_medium"], padx=10, pady=8)
        top_bar.pack(fill="x")

        tk.Label(
            top_bar,
            text="Search:",
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 10),
        ).pack(side="left")

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        search_entry = tk.Entry(
            top_bar,
            textvariable=self.search_var,
            bg=COLORS["bg_dark"],
            fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
            font=("Helvetica", 10),
            width=30,
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent_blue"],
        )
        search_entry.pack(side="left", padx=(5, 15))

        self.process_count_label = tk.Label(
            top_bar,
            text="Processes: ...",
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 10),
        )
        self.process_count_label.pack(side="left")

        # Sort dropdown
        tk.Label(
            top_bar,
            text="Sort by:",
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 10),
        ).pack(side="left", padx=(20, 5))

        self.sort_var = tk.StringVar(value="CPU %")
        sort_menu = ttk.Combobox(
            top_bar,
            textvariable=self.sort_var,
            values=["CPU %", "Memory %", "Memory (RSS)", "PID", "Name"],
            state="readonly",
            width=15,
        )
        sort_menu.pack(side="left")
        sort_menu.bind("<<ComboboxSelected>>", self._on_sort_change)

        # -- Treeview for process list --
        tree_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        style = ttk.Style()
        style.configure(
            "Proc.Treeview",
            background=COLORS["bg_dark"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_dark"],
            borderwidth=0,
            font=("Helvetica", 9),
            rowheight=24,
        )
        style.configure(
            "Proc.Treeview.Heading",
            background=COLORS["bg_medium"],
            foreground=COLORS["text_primary"],
            font=("Helvetica", 9, "bold"),
            borderwidth=1,
            relief="flat",
        )
        style.map(
            "Proc.Treeview",
            background=[("selected", COLORS["bg_light"])],
            foreground=[("selected", COLORS["text_primary"])],
        )

        columns = ("pid", "name", "status", "cpu", "mem_pct", "mem_rss", "threads", "user")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Proc.Treeview",
            selectmode="browse",
        )

        headings = {
            "pid": ("PID", 70),
            "name": ("Name", 200),
            "status": ("Status", 80),
            "cpu": ("CPU %", 80),
            "mem_pct": ("Mem %", 80),
            "mem_rss": ("Mem (RSS)", 100),
            "threads": ("Threads", 70),
            "user": ("User", 120),
        }

        for col, (text, width) in headings.items():
            self.tree.heading(col, text=text, command=lambda c=col: self._sort_by_column(c))
            self.tree.column(col, width=width, minwidth=50)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _on_search_change(self, *args):
        self._search_text = self.search_var.get().lower()

    def _on_sort_change(self, event=None):
        sort_map = {
            "CPU %": "cpu_percent",
            "Memory %": "mem_percent",
            "Memory (RSS)": "mem_rss",
            "PID": "pid",
            "Name": "name",
        }
        self._sort_col = sort_map.get(self.sort_var.get(), "cpu_percent")
        self._sort_reverse = self._sort_col not in ("pid", "name")

    def _sort_by_column(self, col):
        col_map = {
            "pid": "pid",
            "name": "name",
            "status": "status",
            "cpu": "cpu_percent",
            "mem_pct": "mem_percent",
            "mem_rss": "mem_rss",
            "threads": "threads",
            "user": "user",
        }
        new_sort = col_map.get(col, "cpu_percent")
        if self._sort_col == new_sort:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = new_sort
            self._sort_reverse = new_sort not in ("pid", "name", "status", "user")

    def update_data(self):
        """Refresh process list."""
        procs = []
        for p in psutil.process_iter(
            ["pid", "name", "status", "cpu_percent", "memory_percent",
             "memory_info", "num_threads", "username"]
        ):
            try:
                info = p.info
                name = info.get("name", "") or ""
                if self._search_text and self._search_text not in name.lower():
                    pid_str = str(info.get("pid", ""))
                    user = (info.get("username", "") or "").lower()
                    if self._search_text not in pid_str and self._search_text not in user:
                        continue

                mem_info = info.get("memory_info")
                rss = mem_info.rss if mem_info else 0

                procs.append({
                    "pid": info.get("pid", 0),
                    "name": name,
                    "status": info.get("status", ""),
                    "cpu_percent": info.get("cpu_percent", 0) or 0,
                    "mem_percent": info.get("memory_percent", 0) or 0,
                    "mem_rss": rss,
                    "threads": info.get("num_threads", 0) or 0,
                    "user": info.get("username", "") or "",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort
        try:
            procs.sort(key=lambda x: x.get(self._sort_col, 0) or 0, reverse=self._sort_reverse)
        except TypeError:
            procs.sort(key=lambda x: str(x.get(self._sort_col, "")), reverse=self._sort_reverse)

        self.process_count_label.config(text=f"Processes: {len(procs)}")

        # Update treeview
        self.tree.delete(*self.tree.get_children())

        for proc in procs[:200]:  # Limit display to top 200
            self.tree.insert("", "end", values=(
                proc["pid"],
                proc["name"],
                proc["status"],
                f"{proc['cpu_percent']:.1f}",
                f"{proc['mem_percent']:.1f}",
                fmt_bytes(proc["mem_rss"]),
                proc["threads"],
                proc["user"],
            ))
