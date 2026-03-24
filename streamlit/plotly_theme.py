import plotly.graph_objects as go

TEXT = "#1f2a22"
MUTED = "#7a6e5e"
GRID = "#e7dfd2"
BORDER = "#ddd3c4"
SUCCESS = "#30945a"
WARNING = "#c8a800"
DANGER = "#cf6e63"
NEUTRAL = "#74866f"
BG = "rgba(0,0,0,0)"
PAPER = "#fffdf8"
FONT = "Manrope, system-ui, sans-serif"


def apply_chart_style(
    fig: go.Figure,
    *,
    height: int = 320,
    legend: bool = True,
    xgrid: bool = True,
    ygrid: bool = True,
    bargap: float = 0.22,
    hovermode: str = "closest",
) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(t=16, r=14, b=38, l=14),
        showlegend=legend,
        plot_bgcolor=BG,
        paper_bgcolor=BG,
        font=dict(color=TEXT, size=12, family=FONT),
        hoverlabel=dict(bgcolor=PAPER, bordercolor=BORDER, font=dict(color=TEXT, size=12, family=FONT)),
        legend=dict(
            orientation="h",
            y=1.11,
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=MUTED, size=11, family=FONT),
        ),
        bargap=bargap,
        hovermode=hovermode,
        separators=".,",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    fig.update_xaxes(
        gridcolor=GRID if xgrid else "rgba(0,0,0,0)",
        gridwidth=1,
        zeroline=False,
        showline=False,
        tickfont=dict(color=MUTED, size=11, family=FONT),
        title_font=dict(color=MUTED, size=11, family=FONT),
        automargin=True,
        ticks="outside",
        ticklen=4,
        tickcolor=BORDER,
        showspikes=False,
    )
    fig.update_yaxes(
        gridcolor=GRID if ygrid else "rgba(0,0,0,0)",
        gridwidth=1,
        zeroline=False,
        showline=False,
        tickfont=dict(color=MUTED, size=11, family=FONT),
        title_font=dict(color=MUTED, size=11, family=FONT),
        automargin=True,
        ticks="outside",
        ticklen=4,
        tickcolor=BORDER,
        showspikes=False,
    )
    fig.update_traces(
        selector=dict(type="bar"),
        marker_line_color="rgba(255, 253, 248, 0.95)",
        marker_line_width=1.25,
        opacity=0.92,
    )
    fig.update_traces(
        selector=dict(type="scatter"),
        marker_line_color="rgba(255, 253, 248, 0.95)",
        marker_line_width=1.2,
    )
    return fig


def add_hline(fig: go.Figure, value: float, label: str, *, color: str = WARNING, dash: str = "dot") -> go.Figure:
    fig.add_hline(
        y=value,
        line_dash=dash,
        line_color=color,
        annotation_text=label,
        annotation_position="top right",
        annotation_font=dict(color=MUTED, size=11),
    )
    return fig


def add_vline(fig: go.Figure, value: float, label: str, *, color: str = WARNING, dash: str = "dot") -> go.Figure:
    fig.add_vline(
        x=value,
        line_dash=dash,
        line_color=color,
        annotation_text=label,
        annotation_position="top right",
        annotation_font=dict(color=MUTED, size=11),
    )
    return fig


def apply_pie_style(fig: go.Figure, *, height: int = 320) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(t=16, r=14, b=14, l=14),
        paper_bgcolor=BG,
        font=dict(color=TEXT, size=12, family=FONT),
        legend=dict(
            orientation="h",
            y=1.05,
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=MUTED, size=11, family=FONT),
        ),
        separators=".,",
    )
    fig.update_traces(
        selector=dict(type="pie"),
        marker_line_color=PAPER,
        marker_line_width=2.2,
        textfont=dict(family=FONT, size=12),
        insidetextorientation="horizontal",
        sort=False,
    )
    return fig
