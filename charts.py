"""Plotly charts with one consistent, terminal-style look.

Conventions (as in Yahoo Finance / TradingView): price axis on the right, crosshair hover,
no weekend gaps, last price tagged on the axis, volume in a separate pane, quiet grids.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import analysis
from i18n import T
from ui import P

FONT = "Inter, system-ui, sans-serif"
CONFIG = {"displayModeBar": False, "scrollZoom": False}


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def base(fig: go.Figure, height: int, right_axis: bool = True, legend: bool = True) -> go.Figure:
    p = P()
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=28 if legend else 10, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=p["muted"]),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=p["surface"], bordercolor=p["line"], font=dict(family=FONT, size=12, color=p["ink"])),
        legend=dict(orientation="h", traceorder="normal", yanchor="bottom", y=1.0, x=0, font=dict(size=11, color=p["muted"]),
                    bgcolor="rgba(0,0,0,0)"),
        showlegend=legend,
        dragmode=False,
    )
    fig.update_xaxes(showgrid=False, linecolor=p["line"], tickfont=dict(size=11, color=p["muted"]),
                     showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1,
                     spikedash="dot", spikecolor=p["faint"], ticks="outside", ticklen=4, tickcolor=p["line"])
    fig.update_yaxes(gridcolor=p["grid"], zeroline=False, tickfont=dict(size=11, color=p["muted"]),
                     side="right" if right_axis else "left", showspikes=True, spikemode="across",
                     spikethickness=1, spikedash="dot", spikecolor=p["faint"])
    return fig


def _last_tag(fig: go.Figure, y: float, color: str, text: str, row: int | None = None) -> None:
    kwargs = dict(xref="paper", x=1.0, y=y, xanchor="left", showarrow=False, text=f"<b>{text}</b>",
                  font=dict(color="#FFFFFF", size=11, family=FONT), bgcolor=color, borderpad=3)
    if row:
        kwargs["yref"] = f"y{'' if row == 1 else row}"
    fig.add_annotation(**kwargs)


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def price_chart(df: pd.DataFrame, kind: str = "area", intraday: bool = False, prev_close: float | None = None,
                mas: tuple[int, ...] = (), bollinger: bool = False, show_rsi: bool = False, full: pd.DataFrame | None = None,
                height: int = 430, cone_vol: float | None = None) -> go.Figure:
    """Main price chart. `full` is the longer history used to compute moving averages before the window starts."""
    p = P()
    rows = 2 + (1 if show_rsi else 0)
    heights = [0.62, 0.16, 0.22] if show_rsi else [0.8, 0.2]
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, row_heights=heights, vertical_spacing=0.025)
    close = df["close"]
    first, last = float(close.iloc[0]), float(close.iloc[-1])
    ref = prev_close if (intraday and prev_close) else first
    up = last >= ref
    color = p["up"] if up else p["down"]
    # y range: the visible prices (plus the indicators drawn below), not zero
    src_full = full["close"] if full is not None else close
    vals = [df["low"] if kind == "candles" and "low" in df else close, df["high"] if kind == "candles" and "high" in df else close]
    for n in mas:
        vals.append(src_full.rolling(n).mean().reindex(df.index))
    if bollinger:
        m20, s20 = src_full.rolling(20).mean(), src_full.rolling(20).std()
        vals += [(m20 + 2 * s20).reindex(df.index), (m20 - 2 * s20).reindex(df.index)]
    if cone_vol and not intraday:
        s63 = cone_vol * np.sqrt(63 / analysis.TRADING_DAYS)
        vals.append(pd.Series([last * np.exp(s63), last * np.exp(-s63)]))
    if intraday and prev_close:
        vals.append(pd.Series([prev_close]))
    lo_v = float(np.nanmin([np.nanmin(np.asarray(v, dtype=float)) for v in vals]))
    hi_v = float(np.nanmax([np.nanmax(np.asarray(v, dtype=float)) for v in vals]))
    pad = (hi_v - lo_v) * 0.06 or hi_v * 0.01
    floor = lo_v - pad

    if kind == "candles" and {"open", "high", "low"} <= set(df.columns):
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["open"], high=df["high"], low=df["low"], close=close, name=T("Price"),
            increasing=dict(line=dict(color=p["up"], width=1), fillcolor=p["up"]),
            decreasing=dict(line=dict(color=p["down"], width=1), fillcolor=p["down"]),
            whiskerwidth=0.3), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=df.index, y=np.full(len(df), floor), mode="lines", line=dict(width=0), showlegend=False,
                                 hoverinfo="skip"), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=close, mode="lines", name=T("Price"), line=dict(color=color, width=2),
            fill="tonexty", fillgradient=dict(type="vertical", colorscale=[[0, _rgba(color, 0.0)], [1, _rgba(color, 0.22)]]),
            hovertemplate="$%{y:,.2f}<extra></extra>"), row=1, col=1)

    src = full["close"] if full is not None else close
    palette = [p["orange"], p["violet"], p["teal"]]
    for i, n in enumerate(mas):
        ma = src.rolling(n).mean().reindex(df.index)
        if ma.notna().any():
            fig.add_trace(go.Scatter(x=df.index, y=ma, mode="lines", name=T("{n}-day avg", n=n),
                                     line=dict(color=palette[i % 3], width=1.3), hovertemplate="$%{y:,.2f}<extra>%{fullData.name}</extra>"),
                          row=1, col=1)
    if bollinger:
        mid = src.rolling(20).mean()
        sd = src.rolling(20).std()
        upper, lower = (mid + 2 * sd).reindex(df.index), (mid - 2 * sd).reindex(df.index)
        fig.add_trace(go.Scatter(x=df.index, y=upper, mode="lines", line=dict(color=p["faint"], width=1, dash="dot"),
                                 name="Bollinger (20, 2σ)", hovertemplate="$%{y:,.2f}<extra>" + T("Upper band") + "</extra>"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=lower, mode="lines", line=dict(color=p["faint"], width=1, dash="dot"),
                                 fill="tonexty", fillcolor=_rgba(p["accent"], 0.05), showlegend=False,
                                 hovertemplate="$%{y:,.2f}<extra>" + T("Lower band") + "</extra>"), row=1, col=1)
    if cone_vol and not intraday:
        future = pd.bdate_range(df.index[-1], periods=64)
        s = cone_vol * np.sqrt(np.arange(len(future)) / analysis.TRADING_DAYS)
        fig.add_trace(go.Scatter(x=future, y=last * np.exp(s), mode="lines", line=dict(color=p["accent"], width=1, dash="dot"),
                                 name=T("±1σ range ahead"), hovertemplate="$%{y:,.2f}<extra>" + T("Upper") + "</extra>"), row=1, col=1)
        fig.add_trace(go.Scatter(x=future, y=last * np.exp(-s), mode="lines", line=dict(color=p["accent"], width=1, dash="dot"),
                                 fill="tonexty", fillcolor=_rgba(p["accent"], 0.08), showlegend=False,
                                 hovertemplate="$%{y:,.2f}<extra>" + T("Lower") + "</extra>"), row=1, col=1)
    if intraday and prev_close:
        fig.add_hline(y=prev_close, line=dict(color=p["faint"], width=1, dash="dash"), row=1, col=1,
                      annotation_text=T("Prev close {v}", v=f"{prev_close:,.2f}"), annotation_position="top left",
                      annotation_font=dict(size=10, color=p["muted"]))

    if "volume" in df and df["volume"].notna().any():
        vcol = np.where(df["close"] >= df["close"].shift(1).fillna(df["close"]), _rgba(p["up"], 0.45), _rgba(p["down"], 0.45))
        fig.add_trace(go.Bar(x=df.index, y=df["volume"], marker_color=vcol, name=T("Volume"), showlegend=False,
                             hovertemplate="%{y:,.0f}<extra>" + T("Volume") + "</extra>"), row=2, col=1)
    if show_rsi:
        r = rsi(src).reindex(df.index)
        fig.add_trace(go.Scatter(x=df.index, y=r, mode="lines", line=dict(color=p["violet"], width=1.3), name="RSI (14)",
                                 hovertemplate="%{y:.0f}<extra>RSI</extra>"), row=3, col=1)
        for lvl in (30, 70):
            fig.add_hline(y=lvl, line=dict(color=p["faint"], width=1, dash="dot"), row=3, col=1)
        fig.update_yaxes(range=[0, 100], tickvals=[30, 70], row=3, col=1)

    base(fig, height)
    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_yaxes(tickprefix="$", range=[floor, hi_v + pad], row=1, col=1)
    fig.update_yaxes(showticklabels=False, showgrid=False, row=2, col=1)
    if intraday:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[16, 9.5], pattern="hour")])
    else:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    _last_tag(fig, last, color, f"{last:,.2f}")
    fig.update_layout(margin=dict(r=62))
    return fig


def fan_chart(close: pd.Series, fan: np.ndarray, levels: list[tuple[str, float, str]], hist_days: int = 126) -> go.Figure:
    """History, then the 5-95 and 25-75 percentile bands of simulated paths, with reference levels."""
    p = P()
    h = close.iloc[-hist_days:]
    future = pd.bdate_range(h.index[-1], periods=fan.shape[1] + 1)[1:]
    last = float(h.iloc[-1])
    fx = [h.index[-1]] + list(future)
    band = lambda row: [last] + list(fan[row])  # noqa: E731
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=h.index, y=h.values, mode="lines", line=dict(color=p["ink"], width=1.8), name=T("Price"),
                             hovertemplate="$%{y:,.2f}<extra>" + T("Price") + "</extra>"))
    fig.add_trace(go.Scatter(x=fx, y=band(4), mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fx, y=band(0), mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=_rgba(p["accent"], 0.12), name=T("9 in 10 scenarios"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fx, y=band(3), mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fx, y=band(1), mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=_rgba(p["accent"], 0.26), name=T("Middle half of scenarios"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fx, y=band(2), mode="lines", line=dict(color=p["accent"], width=1.8, dash="dash"),
                             name=T("Median path"), hovertemplate="$%{y:,.2f}<extra>" + T("Median") + "</extra>"))
    for name, value, color_key in levels:
        if value:
            fig.add_hline(y=value, line=dict(color=p[color_key], width=1.2, dash="dot"),
                          annotation_text=f"{name} ${value:,.2f}", annotation_position="top left",
                          annotation_font=dict(size=10, color=p[color_key]))
    base(fig, 440)
    fig.update_yaxes(tickprefix="$")
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(margin=dict(r=62))
    return fig


def sector_bars(rows: list[tuple[str, float]]) -> go.Figure:
    p = P()
    rows = sorted(rows, key=lambda r: r[1])
    names, vals = [r[0] for r in rows], [r[1] for r in rows]
    colors = [p["up"] if v >= 0 else p["down"] for v in vals]
    fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker=dict(color=colors, cornerradius=3),
                           text=[f"{v:+.2f}%" for v in vals], textposition="outside", cliponaxis=False,
                           textfont=dict(size=11, color=p["muted"]), hovertemplate="%{y}: %{x:+.2f}%<extra></extra>"))
    base(fig, 30 + 26 * len(rows), right_axis=False, legend=False)
    lim = max(abs(v) for v in vals) * 1.35 or 1
    fig.update_xaxes(range=[-lim, lim], ticksuffix="%", showspikes=False, zeroline=True, zerolinecolor=p["line"])
    fig.update_yaxes(showgrid=False, showspikes=False, tickfont=dict(size=11, color=p["body"]))
    fig.update_layout(hovermode="closest", bargap=0.35, margin=dict(l=6, r=40, t=6, b=6))
    return fig


def yield_curve(df: pd.DataFrame) -> go.Figure:
    p = P()
    fig = go.Figure()
    if df["month_ago"].notna().any():
        fig.add_trace(go.Scatter(x=df["tenor"], y=df["month_ago"], mode="lines+markers", name=T("A month ago"),
                                 line=dict(color=p["faint"], width=1.5, dash="dot"), marker=dict(size=5),
                                 hovertemplate="%{y:.2f}%<extra>" + T("A month ago") + "</extra>"))
    fig.add_trace(go.Scatter(x=df["tenor"], y=df["now"], mode="lines+markers", name=T("Latest ({d})", d=df['date'].iloc[0]),
                             line=dict(color=p["accent"], width=2.2), marker=dict(size=6),
                             hovertemplate="%{y:.2f}%<extra>" + T("Latest") + "</extra>"))
    base(fig, 260)
    fig.update_yaxes(ticksuffix="%")
    fig.update_xaxes(showspikes=False)
    return fig


def treemap(rows: list[dict]) -> go.Figure:
    """Finviz-style market map: size = market cap, color = today's % change."""
    p = P()
    sectors = sorted({r["sector"] for r in rows})
    ids = sectors + [r["ticker"] for r in rows]
    labels = sectors + [r["ticker"] for r in rows]
    parents = [""] * len(sectors) + [r["sector"] for r in rows]
    values = [0] * len(sectors) + [r["cap"] for r in rows]
    colors = [0.0] * len(sectors) + [max(-3.0, min(3.0, r["pct"])) for r in rows]
    text = [""] * len(sectors) + [f"{r['pct']:+.2f}%" for r in rows]
    custom = [["", 0, ""]] * len(sectors) + [[r["name"], r["price"], f"{r['pct']:+.2f}%"] for r in rows]
    scale = [[0, "#B3261E"], [0.35, "#7A2A2A"], [0.5, "#3B4252"], [0.65, "#1F6B3F"], [1, "#16A34A"]]
    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values, branchvalues="remainder", text=text,
        customdata=custom, textinfo="label+text", texttemplate="<b>%{label}</b><br>%{text}",
        textfont=dict(family=FONT, color="#FFFFFF", size=14), textposition="middle center",
        marker=dict(colors=colors, colorscale=scale, cmin=-3, cmax=3, line=dict(width=1.5, color=p["paper"])),
        hovertemplate="<b>%{label}</b> %{customdata[0]}<br>$%{customdata[1]:,.2f}  %{customdata[2]}<extra></extra>",
        pathbar=dict(visible=False), root=dict(color=p["paper"]), tiling=dict(pad=2),
    ))
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=FONT))
    return fig


def compare_lines(series: dict[str, pd.Series], highlight: str | None = None, height: int = 420) -> go.Figure:
    p = P()
    palette = [p["accent"], p["orange"], p["teal"], p["violet"], "#D9A400", "#E1567C", p["muted"]]
    fig = go.Figure()
    for i, (name, s) in enumerate(series.items()):
        perf = (s / s.iloc[0] - 1) * 100
        is_bench = name in ("SPY", "S&P 500 (SPY)")
        width = 2.4 if name == highlight else 1.6
        fig.add_trace(go.Scatter(x=perf.index, y=perf.values, mode="lines", name=name,
                                 line=dict(color=p["ink"] if is_bench else palette[i % len(palette)], width=width,
                                           dash="dot" if is_bench else "solid"),
                                 hovertemplate="%{y:+.1f}%<extra>" + name + "</extra>"))
        fig.add_annotation(xref="paper", x=1.0, y=perf.iloc[-1], xanchor="left", showarrow=False,
                           text=f"<b>{name} {perf.iloc[-1]:+.1f}%</b>", font=dict(size=10, color="#FFF"),
                           bgcolor=p["ink"] if is_bench else palette[i % len(palette)], borderpad=2)
    base(fig, height)
    fig.update_yaxes(ticksuffix="%", zeroline=True, zerolinecolor=p["line"])
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(margin=dict(r=110))
    return fig


def correlation(df: pd.DataFrame) -> go.Figure:
    p = P()
    c = df.corr()
    fig = go.Figure(go.Heatmap(z=c.values, x=c.columns, y=c.index, zmin=-1, zmax=1,
                               colorscale=[[0, "#C2413B"], [0.5, p["soft"]], [1, "#1F5BD8"]],
                               text=np.round(c.values, 2), texttemplate="%{text:.2f}", textfont=dict(size=12),
                               hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>", showscale=False))
    base(fig, 60 + 46 * len(c), right_axis=False, legend=False)
    fig.update_xaxes(showspikes=False, side="top")
    fig.update_yaxes(showspikes=False, autorange="reversed", showgrid=False)
    fig.update_layout(hovermode="closest")
    return fig


def recommendations(rows: list[dict]) -> go.Figure:
    p = P()
    rows = list(reversed(rows))
    periods = [r["period"][:7] for r in rows]
    parts = [("strongSell", T("Strong sell"), "#B3261E"), ("sell", T("Sell"), "#E0675F"), ("hold", T("Hold"), p["faint"]),
             ("buy", T("Buy"), "#3FB27F"), ("strongBuy", T("Strong buy"), "#0A7F45")]
    fig = go.Figure()
    for key, name, color in parts:
        fig.add_trace(go.Bar(x=periods, y=[r.get(key, 0) for r in rows], name=name, marker_color=color,
                             hovertemplate="%{y}<extra>" + name + "</extra>"))
    base(fig, 250, right_axis=False)
    fig.update_layout(barmode="stack", bargap=0.35, hovermode="x unified")
    fig.update_xaxes(showspikes=False)
    fig.update_yaxes(showspikes=False)
    return fig


def financial_bars(years: list, series: list[tuple[str, list, str]], height: int = 300, suffix: str = "B") -> go.Figure:
    p = P()
    fig = go.Figure()
    for name, vals, color_key in series:
        fig.add_trace(go.Bar(x=[str(y) for y in years], y=vals, name=name, marker=dict(color=p[color_key], cornerradius=3),
                             hovertemplate="$%{y:,.1f}" + suffix + "<extra>" + name + "</extra>"))
    base(fig, height)
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.06)
    fig.update_yaxes(tickprefix="$", ticksuffix=suffix)
    fig.update_xaxes(showspikes=False, type="category")
    return fig


def margin_lines(years: list, series: list[tuple[str, list, str]], height: int = 300) -> go.Figure:
    p = P()
    fig = go.Figure()
    for name, vals, color_key in series:
        fig.add_trace(go.Scatter(x=[str(y) for y in years], y=vals, name=name, mode="lines+markers",
                                 line=dict(color=p[color_key], width=2), marker=dict(size=6),
                                 hovertemplate="%{y:.1f}%<extra>" + name + "</extra>"))
    base(fig, height)
    fig.update_yaxes(ticksuffix="%")
    fig.update_xaxes(showspikes=False, type="category")
    return fig


def drawdown(close: pd.Series) -> go.Figure:
    p = P()
    dd = analysis.drawdown_series(close) * 100
    fig = go.Figure(go.Scatter(x=dd.index, y=dd.values, mode="lines", line=dict(color=p["down"], width=1.5),
                               fill="tozeroy", fillcolor=_rgba(p["down"], 0.12), hovertemplate="%{y:.1f}%<extra>From peak</extra>"))
    base(fig, 250, legend=False)
    fig.update_yaxes(ticksuffix="%")
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig


def football_field(rows: list[tuple[str, float, float]], price: float) -> go.Figure:
    p = P()
    rows = [r for r in rows if r[1] is not None and r[2] is not None]
    names = [r[0] for r in rows][::-1]
    lows = [min(r[1], r[2]) for r in rows][::-1]
    highs = [max(r[1], r[2]) for r in rows][::-1]
    fig = go.Figure(go.Bar(
        y=names, x=[h - lo for lo, h in zip(lows, highs)], base=lows, orientation="h",
        marker=dict(color=_rgba(p["accent"], 0.8), cornerradius=3), width=0.5, customdata=list(zip(lows, highs)),
        hovertemplate="%{y}: $%{customdata[0]:,.0f} to $%{customdata[1]:,.0f}<extra></extra>",
        text=[f"${lo:,.0f} – ${h:,.0f}" for lo, h in zip(lows, highs)], textposition="outside",
        textfont=dict(color=p["muted"], size=11), cliponaxis=False))
    fig.add_vline(x=price, line=dict(color=p["ink"], width=2, dash="dot"))
    fig.add_annotation(x=price, y=1.07, yref="paper", text="<b>" + T("Price") + f" ${price:,.2f}</b>", showarrow=False,
                       font=dict(color=p["ink"], size=11))
    lo_all, hi_all = min(lows + [price]), max(highs + [price])
    span = hi_all - lo_all or 1
    base(fig, 80 + 56 * len(rows), right_axis=False, legend=False)
    fig.update_xaxes(tickprefix="$", range=[max(0, lo_all - span * 0.08), hi_all + span * 0.3], showgrid=True,
                     gridcolor=p["grid"], showspikes=False)
    fig.update_yaxes(showgrid=False, showspikes=False, tickfont=dict(size=11, color=p["body"]))
    fig.update_layout(hovermode="closest", margin=dict(l=6, r=10, t=26, b=6))
    return fig
