"""Custom widgets for system resource monitoring - gauges, charts, and info panels."""

import tkinter as tk
from tkinter import ttk
import math
from collections import deque


# -- Color scheme --
COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_medium": "#16213e",
    "bg_light": "#0f3460",
    "accent": "#e94560",
    "accent_green": "#00b894",
    "accent_blue": "#0984e3",
    "accent_yellow": "#fdcb6e",
    "accent_orange": "#e17055",
    "accent_purple": "#a29bfe",
    "text_primary": "#ffffff",
    "text_secondary": "#b2bec3",
    "text_dim": "#636e72",
    "gauge_bg": "#2d3436",
    "chart_grid": "#2d3436",
    "border": "#2d3436",
}

# Severity colors for usage percentages
def get_usage_color(percent):
    """Return color based on usage percentage."""
    if percent < 50:
        return COLORS["accent_green"]
    elif percent < 75:
        return COLORS["accent_yellow"]
    elif percent < 90:
        return COLORS["accent_orange"]
    else:
        return COLORS["accent"]


class ArcGauge(tk.Canvas):
    """A circular arc gauge widget showing a percentage value."""

    def __init__(self, parent, size=150, thickness=12, label="", **kwargs):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=COLORS["bg_dark"],
            highlightthickness=0,
            **kwargs,
        )
        self.size = size
        self.thickness = thickness
        self.label = label
        self._value = 0
        self._draw()

    def _draw(self):
        self.delete("all")
        cx, cy = self.size / 2, self.size / 2
        r = (self.size - self.thickness) / 2 - 4
        start_angle = 225
        sweep = 270

        # Background arc
        self._draw_arc(cx, cy, r, start_angle, -sweep, COLORS["gauge_bg"])

        # Value arc
        if self._value > 0:
            value_sweep = (self._value / 100) * sweep
            color = get_usage_color(self._value)
            self._draw_arc(cx, cy, r, start_angle, -value_sweep, color)

        # Center text - percentage
        self.create_text(
            cx,
            cy - 8,
            text=f"{self._value:.1f}%",
            fill=COLORS["text_primary"],
            font=("Helvetica", int(self.size / 7), "bold"),
        )

        # Label text
        if self.label:
            self.create_text(
                cx,
                cy + int(self.size / 7) + 2,
                text=self.label,
                fill=COLORS["text_secondary"],
                font=("Helvetica", int(self.size / 14)),
            )

    def _draw_arc(self, cx, cy, r, start, extent, color):
        x1, y1 = cx - r, cy - r
        x2, y2 = cx + r, cy + r
        self.create_arc(
            x1, y1, x2, y2,
            start=start,
            extent=extent,
            style="arc",
            outline=color,
            width=self.thickness,
        )

    def set_value(self, value):
        self._value = max(0, min(100, value))
        self._draw()


class LineChart(tk.Canvas):
    """A real-time line chart widget with support for multiple data series."""

    def __init__(self, parent, width=400, height=150, max_points=60,
                 y_min=0, y_max=100, y_label="", series_colors=None,
                 series_labels=None, show_legend=True, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=COLORS["bg_dark"],
            highlightthickness=0,
            **kwargs,
        )
        self.chart_width = width
        self.chart_height = height
        self.max_points = max_points
        self.y_min = y_min
        self.y_max = y_max
        self.y_label = y_label
        self.show_legend = show_legend

        self.series_colors = series_colors or [COLORS["accent_blue"]]
        self.series_labels = series_labels or [""]
        self.num_series = len(self.series_colors)

        self.data = [deque(maxlen=max_points) for _ in range(self.num_series)]

        self.padding = {"left": 50, "right": 15, "top": 15, "bottom": 25}
        if show_legend and any(self.series_labels):
            self.padding["top"] = 30

        self._draw()

    def _draw(self):
        self.delete("all")
        pl, pr = self.padding["left"], self.padding["right"]
        pt, pb = self.padding["top"], self.padding["bottom"]
        plot_w = self.chart_width - pl - pr
        plot_h = self.chart_height - pt - pb

        # Draw grid lines and y-axis labels
        num_gridlines = 4
        for i in range(num_gridlines + 1):
            y = pt + (plot_h / num_gridlines) * i
            val = self.y_max - (self.y_max - self.y_min) * (i / num_gridlines)

            self.create_line(pl, y, pl + plot_w, y, fill=COLORS["chart_grid"], dash=(2, 4))
            self.create_text(
                pl - 5, y,
                text=f"{val:.0f}",
                anchor="e",
                fill=COLORS["text_dim"],
                font=("Helvetica", 8),
            )

        # Y-axis label
        if self.y_label:
            self.create_text(
                8, pt + plot_h / 2,
                text=self.y_label,
                angle=90,
                fill=COLORS["text_secondary"],
                font=("Helvetica", 8),
            )

        # Draw border
        self.create_rectangle(pl, pt, pl + plot_w, pt + plot_h, outline=COLORS["border"])

        # Draw each data series
        for s in range(self.num_series):
            points = list(self.data[s])
            if len(points) < 2:
                continue

            coords = []
            for i, val in enumerate(points):
                x = pl + (i / (self.max_points - 1)) * plot_w
                clamped = max(self.y_min, min(self.y_max, val))
                y = pt + plot_h - ((clamped - self.y_min) / max(1, self.y_max - self.y_min)) * plot_h
                coords.extend([x, y])

            if len(coords) >= 4:
                self.create_line(
                    *coords,
                    fill=self.series_colors[s],
                    width=2,
                    smooth=True,
                )

        # Draw legend
        if self.show_legend and any(self.series_labels):
            x_offset = pl
            for s in range(self.num_series):
                if not self.series_labels[s]:
                    continue
                self.create_rectangle(
                    x_offset, 5, x_offset + 12, 15,
                    fill=self.series_colors[s], outline="",
                )
                self.create_text(
                    x_offset + 16, 10,
                    text=self.series_labels[s],
                    anchor="w",
                    fill=COLORS["text_secondary"],
                    font=("Helvetica", 8),
                )
                x_offset += len(self.series_labels[s]) * 7 + 30

    def add_point(self, value, series=0):
        """Add a data point to a specific series."""
        if 0 <= series < self.num_series:
            self.data[series].append(value)
        self._draw()

    def add_points(self, values):
        """Add one data point to each series at once."""
        for s, val in enumerate(values):
            if s < self.num_series:
                self.data[s].append(val)
        self._draw()

    def set_y_range(self, y_min, y_max):
        """Dynamically update the Y-axis range."""
        self.y_min = y_min
        self.y_max = y_max
        self._draw()


class BarMeter(tk.Canvas):
    """A horizontal bar meter for showing usage."""

    def __init__(self, parent, width=300, height=22, label="", show_text=True, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=COLORS["bg_dark"],
            highlightthickness=0,
            **kwargs,
        )
        self.bar_width = width
        self.bar_height = height
        self.label = label
        self.show_text = show_text
        self._value = 0
        self._text = ""
        self._draw()

    def _draw(self):
        self.delete("all")
        h = self.bar_height
        label_offset = 0

        if self.label:
            self.create_text(
                0, h / 2,
                text=self.label,
                anchor="w",
                fill=COLORS["text_secondary"],
                font=("Helvetica", 9),
            )
            label_offset = len(self.label) * 7 + 10

        bar_x = label_offset
        bar_w = self.bar_width - label_offset
        if self.show_text:
            bar_w -= 60

        # Background bar
        self.create_rectangle(
            bar_x, 3, bar_x + bar_w, h - 3,
            fill=COLORS["gauge_bg"], outline="",
        )

        # Value bar
        if self._value > 0:
            fill_w = (self._value / 100) * bar_w
            color = get_usage_color(self._value)
            self.create_rectangle(
                bar_x, 3, bar_x + fill_w, h - 3,
                fill=color, outline="",
            )

        # Text value
        if self.show_text:
            display = self._text if self._text else f"{self._value:.1f}%"
            self.create_text(
                bar_x + bar_w + 5, h / 2,
                text=display,
                anchor="w",
                fill=COLORS["text_primary"],
                font=("Helvetica", 9),
            )

    def set_value(self, value, text=""):
        self._value = max(0, min(100, value))
        self._text = text
        self._draw()


class InfoRow(tk.Frame):
    """A key-value information row."""

    def __init__(self, parent, label, value="", **kwargs):
        super().__init__(parent, bg=COLORS["bg_dark"], **kwargs)
        self.label_widget = tk.Label(
            self,
            text=label,
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_dark"],
            font=("Helvetica", 10),
            anchor="w",
            width=20,
        )
        self.label_widget.pack(side="left", padx=(0, 10))

        self.value_widget = tk.Label(
            self,
            text=value,
            fg=COLORS["text_primary"],
            bg=COLORS["bg_dark"],
            font=("Helvetica", 10, "bold"),
            anchor="w",
        )
        self.value_widget.pack(side="left", fill="x", expand=True)

    def set_value(self, value):
        self.value_widget.config(text=str(value))


class SectionHeader(tk.Frame):
    """A section header with an accent bar."""

    def __init__(self, parent, text, **kwargs):
        super().__init__(parent, bg=COLORS["bg_dark"], **kwargs)

        accent = tk.Frame(self, bg=COLORS["accent_blue"], width=4)
        accent.pack(side="left", fill="y", padx=(0, 8))

        tk.Label(
            self,
            text=text,
            fg=COLORS["text_primary"],
            bg=COLORS["bg_dark"],
            font=("Helvetica", 12, "bold"),
            anchor="w",
        ).pack(side="left")


class ScrollableFrame(ttk.Frame):
    """A scrollable frame container."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.canvas = tk.Canvas(self, bg=COLORS["bg_dark"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORS["bg_dark"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas_frame = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind mousewheel
        self.scrollable_frame.bind("<Enter>", self._bind_mousewheel)
        self.scrollable_frame.bind("<Leave>", self._unbind_mousewheel)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
