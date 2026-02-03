"""
TODO
- default just main sector
- fix date
- rrg of US stock
"""


import os
import glob
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_script_dir = os.path.dirname(os.path.realpath(__file__))
if os.path.isdir(os.path.join(_script_dir, "data")):
    BASE_DIR = _script_dir
else:
    BASE_DIR = os.getcwd()

CENTER = 100

# Main sectors to show by default (reduced list for better initial view)
MAIN_SECTORS = [
    "AGRI", "BANK", "CONS", "ENERG",
    "FIN", "ICT", "PROP", "PETRO"
]

# Default periods per interval
DEFAULT_PERIODS = {
    "weekly": {"rs_period": 8, "mom_period": 8, "tail_length": 5},
    "daily": {"rs_period": 10, "mom_period": 10, "tail_length": 10},
    "1h": {"rs_period": 10, "mom_period": 10, "tail_length": 20},
}

# ---------------------------------------------------------------------------
# RRG computation (JdK style with ema_alpha / Wilder's smoothing)
# ---------------------------------------------------------------------------

def load_csv(path: str, interval: str = "daily") -> pd.Series:
    """Load a sector CSV and return close prices.

    For weekly: resample daily to weekly (W-FRI) - ต้นตำรับ
    For daily: no resample (use raw daily)
    For 1h: no resample (use raw hourly) + add 7 hours for Thailand timezone
    """
    df = pd.read_csv(path, parse_dates=["datetime"])
    df = df.sort_values("datetime").set_index("datetime")

    # Fix timezone for 1h data (Thailand is UTC+7)
    if interval == "1h":
        df.index = df.index + pd.Timedelta(hours=7)

    if interval == "weekly":
        return df["close"].resample("W-FRI").last().dropna()
    else:
        return df["close"].dropna()


def ema_alpha(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing (RMA) - ต้นตำรับ JdK RRG"""
    return series.ewm(alpha=1/period, adjust=False).mean()


def compute_rrg(sector_close: pd.Series,
                benchmark_close: pd.Series,
                rs_period: int,
                mom_period: int) -> pd.DataFrame:
    """
    Compute RS-Ratio and RS-Momentum using JdK methodology.
    ใช้ ema_alpha (Wilder's smoothing) ตามต้นตำรับ
    """
    # Raw relative strength
    rs = sector_close / benchmark_close

    # RS-Ratio: ใช้ ema_alpha
    rs_smooth = ema_alpha(rs, rs_period)
    rs_ratio = CENTER + ((rs - rs_smooth) / rs_smooth) * CENTER
    
    # RS-Momentum: ใช้ ema_alpha
    ratio_smooth = ema_alpha(rs_ratio, mom_period)
    rs_momentum = CENTER + ((rs_ratio - ratio_smooth) / ratio_smooth) * CENTER

    result = pd.DataFrame({"rs_ratio": rs_ratio, "rs_momentum": rs_momentum})
    return result.dropna()


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_all_sectors(interval: str, rs_period: int, mom_period: int):
    """Load benchmark and all sector RRG data. Returns (dict, error_msg|None)."""
    # Weekly และ Daily ใช้ data จาก folder "daily"
    if interval in ["weekly", "daily"]:
        data_dir = os.path.join(BASE_DIR, "data", "daily")
    else:
        data_dir = os.path.join(BASE_DIR, "data", "1h")
    benchmark_file = os.path.join(data_dir, "SET.csv")

    if not os.path.isfile(benchmark_file):
        return {}, f"Benchmark file not found: {benchmark_file}"

    try:
        benchmark = load_csv(benchmark_file, interval)
    except Exception as e:
        return {}, f"Error loading benchmark: {e}"

    sector_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    sector_files = [f for f in sector_files if os.path.basename(f) != "SET.csv"]

    sectors = {}
    errors = []
    min_rows = rs_period + mom_period + 10
    for fpath in sector_files:
        name = os.path.splitext(os.path.basename(fpath))[0]
        try:
            close = load_csv(fpath, interval)
            common = close.index.intersection(benchmark.index)
            if len(common) < min_rows:
                continue
            rrg = compute_rrg(close.loc[common], benchmark.loc[common], rs_period, mom_period)
            if len(rrg) >= 5:
                sectors[name] = rrg
        except Exception as e:
            errors.append(f"{name}: {e}")
            continue

    if not sectors and errors:
        return {}, f"All sectors failed. First errors: {errors[:3]}"
    return sectors, None


# ---------------------------------------------------------------------------
# Plotly chart
# ---------------------------------------------------------------------------

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

    date_fmt = "%Y-%m-%d %H:%M" if interval == "1h" else "%Y-%m-%d"

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

st.set_page_config(page_title="RRG – SET Sectors", layout="wide")
st.title("Relative Rotation Graph – SET Sectors")

# Initialize session state for selected sectors
if "selected_sectors" not in st.session_state:
    st.session_state.selected_sectors = None

# Sidebar controls
with st.sidebar:
    st.header("Settings")

    # Interval selection
    interval = st.radio("Interval", options=["Weekly", "Daily", "1 Hour"], horizontal=True)
    interval_key = {"Weekly": "weekly", "Daily": "daily", "1 Hour": "1h"}[interval]

    # Get default periods for selected interval
    defaults = DEFAULT_PERIODS[interval_key]

    st.subheader("Parameters")

    # RS-Ratio Period
    rs_period = st.slider(
        "RS-Ratio Period",
        min_value=5,
        max_value=50,
        value=defaults["rs_period"],
        help="Period for RS-Ratio smoothing (ema_alpha)"
    )

    # RS-Momentum Period
    mom_period = st.slider(
        "RS-Momentum Period",
        min_value=5,
        max_value=50,
        value=defaults["mom_period"],
        help="Period for RS-Momentum smoothing (ema_alpha)"
    )

    # Tail length
    tail_units = {"weekly": "weeks", "daily": "days", "1h": "hours"}
    tail_unit = tail_units[interval_key]
    tail_length = st.slider(
        f"Tail length ({tail_unit})",
        min_value=2,
        max_value=50,
        value=defaults["tail_length"]
    )

    st.divider()

    # Load data with selected parameters
    sectors, load_error = load_all_sectors(interval_key, rs_period, mom_period)

    if not sectors:
        st.error(f"No sector data found.\n\n{load_error or 'Unknown error'}")
        st.stop()

    # Sector selection with persistent state
    all_names = sorted(sectors.keys())

    # Determine default selection
    if st.session_state.selected_sectors is None:
        # First time: use main sectors (or all if main sectors not available)
        default_selection = [s for s in MAIN_SECTORS if s in all_names]
        if not default_selection:
            default_selection = all_names
    else:
        # Keep previous selection, but filter to only available sectors
        default_selection = [s for s in st.session_state.selected_sectors if s in all_names]
        if not default_selection:
            # If none of previous selection available, fallback to main sectors
            default_selection = [s for s in MAIN_SECTORS if s in all_names]
            if not default_selection:
                default_selection = all_names

    selected = st.multiselect("Sectors", options=all_names, default=default_selection)

    # Update session state with current selection
    st.session_state.selected_sectors = selected

    st.divider()
    
    # Info box
    st.info(f"""
    **Smoothing:** ema_alpha (Wilder's RMA)  
    **Formula:** `ewm(alpha=1/period)`  
    **RS Period:** {rs_period}  
    **Mom Period:** {mom_period}
    """)

    # Last-updated date
    latest_date = max(rrg.index[-1] for rrg in sectors.values())
    date_fmt = "%Y-%m-%d %H:%M" if interval_key == "1h" else "%Y-%m-%d"
    st.markdown(f"**Data as of:** {latest_date.strftime(date_fmt)}")

if not selected:
    st.warning("Select at least one sector from the sidebar.")
    st.stop()

fig = build_figure(sectors, selected, tail_length, interval_key)
st.plotly_chart(fig, use_container_width=True)