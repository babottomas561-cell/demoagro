from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLOR_SEQUENCE = ["#607053", "#c96d4a", "#d0a44c", "#8a9f6d", "#30453a", "#8e5d4f"]


def line_chart(
    dataframe: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    title: str | None = None,
) -> go.Figure:
    figure = px.line(
        dataframe,
        x=x,
        y=y,
        color=color,
        markers=True,
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    return _style_figure(figure, title)


def bar_chart(
    dataframe: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    title: str | None = None,
    orientation: str = "v",
    horizontal: bool = False,
    barmode: str = "group",
) -> go.Figure:
    resolved_orientation = "h" if horizontal else orientation
    figure = px.bar(
        dataframe,
        x=x if not horizontal else y,
        y=y if not horizontal else x,
        color=color,
        orientation=resolved_orientation,
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    figure.update_layout(barmode=barmode)
    return _style_figure(figure, title)


def donut_chart(
    dataframe: pd.DataFrame,
    names: str,
    values: str,
    title: str | None = None,
) -> go.Figure:
    figure = px.pie(
        dataframe,
        names=names,
        values=values,
        hole=0.58,
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    return _style_figure(figure, title)


def scatter_chart(
    dataframe: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    size: str | None = None,
    hover_name: str | None = None,
    title: str | None = None,
) -> go.Figure:
    figure = px.scatter(
        dataframe,
        x=x,
        y=y,
        color=color,
        size=size,
        hover_name=hover_name,
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    figure.update_traces(marker=dict(line=dict(width=0.8, color="rgba(32, 49, 38, 0.25)")))
    return _style_figure(figure, title)


def combo_chart(
    dataframe: pd.DataFrame,
    x: str,
    bar_column: str,
    line_columns: list[str],
    title: str | None = None,
    bar_name: str | None = None,
    line_names: dict[str, str] | None = None,
    line_tickformat: str | None = None,
) -> go.Figure:
    line_names = line_names or {}
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=dataframe[x],
            y=dataframe[bar_column],
            name=bar_name or bar_column,
            marker_color=COLOR_SEQUENCE[0],
            opacity=0.82,
        )
    )
    for index, column in enumerate(line_columns):
        figure.add_trace(
            go.Scatter(
                x=dataframe[x],
                y=dataframe[column],
                mode="lines+markers",
                name=line_names.get(column, column),
                yaxis="y2",
                line=dict(color=COLOR_SEQUENCE[(index + 1) % len(COLOR_SEQUENCE)], width=3),
                marker=dict(size=8),
            )
        )
    figure = _style_figure(figure, title)
    figure.update_layout(
        bargap=0.22,
        yaxis2=dict(
            overlaying="y",
            side="right",
            showgrid=False,
            tickformat=line_tickformat,
        ),
    )
    return figure


def waterfall_chart(
    dataframe: pd.DataFrame,
    x: str,
    y: str,
    measure: str,
    title: str | None = None,
) -> go.Figure:
    figure = go.Figure(
        go.Waterfall(
            x=dataframe[x],
            y=dataframe[y],
            measure=dataframe[measure],
            connector={"line": {"color": "rgba(32, 49, 38, 0.18)"}},
            increasing={"marker": {"color": "#8a9f6d"}},
            decreasing={"marker": {"color": "#c96d4a"}},
            totals={"marker": {"color": "#30453a"}},
        )
    )
    return _style_figure(figure, title)


def _style_figure(figure: go.Figure, title: str | None = None) -> go.Figure:
    figure.update_layout(
        title=title,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=48, b=20),
        legend_title_text="",
        hovermode="x unified",
        font=dict(family="IBM Plex Sans, sans-serif", color="#203126"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    figure.update_xaxes(showgrid=False, zeroline=False)
    figure.update_yaxes(gridcolor="rgba(32, 49, 38, 0.08)", zeroline=False)
    return figure
