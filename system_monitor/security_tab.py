"""Security tab - open ports scanner and process anomaly detection."""

import tkinter as tk
from tkinter import ttk
import psutil
import time

from system_monitor.widgets import (
    COLORS, InfoRow, SectionHeader, ScrollableFrame,
)


# Well-known services by port
KNOWN_SERVICES = {
    22: "SSH", 53: "DNS", 80: "HTTP", 443: "HTTPS",
    3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis",
    8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB",
    5672: "RabbitMQ", 9200: "Elasticsearch", 11211: "Memcached",
    25: "SMTP", 110: "POP3", 143: "IMAP", 993: "IMAPS",
    995: "POP3S", 587: "SMTP-TLS", 21: "FTP", 23: "Telnet",
    3389: "RDP", 5900: "VNC", 8888: "Jupyter",
}

# Default anomaly thresholds
ANOMALY_CPU_THRESHOLD = 80.0  # Flag processes above this CPU %
ANOMALY_MEM_THRESHOLD = 50.0  # Flag processes above this memory %


class SecurityTab(tk.Frame):
    """Security monitoring - open ports and process anomaly detection."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._scan_counter = 0
        self._known_processes = set()  # Whitelist of known process names
        self._anomaly_cpu = ANOMALY_CPU_THRESHOLD
        self._anomaly_mem = ANOMALY_MEM_THRESHOLD
        self._build_ui()

    def _build_ui(self):
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        container = scroll.scrollable_frame

        # -- Open Ports Scanner --
        ports_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        ports_frame.pack(fill="x", padx=10, pady=10)

        SectionHeader(ports_frame, text="Open / Listening Ports").pack(fill="x", pady=(0, 5))

        self.ports_summary = tk.Label(
            ports_frame,
            text="Scanning...",
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_dark"],
            font=("Helvetica", 9),
            anchor="w",
        )
        self.ports_summary.pack(fill="x", pady=(0, 5))

        # Ports treeview
        ports_tree_frame = tk.Frame(ports_frame, bg=COLORS["bg_dark"])
        ports_tree_frame.pack(fill="x")

        columns = ("port", "protocol", "address", "pid", "process", "service", "risk")
        self.ports_tree = ttk.Treeview(
            ports_tree_frame,
            columns=columns,
            show="headings",
            style="Proc.Treeview",
            selectmode="browse",
            height=12,
        )

        headings = {
            "port": ("Port", 70),
            "protocol": ("Proto", 60),
            "address": ("Bind Address", 140),
            "pid": ("PID", 60),
            "process": ("Process", 150),
            "service": ("Service", 100),
            "risk": ("Risk Level", 100),
        }

        for col, (text, width) in headings.items():
            self.ports_tree.heading(col, text=text)
            self.ports_tree.column(col, width=width, minwidth=40)

        scrollbar = ttk.Scrollbar(ports_tree_frame, orient="vertical", command=self.ports_tree.yview)
        self.ports_tree.configure(yscrollcommand=scrollbar.set)
        self.ports_tree.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Risk legend
        legend_frame = tk.Frame(ports_frame, bg=COLORS["bg_dark"])
        legend_frame.pack(fill="x", pady=(5, 0))

        for text, color in [
            ("Low Risk (known service)", COLORS["accent_green"]),
            ("Medium Risk (high port, known process)", COLORS["accent_yellow"]),
            ("High Risk (unexpected port/process)", COLORS["accent_orange"]),
        ]:
            dot = tk.Canvas(legend_frame, width=10, height=10, bg=COLORS["bg_dark"], highlightthickness=0)
            dot.create_oval(1, 1, 9, 9, fill=color, outline="")
            dot.pack(side="left", padx=(10, 3))
            tk.Label(
                legend_frame, text=text, fg=COLORS["text_dim"],
                bg=COLORS["bg_dark"], font=("Helvetica", 8),
            ).pack(side="left", padx=(0, 10))

        # -- Process Anomaly Detection --
        anomaly_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        anomaly_frame.pack(fill="x", padx=10, pady=(15, 5))

        SectionHeader(anomaly_frame, text="Process Anomaly Detection").pack(fill="x", pady=(0, 5))

        # Threshold controls
        controls = tk.Frame(anomaly_frame, bg=COLORS["bg_dark"])
        controls.pack(fill="x", pady=(0, 5))

        tk.Label(
            controls, text="CPU threshold:", fg=COLORS["text_secondary"],
            bg=COLORS["bg_dark"], font=("Helvetica", 9),
        ).pack(side="left")

        self.cpu_threshold_var = tk.IntVar(value=int(self._anomaly_cpu))
        self.cpu_threshold_label = tk.Label(
            controls, text=f"{int(self._anomaly_cpu)}%",
            fg=COLORS["accent_yellow"], bg=COLORS["bg_dark"],
            font=("Helvetica", 9, "bold"), width=5,
        )

        cpu_slider = tk.Scale(
            controls, from_=10, to=100, orient="horizontal",
            variable=self.cpu_threshold_var,
            command=self._on_cpu_threshold_change,
            bg=COLORS["bg_dark"], fg=COLORS["text_dim"],
            troughcolor=COLORS["bg_medium"], highlightthickness=0,
            font=("Helvetica", 7), showvalue=False, sliderlength=12, width=8, length=100,
        )
        cpu_slider.pack(side="left", padx=3)
        self.cpu_threshold_label.pack(side="left", padx=(0, 15))

        tk.Label(
            controls, text="Memory threshold:", fg=COLORS["text_secondary"],
            bg=COLORS["bg_dark"], font=("Helvetica", 9),
        ).pack(side="left")

        self.mem_threshold_var = tk.IntVar(value=int(self._anomaly_mem))
        self.mem_threshold_label = tk.Label(
            controls, text=f"{int(self._anomaly_mem)}%",
            fg=COLORS["accent_yellow"], bg=COLORS["bg_dark"],
            font=("Helvetica", 9, "bold"), width=5,
        )

        mem_slider = tk.Scale(
            controls, from_=5, to=100, orient="horizontal",
            variable=self.mem_threshold_var,
            command=self._on_mem_threshold_change,
            bg=COLORS["bg_dark"], fg=COLORS["text_dim"],
            troughcolor=COLORS["bg_medium"], highlightthickness=0,
            font=("Helvetica", 7), showvalue=False, sliderlength=12, width=8, length=100,
        )
        mem_slider.pack(side="left", padx=3)
        self.mem_threshold_label.pack(side="left", padx=(0, 15))

        # Whitelist button
        self.whitelist_btn = tk.Button(
            controls,
            text="Learn Current as Normal",
            command=self._learn_whitelist,
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
            font=("Helvetica", 8),
            relief="flat",
            padx=8,
        )
        self.whitelist_btn.pack(side="left")

        self.whitelist_label = tk.Label(
            controls, text="", fg=COLORS["text_dim"],
            bg=COLORS["bg_dark"], font=("Helvetica", 8),
        )
        self.whitelist_label.pack(side="left", padx=5)

        # Anomaly info
        self.anomaly_summary = tk.Label(
            anomaly_frame,
            text="",
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_dark"],
            font=("Helvetica", 9),
            anchor="w",
        )
        self.anomaly_summary.pack(fill="x", pady=(0, 5))

        # Anomaly treeview
        anomaly_tree_frame = tk.Frame(anomaly_frame, bg=COLORS["bg_dark"])
        anomaly_tree_frame.pack(fill="x")

        columns = ("pid", "name", "cpu", "mem", "user", "reason")
        self.anomaly_tree = ttk.Treeview(
            anomaly_tree_frame,
            columns=columns,
            show="headings",
            style="Proc.Treeview",
            selectmode="browse",
            height=10,
        )

        headings = {
            "pid": ("PID", 60),
            "name": ("Process", 160),
            "cpu": ("CPU %", 80),
            "mem": ("Mem %", 80),
            "user": ("User", 120),
            "reason": ("Anomaly Reason", 250),
        }

        for col, (text, width) in headings.items():
            self.anomaly_tree.heading(col, text=text)
            self.anomaly_tree.column(col, width=width, minwidth=40)

        scrollbar2 = ttk.Scrollbar(anomaly_tree_frame, orient="vertical", command=self.anomaly_tree.yview)
        self.anomaly_tree.configure(yscrollcommand=scrollbar2.set)
        self.anomaly_tree.pack(side="left", fill="x", expand=True)
        scrollbar2.pack(side="right", fill="y")

    def _on_cpu_threshold_change(self, val):
        self._anomaly_cpu = float(val)
        self.cpu_threshold_label.config(text=f"{int(self._anomaly_cpu)}%")

    def _on_mem_threshold_change(self, val):
        self._anomaly_mem = float(val)
        self.mem_threshold_label.config(text=f"{int(self._anomaly_mem)}%")

    def _learn_whitelist(self):
        """Learn current running processes as normal/known."""
        self._known_processes.clear()
        for p in psutil.process_iter(["name"]):
            try:
                name = p.info.get("name")
                if name:
                    self._known_processes.add(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        count = len(self._known_processes)
        self.whitelist_label.config(text=f"Learned {count} processes")

    def _assess_port_risk(self, port, address, process_name):
        """Assess risk level of an open port."""
        # Known service on standard port
        if port in KNOWN_SERVICES:
            return "Low", COLORS["accent_green"]

        # System ports (< 1024) without known service
        if port < 1024:
            return "High", COLORS["accent_orange"]

        # Well-known process on high port
        known_procs = {"python", "node", "java", "nginx", "apache", "httpd",
                       "postgres", "mysql", "redis", "mongod", "sshd"}
        if process_name.lower() in known_procs:
            return "Medium", COLORS["accent_yellow"]

        # Bound to all interfaces (0.0.0.0)
        if address in ("0.0.0.0", "::"):
            return "Medium", COLORS["accent_yellow"]

        # Localhost only
        if address in ("127.0.0.1", "::1"):
            return "Low", COLORS["accent_green"]

        return "Medium", COLORS["accent_yellow"]

    def _scan_ports(self):
        """Scan for listening ports."""
        listening = []
        try:
            connections = psutil.net_connections(kind="inet")
            for conn in connections:
                if conn.status == "LISTEN" and conn.laddr:
                    proc_name = ""
                    if conn.pid:
                        try:
                            proc_name = psutil.Process(conn.pid).name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            proc_name = f"<PID {conn.pid}>"

                    port = conn.laddr.port
                    address = conn.laddr.ip
                    service = KNOWN_SERVICES.get(port, "Unknown")
                    proto = "TCP"
                    risk_level, risk_color = self._assess_port_risk(port, address, proc_name)

                    listening.append({
                        "port": port,
                        "protocol": proto,
                        "address": address,
                        "pid": conn.pid or 0,
                        "process": proc_name,
                        "service": service,
                        "risk": risk_level,
                        "risk_color": risk_color,
                    })
        except (psutil.AccessDenied, Exception):
            pass

        # Also check UDP
        try:
            for conn in psutil.net_connections(kind="udp"):
                if conn.laddr and not conn.raddr:
                    proc_name = ""
                    if conn.pid:
                        try:
                            proc_name = psutil.Process(conn.pid).name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    port = conn.laddr.port
                    address = conn.laddr.ip
                    service = KNOWN_SERVICES.get(port, "Unknown")
                    risk_level, risk_color = self._assess_port_risk(port, address, proc_name)

                    listening.append({
                        "port": port,
                        "protocol": "UDP",
                        "address": address,
                        "pid": conn.pid or 0,
                        "process": proc_name,
                        "service": service,
                        "risk": risk_level,
                        "risk_color": risk_color,
                    })
        except Exception:
            pass

        # Sort by port
        listening.sort(key=lambda x: x["port"])
        return listening

    def _detect_anomalies(self):
        """Detect processes with abnormal resource usage."""
        anomalies = []

        for p in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent", "username"]
        ):
            try:
                info = p.info
                name = info.get("name", "") or ""
                cpu_pct = info.get("cpu_percent", 0) or 0
                mem_pct = info.get("memory_percent", 0) or 0
                user = info.get("username", "") or ""
                pid = info.get("pid", 0)

                reasons = []

                # High CPU
                if cpu_pct >= self._anomaly_cpu:
                    reasons.append(f"High CPU: {cpu_pct:.1f}%")

                # High memory
                if mem_pct >= self._anomaly_mem:
                    reasons.append(f"High Memory: {mem_pct:.1f}%")

                # Unknown process (not in whitelist) with significant resource use
                if self._known_processes and name not in self._known_processes:
                    if cpu_pct > 5 or mem_pct > 5:
                        reasons.append("Unknown process (not in whitelist)")

                if reasons:
                    anomalies.append({
                        "pid": pid,
                        "name": name,
                        "cpu": cpu_pct,
                        "mem": mem_pct,
                        "user": user,
                        "reason": "; ".join(reasons),
                    })

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by CPU usage
        anomalies.sort(key=lambda x: x["cpu"], reverse=True)
        return anomalies

    def update_data(self):
        """Refresh security data."""
        # Scan ports every 10 updates
        self._scan_counter += 1
        if self._scan_counter >= 10 or self._scan_counter == 1:
            self._scan_counter = 1
            ports = self._scan_ports()

            self.ports_tree.delete(*self.ports_tree.get_children())

            high_risk = sum(1 for p in ports if p["risk"] == "High")
            medium_risk = sum(1 for p in ports if p["risk"] == "Medium")

            self.ports_summary.config(
                text=f"{len(ports)} listening port(s) | "
                     f"{high_risk} high risk | {medium_risk} medium risk"
            )

            for port_info in ports:
                item_id = self.ports_tree.insert("", "end", values=(
                    port_info["port"],
                    port_info["protocol"],
                    port_info["address"],
                    port_info["pid"],
                    port_info["process"],
                    port_info["service"],
                    port_info["risk"],
                ))

        # Anomaly detection (every update)
        anomalies = self._detect_anomalies()

        self.anomaly_tree.delete(*self.anomaly_tree.get_children())

        if anomalies:
            self.anomaly_summary.config(
                text=f"{len(anomalies)} anomalous process(es) detected",
                fg=COLORS["accent_orange"],
            )
        else:
            self.anomaly_summary.config(
                text="No anomalies detected",
                fg=COLORS["accent_green"],
            )

        for a in anomalies[:50]:
            self.anomaly_tree.insert("", "end", values=(
                a["pid"],
                a["name"],
                f"{a['cpu']:.1f}",
                f"{a['mem']:.1f}",
                a["user"],
                a["reason"],
            ))
