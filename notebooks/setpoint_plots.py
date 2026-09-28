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
