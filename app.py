"""PsO Market Access Intelligence — payer prior-authorization lens.

A board-ready view of how payer policies shape access across the PsO biologic
basket. One set of global filters (sidebar) drives every tab; the TREMFYA vs
STELARA head-to-head is the analytical spine.
"""
from __future__ import annotations
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

TREMFYA_C       = "#047857"
TREMFYA_LIGHT   = "#10B981"
STELARA_C       = "#6D28D9"
STELARA_LIGHT   = "#A78BFA"

FOCUS_BRANDS = ["TREMFYA", "STELARA"]

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


# Access tiers — 0 / 25 / 50 / 75 / 100, anchored to the FDA label (50 = parity).
ACCESS_TIER_ORDER = ["No access", "Restricted", "Parity", "Preferred", "Open"]
ACCESS_TIER_COLOR = {
    "No access":   "#B91C1C",
    "Restricted":  "#EA580C",
    "Parity":      "#CA8A04",
    "Preferred":   "#16A34A",
    "Open":        "#047857",
    "Unscored":    "#94A3B8",
}

# A green→red restrictiveness ramp for "more is worse" count charts.
RESTRICT_RAMP = ["#16A34A", "#CA8A04", "#EA580C", "#B91C1C", "#7F1D1D", "#450A0A"]

# Section accents — each section gets its own colour block.
SEC = {
    "exec":     "#D97706",
    "param":    "#2563EB",
    "compare":  "#0D9488",
    "drivers":  "#DB2777",
    "method":   "#7C3AED",
    "explorer": "#0E7490",
}

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Manrope, -apple-system, BlinkMacSystemFont, sans-serif",
              color=INK, size=13),
    margin=dict(l=10, r=10, t=24, b=10),
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
section.main > div.block-container {{ padding-top: 1.4rem; padding-bottom: 4rem; max-width: 1400px; }}

/* Masthead */
.zs-masthead {{ display: flex; justify-content: space-between; align-items: flex-end;
    padding-bottom: 14px; margin-bottom: 12px; border-bottom: 1px solid {LINE}; }}
.zs-masthead-left .eyebrow {{ font-size: 10.5px; letter-spacing: 0.22em; text-transform: uppercase;
    color: {AMBER}; font-weight: 700; margin-bottom: 5px; }}
.zs-masthead-left h1 {{ font-family: 'Fraunces', Georgia, serif !important; font-weight: 600;
    font-size: 27px; line-height: 1.15; letter-spacing: -0.015em; color: {INK}; margin: 0 0 5px 0; }}
.zs-masthead-left .deck {{ font-size: 12.5px; color: {INK_SOFT}; max-width: 720px; line-height: 1.45; }}
.zs-masthead-right {{ text-align: right; font-size: 11px; letter-spacing: 0.06em;
    text-transform: uppercase; color: {SLATE}; font-weight: 500; }}
.zs-pill-tremfya, .zs-pill-stelara {{ display: inline-block; padding: 4px 11px; margin-left: 6px;
    border-radius: 2px; font-weight: 700; font-size: 10px; letter-spacing: 0.14em; color: #FFFFFF; }}
.zs-pill-tremfya {{ background: {TREMFYA_C}; }}
.zs-pill-stelara {{ background: {STELARA_C}; }}

/* Global-filter context bar */
.zs-filterbar {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    background: {CARD}; border: 1px solid {LINE}; border-left: 4px solid {AMBER};
    border-radius: 5px; padding: 9px 14px; margin-bottom: 8px; font-size: 12px; color: {INK_SOFT}; }}
.zs-filterbar .lead {{ font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase;
    font-weight: 700; color: {AMBER}; }}
.zs-chip {{ display: inline-flex; align-items: center; gap: 5px; background: {PAPER};
    border: 1px solid {LINE}; border-radius: 20px; padding: 3px 11px; font-size: 11.5px;
    font-weight: 600; color: {INK}; }}
.zs-chip b {{ color: {INK}; }}
.zs-filterbar .note {{ margin-left: auto; font-size: 10.5px; color: {SLATE}; font-style: italic; }}

/* Scale / units legend */
.zs-scale {{ display: flex; align-items: center; gap: 0; margin: 4px 0 2px 0;
    border: 1px solid {LINE}; border-radius: 6px; overflow: hidden; font-size: 11px; }}
.zs-scale .seg {{ flex: 1; padding: 7px 10px; color: #FFFFFF; font-weight: 600;
    letter-spacing: 0.02em; text-align: center; }}
.zs-scale .seg .v {{ font-family: 'Fraunces', serif; font-size: 14px; font-weight: 700; }}
.zs-scale .seg .l {{ display: block; font-size: 9.5px; opacity: 0.92; font-weight: 600;
    letter-spacing: 0.06em; text-transform: uppercase; }}
.zs-scale-note {{ font-size: 11px; color: {SLATE}; margin: 4px 0 2px 2px; }}
.zs-scale-note b {{ color: {INK_SOFT}; }}

/* Section heading */
.zs-sec {{ margin: 26px 0 12px 0; padding: 11px 16px; border-radius: 5px; border-left: 5px solid {AMBER};
    background: linear-gradient(90deg, rgba(217,119,6,0.07) 0%, rgba(217,119,6,0.0) 60%); }}
.zs-sec h2 {{ font-family: 'Fraunces', Georgia, serif !important; font-weight: 600; font-size: 19px;
    line-height: 1.2; letter-spacing: -0.01em; color: {INK}; margin: 0 0 2px 0; }}
.zs-sec .deck {{ font-size: 12px; color: {INK_SOFT}; line-height: 1.45; max-width: 880px; }}

/* Chart caption */
.zs-cap {{ font-size: 12.5px; color: {INK_SOFT}; margin: 12px 0 4px 0; line-height: 1.4; }}
.zs-cap b {{ color: {INK}; font-weight: 700; }}

/* Headline takeaway */
.zs-takeaway {{ background: {CARD}; border: 1px solid {LINE}; border-left: 5px solid {AMBER};
    border-radius: 6px; padding: 14px 18px; margin: 2px 0 6px 0; }}
.zs-takeaway .k {{ font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
    font-weight: 700; color: {AMBER}; margin-bottom: 5px; }}
.zs-takeaway .t {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 16.5px;
    font-weight: 500; line-height: 1.4; color: {INK}; }}
.zs-takeaway .t b {{ font-weight: 700; }}

/* KPI cards */
.zs-kpi {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 5px; padding: 13px 16px;
    height: 100%; position: relative; overflow: hidden; }}
.zs-kpi-accent {{ position: absolute; top: 0; left: 0; width: 5px; height: 100%; background: {AMBER}; }}
.zs-kpi-label {{ font-size: 10px; letter-spacing: 0.13em; text-transform: uppercase; color: {SLATE};
    font-weight: 600; margin-bottom: 6px; }}
.zs-kpi-value {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 29px; font-weight: 600;
    line-height: 1.05; color: {INK}; letter-spacing: -0.02em; }}
.zs-kpi-value .unit {{ font-size: 12px; color: {SLATE}; font-family: 'Manrope', sans-serif !important;
    font-weight: 500; margin-left: 4px; }}
.zs-kpi-foot {{ font-size: 11px; color: {INK_SOFT}; margin-top: 7px; line-height: 1.35; min-height: 1.35em; }}

/* Insight tiles */
.zs-obs {{ background: {CARD}; border: 1px solid {LINE}; border-left: 4px solid {AMBER}; border-radius: 5px;
    padding: 13px 15px; height: 100%; }}
.zs-obs-tag {{ font-size: 9.5px; letter-spacing: 0.15em; text-transform: uppercase; font-weight: 700;
    margin-bottom: 5px; }}
.zs-obs-text {{ font-size: 12.5px; color: {INK}; line-height: 1.5; }}
.zs-obs-text b {{ color: {INK}; font-weight: 700; }}

/* Verdict band */
.zs-verdict {{ color: #FFFFFF; padding: 13px 22px; border-radius: 5px; margin-top: 4px; display: flex;
    align-items: center; justify-content: space-between; }}
.zs-verdict .label {{ font-size: 10px; letter-spacing: 0.20em; text-transform: uppercase; font-weight: 700;
    opacity: 0.9; }}
.zs-verdict .text {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 17px; font-weight: 600;
    line-height: 1.25; margin-top: 4px; max-width: 760px; }}
.zs-verdict .number {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 38px; font-weight: 700;
    line-height: 1; letter-spacing: -0.02em; white-space: nowrap; }}
.zs-verdict .number .small {{ font-size: 14px; font-weight: 500; opacity: 0.9; }}

/* Scorecard */
.zs-scorecard {{ background: {CARD}; border: 1px solid {LINE}; border-top: 5px solid {TREMFYA_C};
    padding: 15px 18px; border-radius: 5px; }}
.zs-scorecard h3 {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 20px; font-weight: 600;
    margin: 0; color: {INK}; letter-spacing: -0.01em; }}
.zs-scorecard .strap {{ font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 700;
    margin-bottom: 3px; }}
.zs-scorecard table {{ width: 100%; margin-top: 11px; border-collapse: collapse; }}
.zs-scorecard table td {{ padding: 6px 0; border-bottom: 1px dashed {LINE}; font-size: 12px; color: {INK}; }}
.zs-scorecard table tr:last-child td {{ border-bottom: none; }}
.zs-scorecard table td.label {{ color: {INK_SOFT}; }}
.zs-scorecard table td.value {{ text-align: right; font-weight: 600; color: {INK};
    font-variant-numeric: tabular-nums; }}

/* Stage card */
.zs-arch {{ background: {CARD}; border: 1px solid {LINE}; border-top: 5px solid {SLATE}; border-radius: 5px;
    padding: 13px 15px; height: 100%; }}
.zs-arch .name {{ font-size: 11px; letter-spacing: 0.10em; text-transform: uppercase; font-weight: 700;
    margin-bottom: 4px; }}
.zs-arch .desc {{ font-size: 12px; color: {INK_SOFT}; margin-top: 4px; line-height: 1.45; }}

/* Explorer field groups */
.zs-fieldgroup {{ border: 1px solid {LINE}; border-radius: 6px; padding: 11px 14px; margin-bottom: 11px;
    background: {CARD}; }}
.zs-fieldgroup .gh {{ font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 700;
    margin-bottom: 7px; }}
.zs-field {{ border-radius: 4px; padding: 8px 11px; margin-bottom: 5px; }}
.zs-field:last-child {{ margin-bottom: 0; }}
.zs-field-label {{ font-size: 9.5px; letter-spacing: 0.08em; text-transform: uppercase; color: {SLATE};
    font-weight: 600; margin-bottom: 2px; }}
.zs-field-value {{ font-size: 12.5px; color: {INK}; line-height: 1.4; font-weight: 500; }}

/* Tier ladder */
.zs-rung {{ display: flex; align-items: center; gap: 14px; padding: 9px 14px; border-radius: 6px;
    margin-bottom: 6px; color: #FFFFFF; }}
.zs-rung .pts {{ font-family: 'Fraunces', serif !important; font-size: 22px; font-weight: 700; width: 52px; }}
.zs-rung .nm {{ font-weight: 700; font-size: 12.5px; letter-spacing: 0.04em; width: 104px; }}
.zs-rung .ds {{ font-size: 12px; opacity: 0.96; }}

/* In-tab view-control strip */
.zs-ctrl-hint {{ font-size: 9.5px; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 700;
    color: {SLATE}; margin-bottom: 2px; }}

/* Tabs */
div[data-baseweb="tab-list"] {{ gap: 0; border-bottom: 1px solid {LINE}; background: transparent;
    padding-left: 0; flex-wrap: wrap; }}
button[data-baseweb="tab"] {{ font-family: 'Manrope', sans-serif !important; font-weight: 600 !important;
    font-size: 13px !important; letter-spacing: 0.02em !important; color: {SLATE} !important;
    background: transparent !important; padding: 12px 20px !important; border-radius: 0 !important;
    border-bottom: 2px solid transparent !important; margin-right: 2px; }}
button[data-baseweb="tab"]:hover {{ color: {INK} !important; background: rgba(217, 119, 6, 0.04) !important; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color: {INK} !important; border-bottom-color: {AMBER} !important; }}
div[data-baseweb="tab-panel"] {{ padding-top: 14px; }}

/* Sidebar */
section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {NAVY} 0%, #0F172A 100%); }}
section[data-testid="stSidebar"] * {{ color: #E5E7EB !important; }}
section[data-testid="stSidebar"] label {{ color: #FCD34D !important; font-size: 10px !important;
    letter-spacing: 0.14em !important; text-transform: uppercase !important; font-weight: 700 !important; }}
.zs-side-brand {{ padding-bottom: 14px; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 14px; }}
.zs-side-brand .eyebrow {{ font-size: 9.5px; letter-spacing: 0.22em; text-transform: uppercase;
    color: {AMBER_SOFT} !important; font-weight: 700; margin-bottom: 4px; }}
.zs-side-brand .title {{ font-family: 'Fraunces', Georgia, serif !important; font-size: 21px; font-weight: 600;
    color: #FFFFFF !important; line-height: 1.2; }}
.zs-side-brand .strap {{ font-size: 11px; color: rgba(229,231,235,0.65) !important; line-height: 1.4;
    margin-top: 5px; }}
.zs-side-scope {{ background: rgba(217,119,6,0.16); border: 1px solid rgba(251,191,36,0.35);
    border-radius: 5px; padding: 8px 11px; margin-bottom: 14px; }}
.zs-side-scope .h {{ font-size: 9.5px; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 700;
    color: {AMBER_SOFT} !important; margin-bottom: 2px; }}
.zs-side-scope .b {{ font-size: 11px; color: rgba(229,231,235,0.85) !important; line-height: 1.4; }}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{ background-color: rgba(255,255,255,0.06) !important;
    border-color: rgba(255,255,255,0.15) !important; color: #FFFFFF !important; }}
section[data-testid="stSidebar"] [data-baseweb="tag"] {{ background-color: {AMBER} !important; }}
section[data-testid="stSidebar"] [data-baseweb="tag"] span {{ color: {NAVY} !important; font-weight: 700; }}
section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] > div > div {{ background-color: {AMBER_SOFT} !important; }}
.zs-side-footer {{ margin-top: 18px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1);
    font-size: 10.5px; color: rgba(229,231,235,0.55) !important; line-height: 1.5; }}

[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 3px; background: {CARD}; }}
.streamlit-expanderHeader {{ font-family: 'Manrope', sans-serif !important; font-weight: 600 !important;
    color: {INK} !important; background: {CARD} !important; border: 1px solid {LINE} !important;
    border-radius: 3px !important; }}
.js-plotly-plot .plotly .modebar {{ display: none !important; }}
.zs-footer {{ margin-top: 48px; padding-top: 14px; border-top: 1px solid {LINE}; font-size: 10.5px;
    letter-spacing: 0.10em; text-transform: uppercase; color: {SLATE}; display: flex;
    justify-content: space-between; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================================
#  DATA LOADING
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


def simulate_access_score(covered, b_steps, g_steps, photo, specialist,
                          qty_limit, reauth_months, init_months, step_known=True):
    why = []
    if not covered:
        return 0, "No access", ["Coverage gate: not covered for PsO → 0"]
    if b_steps >= 2:
        anchor = 25; why.append(f"Anchor: {b_steps} biologic steps (beyond label) → 25")
    elif b_steps == 1:
        anchor = 25; why.append("Anchor: 1 biologic step (beyond label) → 25 floor")
    elif g_steps >= 1 or photo:
        anchor = 50; why.append(f"Anchor: label-consistent step → 50 parity")
    elif step_known:
        anchor = 75; why.append("Anchor: criteria reviewed, no step → 75")
    else:
        anchor = 50; why.append("Anchor: step unknown → 50")
    burden = 0; notes = []
    if specialist:
        burden += 1; notes.append("specialist")
    if qty_limit:
        burden += 1; notes.append("quantity limit")
    if reauth_months and reauth_months <= 6:
        burden += 1; notes.append("short reauth")
    if init_months and init_months < 3:
        burden += 1; notes.append("short initial")
    if g_steps >= 2:
        burden += (g_steps - 1); notes.append(f"{g_steps} conventional steps")
    if photo and (b_steps > 0 or g_steps > 0):
        burden += 1; notes.append("added phototherapy")
    why.append(f"Burden = {burden} ({', '.join(notes) if notes else 'none'})")
    if anchor == 25:
        score = 25
    elif anchor == 50:
        score = 25 if burden >= 2 else 50
    elif anchor == 75:
        score = 100 if burden == 0 else (50 if burden >= 2 else 75)
    else:
        score = anchor
    why.append(f"Final score {score}")
    return score, access_tier(score), why


def kpi_card(col, label, value, foot="", accent=AMBER):
    col.markdown(
        f"""<div class="zs-kpi"><div class="zs-kpi-accent" style="background:{accent};"></div>
  <div class="zs-kpi-label">{label}</div>
  <div class="zs-kpi-value">{value}</div>
  <div class="zs-kpi-foot">{foot}</div></div>""",
        unsafe_allow_html=True,
    )


def insight_tile(col, tag, html, accent=AMBER):
    col.markdown(
        f"""<div class="zs-obs" style="border-left-color:{accent};">
  <div class="zs-obs-tag" style="color:{accent};">{tag}</div>
  <div class="zs-obs-text">{html}</div></div>""",
        unsafe_allow_html=True,
    )


def section_h2(title, deck="", accent=AMBER):
    st.markdown(
        f"""<div class="zs-sec" style="border-left-color:{accent};
     background: linear-gradient(90deg, {accent}14 0%, {accent}00 60%);">
  <h2>{title}</h2>
  {f'<div class="deck">{deck}</div>' if deck else ''}</div>""",
        unsafe_allow_html=True,
    )


def chart_caption(html):
    st.markdown(f'<div class="zs-cap">{html}</div>', unsafe_allow_html=True)


def control_hint(text):
    st.markdown(f'<div class="zs-ctrl-hint">{text}</div>', unsafe_allow_html=True)


def score_scale_strip():
    segs = [
        ("0", "No access", ACCESS_TIER_COLOR["No access"]),
        ("25", "Restricted", ACCESS_TIER_COLOR["Restricted"]),
        ("50", "FDA parity", ACCESS_TIER_COLOR["Parity"]),
        ("75", "Preferred", ACCESS_TIER_COLOR["Preferred"]),
        ("100", "Open", ACCESS_TIER_COLOR["Open"]),
    ]
    body = "".join(
        f'<div class="seg" style="background:{c};"><span class="v">{v}</span>'
        f'<span class="l">{l}</span></div>' for v, l, c in segs)
    st.markdown(f'<div class="zs-scale">{body}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="zs-scale-note"><b>Access Score (pts)</b> — a 0–100 index of how '
        'restrictive a policy is versus the FDA label. Higher = easier access. '
        '<b>50 = parity</b> with the label; below 50 = payer-added barriers; above 50 = lighter than label.</div>',
        unsafe_allow_html=True,
    )


# ============================================================================
#  INGESTION
# ============================================================================
st.sidebar.markdown(
    """<div class="zs-side-brand">
  <div class="eyebrow">ZS · Market Access</div>
  <div class="title">PsO Policy Lens</div>
  <div class="strap">Prior-authorization intelligence across the PsO biologic basket.</div>
</div>""",
    unsafe_allow_html=True,
)

local_path = find_local_file()
if local_path is None:
    st.error("Results workbook not found. Place **result__15_.xlsx** next to this app and reload.")
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
                    key=lambda b: (b not in FOCUS_BRANDS, b))

# ============================================================================
#  SIDEBAR — GLOBAL FILTERS (drive every tab)
# ============================================================================
st.sidebar.markdown(
    """<div class="zs-side-scope">
  <div class="h">Global filters</div>
  <div class="b">Every selection below applies to all six tabs.</div>
</div>""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("**Brands in view**")
default_brands = [b for b in FOCUS_BRANDS if b in ALL_BRANDS] or ALL_BRANDS[:1]
selected_brands = st.sidebar.multiselect(
    "Brands in view", options=ALL_BRANDS, default=default_brands,
    label_visibility="collapsed",
    help="The whole dashboard responds to this. Headline numbers focus on TREMFYA vs STELARA.",
)
if not selected_brands:
    selected_brands = default_brands

st.sidebar.markdown("**Access-score range (pts)**")
score_range = st.sidebar.slider(
    "Access-score range", min_value=0, max_value=100, value=(0, 100), step=25,
    label_visibility="collapsed",
)

st.sidebar.markdown("**Access tiers**")
tier_options = [t for t in ACCESS_TIER_ORDER if t in df_all["Access Tier"].unique()]
selected_tiers = st.sidebar.multiselect(
    "Access tiers", options=tier_options, default=tier_options,
    label_visibility="collapsed",
)

base_mask = (df_all["Access Score"].between(score_range[0], score_range[1])
             & df_all["Access Tier"].isin(selected_tiers))
df = df_all[base_mask & df_all["Brand"].isin(selected_brands)].copy()
focus_present = [b for b in FOCUS_BRANDS if b in df_all["Brand"].unique()]
df_focus = df_all[base_mask & df_all["Brand"].isin(focus_present)].copy()

st.sidebar.markdown(
    f"""<div class="zs-side-footer">
<b>{df_all['Policy ID'].nunique()}</b> payer policies · <b>{len(df_all)}</b> brand-policy records ·
<b>{len(ALL_BRANDS)}</b> brands.<br><br>
In view: <b>{len(selected_brands)}</b> brand(s) · <b>{len(df)}</b> records.
</div>""",
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("No records match the current filters. Loosen them in the sidebar to continue.")
    st.stop()

# ============================================================================
#  MASTHEAD
# ============================================================================
st.markdown(
    f"""<div class="zs-masthead">
  <div class="zs-masthead-left">
    <div class="eyebrow">Plaque Psoriasis · Payer Access Intelligence</div>
    <h1>How payer policies shape access across the PsO biologic basket</h1>
    <div class="deck">Prior-authorization signals from {df_all['Policy ID'].nunique()} payer policies —
    where access opens, where it tightens, and what drives the gap. TREMFYA vs STELARA in focus.</div>
  </div>
  <div class="zs-masthead-right">
    Focus pair<span class="zs-pill-tremfya">TREMFYA</span><span class="zs-pill-stelara">STELARA</span>
  </div>
</div>""",
    unsafe_allow_html=True,
)

# Global-filter context bar — makes filter scope unmistakable on every page.
brand_label = ", ".join(selected_brands) if len(selected_brands) <= 4 else f"{len(selected_brands)} brands"
tier_label = "All tiers" if len(selected_tiers) == len(tier_options) else ", ".join(selected_tiers)
st.markdown(
    f"""<div class="zs-filterbar">
  <span class="lead">Filters in effect</span>
  <span class="zs-chip">Brands · <b>{brand_label}</b></span>
  <span class="zs-chip">Score · <b>{score_range[0]}–{score_range[1]} pts</b></span>
  <span class="zs-chip">Tiers · <b>{tier_label}</b></span>
  <span class="zs-chip"><b>{len(df)}</b> records in view</span>
  <span class="note">Set in the sidebar · applies to all tabs</span>
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
    "Methodology",
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

    score_scale_strip()
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Policies in view", f"{df['Policy ID'].nunique()}",
             foot=f"{len(df)} records · {len(selected_brands)} brand(s)", accent=SLATE)
    kpi_card(c2, "TREMFYA mean access", f"{t_mean:.0f}<span class='unit'>pts</span>" if not np.isnan(t_mean) else "—",
             foot=f"across {len(tdf)} TREMFYA policies", accent=TREMFYA_C)
    kpi_card(c3, "STELARA mean access", f"{s_mean:.0f}<span class='unit'>pts</span>" if not np.isnan(s_mean) else "—",
             foot=f"across {len(sdf)} STELARA policies", accent=STELARA_C)
    if not np.isnan(diff):
        leader = "TREMFYA" if diff > 0 else ("STELARA" if diff < 0 else "Parity")
        sign = "+" if diff > 0 else ""
        acc = TREMFYA_C if diff > 0 else (STELARA_C if diff < 0 else SLATE)
        kpi_card(c4, "Access gap", f"{sign}{diff:.0f}<span class='unit'>pts</span>",
                 foot=f"{leader} ahead on mean access", accent=acc)
    else:
        kpi_card(c4, "Access gap", "—", "", accent=SLATE)

    if not np.isnan(diff):
        if abs(diff) < 1:
            grad = f"linear-gradient(90deg,{SLATE} 0%,#94A3B8 100%)"
            lbl, txt, num = "Verdict · parity", "TREMFYA and STELARA face broadly equal payer access.", "≈ 0<span class='small'> pts</span>"
        elif diff > 0:
            grad = f"linear-gradient(90deg,{TREMFYA_C} 0%,{TREMFYA_LIGHT} 100%)"
            lbl, txt, num = "Access leader · TREMFYA", "TREMFYA holds the mean-access advantage across the corpus.", f"+{diff:.0f}<span class='small'> pts</span>"
        else:
            grad = f"linear-gradient(90deg,{STELARA_C} 0%,{STELARA_LIGHT} 100%)"
            lbl, txt, num = "Access leader · STELARA", "STELARA holds the mean-access advantage across the corpus.", f"+{abs(diff):.0f}<span class='small'> pts</span>"
        st.markdown(
            f"""<div class="zs-verdict" style="background:{grad};">
  <div><div class="label">{lbl}</div><div class="text">{txt}</div></div>
  <div class="number">{num}</div></div>""",
            unsafe_allow_html=True,
        )

    # Headline takeaway — the single "so what".
    rs_all = restriction_share(df).sort_values("Share", ascending=False)
    top_lever = rs_all.iloc[0] if len(rs_all) else None
    t_range = (tdf["Access Score"].max() - tdf["Access Score"].min()) if len(tdf) else 0
    s_range = (sdf["Access Score"].max() - sdf["Access Score"].min()) if len(sdf) else 0
    spread = max(t_range, s_range)
    if top_lever is not None:
        st.markdown(
            f"""<div class="zs-takeaway">
      <div class="k">Headline</div>
      <div class="t">Access is set by the <b>payer, not the molecule</b>: scores swing up to
      <b>{spread:.0f} pts</b> policy-to-policy, and <b>{top_lever['Restriction'].lower()}</b> is the
      control behind it — present in <b>{top_lever['Share']*100:.0f}%</b> of policies in view.</div>
    </div>""",
            unsafe_allow_html=True,
        )

    section_h2("Access spectrum", accent=SEC["exec"])
    chart_caption("Where each brand's policies land on the 0–100 access scale. "
                  "Mass near <b>25</b> = biologic step-through beyond the FDA label; mass near <b>50</b> = label parity.")
    fig_dist = go.Figure()
    plot_brands = selected_brands if len(selected_brands) <= 6 else (focus_present or selected_brands[:6])
    for i, b in enumerate(plot_brands):
        bsub = df[df["Brand"] == b].dropna(subset=["Access Score"])
        if len(bsub) == 0:
            continue
        fig_dist.add_trace(go.Violin(
            x=bsub["Access Score"], y=[b] * len(bsub), name=b, orientation="h",
            side="positive", line_color=brand_color(b, i), fillcolor=brand_color(b, i),
            opacity=0.5, box_visible=True, meanline_visible=True, points="all",
            pointpos=-0.6, jitter=0.25,
            marker=dict(color=brand_color(b, i), size=6, opacity=0.85,
                        line=dict(color="#FFFFFF", width=0.5)),
            hoveron="points", hovertemplate=f"<b>{b}</b><br>%{{x}} pts<extra></extra>",
            scalemode="count", spanmode="hard",
        ))
    apply_layout(fig_dist, height=max(300, 92 * len(plot_brands) + 80),
                 xaxis=dict(range=[-5, 105], title="Access Score (pts)",
                            tickvals=[0, 25, 50, 75, 100], title_font=dict(size=12, color=INK_SOFT)),
                 yaxis=dict(title="", showgrid=False), showlegend=False, violinmode="group")
    # FDA-parity reference line
    fig_dist.add_vline(x=50, line=dict(color=ACCESS_TIER_COLOR["Parity"], width=1.2, dash="dot"))
    fig_dist.add_annotation(x=50, y=1.0, yref="paper", text="FDA parity",
                            showarrow=False, font=dict(size=10, color=ACCESS_TIER_COLOR["Parity"]),
                            yshift=8)
    st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar": False})

    section_h2("What this means", accent=SEC["exec"])
    ic = st.columns(3)
    if not np.isnan(diff):
        leader = "TREMFYA" if diff > 0 else "STELARA"
        trail = "STELARA" if diff > 0 else "TREMFYA"
        acc = TREMFYA_C if diff > 0 else STELARA_C
        insight_tile(ic[0], "Brand positioning",
                     f"<b>{leader} leads by {abs(diff):.0f} pts</b> on mean access. "
                     f"Defend {leader}'s lead; close {trail}'s gap at its weakest accounts.",
                     accent=acc)
    insight_tile(ic[1], "Payer vs brand",
                 f"Access varies up to <b>{spread:.0f} pts</b> across payers within a single brand. "
                 f"<b>Target by account, not by brand.</b>",
                 accent=SEC["exec"])
    if top_lever is not None:
        insight_tile(ic[2], "Highest-leverage control",
                     f"<b>{top_lever['Restriction']}</b> appears in <b>{top_lever['Share']*100:.0f}%</b> "
                     f"of policies — the single biggest negotiation lever.",
                     accent=SEC["exec"])

# ----------------------------------------------------------------------------
#  TAB 2 — PARAMETER ANALYSIS
# ----------------------------------------------------------------------------
with tab2:
    section_h2("Parameter analysis",
               "Pick any extracted PA parameter to see its corpus-wide distribution and how it splits by brand.",
               accent=SEC["param"])

    PARAM_GROUPS = {
        "Eligibility & screening": [
            ("Age Criterion", "categorical", "Age criterion"),
            ("TB Test", "yesno", "TB test required"),
            ("Specialist Required", "yesno", "Specialist prescriber required"),
        ],
        "Step therapy & pre-treatment": [
            ("Step Therapy", "yesno", "Step therapy documented"),
            ("Brand Steps", "numeric", "Biologic steps required"),
            ("Generic Steps", "numeric", "Conventional/oral steps required"),
            ("Phototherapy Step", "yesno", "Phototherapy step required"),
        ],
        "Utilization management": [
            ("Quantity Limit", "yesno", "Quantity limit imposed"),
            ("Initial Auth (months)", "numeric", "Initial authorization (months)"),
            ("Reauth (months)", "numeric", "Reauthorization (months)"),
        ],
    }
    PARAM_INSIGHTS = {
        "Age Criterion": "Age thresholds size the eligible pool — explicit floors (≥6, ≥18) matter most for pediatric positioning.",
        "TB Test": "TB screening is standard pre-biologic care, not a true barrier — it is deliberately not penalised in the score.",
        "Specialist Required": "Dermatologist-only prescribing narrows the writer base; 'in consultation with' language softens it.",
        "Step Therapy": "The single most material access lever, required in most policies — the primary battleground for access teams.",
        "Brand Steps": "Biologic step-through is the strongest driver of delay and abandonment — every prior biologic is a barrier beyond the label.",
        "Generic Steps": "Conventional/oral steps (methotrexate, cyclosporine, acitretin) are label-consistent and depress access far less.",
        "Phototherapy Step": "Uncommon but consequential — mandatory clinic-administered UVB/PUVA is out of reach for many patients.",
        "Quantity Limit": "Below-label unit caps restrict dose optimisation — a genuine access constraint.",
        "Initial Auth (months)": "Short initial windows (≤6 months) raise early-discontinuation risk and practice workload.",
        "Reauth (months)": "Sets ongoing administrative burden — 12 months is the prevailing, lower-friction standard.",
    }

    control_hint("View control · this tab only")
    pc1, pc2 = st.columns([1, 2])
    with pc1:
        category = st.selectbox("Parameter group", options=list(PARAM_GROUPS.keys()), index=1)
    with pc2:
        opts = [(label, col, kind) for col, kind, label in PARAM_GROUPS[category]]
        chosen_label = st.selectbox("Parameter", options=[lbl for lbl, _, _ in opts], index=0)
    sel_col, sel_kind = next((c, k) for lbl, c, k in opts if lbl == chosen_label)

    is_restrictive = sel_col in ("Brand Steps", "Generic Steps")

    left, right = st.columns(2)
    with left:
        chart_caption(f"<b>{chosen_label}</b> — distribution across policies in view")
        if sel_kind == "numeric":
            d = df[sel_col].dropna()
            if len(d) == 0:
                st.info("No data for this parameter in the current filter.")
            else:
                vc = d.astype(int).value_counts().sort_index()
                if is_restrictive:
                    bar_colors = [RESTRICT_RAMP[min(int(x), len(RESTRICT_RAMP) - 1)] for x in vc.index]
                else:
                    bar_colors = SEC["param"]
                fig_p = go.Figure(go.Bar(
                    x=vc.index, y=vc.values,
                    marker=dict(color=bar_colors, line=dict(color="#FFFFFF", width=0.5)),
                    hovertemplate=f"<b>{chosen_label}</b>: %{{x}}<br>%{{y}} policies<extra></extra>"))
                apply_layout(fig_p, height=300,
                             xaxis=dict(title=chosen_label, dtick=1, title_font=dict(size=12, color=INK_SOFT)),
                             yaxis=dict(title="Policies", title_font=dict(size=12, color=INK_SOFT)),
                             showlegend=False, bargap=0.22)
                st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})
        else:
            vc = df[sel_col].fillna("Not specified").value_counts()
            n = len(vc)
            cat_colors = [_FALLBACK_CYCLE[i % len(_FALLBACK_CYCLE)] for i in range(n)]
            fig_p = go.Figure(go.Bar(
                y=vc.index.tolist(), x=vc.values, orientation="h",
                marker=dict(color=cat_colors, line=dict(color="#FFFFFF", width=0.5)),
                hovertemplate=f"<b>{chosen_label}</b>: %{{y}}<br>%{{x}} policies<extra></extra>"))
            apply_layout(fig_p, height=max(220, 46 * n + 80),
                         xaxis=dict(title="Policies", title_font=dict(size=12, color=INK_SOFT)),
                         yaxis=dict(title=""), showlegend=False)
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})
    with right:
        chart_caption(f"<b>{chosen_label}</b> — by brand")
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
                            opacity=0.5, boxmean=True, orientation="h",
                            hovertemplate=f"<b>{b}</b><br>%{{x}}<extra></extra>"))
                apply_layout(fig_b, height=max(280, 58 * len(selected_brands) + 80),
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
        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
        insight_tile(st.container(), "Implication", interp, accent=SEC["param"])

# ----------------------------------------------------------------------------
#  TAB 3 — BRAND COMPARISON
# ----------------------------------------------------------------------------
with tab3:
    section_h2("Brand comparison",
               "Scorecards and access-tier mix for the brands in view. The paired view compares TREMFYA and STELARA inside the same policy.",
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
            "Mean access (pts)": f"{sub['Access Score'].mean():.0f}",
            "Median access (pts)": f"{sub['Access Score'].median():.0f}",
            "Score range (pts)": f"{sub['Access Score'].min():.0f}–{sub['Access Score'].max():.0f}",
            "Step therapy": f"{(sub['Step Therapy']=='Required').mean()*100:.0f}%",
            "Biologic step (any)": f"{(sub['Brand Steps']>=1).mean()*100:.0f}%",
            "TB test": f"{(sub['TB Test']=='Yes').mean()*100:.0f}%",
            "Quantity limit": f"{(sub['Quantity Limit']=='Yes').mean()*100:.0f}%",
            "Specialist required": f"{(sub['Specialist Required']=='Required').mean()*100:.0f}%",
            "Median reauth": (f"{sub['Reauth (months)'].median():.0f} mo"
                              if sub["Reauth (months)"].notna().any() else "—"),
        }
        rows_html = "".join(
            f'<tr><td class="label">{k}</td><td class="value">{v}</td></tr>' for k, v in metrics.items())
        acc = brand_color(brand, i)
        with col:
            st.markdown(
                f"""<div class="zs-scorecard" style="border-top-color:{acc};">
  <div class="strap" style="color:{acc};">Scorecard</div>
  <h3>{brand}</h3><table>{rows_html}</table></div>""",
                unsafe_allow_html=True,
            )

    section_h2("Access-tier mix", accent=SEC["compare"])
    chart_caption("Share of each brand's policies in each access tier. More green = lighter management; more red/orange = tighter.")
    tier_data = []
    for b in selected_brands:
        sub = df[df["Brand"] == b]
        if len(sub) == 0:
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
        apply_layout(fig_tier, barmode="stack", height=max(220, 50 * len(selected_brands) + 80),
                     xaxis=dict(range=[0, 100], ticksuffix="%", title="Share of policies",
                                title_font=dict(size=12, color=INK_SOFT)),
                     yaxis=dict(title=""),
                     legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        st.plotly_chart(fig_tier, use_container_width=True, config={"displayModeBar": False})

    section_h2("Head-to-head · TREMFYA vs STELARA",
               "Inside the same payer policy, which brand is treated more favourably?",
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
        chart_caption(f"Each line is one of the <b>{len(pivot)}</b> policies covering both brands. "
                      f"Dot position = access score; a wider gap means the policy favours one brand more strongly.")
        fig_pair = go.Figure()
        for _, r in pivot.iterrows():
            fig_pair.add_trace(go.Scatter(x=[r["STELARA"], r["TREMFYA"]],
                                          y=[r["Policy #"], r["Policy #"]], mode="lines",
                                          line=dict(color=LINE, width=2), showlegend=False, hoverinfo="skip"))
        fig_pair.add_trace(go.Scatter(x=pivot["STELARA"], y=pivot["Policy #"], mode="markers", name="STELARA",
                                      marker=dict(color=STELARA_C, size=13, line=dict(color="#FFFFFF", width=1.5)),
                                      hovertemplate="<b>STELARA</b><br>%{y}<br>%{x:.0f} pts<extra></extra>"))
        fig_pair.add_trace(go.Scatter(x=pivot["TREMFYA"], y=pivot["Policy #"], mode="markers", name="TREMFYA",
                                      marker=dict(color=TREMFYA_C, size=13, line=dict(color="#FFFFFF", width=1.5)),
                                      hovertemplate="<b>TREMFYA</b><br>%{y}<br>%{x:.0f} pts<extra></extra>"))
        apply_layout(fig_pair, height=max(280, 30 * len(pivot) + 80),
                     xaxis=dict(range=[-5, 105], title="Access Score (pts)",
                                tickvals=[0, 25, 50, 75, 100], title_font=dict(size=12, color=INK_SOFT)),
                     yaxis=dict(title=""), legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        st.plotly_chart(fig_pair, use_container_width=True, config={"displayModeBar": False})
        t_h = int((pivot["delta"] > 0).sum()); s_h = int((pivot["delta"] < 0).sum())
        tie = int((pivot["delta"] == 0).sum())
        avg_d = pivot["delta"].mean()
        cc = st.columns(3)
        insight_tile(cc[0], "TREMFYA favoured", f"<b>{t_h} of {len(pivot)}</b> shared policies score TREMFYA higher.", accent=TREMFYA_C)
        insight_tile(cc[1], "STELARA favoured", f"<b>{s_h} of {len(pivot)}</b> shared policies score STELARA higher{f' · {tie} tied' if tie else ''}.", accent=STELARA_C)
        insight_tile(cc[2], "Average gap", f"TREMFYA vs STELARA within-policy: <b>{avg_d:+.0f} pts</b>.", accent=SEC["compare"])
    else:
        st.info("Not enough policies cover both TREMFYA and STELARA under the current filters for a paired view.")

# ----------------------------------------------------------------------------
#  TAB 4 — ACCESS DRIVERS
# ----------------------------------------------------------------------------
with tab4:
    section_h2("Restriction patterns",
               "The prior-authorization controls payers apply most often.", accent=SEC["drivers"])
    chart_caption("Share of policies imposing each control, by brand. The controls higher up are the most common.")
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
    apply_layout(fig_r, height=max(340, 50 * len(order) + 60), barmode="group",
                 xaxis=dict(range=[0, 105], ticksuffix="%", title="Share of policies",
                            title_font=dict(size=12, color=INK_SOFT)),
                 yaxis=dict(title=""), legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), bargap=0.18)
    st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})

    section_h2("Step-therapy intensity",
               "How many therapies a patient must try first — the biggest single driver of access.",
               accent=SEC["drivers"])
    chart_caption("Count of required prior therapies per policy. <b>More steps = tighter access</b> (bars shaded red as steps rise).")
    step_rows = []
    for b in selected_brands:
        sub = df[df["Brand"] == b].dropna(subset=["Total Steps"])
        for _, r in sub.iterrows():
            step_rows.append({"Brand": b, "Steps": int(r["Total Steps"])})
    step_df = pd.DataFrame(step_rows)
    if not step_df.empty:
        all_steps = list(range(0, int(step_df["Steps"].max()) + 1))
        # Aggregate, colour each step-count bucket by restrictiveness ramp.
        agg = step_df.groupby("Steps").size().reindex(all_steps, fill_value=0)
        fig_steps = go.Figure(go.Bar(
            x=agg.index, y=agg.values,
            marker=dict(color=[RESTRICT_RAMP[min(s, len(RESTRICT_RAMP) - 1)] for s in agg.index],
                        line=dict(color="#FFFFFF", width=0.5)),
            hovertemplate="%{x} prior step(s) · %{y} policies<extra></extra>"))
        apply_layout(fig_steps, height=300,
                     xaxis=dict(title="Required prior therapies", dtick=1,
                                title_font=dict(size=12, color=INK_SOFT)),
                     yaxis=dict(title="Policies", title_font=dict(size=12, color=INK_SOFT)),
                     showlegend=False, bargap=0.25)
        st.plotly_chart(fig_steps, use_container_width=True, config={"displayModeBar": False})

    section_h2("Authorization windows",
               "Approval cycle length — shorter windows mean more frequent reauthorization touchpoints.",
               accent=SEC["drivers"])
    chart_caption("Median months for initial approval and reauthorization, by brand. Longer = lighter ongoing burden.")
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
#  TAB 5 — METHODOLOGY
# ----------------------------------------------------------------------------
with tab5:
    section_h2("How the access score works",
               "A 0–100 index anchored to the FDA label. Deterministic and auditable — every point traces to a policy fact.",
               accent=SEC["method"])

    st.markdown('<div style="height:2px"></div>', unsafe_allow_html=True)
    rungs = [
        ("100", "Open", ACCESS_TIER_COLOR["Open"], "Covered, no meaningful management — effectively unrestricted."),
        ("75", "Preferred", ACCESS_TIER_COLOR["Preferred"], "Covered, lighter than the FDA label (e.g. no step therapy)."),
        ("50", "Parity", ACCESS_TIER_COLOR["Parity"], "Mirrors the FDA label — one conventional step, standard reauth."),
        ("25", "Restricted", ACCESS_TIER_COLOR["Restricted"], "Tighter than the label — typically biologic step-through."),
        ("0", "No access", ACCESS_TIER_COLOR["No access"], "Not covered / excluded for plaque psoriasis."),
    ]
    ladder = "".join(
        f"""<div class="zs-rung" style="background:{c};">
              <div class="pts">{p}</div><div class="nm">{n}</div><div class="ds">{d}</div></div>"""
        for p, n, c, d in rungs)
    st.markdown(ladder, unsafe_allow_html=True)
    st.markdown(
        f"""<div class="zs-obs" style="border-left-color:{SEC['method']}; margin-top:4px;">
        <div class="zs-obs-tag" style="color:{SEC['method']};">Reading the score</div>
        <div class="zs-obs-text">The number is an <b>access-restrictiveness index versus the FDA label</b>, not a quality grade.
        <b>50 = parity.</b> Points are added toward 75–100 when a policy is lighter than the label, and deducted toward 25–0 for each
        added barrier — with <b>biologic step-through</b> the dominant deduction.</div></div>""",
        unsafe_allow_html=True)

    section_h2("The three-stage logic", accent=SEC["method"])
    sc = st.columns(3)
    stages = [
        ("Stage 1 · Coverage gate", "#B91C1C",
         "Covered for PsO? If excluded → <b>0</b> and scoring stops. 0 is reserved for genuine non-access."),
        ("Stage 2 · Step-therapy anchor", "#CA8A04",
         "The binding constraint sets the tier. <b>Any biologic step → 25.</b> Conventional/phototherapy step → <b>50</b>. No step → <b>75</b>."),
        ("Stage 3 · Secondary burden", "#16A34A",
         "Specialist gating, below-label quantity limits, short reauth and extra steps each nudge the anchor down. <b>TB testing is never penalised.</b>"),
    ]
    for col, (t, c, d) in zip(sc, stages):
        col.markdown(
            f"""<div class="zs-arch" style="border-top-color:{c}; height:100%;">
              <div class="name" style="color:{c};">{t}</div>
              <div class="desc">{d}</div></div>""",
            unsafe_allow_html=True)

    section_h2("Score simulator",
               "Set a hypothetical policy's controls and watch the score resolve live — the exact logic behind every record.",
               accent=SEC["method"])
    control_hint("Interactive · adjust the inputs")
    sim_in, sim_out = st.columns([1.05, 1])
    with sim_in:
        covered = st.toggle("Covered for plaque psoriasis", value=True)
        cb1, cb2 = st.columns(2)
        with cb1:
            b_steps = st.select_slider("Biologic steps", options=[0, 1, 2, 3], value=0)
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
            number=dict(font=dict(size=46, color=INK, family="Fraunces"), suffix=" pts"),
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

    section_h2("Where to act", "Priorities for the brand and field team.", accent=SEC["method"])
    ic = st.columns(2)
    insights = [
        ("Target the binding constraint", SEC["drivers"],
         "Removing one biologic step moves a policy from Restricted (25) to Parity (50) — a bigger gain than any number of minor concessions."),
        ("Account-led, not brand-led", SEC["compare"],
         "Access varies more across payers than across brands. Prioritise accounts at the Restricted / No-access end, where upside is concentrated."),
        ("Don't over-state open access", SEC["method"],
         "A sparse policy is held at Parity, never promoted to Preferred/Open — a conservative posture that avoids over-claiming access."),
        ("Administrative burden as a soft lever", SEC["param"],
         "Short reauth windows and specialist gating raise abandonment risk without blocking access — quick wins for patient-services programmes."),
    ]
    for i, (t, c, d) in enumerate(insights):
        insight_tile(ic[i % 2], t, d, accent=c)

# ----------------------------------------------------------------------------
#  TAB 6 — POLICY EXPLORER
# ----------------------------------------------------------------------------
with tab6:
    section_h2("Policy explorer",
               "Open any single policy to see its full extracted parameter set.",
               accent=SEC["explorer"])

    # Aligned view-control strip (labels above each control keep them on one baseline).
    control_hint("View control · this tab only")
    nav1, nav2 = st.columns([1, 2])
    with nav1:
        explore_brand = st.selectbox("Brand", options=selected_brands, index=0)
    with nav2:
        sort_choice = st.selectbox(
            "Sort by",
            options=["Most restrictive first", "Most open first", "Policy ID"],
            index=0,
        )
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
            return f"{row['Policy #']}  ·  {score} pts  ·  {row['Access Tier']}"
        sub["__label"] = sub.apply(policy_label, axis=1)

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

        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

        GROUPS = [
            ("Eligibility & screening", "#2563EB", [
                ("Age criterion", lambda r: r["Age Criterion"]),
                ("Specialist", lambda r: r["Specialist Detail"]),
                ("TB test", lambda r: r["TB Test"]),
            ]),
            ("Step therapy", "#D97706", [
                ("Step therapy", lambda r: r["Step Therapy"]),
                ("Biologic steps", lambda r: f"{int(r['Brand Steps'])}" if pd.notna(r['Brand Steps']) else "—"),
                ("Conventional steps", lambda r: f"{int(r['Generic Steps'])}" if pd.notna(r['Generic Steps']) else "—"),
                ("Phototherapy step", lambda r: r["Phototherapy Step"]),
            ]),
            ("Utilization & duration", "#0D9488", [
                ("Quantity limit", lambda r: r["Quantity Limit"]),
                ("Initial authorization", lambda r: (f"{int(r['Initial Auth (months)'])} months"
                                                     if pd.notna(r['Initial Auth (months)'])
                                                     else str(r.get('Initial Authorization Duration(in-months)') or '—'))),
                ("Reauthorization", lambda r: (f"{int(r['Reauth (months)'])} months"
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
                    f"""<div style="background:{CARD}; border:1px solid {LINE}; border-top:5px solid {bcol};
            border-radius:6px; padding:15px 18px; margin-bottom:11px;">
  <div style="font-size:10px; letter-spacing:0.14em; text-transform:uppercase;
              color:{bcol}; font-weight:700;">{row['Brand']} · {row['Policy #']}</div>
  <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
    <div>
      <div style="font-family:'Fraunces',serif; font-size:32px; font-weight:600; color:{INK}; line-height:1;">
        {score_html}<span style="font-size:13px; color:{SLATE}; font-family:Manrope; margin-left:6px;">/ 100 pts</span></div>
      <div style="font-size:10.5px; color:{SLATE}; margin-top:4px; letter-spacing:0.08em;
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
                    with st.expander("Reauthorization language (verbatim)"):
                        st.write(reauth_text)
                if pd.notna(qty_text) and len(str(qty_text).strip()) > 6 and str(qty_text).strip().lower() not in ("no", "nan"):
                    with st.expander("Quantity-limit language (verbatim)"):
                        st.write(qty_text)
                with st.expander("Source policy file"):
                    st.code(row["Policy ID"] + ".pdf", language="text")

# ============================================================================
#  FOOTER
# ============================================================================
st.markdown(
    f"""<div class="zs-footer">
  <span>ZS · Market Access · Plaque Psoriasis Policy Lens</span>
  <span>{df_all['Policy ID'].nunique()} policies · {len(ALL_BRANDS)} brands · TREMFYA & STELARA in focus</span>
</div>""",
    unsafe_allow_html=True,
)
