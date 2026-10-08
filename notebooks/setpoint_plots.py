"""Interactive chiller set-point figure for the SOTN-012 technote (RSO-901).

Shared by the *Date Range* notebook (which queries the EFD on the RSP) so the
figure embedded in the technote can be regenerated for any ``day_obs`` range.
"""

import pandas as pd
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, HoverTool, Label, Range1d, Span
from bokeh.plotting import figure

# device_id (DeviceId_chiller enum) -> (label, colour). Colours are the first
# three slots of a CVD-validated categorical palette. Chiller 04 (coating) has
# never published a chillerConfiguration event, so it has no series.
CHILLERS = {
    101: ("Chiller 01 (cold, EAS)", "#2a78d6"),
    102: ("Chiller 02 (cold, EAS)", "#eb6834"),
    103: ("Chiller 03 (comfort)", "#1baf7a"),
    104: ("Chiller 04 (coating)", "#4a3aa7"),
}
EVENT_COLOR = "#6b6a66"  # neutral gray: incidents are context, not a series
GRID = "#e6e5e1"


def genuine_changes(df):
    """Keep the first row and every real change of ``activeSetpoint`` per chiller."""
    df = df.sort_index()
    moved = df.groupby("device_id")["activeSetpoint"].diff().ne(0)
    return df[moved].rename_axis("time").reset_index()


def _style(p):
    p.background_fill_color = "white"
    p.border_fill_color = "white"
    p.outline_line_color = None
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = GRID
    for ax in (p.xaxis, p.yaxis):
        ax.axis_line_color = "#b8b7b1"
        ax.major_tick_line_color = "#b8b7b1"
        ax.minor_tick_line_color = None
        ax.major_label_text_color = "#52514e"
        ax.axis_label_text_color = "#52514e"
        ax.axis_label_text_font_style = "normal"
    p.title.text_color = "#0b0b0b"
    p.title.text_font_size = "11pt"
    p.toolbar.logo = None


def build_technote_figure(df, events_win, x_lo, x_hi, freq="W-MON"):
    """Two stacked panels sharing the time axis.

    Top: each chiller's active set point as a step line (held to ``x_hi``),
    with catalogued cooling incidents as dashed vertical lines.
    Bottom: number of genuine set-point changes per chiller per ``freq`` bin.

    Parameters
    ----------
    df : `pandas.DataFrame`
        ``logevent_chillerConfiguration`` rows indexed by (naive UTC) time,
        with ``device_id`` and ``activeSetpoint`` columns.
    events_win : `pandas.DataFrame`
        Incidents inside the window, with ``t`` (naive UTC), ``event_id``,
        ``outcome`` and ``fracas_ticket`` columns.
    x_lo, x_hi : `datetime.datetime`
        Naive UTC window limits.
    """
    x_range = Range1d(start=x_lo, end=x_hi)
    tools = "xpan,xwheel_zoom,box_zoom,reset,save"

    top = figure(
        height=380,
        sizing_mode="stretch_width",
        x_axis_type="datetime",
        x_range=x_range,
        title="Active set point per chiller (logevent_chillerConfiguration)",
        tools=tools,
        active_scroll="xwheel_zoom",
    )
    bottom = figure(
        height=220,
        sizing_mode="stretch_width",
        x_axis_type="datetime",
        x_range=x_range,
        title="Set-point changes per week",
        tools=tools,
        active_scroll="xwheel_zoom",
    )

    changes = genuine_changes(df)
    # Bin labels are the week's closing Monday; include the partial last week.
    bins = pd.date_range(pd.Timestamp(x_lo).floor("D"), pd.Timestamp(x_hi) + pd.Timedelta(days=7), freq=freq)
    width_ms = (bins[1] - bins[0]).total_seconds() * 1e3 if len(bins) > 1 else 6e8
    present = [d for d in CHILLERS if (df["device_id"] == d).any()]
    bar_w = 0.9 * width_ms / max(len(present), 1)

    for k, dev_id in enumerate(present):
        name, color = CHILLERS[dev_id]
        g = df[df["device_id"] == dev_id].sort_index()
        src = ColumnDataSource(
            dict(
                x=list(g.index) + [x_hi],
                y=list(g["activeSetpoint"]) + [g["activeSetpoint"].iloc[-1]],
            )
        )
        step = top.step(
            "x", "y", source=src, mode="after",
            line_color=color, line_width=2, legend_label=name,
        )
        top.add_tools(
            HoverTool(
                renderers=[step],
                tooltips=[("", name), ("time", "@x{%F %H:%M} UTC"),
                          ("set point", "@y{0.0} °C")],
                formatters={"@x": "datetime"},
            )
        )

        c = changes[changes["device_id"] == dev_id].iloc[1:]  # first row is not a change
        counts = (
            c.set_index("time")["activeSetpoint"].resample(freq).count()
            .reindex(bins, fill_value=0)
        )
        offset = (k - (len(present) - 1) / 2) * bar_w
        bsrc = ColumnDataSource(
            dict(x=counts.index + pd.to_timedelta(offset - width_ms / 2, unit="ms"),
                 week=counts.index - pd.Timedelta(days=7), n=counts.values)
        )
        bars = bottom.vbar(
            x="x", top="n", width=bar_w * 0.85, source=bsrc,
            fill_color=color, line_color=None, legend_label=name,
        )
        bottom.add_tools(
            HoverTool(
                renderers=[bars],
                tooltips=[("", name), ("week of", "@week{%F}"), ("changes", "@n")],
                formatters={"@week": "datetime"},
            )
        )

    for _, ev in events_win.iterrows():
        for p in (top, bottom):
            p.add_layout(Span(location=ev["t"], dimension="height",
                              line_color=EVENT_COLOR, line_dash="dashed", line_width=1.5))
        # Short tag only (the event_id); ticket details live in the events table.
        top.add_layout(
            Label(x=ev["t"], y=6, y_units="screen", x_offset=-4, text_align="right",
                  text=f"#{int(ev['event_id'])}",
                  text_color="#52514e", text_font_size="8pt",
                  background_fill_color="white", background_fill_alpha=0.8)
        )

    top.yaxis.axis_label = "Set point [°C]"
    bottom.yaxis.axis_label = "Changes"
    bottom.xaxis.axis_label = "Time [UTC]"
    bottom.y_range.start = 0
    for p in (top, bottom):
        _style(p)
        p.legend.orientation = "horizontal"
        p.legend.click_policy = "hide"
        p.legend.label_text_font_size = "9pt"
        p.legend.label_text_color = "#0b0b0b"
        p.legend.background_fill_alpha = 0.85
        p.legend.border_line_color = None
    bottom.legend.visible = False
    top.add_layout(top.legend[0], "above")
    top.xaxis.major_label_text_font_size = "0pt"

    return column(top, bottom, sizing_mode="stretch_width")


# Chiller names used by the *Command Response* notebook -> device_id above.
EAS_CHILLERS = {"chiller01": 101, "chiller02": 102}
SMALL_COLOR = "#b8b7b1"  # sub-threshold mismatches: present, but not of interest


def daily_mismatch(judged, large_c):
    """Per UTC day: hours mismatched (small and large) and the worst signed error.

    Parameters
    ----------
    judged : `pandas.DataFrame`
        Judged commands of one chiller, indexed by (naive UTC) time, with the
        ``interval_min``, ``mismatch``, ``large`` and ``error`` columns built
        by the *Command Response* notebook.
    large_c : `float`
        Threshold for a large mismatch, in °C; only used for the tooltip.
    """
    small = judged["mismatch"] & ~judged["large"]
    out = pd.DataFrame({
        "small_h": (judged["interval_min"] * small).resample("D").sum() / 60,
        "large_h": (judged["interval_min"] * judged["large"]).resample("D").sum() / 60,
    })
    m = judged[judged["mismatch"]]
    worst = (
        m.assign(day=m.index.floor("D"), abs_err=m["error"].abs())
        .sort_values("abs_err")
        .groupby("day")["error"].last()
    )
    out["worst_c"] = worst.reindex(out.index)
    return out[(out["small_h"] > 0) | (out["large_h"] > 0)]


def build_command_response_figure(judged_all, events_win, x_lo, x_hi, large_c=0.5):
    """Stacked panels sharing the time axis, one row per EAS chiller plus one.

    Chiller rows: hours per UTC day with the readback off the command, gray for
    mismatches under ``large_c`` and in the chiller colour for large ones.
    Bottom row: the worst signed error (readback - command) of each day with a
    mismatch, with the ``±large_c`` threshold dashed.

    Parameters
    ----------
    judged_all : `pandas.DataFrame`
        The *Command Response* notebook's ``judged_all``: judged commands of
        both chillers, indexed by naive UTC time, with a ``chiller`` column.
    events_win : `pandas.DataFrame`
        Incidents inside the window (``t``, ``event_id``), as for
        `build_technote_figure`.
    x_lo, x_hi : `datetime.datetime`
        Naive UTC window limits.
    large_c : `float`
        Threshold for a large mismatch, in °C.
    """
    x_range = Range1d(start=x_lo, end=x_hi)
    tools = "xpan,xwheel_zoom,box_zoom,reset,save"
    day_ms = 86_400e3

    def panel(height, title):
        return figure(
            height=height, sizing_mode="stretch_width", x_axis_type="datetime",
            x_range=x_range, title=title, tools=tools, active_scroll="xwheel_zoom",
        )

    rows = []
    err = panel(240, "Worst error of each day with a mismatch (readback − command)")
    for name, dev_id in EAS_CHILLERS.items():
        label, color = CHILLERS[dev_id]
        d = daily_mismatch(judged_all[judged_all["chiller"] == name], large_c)
        src = ColumnDataSource(dict(
            x=d.index + pd.Timedelta(hours=12), day=d.index,
            small=d["small_h"].to_numpy(), total=(d["small_h"] + d["large_h"]).to_numpy(),
            large=d["large_h"].to_numpy(), worst=d["worst_c"].to_numpy(),
        ))
        p = panel(200, f"{label}: hours per day with readback ≠ command")
        bars = [
            p.vbar(x="x", bottom=0, top="small", width=0.9 * day_ms, source=src,
                   fill_color=SMALL_COLOR, line_color=None, legend_label=f"< {large_c} °C"),
            p.vbar(x="x", bottom="small", top="total", width=0.9 * day_ms, source=src,
                   fill_color=color, line_color=None, legend_label=f"≥ {large_c} °C"),
        ]
        tooltips = [("", label), ("day", "@day{%F}"), (f"< {large_c} °C", "@small{0.00} h"),
                    (f"≥ {large_c} °C", "@large{0.00} h"), ("worst error", "@worst{+0.0} °C")]
        p.add_tools(HoverTool(renderers=bars, tooltips=tooltips, formatters={"@day": "datetime"}))
        p.yaxis.axis_label = "Hours / day"
        p.y_range.start = 0
        p.legend.location = "top_left"
        rows.append(p)

        dots = err.scatter(x="x", y="worst", source=src, size=5, fill_color=color,
                           line_color=None, fill_alpha=0.8, legend_label=label)
        err.add_tools(HoverTool(renderers=[dots], tooltips=tooltips, formatters={"@day": "datetime"}))

    for sign in (-1, 1):
        err.add_layout(Span(location=sign * large_c, dimension="width",
                            line_color=EVENT_COLOR, line_dash="dashed", line_width=1))
    err.yaxis.axis_label = "Error [°C]"
    err.xaxis.axis_label = "Time [UTC]"
    err.legend.location = "bottom_left"
    rows.append(err)

    for _, ev in events_win.iterrows():
        for p in rows:
            p.add_layout(Span(location=ev["t"], dimension="height",
                              line_color=EVENT_COLOR, line_dash="dashed", line_width=1.5))
        rows[0].add_layout(
            Label(x=ev["t"], y=6, y_units="screen", x_offset=-4, text_align="right",
                  text=f"#{int(ev['event_id'])}",
                  text_color="#52514e", text_font_size="8pt",
                  background_fill_color="white", background_fill_alpha=0.8)
        )

    for p in rows:
        _style(p)
        p.legend.orientation = "horizontal"
        p.legend.click_policy = "hide"
        p.legend.label_text_font_size = "9pt"
        p.legend.label_text_color = "#0b0b0b"
        p.legend.background_fill_alpha = 0.85
        p.legend.border_line_color = None
    for p in rows[:-1]:
        p.xaxis.major_label_text_font_size = "0pt"

    return column(*rows, sizing_mode="stretch_width")
