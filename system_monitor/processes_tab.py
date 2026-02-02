"""Processes monitoring tab - process list with kill, detail view, sorting, and search."""

import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import os

from system_monitor.widgets import COLORS


def fmt_bytes(b):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


class ProcessDetailDialog(tk.Toplevel):
    """Dialog showing detailed information about a process."""

    def __init__(self, parent, pid):
        super().__init__(parent)
        self.title(f"Process Details - PID {pid}")
        self.geometry("700x600")
        self.configure(bg=COLORS["bg_dark"])
        self.transient(parent)

        self._pid = pid
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=COLORS["bg_medium"], padx=10, pady=8)
        header.pack(fill="x")

        self.header_label = tk.Label(
            header,
            text=f"PID {self._pid}",
            fg=COLORS["accent_blue"],
            bg=COLORS["bg_medium"],
            font=("Helvetica", 13, "bold"),
        )
        self.header_label.pack(side="left")

        # Close button
        tk.Button(
            header,
            text="Close",
            command=self.destroy,
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
            font=("Helvetica", 9),
            relief="flat",
            padx=10,
        ).pack(side="right")

        # Notebook for sections
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # -- General Info tab --
        self.general_frame = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(self.general_frame, text="  General  ")

        # -- Open Files tab --
        self.files_frame = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(self.files_frame, text="  Open Files  ")

        # -- Connections tab --
        self.connections_frame = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(self.connections_frame, text="  Connections  ")

        # -- Children tab --
        self.children_frame = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(self.children_frame, text="  Children  ")

        # -- Environment tab --
        self.env_frame = tk.Frame(self.notebook, bg=COLORS["bg_dark"])
        self.notebook.add(self.env_frame, text="  Environment  ")

    def _make_text_widget(self, parent):
        text = tk.Text(
            parent,
            bg=COLORS["bg_dark"],
            fg=COLORS["text_primary"],
            font=("Courier", 9),
            wrap="word",
            relief="flat",
            padx=10,
            pady=10,
            insertbackground=COLORS["text_primary"],
        )
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return text

    def _add_info_line(self, text_widget, label, value):
        text_widget.insert("end", f"{label}: ", "label")
        text_widget.insert("end", f"{value}\n", "value")

    def _load_data(self):
        try:
            proc = psutil.Process(self._pid)
            name = proc.name()
            self.header_label.config(text=f"PID {self._pid} - {name}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self.header_label.config(text=f"PID {self._pid} - Process not found or access denied")
            return

        # -- General Info --
        general_text = self._make_text_widget(self.general_frame)
        general_text.tag_configure("label", foreground=COLORS["text_secondary"], font=("Courier", 9, "bold"))
        general_text.tag_configure("value", foreground=COLORS["text_primary"])

        try:
            info_items = [
                ("Name", proc.name()),
                ("PID", str(proc.pid)),
                ("Status", proc.status()),
            ]

            try:
                info_items.append(("PPID", str(proc.ppid())))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                info_items.append(("PPID", "Access Denied"))

            try:
                info_items.append(("Username", proc.username()))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                info_items.append(("Username", "Access Denied"))

            try:
                import datetime
                create_time = datetime.datetime.fromtimestamp(proc.create_time())
                info_items.append(("Created", create_time.strftime("%Y-%m-%d %H:%M:%S")))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                info_items.append(("Created", "Access Denied"))

            try:
                info_items.append(("CPU %", f"{proc.cpu_percent(interval=0):.1f}%"))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            try:
                mem = proc.memory_info()
                info_items.append(("Memory RSS", fmt_bytes(mem.rss)))
                info_items.append(("Memory VMS", fmt_bytes(mem.vms)))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            try:
                info_items.append(("Memory %", f"{proc.memory_percent():.2f}%"))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            try:
                info_items.append(("Threads", str(proc.num_threads())))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            try:
                info_items.append(("Nice", str(proc.nice())))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            try:
                exe = proc.exe()
                info_items.append(("Executable", exe))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                info_items.append(("Executable", "Access Denied"))

            try:
                cwd = proc.cwd()
                info_items.append(("Working Dir", cwd))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                info_items.append(("Working Dir", "Access Denied"))

            try:
                cmdline = " ".join(proc.cmdline())
                info_items.append(("Command Line", cmdline or "N/A"))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                info_items.append(("Command Line", "Access Denied"))

            for label, value in info_items:
                self._add_info_line(general_text, f"  {label:<16}", value)

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            general_text.insert("end", f"Error reading process info: {e}")

        general_text.config(state="disabled")

        # -- Open Files --
        files_text = self._make_text_widget(self.files_frame)
        files_text.tag_configure("header", foreground=COLORS["accent_blue"], font=("Courier", 9, "bold"))
        try:
            open_files = proc.open_files()
            if open_files:
                files_text.insert("end", f"  {len(open_files)} open file(s):\n\n", "header")
                for f in open_files:
                    fd_str = f"  FD {f.fd:<4}" if hasattr(f, "fd") and f.fd >= 0 else "  FD  -- "
                    mode = getattr(f, "mode", "")
                    mode_str = f"  [{mode}]" if mode else ""
                    files_text.insert("end", f"{fd_str}  {f.path}{mode_str}\n")
            else:
                files_text.insert("end", "  No open files (or access denied)")
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            files_text.insert("end", "  Access denied - unable to read open files")
        files_text.config(state="disabled")

        # -- Connections --
        conn_text = self._make_text_widget(self.connections_frame)
        conn_text.tag_configure("header", foreground=COLORS["accent_blue"], font=("Courier", 9, "bold"))
        try:
            connections = proc.net_connections(kind="inet")
            if connections:
                conn_text.insert("end", f"  {len(connections)} connection(s):\n\n", "header")
                conn_text.insert("end", f"  {'Proto':<8}{'Local Address':<28}{'Remote Address':<28}{'Status'}\n")
                conn_text.insert("end", f"  {'─' * 80}\n")
                for c in connections:
                    proto = "TCP" if c.type == 1 else "UDP"
                    local = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "*:*"
                    remote = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "*:*"
                    conn_text.insert("end", f"  {proto:<8}{local:<28}{remote:<28}{c.status}\n")
            else:
                conn_text.insert("end", "  No active network connections")
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            conn_text.insert("end", "  Access denied - unable to read connections")
        conn_text.config(state="disabled")

        # -- Children --
        children_text = self._make_text_widget(self.children_frame)
        children_text.tag_configure("header", foreground=COLORS["accent_blue"], font=("Courier", 9, "bold"))
        try:
            children = proc.children(recursive=True)
            if children:
                children_text.insert("end", f"  {len(children)} child process(es):\n\n", "header")
                children_text.insert("end", f"  {'PID':<10}{'Name':<25}{'Status':<15}{'CPU %':<10}{'Mem %'}\n")
                children_text.insert("end", f"  {'─' * 70}\n")
                for child in children:
                    try:
                        children_text.insert(
                            "end",
                            f"  {child.pid:<10}{child.name():<25}{child.status():<15}"
                            f"{child.cpu_percent(interval=0):<10.1f}{child.memory_percent():.2f}%\n",
                        )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        children_text.insert("end", f"  {child.pid:<10}(process ended or access denied)\n")
            else:
                children_text.insert("end", "  No child processes")
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            children_text.insert("end", "  Access denied - unable to read children")
        children_text.config(state="disabled")

        # -- Environment --
        env_text = self._make_text_widget(self.env_frame)
        env_text.tag_configure("key", foreground=COLORS["accent_yellow"], font=("Courier", 9, "bold"))
        try:
            environ = proc.environ()
            if environ:
                for key in sorted(environ.keys()):
                    env_text.insert("end", f"  {key}", "key")
                    env_text.insert("end", f"={environ[key]}\n")
            else:
                env_text.insert("end", "  No environment variables (or access denied)")
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            env_text.insert("end", "  Access denied - unable to read environment variables")
        env_text.config(state="disabled")


class ProcessesTab(tk.Frame):
    """Process list with sorting, search, kill, and detail view."""

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

        # -- Right-click context menu --
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="View Details", command=self._view_details)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Terminate (SIGTERM)", command=self._terminate_process)
        self.context_menu.add_command(label="Kill (SIGKILL)", command=self._kill_process)

        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _on_right_click(self, event):
        """Show context menu on right-click."""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def _on_double_click(self, event):
        """Open detail view on double-click."""
        self._view_details()

    def _get_selected_pid(self):
        """Get PID of the currently selected process."""
        selection = self.tree.selection()
        if not selection:
            return None
        values = self.tree.item(selection[0], "values")
        if values:
            try:
                return int(values[0])
            except (ValueError, IndexError):
                return None
        return None

    def _view_details(self):
        """Open process detail dialog for selected process."""
        pid = self._get_selected_pid()
        if pid is not None:
            ProcessDetailDialog(self, pid)

    def _terminate_process(self):
        """Send SIGTERM to the selected process."""
        pid = self._get_selected_pid()
        if pid is None:
            return

        selection = self.tree.selection()
        name = self.tree.item(selection[0], "values")[1] if selection else str(pid)

        if not messagebox.askyesno(
            "Terminate Process",
            f"Terminate process '{name}' (PID {pid})?\n\n"
            "This sends SIGTERM, allowing the process to clean up.",
            parent=self,
        ):
            return

        try:
            proc = psutil.Process(pid)
            proc.terminate()
            messagebox.showinfo("Success", f"SIGTERM sent to PID {pid}", parent=self)
        except psutil.NoSuchProcess:
            messagebox.showwarning("Not Found", f"Process {pid} no longer exists.", parent=self)
        except psutil.AccessDenied:
            messagebox.showerror("Access Denied", f"Cannot terminate PID {pid} - permission denied.", parent=self)

    def _kill_process(self):
        """Send SIGKILL to the selected process."""
        pid = self._get_selected_pid()
        if pid is None:
            return

        selection = self.tree.selection()
        name = self.tree.item(selection[0], "values")[1] if selection else str(pid)

        if not messagebox.askyesno(
            "Kill Process",
            f"Force kill process '{name}' (PID {pid})?\n\n"
            "WARNING: This sends SIGKILL and will immediately end the process\n"
            "without allowing it to save data or clean up.",
            icon="warning",
            parent=self,
        ):
            return

        try:
            proc = psutil.Process(pid)
            proc.kill()
            messagebox.showinfo("Success", f"SIGKILL sent to PID {pid}", parent=self)
        except psutil.NoSuchProcess:
            messagebox.showwarning("Not Found", f"Process {pid} no longer exists.", parent=self)
        except psutil.AccessDenied:
            messagebox.showerror("Access Denied", f"Cannot kill PID {pid} - permission denied.", parent=self)

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
