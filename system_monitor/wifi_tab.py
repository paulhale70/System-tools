"""WiFi analyzer tab - scan networks, signal strength, channel analysis."""

import tkinter as tk
from tkinter import ttk
import subprocess
import re
import platform
from collections import deque

from system_monitor.widgets import (
    COLORS, LineChart, InfoRow, SectionHeader, ScrollableFrame,
)


def _run_cmd(cmd, timeout=10):
    """Run a shell command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout
    except Exception:
        return ""


class WifiTab(tk.Frame):
    """WiFi network analysis - current connection, available networks, signal tracking."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self._scan_counter = 0
        self._signal_history = deque(maxlen=60)
        self._networks_cache = []
        self._system = platform.system()
        self._build_ui()

    def _build_ui(self):
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        container = scroll.scrollable_frame

        # -- Current Connection --
        conn_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        conn_frame.pack(fill="x", padx=10, pady=10)

        SectionHeader(conn_frame, text="Current WiFi Connection").pack(fill="x", pady=(0, 5))

        self.conn_info = {}
        for key, label in [
            ("interface", "Interface"),
            ("ssid", "SSID (Network Name)"),
            ("bssid", "BSSID (AP MAC)"),
            ("signal", "Signal Strength"),
            ("frequency", "Frequency"),
            ("channel", "Channel"),
            ("bitrate", "Link Speed"),
            ("security", "Security"),
            ("ip_address", "IP Address"),
            ("gateway", "Gateway"),
            ("dns", "DNS Servers"),
        ]:
            row = InfoRow(conn_frame, label)
            row.pack(fill="x", pady=1)
            self.conn_info[key] = row

        # -- Signal Strength Chart --
        signal_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        signal_frame.pack(fill="x", padx=10, pady=5)

        SectionHeader(signal_frame, text="Signal Strength History (dBm)").pack(fill="x", pady=(0, 5))

        self.signal_chart = LineChart(
            signal_frame,
            width=750,
            height=150,
            max_points=60,
            y_min=-100,
            y_max=-20,
            y_label="dBm",
            series_colors=[COLORS["accent_green"]],
            series_labels=["Signal"],
        )
        self.signal_chart.pack(fill="x")

        # -- Signal quality bar --
        quality_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        quality_frame.pack(fill="x", padx=10, pady=5)

        self.quality_canvas = tk.Canvas(
            quality_frame, height=30, bg=COLORS["bg_dark"], highlightthickness=0,
        )
        self.quality_canvas.pack(fill="x")

        # -- Available Networks --
        networks_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        networks_frame.pack(fill="x", padx=10, pady=5)

        header_row = tk.Frame(networks_frame, bg=COLORS["bg_dark"])
        header_row.pack(fill="x", pady=(0, 5))

        SectionHeader(header_row, text="Available Networks").pack(side="left")

        self.scan_btn = tk.Button(
            header_row,
            text="Scan Now",
            command=self._manual_scan,
            bg=COLORS["bg_light"],
            fg=COLORS["text_primary"],
            font=("Helvetica", 9),
            relief="flat",
            padx=10,
            pady=2,
        )
        self.scan_btn.pack(side="right", padx=5)

        self.scan_status = tk.Label(
            header_row,
            text="",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_dark"],
            font=("Helvetica", 9),
        )
        self.scan_status.pack(side="right")

        # Treeview for networks
        tree_frame = tk.Frame(networks_frame, bg=COLORS["bg_dark"])
        tree_frame.pack(fill="x")

        columns = ("ssid", "signal", "quality", "channel", "frequency", "security", "bssid")
        self.networks_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Proc.Treeview",
            selectmode="browse",
            height=12,
        )

        headings = {
            "ssid": ("SSID", 180),
            "signal": ("Signal (dBm)", 100),
            "quality": ("Quality", 80),
            "channel": ("Channel", 70),
            "frequency": ("Freq (GHz)", 90),
            "security": ("Security", 120),
            "bssid": ("BSSID", 150),
        }

        for col, (text, width) in headings.items():
            self.networks_tree.heading(col, text=text)
            self.networks_tree.column(col, width=width, minwidth=50)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.networks_tree.yview)
        self.networks_tree.configure(yscrollcommand=scrollbar.set)
        self.networks_tree.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

        # -- Channel Utilization --
        channel_frame = tk.Frame(container, bg=COLORS["bg_dark"])
        channel_frame.pack(fill="x", padx=10, pady=(5, 15))

        SectionHeader(channel_frame, text="Channel Utilization").pack(fill="x", pady=(0, 5))

        self.channel_canvas = tk.Canvas(
            channel_frame, height=120, bg=COLORS["bg_dark"], highlightthickness=0,
        )
        self.channel_canvas.pack(fill="x")

        # No WiFi message
        self.no_wifi_label = tk.Label(
            container,
            text="",
            fg=COLORS["text_dim"],
            bg=COLORS["bg_dark"],
            font=("Helvetica", 10),
        )

    def _manual_scan(self):
        """Trigger a manual WiFi scan."""
        self.scan_status.config(text="Scanning...")
        self._scan_counter = 29  # Force scan on next update
        self.update_data()

    def _get_wifi_info_linux(self):
        """Get WiFi info on Linux using iw/iwconfig/nmcli."""
        info = {
            "interface": "N/A", "ssid": "N/A", "bssid": "N/A",
            "signal": "N/A", "frequency": "N/A", "channel": "N/A",
            "bitrate": "N/A", "security": "N/A", "ip_address": "N/A",
            "gateway": "N/A", "dns": "N/A",
        }
        signal_dbm = None

        # Try nmcli first (most reliable)
        nmcli_out = _run_cmd(["nmcli", "-t", "-f", "all", "dev", "wifi", "list", "--rescan", "no"])
        if not nmcli_out:
            nmcli_out = _run_cmd(["nmcli", "dev", "wifi", "list", "--rescan", "no"])

        # Get active connection info
        active = _run_cmd(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE,STATE", "connection", "show", "--active"])
        wifi_device = None
        for line in active.splitlines():
            parts = line.split(":")
            if len(parts) >= 4 and "wifi" in parts[1].lower() and "activated" in parts[3].lower():
                wifi_device = parts[2]
                info["ssid"] = parts[0]
                break

        if wifi_device:
            info["interface"] = wifi_device

            # Detailed device info
            dev_info = _run_cmd(["nmcli", "-t", "-f", "all", "dev", "show", wifi_device])
            for line in dev_info.splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    if "IP4.ADDRESS" in key and val:
                        info["ip_address"] = val
                    elif "IP4.GATEWAY" in key and val:
                        info["gateway"] = val
                    elif "IP4.DNS" in key and val:
                        info["dns"] = val
                    elif "GENERAL.HWADDR" in key:
                        pass  # Our MAC

            # iw for signal and detailed wireless info
            iw_out = _run_cmd(["iw", "dev", wifi_device, "link"])
            for line in iw_out.splitlines():
                line = line.strip()
                if line.startswith("signal:"):
                    match = re.search(r"(-?\d+)", line)
                    if match:
                        signal_dbm = int(match.group(1))
                        info["signal"] = f"{signal_dbm} dBm"
                elif line.startswith("freq:"):
                    match = re.search(r"(\d+)", line)
                    if match:
                        freq_mhz = int(match.group(1))
                        info["frequency"] = f"{freq_mhz} MHz ({freq_mhz / 1000:.1f} GHz)"
                        info["channel"] = str(self._freq_to_channel(freq_mhz))
                elif line.startswith("tx bitrate:"):
                    info["bitrate"] = line.split(":", 1)[1].strip()
                elif "Connected to" in line:
                    match = re.search(r"([0-9a-fA-F:]{17})", line)
                    if match:
                        info["bssid"] = match.group(1)

            # iwconfig fallback
            if signal_dbm is None:
                iwconfig_out = _run_cmd(["iwconfig", wifi_device])
                match = re.search(r"Signal level[=:](-?\d+)", iwconfig_out)
                if match:
                    signal_dbm = int(match.group(1))
                    info["signal"] = f"{signal_dbm} dBm"
                match = re.search(r"Bit Rate[=:](\S+)", iwconfig_out)
                if match and info["bitrate"] == "N/A":
                    info["bitrate"] = match.group(1)
                match = re.search(r'ESSID:"([^"]*)"', iwconfig_out)
                if match and info["ssid"] == "N/A":
                    info["ssid"] = match.group(1)

            # Security info
            conn_detail = _run_cmd(["nmcli", "-t", "-f", "802-11-wireless-security.key-mgmt",
                                     "connection", "show", info["ssid"]])
            for line in conn_detail.splitlines():
                if "key-mgmt" in line.lower():
                    val = line.split(":")[-1].strip()
                    security_map = {
                        "wpa-psk": "WPA-PSK",
                        "wpa-eap": "WPA-Enterprise",
                        "sae": "WPA3-SAE",
                        "owe": "WPA3-OWE",
                        "wpa-eap-suite-b-192": "WPA3-Enterprise",
                    }
                    info["security"] = security_map.get(val, val.upper() if val else "Open")
        else:
            # Try finding any WiFi interface
            iw_dev = _run_cmd(["iw", "dev"])
            match = re.search(r"Interface\s+(\w+)", iw_dev)
            if match:
                info["interface"] = match.group(1) + " (disconnected)"

        return info, signal_dbm

    def _get_wifi_info_macos(self):
        """Get WiFi info on macOS."""
        info = {
            "interface": "N/A", "ssid": "N/A", "bssid": "N/A",
            "signal": "N/A", "frequency": "N/A", "channel": "N/A",
            "bitrate": "N/A", "security": "N/A", "ip_address": "N/A",
            "gateway": "N/A", "dns": "N/A",
        }
        signal_dbm = None

        # macOS airport utility
        airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        output = _run_cmd([airport_path, "-I"])

        for line in output.splitlines():
            line = line.strip()
            if ": " in line:
                key, _, val = line.partition(": ")
                key = key.strip()
                val = val.strip()
                if key == "SSID":
                    info["ssid"] = val
                elif key == "BSSID":
                    info["bssid"] = val
                elif key == "agrCtlRSSI":
                    try:
                        signal_dbm = int(val)
                        info["signal"] = f"{signal_dbm} dBm"
                    except ValueError:
                        pass
                elif key == "channel":
                    info["channel"] = val
                elif key == "lastTxRate":
                    info["bitrate"] = f"{val} Mbps"
                elif key == "link auth":
                    info["security"] = val

        info["interface"] = "en0"
        return info, signal_dbm

    def _get_wifi_info_windows(self):
        """Get WiFi info on Windows."""
        info = {
            "interface": "N/A", "ssid": "N/A", "bssid": "N/A",
            "signal": "N/A", "frequency": "N/A", "channel": "N/A",
            "bitrate": "N/A", "security": "N/A", "ip_address": "N/A",
            "gateway": "N/A", "dns": "N/A",
        }
        signal_dbm = None

        output = _run_cmd(["netsh", "wlan", "show", "interfaces"])
        for line in output.splitlines():
            line = line.strip()
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip().lower()
                val = val.strip()
                if "ssid" in key and "bssid" not in key:
                    info["ssid"] = val
                elif "bssid" in key:
                    info["bssid"] = val
                elif "signal" in key:
                    match = re.search(r"(\d+)", val)
                    if match:
                        quality = int(match.group(1))
                        signal_dbm = self._quality_to_dbm(quality)
                        info["signal"] = f"{signal_dbm} dBm ({quality}%)"
                elif "channel" in key:
                    info["channel"] = val
                elif "receive rate" in key or "transmit rate" in key:
                    if info["bitrate"] == "N/A":
                        info["bitrate"] = val
                elif "authentication" in key:
                    info["security"] = val
                elif key == "name":
                    info["interface"] = val

        return info, signal_dbm

    def _scan_networks_linux(self):
        """Scan for WiFi networks on Linux."""
        networks = []

        # Try nmcli scan
        output = _run_cmd(["nmcli", "-t", "-f",
                           "SSID,BSSID,SIGNAL,FREQ,CHAN,SECURITY,RATE",
                           "dev", "wifi", "list"])

        for line in output.splitlines():
            parts = line.split(":")
            if len(parts) >= 6:
                ssid = parts[0].strip()
                bssid = ":".join(parts[1:7]).strip() if len(parts) > 7 else parts[1].strip()
                # Re-parse with known BSSID format
                remaining = line
                if ssid:
                    remaining = remaining[len(ssid) + 1:]

                # Simple parse approach
                try:
                    fields = line.replace("\\:", "@@").split(":")
                    if len(fields) >= 6:
                        ssid = fields[0].replace("@@", ":")
                        # Reconstruct BSSID (6 hex pairs)
                        bssid_parts = fields[1:7]
                        bssid = ":".join(bssid_parts).replace("@@", ":")
                        rest = fields[7:]
                        if len(rest) >= 4:
                            signal = rest[0].strip()
                            freq = rest[1].strip()
                            chan = rest[2].strip()
                            security = rest[3].strip().replace("@@", ":")
                        else:
                            continue
                    else:
                        continue
                except (IndexError, ValueError):
                    continue

                if not ssid or ssid == "--":
                    ssid = "(Hidden)"

                try:
                    signal_val = int(signal)
                    # nmcli reports signal as 0-100 quality
                    dbm = self._quality_to_dbm(signal_val)
                    quality = signal_val
                except ValueError:
                    dbm = -100
                    quality = 0

                try:
                    freq_mhz = int(freq)
                    freq_ghz = freq_mhz / 1000
                except ValueError:
                    freq_ghz = 0
                    freq_mhz = 0

                networks.append({
                    "ssid": ssid,
                    "bssid": bssid,
                    "signal_dbm": dbm,
                    "quality": quality,
                    "channel": chan,
                    "frequency": freq_ghz,
                    "security": security or "Open",
                })

        # Sort by signal quality
        networks.sort(key=lambda x: x.get("quality", 0), reverse=True)
        return networks

    def _scan_networks_macos(self):
        """Scan for WiFi networks on macOS."""
        networks = []
        airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        output = _run_cmd([airport_path, "-s"])

        lines = output.strip().splitlines()
        if len(lines) < 2:
            return networks

        for line in lines[1:]:
            match = re.match(
                r"\s*(.+?)\s+([0-9a-fA-F:]{17})\s+(-?\d+)\s+(\S+)\s+\w+\s+\w+\s+(.+)",
                line,
            )
            if match:
                ssid = match.group(1).strip()
                bssid = match.group(2)
                rssi = int(match.group(3))
                channel = match.group(4)
                security = match.group(5).strip()

                networks.append({
                    "ssid": ssid or "(Hidden)",
                    "bssid": bssid,
                    "signal_dbm": rssi,
                    "quality": self._dbm_to_quality(rssi),
                    "channel": channel,
                    "frequency": 0,
                    "security": security or "Open",
                })

        networks.sort(key=lambda x: x.get("quality", 0), reverse=True)
        return networks

    def _scan_networks_windows(self):
        """Scan for WiFi networks on Windows."""
        networks = []
        output = _run_cmd(["netsh", "wlan", "show", "networks", "mode=bssid"])

        current = {}
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("SSID") and "BSSID" not in line:
                if current:
                    networks.append(current)
                current = {"ssid": "", "bssid": "", "signal_dbm": -100, "quality": 0,
                           "channel": "", "frequency": 0, "security": ""}
                match = re.search(r":\s*(.+)", line)
                if match:
                    current["ssid"] = match.group(1).strip() or "(Hidden)"
            elif "BSSID" in line:
                match = re.search(r":\s*(.+)", line)
                if match:
                    current["bssid"] = match.group(1).strip()
            elif "Signal" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    quality = int(match.group(1))
                    current["quality"] = quality
                    current["signal_dbm"] = self._quality_to_dbm(quality)
            elif "Channel" in line:
                match = re.search(r":\s*(\d+)", line)
                if match:
                    current["channel"] = match.group(1)
            elif "Authentication" in line:
                match = re.search(r":\s*(.+)", line)
                if match:
                    current["security"] = match.group(1).strip()

        if current and current.get("ssid"):
            networks.append(current)

        networks.sort(key=lambda x: x.get("quality", 0), reverse=True)
        return networks

    @staticmethod
    def _freq_to_channel(freq_mhz):
        """Convert frequency in MHz to WiFi channel number."""
        if 2412 <= freq_mhz <= 2484:
            if freq_mhz == 2484:
                return 14
            return (freq_mhz - 2412) // 5 + 1
        elif 5170 <= freq_mhz <= 5825:
            return (freq_mhz - 5170) // 5 + 34
        elif 5955 <= freq_mhz <= 7115:  # 6 GHz (WiFi 6E)
            return (freq_mhz - 5955) // 5 + 1
        return 0

    @staticmethod
    def _quality_to_dbm(quality):
        """Convert signal quality (0-100) to approximate dBm."""
        return max(-100, min(-20, -100 + quality * 0.8))

    @staticmethod
    def _dbm_to_quality(dbm):
        """Convert dBm to signal quality percentage (0-100)."""
        if dbm <= -100:
            return 0
        elif dbm >= -50:
            return 100
        return 2 * (dbm + 100)

    def _draw_quality_bar(self, quality, ssid=""):
        """Draw a visual signal quality bar."""
        self.quality_canvas.delete("all")
        w = self.quality_canvas.winfo_width() or 750
        h = 30

        # Background
        self.quality_canvas.create_rectangle(0, 0, w, h, fill=COLORS["bg_dark"], outline="")

        # Label
        self.quality_canvas.create_text(
            5, h / 2, text=f"Signal Quality:", anchor="w",
            fill=COLORS["text_secondary"], font=("Helvetica", 9),
        )

        bar_start = 120
        bar_w = w - bar_start - 60

        # Bar background
        self.quality_canvas.create_rectangle(
            bar_start, 5, bar_start + bar_w, h - 5,
            fill=COLORS["gauge_bg"], outline="",
        )

        # Bar fill
        if quality > 0:
            fill_w = (quality / 100) * bar_w
            if quality >= 70:
                color = COLORS["accent_green"]
            elif quality >= 40:
                color = COLORS["accent_yellow"]
            else:
                color = COLORS["accent"]
            self.quality_canvas.create_rectangle(
                bar_start, 5, bar_start + fill_w, h - 5,
                fill=color, outline="",
            )

        # Text
        self.quality_canvas.create_text(
            bar_start + bar_w + 5, h / 2, text=f"{quality}%", anchor="w",
            fill=COLORS["text_primary"], font=("Helvetica", 9, "bold"),
        )

    def _draw_channel_chart(self, networks):
        """Draw channel utilization bar chart."""
        self.channel_canvas.delete("all")
        w = self.channel_canvas.winfo_width() or 750
        h = 120

        # Count networks per channel
        channel_counts = {}
        for net in networks:
            ch = net.get("channel", "")
            if ch:
                # Handle compound channels like "6,+1"
                base_ch = ch.split(",")[0].split("+")[0].split("-")[0].strip()
                try:
                    ch_num = int(base_ch)
                    channel_counts[ch_num] = channel_counts.get(ch_num, 0) + 1
                except ValueError:
                    pass

        if not channel_counts:
            self.channel_canvas.create_text(
                w / 2, h / 2, text="No channel data available",
                fill=COLORS["text_dim"], font=("Helvetica", 10),
            )
            return

        # 2.4 GHz channels: 1-14, 5 GHz: 36-165
        all_channels = sorted(channel_counts.keys())
        channels_2g = [c for c in range(1, 15) if c in channel_counts]
        channels_5g = [c for c in all_channels if c >= 36]

        display_channels = channels_2g + channels_5g
        if not display_channels:
            display_channels = all_channels

        max_count = max(channel_counts.values(), default=1)
        padding_left = 40
        padding_right = 10
        padding_top = 20
        padding_bottom = 25

        bar_area_w = w - padding_left - padding_right
        bar_area_h = h - padding_top - padding_bottom

        if len(display_channels) == 0:
            return

        bar_w = max(10, min(40, bar_area_w // len(display_channels) - 4))
        total_bars_w = len(display_channels) * (bar_w + 4)
        start_x = padding_left + (bar_area_w - total_bars_w) / 2

        # Y-axis
        self.channel_canvas.create_line(
            padding_left, padding_top, padding_left, h - padding_bottom,
            fill=COLORS["border"],
        )

        for i, ch in enumerate(display_channels):
            count = channel_counts.get(ch, 0)
            x = start_x + i * (bar_w + 4)
            bar_h = (count / max_count) * bar_area_h if max_count > 0 else 0

            # Determine color by band
            if ch <= 14:
                color = COLORS["accent_blue"]
            elif ch <= 64:
                color = COLORS["accent_green"]
            else:
                color = COLORS["accent_purple"]

            # Bar
            y_bottom = h - padding_bottom
            y_top = y_bottom - bar_h
            self.channel_canvas.create_rectangle(
                x, y_top, x + bar_w, y_bottom,
                fill=color, outline="",
            )

            # Count label
            if count > 0:
                self.channel_canvas.create_text(
                    x + bar_w / 2, y_top - 5, text=str(count),
                    fill=COLORS["text_primary"], font=("Helvetica", 7, "bold"),
                )

            # Channel label
            self.channel_canvas.create_text(
                x + bar_w / 2, h - padding_bottom + 10, text=str(ch),
                fill=COLORS["text_secondary"], font=("Helvetica", 7),
            )

        # Legend
        legend_x = w - 200
        for label, color in [("2.4 GHz", COLORS["accent_blue"]),
                              ("5 GHz Low", COLORS["accent_green"]),
                              ("5 GHz High", COLORS["accent_purple"])]:
            self.channel_canvas.create_rectangle(
                legend_x, 3, legend_x + 10, 13, fill=color, outline="",
            )
            self.channel_canvas.create_text(
                legend_x + 14, 8, text=label, anchor="w",
                fill=COLORS["text_secondary"], font=("Helvetica", 7),
            )
            legend_x += 65

    def update_data(self):
        """Refresh WiFi data."""
        # Get current connection info
        if self._system == "Linux":
            info, signal_dbm = self._get_wifi_info_linux()
        elif self._system == "Darwin":
            info, signal_dbm = self._get_wifi_info_macos()
        elif self._system == "Windows":
            info, signal_dbm = self._get_wifi_info_windows()
        else:
            info = {k: "Unsupported OS" for k in self.conn_info}
            signal_dbm = None

        # Update connection info
        for key, row in self.conn_info.items():
            row.set_value(info.get(key, "N/A"))

        # Update signal chart
        if signal_dbm is not None:
            self.signal_chart.add_point(signal_dbm)
            quality = self._dbm_to_quality(signal_dbm)
            self._draw_quality_bar(quality, info.get("ssid", ""))
        else:
            self._draw_quality_bar(0)

            # Check if WiFi is available at all
            if info.get("ssid", "N/A") == "N/A":
                self.no_wifi_label.config(
                    text="No WiFi connection detected. Connect to a WiFi network to see details."
                )
                self.no_wifi_label.pack(fill="x", padx=20, pady=5)

        # Scan for available networks every ~30 seconds
        self._scan_counter += 1
        if self._scan_counter >= 30 or not self._networks_cache:
            self._scan_counter = 0
            self.scan_status.config(text="Scanning...")

            if self._system == "Linux":
                self._networks_cache = self._scan_networks_linux()
            elif self._system == "Darwin":
                self._networks_cache = self._scan_networks_macos()
            elif self._system == "Windows":
                self._networks_cache = self._scan_networks_windows()

            self.scan_status.config(text=f"Found {len(self._networks_cache)} networks")

        # Update networks tree
        self.networks_tree.delete(*self.networks_tree.get_children())
        for net in self._networks_cache:
            quality = net.get("quality", 0)
            quality_str = f"{quality}%"
            if quality >= 70:
                quality_str += " (Good)"
            elif quality >= 40:
                quality_str += " (Fair)"
            elif quality > 0:
                quality_str += " (Weak)"

            freq_str = f"{net['frequency']:.1f}" if net.get("frequency", 0) > 0 else "N/A"

            self.networks_tree.insert("", "end", values=(
                net.get("ssid", ""),
                net.get("signal_dbm", "N/A"),
                quality_str,
                net.get("channel", "N/A"),
                freq_str,
                net.get("security", "Open"),
                net.get("bssid", ""),
            ))

        # Update channel chart
        if self._networks_cache:
            self._draw_channel_chart(self._networks_cache)
