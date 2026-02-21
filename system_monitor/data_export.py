"""Data export - CSV/JSON logging and HTML/text session snapshots."""

import csv
import json
import os
import time
import datetime
import threading
import psutil
import platform


def fmt_bytes(b):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


class DataLogger:
    """Continuously logs system metrics to CSV or JSON files."""

    def __init__(self, output_dir=".", fmt="csv", interval=1.0):
        self.output_dir = output_dir
        self.fmt = fmt
        self.interval = interval
        self._running = False
        self._thread = None
        self._filepath = None

    def start(self, filepath=None):
        """Start logging to file."""
        if self._running:
            return self._filepath

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if filepath is None:
            ext = "csv" if self.fmt == "csv" else "jsonl"
            filepath = os.path.join(self.output_dir, f"sysmon_log_{timestamp}.{ext}")

        self._filepath = filepath
        self._running = True

        if self.fmt == "csv":
            with open(self._filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "cpu_percent", "cpu_freq_mhz",
                    "ram_percent", "ram_used_bytes", "ram_total_bytes",
                    "swap_percent", "swap_used_bytes",
                    "disk_percent", "disk_used_bytes", "disk_total_bytes",
                    "net_bytes_sent", "net_bytes_recv",
                    "process_count",
                ])

        self._thread = threading.Thread(target=self._log_loop, daemon=True)
        self._thread.start()
        return self._filepath

    def stop(self):
        """Stop logging."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    @property
    def is_running(self):
        return self._running

    @property
    def filepath(self):
        return self._filepath

    def _collect_sample(self):
        """Collect a single data sample."""
        cpu_pct = psutil.cpu_percent(interval=0)
        try:
            freq = psutil.cpu_freq()
            cpu_freq = freq.current if freq else 0
        except Exception:
            cpu_freq = 0

        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        try:
            disk = psutil.disk_usage("/")
        except Exception:
            disk = None

        net = psutil.net_io_counters()

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "cpu_percent": round(cpu_pct, 2),
            "cpu_freq_mhz": round(cpu_freq, 1),
            "ram_percent": round(mem.percent, 2),
            "ram_used_bytes": mem.used,
            "ram_total_bytes": mem.total,
            "swap_percent": round(swap.percent, 2),
            "swap_used_bytes": swap.used,
            "disk_percent": round(disk.percent, 2) if disk else 0,
            "disk_used_bytes": disk.used if disk else 0,
            "disk_total_bytes": disk.total if disk else 0,
            "net_bytes_sent": net.bytes_sent,
            "net_bytes_recv": net.bytes_recv,
            "process_count": len(psutil.pids()),
        }

    def _log_loop(self):
        """Background logging loop."""
        while self._running:
            try:
                sample = self._collect_sample()

                if self.fmt == "csv":
                    with open(self._filepath, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(sample.values())
                else:
                    with open(self._filepath, "a") as f:
                        f.write(json.dumps(sample) + "\n")
            except Exception:
                pass

            time.sleep(self.interval)


def generate_snapshot(filepath=None, fmt="html"):
    """Generate a full system snapshot report."""
    timestamp = datetime.datetime.now()

    if filepath is None:
        ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
        ext = "html" if fmt == "html" else "txt"
        filepath = f"sysmon_snapshot_{ts_str}.{ext}"

    data = _collect_full_snapshot(timestamp)

    if fmt == "html":
        content = _render_html(data)
    else:
        content = _render_text(data)

    with open(filepath, "w") as f:
        f.write(content)

    return filepath


def _collect_full_snapshot(timestamp):
    """Gather all system information for a snapshot."""
    uname = platform.uname()
    cpu_pct = psutil.cpu_percent(interval=0.5)
    per_core = psutil.cpu_percent(interval=0, percpu=True)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    try:
        freq = psutil.cpu_freq()
    except Exception:
        freq = None

    try:
        load = psutil.getloadavg()
    except Exception:
        load = None

    partitions = []
    for p in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(p.mountpoint)
            partitions.append({
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            })
        except Exception:
            pass

    net = psutil.net_io_counters()
    net_addrs = psutil.net_if_addrs()

    try:
        connections = psutil.net_connections(kind="inet")
        conn_summary = {}
        for c in connections:
            conn_summary[c.status] = conn_summary.get(c.status, 0) + 1
    except Exception:
        connections = []
        conn_summary = {}

    battery = psutil.sensors_battery()
    try:
        temps = psutil.sensors_temperatures()
    except Exception:
        temps = {}

    boot_time = psutil.boot_time()
    uptime_secs = time.time() - boot_time
    uptime_str = str(datetime.timedelta(seconds=int(uptime_secs)))

    # Top processes by CPU
    top_procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "username"]):
        try:
            top_procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    top_procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)

    # Listening ports
    listening = []
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status == "LISTEN" and c.laddr:
                name = ""
                if c.pid:
                    try:
                        name = psutil.Process(c.pid).name()
                    except Exception:
                        pass
                listening.append({
                    "port": c.laddr.port,
                    "address": c.laddr.ip,
                    "pid": c.pid or 0,
                    "process": name,
                })
    except Exception:
        pass

    return {
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "system": {
            "hostname": uname.node,
            "os": f"{uname.system} {uname.release}",
            "arch": uname.machine,
            "python": platform.python_version(),
            "uptime": uptime_str,
            "boot_time": datetime.datetime.fromtimestamp(boot_time).strftime("%Y-%m-%d %H:%M:%S"),
        },
        "cpu": {
            "percent": cpu_pct,
            "per_core": per_core,
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
            "freq_current": freq.current if freq else 0,
            "freq_max": freq.max if freq else 0,
            "load_avg": load,
        },
        "memory": {
            "ram_total": mem.total,
            "ram_used": mem.used,
            "ram_available": mem.available,
            "ram_percent": mem.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
        },
        "disks": partitions,
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "connections": conn_summary,
            "interfaces": {name: [str(a.address) for a in addrs] for name, addrs in net_addrs.items()},
        },
        "battery": {
            "percent": battery.percent if battery else None,
            "plugged": battery.power_plugged if battery else None,
            "secs_left": battery.secsleft if battery else None,
        },
        "temperatures": {name: [{"label": s.label, "current": s.current} for s in sensors]
                         for name, sensors in temps.items()} if temps else {},
        "top_processes": top_procs[:20],
        "listening_ports": listening,
    }


def _render_text(data):
    """Render snapshot as plain text."""
    lines = []
    lines.append("=" * 70)
    lines.append("SYSTEM RESOURCE MONITOR - SNAPSHOT REPORT")
    lines.append(f"Generated: {data['timestamp']}")
    lines.append("=" * 70)

    s = data["system"]
    lines.append(f"\n--- SYSTEM ---")
    lines.append(f"Hostname:    {s['hostname']}")
    lines.append(f"OS:          {s['os']}")
    lines.append(f"Arch:        {s['arch']}")
    lines.append(f"Uptime:      {s['uptime']}")
    lines.append(f"Boot Time:   {s['boot_time']}")

    c = data["cpu"]
    lines.append(f"\n--- CPU ---")
    lines.append(f"Usage:       {c['percent']}%")
    lines.append(f"Cores:       {c['cores_physical']} physical / {c['cores_logical']} logical")
    lines.append(f"Frequency:   {c['freq_current']:.0f} MHz (max: {c['freq_max']:.0f} MHz)")
    if c["load_avg"]:
        lines.append(f"Load Avg:    {c['load_avg'][0]:.2f}, {c['load_avg'][1]:.2f}, {c['load_avg'][2]:.2f}")
    lines.append(f"Per-core:    {', '.join(f'{v:.1f}%' for v in c['per_core'])}")

    m = data["memory"]
    lines.append(f"\n--- MEMORY ---")
    lines.append(f"RAM:         {m['ram_percent']}% ({fmt_bytes(m['ram_used'])} / {fmt_bytes(m['ram_total'])})")
    lines.append(f"Swap:        {m['swap_percent']}% ({fmt_bytes(m['swap_used'])} / {fmt_bytes(m['swap_total'])})")

    lines.append(f"\n--- DISKS ---")
    for d in data["disks"]:
        lines.append(f"  {d['device']} ({d['mountpoint']}) [{d['fstype']}]")
        lines.append(f"    {d['percent']}% ({fmt_bytes(d['used'])} / {fmt_bytes(d['total'])})")

    n = data["network"]
    lines.append(f"\n--- NETWORK ---")
    lines.append(f"Sent:        {fmt_bytes(n['bytes_sent'])}")
    lines.append(f"Received:    {fmt_bytes(n['bytes_recv'])}")
    lines.append(f"Connections: {n['connections']}")

    b = data["battery"]
    if b["percent"] is not None:
        lines.append(f"\n--- BATTERY ---")
        lines.append(f"Charge:      {b['percent']}%")
        lines.append(f"Plugged:     {'Yes' if b['plugged'] else 'No'}")

    if data["listening_ports"]:
        lines.append(f"\n--- LISTENING PORTS ---")
        lines.append(f"  {'Port':<8}{'Address':<20}{'PID':<8}{'Process'}")
        lines.append(f"  {'-' * 50}")
        for p in sorted(data["listening_ports"], key=lambda x: x["port"]):
            lines.append(f"  {p['port']:<8}{p['address']:<20}{p['pid']:<8}{p['process']}")

    lines.append(f"\n--- TOP PROCESSES (by CPU) ---")
    lines.append(f"  {'PID':<8}{'Name':<25}{'CPU %':<10}{'Mem %':<10}{'User'}")
    lines.append(f"  {'-' * 60}")
    for p in data["top_processes"]:
        lines.append(
            f"  {p.get('pid', 0):<8}{(p.get('name') or ''):<25}"
            f"{(p.get('cpu_percent') or 0):<10.1f}{(p.get('memory_percent') or 0):<10.1f}"
            f"{p.get('username') or ''}"
        )

    lines.append(f"\n{'=' * 70}")
    return "\n".join(lines) + "\n"


def _render_html(data):
    """Render snapshot as an HTML report."""
    s = data["system"]
    c = data["cpu"]
    m = data["memory"]
    n = data["network"]
    b = data["battery"]

    def pct_color(v):
        if v < 50:
            return "#00b894"
        elif v < 75:
            return "#fdcb6e"
        elif v < 90:
            return "#e17055"
        return "#e94560"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>System Snapshot - {data['timestamp']}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #1a1a2e; color: #fff; margin: 0; padding: 20px; }}
h1 {{ color: #0984e3; border-bottom: 2px solid #0984e3; padding-bottom: 8px; }}
h2 {{ color: #a29bfe; margin-top: 30px; }}
.card {{ background: #16213e; border-radius: 8px; padding: 15px; margin: 10px 0; }}
table {{ border-collapse: collapse; width: 100%; }}
th {{ text-align: left; padding: 8px 12px; background: #0f3460; color: #b2bec3; font-size: 13px; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #2d3436; font-size: 13px; }}
.pct-bar {{ background: #2d3436; border-radius: 4px; height: 20px; position: relative; }}
.pct-fill {{ border-radius: 4px; height: 100%; }}
.pct-text {{ position: absolute; top: 0; left: 8px; line-height: 20px; font-size: 12px; font-weight: bold; }}
.meta {{ color: #636e72; font-size: 12px; margin-top: 20px; }}
</style></head><body>
<h1>System Resource Monitor - Snapshot</h1>
<p style="color:#b2bec3">Generated: {data['timestamp']}</p>

<h2>System</h2>
<div class="card">
<table>
<tr><td>Hostname</td><td><b>{s['hostname']}</b></td></tr>
<tr><td>OS</td><td>{s['os']}</td></tr>
<tr><td>Architecture</td><td>{s['arch']}</td></tr>
<tr><td>Uptime</td><td>{s['uptime']}</td></tr>
<tr><td>Boot Time</td><td>{s['boot_time']}</td></tr>
</table></div>

<h2>CPU</h2>
<div class="card">
<div class="pct-bar"><div class="pct-fill" style="width:{c['percent']}%;background:{pct_color(c['percent'])}"></div>
<span class="pct-text">{c['percent']}%</span></div>
<table>
<tr><td>Cores</td><td>{c['cores_physical']} physical / {c['cores_logical']} logical</td></tr>
<tr><td>Frequency</td><td>{c['freq_current']:.0f} MHz</td></tr>
{'<tr><td>Load Avg</td><td>' + ', '.join(f'{v:.2f}' for v in c['load_avg']) + '</td></tr>' if c['load_avg'] else ''}
</table></div>

<h2>Memory</h2>
<div class="card">
<p><b>RAM</b></p>
<div class="pct-bar"><div class="pct-fill" style="width:{m['ram_percent']}%;background:{pct_color(m['ram_percent'])}"></div>
<span class="pct-text">{m['ram_percent']}% ({fmt_bytes(m['ram_used'])} / {fmt_bytes(m['ram_total'])})</span></div>
<p style="margin-top:10px"><b>Swap</b></p>
<div class="pct-bar"><div class="pct-fill" style="width:{m['swap_percent']}%;background:{pct_color(m['swap_percent'])}"></div>
<span class="pct-text">{m['swap_percent']}% ({fmt_bytes(m['swap_used'])} / {fmt_bytes(m['swap_total'])})</span></div>
</div>

<h2>Disk</h2>
<div class="card"><table><tr><th>Device</th><th>Mount</th><th>Type</th><th>Used</th><th>Total</th><th>Usage</th></tr>
"""
    for d in data["disks"]:
        html += f"""<tr><td>{d['device']}</td><td>{d['mountpoint']}</td><td>{d['fstype']}</td>
<td>{fmt_bytes(d['used'])}</td><td>{fmt_bytes(d['total'])}</td>
<td><div class="pct-bar" style="width:150px;display:inline-block">
<div class="pct-fill" style="width:{d['percent']}%;background:{pct_color(d['percent'])}"></div>
<span class="pct-text">{d['percent']}%</span></div></td></tr>"""

    html += f"""</table></div>

<h2>Network</h2>
<div class="card"><table>
<tr><td>Total Sent</td><td>{fmt_bytes(n['bytes_sent'])}</td></tr>
<tr><td>Total Received</td><td>{fmt_bytes(n['bytes_recv'])}</td></tr>
<tr><td>Connections</td><td>{n['connections']}</td></tr>
</table></div>
"""

    if b["percent"] is not None:
        html += f"""<h2>Battery</h2>
<div class="card">
<div class="pct-bar"><div class="pct-fill" style="width:{b['percent']}%;background:{pct_color(100 - b['percent'])}"></div>
<span class="pct-text">{b['percent']}%</span></div>
<p>Power: {'Plugged In' if b['plugged'] else 'On Battery'}</p>
</div>"""

    if data["listening_ports"]:
        html += """<h2>Listening Ports</h2>
<div class="card"><table><tr><th>Port</th><th>Address</th><th>PID</th><th>Process</th></tr>"""
        for p in sorted(data["listening_ports"], key=lambda x: x["port"]):
            html += f"<tr><td>{p['port']}</td><td>{p['address']}</td><td>{p['pid']}</td><td>{p['process']}</td></tr>"
        html += "</table></div>"

    html += """<h2>Top Processes (by CPU)</h2>
<div class="card"><table><tr><th>PID</th><th>Name</th><th>CPU %</th><th>Mem %</th><th>User</th></tr>"""
    for p in data["top_processes"]:
        html += (f"<tr><td>{p.get('pid', 0)}</td><td>{p.get('name', '')}</td>"
                 f"<td>{(p.get('cpu_percent') or 0):.1f}</td>"
                 f"<td>{(p.get('memory_percent') or 0):.1f}</td>"
                 f"<td>{p.get('username', '')}</td></tr>")

    html += f"""</table></div>
<p class="meta">Generated by System Resource Monitor</p>
</body></html>"""

    return html


def headless_log(fmt="csv", interval=1.0, output=None, duration=None):
    """Run headless logging to stdout or file."""
    import signal

    running = [True]

    def handle_signal(sig, frame):
        running[0] = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Initial CPU sample
    psutil.cpu_percent(interval=0)

    start_time = time.time()
    file_handle = None
    csv_writer = None

    if output:
        file_handle = open(output, "w", newline="" if fmt == "csv" else None)

    try:
        if fmt == "csv":
            header = [
                "timestamp", "cpu_percent", "cpu_freq_mhz",
                "ram_percent", "ram_used_bytes", "ram_total_bytes",
                "swap_percent", "net_bytes_sent", "net_bytes_recv",
                "process_count",
            ]
            if file_handle:
                csv_writer = csv.writer(file_handle)
                csv_writer.writerow(header)
            else:
                print(",".join(header))

        while running[0]:
            if duration and (time.time() - start_time) >= duration:
                break

            cpu_pct = psutil.cpu_percent(interval=0)
            try:
                freq = psutil.cpu_freq()
                cpu_freq = freq.current if freq else 0
            except Exception:
                cpu_freq = 0
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            net = psutil.net_io_counters()
            procs = len(psutil.pids())

            ts = datetime.datetime.now().isoformat()

            if fmt == "csv":
                row = [ts, f"{cpu_pct:.2f}", f"{cpu_freq:.1f}",
                       f"{mem.percent:.2f}", mem.used, mem.total,
                       f"{swap.percent:.2f}", net.bytes_sent, net.bytes_recv, procs]
                if csv_writer:
                    csv_writer.writerow(row)
                    file_handle.flush()
                else:
                    print(",".join(str(v) for v in row))
            else:
                record = {
                    "timestamp": ts,
                    "cpu_percent": round(cpu_pct, 2),
                    "cpu_freq_mhz": round(cpu_freq, 1),
                    "ram_percent": round(mem.percent, 2),
                    "ram_used": mem.used,
                    "ram_total": mem.total,
                    "swap_percent": round(swap.percent, 2),
                    "net_sent": net.bytes_sent,
                    "net_recv": net.bytes_recv,
                    "processes": procs,
                }
                line = json.dumps(record)
                if file_handle:
                    file_handle.write(line + "\n")
                    file_handle.flush()
                else:
                    print(line)

            time.sleep(interval)

    finally:
        if file_handle:
            file_handle.close()
