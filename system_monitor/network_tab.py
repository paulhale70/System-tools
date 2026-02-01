"""Network monitoring tab - interfaces, bandwidth, and connections."""

import tkinter as tk
from tkinter import ttk
import psutil

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
    """Network interface monitoring and bandwidth tracking."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._prev_counters = None
        self._prev_per_iface = None
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

        # Connections
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
