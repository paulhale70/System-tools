#!/usr/bin/env python3
"""
WiFi Packet Sniffer - Standalone network packet capture and analysis tool.

Requires: scapy, tkinter
On Windows: Also requires Npcap (https://npcap.com)
Must run with elevated privileges (Administrator/root).
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import datetime
import csv
import os
import sys
from collections import defaultdict

# Check for scapy
try:
    from scapy.all import (
        sniff, get_if_list, conf, IP, IPv6, TCP, UDP, ICMP, ARP, DNS,
        Ether, Raw, wrpcap, hexdump
    )
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


# Theme colors
DARK_THEME = {
    "bg": "#1a1a2e",
    "fg": "#ffffff",
    "accent": "#0984e3",
    "card": "#16213e",
    "border": "#0f3460",
    "text_secondary": "#b2bec3",
    "success": "#00b894",
    "warning": "#fdcb6e",
    "danger": "#e94560",
    "highlight": "#2d3436",
}


def get_protocol_name(packet):
    """Extract protocol name from packet."""
    if packet.haslayer(DNS):
        return "DNS"
    elif packet.haslayer(TCP):
        sport = packet[TCP].sport
        dport = packet[TCP].dport
        if 80 in (sport, dport):
            return "HTTP"
        elif 443 in (sport, dport):
            return "HTTPS"
        elif 22 in (sport, dport):
            return "SSH"
        elif 21 in (sport, dport):
            return "FTP"
        elif 25 in (sport, dport) or 587 in (sport, dport):
            return "SMTP"
        return "TCP"
    elif packet.haslayer(UDP):
        sport = packet[UDP].sport
        dport = packet[UDP].dport
        if 53 in (sport, dport):
            return "DNS"
        elif 67 in (sport, dport) or 68 in (sport, dport):
            return "DHCP"
        return "UDP"
    elif packet.haslayer(ICMP):
        return "ICMP"
    elif packet.haslayer(ARP):
        return "ARP"
    elif packet.haslayer(IPv6):
        return "IPv6"
    elif packet.haslayer(IP):
        return "IP"
    elif packet.haslayer(Ether):
        return "Ethernet"
    return "Other"


def get_packet_info(packet):
    """Extract displayable info from a packet."""
    info = {
        "time": datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "src": "",
        "dst": "",
        "protocol": get_protocol_name(packet),
        "length": len(packet),
        "info": "",
        "src_port": "",
        "dst_port": "",
    }

    # IP layer
    if packet.haslayer(IP):
        info["src"] = packet[IP].src
        info["dst"] = packet[IP].dst
    elif packet.haslayer(IPv6):
        info["src"] = packet[IPv6].src
        info["dst"] = packet[IPv6].dst
    elif packet.haslayer(ARP):
        info["src"] = packet[ARP].psrc
        info["dst"] = packet[ARP].pdst
        info["info"] = f"ARP {'Request' if packet[ARP].op == 1 else 'Reply'}"
    elif packet.haslayer(Ether):
        info["src"] = packet[Ether].src
        info["dst"] = packet[Ether].dst

    # TCP/UDP ports
    if packet.haslayer(TCP):
        info["src_port"] = str(packet[TCP].sport)
        info["dst_port"] = str(packet[TCP].dport)
        flags = packet[TCP].flags
        flag_str = ""
        if flags.S: flag_str += "SYN "
        if flags.A: flag_str += "ACK "
        if flags.F: flag_str += "FIN "
        if flags.R: flag_str += "RST "
        if flags.P: flag_str += "PSH "
        info["info"] = f"{packet[TCP].sport} -> {packet[TCP].dport} [{flag_str.strip()}]"
    elif packet.haslayer(UDP):
        info["src_port"] = str(packet[UDP].sport)
        info["dst_port"] = str(packet[UDP].dport)
        info["info"] = f"{packet[UDP].sport} -> {packet[UDP].dport}"

    # DNS
    if packet.haslayer(DNS):
        dns = packet[DNS]
        if dns.qr == 0 and dns.qd:
            info["info"] = f"Query: {dns.qd.qname.decode() if hasattr(dns.qd.qname, 'decode') else dns.qd.qname}"
        elif dns.qr == 1:
            info["info"] = f"Response"

    # ICMP
    if packet.haslayer(ICMP):
        icmp_types = {0: "Echo Reply", 8: "Echo Request", 3: "Dest Unreachable", 11: "Time Exceeded"}
        info["info"] = icmp_types.get(packet[ICMP].type, f"Type {packet[ICMP].type}")

    return info


class PacketSniffer:
    """Packet capture backend using scapy."""

    def __init__(self, callback):
        self.callback = callback
        self._running = False
        self._thread = None
        self._packets = []
        self._lock = threading.Lock()
        self.interface = None
        self.filter_str = ""

    def get_interfaces(self):
        """Get available network interfaces."""
        try:
            return get_if_list()
        except Exception:
            return []

    def start(self, interface=None, bpf_filter=""):
        """Start packet capture."""
        if self._running:
            return

        self.interface = interface
        self.filter_str = bpf_filter
        self._running = True
        self._packets = []

        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop packet capture."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    @property
    def is_running(self):
        return self._running

    @property
    def packets(self):
        with self._lock:
            return list(self._packets)

    def clear(self):
        """Clear captured packets."""
        with self._lock:
            self._packets = []

    def _capture_loop(self):
        """Background capture loop."""
        try:
            sniff(
                iface=self.interface,
                filter=self.filter_str if self.filter_str else None,
                prn=self._process_packet,
                store=False,
                stop_filter=lambda _: not self._running,
            )
        except Exception as e:
            # Schedule error display on main thread
            self.callback(None, error=str(e))

    def _process_packet(self, packet):
        """Process a captured packet."""
        with self._lock:
            self._packets.append(packet)
        self.callback(packet)

    def export_pcap(self, filepath):
        """Export captured packets to PCAP file."""
        with self._lock:
            if self._packets:
                wrpcap(filepath, self._packets)
                return len(self._packets)
        return 0


class PacketSnifferApp:
    """Main GUI application for packet sniffing."""

    def __init__(self, root):
        self.root = root
        self.root.title("Packet Sniffer")
        self.root.geometry("1200x800")
        self.root.configure(bg=DARK_THEME["bg"])

        # Check for scapy
        if not SCAPY_AVAILABLE:
            self._show_dependency_error()
            return

        # Initialize sniffer
        self.sniffer = PacketSniffer(self._on_packet)

        # Stats
        self.packet_count = 0
        self.bytes_total = 0
        self.protocol_counts = defaultdict(int)
        self.start_time = None

        # Packet display data
        self.displayed_packets = []
        self.selected_packet = None

        # Filters
        self.filter_protocol = tk.StringVar(value="All")
        self.filter_ip = tk.StringVar()
        self.filter_port = tk.StringVar()

        self._setup_styles()
        self._create_ui()
        self._update_stats_display()

    def _show_dependency_error(self):
        """Show error when scapy is not available."""
        frame = tk.Frame(self.root, bg=DARK_THEME["bg"])
        frame.pack(expand=True, fill="both", padx=50, pady=50)

        tk.Label(
            frame,
            text="Scapy Not Installed",
            font=("Segoe UI", 24, "bold"),
            bg=DARK_THEME["bg"],
            fg=DARK_THEME["danger"],
        ).pack(pady=20)

        msg = """This packet sniffer requires the 'scapy' library.

Install it with:
    pip install scapy

On Windows, you also need Npcap:
    https://npcap.com

Then restart this application."""

        tk.Label(
            frame,
            text=msg,
            font=("Consolas", 12),
            bg=DARK_THEME["bg"],
            fg=DARK_THEME["fg"],
            justify="left",
        ).pack(pady=20)

        tk.Button(
            frame,
            text="Exit",
            command=self.root.quit,
            bg=DARK_THEME["accent"],
            fg="white",
            font=("Segoe UI", 11),
            relief="flat",
            padx=20,
            pady=8,
        ).pack(pady=20)

    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        style.theme_use("clam")

        # Treeview
        style.configure(
            "Packet.Treeview",
            background=DARK_THEME["card"],
            foreground=DARK_THEME["fg"],
            fieldbackground=DARK_THEME["card"],
            rowheight=22,
        )
        style.configure(
            "Packet.Treeview.Heading",
            background=DARK_THEME["border"],
            foreground=DARK_THEME["fg"],
            relief="flat",
        )
        style.map(
            "Packet.Treeview",
            background=[("selected", DARK_THEME["accent"])],
            foreground=[("selected", "white")],
        )

        # Scrollbar
        style.configure(
            "Dark.Vertical.TScrollbar",
            background=DARK_THEME["border"],
            troughcolor=DARK_THEME["bg"],
            borderwidth=0,
        )

    def _create_ui(self):
        """Create the main UI layout."""
        # Top toolbar
        self._create_toolbar()

        # Main content area with packet list and details
        main_pane = tk.PanedWindow(
            self.root,
            orient=tk.VERTICAL,
            bg=DARK_THEME["bg"],
            sashwidth=4,
            sashrelief="flat",
        )
        main_pane.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Packet list frame
        list_frame = tk.Frame(main_pane, bg=DARK_THEME["card"])
        main_pane.add(list_frame, height=450)

        self._create_packet_list(list_frame)

        # Details frame
        details_frame = tk.Frame(main_pane, bg=DARK_THEME["card"])
        main_pane.add(details_frame, height=200)

        self._create_details_panel(details_frame)

        # Bottom status bar
        self._create_status_bar()

    def _create_toolbar(self):
        """Create the top toolbar."""
        toolbar = tk.Frame(self.root, bg=DARK_THEME["card"], height=60)
        toolbar.pack(fill="x", padx=10, pady=10)
        toolbar.pack_propagate(False)

        # Interface selector
        tk.Label(
            toolbar,
            text="Interface:",
            bg=DARK_THEME["card"],
            fg=DARK_THEME["text_secondary"],
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(10, 5))

        self.interface_var = tk.StringVar()
        interfaces = self.sniffer.get_interfaces()
        self.interface_combo = ttk.Combobox(
            toolbar,
            textvariable=self.interface_var,
            values=interfaces,
            width=20,
            state="readonly",
        )
        self.interface_combo.pack(side="left", padx=5)
        if interfaces:
            self.interface_combo.current(0)

        # BPF Filter
        tk.Label(
            toolbar,
            text="BPF Filter:",
            bg=DARK_THEME["card"],
            fg=DARK_THEME["text_secondary"],
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(20, 5))

        self.bpf_entry = tk.Entry(
            toolbar,
            width=30,
            bg=DARK_THEME["bg"],
            fg=DARK_THEME["fg"],
            insertbackground=DARK_THEME["fg"],
            relief="flat",
            font=("Consolas", 10),
        )
        self.bpf_entry.pack(side="left", padx=5, ipady=4)
        self.bpf_entry.insert(0, "")

        # Start/Stop buttons
        self.start_btn = tk.Button(
            toolbar,
            text="Start Capture",
            command=self._start_capture,
            bg=DARK_THEME["success"],
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        )
        self.start_btn.pack(side="left", padx=(20, 5))

        self.stop_btn = tk.Button(
            toolbar,
            text="Stop",
            command=self._stop_capture,
            bg=DARK_THEME["danger"],
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=15,
            pady=5,
            state="disabled",
            cursor="hand2",
        )
        self.stop_btn.pack(side="left", padx=5)

        # Clear button
        tk.Button(
            toolbar,
            text="Clear",
            command=self._clear_packets,
            bg=DARK_THEME["border"],
            fg=DARK_THEME["fg"],
            font=("Segoe UI", 10),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=5)

        # Export buttons
        tk.Button(
            toolbar,
            text="Export CSV",
            command=self._export_csv,
            bg=DARK_THEME["border"],
            fg=DARK_THEME["fg"],
            font=("Segoe UI", 10),
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
        ).pack(side="right", padx=5)

        tk.Button(
            toolbar,
            text="Export PCAP",
            command=self._export_pcap,
            bg=DARK_THEME["border"],
            fg=DARK_THEME["fg"],
            font=("Segoe UI", 10),
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
        ).pack(side="right", padx=5)

    def _create_packet_list(self, parent):
        """Create the packet list treeview."""
        # Filter bar
        filter_bar = tk.Frame(parent, bg=DARK_THEME["card"])
        filter_bar.pack(fill="x", padx=5, pady=5)

        tk.Label(
            filter_bar,
            text="Display Filter:",
            bg=DARK_THEME["card"],
            fg=DARK_THEME["text_secondary"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=5)

        # Protocol filter
        protocols = ["All", "TCP", "UDP", "ICMP", "DNS", "HTTP", "HTTPS", "ARP", "SSH"]
        proto_combo = ttk.Combobox(
            filter_bar,
            textvariable=self.filter_protocol,
            values=protocols,
            width=10,
            state="readonly",
        )
        proto_combo.pack(side="left", padx=5)
        proto_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_display_filter())

        tk.Label(
            filter_bar,
            text="IP:",
            bg=DARK_THEME["card"],
            fg=DARK_THEME["text_secondary"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(15, 5))

        ip_entry = tk.Entry(
            filter_bar,
            textvariable=self.filter_ip,
            width=15,
            bg=DARK_THEME["bg"],
            fg=DARK_THEME["fg"],
            insertbackground=DARK_THEME["fg"],
            relief="flat",
            font=("Consolas", 9),
        )
        ip_entry.pack(side="left", padx=5, ipady=2)
        ip_entry.bind("<Return>", lambda e: self._apply_display_filter())

        tk.Label(
            filter_bar,
            text="Port:",
            bg=DARK_THEME["card"],
            fg=DARK_THEME["text_secondary"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(15, 5))

        port_entry = tk.Entry(
            filter_bar,
            textvariable=self.filter_port,
            width=8,
            bg=DARK_THEME["bg"],
            fg=DARK_THEME["fg"],
            insertbackground=DARK_THEME["fg"],
            relief="flat",
            font=("Consolas", 9),
        )
        port_entry.pack(side="left", padx=5, ipady=2)
        port_entry.bind("<Return>", lambda e: self._apply_display_filter())

        tk.Button(
            filter_bar,
            text="Apply",
            command=self._apply_display_filter,
            bg=DARK_THEME["accent"],
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            cursor="hand2",
        ).pack(side="left", padx=10)

        # Packet list
        columns = ("no", "time", "source", "destination", "protocol", "length", "info")

        tree_frame = tk.Frame(parent, bg=DARK_THEME["card"])
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.packet_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Packet.Treeview",
            selectmode="browse",
        )

        # Column headers
        self.packet_tree.heading("no", text="No.")
        self.packet_tree.heading("time", text="Time")
        self.packet_tree.heading("source", text="Source")
        self.packet_tree.heading("destination", text="Destination")
        self.packet_tree.heading("protocol", text="Protocol")
        self.packet_tree.heading("length", text="Length")
        self.packet_tree.heading("info", text="Info")

        # Column widths
        self.packet_tree.column("no", width=60, anchor="center")
        self.packet_tree.column("time", width=100, anchor="center")
        self.packet_tree.column("source", width=150)
        self.packet_tree.column("destination", width=150)
        self.packet_tree.column("protocol", width=80, anchor="center")
        self.packet_tree.column("length", width=70, anchor="center")
        self.packet_tree.column("info", width=350)

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.packet_tree.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.packet_tree.configure(yscrollcommand=scrollbar.set)

        self.packet_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Selection event
        self.packet_tree.bind("<<TreeviewSelect>>", self._on_packet_select)

        # Protocol color tags
        self.packet_tree.tag_configure("TCP", foreground="#74b9ff")
        self.packet_tree.tag_configure("UDP", foreground="#a29bfe")
        self.packet_tree.tag_configure("HTTP", foreground="#00cec9")
        self.packet_tree.tag_configure("HTTPS", foreground="#00b894")
        self.packet_tree.tag_configure("DNS", foreground="#fdcb6e")
        self.packet_tree.tag_configure("ICMP", foreground="#e17055")
        self.packet_tree.tag_configure("ARP", foreground="#fab1a0")
        self.packet_tree.tag_configure("SSH", foreground="#81ecec")

    def _create_details_panel(self, parent):
        """Create the packet details panel."""
        # Notebook for different views
        self.details_notebook = ttk.Notebook(parent)
        self.details_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Packet info tab
        info_frame = tk.Frame(self.details_notebook, bg=DARK_THEME["bg"])
        self.details_notebook.add(info_frame, text="Packet Info")

        self.info_text = tk.Text(
            info_frame,
            bg=DARK_THEME["bg"],
            fg=DARK_THEME["fg"],
            font=("Consolas", 10),
            relief="flat",
            padx=10,
            pady=10,
            state="disabled",
        )
        self.info_text.pack(fill="both", expand=True)

        # Hex dump tab
        hex_frame = tk.Frame(self.details_notebook, bg=DARK_THEME["bg"])
        self.details_notebook.add(hex_frame, text="Hex Dump")

        self.hex_text = tk.Text(
            hex_frame,
            bg=DARK_THEME["bg"],
            fg=DARK_THEME["fg"],
            font=("Consolas", 9),
            relief="flat",
            padx=10,
            pady=10,
            state="disabled",
        )
        self.hex_text.pack(fill="both", expand=True)

        # Raw bytes tab
        raw_frame = tk.Frame(self.details_notebook, bg=DARK_THEME["bg"])
        self.details_notebook.add(raw_frame, text="Raw Data")

        self.raw_text = tk.Text(
            raw_frame,
            bg=DARK_THEME["bg"],
            fg=DARK_THEME["fg"],
            font=("Consolas", 9),
            relief="flat",
            padx=10,
            pady=10,
            state="disabled",
            wrap="char",
        )
        self.raw_text.pack(fill="both", expand=True)

    def _create_status_bar(self):
        """Create the bottom status bar."""
        status_bar = tk.Frame(self.root, bg=DARK_THEME["card"], height=35)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)

        # Status label
        self.status_label = tk.Label(
            status_bar,
            text="Ready",
            bg=DARK_THEME["card"],
            fg=DARK_THEME["text_secondary"],
            font=("Segoe UI", 9),
        )
        self.status_label.pack(side="left", padx=10)

        # Stats labels
        self.stats_frame = tk.Frame(status_bar, bg=DARK_THEME["card"])
        self.stats_frame.pack(side="right", padx=10)

        self.packets_label = tk.Label(
            self.stats_frame,
            text="Packets: 0",
            bg=DARK_THEME["card"],
            fg=DARK_THEME["fg"],
            font=("Segoe UI", 9),
        )
        self.packets_label.pack(side="left", padx=15)

        self.bytes_label = tk.Label(
            self.stats_frame,
            text="Bytes: 0",
            bg=DARK_THEME["card"],
            fg=DARK_THEME["fg"],
            font=("Segoe UI", 9),
        )
        self.bytes_label.pack(side="left", padx=15)

        self.rate_label = tk.Label(
            self.stats_frame,
            text="Rate: 0 pkt/s",
            bg=DARK_THEME["card"],
            fg=DARK_THEME["fg"],
            font=("Segoe UI", 9),
        )
        self.rate_label.pack(side="left", padx=15)

        # Protocol breakdown
        self.proto_label = tk.Label(
            self.stats_frame,
            text="",
            bg=DARK_THEME["card"],
            fg=DARK_THEME["text_secondary"],
            font=("Segoe UI", 9),
        )
        self.proto_label.pack(side="left", padx=15)

    def _start_capture(self):
        """Start packet capture."""
        iface = self.interface_var.get() or None
        bpf = self.bpf_entry.get().strip()

        self.packet_count = 0
        self.bytes_total = 0
        self.protocol_counts.clear()
        self.start_time = time.time()
        self.displayed_packets = []

        # Clear tree
        for item in self.packet_tree.get_children():
            self.packet_tree.delete(item)

        try:
            self.sniffer.start(interface=iface, bpf_filter=bpf)
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.interface_combo.config(state="disabled")
            self.bpf_entry.config(state="disabled")
            self.status_label.config(text=f"Capturing on {iface or 'all interfaces'}...")
        except Exception as e:
            messagebox.showerror("Capture Error", str(e))

    def _stop_capture(self):
        """Stop packet capture."""
        self.sniffer.stop()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.interface_combo.config(state="readonly")
        self.bpf_entry.config(state="normal")
        self.status_label.config(text="Capture stopped")

    def _clear_packets(self):
        """Clear all captured packets."""
        self.sniffer.clear()
        self.displayed_packets = []
        self.packet_count = 0
        self.bytes_total = 0
        self.protocol_counts.clear()

        for item in self.packet_tree.get_children():
            self.packet_tree.delete(item)

        self._clear_details()
        self._update_stats_display()

    def _on_packet(self, packet, error=None):
        """Callback when a packet is captured."""
        if error:
            self.root.after(0, lambda: messagebox.showerror("Capture Error", error))
            self.root.after(0, self._stop_capture)
            return

        if packet is None:
            return

        # Update stats
        self.packet_count += 1
        self.bytes_total += len(packet)

        info = get_packet_info(packet)
        self.protocol_counts[info["protocol"]] += 1

        # Store packet data
        self.displayed_packets.append((packet, info))

        # Add to tree (on main thread)
        self.root.after(0, lambda: self._add_packet_to_tree(info))

        # Update stats periodically
        if self.packet_count % 10 == 0:
            self.root.after(0, self._update_stats_display)

    def _add_packet_to_tree(self, info):
        """Add a packet to the treeview."""
        # Check display filters
        if not self._matches_display_filter(info):
            return

        no = self.packet_count
        values = (
            no,
            info["time"],
            info["src"],
            info["dst"],
            info["protocol"],
            info["length"],
            info["info"],
        )

        tag = info["protocol"] if info["protocol"] in ("TCP", "UDP", "HTTP", "HTTPS", "DNS", "ICMP", "ARP", "SSH") else ""

        self.packet_tree.insert("", "end", values=values, tags=(tag,))

        # Auto-scroll to bottom
        self.packet_tree.yview_moveto(1.0)

    def _matches_display_filter(self, info):
        """Check if packet matches current display filters."""
        # Protocol filter
        proto = self.filter_protocol.get()
        if proto != "All" and info["protocol"] != proto:
            return False

        # IP filter
        ip_filter = self.filter_ip.get().strip()
        if ip_filter and ip_filter not in info["src"] and ip_filter not in info["dst"]:
            return False

        # Port filter
        port_filter = self.filter_port.get().strip()
        if port_filter and port_filter != info["src_port"] and port_filter != info["dst_port"]:
            return False

        return True

    def _apply_display_filter(self):
        """Re-apply display filters to all packets."""
        # Clear tree
        for item in self.packet_tree.get_children():
            self.packet_tree.delete(item)

        # Re-add matching packets
        for i, (packet, info) in enumerate(self.displayed_packets):
            if self._matches_display_filter(info):
                values = (
                    i + 1,
                    info["time"],
                    info["src"],
                    info["dst"],
                    info["protocol"],
                    info["length"],
                    info["info"],
                )
                tag = info["protocol"] if info["protocol"] in ("TCP", "UDP", "HTTP", "HTTPS", "DNS", "ICMP", "ARP", "SSH") else ""
                self.packet_tree.insert("", "end", values=values, tags=(tag,))

    def _on_packet_select(self, event):
        """Handle packet selection in treeview."""
        selection = self.packet_tree.selection()
        if not selection:
            return

        item = self.packet_tree.item(selection[0])
        packet_no = int(item["values"][0]) - 1

        if 0 <= packet_no < len(self.displayed_packets):
            packet, info = self.displayed_packets[packet_no]
            self._show_packet_details(packet, info)

    def _show_packet_details(self, packet, info):
        """Show details for selected packet."""
        self.selected_packet = packet

        # Packet info
        self.info_text.config(state="normal")
        self.info_text.delete("1.0", "end")

        lines = []
        lines.append(f"Time:     {info['time']}")
        lines.append(f"Source:   {info['src']}" + (f":{info['src_port']}" if info['src_port'] else ""))
        lines.append(f"Dest:     {info['dst']}" + (f":{info['dst_port']}" if info['dst_port'] else ""))
        lines.append(f"Protocol: {info['protocol']}")
        lines.append(f"Length:   {info['length']} bytes")
        lines.append(f"Info:     {info['info']}")
        lines.append("")
        lines.append("--- Layers ---")
        lines.append(packet.summary())
        lines.append("")
        lines.append("--- Full Packet ---")
        lines.append(packet.show(dump=True))

        self.info_text.insert("1.0", "\n".join(lines))
        self.info_text.config(state="disabled")

        # Hex dump
        self.hex_text.config(state="normal")
        self.hex_text.delete("1.0", "end")

        try:
            import io
            output = io.StringIO()
            hexdump(packet, dump=True)
            hex_output = hexdump(packet, dump=True)
            self.hex_text.insert("1.0", hex_output if hex_output else bytes(packet).hex())
        except Exception:
            self.hex_text.insert("1.0", bytes(packet).hex())

        self.hex_text.config(state="disabled")

        # Raw bytes
        self.raw_text.config(state="normal")
        self.raw_text.delete("1.0", "end")

        raw = bytes(packet)
        # Show printable ASCII
        ascii_repr = "".join(chr(b) if 32 <= b < 127 else "." for b in raw)
        self.raw_text.insert("1.0", ascii_repr)

        self.raw_text.config(state="disabled")

    def _clear_details(self):
        """Clear the details panel."""
        for text_widget in (self.info_text, self.hex_text, self.raw_text):
            text_widget.config(state="normal")
            text_widget.delete("1.0", "end")
            text_widget.config(state="disabled")

    def _update_stats_display(self):
        """Update the stats in the status bar."""
        self.packets_label.config(text=f"Packets: {self.packet_count:,}")

        # Format bytes
        b = self.bytes_total
        if b < 1024:
            bytes_str = f"{b} B"
        elif b < 1024 * 1024:
            bytes_str = f"{b / 1024:.1f} KB"
        else:
            bytes_str = f"{b / 1024 / 1024:.1f} MB"
        self.bytes_label.config(text=f"Bytes: {bytes_str}")

        # Packet rate
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                rate = self.packet_count / elapsed
                self.rate_label.config(text=f"Rate: {rate:.1f} pkt/s")

        # Protocol breakdown (top 3)
        if self.protocol_counts:
            top_protos = sorted(self.protocol_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            proto_str = "  ".join(f"{p}: {c}" for p, c in top_protos)
            self.proto_label.config(text=proto_str)

    def _export_csv(self):
        """Export packets to CSV."""
        if not self.displayed_packets:
            messagebox.showinfo("Export", "No packets to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"capture_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )

        if not filepath:
            return

        try:
            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["No", "Time", "Source", "Destination", "Protocol", "Length", "Info"])

                for i, (packet, info) in enumerate(self.displayed_packets):
                    src = info["src"] + (f":{info['src_port']}" if info["src_port"] else "")
                    dst = info["dst"] + (f":{info['dst_port']}" if info["dst_port"] else "")
                    writer.writerow([i + 1, info["time"], src, dst, info["protocol"], info["length"], info["info"]])

            messagebox.showinfo("Export", f"Exported {len(self.displayed_packets)} packets to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _export_pcap(self):
        """Export packets to PCAP format."""
        if not self.displayed_packets:
            messagebox.showinfo("Export", "No packets to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pcap",
            filetypes=[("PCAP files", "*.pcap"), ("All files", "*.*")],
            initialfile=f"capture_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pcap",
        )

        if not filepath:
            return

        try:
            count = self.sniffer.export_pcap(filepath)
            messagebox.showinfo("Export", f"Exported {count} packets to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


def main():
    """Main entry point."""
    # Check for admin privileges
    if os.name == "nt":
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("Warning: This application requires Administrator privileges for packet capture.")
            print("Please run as Administrator.")
    elif os.geteuid() != 0:
        print("Warning: This application requires root privileges for packet capture.")
        print("Please run with sudo.")

    root = tk.Tk()
    app = PacketSnifferApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
