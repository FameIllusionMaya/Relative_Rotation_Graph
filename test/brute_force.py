import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "daily")
BENCHMARK_FILE = os.path.join(DATA_DIR, "SET.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brute_force")

# Brute force parameters
RS_RATIO_RANGE = range(5, 15)        # 8, 9, 10, 11, 12, 13, 14, 15
RS_MOMENTUM_RANGE = range(5, 15)     # 6, 7, 8, 9, 10, 11, 12, 13

# Smoothing methods: name -> function
SMOOTHING_METHODS = {
    # 1. พื้นฐาน
    # 'sma': lambda s, p: s.rolling(window=p).mean(),
    # 'ema_span': lambda s, p: s.ewm(span=p, adjust=False).mean(),
    # 'ema_alpha': lambda s, p: s.ewm(alpha=1/p, adjust=False).mean(),
    
    # 2. Weighted Moving Average (ให้น้ำหนักมากกับข้อมูลล่าสุด)
    'wma': lambda s, p: s.rolling(p).apply(
        lambda x: np.sum(np.arange(1, p+1) * x) / np.sum(np.arange(1, p+1)), raw=True
    ),
    
    # 3. Double EMA (DEMA) - ลด lag
    'dema': lambda s, p: 2 * s.ewm(span=p).mean() - s.ewm(span=p).mean().ewm(span=p).mean(),
    
    # 4. Triple EMA (TEMA) - ลด lag มากขึ้น
    'tema': lambda s, p: (
        3 * s.ewm(span=p).mean() 
        - 3 * s.ewm(span=p).mean().ewm(span=p).mean() 
        + s.ewm(span=p).mean().ewm(span=p).mean().ewm(span=p).mean()
    ),
    
    # 5. Hull Moving Average (HMA) - smooth + ลด lag
    'hma': lambda s, p: (
        (2 * s.ewm(span=p//2).mean() - s.ewm(span=p).mean())
        .rolling(window=int(np.sqrt(p))).mean()
    ),
    
    # 6. Kaufman Adaptive MA (KAMA) - ปรับตามความผันผวน
    'kama': lambda s, p: _kama(s, p),
    
    # 7. Zero-Lag EMA (ZLEMA)
    'zlema': lambda s, p: s.ewm(span=p).mean() + (s - s.shift(int((p-1)/2))).ewm(span=p).mean() * 0.5,
    
    # 8. Triangular MA (TMA) - smooth มาก
    'tma': lambda s, p: s.rolling(window=p).mean().rolling(window=p).mean(),
}

# Helper function for KAMA
def _kama(series, period, fast=2, slow=30):
    """Kaufman Adaptive Moving Average"""
    change = abs(series - series.shift(period))
    volatility = abs(series - series.shift(1)).rolling(period).sum()
    er = change / volatility  # Efficiency Ratio
    
    fast_sc = 2 / (fast + 1)
    slow_sc = 2 / (slow + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2  # Smoothing Constant
    
    kama = pd.Series(index=series.index, dtype=float)
    kama.iloc[period-1] = series.iloc[:period].mean()
    
    for i in range(period, len(series)):
        kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i] * (series.iloc[i] - kama.iloc[i-1])
    
    return kama

TAIL_LENGTH = 5
CENTER = 100

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_csv(path: str) -> pd.DataFrame:
    """Load a sector CSV, parse dates, and return weekly close prices."""
    df = pd.read_csv(path, parse_dates=["datetime"])
    df = df.sort_values("datetime")
    df = df.set_index("datetime")
    # weekly = df["close"].resample("W-FRI").last().dropna()
    # return weekly
    return df["close"].dropna()


def compute_rrg(sector_close: pd.Series,
                benchmark_close: pd.Series,
                rs_period: int,
                mom_period: int,
                smooth_func) -> pd.DataFrame:
    """Compute RS-Ratio and RS-Momentum with configurable parameters."""
    rs = sector_close / benchmark_close
    
    rs_sma = smooth_func(rs, rs_period)
    rs_ratio = CENTER + ((rs - rs_sma) / rs_sma) * CENTER
    
    ratio_sma = smooth_func(rs_ratio, mom_period)
    rs_momentum = CENTER + ((rs_ratio - ratio_sma) / ratio_sma) * CENTER

    result = pd.DataFrame({
        "rs_ratio": rs_ratio,
        "rs_momentum": rs_momentum,
    })
    return result.dropna()


def plot_rrg(sectors: dict, title: str, output_path: str):
    """Plot RRG chart and save to file."""
    fig, ax = plt.subplots(figsize=(12, 10))
    
    ax.axhline(CENTER, color="grey", linewidth=0.8, linestyle="--")
    ax.axvline(CENTER, color="grey", linewidth=0.8, linestyle="--")
    
    all_x, all_y = [], []
    cmap = plt.get_cmap("tab20", max(len(sectors), 1))
    colors = {name: cmap(i) for i, name in enumerate(sorted(sectors.keys()))}

    for name, rrg in sorted(sectors.items()):
        tail = rrg.iloc[-TAIL_LENGTH:]
        x = tail["rs_ratio"].values
        y = tail["rs_momentum"].values
        all_x.extend(x)
        all_y.extend(y)
        c = colors[name]

        ax.plot(x, y, color=c, linewidth=1.5, alpha=0.7)
        sizes = np.linspace(20, 60, len(x))
        ax.scatter(x, y, s=sizes, color=c, zorder=5, edgecolors="white", linewidths=0.3)
        ax.annotate(name, xy=(x[-1], y[-1]), xytext=(5, 5),
                    textcoords="offset points", fontsize=7, fontweight="bold", color=c)

    if all_x and all_y:
        x_margin = max((max(all_x) - min(all_x)) * 0.15, 0.5)
        y_margin = max((max(all_y) - min(all_y)) * 0.15, 0.5)
        ax.set_xlim(min(all_x) - x_margin, max(all_x) + x_margin)
        ax.set_ylim(min(all_y) - y_margin, max(all_y) + y_margin)

    xlo, xhi = ax.get_xlim()
    ylo, yhi = ax.get_ylim()
    ax.fill_between([CENTER, xhi], CENTER, yhi, color="green", alpha=0.06)
    ax.fill_between([xlo, CENTER], CENTER, yhi, color="blue", alpha=0.06)
    ax.fill_between([xlo, CENTER], ylo, CENTER, color="red", alpha=0.06)
    ax.fill_between([CENTER, xhi], ylo, CENTER, color="orange", alpha=0.06)

    offset = 0.3
    ax.text(xhi - offset, yhi - offset, "LEADING", ha="right", va="top", fontsize=11, color="green", alpha=0.5, fontweight="bold")
    ax.text(xlo + offset, yhi - offset, "IMPROVING", ha="left", va="top", fontsize=11, color="blue", alpha=0.5, fontweight="bold")
    ax.text(xlo + offset, ylo + offset, "LAGGING", ha="left", va="bottom", fontsize=11, color="red", alpha=0.5, fontweight="bold")
    ax.text(xhi - offset, ylo + offset, "WEAKENING", ha="right", va="bottom", fontsize=11, color="orange", alpha=0.5, fontweight="bold")

    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("RS-Ratio →", fontsize=10)
    ax.set_ylabel("RS-Momentum →", fontsize=10)
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load benchmark
    print("Loading data...")
    benchmark = load_csv(BENCHMARK_FILE)
    
    # Load all sector files
    sector_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    sector_files = [f for f in sector_files if os.path.basename(f) != "SET.csv"]
    
    sector_data = {}
    for fpath in sector_files:
        name = os.path.splitext(os.path.basename(fpath))[0]
        try:
            close = load_csv(fpath)
            common = close.index.intersection(benchmark.index)
            if len(common) >= 50:
                sector_data[name] = (close.loc[common], benchmark.loc[common])
        except Exception as e:
            print(f"Error loading {name}: {e}")
    
    print(f"Loaded {len(sector_data)} sectors")
    
    # Calculate total combinations
    total = len(RS_RATIO_RANGE) * len(RS_MOMENTUM_RANGE) * len(SMOOTHING_METHODS)
    count = 0
    
    print(f"\nRunning {total} combinations...")
    print(f"RS_RATIO_PERIOD: {list(RS_RATIO_RANGE)}")
    print(f"RS_MOMENTUM_PERIOD: {list(RS_MOMENTUM_RANGE)}")
    print(f"Methods: {list(SMOOTHING_METHODS.keys())}")
    print("-" * 60)
    
    # Brute force loop
    for method_name, smooth_func in SMOOTHING_METHODS.items():
        for rs_period in RS_RATIO_RANGE:
            for mom_period in RS_MOMENTUM_RANGE:
                count += 1
                
                # Compute RRG for all sectors
                sectors = {}
                for name, (sector_close, bench_close) in sector_data.items():
                    try:
                        rrg = compute_rrg(sector_close, bench_close, rs_period, mom_period, smooth_func)
                        if len(rrg) >= TAIL_LENGTH:
                            sectors[name] = rrg
                    except:
                        pass
                
                if not sectors:
                    continue
                
                # Generate filename: {RS_RATIO_PERIOD}_{RS_MOMENTUM_PERIOD}_{formula_name}.png
                filename = f"{rs_period}_{mom_period}_{method_name}.png"
                title = f"RRG | RS-Period: {rs_period} | Mom-Period: {mom_period} | Method: {method_name}"
                output_path = os.path.join(OUTPUT_DIR, filename)
                
                # Plot and save
                plot_rrg(sectors, title, output_path)
                
                # Progress update
                if count % 10 == 0 or count == total:
                    print(f"Progress: {count}/{total} ({100*count/total:.1f}%) - Saved: {filename}")
    
    print("-" * 60)
    print(f"Done! Saved {count} images to: {OUTPUT_DIR}")
    print(f"\nFile format: {{RS_RATIO_PERIOD}}_{{RS_MOMENTUM_PERIOD}}_{{formula_name}}.png")
    print(f"\nFormula names:")
    print(f"  sma       = rs.rolling(window=period).mean()")
    print(f"  ema_span  = rs.ewm(span=period, adjust=False).mean()")
    print(f"  ema_alpha = rs.ewm(alpha=1/period, adjust=False).mean()")