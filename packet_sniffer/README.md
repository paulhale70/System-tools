# Packet Sniffer

A standalone network packet capture and analysis tool with a graphical interface.

Built with Python, tkinter, and scapy.

## Features

- **Live packet capture** on selected network interface
- **BPF filter support** (e.g., `tcp port 80`, `host 192.168.1.1`)
- **Protocol detection** (TCP, UDP, ICMP, DNS, HTTP, HTTPS, SSH, ARP, etc.)
- **Color-coded protocols** for easy identification
- **Display filters** - filter captured packets by protocol, IP, or port
- **Packet details view** with layer breakdown
- **Hex dump view** of raw packet data
- **Real-time statistics** - packet count, bytes, rate, protocol breakdown
- **Export to CSV** - save packet list as CSV file
- **Export to PCAP** - save raw packets for Wireshark analysis

## Requirements

- Python 3.7+
- tkinter (included with most Python installations)
- scapy

### Windows Additional Requirements

On Windows, you must install **Npcap** for packet capture:
1. Download from https://npcap.com
2. Install with "WinPcap API-compatible Mode" checked

## Installation

```bash
pip install scapy
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

## Usage

**Important:** Packet capture requires elevated privileges.

### Linux / macOS
```bash
sudo python sniffer.py
```

### Windows
Run Command Prompt or PowerShell as Administrator, then:
```cmd
python sniffer.py
```

## Interface Guide

### Toolbar
- **Interface** - Select the network interface to capture on
- **BPF Filter** - Enter a Berkeley Packet Filter expression (optional)
- **Start Capture** - Begin capturing packets
- **Stop** - Stop the current capture
- **Clear** - Clear all captured packets
- **Export CSV** - Save packet list to CSV file
- **Export PCAP** - Save raw packets to PCAP file (compatible with Wireshark)

### Display Filters
- **Protocol** - Filter by protocol type (TCP, UDP, DNS, etc.)
- **IP** - Filter by source or destination IP address
- **Port** - Filter by source or destination port

### Packet List
Click any packet to see its details below. Packets are color-coded by protocol:
- Blue: TCP
- Purple: UDP
- Yellow: DNS
- Orange: ICMP
- Pink: ARP
- Cyan: SSH
- Teal: HTTP/HTTPS

### Details Panel
- **Packet Info** - Layer breakdown and summary
- **Hex Dump** - Hexadecimal representation of packet bytes
- **Raw Data** - ASCII representation of packet data

### Status Bar
- Packet count
- Total bytes captured
- Capture rate (packets/second)
- Protocol breakdown

## BPF Filter Examples

```
tcp                     # All TCP packets
udp port 53             # DNS traffic
host 192.168.1.1        # Traffic to/from specific IP
tcp port 80 or port 443 # HTTP and HTTPS
icmp                    # Ping/ICMP traffic
not broadcast           # Exclude broadcast packets
src net 192.168.1.0/24  # Traffic from local subnet
```

## Troubleshooting

### "No module named 'scapy'"
Install scapy: `pip install scapy`

### "Permission denied" / "Operation not permitted"
Run with elevated privileges (sudo on Linux/macOS, Administrator on Windows)

### No interfaces listed (Windows)
1. Install Npcap from https://npcap.com
2. Make sure "WinPcap API-compatible Mode" is checked during installation
3. Restart the application

### Capture not working
- Check that you have network connectivity
- Try selecting a specific interface instead of "all"
- On WiFi, you'll only see traffic to/from your machine (not other devices)

## Notes

- This tool captures packets on your network interfaces in promiscuous mode
- You will see all traffic on wired networks (if your switch allows it)
- On WiFi, you typically only see your own traffic unless the adapter supports monitor mode
- Monitor mode (for capturing all WiFi traffic) is mostly Linux-only and requires compatible hardware

## License

MIT
