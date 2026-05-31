"""PsO Market Access Intelligence — payer prior-authorization lens.

Consulting-grade Streamlit dashboard built on the best extraction results
(result__15_.xlsx). All tabs are driven by a single all-brand filter; the
TREMFYA vs STELARA paired insights remain the analytical centrepiece.
"""
from __future__ import annotations
import io
import re
from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================================
#  PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="PsO Market Access Intelligence",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
#  DESIGN SYSTEM
# ============================================================================
INK         = "#1F2937"
INK_SOFT    = "#4B5563"
SLATE       = "#6B7280"
LINE        = "#E5E7EB"
LINE_SOFT   = "#F1EFE9"
PAPER       = "#FBFAF6"
CARD        = "#FFFFFF"
NAVY        = "#1E293B"
AMBER       = "#D97706"
AMBER_SOFT  = "#FBBF24"

# Signature brand colours
TREMFYA_C       = "#047857"
TREMFYA_LIGHT   = "#10B981"
STELARA_C       = "#6D28D9"
STELARA_LIGHT   = "#A78BFA"

FOCUS_BRANDS = ["TREMFYA", "STELARA"]

# Full brand palette — every brand in the corpus gets a distinct colour so the
# all-brand filter never falls back to monochrome.
_BRAND_PALETTE = {
    "TREMFYA":   TREMFYA_C,
    "STELARA":   STELARA_C,
    "SKYRIZI":   "#4F46E5",
    "COSENTYX":  "#DC2626",
    "BIMZELX":   "#DB2777",
    "ILUMYA":    "#65A30D",
    "OTEZLA":    "#9333EA",
    "AMJEVITA":  "#2563EB",
    "ENBREL":    "#EA580C",
    "CIMZIA":    "#0E7490",
    "REMICADE":  "#CA8A04",
    "SILIQ":     "#E11D48",
    "YESINTEK":  "#0D9488",
    "OTULFI":    "#7C3AED",
    "ACITRETIN": "#78716C",
}
_FALLBACK_CYCLE = ["#2563EB", "#DC2626", "#0D9488", "#9333EA", "#EA580C",
                   "#65A30D", "#DB2777", "#0E7490", "#CA8A04", "#4F46E5"]


def brand_color(b: str, i: int = 0) -> str:
    return _BRAND_PALETTE.get(str(b).upper(), _FALLBACK_CYCLE[i % len(_FALLBACK_CYCLE)])


# Access tiers — aligned to the 0 / 25 / 50 / 75 / 100 framework, anchored to
# the FDA label (50 = parity). This is the single source of truth for "points".
ACCESS_TIER_ORDER = ["No access", "Restricted", "Parity", "Preferred", "Open"]
ACCESS_TIER_COLOR = {
    "No access":   "#B91C1C",
    "Restricted":  "#EA580C",
    "Parity":      "#CA8A04",
    "Preferred":   "#16A34A",
    "Open":        "#047857",
    "Unscored":    "#94A3B8",
}
ACCESS_TIER_MEANING = {
    "No access":  "Not covered / excluded for PsO",
    "Restricted": "More restrictive than the FDA label (e.g. biologic step-through)",
    "Parity":     "Management mirrors the FDA label",
    "Preferred":  "Lighter than the FDA label",
    "Open":       "Effectively unrestricted access",
}

ARCHETYPE_ORDER = ["Open access", "Standard access", "Tight access"]
ARCHETYPE_COLOR = {
    "Open access":     "#16A34A",
    "Standard access": "#CA8A04",
    "Tight access":    "#B91C1C",
}

# Section accent palette — used to give each section its own colour block so the
# layout reads less monochromatic.
SEC = {
    "exec":     "#D97706",  # amber
    "param":    "#2563EB",  # blue
    "compare":  "#0D9488",  # teal
    "drivers":  "#DB2777",  # magenta
    "method":   "#7C3AED",  # violet
    "explorer": "#0E7490",  # cyan
}

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Manrope, -apple-system, BlinkMacSystemFont, sans-serif",
              color=INK, size=13),
    margin=dict(l=10, r=10, t=20, b=10),
    xaxis=dict(showgrid=False, linecolor=LINE, ticks="outside",
               tickcolor=LINE, tickfont=dict(color=INK_SOFT, size=11)),
    yaxis=dict(gridcolor="#F0EDE5", linecolor=LINE, ticks="outside",
               tickcolor=LINE, zeroline=False,
               tickfont=dict(color=INK_SOFT, size=11)),
    legend=dict(font=dict(size=11, color=INK_SOFT), bgcolor="rgba(0,0,0,0)"),
    hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINE, font_family="Manrope",
                    font_color=INK),
)


def apply_layout(fig: go.Figure, **overrides) -> go.Figure:
    merged = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PLOTLY_BASE.items()}
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    fig.update_layout(**merged)
    return fig


CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Manrope:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"], button, input, select, textarea {{
    font-family: 'Manrope', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: {INK};
}}
.stApp {{ background: {PAPER}; color: {INK}; }}
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
section.main > div.block-container {{ padding-top: 1.5rem; padding-bottom: 4rem; max-width: 1380px; }}
/* Masthead */
.zs-masthead {{
    display: flex; justify-content: space-between; align-items: flex-end;
    padding-bottom: 14px; margin-bottom: 18px; border-bottom: 1px solid {LINE};
}}
.zs-masthead-left .eyebrow {{
    font-size: 10.5px; letter-spacing: 0.22em; text-transform: uppercase;
    color: {AMBER}; font-weight: 700; margin-bottom: 4px;
}}
.zs-masthead-left h1 {{
    font-family: 'Fraunces', Georgia, serif !important;
    font-weight: 600; font-size: 28px; line-height: 1.15;
    letter-spacing: -0.015em; color: {INK}; margin: 0 0 4px 0;
}}
.zs-masthead-left .deck {{ font-size: 13px; color: {INK_SOFT}; max-width: 760px; line-height: 1.45; }}
.zs-masthead-right {{
    text-align: right; font-size: 11px; letter-spacing: 0.06em;
    text-transform: uppercase; color: {SLATE}; font-weight: 500;
}}
.zs-pill-tremfya, .zs-pill-stelara {{
    display: inline-block; padding: 4px 11px; margin-left: 6px;
    border-radius: 2px; font-weight: 700; font-size: 10px;
    letter-spacing: 0.14em; color: #FFFFFF;
}}
.zs-pill-tremfya {{ background: {TREMFYA_C}; }}
.zs-pill-stelara {{ background: {STELARA_C}; }}
/* Colour-blocked section heading */
.zs-sec {{
    margin: 30px 0 14px 0; padding: 12px 16px; border-radius: 5px;
    border-left: 5px solid {AMBER};
    background: linear-gradient(90deg, rgba(217,119,6,0.07) 0%, rgba(217,119,6,0.0) 60%);
}}
.zs-sec h2 {{
    font-family: 'Fraunces', Georgia, serif !important;
    font-weight: 600; font-size: 20px; line-height: 1.2;
    letter-spacing: -0.01em; color: {INK}; margin: 0 0 3px 0;
}}
.zs-sec .deck {{ font-size: 12.5px; color: {INK_SOFT}; line-height: 1.5; max-width: 880px; }}
/* Question prompt */
.zs-question {{
    font-family: 'Fraunces', Georgia, serif !important;
    font-size: 15px; font-weight: 500; font-style: italic;
    color: {INK}; margin: 16px 0 6px 0; line-height: 1.4;
}}
/* KPI cards */
.zs-kpi {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 5px; padding: 14px 16px; height: 100%; position: relative; overflow: hidden; }}
.zs-kpi-accent {{ position: absolute; top: 0; left: 0; width: 5px; height: 100%; background: {AMBER}; }}
.zs-kpi-label {{ font-size: 10.5px; letter-spacing: 0.14em; text-transform: uppercase; color: {SLATE}; font-weight: 600; margin-bottom: 6px; }}
.zs-kpi-value {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 30px; font-weight: 600; line-height: 1.05; color: {INK}; letter-spacing: -0.02em; }}
.zs-kpi-value .unit {{ font-size: 13px; color: {SLATE}; font-family: 'Manrope', sans-serif !important; font-weight: 500; margin-left: 4px; }}
.zs-kpi-foot {{ font-size: 11.5px; color: {INK_SOFT}; margin-top: 8px; line-height: 1.4; min-height: 1.4em; }}
/* Implication tiles */
.zs-obs {{ background: {CARD}; border: 1px solid {LINE}; border-left: 4px solid {AMBER}; border-radius: 5px; padding: 14px 16px; height: 100%; }}
.zs-obs-tag {{ font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; font-weight: 700; margin-bottom: 6px; }}
.zs-obs-text {{ font-size: 13px; color: {INK}; line-height: 1.55; }}
.zs-obs-text b {{ color: {INK}; font-weight: 700; }}
/* Verdict band */
.zs-verdict {{ color: #FFFFFF; padding: 14px 22px; border-radius: 5px; margin-top: 6px; display: flex; align-items: center; justify-content: space-between; }}
.zs-verdict .label {{ font-size: 10.5px; letter-spacing: 0.22em; text-transform: uppercase; font-weight: 700; opacity: 0.85; }}
.zs-verdict .text {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 18px; font-weight: 600; line-height: 1.25; margin-top: 4px; }}
.zs-verdict .number {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 38px; font-weight: 700; line-height: 1; letter-spacing: -0.02em; }}
.zs-verdict .number .small {{ font-size: 14px; font-weight: 500; opacity: 0.85; }}
/* Scorecard */
.zs-scorecard {{ background: {CARD}; border: 1px solid {LINE}; border-top: 5px solid {TREMFYA_C}; padding: 16px 18px; border-radius: 5px; }}
.zs-scorecard h3 {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 21px; font-weight: 600; margin: 0; color: {INK}; letter-spacing: -0.01em; }}
.zs-scorecard .strap {{ font-size: 10.5px; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 700; margin-bottom: 4px; }}
.zs-scorecard table {{ width: 100%; margin-top: 12px; border-collapse: collapse; }}
.zs-scorecard table td {{ padding: 7px 0; border-bottom: 1px dashed {LINE}; font-size: 12.5px; color: {INK}; }}
.zs-scorecard table tr:last-child td {{ border-bottom: none; }}
.zs-scorecard table td.label {{ color: {INK_SOFT}; }}
.zs-scorecard table td.value {{ text-align: right; font-weight: 600; color: {INK}; font-variant-numeric: tabular-nums; }}
/* Archetype card */
.zs-arch {{ background: {CARD}; border: 1px solid {LINE}; border-top: 5px solid {SLATE}; border-radius: 5px; padding: 14px 16px; height: 100%; }}
.zs-arch .name {{ font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: {SLATE}; font-weight: 700; margin-bottom: 4px; }}
.zs-arch .count {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 28px; font-weight: 600; color: {INK}; line-height: 1; }}
.zs-arch .count .u {{ font-size: 13px; color: {SLATE}; font-family: 'Manrope', sans-serif !important; margin-left: 4px; }}
.zs-arch .desc {{ font-size: 12px; color: {INK_SOFT}; margin-top: 6px; line-height: 1.4; }}
.zs-arch .mix {{ margin-top: 10px; padding-top: 10px; border-top: 1px dashed {LINE}; display: flex; gap: 14px; font-size: 12px; }}
/* Field cards & colour-grouped explorer */
.zs-fieldgroup {{ border: 1px solid {LINE}; border-radius: 6px; padding: 12px 14px; margin-bottom: 12px; background: {CARD}; }}
.zs-fieldgroup .gh {{ font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; font-weight: 700; margin-bottom: 8px; }}
.zs-field {{ border-radius: 4px; padding: 9px 11px; margin-bottom: 6px; }}
.zs-field:last-child {{ margin-bottom: 0; }}
.zs-field-label {{ font-size: 10px; letter-spacing: 0.10em; text-transform: uppercase; color: {SLATE}; font-weight: 600; margin-bottom: 2px; }}
.zs-field-value {{ font-size: 13px; color: {INK}; line-height: 1.45; font-weight: 500; }}
/* Tier ladder (methodology) */
.zs-rung {{ display: flex; align-items: center; gap: 14px; padding: 10px 14px; border-radius: 6px; margin-bottom: 7px; color: #FFFFFF; }}
.zs-rung .pts {{ font-family: 'Fraunces', serif !important; font-size: 24px; font-weight: 700; width: 56px; }}
.zs-rung .nm {{ font-weight: 700; font-size: 13px; letter-spacing: 0.04em; width: 110px; }}
.zs-rung .ds {{ font-size: 12.5px; opacity: 0.95; }}
/* Tabs */
div[data-baseweb="tab-list"] {{ gap: 0; border-bottom: 1px solid {LINE}; background: transparent; padding-left: 0; flex-wrap: wrap; }}
button[data-baseweb="tab"] {{
    font-family: 'Manrope', sans-serif !important; font-weight: 600 !important;
    font-size: 13px !important; letter-spacing: 0.02em !important;
    color: {SLATE} !important; background: transparent !important;
    padding: 12px 20px !important; border-radius: 0 !important;
    border-bottom: 2px solid transparent !important; margin-right: 2px;
}}
button[data-baseweb="tab"]:hover {{ color: {INK} !important; background: rgba(217, 119, 6, 0.04) !important; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color: {INK} !important; border-bottom-color: {AMBER} !important; }}
div[data-baseweb="tab-panel"] {{ padding-top: 16px; }}
/* Sidebar */
section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {NAVY} 0%, #0F172A 100%); }}
section[data-testid="stSidebar"] * {{ color: #E5E7EB !important; }}
section[data-testid="stSidebar"] label {{ color: #FCD34D !important; font-size: 10.5px !important; letter-spacing: 0.16em !important; text-transform: uppercase !important; font-weight: 700 !important; }}
.zs-side-brand {{ padding-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 18px; }}
.zs-side-brand .eyebrow {{ font-size: 10px; letter-spacing: 0.24em; text-transform: uppercase; color: {AMBER_SOFT} !important; font-weight: 700; margin-bottom: 4px; }}
.zs-side-brand .title {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 22px; font-weight: 600; color: #FFFFFF !important; line-height: 1.2; }}
.zs-side-brand .strap {{ font-size: 11.5px; color: rgba(229,231,235,0.65) !important; line-height: 1.4; margin-top: 6px; }}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{ background-color: rgba(255,255,255,0.06) !important; border-color: rgba(255,255,255,0.15) !important; color: #FFFFFF !important; }}
section[data-testid="stSidebar"] [data-baseweb="tag"] {{ background-color: {AMBER} !important; }}
section[data-testid="stSidebar"] [data-baseweb="tag"] span {{ color: {NAVY} !important; font-weight: 700; }}
section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] > div > div {{ background-color: {AMBER_SOFT} !important; }}
.zs-side-footer {{ margin-top: 22px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 11px; color: rgba(229,231,235,0.55) !important; line-height: 1.5; }}
/* Dataframe / expander */
[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 3px; background: {CARD}; }}
.streamlit-expanderHeader {{ font-family: 'Manrope', sans-serif !important; font-weight: 600 !important; color: {INK} !important; background: {CARD} !important; border: 1px solid {LINE} !important; border-radius: 3px !important; }}
.js-plotly-plot .plotly .modebar {{ display: none !important; }}
.zs-footer {{ margin-top: 56px; padding-top: 16px; border-top: 1px solid {LINE}; font-size: 11px; letter-spacing: 0.10em; text-transform: uppercase; color: {SLATE}; display: flex; justify-content: space-between; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================================
#  DATA LOADING  (best-results file; no uploader)
# ============================================================================
DATA_CANDIDATES = [
    "result__15_.xlsx", "result_15.xlsx", "result.xlsx",
    "data/result__15_.xlsx", "./result__15_.xlsx",
    "/mnt/user-data/uploads/result__15_.xlsx",
    "PA_Gold_Standard_Dataset_v5.xlsx",
]


def find_local_file() -> Optional[str]:
    for p in DATA_CANDIDATES:
        if Path(p).exists():
            return p
    return None


@st.cache_data(show_spinner=False)
def load_results(path: str) -> pd.DataFrame:
    # Read the first sheet that contains an "Access Score" column.
    xls = pd.ExcelFile(path, engine="openpyxl")
    for sh in xls.sheet_names:
        d = pd.read_excel(xls, sheet_name=sh)
        if any(str(c).strip().lower() == "access score" for c in d.columns):
            return d
    return pd.read_excel(xls, sheet_name=xls.sheet_names[0])


# ============================================================================
#  DATA PREPARATION
# ============================================================================
def _parse_duration(v):
    if pd.isna(v):
        return np.nan
    s = str(v).strip()
    if s == "" or s.lower() in {"unspecified", "n/a", "na", "none", "nan"}:
        return np.nan
    m = re.match(r"^\s*(\d+(?:\.\d+)?)", s)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return np.nan
    return np.nan


def _yes_no(v):
    if pd.isna(v):
        return "Not specified"
    s = str(v).strip().lower()
    if s in {"yes", "y", "true"}:
        return "Yes"
    if s in {"no", "n", "false"}:
        return "No"
    return "Not specified"


def _has_text(v) -> bool:
    if pd.isna(v):
        return False
    s = str(v).strip()
    if s == "" or s.lower() in {"no", "none", "n/a", "na", "unspecified", "not specified", "nan"}:
        return False
    return len(s) > 3


def access_tier(score) -> str:
    """Map a 0-100 access score onto the FDA-anchored 5-band ladder."""
    if pd.isna(score):
        return "Unscored"
    s = float(score)
    if s < 12.5:
        return "No access"
    if s < 37.5:
        return "Restricted"
    if s < 62.5:
        return "Parity"
    if s < 87.5:
        return "Preferred"
    return "Open"


@st.cache_data(show_spinner=False)
def prepare(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    str_cols = [c for c in df.columns
                if df[c].dtype == object or pd.api.types.is_string_dtype(df[c])]
    for c in str_cols:
        df[c] = df[c].astype(str).str.strip().replace(
            {"nan": np.nan, "NaN": np.nan, "None": np.nan, "": np.nan}
        )
    df["Brand"] = df["Brand"].fillna("Unknown").astype(str).str.upper()
    df["Access Score"] = pd.to_numeric(df["Access Score"], errors="coerce")
    df["Access Tier"] = df["Access Score"].apply(access_tier)
    df["Initial Auth (months)"] = df["Initial Authorization Duration(in-months)"].apply(_parse_duration)
    df["Reauth (months)"] = df["Reauthorization Duration(in-months)"].apply(_parse_duration)
    df["TB Test"] = df["TB Test required"].apply(_yes_no)
    df["Phototherapy Step"] = df["Step through-Phototherapy"].apply(_yes_no)
    df["Reauthorization"] = df["Reauthorization Required"].apply(
        lambda v: "Required" if str(v).strip().lower() == "yes" else "Not specified"
    )

    def qlim_flag(v):
        if pd.isna(v):
            return "Not specified"
        s = str(v).strip().lower()
        if s == "no":
            return "No"
        if s == "yes" or len(str(v).strip()) > 6:
            return "Yes"
        return "Not specified"

    df["Quantity Limit"] = df["Quantity Limits"].apply(qlim_flag)
    df["Step Therapy"] = df["Step Therapy Requirements Documented in Policy"].apply(
        lambda v: "Required" if _has_text(v) else "Not documented"
    )
    df["Brand Steps"] = pd.to_numeric(df["Number of Steps through Brands"], errors="coerce")
    df["Generic Steps"] = pd.to_numeric(df["Number of Steps through Generic"], errors="coerce")
    df["Total Steps"] = df[["Brand Steps", "Generic Steps"]].sum(axis=1, min_count=1)
    df["Specialist Required"] = df["Specialist Types"].apply(
        lambda v: "Required" if _has_text(v) else "Not specified"
    )
    df["Specialist Detail"] = df["Specialist Types"].fillna("—")
    df["Age Criterion"] = df["Age"].fillna("Not specified")
    df["Policy ID"] = df["Filename"].astype(str).str.replace(".pdf", "", regex=False)
    uniq = df["Policy ID"].drop_duplicates().reset_index(drop=True)
    rank_map = {pid: i + 1 for i, pid in enumerate(uniq)}
    df["Policy #"] = df["Policy ID"].map(rank_map).apply(lambda i: f"Policy {i:02d}")
    return df


# ============================================================================
#  ANALYSIS HELPERS
# ============================================================================
RESTRICTION_DEFS = [
    ("Step Therapy",        "Required", "Step therapy required"),
    ("TB Test",             "Yes",      "TB test required"),
    ("Quantity Limit",      "Yes",      "Quantity limit imposed"),
    ("Specialist Required", "Required", "Specialist prescriber required"),
    ("Phototherapy Step",   "Yes",      "Phototherapy step required"),
    ("Reauthorization",     "Required", "Reauthorization required"),
]


def restriction_count(df: pd.DataFrame) -> pd.Series:
    s = pd.Series(0, index=df.index)
    for col, val, _ in RESTRICTION_DEFS:
        s = s + (df[col] == val).astype(int)
    return s


def restriction_share(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(df)
    if n == 0:
        return pd.DataFrame(columns=["Restriction", "Count", "Share"])
    for col, val, label in RESTRICTION_DEFS:
        c = int((df[col] == val).sum())
        rows.append({"Restriction": label, "Count": c, "Share": c / n})
    return pd.DataFrame(rows)


def restriction_by_brand(df: pd.DataFrame, brands: List[str]) -> pd.DataFrame:
    rows = []
    for b in brands:
        sub = df[df["Brand"] == b]
        n = len(sub)
        for col, val, label in RESTRICTION_DEFS:
            share = (sub[col] == val).mean() if n else 0
            rows.append({"Brand": b, "Restriction": label, "Share": share,
                         "Count": int((sub[col] == val).sum()), "N": n})
    return pd.DataFrame(rows)


def archetype_label(count):
    if pd.isna(count):
        return "Unknown"
    if count <= 2:
        return "Open access"
    if count <= 4:
        return "Standard access"
    return "Tight access"


def simulate_access_score(covered, b_steps, g_steps, photo, specialist,
                          qty_limit, reauth_months, init_months, step_known=True):
    """Replica of the production binding-constraint scorer — used by the live
    simulator in the Methodology tab. Returns (score, tier, rationale list)."""
    why = []
    if not covered:
        return 0, "No access", ["Coverage gate: not covered for PsO → 0"]
    # Stage 2 — step-therapy anchor (biologic step-through dominates)
    if b_steps >= 2:
        anchor = 25; why.append(f"Anchor: {b_steps} biologic steps (beyond FDA label) → 25")
    elif b_steps == 1:
        anchor = 25; why.append("Anchor: 1 biologic step (beyond FDA label) → 25 (hard floor)")
    elif g_steps >= 1 or photo:
        anchor = 50; why.append(f"Anchor: label-consistent step (generic={g_steps}{', photo' if photo else ''}) → 50 parity")
    elif step_known:
        anchor = 75; why.append("Anchor: criteria reviewed, no step therapy → 75 (provisional)")
    else:
        anchor = 50; why.append("Anchor: step therapy unknown → 50 (unknown ≠ open)")
    # Stage 3 — secondary burden
    burden = 0; notes = []
    if specialist:
        burden += 1; notes.append("specialist")
    if qty_limit:
        burden += 1; notes.append("quantity-limit")
    if reauth_months and reauth_months <= 6:
        burden += 1; notes.append("short reauth ≤6mo")
    if init_months and init_months < 3:
        burden += 1; notes.append("short initial <3mo")
    if g_steps >= 2:
        burden += (g_steps - 1); notes.append(f"{g_steps} conventional steps")
    if photo and (b_steps > 0 or g_steps > 0):
        burden += 1; notes.append("phototherapy as extra step")
    why.append(f"Burden = {burden} ({', '.join(notes) if notes else 'none'})")
    # Final adjustment
    if anchor == 25:
        score = 25
    elif anchor == 50:
        score = 25 if burden >= 2 else 50
    elif anchor == 75:
        score = 100 if burden == 0 else (50 if burden >= 2 else 75)
    else:
        score = anchor
    why.append(f"→ Final score {score}")
    return score, access_tier(score), why


def kpi_card(col, label, value, foot="", accent=AMBER):
    col.markdown(
        f"""
<div class="zs-kpi">
  <div class="zs-kpi-accent" style="background:{accent};"></div>
  <div class="zs-kpi-label">{label}</div>
  <div class="zs-kpi-value">{value}</div>
  <div class="zs-kpi-foot">{foot}</div>
</div>""",
        unsafe_allow_html=True,
    )


def implication_tile(col, tag, html, accent=AMBER):
    col.markdown(
        f"""
<div class="zs-obs" style="border-left-color:{accent};">
  <div class="zs-obs-tag" style="color:{accent};">{tag}</div>
  <div class="zs-obs-text">{html}</div>
</div>""",
        unsafe_allow_html=True,
    )


def section_h2(title, deck="", accent=AMBER):
    tint = accent
    st.markdown(
        f"""
<div class="zs-sec" style="border-left-color:{tint};
     background: linear-gradient(90deg, {tint}14 0%, {tint}00 60%);">
  <h2>{title}</h2>
  {f'<div class="deck">{deck}</div>' if deck else ''}
</div>""",
        unsafe_allow_html=True,
    )


def question(text):
    st.markdown(f'<div class="zs-question">{text}</div>', unsafe_allow_html=True)


# ============================================================================
#  INGESTION
# ============================================================================
st.sidebar.markdown(
    """
<div class="zs-side-brand">
  <div class="eyebrow">ZS · Market Access</div>
  <div class="title">PsO Policy Lens</div>
  <div class="strap">Prior-authorization intelligence across the PsO biologic basket.</div>
</div>""",
    unsafe_allow_html=True,
)

local_path = find_local_file()
if local_path is None:
    st.error(
        "Results workbook not found. Place **result__15_.xlsx** next to this app "
        "(same folder) and reload. No upload step is required."
    )
    st.stop()

try:
    df_raw = load_results(local_path)
except ImportError:
    st.error("Missing dependency `openpyxl`. Add `openpyxl>=3.1` to requirements.txt and redeploy.")
    st.stop()
except Exception as e:
    st.error(f"Could not read the results workbook. Details: `{e}`")
    st.stop()

df_all = prepare(df_raw)
ALL_BRANDS = sorted(df_all["Brand"].unique().tolist(),
                    key=lambda b: (b not in FOCUS_BRANDS, b))  # focus brands first

# ============================================================================
#  SIDEBAR FILTERS  (brand filter drives every tab)
# ============================================================================
st.sidebar.markdown("**Brand filter**")
default_brands = [b for b in FOCUS_BRANDS if b in ALL_BRANDS] or ALL_BRANDS[:1]
selected_brands = st.sidebar.multiselect(
    "Brand filter",
    options=ALL_BRANDS,
    default=default_brands,
    label_visibility="collapsed",
    help="Pick any brands in the corpus. Headline insights focus on TREMFYA vs STELARA; "
         "all charts, the parameter explorer and the policy explorer respond to this filter.",
)
if not selected_brands:
    selected_brands = default_brands

st.sidebar.markdown("**Access score range**")
score_lo = int(np.nanmin(df_all["Access Score"])) if df_all["Access Score"].notna().any() else 0
score_hi = int(np.nanmax(df_all["Access Score"])) if df_all["Access Score"].notna().any() else 100
score_range = st.sidebar.slider(
    "Access score range", min_value=0, max_value=100,
    value=(0, 100), step=25, label_visibility="collapsed",
)

st.sidebar.markdown("**Filter by access tier**")
tier_options = [t for t in ACCESS_TIER_ORDER if t in df_all["Access Tier"].unique()]
selected_tiers = st.sidebar.multiselect(
    "Filter by access tier", options=tier_options, default=tier_options,
    label_visibility="collapsed",
)

# Filtered frames
base_mask = (df_all["Access Score"].between(score_range[0], score_range[1])
             & df_all["Access Tier"].isin(selected_tiers))
df = df_all[base_mask & df_all["Brand"].isin(selected_brands)].copy()          # brand-filtered
focus_present = [b for b in FOCUS_BRANDS if b in df_all["Brand"].unique()]
df_focus = df_all[base_mask & df_all["Brand"].isin(focus_present)].copy()       # TREMFYA/STELARA

st.sidebar.markdown(
    f"""
<div class="zs-side-footer">
Corpus: <b>{df_all['Policy ID'].nunique()}</b> payer policies · <b>{len(df_all)}</b> brand-policy
observations across <b>{len(ALL_BRANDS)}</b> PsO brands.<br><br>
Active filter: <b>{len(selected_brands)}</b> brand(s) · <b>{len(df)}</b> observations in view.
</div>""",
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("No rows match the current filters. Loosen them from the sidebar to continue.")
    st.stop()

# ============================================================================
#  MASTHEAD
# ============================================================================
st.markdown(
    f"""
<div class="zs-masthead">
  <div class="zs-masthead-left">
    <div class="eyebrow">Plaque Psoriasis · Payer Access Intelligence</div>
    <h1>How payer policies shape access across the PsO biologic basket</h1>
    <div class="deck">A consulting view of prior-authorization signals from {df_all['Policy ID'].nunique()} payer
    policies — quantifying where access opens, where it tightens, and the payer behaviours driving the difference.
    Headline comparison focuses on TREMFYA vs STELARA; the brand filter unlocks the full basket.</div>
  </div>
  <div class="zs-masthead-right">
    Focus pair<span class="zs-pill-tremfya">TREMFYA</span><span class="zs-pill-stelara">STELARA</span>
  </div>
</div>""",
    unsafe_allow_html=True,
)

# ============================================================================
#  TABS
# ============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Executive Summary",
    "Parameter Analysis",
    "Brand Comparison",
    "Access Drivers",
    "Methodology & Insights",
    "Policy Explorer",
])

# ----------------------------------------------------------------------------
#  TAB 1 — EXECUTIVE SUMMARY
# ----------------------------------------------------------------------------
with tab1:
    tdf = df_focus[df_focus["Brand"] == "TREMFYA"]
    sdf = df_focus[df_focus["Brand"] == "STELARA"]
    t_mean = tdf["Access Score"].mean() if len(tdf) else np.nan
    s_mean = sdf["Access Score"].mean() if len(sdf) else np.nan
    diff = t_mean - s_mean if not (np.isnan(t_mean) or np.isnan(s_mean)) else np.nan

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Policies analysed", f"{df['Policy ID'].nunique()}",
             foot=f"{len(df)} observations · {len(selected_brands)} brand(s) in view", accent=SLATE)
    kpi_card(c2, "TREMFYA · mean access", f"{t_mean:.1f}" if not np.isnan(t_mean) else "—",
             foot=f"{len(tdf)} policies covering TREMFYA", accent=TREMFYA_C)
    kpi_card(c3, "STELARA · mean access", f"{s_mean:.1f}" if not np.isnan(s_mean) else "—",
             foot=f"{len(sdf)} policies covering STELARA", accent=STELARA_C)
    if not np.isnan(diff):
        leader = "TREMFYA" if diff > 0 else ("STELARA" if diff < 0 else "Parity")
        sign = "+" if diff > 0 else ""
        acc = TREMFYA_C if diff > 0 else (STELARA_C if diff < 0 else SLATE)
        kpi_card(c4, "Access differential", f"{sign}{diff:.1f}<span class='unit'>pts</span>",
                 foot=f"{leader} advantage on the 0–100 access scale", accent=acc)
    else:
        kpi_card(c4, "Access differential", "—", "", accent=SLATE)

    if not np.isnan(diff):
        if abs(diff) < 1:
            grad = f"linear-gradient(90deg,{SLATE} 0%,#94A3B8 100%)"
            lbl, txt, num = "Access verdict", "TREMFYA and STELARA face broadly similar payer access conditions across the corpus.", "≈ Parity"
        elif diff > 0:
            grad = f"linear-gradient(90deg,{TREMFYA_C} 0%,{TREMFYA_LIGHT} 100%)"
            lbl, txt, num = "Access leader · TREMFYA", "TREMFYA holds a measurable corpus-mean access advantage over STELARA.", f"+{diff:.1f}<span class='small'> pts</span>"
        else:
            grad = f"linear-gradient(90deg,{STELARA_C} 0%,{STELARA_LIGHT} 100%)"
            lbl, txt, num = "Access leader · STELARA", "STELARA holds a measurable corpus-mean access advantage over TREMFYA.", f"+{abs(diff):.1f}<span class='small'> pts</span>"
        st.markdown(
            f"""<div class="zs-verdict" style="background:{grad};">
  <div><div class="label">{lbl}</div><div class="text">{txt}</div></div>
  <div class="number">{num}</div></div>""",
            unsafe_allow_html=True,
        )

    section_h2("Access Overview",
               "Distribution of access scores for the brands in view. Position of the mass tells "
               "the story — clustering near 25 signals payer-imposed step-edits beyond the FDA label.",
               accent=SEC["exec"])
    question("Where does each selected brand sit on the 0–100 access spectrum?")
    fig_dist = go.Figure()
    plot_brands = selected_brands if len(selected_brands) <= 6 else (focus_present or selected_brands[:6])
    for i, b in enumerate(plot_brands):
        bsub = df[df["Brand"] == b].dropna(subset=["Access Score"])
        if len(bsub) == 0:
            continue
        fig_dist.add_trace(go.Violin(
            x=bsub["Access Score"], y=[b] * len(bsub), name=b, orientation="h",
            side="positive", line_color=brand_color(b, i), fillcolor=brand_color(b, i),
            opacity=0.55, box_visible=True, meanline_visible=True, points="all",
            pointpos=-0.6, jitter=0.25,
            marker=dict(color=brand_color(b, i), size=6, opacity=0.85,
                        line=dict(color="#FFFFFF", width=0.5)),
            hoveron="points", hovertemplate=f"<b>{b}</b><br>Score: %{{x}}<extra></extra>",
            scalemode="count", spanmode="hard",
        ))
    apply_layout(fig_dist, height=max(300, 95 * len(plot_brands) + 80),
                 xaxis=dict(range=[-5, 105], title="Access Score (0 = no access · 50 = FDA parity · 100 = open)",
                            title_font=dict(size=12, color=INK_SOFT)),
                 yaxis=dict(title="", showgrid=False), showlegend=False, violinmode="group")
    st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar": False})

    section_h2("Consulting Implications", accent=SEC["exec"])
    rs = restriction_share(df_focus).sort_values("Share", ascending=False)
    top_restr = rs.iloc[0] if len(rs) else None
    t_range = (tdf["Access Score"].max() - tdf["Access Score"].min()) if len(tdf) else 0
    s_range = (sdf["Access Score"].max() - sdf["Access Score"].min()) if len(sdf) else 0
    ic = st.columns(3)
    if not np.isnan(diff):
        leader = "TREMFYA" if diff > 0 else "STELARA"
        acc = TREMFYA_C if diff > 0 else STELARA_C
        implication_tile(ic[0], "Brand positioning",
                         f"<b>{leader} carries a {abs(diff):.1f}-point access edge</b> on a corpus-mean basis. "
                         f"The gap is directionally consistent and shapes relative pull-through potential — "
                         f"the trailing brand should prioritise formulary-access wins at its weakest accounts.",
                         accent=acc)
    implication_tile(ic[1], "Payer mix vs brand choice",
                     f"Within-brand access swings by up to <b>{max(t_range, s_range):.0f} points</b> from the "
                     f"tightest to the most open policy. <b>Payer selection moves access more than brand selection</b> — "
                     f"field-team targeting should be account-led, not brand-led.",
                     accent=SEC["exec"])
    if top_restr is not None:
        implication_tile(ic[2], "Dominant UM lever",
                         f"<b>{top_restr['Restriction']}</b> is the most prevalent utilization-management lever, "
                         f"applied in <b>{top_restr['Share']*100:.0f}%</b> of policies. Concentrating payer "
                         f"negotiation on this single lever offers the largest addressable-population upside.",
                         accent=SEC["exec"])

# ----------------------------------------------------------------------------
#  TAB 2 — PARAMETER ANALYSIS  (parameter-led; all brands selectable)
# ----------------------------------------------------------------------------
with tab2:
    section_h2("Parameter Analysis",
               "Lead with the parameter, not the brand. Pick any extracted PA parameter and see how it is "
               "distributed across the corpus and how it differs across the brands in view.",
               accent=SEC["param"])

    PARAM_GROUPS = {
        "Eligibility & screening": [
            ("Age Criterion", "categorical", "Age criterion"),
            ("TB Test", "yesno", "TB test required"),
            ("Specialist Required", "yesno", "Specialist prescriber required"),
        ],
        "Step therapy & pre-treatment": [
            ("Step Therapy", "yesno", "Step therapy documented"),
            ("Brand Steps", "numeric", "Number of brand/biologic steps"),
            ("Generic Steps", "numeric", "Number of generic/oral steps"),
            ("Phototherapy Step", "yesno", "Phototherapy step required"),
        ],
        "Utilization management": [
            ("Quantity Limit", "yesno", "Quantity limit imposed"),
            ("Initial Auth (months)", "numeric", "Initial authorization duration"),
            ("Reauth (months)", "numeric", "Reauthorization duration"),
        ],
    }
    PARAM_INSIGHTS = {
        "Age Criterion": "Age thresholds size the eligible population. 'FDA approved age' defaults to the label; explicit thresholds (≥6, ≥18) carve out cohorts and matter for pediatric positioning.",
        "TB Test": "TB screening is the clinical norm before any biologic — it is a low-friction gate, not a true access barrier, and should not be over-weighted in access scoring.",
        "Specialist Required": "Dermatologist-only prescribing narrows the writer base and adds referral friction; 'or in consultation with' language softens the constraint materially.",
        "Step Therapy": "Step therapy is the single most material access lever and is required in the majority of policies — the primary battleground for formulary access teams.",
        "Brand Steps": "Biologic step-through is the strongest predictor of delay and abandonment. Each required prior biologic is a payer-imposed hurdle beyond the FDA label.",
        "Generic Steps": "Conventional/oral systemics (methotrexate, cyclosporine, acitretin) sit earlier in the ladder and are broadly label-consistent — they depress access far less than biologic step-edits.",
        "Phototherapy Step": "Mandatory phototherapy is uncommon but consequential — it requires clinic-administered UVB/PUVA access that many patients cannot reach.",
        "Quantity Limit": "Quantity limits cap units per fill; below-label limits restrict dose optimisation and are a genuine access constraint.",
        "Initial Auth (months)": "Short initial windows (≤6 months) raise early-discontinuation risk and administrative load on the practice.",
        "Reauth (months)": "Reauthorization cadence sets ongoing administrative burden — 12 months is the prevailing, lower-friction standard.",
    }

    pc1, pc2 = st.columns([1, 2])
    with pc1:
        category = st.selectbox("Parameter category", options=list(PARAM_GROUPS.keys()), index=1)
    with pc2:
        opts = [(label, col, kind) for col, kind, label in PARAM_GROUPS[category]]
        chosen_label = st.selectbox("Parameter", options=[lbl for lbl, _, _ in opts], index=0)
    sel_col, sel_kind = next((c, k) for lbl, c, k in opts if lbl == chosen_label)

    left, right = st.columns(2)
    with left:
        question(f"How does '{chosen_label}' distribute across policies in view?")
        if sel_kind == "numeric":
            d = df[sel_col].dropna()
            if len(d) == 0:
                st.info("No data for this parameter in the current filter.")
            else:
                vc = d.astype(int).value_counts().sort_index()
                fig_p = go.Figure(go.Bar(
                    x=vc.index, y=vc.values,
                    marker=dict(color=SEC["param"], line=dict(color="#FFFFFF", width=0.5)),
                    hovertemplate=f"<b>{chosen_label}</b>: %{{x}}<br>%{{y}} policies<extra></extra>"))
                apply_layout(fig_p, height=300,
                             xaxis=dict(title=chosen_label, title_font=dict(size=12, color=INK_SOFT)),
                             yaxis=dict(title="Policies", title_font=dict(size=12, color=INK_SOFT)),
                             showlegend=False, bargap=0.22)
                st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})
        else:
            vc = df[sel_col].fillna("Not specified").value_counts()
            fig_p = go.Figure(go.Bar(
                y=vc.index.tolist(), x=vc.values, orientation="h",
                marker=dict(color=SEC["param"], line=dict(color="#FFFFFF", width=0.5)),
                hovertemplate=f"<b>{chosen_label}</b>: %{{y}}<br>%{{x}} policies<extra></extra>"))
            apply_layout(fig_p, height=max(220, 46 * len(vc) + 80),
                         xaxis=dict(title="Policies", title_font=dict(size=12, color=INK_SOFT)),
                         yaxis=dict(title=""), showlegend=False)
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})
    with right:
        question(f"How does '{chosen_label}' differ by brand?")
        if sel_kind == "numeric":
            sub = df.dropna(subset=[sel_col])
            if len(sub) == 0:
                st.info("No data for the brands in view.")
            else:
                fig_b = go.Figure()
                for i, b in enumerate(selected_brands):
                    bsub = sub[sub["Brand"] == b]
                    if len(bsub):
                        fig_b.add_trace(go.Box(
                            x=bsub[sel_col], name=b, marker=dict(color=brand_color(b, i)),
                            line=dict(color=brand_color(b, i)), fillcolor=brand_color(b, i),
                            opacity=0.55, boxmean=True, orientation="h",
                            hovertemplate=f"<b>{b}</b><br>%{{x}}<extra></extra>"))
                apply_layout(fig_b, height=max(280, 60 * len(selected_brands) + 80),
                             xaxis=dict(title=chosen_label, title_font=dict(size=12, color=INK_SOFT)),
                             yaxis=dict(title=""),
                             legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
                st.plotly_chart(fig_b, use_container_width=True, config={"displayModeBar": False})
        else:
            sub = df.copy()
            sub[sel_col] = sub[sel_col].fillna("Not specified")
            cross = sub.groupby(["Brand", sel_col]).size().reset_index(name="n")
            totals = sub.groupby("Brand").size()
            cross["pct"] = cross.apply(lambda r: r["n"] / totals[r["Brand"]] * 100, axis=1)
            fig_b = go.Figure()
            for i, b in enumerate(selected_brands):
                bsub = cross[cross["Brand"] == b]
                fig_b.add_trace(go.Bar(
                    x=bsub[sel_col], y=bsub["pct"], name=b,
                    marker=dict(color=brand_color(b, i), line=dict(color="#FFFFFF", width=0.5)),
                    hovertemplate=f"<b>{b}</b><br>%{{x}}: %{{y:.0f}}%%<extra></extra>"))
            apply_layout(fig_b, height=300, barmode="group",
                         xaxis=dict(title=chosen_label, title_font=dict(size=12, color=INK_SOFT)),
                         yaxis=dict(title="% of brand's policies", ticksuffix="%",
                                    title_font=dict(size=12, color=INK_SOFT)),
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
            st.plotly_chart(fig_b, use_container_width=True, config={"displayModeBar": False})

    interp = PARAM_INSIGHTS.get(sel_col, "")
    if interp:
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
        implication_tile(st.container(), "Market-access read", interp, accent=SEC["param"])

# ----------------------------------------------------------------------------
#  TAB 3 — BRAND COMPARISON
# ----------------------------------------------------------------------------
with tab3:
    section_h2("Brand Comparison",
               "Scorecards and access-tier composition for the brands in view. The paired analysis below "
               "always compares the TREMFYA vs STELARA focus pair head-to-head.",
               accent=SEC["compare"])

    cards = selected_brands[:4]
    sc_cols = st.columns(len(cards))
    for i, (col, brand) in enumerate(zip(sc_cols, cards)):
        sub = df[df["Brand"] == brand]
        if len(sub) == 0:
            with col:
                st.info(f"No {brand} policies in view.")
            continue
        metrics = {
            "Policies covered": len(sub),
            "Mean access score": f"{sub['Access Score'].mean():.1f}",
            "Median access score": f"{sub['Access Score'].median():.0f}",
            "Score range": f"{sub['Access Score'].min():.0f}–{sub['Access Score'].max():.0f}",
            "Step therapy required": f"{(sub['Step Therapy']=='Required').mean()*100:.0f}%",
            "Biologic step (any)": f"{(sub['Brand Steps']>=1).mean()*100:.0f}%",
            "TB test required": f"{(sub['TB Test']=='Yes').mean()*100:.0f}%",
            "Quantity limit imposed": f"{(sub['Quantity Limit']=='Yes').mean()*100:.0f}%",
            "Specialist required": f"{(sub['Specialist Required']=='Required').mean()*100:.0f}%",
            "Median reauthorization": (f"{sub['Reauth (months)'].median():.0f} months"
                                       if sub["Reauth (months)"].notna().any() else "—"),
        }
        rows_html = "".join(
            f'<tr><td class="label">{k}</td><td class="value">{v}</td></tr>' for k, v in metrics.items())
        acc = brand_color(brand, i)
        with col:
            st.markdown(
                f"""<div class="zs-scorecard" style="border-top-color:{acc};">
  <div class="strap" style="color:{acc};">Brand scorecard</div>
  <h3>{brand}</h3><table>{rows_html}</table></div>""",
                unsafe_allow_html=True,
            )

    section_h2("Access Tier Composition",
               "Share of each brand's policies in each FDA-anchored access tier.", accent=SEC["compare"])
    question("Where does each brand's policy mass concentrate on the restriction spectrum?")
    tier_data = []
    for b in selected_brands:
        sub = df[df["Brand"] == b]
        n = len(sub)
        if n == 0:
            continue
        vc = sub["Access Tier"].value_counts(normalize=True)
        for t in ACCESS_TIER_ORDER:
            tier_data.append({"Brand": b, "Tier": t, "Share": vc.get(t, 0.0)})
    tier_df = pd.DataFrame(tier_data)
    if not tier_df.empty:
        fig_tier = go.Figure()
        for t in ACCESS_TIER_ORDER:
            sub = tier_df[tier_df["Tier"] == t]
            fig_tier.add_trace(go.Bar(
                y=sub["Brand"], x=sub["Share"] * 100, orientation="h", name=t,
                marker=dict(color=ACCESS_TIER_COLOR[t], line=dict(color="#FFFFFF", width=1)),
                hovertemplate=f"<b>{t}</b><br>%{{y}}: %{{x:.0f}}%% of policies<extra></extra>"))
        apply_layout(fig_tier, barmode="stack", height=max(220, 52 * len(selected_brands) + 80),
                     xaxis=dict(range=[0, 100], ticksuffix="%", title="Share of policies",
                                title_font=dict(size=12, color=INK_SOFT)),
                     yaxis=dict(title=""),
                     legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        st.plotly_chart(fig_tier, use_container_width=True, config={"displayModeBar": False})

    # Paired TREMFYA vs STELARA
    section_h2("Paired Policy Analysis — TREMFYA vs STELARA",
               "Within the same payer policy, which brand receives the more favourable treatment?",
               accent=SEC["compare"])
    paired = df_all[df_all["Brand"].isin(FOCUS_BRANDS)].copy()
    grp = paired.groupby("Policy ID")["Brand"].nunique()
    paired_ids = grp[grp == 2].index.tolist()
    pf = paired[paired["Policy ID"].isin(paired_ids)]
    pf = pf[pf["Access Score"].between(score_range[0], score_range[1]) & pf["Access Tier"].isin(selected_tiers)]
    pivot = pf.pivot_table(index=["Policy ID", "Policy #"], columns="Brand",
                           values="Access Score").reset_index()
    if {"TREMFYA", "STELARA"}.issubset(pivot.columns):
        pivot = pivot.dropna(subset=["TREMFYA", "STELARA"])
        pivot["delta"] = pivot["TREMFYA"] - pivot["STELARA"]
        pivot = pivot.sort_values("delta")
    else:
        pivot = pd.DataFrame()
    if len(pivot) >= 2:
        question(f"In the {len(pivot)} policies that cover both brands, who scores higher?")
        fig_pair = go.Figure()
        for _, r in pivot.iterrows():
            fig_pair.add_trace(go.Scatter(x=[r["STELARA"], r["TREMFYA"]],
                                          y=[r["Policy #"], r["Policy #"]], mode="lines",
                                          line=dict(color=LINE, width=2), showlegend=False, hoverinfo="skip"))
        fig_pair.add_trace(go.Scatter(x=pivot["STELARA"], y=pivot["Policy #"], mode="markers", name="STELARA",
                                      marker=dict(color=STELARA_C, size=13, line=dict(color="#FFFFFF", width=1.5)),
                                      hovertemplate="<b>STELARA</b><br>%{y}<br>Score: %{x:.0f}<extra></extra>"))
        fig_pair.add_trace(go.Scatter(x=pivot["TREMFYA"], y=pivot["Policy #"], mode="markers", name="TREMFYA",
                                      marker=dict(color=TREMFYA_C, size=13, line=dict(color="#FFFFFF", width=1.5)),
                                      hovertemplate="<b>TREMFYA</b><br>%{y}<br>Score: %{x:.0f}<extra></extra>"))
        apply_layout(fig_pair, height=max(280, 30 * len(pivot) + 80),
                     xaxis=dict(range=[-5, 105], title="Access Score", title_font=dict(size=12, color=INK_SOFT)),
                     yaxis=dict(title=""), legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        st.plotly_chart(fig_pair, use_container_width=True, config={"displayModeBar": False})
        t_h = int((pivot["delta"] > 0).sum()); s_h = int((pivot["delta"] < 0).sum())
        avg_d = pivot["delta"].mean()
        cc = st.columns(3)
        implication_tile(cc[0], "TREMFYA wins", f"<b>{t_h} of {len(pivot)}</b> shared policies score TREMFYA above STELARA.", accent=TREMFYA_C)
        implication_tile(cc[1], "STELARA wins", f"<b>{s_h} of {len(pivot)}</b> shared policies score STELARA above TREMFYA.", accent=STELARA_C)
        implication_tile(cc[2], "Within-policy gap", f"Average within-policy advantage for TREMFYA: <b>{avg_d:+.1f}</b> points.", accent=SEC["compare"])
    else:
        st.info("Insufficient policies covering both TREMFYA and STELARA for a paired comparison under the current filters.")

# ----------------------------------------------------------------------------
#  TAB 4 — ACCESS DRIVERS
# ----------------------------------------------------------------------------
with tab4:
    section_h2("Restriction Patterns",
               "The prior-authorization levers payers apply most often across the brands in view.",
               accent=SEC["drivers"])
    question("Which restrictions are most prevalent, and where do the brands diverge?")
    rb = restriction_by_brand(df, selected_brands)
    overall = restriction_share(df).sort_values("Share", ascending=True)
    order = overall["Restriction"].tolist()
    fig_r = go.Figure()
    for i, b in enumerate(selected_brands):
        sub = rb[rb["Brand"] == b].set_index("Restriction").reindex(order).reset_index()
        fig_r.add_trace(go.Bar(
            y=sub["Restriction"], x=sub["Share"] * 100, orientation="h", name=b,
            marker=dict(color=brand_color(b, i), line=dict(color="#FFFFFF", width=0.5)),
            hovertemplate=f"<b>{b}</b><br>%{{y}}<br>%{{x:.0f}}%% of policies<extra></extra>"))
    apply_layout(fig_r, height=max(340, 52 * len(order) + 60), barmode="group",
                 xaxis=dict(range=[0, 105], ticksuffix="%", title="Share of policies imposing the restriction",
                            title_font=dict(size=12, color=INK_SOFT)),
                 yaxis=dict(title=""), legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), bargap=0.18)
    st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})

    section_h2("Step-Therapy Intensity",
               "Step therapy is the single most material access barrier — how many hurdles must a patient clear?",
               accent=SEC["drivers"])
    question("How many therapies must a patient try before accessing each brand?")
    step_rows = []
    for b in selected_brands:
        sub = df[df["Brand"] == b].dropna(subset=["Total Steps"])
        for _, r in sub.iterrows():
            step_rows.append({"Brand": b, "Steps": int(r["Total Steps"])})
    step_df = pd.DataFrame(step_rows)
    if not step_df.empty:
        all_steps = list(range(0, int(step_df["Steps"].max()) + 1))
        fig_steps = go.Figure()
        for i, b in enumerate(selected_brands):
            sb = step_df[step_df["Brand"] == b]
            vc = sb["Steps"].value_counts().reindex(all_steps, fill_value=0)
            fig_steps.add_trace(go.Bar(x=vc.index, y=vc.values, name=b,
                                       marker=dict(color=brand_color(b, i), line=dict(color="#FFFFFF", width=0.5)),
                                       hovertemplate=f"<b>{b}</b><br>%{{x}} steps · %{{y}} policies<extra></extra>"))
        apply_layout(fig_steps, height=300, barmode="group",
                     xaxis=dict(title="Total step-therapy hurdles required", dtick=1,
                                title_font=dict(size=12, color=INK_SOFT)),
                     yaxis=dict(title="Number of policies", title_font=dict(size=12, color=INK_SOFT)),
                     legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), bargap=0.25)
        st.plotly_chart(fig_steps, use_container_width=True, config={"displayModeBar": False})

    section_h2("Authorization Windows",
               "Approval durations — shorter windows mean more frequent administrative touchpoints.",
               accent=SEC["drivers"])
    question("How long are the approval cycles for each brand?")
    auth_rows = []
    for b in selected_brands:
        sub = df[df["Brand"] == b]
        auth_rows.append({"Brand": b, "Type": "Initial authorization", "Median months": sub["Initial Auth (months)"].median()})
        auth_rows.append({"Brand": b, "Type": "Reauthorization", "Median months": sub["Reauth (months)"].median()})
    auth_df = pd.DataFrame(auth_rows)
    fig_auth = go.Figure()
    for i, b in enumerate(selected_brands):
        sub = auth_df[auth_df["Brand"] == b]
        fig_auth.add_trace(go.Bar(x=sub["Type"], y=sub["Median months"], name=b,
                                  marker=dict(color=brand_color(b, i), line=dict(color="#FFFFFF", width=0.5)),
                                  hovertemplate=f"<b>{b}</b><br>%{{x}}<br>Median %{{y:.0f}} months<extra></extra>"))
    apply_layout(fig_auth, height=300, barmode="group", xaxis=dict(title=""),
                 yaxis=dict(title="Median months", title_font=dict(size=12, color=INK_SOFT)),
                 legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), bargap=0.4)
    st.plotly_chart(fig_auth, use_container_width=True, config={"displayModeBar": False})

# ----------------------------------------------------------------------------
#  TAB 5 — METHODOLOGY & INSIGHTS  (visual + interactive)
# ----------------------------------------------------------------------------
with tab5:
    section_h2("How the Access Score Works",
               "The access score is a 0–100 index built by binding-constraint logic and anchored to the "
               "FDA label. It is deterministic and auditable — every point is traceable to a policy fact.",
               accent=SEC["method"])

    # The ladder — clarifies exactly what the 'points' mean
    st.markdown('<div style="height:2px"></div>', unsafe_allow_html=True)
    rungs = [
        ("100", "Open", ACCESS_TIER_COLOR["Open"], "Covered, no meaningful utilization management — effectively unrestricted."),
        ("75", "Preferred", ACCESS_TIER_COLOR["Preferred"], "Covered, lighter management than the FDA label (e.g. no step therapy)."),
        ("50", "Parity", ACCESS_TIER_COLOR["Parity"], "Management mirrors the FDA label — one conventional step, standard reauth."),
        ("25", "Restricted", ACCESS_TIER_COLOR["Restricted"], "More restrictive than the label — typically biologic step-through."),
        ("0", "No access", ACCESS_TIER_COLOR["No access"], "Not covered / excluded for plaque psoriasis."),
    ]
    ladder = "".join(
        f"""<div class="zs-rung" style="background:{c};">
              <div class="pts">{p}</div><div class="nm">{n}</div><div class="ds">{d}</div></div>"""
        for p, n, c, d in rungs)
    st.markdown(ladder, unsafe_allow_html=True)
    st.markdown(
        f"""<div class="zs-obs" style="border-left-color:{SEC['method']}; margin-top:6px;">
        <div class="zs-obs-tag" style="color:{SEC['method']};">What the points mean</div>
        <div class="zs-obs-text">The number is <b>not</b> a quality grade — it is an <b>access-restrictiveness index relative to the FDA label</b>.
        50 is the reference point (the policy asks for what the label contemplates). Points are <b>added back toward 75–100</b> when a policy is lighter than the label,
        and <b>deducted toward 25–0</b> for each payer-imposed barrier beyond it — with <b>biologic step-through</b> the dominant deduction.</div></div>""",
        unsafe_allow_html=True)

    # The three-stage logic
    section_h2("The Three-Stage Logic", accent=SEC["method"])
    sc = st.columns(3)
    stages = [
        ("Stage 1 · Coverage gate", "#B91C1C",
         "Is the brand covered for PsO? If excluded or not on formulary → <b>0</b>, and scoring stops. 0 is reserved strictly for genuine non-access."),
        ("Stage 2 · Step-therapy anchor", "#CA8A04",
         "The binding constraint sets the base tier. <b>Any biologic step-through → 25.</b> A conventional/phototherapy step → <b>50</b> (label-consistent). No step + criteria reviewed → <b>75</b>."),
        ("Stage 3 · Secondary burden", "#16A34A",
         "Specialist gating, below-label quantity limits, short reauth, extra conventional steps each add burden — nudging the anchor down. <b>TB testing is never penalised</b> (clinical norm)."),
    ]
    for col, (t, c, d) in zip(sc, stages):
        col.markdown(
            f"""<div class="zs-arch" style="border-top-color:{c}; height:100%;">
              <div class="name" style="color:{c};">{t}</div>
              <div class="desc" style="font-size:12.5px;">{d}</div></div>""",
            unsafe_allow_html=True)

    # Interactive simulator
    section_h2("Interactive Access-Score Simulator",
               "Toggle a hypothetical policy's restrictions and watch the score resolve in real time — "
               "the same logic that scores every policy in this dashboard.",
               accent=SEC["method"])
    sim_in, sim_out = st.columns([1.05, 1])
    with sim_in:
        covered = st.toggle("Covered for plaque psoriasis", value=True)
        cb1, cb2 = st.columns(2)
        with cb1:
            b_steps = st.select_slider("Biologic step-throughs", options=[0, 1, 2, 3], value=0)
            g_steps = st.select_slider("Conventional/oral steps", options=[0, 1, 2, 3], value=1)
            photo = st.checkbox("Phototherapy step required", value=False)
        with cb2:
            specialist = st.checkbox("Specialist prescriber required", value=True)
            qty = st.checkbox("Quantity limit imposed", value=False)
            reauth_m = st.select_slider("Reauth window (months)", options=[3, 6, 12, 24], value=12)
            init_m = st.select_slider("Initial window (months)", options=[1, 3, 6, 12], value=6)
        step_known = st.checkbox("Criteria reviewed (step status known)", value=True,
                                 help="If unchecked, an absent step count is treated as unknown → parity, not open.")
    score, tier, why = simulate_access_score(covered, b_steps, g_steps, photo, specialist,
                                             qty, reauth_m, init_m, step_known)
    with sim_out:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=score,
            number=dict(font=dict(size=46, color=INK, family="Fraunces")),
            gauge=dict(
                axis=dict(range=[0, 100], tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=10, color=INK_SOFT)),
                bar=dict(color=ACCESS_TIER_COLOR[tier], thickness=0.28),
                bgcolor="rgba(0,0,0,0)", borderwidth=0,
                steps=[
                    dict(range=[0, 12.5], color="#FEE2E2"),
                    dict(range=[12.5, 37.5], color="#FFEDD5"),
                    dict(range=[37.5, 62.5], color="#FEF9C3"),
                    dict(range=[62.5, 87.5], color="#DCFCE7"),
                    dict(range=[87.5, 100], color="#D1FAE5"),
                ],
            )))
        gauge.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=0),
                            paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Manrope"))
        st.plotly_chart(gauge, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f"""<div style="text-align:center; margin-top:-10px;">
            <span style="background:{ACCESS_TIER_COLOR[tier]}; color:#FFFFFF; padding:5px 14px;
            border-radius:3px; font-weight:700; font-size:12px; letter-spacing:0.08em;
            text-transform:uppercase;">{tier}</span></div>""",
            unsafe_allow_html=True)
    st.markdown(
        f"""<div class="zs-obs" style="border-left-color:{SEC['method']};">
        <div class="zs-obs-tag" style="color:{SEC['method']};">Score trace</div>
        <div class="zs-obs-text">{' &nbsp;→&nbsp; '.join(why)}</div></div>""",
        unsafe_allow_html=True)

    # Consultant insights
    section_h2("What a Market-Access Consultant Takes From This",
               "The decisions this lens informs for a brand and field team.", accent=SEC["method"])
    ic = st.columns(2)
    insights = [
        ("Target the binding constraint", SEC["drivers"],
         "Biologic step-through is the single largest access deduction. One negotiated removal of a step-edit "
         "moves a policy from Restricted (25) to Parity (50) — a bigger access gain than any number of minor concessions."),
        ("Account-led, not brand-led", SEC["compare"],
         "Within-brand access varies more than between-brand access. Field-team prioritisation should be by payer "
         "account at the Restricted/No-access end, where the addressable-population upside is concentrated."),
        ("Protect against false 'open' reads", SEC["method"],
         "A near-empty extraction is held at Parity, never promoted to Preferred/Open. For a brand team this means the "
         "lens will not over-state access where a policy simply could not be parsed — a conservative, defensible posture."),
        ("Administrative burden as a soft lever", SEC["param"],
         "Short reauth windows and specialist gating don't block access but raise abandonment risk. They are the "
         "secondary levers to raise once the step-edit fight is won — and quick wins for patient-services programmes."),
    ]
    for i, (t, c, d) in enumerate(insights):
        implication_tile(ic[i % 2], t, d, accent=c)

# ----------------------------------------------------------------------------
#  TAB 6 — POLICY EXPLORER (colourised)
# ----------------------------------------------------------------------------
with tab6:
    section_h2("Policy Explorer",
               "Drill into individual policy records. Pick a brand, then a policy, to see the full extracted "
               "parameter set, grouped into colour-coded sections.",
               accent=SEC["explorer"])

    nav1, nav2 = st.columns([1, 3])
    with nav1:
        explore_brand = st.selectbox("Brand", options=selected_brands, index=0)
    with nav2:
        sort_choice = st.radio("Sort policies by",
                               options=["Most restrictive first", "Most open first", "Policy ID"],
                               index=0, horizontal=True)
    sub = df[df["Brand"] == explore_brand].copy()
    if sort_choice == "Most restrictive first":
        sub = sub.sort_values("Access Score", ascending=True, na_position="last")
    elif sort_choice == "Most open first":
        sub = sub.sort_values("Access Score", ascending=False, na_position="last")
    else:
        sub = sub.sort_values("Policy ID")

    if len(sub) == 0:
        st.info(f"No {explore_brand} policies match the current filters.")
    else:
        def policy_label(row):
            score = f"{int(row['Access Score'])}" if pd.notna(row["Access Score"]) else "—"
            return f"{row['Policy #']}  ·  Score {score}  ·  {row['Access Tier']}"
        sub["__label"] = sub.apply(policy_label, axis=1)
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
        compare = st.toggle("Compare two policies side by side", value=False)
        if not compare:
            chosen = st.selectbox(f"Select a {explore_brand} policy", options=sub["__label"].tolist(), index=0)
            panels = [sub[sub["__label"] == chosen].iloc[0]]
        else:
            cc1, cc2 = st.columns(2)
            with cc1:
                c1 = st.selectbox("Policy A", options=sub["__label"].tolist(), index=0, key="pa")
            with cc2:
                c2 = st.selectbox("Policy B", options=sub["__label"].tolist(),
                                  index=1 if len(sub) > 1 else 0, key="pb")
            panels = [sub[sub["__label"] == c1].iloc[0], sub[sub["__label"] == c2].iloc[0]]

        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

        # Colour-coded field groups
        GROUPS = [
            ("Eligibility & screening", "#2563EB", [
                ("Age criterion", lambda r: r["Age Criterion"]),
                ("Specialist", lambda r: r["Specialist Detail"]),
                ("TB test", lambda r: r["TB Test"]),
            ]),
            ("Step therapy", "#D97706", [
                ("Step therapy", lambda r: r["Step Therapy"]),
                ("Brand-step requirements", lambda r: f"{int(r['Brand Steps'])}" if pd.notna(r['Brand Steps']) else "—"),
                ("Generic-step requirements", lambda r: f"{int(r['Generic Steps'])}" if pd.notna(r['Generic Steps']) else "—"),
                ("Phototherapy step", lambda r: r["Phototherapy Step"]),
            ]),
            ("Utilization & duration", "#0D9488", [
                ("Quantity limit", lambda r: r["Quantity Limit"]),
                ("Initial authorization", lambda r: (f"{int(r['Initial Auth (months)'])} months"
                                                     if pd.notna(r['Initial Auth (months)'])
                                                     else str(r.get('Initial Authorization Duration(in-months)') or '—'))),
                ("Reauthorization duration", lambda r: (f"{int(r['Reauth (months)'])} months"
                                                        if pd.notna(r['Reauth (months)'])
                                                        else str(r.get('Reauthorization Duration(in-months)') or '—'))),
            ]),
        ]

        cols_panel = st.columns(len(panels), gap="medium")
        for panel_col, row in zip(cols_panel, panels):
            with panel_col:
                score = int(row["Access Score"]) if pd.notna(row["Access Score"]) else None
                tier = row["Access Tier"]
                tier_color = ACCESS_TIER_COLOR.get(tier, SLATE)
                bcol = brand_color(row["Brand"])
                score_html = f"{score}" if score is not None else "—"
                st.markdown(
                    f"""
<div style="background:{CARD}; border:1px solid {LINE}; border-top:5px solid {bcol};
            border-radius:6px; padding:16px 18px; margin-bottom:12px;">
  <div style="font-size:10.5px; letter-spacing:0.16em; text-transform:uppercase;
              color:{bcol}; font-weight:700;">{row['Brand']} · {row['Policy #']}</div>
  <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
    <div>
      <div style="font-family:'Fraunces',serif; font-size:32px; font-weight:600; color:{INK}; line-height:1;">
        {score_html}<span style="font-size:14px; color:{SLATE}; font-family:Manrope; margin-left:6px;">/ 100</span></div>
      <div style="font-size:11px; color:{SLATE}; margin-top:4px; letter-spacing:0.08em;
                  text-transform:uppercase; font-weight:600;">Access score</div>
    </div>
    <div style="background:{tier_color}; color:#FFFFFF; padding:5px 12px; border-radius:3px;
                font-size:11px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;">{tier}</div>
  </div>
</div>""",
                    unsafe_allow_html=True)

                for gname, gcolor, fields in GROUPS:
                    inner = ""
                    for label, fn in fields:
                        val = fn(row)
                        if pd.isna(val) or str(val).strip() in ("", "nan", "None"):
                            val = "—"
                        inner += (f'<div class="zs-field" style="background:{gcolor}0F;">'
                                  f'<div class="zs-field-label">{label}</div>'
                                  f'<div class="zs-field-value">{val}</div></div>')
                    st.markdown(
                        f"""<div class="zs-fieldgroup" style="border-top:4px solid {gcolor};">
                          <div class="gh" style="color:{gcolor};">{gname}</div>{inner}</div>""",
                        unsafe_allow_html=True)

                step_text = row.get("Step Therapy Requirements Documented in Policy")
                reauth_text = row.get("Reauthorization Requirements Documented in Policy")
                qty_text = row.get("Quantity Limits")
                if pd.notna(step_text) and str(step_text).strip().lower() not in ("no", "nan", ""):
                    with st.expander("Step-therapy language (verbatim)"):
                        st.write(step_text)
                if pd.notna(reauth_text) and str(reauth_text).strip().lower() not in ("no", "nan", ""):
                    with st.expander("Reauthorization requirements (verbatim)"):
                        st.write(reauth_text)
                if pd.notna(qty_text) and len(str(qty_text).strip()) > 6 and str(qty_text).strip().lower() not in ("no", "nan"):
                    with st.expander("Quantity-limit language (verbatim)"):
                        st.write(qty_text)
                with st.expander("Source policy identifier"):
                    st.code(row["Policy ID"] + ".pdf", language="text")

# ============================================================================
#  FOOTER
# ============================================================================
st.markdown(
    f"""
<div class="zs-footer">
  <span>ZS · Market Access Practice · Plaque Psoriasis Policy Lens</span>
  <span>{df_all['Policy ID'].nunique()} policies · {len(ALL_BRANDS)} brands · TREMFYA & STELARA in focus</span>
</div>""",
    unsafe_allow_html=True,
)
