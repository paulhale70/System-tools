# System Resource Monitor

A desktop application for real-time monitoring of local system resources including CPU, memory, disk, network, WiFi, power/battery, and running processes.

Built with Python, tkinter, and psutil.

## Features

### Monitoring Tabs
- **Overview Dashboard** - At-a-glance gauges for CPU, RAM, Disk, and Swap with live history charts and quick stats
- **CPU Monitor** - Overall and per-core usage, frequency, load average, CPU times breakdown, context switches, and usage history
- **Memory Monitor** - RAM and swap usage with detailed breakdowns (cached, buffers, active/inactive), live history chart
- **Disk Monitor** - All partition usage bars, disk I/O read/write speeds with auto-scaling chart
- **Network Monitor** - Bandwidth chart, per-interface stats, per-process network connections, ping/latency monitor with live chart, connection summary
- **Power/Battery** - Battery charge gauge and history, power source status, time remaining, temperature sensors, fan speeds
- **WiFi Analyzer** - Current connection details, signal strength history, available networks scanner, channel utilization chart
- **Processes** - Sortable process list with search, right-click to kill/terminate, double-click for process detail view (open files, connections, children, environment variables)

### Process Management
- **Right-click context menu** on any process to Terminate (SIGTERM) or Kill (SIGKILL)
- **Process detail dialog** with tabbed view showing:
  - General info (PID, name, status, CPU/memory, executable, command line)
  - Open files with file descriptors
  - Network connections (protocol, local/remote address, status)
  - Child processes (recursive)
  - Environment variables

### Network Extras
- **Per-process network connections** - see which processes have active network connections
- **Ping/Latency monitor** - real-time ping to configurable targets (Google DNS, Cloudflare, OpenDNS presets) with latency chart, min/max/avg stats, and packet loss tracking

### WiFi Analyzer
- Current WiFi connection details (SSID, BSSID, signal, frequency, channel, security, IP)
- Signal strength history chart (dBm over time)
- Available networks scanner with signal quality, channel, and security info
- Channel utilization bar chart showing 2.4 GHz and 5 GHz band usage
- Cross-platform support (Linux/macOS/Windows)

### Visual Enhancements
- **Light/Dark theme toggle** - switch themes with a button in the top bar
- **Customizable refresh rate** - slider in the bottom bar to adjust from 500ms to 5000ms
- **Detachable tabs** - right-click any tab to pop it out into its own window for multi-monitor setups; closing the window reattaches the tab

## Requirements

- Python 3.7+
- tkinter (included with most Python installations)
- psutil

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python run.py
```

## Project Structure

```
System-tools/
├── run.py                          # Entry point
├── requirements.txt                # Dependencies
├── README.md
└── system_monitor/
    ├── __init__.py
    ├── app.py                      # Main window, theme toggle, refresh slider, tab detach
    ├── widgets.py                  # Custom widgets + theme system (dark/light)
    ├── overview_tab.py             # Overview dashboard tab
    ├── cpu_tab.py                  # CPU monitoring tab
    ├── memory_tab.py               # Memory monitoring tab
    ├── disk_tab.py                 # Disk monitoring tab
    ├── network_tab.py              # Network + ping/latency + per-process connections
    ├── power_tab.py                # Power/Battery/Thermal tab
    ├── wifi_tab.py                 # WiFi analyzer tab
    └── processes_tab.py            # Process list + kill + detail view
```

## Color-Coded Severity

The application uses color-coded gauges and bars:
- Green: < 50% usage
- Yellow: 50-75% usage
- Orange: 75-90% usage
- Red: > 90% usage

## License

MIT
