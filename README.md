# System Resource Monitor

A desktop application for real-time monitoring of local system resources including CPU, memory, disk, network, WiFi, power/battery, GPU, security, and running processes.

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
- **GPU Monitor** - NVIDIA GPU utilization, VRAM usage, temperature, fan speed, power draw, clock speeds, PCIe info (requires pynvml or GPUtil)
- **Processes** - Sortable process list with search, right-click to kill/terminate, double-click for process detail view (open files, connections, children, environment variables)
- **Security** - Open ports scanner with risk assessment, process anomaly detection with configurable thresholds

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

### GPU Monitoring
- NVIDIA GPU utilization and VRAM usage gauges
- Temperature, fan speed, and power draw tracking
- GPU/memory clock speeds and PCIe link info
- Driver version and GPU name display
- Graceful fallback when no GPU or drivers detected

### Security
- **Open Ports Scanner** - Lists all TCP/UDP listening ports with process info, service names, and risk assessment (Low/Medium/High)
- **Process Anomaly Detection** - Flags processes exceeding configurable CPU/memory thresholds
- **Whitelist** - "Learn Current as Normal" to baseline known processes; flags unknown processes with significant resource use

### Data & Logging
- **CSV/JSON export** - Log system metrics (CPU, memory, disk, network) to CSV or JSON files
- **Session snapshots** - Generate full system reports in HTML or plain text format
- **Headless mode** - Run without GUI for server monitoring and logging

### Alerts & Notifications
- **Configurable alerts** for CPU, RAM, Disk, and Swap usage thresholds
- **Desktop notifications** via notify-send (Linux) / osascript (macOS)
- **Alert log** showing recent triggered alerts with timestamps
- **Per-alert enable/disable** and cooldown to prevent notification spam

### Visual Enhancements
- **Light/Dark theme toggle** - switch themes with a button in the top bar
- **Customizable refresh rate** - slider in the bottom bar to adjust from 500ms to 5000ms
- **Detachable tabs** - right-click any tab to pop it out into its own window for multi-monitor setups; closing the window reattaches the tab

### Keyboard Shortcuts
- **Ctrl+1 through Ctrl+0** - Switch to tab 1-10
- **Ctrl+Q** - Quit application
- **F5** - Force refresh
- **Ctrl+S** - Save system snapshot
- **Ctrl+L** - Toggle data logging

## Requirements

- Python 3.7+
- tkinter (included with most Python installations)
- psutil

### Optional Dependencies

For GPU monitoring (NVIDIA):
```bash
pip install pynvml
# or
pip install GPUtil
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### GUI Mode
```bash
python run.py
```

### Command-Line Options
```bash
python run.py --theme light          # Start with light theme
python run.py --refresh 2000         # Set refresh rate to 2000ms
python run.py --snapshot report.html  # Generate system snapshot and exit
python run.py --snapshot report.txt   # Plain text snapshot
```

### Headless Mode (no GUI)
```bash
python run.py --headless                           # Log to stdout as CSV
python run.py --headless --format json             # Log as JSON
python run.py --headless --output metrics.csv      # Log to file
python run.py --headless --duration 60             # Log for 60 seconds
python run.py --headless --refresh 5000            # Log every 5 seconds
```

## Project Structure

```
System-tools/
├── run.py                          # Entry point
├── requirements.txt                # Dependencies
├── README.md
└── system_monitor/
    ├── __init__.py
    ├── app.py                      # Main window, theme, refresh, tabs, CLI args
    ├── widgets.py                  # Custom widgets + theme system (dark/light)
    ├── overview_tab.py             # Overview dashboard tab
    ├── cpu_tab.py                  # CPU monitoring tab
    ├── memory_tab.py               # Memory monitoring tab
    ├── disk_tab.py                 # Disk monitoring tab
    ├── network_tab.py              # Network + ping/latency + per-process connections
    ├── power_tab.py                # Power/Battery/Thermal tab
    ├── wifi_tab.py                 # WiFi analyzer tab
    ├── gpu_tab.py                  # GPU monitoring tab (NVIDIA)
    ├── processes_tab.py            # Process list + kill + detail view
    ├── security_tab.py             # Open ports + anomaly detection
    ├── data_export.py              # CSV/JSON export + snapshots + headless mode
    └── alerts.py                   # Alert rules + notifications + config dialog
```

## Color-Coded Severity

The application uses color-coded gauges and bars:
- Green: < 50% usage
- Yellow: 50-75% usage
- Orange: 75-90% usage
- Red: > 90% usage

## License

MIT
