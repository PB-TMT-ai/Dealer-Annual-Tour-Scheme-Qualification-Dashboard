"""
FY 26 — Dealer Annual Tour Scheme Qualification Dashboard
Single-file Streamlit app.
"""

import datetime as dt
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
from src.lib.logger import info, error  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DATA_DIR = PROJECT_ROOT / "data"
SHEET_NAME = "FY 26_qualification scenario"
HEADER_ROW = 2  # 0-indexed


def _find_excel_file() -> Path:
    """Auto-detect the latest .xlsx file in data/ folder."""
    xlsx_files = sorted(DATA_DIR.glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not xlsx_files:
        st.error("❌ No .xlsx file found in the `data/` folder. Please add one.")
        st.stop()
    if len(xlsx_files) > 1:
        st.sidebar.info(f"📂 Found {len(xlsx_files)} Excel files. Using latest: **{xlsx_files[0].name}**")
    return xlsx_files[0]

TOTAL_RETAIL_MT = 143_000.0

# Ordered list of the 12 FY-26 month column names AFTER normalisation
MONTH_LABELS = [
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
]

# Slab configuration — single source of truth
SLAB_CONFIG = [
    {
        "slab": "A",
        "range": "200–300 MT",
        "lower": 200.0,
        "upper": 300.0,
        "gift": "Domestic Trip 1 pax 3N-4D",
        "gift_full": "Domestic Trip 1 pax 3N-4D",
        "category": "A",
        "value": 50_000,
        "value_tds": 55_000,
    },
    {
        "slab": "B",
        "range": "300–500 MT",
        "lower": 300.0,
        "upper": 500.0,
        "gift": "Intl Trip (1 pax South Asia) 3N-4D",
        "gift_full": "International Trip (1 pax South Asia) 3N-4D",
        "category": "B",
        "value": 70_000,
        "value_tds": 77_000,
    },
    {
        "slab": "C",
        "range": "500–750 MT",
        "lower": 500.0,
        "upper": 750.0,
        "gift": "Intl Trip Almaty / 2 pax SE Asia 3N-4D",
        "gift_full": "Intl Trip (1 pax Almaty) / (2 pax SE Asia) 3N-4D",
        "category": "C",
        "value": 100_000,
        "value_tds": 110_000,
    },
    {
        "slab": "D",
        "range": "750–1250 MT",
        "lower": 750.0,
        "upper": 1250.0,
        "gift": "Intl Trip 2 pax SE Asia + EV / 2 pax Almaty",
        "gift_full": "Intl Trip (2 pax SE Asia) + EV Scooter / (2 pax Almaty)",
        "category": "D",
        "value": 220_000,
        "value_tds": 242_000,
    },
    {
        "slab": "E",
        "range": "≥ 1250 MT",
        "lower": 1250.0,
        "upper": float("inf"),
        "gift": "Luxury Intl Trip (2 pax Dubai) 3N-4D",
        "gift_full": "Luxury International Trip (2 pax Dubai) 3N-4D",
        "category": "E",
        "value": 240_000,
        "value_tds": 264_000,
    },
]

SLAB_GIFT_MAP = {s["slab"]: s["gift"] for s in SLAB_CONFIG}
SLAB_GIFT_MAP["No Slab"] = "Non-Qualifier"
SLAB_GIFT_MAP["Max Slab"] = ""

SLAB_VALUE_TDS = {s["slab"]: s["value_tds"] for s in SLAB_CONFIG}
SLAB_VALUE_TDS["No Slab"] = 0

SLAB_COLORS = {
    "A": "#3b82f6",
    "B": "#8b5cf6",
    "C": "#f59e0b",
    "D": "#ef4444",
    "E": "#10b981",
    "No Slab": "#94a3b8",
}

SLAB_ORDER = ["A", "B", "C", "D", "E", "No Slab"]

NEXT_SLAB_MAP = {
    "No Slab": "A",
    "A": "B",
    "B": "C",
    "C": "D",
    "D": "E",
    "E": "Max Slab",
}

NEXT_SLAB_THRESHOLD = {
    "No Slab": 200.0,
    "A": 300.0,
    "B": 500.0,
    "C": 750.0,
    "D": 1250.0,
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


def format_indian(number: float, prefix: str = "", decimal: int = 0) -> str:
    """Format *number* with Indian comma grouping (12,34,567)."""
    if pd.isna(number):
        return f"{prefix}0"
    is_negative = number < 0
    number = abs(number)
    int_part = int(number)
    dec_part = round(number - int_part, decimal) if decimal else 0

    s = str(int_part)
    if len(s) <= 3:
        result = s
    else:
        last3 = s[-3:]
        remaining = s[:-3]
        groups: list[str] = []
        while len(remaining) > 2:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.append(remaining)
        groups.reverse()
        result = ",".join(groups) + "," + last3

    if decimal:
        frac = f"{dec_part:.{decimal}f}".split(".")[1]
        result += "." + frac

    if is_negative:
        result = "-" + result
    return f"{prefix}{result}"


def assign_slab(vol: float) -> str:
    """Return slab letter based on FY 26 total volume."""
    if pd.isna(vol) or vol < 200:
        return "No Slab"
    if vol < 300:
        return "A"
    if vol < 500:
        return "B"
    if vol < 750:
        return "C"
    if vol < 1250:
        return "D"
    return "E"


def get_next_slab(current: str) -> str:
    return NEXT_SLAB_MAP.get(current, "Max Slab")


def volume_to_next(vol: float, current: str) -> Optional[float]:
    """MT remaining to reach next slab. None for slab E."""
    if current == "E":
        return None
    threshold = NEXT_SLAB_THRESHOLD.get(current, 200.0)
    gap = threshold - vol
    return max(gap, 0.0)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — CUSTOM CSS
# ═══════════════════════════════════════════════════════════════════════════


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        /* ---------- global ---------- */
        .block-container { padding-top: 1.5rem; }
        .stTabs [data-baseweb="tab"] { font-size: 1rem; font-weight: 500; }

        /* ---------- header bar ---------- */
        .header-bar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 0.75rem 0; margin-bottom: 0.25rem;
        }
        .header-bar h1 { font-size: 1.6rem; font-weight: 700; color: #0f172a; margin: 0; }
        .header-bar span { font-size: 0.85rem; color: #64748b; }

        /* ---------- slab card ---------- */
        .slab-card {
            background: #ffffff;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            padding: 1.1rem 1rem;
            height: 100%;
        }
        .slab-card .slab-title {
            font-size: 0.95rem; font-weight: 600; margin: 0;
        }
        .slab-card .slab-gift {
            font-size: 0.72rem; color: #64748b; margin: 0.2rem 0 0.6rem;
            line-height: 1.3;
        }
        .slab-card .slab-count {
            font-size: 1.7rem; font-weight: 700; margin: 0;
        }
        .slab-card .slab-vol {
            font-size: 0.8rem; color: #475569; margin: 0.15rem 0 0;
        }

        /* ---------- kpi card ---------- */
        .kpi-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 0.5rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            padding: 1rem 1.1rem;
            text-align: center;
        }
        .kpi-card .kpi-label {
            font-size: 0.78rem; color: #64748b; margin: 0 0 0.3rem;
            text-transform: uppercase; letter-spacing: 0.03em;
        }
        .kpi-card .kpi-value {
            font-size: 1.35rem; font-weight: 700; color: #0f172a; margin: 0;
        }
        .kpi-card .kpi-sub {
            font-size: 0.75rem; color: #475569; margin: 0.2rem 0 0;
        }

        /* ---------- costing table ---------- */
        .total-row { font-weight: 700; background: #f1f5f9; }

        /* ---------- hide streamlit chrome ---------- */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

# The 12 FY-26 month columns in the raw Excel.
# Excel stores date headers as datetime.datetime objects (NOT pd.Timestamp);
# the Dec-25 column is a plain string.
_MONTH_RENAME = {
    dt.datetime(2025, 4, 1): "Apr",
    dt.datetime(2025, 5, 1): "May",
    dt.datetime(2025, 6, 1): "Jun",
    dt.datetime(2025, 7, 1): "Jul",
    dt.datetime(2025, 8, 1): "Aug",
    dt.datetime(2025, 9, 1): "Sep",
    dt.datetime(2025, 10, 1): "Oct",
    dt.datetime(2025, 11, 1): "Nov",
    "Dec-25": "Dec",
    dt.datetime(2026, 1, 1): "Jan",
    dt.datetime(2026, 2, 1): "Feb",
    dt.datetime(2026, 3, 1): "Mar",
}


@st.cache_data
def load_data() -> tuple[pd.DataFrame, list[str]]:
    """Read Excel, clean, add derived columns. Returns (df, month_col_list)."""
    data_path = _find_excel_file()
    info(f"Loading Excel data from {data_path.name} …")
    raw = pd.read_excel(data_path, sheet_name=SHEET_NAME, header=HEADER_ROW)
    info(f"Loaded {len(raw)} rows × {len(raw.columns)} cols")

    # ── rename month columns ──────────────────────────────────────────
    rename_map: dict = {}
    month_cols: list[str] = []
    for target, label in _MONTH_RENAME.items():
        for col in raw.columns:
            match = False
            if isinstance(target, dt.datetime) and isinstance(col, (dt.datetime, pd.Timestamp)):
                match = col == target
            elif isinstance(target, str) and isinstance(col, str):
                match = col == target
            if match:
                rename_map[col] = label
                break
        month_cols.append(label)

    raw.rename(columns=rename_map, inplace=True)

    # ── numeric coercion on month + aggregate cols ────────────────────
    for col in month_cols:
        if col in raw.columns:
            raw[col] = pd.to_numeric(raw[col], errors="coerce").fillna(0.0)
    raw["FY 26 total"] = pd.to_numeric(raw["FY 26 total"], errors="coerce").fillna(0.0)
    raw["FY 25 vol."] = pd.to_numeric(raw.get("FY 25 vol."), errors="coerce").fillna(0.0)
    raw["Avg. monthly vol."] = pd.to_numeric(
        raw.get("Avg. monthly vol."), errors="coerce"
    ).fillna(0.0)

    # ── clean State ───────────────────────────────────────────────────
    raw["State"] = raw["State"].apply(
        lambda x: "Unknown"
        if (isinstance(x, (int, float)) and not pd.isna(x)) or pd.isna(x)
        else str(x).strip().title()
    )
    # handle any remaining edge‑case 0‑strings
    raw.loc[raw["State"].isin(["0", "0.0"]), "State"] = "Unknown"

    # ── clean Zone ────────────────────────────────────────────────────
    raw["Zone"] = raw["Zone"].apply(
        lambda x: "Unknown"
        if (isinstance(x, (int, float)) and not pd.isna(x)) or pd.isna(x)
        else str(x).strip()
    )
    raw.loc[raw["Zone"].isin(["0", "0.0"]), "Zone"] = "Unknown"

    # ── clean District (mixed int/str) ────────────────────────────────
    raw["District"] = raw["District"].apply(
        lambda x: "" if pd.isna(x) or (isinstance(x, (int, float)) and x == 0) else str(x).strip()
    )
    # ── clean Distributor Name ────────────────────────────────────────
    raw["Distributor Name"] = raw["Distributor Name"].apply(
        lambda x: "" if pd.isna(x) else str(x).strip()
    )

    # ── clean Distributor self-counter flag ──────────────────────────
    if "Distributor self-counter (Yes/No)" in raw.columns:
        raw["Self-Counter"] = (
            raw["Distributor self-counter (Yes/No)"]
            .fillna("No")
            .astype(str)
            .str.strip()
            .str.title()
        )
        raw.loc[~raw["Self-Counter"].isin(["Yes", "No"]), "Self-Counter"] = "No"
    else:
        raw["Self-Counter"] = "No"

    # ── derived columns ───────────────────────────────────────────────
    raw["Qualified Slab"] = raw["FY 26 total"].apply(assign_slab)
    # force self-counter dealers to No Slab
    raw.loc[raw["Self-Counter"] == "Yes", "Qualified Slab"] = "No Slab"
    raw["Lifting Frequency"] = raw[month_cols].gt(0).sum(axis=1).astype(int)
    raw["Next Upgrade Slab"] = raw["Qualified Slab"].map(NEXT_SLAB_MAP)
    raw["Vol to Next Slab"] = raw.apply(
        lambda r: volume_to_next(r["FY 26 total"], r["Qualified Slab"]), axis=1
    )

    info(f"Data ready. Slab distribution: {raw['Qualified Slab'].value_counts().to_dict()}")
    return raw, month_cols


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 — CASCADING FILTERS
# ═══════════════════════════════════════════════════════════════════════════


def render_cascading_filters(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Render Zone → State → Distributor → District → Slab dropdowns. Returns filtered df."""

    def _opts(series: pd.Series) -> list[str]:
        """Return sorted unique string values, filtering out blanks."""
        vals = series.dropna().astype(str).unique().tolist()
        vals = [v for v in vals if v not in ("", "0", "0.0", "nan")]
        return ["All"] + sorted(vals)

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        zone = st.selectbox("Zone", _opts(df["Zone"]), key=f"{key}_zone")
    filt = df if zone == "All" else df[df["Zone"] == zone]

    with c2:
        state = st.selectbox("State", _opts(filt["State"]), key=f"{key}_state")
    if state != "All":
        filt = filt[filt["State"] == state]

    with c3:
        distrib = st.selectbox("Distributor", _opts(filt["Distributor Name"]), key=f"{key}_dist")
    if distrib != "All":
        filt = filt[filt["Distributor Name"] == distrib]

    with c4:
        district = st.selectbox("District", _opts(filt["District"]), key=f"{key}_district")
    if district != "All":
        filt = filt[filt["District"].astype(str) == district]

    with c5:
        slab_opts = ["All"] + SLAB_ORDER
        slab = st.selectbox("Slab", slab_opts, key=f"{key}_slab")
    if slab != "All":
        filt = filt[filt["Qualified Slab"] == slab]

    return filt


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 — TAB 1: SCHEME OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════


def _render_slab_card(
    slab: str, gift: str, count: int, volume: float, color: str, vol_range: str
) -> None:
    st.markdown(
        f"""
        <div class="slab-card" style="border-left: 4px solid {color};">
            <p class="slab-title" style="color:{color};">Slab {slab} · {vol_range}</p>
            <p class="slab-gift">{gift}</p>
            <p class="slab-count" style="color:{color};">{count}</p>
            <p class="slab-vol">Qualified Dealers</p>
            <p class="slab-count" style="font-size:1.1rem; color:#334155;">{format_indian(volume, decimal=1)} MT</p>
            <p class="slab-vol">Total Volume</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scheme_overview(df: pd.DataFrame, month_cols: list[str]) -> None:
    filtered = render_cascading_filters(df, "ov")

    if filtered.empty:
        st.info("No dealers match the selected filters.")
        return

    # ── Slab Summary Cards ────────────────────────────────────────────
    st.markdown("#### Slab Summary")
    cols = st.columns(6)
    slab_range_map = {s["slab"]: s["range"] for s in SLAB_CONFIG}
    slab_range_map["No Slab"] = "0–200 MT"

    for idx, slab in enumerate(SLAB_ORDER):
        subset = filtered[filtered["Qualified Slab"] == slab]
        with cols[idx]:
            _render_slab_card(
                slab=slab,
                gift=SLAB_GIFT_MAP[slab],
                count=len(subset),
                volume=subset["FY 26 total"].sum(),
                color=SLAB_COLORS[slab],
                vol_range=slab_range_map[slab],
            )

    st.markdown("---")

    # ── Dealer Search ─────────────────────────────────────────────────
    search = st.text_input("🔍 Search Dealer Name", "", key="ov_search")
    if search:
        filtered = filtered[
            filtered["Name of the Dealer"]
            .fillna("")
            .str.contains(search, case=False, na=False)
        ]

    if filtered.empty:
        st.info("No dealers match the search query.")
        return

    # ── Dealer Table ──────────────────────────────────────────────────
    display = (
        filtered[
            [
                "Name of the Dealer",
                "Distributor Name",
                "State",
                "Zone",
                "Qualified Slab",
                "Lifting Frequency",
                "FY 26 total",
                "Self-Counter",
                "Next Upgrade Slab",
                "Vol to Next Slab",
            ]
        ]
        .copy()
        .sort_values("FY 26 total", ascending=False)
        .reset_index(drop=True)
    )

    # Format lifting frequency as "X / 12"
    display["Lifting Frequency"] = display["Lifting Frequency"].apply(
        lambda x: f"{x} / 12"
    )
    # Format volumes
    display["FY 26 total"] = display["FY 26 total"].apply(lambda v: round(v, 1))
    display["Vol to Next Slab"] = display["Vol to Next Slab"].apply(
        lambda v: "—" if pd.isna(v) else round(v, 1)
    )

    display.rename(
        columns={
            "Name of the Dealer": "Dealer Name",
            "Distributor Name": "Distributor",
            "FY 26 total": "FY 26 Volume (MT)",
            "Vol to Next Slab": "Vol. to Next Slab (MT)",
        },
        inplace=True,
    )

    def _highlight_self_counter(row: pd.Series) -> list[str]:
        if row.get("Self-Counter") == "Yes":
            return ["background-color: #fef3c7"] * len(row)
        return [""] * len(row)

    styled_display = display.style.apply(_highlight_self_counter, axis=1)
    st.dataframe(styled_display, use_container_width=True, height=520, hide_index=True)
    st.caption(f"Showing **{len(display)}** dealers")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 — TAB 2: DEALER DEEP DIVE
# ═══════════════════════════════════════════════════════════════════════════


def render_dealer_deep_dive(df: pd.DataFrame, month_cols: list[str]) -> None:
    filtered = render_cascading_filters(df, "dd")

    if filtered.empty:
        st.info("No dealers match the selected filters.")
        return

    dealer_names = sorted(
        filtered["Name of the Dealer"].dropna().astype(str).unique().tolist()
    )

    if not dealer_names:
        st.info("No dealers available for selection.")
        return

    selected = st.selectbox(
        "Select Dealer",
        [""] + dealer_names,
        key="dd_dealer",
        format_func=lambda x: "— Select a Dealer —" if x == "" else x,
    )

    if not selected:
        st.info("👆 Select a dealer from the dropdown above to view their performance.")
        return

    row = filtered[filtered["Name of the Dealer"] == selected].iloc[0]

    fy26_vol = row["FY 26 total"]
    slab = row["Qualified Slab"]
    freq = int(row["Lifting Frequency"])
    next_s = get_next_slab(slab)
    gap = volume_to_next(fy26_vol, slab)

    # ── KPI Cards ─────────────────────────────────────────────────────
    is_self_counter = row.get("Self-Counter", "No") == "Yes"
    sc_badge = (
        '<span style="display:inline-block;margin-left:0.7rem;padding:0.15rem 0.7rem;'
        'font-size:0.75rem;font-weight:600;border-radius:999px;vertical-align:middle;'
        f'background:{"#fef3c7" if is_self_counter else "#dcfce7"};'
        f'color:{"#92400e" if is_self_counter else "#166534"};">'
        f'Self Counter: {"Yes" if is_self_counter else "No"}</span>'
    )
    st.markdown(
        f'<h4 style="margin:0;">Key Performance Indicators {sc_badge}</h4>',
        unsafe_allow_html=True,
    )
    k1, k2, k3, k4, k5 = st.columns(5)

    def _kpi(col, label: str, value: str, sub: str = "") -> None:
        with col:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <p class="kpi-label">{label}</p>
                    <p class="kpi-value">{value}</p>
                    <p class="kpi-sub">{sub}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    _kpi(k1, "Lifting Frequency", f"{freq} / 12", "months active")
    _kpi(k2, "FY 26 Volume", f"{format_indian(fy26_vol, decimal=1)} MT", "total volume")
    _kpi(
        k3,
        "Qualified Slab",
        f"Slab {slab}" if slab != "No Slab" else "No Slab",
        SLAB_GIFT_MAP.get(slab, ""),
    )
    _kpi(
        k4,
        "Next Upgrade Slab",
        f"Slab {next_s}" if next_s not in ("Max Slab",) else "Max Slab Reached",
        SLAB_GIFT_MAP.get(next_s, "") if next_s != "Max Slab" else "Already at highest tier",
    )
    _kpi(
        k5,
        "Vol. to Upgrade",
        f"{format_indian(gap, decimal=1)} MT" if gap is not None else "—",
        "remaining to next slab" if gap is not None else "Max slab reached",
    )

    st.markdown("---")

    # ── Monthly Lifting Bar Chart ─────────────────────────────────────
    volumes = [float(row[m]) if pd.notna(row.get(m)) else 0.0 for m in month_cols]
    avg_vol = float(np.mean(volumes))

    colors = ["#10b981" if v > avg_vol else "#f59e0b" for v in volumes]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=MONTH_LABELS,
            y=volumes,
            marker_color=colors,
            text=[f"{v:.1f}" for v in volumes],
            textposition="outside",
            hovertemplate="%{x}: <b>%{y:.1f} MT</b><extra></extra>",
            name="Monthly Volume",
        )
    )
    fig.add_hline(
        y=avg_vol,
        line_dash="dash",
        line_color="#64748b",
        line_width=1.5,
        annotation_text=f"Avg: {avg_vol:.1f} MT",
        annotation_position="top right",
        annotation_font_color="#64748b",
    )

    y_max = max(volumes) * 1.25 if max(volumes) > 0 else 10
    fig.update_layout(
        title=f"{selected} — Monthly Lifting FY 26",
        xaxis_title="Month",
        yaxis_title="Volume (MT)",
        yaxis_range=[0, y_max],
        plot_bgcolor="white",
        height=430,
        margin=dict(t=60, b=50, l=60, r=40),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9")

    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8 — TAB 3: SCHEME COSTING
# ═══════════════════════════════════════════════════════════════════════════


def render_scheme_costing(df: pd.DataFrame) -> None:
    # ── Slab Cost Summary Table ───────────────────────────────────────
    st.markdown("#### Slab-wise Cost Summary")

    rows: list[dict] = []
    total_dealers = 0
    total_cost = 0

    for cfg in SLAB_CONFIG:
        slab = cfg["slab"]
        count = int((df["Qualified Slab"] == slab).sum())
        cost = count * cfg["value_tds"]
        total_dealers += count
        total_cost += cost
        rows.append(
            {
                "Slab": f"{slab} ({cfg['range']})",
                "Gift / Reward": cfg["gift_full"],
                "Category": cfg["category"],
                "Gift Value with TDS (₹)": format_indian(cfg["value_tds"], prefix="₹"),
                "# Qualified Dealers": count,
                "Total Cost (₹)": format_indian(cost, prefix="₹"),
            }
        )

    # Total row
    rows.append(
        {
            "Slab": "TOTAL",
            "Gift / Reward": "",
            "Category": "",
            "Gift Value with TDS (₹)": "",
            "# Qualified Dealers": total_dealers,
            "Total Cost (₹)": format_indian(total_cost, prefix="₹"),
        }
    )

    cost_df = pd.DataFrame(rows)
    st.dataframe(cost_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Scheme Efficiency Metrics ─────────────────────────────────────
    st.markdown("#### Scheme Efficiency Metrics")

    total_secondary = float(df["FY 26 total"].sum())
    qualified_mask = df["Qualified Slab"] != "No Slab"
    qualified_vol = float(df.loc[qualified_mask, "FY 26 total"].sum())
    pct_under_scheme = (
        (qualified_vol / total_secondary * 100) if total_secondary > 0 else 0.0
    )
    per_mt_cost = total_cost / TOTAL_RETAIL_MT if TOTAL_RETAIL_MT > 0 else 0.0

    m1, m2, m3 = st.columns(3)
    m4, m5, m6 = st.columns(3)

    with m1:
        st.metric("Total Retail Sales (MT)", f"{format_indian(TOTAL_RETAIL_MT)} MT")
    with m2:
        st.metric(
            "Total Secondary Sales (MT)",
            f"{format_indian(total_secondary, decimal=1)} MT",
        )
    with m3:
        st.metric(
            "Qualified Volume (MT)",
            f"{format_indian(qualified_vol, decimal=1)} MT",
        )
    with m4:
        st.metric("% Volume Under Scheme", f"{pct_under_scheme:.1f}%")
    with m5:
        st.metric("Total Scheme Cost", format_indian(total_cost, prefix="₹"))
    with m6:
        st.metric("Per MT Cost (₹/MT)", f"₹{per_mt_cost:,.2f}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9 — MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    st.set_page_config(
        page_title="FY26 Tour Scheme Dashboard",
        layout="wide",
        page_icon="🏆",
    )
    inject_custom_css()

    # Header bar
    st.markdown(
        """
        <div class="header-bar">
            <h1>🏆 FY 26 — Dealer Annual Tour Scheme Qualification</h1>
            <span>Data as of: FY 2025-26</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Load data
    df, month_cols = load_data()

    # Tabs
    tab1, tab2, tab3 = st.tabs(
        ["📊 Scheme Overview", "🔍 Dealer Deep Dive", "💰 Scheme Costing"]
    )

    with tab1:
        render_scheme_overview(df, month_cols)
    with tab2:
        render_dealer_deep_dive(df, month_cols)
    with tab3:
        render_scheme_costing(df)


if __name__ == "__main__":
    main()
