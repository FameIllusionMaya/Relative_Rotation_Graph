import os
import glob
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Use the script's real directory; fall back to cwd if __file__ is unreliable
_script_dir = os.path.dirname(os.path.realpath(__file__))
if os.path.isdir(os.path.join(_script_dir, "data")):
    BASE_DIR = _script_dir
else:
    BASE_DIR = os.getcwd()

RS_RATIO_PERIOD = 12
RS_MOMENTUM_PERIOD = 10
CENTER = 100

# ---------------------------------------------------------------------------
# RRG computation (reused from generate_graph.py)
# ---------------------------------------------------------------------------

def load_csv(path: str, interval: str = "daily") -> pd.Series:
    """Load a sector CSV and return close prices.

    For daily data: resample to weekly (W-FRI) as before.
    For 1h data: return raw hourly close without resampling.
    """
    df = pd.read_csv(path, parse_dates=["datetime"])
    df = df.sort_values("datetime").set_index("datetime")
    if interval == "daily":
        return df["close"].resample("W-FRI").last().dropna()
    else:
        return df["close"].dropna()


def compute_rrg(sector_close: pd.Series,
                benchmark_close: pd.Series,
                rs_period: int = RS_RATIO_PERIOD,
                mom_period: int = RS_MOMENTUM_PERIOD) -> pd.DataFrame:
    rs = sector_close / benchmark_close
    rs_sma = rs.rolling(window=rs_period).mean()
    rs_ratio = CENTER + ((rs - rs_sma) / rs_sma) * CENTER
    ratio_sma = rs_ratio.rolling(window=mom_period).mean()
    rs_momentum = CENTER + ((rs_ratio - ratio_sma) / ratio_sma) * CENTER
    result = pd.DataFrame({"rs_ratio": rs_ratio, "rs_momentum": rs_momentum})
    return result.dropna()


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_all_sectors(interval: str = "daily"):
    """Load benchmark and all sector RRG data. Returns dict of DataFrames."""
    data_dir = os.path.join(BASE_DIR, "data", "daily" if interval == "daily" else "1h")
    benchmark_file = os.path.join(data_dir, "SET.csv")

    if not os.path.isfile(benchmark_file):
        return {}

    benchmark = load_csv(benchmark_file, interval)

    sector_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    sector_files = [f for f in sector_files if os.path.basename(f) != "SET.csv"]

    sectors = {}
    min_rows = RS_RATIO_PERIOD + RS_MOMENTUM_PERIOD + 5
    for fpath in sector_files:
        name = os.path.splitext(os.path.basename(fpath))[0]
        try:
            close = load_csv(fpath, interval)
            common = close.index.intersection(benchmark.index)
            if len(common) < min_rows:
                continue
            rrg = compute_rrg(close.loc[common], benchmark.loc[common])
            if len(rrg) >= 5:
                sectors[name] = rrg
        except Exception:
            continue
    return sectors


# ---------------------------------------------------------------------------
# Plotly chart
# ---------------------------------------------------------------------------

# 20 distinct colours for sector tails
COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
    "#c49c94", "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5",
]


def build_figure(sectors: dict, selected: list[str], tail_length: int,
                 interval: str = "daily") -> go.Figure:
    fig = go.Figure()

    color_map = {name: COLORS[i % len(COLORS)] for i, name in enumerate(sorted(sectors.keys()))}

    date_fmt = "%Y-%m-%d" if interval == "daily" else "%Y-%m-%d %H:%M"

    all_x, all_y = [], []

    for name in sorted(selected):
        rrg = sectors[name]
        tail = rrg.iloc[-tail_length:]
        x = tail["rs_ratio"].values
        y = tail["rs_momentum"].values
        all_x.extend(x)
        all_y.extend(y)
        c = color_map[name]
        dates = tail.index.strftime(date_fmt).tolist()

        # Tail line
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines",
            line=dict(color=c, width=2),
            name=name, legendgroup=name,
            showlegend=False,
            hoverinfo="skip",
        ))

        # Dots (sized by recency)
        sizes = np.linspace(5, 12, len(x))
        hover_text = [f"<b>{name}</b><br>Date: {d}<br>RS-Ratio: {xi:.2f}<br>RS-Mom: {yi:.2f}"
                      for d, xi, yi in zip(dates, x, y)]
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers",
            marker=dict(color=c, size=sizes, line=dict(color="white", width=0.5)),
            name=name, legendgroup=name,
            showlegend=True,
            hovertemplate="%{text}<extra></extra>",
            text=hover_text,
        ))

        # Label at latest point
        fig.add_annotation(
            x=x[-1], y=y[-1], text=f"<b>{name}</b>",
            showarrow=False, xshift=10, yshift=8,
            font=dict(size=10, color=c),
        )

    # Axis range with padding
    if all_x and all_y:
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        x_margin = max((x_max - x_min) * 0.15, 0.5)
        y_margin = max((y_max - y_min) * 0.15, 0.5)
        x_lo, x_hi = x_min - x_margin, x_max + x_margin
        y_lo, y_hi = y_min - y_margin, y_max + y_margin
    else:
        x_lo, x_hi, y_lo, y_hi = 96, 104, 96, 104

    # Quadrant shading
    fig.add_shape(type="rect", x0=CENTER, x1=x_hi, y0=CENTER, y1=y_hi,
                  fillcolor="green", opacity=0.06, line_width=0, layer="below")
    fig.add_shape(type="rect", x0=x_lo, x1=CENTER, y0=CENTER, y1=y_hi,
                  fillcolor="blue", opacity=0.06, line_width=0, layer="below")
    fig.add_shape(type="rect", x0=x_lo, x1=CENTER, y0=y_lo, y1=CENTER,
                  fillcolor="red", opacity=0.06, line_width=0, layer="below")
    fig.add_shape(type="rect", x0=CENTER, x1=x_hi, y0=y_lo, y1=CENTER,
                  fillcolor="orange", opacity=0.06, line_width=0, layer="below")

    # Quadrant labels
    fig.add_annotation(x=x_hi, y=y_hi, text="<b>LEADING</b>", showarrow=False,
                       xanchor="right", yanchor="top", font=dict(size=14, color="green"), opacity=0.5)
    fig.add_annotation(x=x_lo, y=y_hi, text="<b>IMPROVING</b>", showarrow=False,
                       xanchor="left", yanchor="top", font=dict(size=14, color="blue"), opacity=0.5)
    fig.add_annotation(x=x_lo, y=y_lo, text="<b>LAGGING</b>", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(size=14, color="red"), opacity=0.5)
    fig.add_annotation(x=x_hi, y=y_lo, text="<b>WEAKENING</b>", showarrow=False,
                       xanchor="right", yanchor="bottom", font=dict(size=14, color="orange"), opacity=0.5)

    # Centre lines
    fig.add_hline(y=CENTER, line_dash="dash", line_color="grey", line_width=0.8)
    fig.add_vline(x=CENTER, line_dash="dash", line_color="grey", line_width=0.8)

    fig.update_layout(
        xaxis_title="RS-Ratio",
        yaxis_title="RS-Momentum",
        xaxis=dict(range=[x_lo, x_hi]),
        yaxis=dict(range=[y_lo, y_hi]),
        height=700,
        margin=dict(t=60, b=60, l=60, r=30),
        legend=dict(font=dict(size=10)),
        hovermode="closest",
    )

    return fig


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="RRG — SET Sectors", layout="wide")
st.title("Relative Rotation Graph — SET Sectors")

# Sidebar controls
with st.sidebar:
    st.header("Settings")

    interval = st.radio("Interval", options=["Daily", "1 Hour"], horizontal=True)
    interval_key = "daily" if interval == "Daily" else "1h"

    sectors = load_all_sectors(interval_key)

    if not sectors:
        data_path = os.path.join(BASE_DIR, "data", "daily" if interval_key == "daily" else "1h")
        bench = os.path.join(data_path, "SET.csv")
        st.error(
            f"No sector data found for this interval.\n\n"
            f"- `BASE_DIR`: `{BASE_DIR}`\n"
            f"- `data_path`: `{data_path}`\n"
            f"- dir exists: `{os.path.isdir(data_path)}`\n"
            f"- SET.csv exists: `{os.path.isfile(bench)}`\n"
            f"- files: `{os.listdir(data_path) if os.path.isdir(data_path) else 'N/A'}`"
        )
        st.stop()

    tail_unit = "weeks" if interval_key == "daily" else "hours"
    tail_length = st.slider(f"Tail length ({tail_unit})", min_value=2, max_value=20, value=5)

    all_names = sorted(sectors.keys())
    selected = st.multiselect("Sectors", options=all_names, default=all_names)

    # Last-updated date
    latest_date = max(rrg.index[-1] for rrg in sectors.values())
    date_fmt = "%Y-%m-%d" if interval_key == "daily" else "%Y-%m-%d %H:%M"
    st.markdown(f"**Data as of:** {latest_date.strftime(date_fmt)}")

if not selected:
    st.warning("Select at least one sector from the sidebar.")
    st.stop()

fig = build_figure(sectors, selected, tail_length, interval_key)
st.plotly_chart(fig, width="stretch")
