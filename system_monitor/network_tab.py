"""Network monitoring tab - interfaces, bandwidth, connections, per-process usage, ping."""

import tkinter as tk
from tkinter import ttk
import psutil
import subprocess
import threading
import re
import time
from collections import deque

from system_monitor.widgets import (
    COLORS, LineChart, InfoRow, SectionHeader, ScrollableFrame,
)


def fmt_bytes(b):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def fmt_speed(b):
    """Format bytes/sec to human-readable speed."""
    for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB/s"


class NetworkTab(tk.Frame):
    """Network interface monitoring, bandwidth tracking, per-process usage, and ping."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._prev_counters = None
        self._prev_per_iface = None
        self._ping_target = "8.8.8.8"
        self._ping_running = False
        self._ping_results = deque(maxlen=60)
        self._proc_net_counter = 0
        self._build_ui()

    def _build_ui(self):
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        container = scroll.scrollable_frame

        # -- Bandwidth Chart --
        chart_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        chart_frame.pack(fill="x", padx=10, pady=10)

        SectionHeader(chart_frame, text="Network Bandwidth").pack(fill="x", pady=(0, 5))

        self.bandwidth_chart = LineChart(
            chart_frame,
            width=750,
            height=160,
            max_points=60,
            y_min=0,
            y_max=1024 * 100,
            y_label="B/s",
            series_colors=[COLORS["accent_green"], COLORS["accent"]],
            series_labels=["Download", "Upload"],
        )
        self.bandwidth_chart.pack(fill="x")

        # -- Overall Stats --
        stats_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        stats_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(stats_frame, text="Overall Network I/O").pack(fill="x", pady=(0, 5))

        self.overall_info = {}
        for key, label in [
            ("bytes_sent", "Total Sent"),
            ("bytes_recv", "Total Received"),
            ("packets_sent", "Packets Sent"),
            ("packets_recv", "Packets Received"),
            ("errin", "Errors In"),
            ("errout", "Errors Out"),
            ("dropin", "Dropped In"),
            ("dropout", "Dropped Out"),
            ("download_speed", "Download Speed"),
            ("upload_speed", "Upload Speed"),
        ]:
            row = InfoRow(stats_frame, label)
            row.pack(fill="x", pady=1)
            self.overall_info[key] = row

        # -- Ping / Latency Monitor --
        ping_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        ping_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(ping_frame, text="Ping / Latency Monitor").pack(fill="x", pady=(0, 5))

        # Ping controls
        ping_controls = tk.Frame(ping_frame, bg=COLORS["bg_dark"])
        ping_controls.pack(fill="x", pady=(0, 5))

        tk.Label(
            ping_controls,
            text="Target:",
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_dark"],
            font=("Helvetica", 9),
        ).pack(side="left")

        self.ping_entry_var = tk.StringVar(value=self._ping_target)
        ping_entry = tk.Entry(
            ping_controls,
            textvariable=self.ping_entry_var,
            bg=COLORS["bg_medium"],
            fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
            font=("Helvetica", 9),
            width=25,
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        ping_entry.pack(side="left", padx=(5, 10))

        self.ping_btn = tk.Button(
            ping_controls,
            text="Start Ping",
            command=self._toggle_ping,
            bg=COLORS["accent_green"],
            fg="#ffffff",
            font=("Helvetica", 9),
            relief="flat",
            padx=10,
            pady=2,
        )
        self.ping_btn.pack(side="left")

        # Quick preset buttons
        for target, label in [("8.8.8.8", "Google DNS"), ("1.1.1.1", "Cloudflare"),
                               ("208.67.222.222", "OpenDNS")]:
            tk.Button(
                ping_controls,
                text=label,
                command=lambda t=target: self._set_ping_target(t),
                bg=COLORS["bg_light"],
                fg=COLORS["text_primary"],
                font=("Helvetica", 8),
                relief="flat",
                padx=6,
                pady=1,
            ).pack(side="left", padx=2)

        # Ping stats
        ping_stats = tk.Frame(ping_frame, bg=COLORS["bg_dark"])
        ping_stats.pack(fill="x", pady=(0, 5))

        self.ping_info = {}
        for key, label in [
            ("last", "Last Ping"),
            ("avg", "Average"),
            ("min", "Minimum"),
            ("max", "Maximum"),
            ("loss", "Packet Loss"),
        ]:
            row = InfoRow(ping_stats, label)
            row.pack(fill="x", pady=1)
            self.ping_info[key] = row

        # Ping chart
        self.ping_chart = LineChart(
            ping_frame,
            width=750,
            height=120,
            max_points=60,
            y_min=0,
            y_max=100,
            y_label="ms",
            series_colors=[COLORS["accent_blue"]],
            series_labels=["Latency"],
        )
        self.ping_chart.pack(fill="x")

        # -- Per-Process Network Usage --
        proc_net_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        proc_net_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(proc_net_frame, text="Per-Process Network Connections").pack(fill="x", pady=(0, 5))

        # Treeview for process connections
        tree_frame = tk.Frame(proc_net_frame, bg=COLORS["bg_dark"])
        tree_frame.pack(fill="x")

        columns = ("pid", "name", "connections", "local", "remote", "status")
        self.proc_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Proc.Treeview",
            selectmode="browse",
            height=10,
        )

        headings = {
            "pid": ("PID", 60),
            "name": ("Process", 150),
            "connections": ("# Conns", 70),
            "local": ("Local Address", 180),
            "remote": ("Remote Address", 180),
            "status": ("Status", 100),
        }

        for col, (text, width) in headings.items():
            self.proc_tree.heading(col, text=text)
            self.proc_tree.column(col, width=width, minwidth=40)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.proc_tree.yview)
        self.proc_tree.configure(yscrollcommand=scrollbar.set)
        self.proc_tree.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

        # -- Network Interfaces --
        iface_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        iface_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(iface_frame, text="Network Interfaces").pack(fill="x", pady=(0, 5))

        self.iface_container = tk.Frame(iface_frame, bg=COLORS["bg_dark"])
        self.iface_container.pack(fill="x")

        self.iface_widgets = {}
        self._build_interfaces()

        # -- Connections Summary --
        conn_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        conn_frame.pack(fill="x", padx=10, pady=(5, 15))

        SectionHeader(conn_frame, text="Connection Summary").pack(fill="x", pady=(0, 5))

        self.conn_info = {}
        for key, label in [
            ("total", "Total Connections"),
            ("established", "Established"),
            ("listen", "Listening"),
            ("time_wait", "Time Wait"),
            ("close_wait", "Close Wait"),
        ]:
            row = InfoRow(conn_frame, label)
            row.pack(fill="x", pady=1)
            self.conn_info[key] = row

    def _build_interfaces(self):
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for iface_name in sorted(addrs.keys()):
            frame = tk.Frame(self.iface_container, bg=COLORS["bg_medium"], padx=10, pady=8)
            frame.pack(fill="x", pady=3)

            # Interface header
            header = tk.Frame(frame, bg=COLORS["bg_medium"])
            header.pack(fill="x")

            iface_stat = stats.get(iface_name)
            status = "UP" if iface_stat and iface_stat.isup else "DOWN"
            status_color = COLORS["accent_green"] if status == "UP" else COLORS["accent"]

            tk.Label(
                header,
                text=f"{iface_name}",
                fg=COLORS["text_primary"],
                bg=COLORS["bg_medium"],
                font=("Helvetica", 10, "bold"),
            ).pack(side="left")

            tk.Label(
                header,
                text=f"  [{status}]",
                fg=status_color,
                bg=COLORS["bg_medium"],
                font=("Helvetica", 9, "bold"),
            ).pack(side="left")

            if iface_stat:
                speed_text = f"  {iface_stat.speed} Mbps" if iface_stat.speed > 0 else ""
                mtu_text = f"  MTU: {iface_stat.mtu}"
                tk.Label(
                    header,
                    text=f"{speed_text}{mtu_text}",
                    fg=COLORS["text_dim"],
                    bg=COLORS["bg_medium"],
                    font=("Helvetica", 9),
                ).pack(side="left")

            # Addresses
            detail_frame = tk.Frame(frame, bg=COLORS["bg_medium"])
            detail_frame.pack(fill="x", pady=(4, 0))

            for addr in addrs[iface_name]:
                family_name = str(addr.family).split(".")[-1]
                tk.Label(
                    detail_frame,
                    text=f"{family_name}: {addr.address}",
                    fg=COLORS["text_secondary"],
                    bg=COLORS["bg_medium"],
                    font=("Helvetica", 9),
                    anchor="w",
                ).pack(fill="x")

            # Speed labels for this interface
            speed_frame = tk.Frame(frame, bg=COLORS["bg_medium"])
            speed_frame.pack(fill="x", pady=(4, 0))

            sent_label = tk.Label(
                speed_frame, text="Sent: ...", fg=COLORS["text_dim"],
                bg=COLORS["bg_medium"], font=("Helvetica", 9),
            )
            sent_label.pack(side="left", padx=(0, 15))

            recv_label = tk.Label(
                speed_frame, text="Recv: ...", fg=COLORS["text_dim"],
                bg=COLORS["bg_medium"], font=("Helvetica", 9),
            )
            recv_label.pack(side="left")

            self.iface_widgets[iface_name] = {
                "sent_label": sent_label,
                "recv_label": recv_label,
            }

    def _set_ping_target(self, target):
        """Set a new ping target."""
        self.ping_entry_var.set(target)
        self._ping_target = target

    def _toggle_ping(self):
        """Start or stop pinging."""
        if self._ping_running:
            self._ping_running = False
            self.ping_btn.config(text="Start Ping", bg=COLORS["accent_green"])
        else:
            self._ping_target = self.ping_entry_var.get().strip()
            if not self._ping_target:
                return
            self._ping_running = True
            self._ping_results.clear()
            self.ping_btn.config(text="Stop Ping", bg=COLORS["accent"])
            self._ping_once()

    def _ping_once(self):
        """Execute a single ping in a background thread."""
        if not self._ping_running:
            return

        def do_ping():
            try:
                cmd = ["ping", "-c", "1", "-W", "2", self._ping_target]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                match = re.search(r"time[=<](\d+\.?\d*)", result.stdout)
                if match:
                    latency = float(match.group(1))
                    self._ping_results.append(("ok", latency))
                else:
                    self._ping_results.append(("fail", 0))
            except Exception:
                self._ping_results.append(("fail", 0))

        thread = threading.Thread(target=do_ping, daemon=True)
        thread.start()

    def _update_ping_display(self):
        """Update ping statistics and chart."""
        if not self._ping_results:
            return

        results = list(self._ping_results)
        ok_results = [r[1] for r in results if r[0] == "ok"]
        fail_count = sum(1 for r in results if r[0] == "fail")
        total = len(results)

        last = results[-1]
        if last[0] == "ok":
            self.ping_info["last"].set_value(f"{last[1]:.1f} ms")
            self.ping_chart.add_point(last[1])
        else:
            self.ping_info["last"].set_value("Timeout")
            self.ping_chart.add_point(0)

        if ok_results:
            avg = sum(ok_results) / len(ok_results)
            self.ping_info["avg"].set_value(f"{avg:.1f} ms")
            self.ping_info["min"].set_value(f"{min(ok_results):.1f} ms")
            self.ping_info["max"].set_value(f"{max(ok_results):.1f} ms")

            # Auto-scale ping chart
            max_lat = max(ok_results)
            if max_lat > self.ping_chart.y_max * 0.8 or max_lat < self.ping_chart.y_max * 0.3:
                self.ping_chart.set_y_range(0, max(max_lat * 1.5, 10))

        loss_pct = (fail_count / total * 100) if total > 0 else 0
        self.ping_info["loss"].set_value(f"{loss_pct:.1f}% ({fail_count}/{total})")

    def _update_per_process_network(self):
        """Update per-process network connections."""
        proc_connections = {}
        try:
            connections = psutil.net_connections(kind="inet")
            for conn in connections:
                pid = conn.pid
                if pid is None or pid == 0:
                    continue

                if pid not in proc_connections:
                    proc_connections[pid] = {
                        "pid": pid,
                        "name": "",
                        "connections": [],
                    }
                proc_connections[pid]["connections"].append(conn)
        except (psutil.AccessDenied, Exception):
            return

        # Get process names
        for pid, data in proc_connections.items():
            try:
                proc = psutil.Process(pid)
                data["name"] = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                data["name"] = f"<PID {pid}>"

        # Sort by number of connections
        sorted_procs = sorted(proc_connections.values(), key=lambda x: len(x["connections"]), reverse=True)

        self.proc_tree.delete(*self.proc_tree.get_children())

        for proc_data in sorted_procs[:50]:
            conns = proc_data["connections"]
            first_conn = conns[0] if conns else None

            local = ""
            remote = ""
            status = ""
            if first_conn:
                local = f"{first_conn.laddr.ip}:{first_conn.laddr.port}" if first_conn.laddr else "*:*"
                remote = f"{first_conn.raddr.ip}:{first_conn.raddr.port}" if first_conn.raddr else "*:*"
                status = first_conn.status

            parent_id = self.proc_tree.insert("", "end", values=(
                proc_data["pid"],
                proc_data["name"],
                len(conns),
                local,
                remote,
                status,
            ))

            # Add child rows for additional connections
            if len(conns) > 1:
                for conn in conns[1:]:
                    c_local = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "*:*"
                    c_remote = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "*:*"
                    self.proc_tree.insert(parent_id, "end", values=(
                        "",
                        "",
                        "",
                        c_local,
                        c_remote,
                        conn.status,
                    ))

    def update_data(self):
        """Refresh network data."""
        counters = psutil.net_io_counters()

        self.overall_info["bytes_sent"].set_value(fmt_bytes(counters.bytes_sent))
        self.overall_info["bytes_recv"].set_value(fmt_bytes(counters.bytes_recv))
        self.overall_info["packets_sent"].set_value(f"{counters.packets_sent:,}")
        self.overall_info["packets_recv"].set_value(f"{counters.packets_recv:,}")
        self.overall_info["errin"].set_value(f"{counters.errin:,}")
        self.overall_info["errout"].set_value(f"{counters.errout:,}")
        self.overall_info["dropin"].set_value(f"{counters.dropin:,}")
        self.overall_info["dropout"].set_value(f"{counters.dropout:,}")

        if self._prev_counters:
            dl_speed = counters.bytes_recv - self._prev_counters.bytes_recv
            ul_speed = counters.bytes_sent - self._prev_counters.bytes_sent
            self.overall_info["download_speed"].set_value(fmt_speed(dl_speed))
            self.overall_info["upload_speed"].set_value(fmt_speed(ul_speed))

            max_val = max(dl_speed, ul_speed, 1024)
            current_max = self.bandwidth_chart.y_max
            if max_val > current_max * 0.9 or max_val < current_max * 0.3:
                self.bandwidth_chart.set_y_range(0, max(max_val * 1.3, 1024))

            self.bandwidth_chart.add_points([dl_speed, ul_speed])

        self._prev_counters = counters

        # Per-interface counters
        try:
            per_iface = psutil.net_io_counters(pernic=True)
            for name, widgets in self.iface_widgets.items():
                if name in per_iface:
                    c = per_iface[name]
                    if self._prev_per_iface and name in self._prev_per_iface:
                        prev = self._prev_per_iface[name]
                        s_speed = c.bytes_sent - prev.bytes_sent
                        r_speed = c.bytes_recv - prev.bytes_recv
                        widgets["sent_label"].config(text=f"Sent: {fmt_bytes(c.bytes_sent)} ({fmt_speed(s_speed)})")
                        widgets["recv_label"].config(text=f"Recv: {fmt_bytes(c.bytes_recv)} ({fmt_speed(r_speed)})")
                    else:
                        widgets["sent_label"].config(text=f"Sent: {fmt_bytes(c.bytes_sent)}")
                        widgets["recv_label"].config(text=f"Recv: {fmt_bytes(c.bytes_recv)}")
            self._prev_per_iface = per_iface
        except Exception:
            pass

        # Connections summary
        try:
            conns = psutil.net_connections(kind="inet")
            status_counts = {}
            for conn in conns:
                s = conn.status
                status_counts[s] = status_counts.get(s, 0) + 1

            self.conn_info["total"].set_value(str(len(conns)))
            self.conn_info["established"].set_value(str(status_counts.get("ESTABLISHED", 0)))
            self.conn_info["listen"].set_value(str(status_counts.get("LISTEN", 0)))
            self.conn_info["time_wait"].set_value(str(status_counts.get("TIME_WAIT", 0)))
            self.conn_info["close_wait"].set_value(str(status_counts.get("CLOSE_WAIT", 0)))
        except (psutil.AccessDenied, Exception):
            self.conn_info["total"].set_value("Access Denied")

        # Per-process network (every 5 updates to reduce overhead)
        self._proc_net_counter += 1
        if self._proc_net_counter >= 5:
            self._proc_net_counter = 0
            self._update_per_process_network()

        # Ping
        if self._ping_running:
            self._update_ping_display()
            self._ping_once()
