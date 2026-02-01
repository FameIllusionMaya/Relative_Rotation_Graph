import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for saving without GUI

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# DATA_DIR = os.path.dirname(os.path.abspath(__file__))
# BENCHMARK_FILE = os.path.join(DATA_DIR, "SET.csv")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "daily")
BENCHMARK_FILE = os.path.join(DATA_DIR, "SET.csv")


RS_RATIO_PERIOD = 12       # lookback for RS-Ratio normalisation
RS_MOMENTUM_PERIOD = 10    # lookback for RS-Momentum normalisation
TAIL_LENGTH = 5            # number of trailing weeks shown on the graph
CENTER = 100               # centre line for both axes

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_csv(path: str) -> pd.DataFrame:
    """Load a sector CSV, parse dates, and return weekly close prices."""
    df = pd.read_csv(path, parse_dates=["datetime"])
    df = df.sort_values("datetime")
    df = df.set_index("datetime")
    # Resample to weekly (Friday close) to reduce noise
    weekly = df["close"].resample("W-FRI").last().dropna()
    return weekly


def compute_rrg(sector_close: pd.Series,
                benchmark_close: pd.Series,
                rs_period: int = RS_RATIO_PERIOD,
                mom_period: int = RS_MOMENTUM_PERIOD) -> pd.DataFrame:
    """
    Compute RS-Ratio and RS-Momentum for a single sector.

    RS-Ratio   = 100 + normalised(RS / SMA(RS, rs_period))
    RS-Momentum = 100 + normalised(RS-Ratio / SMA(RS-Ratio, mom_period))
    """
    # Raw relative strength
    rs = sector_close / benchmark_close

    # RS-Ratio: ratio vs its own SMA, scaled around 100
    rs_sma = rs.rolling(window=rs_period).mean()
    rs_ratio = CENTER + ((rs - rs_sma) / rs_sma) * CENTER

    # RS-Momentum: ratio of RS-Ratio vs its own SMA, scaled around 100
    ratio_sma = rs_ratio.rolling(window=mom_period).mean()
    rs_momentum = CENTER + ((rs_ratio - ratio_sma) / ratio_sma) * CENTER

    result = pd.DataFrame({
        "rs_ratio": rs_ratio,
        "rs_momentum": rs_momentum,
    })
    return result.dropna()


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
benchmark = load_csv(BENCHMARK_FILE)

sector_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
sector_files = [f for f in sector_files if os.path.basename(f) != "SET.csv"]

sectors = {}
for fpath in sector_files:
    name = os.path.splitext(os.path.basename(fpath))[0]
    try:
        close = load_csv(fpath)
        # Align dates with benchmark
        common = close.index.intersection(benchmark.index)
        if len(common) < RS_RATIO_PERIOD + RS_MOMENTUM_PERIOD + TAIL_LENGTH:
            print(f"Skipping {name}: not enough overlapping data")
            continue
        rrg = compute_rrg(close.loc[common], benchmark.loc[common])
        if len(rrg) >= TAIL_LENGTH:
            sectors[name] = rrg
    except Exception as e:
        print(f"Error processing {name}: {e}")

print(f"Loaded {len(sectors)} sectors")

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 10))

# Quadrant background colours (very light)
ax.axhline(CENTER, color="grey", linewidth=0.8, linestyle="--")
ax.axvline(CENTER, color="grey", linewidth=0.8, linestyle="--")

# Shade quadrants
xlim_pad, ylim_pad = 4, 4  # will be adjusted after plotting
all_x = []
all_y = []

# Assign a unique colour to each sector
cmap = plt.get_cmap("tab20", len(sectors))
colors = {name: cmap(i) for i, name in enumerate(sorted(sectors.keys()))}

for name, rrg in sorted(sectors.items()):
    tail = rrg.iloc[-TAIL_LENGTH:]
    x = tail["rs_ratio"].values
    y = tail["rs_momentum"].values
    all_x.extend(x)
    all_y.extend(y)
    c = colors[name]

    # Tail line
    ax.plot(x, y, color=c, linewidth=1.5, alpha=0.7)

    # Dots along the tail (smaller for older, bigger for newest)
    sizes = np.linspace(20, 60, len(x))
    ax.scatter(x, y, s=sizes, color=c, zorder=5, edgecolors="white", linewidths=0.3)

    # Label at the most recent point
    ax.annotate(
        name,
        xy=(x[-1], y[-1]),
        xytext=(5, 5),
        textcoords="offset points",
        fontsize=7,
        fontweight="bold",
        color=c,
    )

# Axis limits with some padding
if all_x and all_y:
    x_margin = max((max(all_x) - min(all_x)) * 0.15, 0.5)
    y_margin = max((max(all_y) - min(all_y)) * 0.15, 0.5)
    ax.set_xlim(min(all_x) - x_margin, max(all_x) + x_margin)
    ax.set_ylim(min(all_y) - y_margin, max(all_y) + y_margin)

# Shade the four quadrants
xlo, xhi = ax.get_xlim()
ylo, yhi = ax.get_ylim()
ax.fill_between([CENTER, xhi], CENTER, yhi, color="green",  alpha=0.06, label="Leading")
ax.fill_between([xlo, CENTER], CENTER, yhi, color="blue",   alpha=0.06, label="Improving")
ax.fill_between([xlo, CENTER], ylo, CENTER, color="red",    alpha=0.06, label="Lagging")
ax.fill_between([CENTER, xhi], ylo, CENTER, color="orange",  alpha=0.06, label="Weakening")

# Quadrant labels
offset = 0.3
ax.text(xhi - offset, yhi - offset, "LEADING",    ha="right", va="top",    fontsize=11, color="green",  alpha=0.5, fontweight="bold")
ax.text(xlo + offset, yhi - offset, "IMPROVING",   ha="left",  va="top",    fontsize=11, color="blue",   alpha=0.5, fontweight="bold")
ax.text(xlo + offset, ylo + offset, "LAGGING",     ha="left",  va="bottom", fontsize=11, color="red",    alpha=0.5, fontweight="bold")
ax.text(xhi - offset, ylo + offset, "WEAKENING",   ha="right", va="bottom", fontsize=11, color="orange", alpha=0.5, fontweight="bold")

# Latest date for the title
latest_date = max(rrg.index[-1] for rrg in sectors.values())
ax.set_title(f"Relative Rotation Graph — SET Sectors\n(weekly, as of {latest_date.strftime('%Y-%m-%d')})",
             fontsize=14, fontweight="bold")
ax.set_xlabel("RS-Ratio →", fontsize=12)
ax.set_ylabel("RS-Momentum →", fontsize=12)
ax.grid(True, alpha=0.2)

plt.tight_layout()

output_path = os.path.join(DATA_DIR, "rrg_output.png")
plt.savefig(output_path, dpi=150)
print(f"Saved: {output_path}")
print("Done.")

