# System Resource Monitor

A desktop application for real-time monitoring of local system resources including CPU, memory, disk, network, power/battery, and running processes.

Built with Python, tkinter, and psutil.

## Features

- **Overview Dashboard** - At-a-glance gauges for CPU, RAM, Disk, and Swap with live history charts and quick stats
- **CPU Monitor** - Overall and per-core usage, frequency, load average, CPU times breakdown, context switches, and usage history
- **Memory Monitor** - RAM and swap usage with detailed breakdowns (cached, buffers, active/inactive), live history chart
- **Disk Monitor** - All partition usage bars, disk I/O read/write speeds with auto-scaling chart
- **Network Monitor** - Bandwidth chart (download/upload), per-interface stats, connection summary (established, listening, etc.)
- **Power/Battery** - Battery charge gauge and history, power source status, time remaining, temperature sensors, fan speeds
- **Processes** - Sortable process list with CPU%, memory, threads, and user info; search/filter support

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
    ├── app.py                      # Main application window and update loop
    ├── widgets.py                  # Custom widgets (ArcGauge, LineChart, BarMeter, etc.)
    ├── overview_tab.py             # Overview dashboard tab
    ├── cpu_tab.py                  # CPU monitoring tab
    ├── memory_tab.py               # Memory monitoring tab
    ├── disk_tab.py                 # Disk monitoring tab
    ├── network_tab.py              # Network monitoring tab
    ├── power_tab.py                # Power/Battery/Thermal tab
    └── processes_tab.py            # Process list tab
```

## Screenshots

The application uses a dark theme with color-coded gauges:
- Green: < 50% usage
- Yellow: 50-75% usage
- Orange: 75-90% usage
- Red: > 90% usage

## License

MIT
