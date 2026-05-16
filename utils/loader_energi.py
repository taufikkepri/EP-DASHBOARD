"""
utils/loader_energi.py
ETL lengkap untuk Dashboard Monitoring Energi Primer PLTU
Fitur:
  - load_harian()   → data harian Coal, HSD, Biomassa + produksi
  - load_mingguan() → rekap mingguan KPI
  - load_target()   → target vs realisasi bulanan
  - tren_harian()   → agregasi tren harian per bahan bakar & KPI
  - prognosa()      → proyeksi konsumsi & stok akhir bulan
  - summary_stok()  → stok awal, penerimaan, konsumsi, stok akhir per bahan bakar
"""

import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path
from datetime import date, timedelta

DATA_PATH = Path(__file__).parent.parent / "data" / "energi_data.xlsx"

# ── Konstanta nilai kalor default ─────────────────────────────────────────────
GCV_COAL_DEFAULT  = 5000   # kCal/kg
GCV_HSD_PER_KL    = 8600   # kCal/liter → kCal/kL = 8.6 GCal/kL
GCV_BIO_PER_TON   = 3500   # kCal/kg → GCal/ton = 3.5

# ── Helper ─────────────────────────────────────────────────────────────────────
def _safe(val, default=0.0):
    try:
        v = float(val)
        return v if not np.isnan(v) else default
    except:
        return default

def _find_col(df, *keywords, exclude=None):
    """Cari kolom yang mengandung semua keyword (case-insensitive)."""
    for c in df.columns:
        cs = str(c).lower()
        if all(k.lower() in cs for k in keywords):
            if exclude and any(e.lower() in cs for e in exclude):
                continue
            return c
    return None

def _parse_header(df):
    """Kalau header masih di baris 1-2, geser."""
    if df.iloc[0].astype(str).str.contains("tanggal|date|tgl", case=False).any():
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]
    return df

# ════════════════════════════════════════════════════════════════════════════
# LOAD RAW SHEETS
# ════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def load_harian(src=None) -> pd.DataFrame:
    path = src or DATA_PATH
    df = pd.read_excel(path, sheet_name="1_Input_Harian", header=2)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(subset=[df.columns[0]])
    df = df[~df[df.columns[0]].astype(str).str.startswith(("⬆","Tanggal","nan"))]

    # Rename kolom ke key standar
    col_map = {
        _find_col(df, "tanggal"):             "tanggal",
        _find_col(df, "unit"):                "unit",
        # Coal
        _find_col(df, "penerimaan", "coal"):  "coal_rcv",
        _find_col(df, "konsumsi", "coal"):    "coal_con",
        _find_col(df, "stok", "awal", "coal"):"coal_stok_awal",
        _find_col(df, "stok", "akhir", "coal", exclude=["awal"]): "coal_stok_akhir",
        _find_col(df, "gcv"):                 "gcv",
        _find_col(df, "nilai", "kalor", "coal"): "coal_kal",
        # HSD
        _find_col(df, "penerimaan", "hsd"):   "hsd_rcv",
        _find_col(df, "konsumsi", "hsd"):     "hsd_con",
        _find_col(df, "stok", "awal", "hsd"): "hsd_stok_awal",
        _find_col(df, "stok", "akhir", "hsd", exclude=["awal"]): "hsd_stok_akhir",
        # Biomassa
        _find_col(df, "penerimaan", "bio"):   "bio_rcv",
        _find_col(df, "konsumsi", "bio"):     "bio_con",
        _find_col(df, "stok", "awal", "bio"): "bio_stok_awal",
        _find_col(df, "stok", "akhir", "bio", exclude=["awal"]): "bio_stok_akhir",
        # Produksi
        _find_col(df, "produksi", "netto"):   "produksi",
        _find_col(df, "beban", "rerata"):     "beban",
        _find_col(df, "heat", "rate"):        "heat_rate",
        _find_col(df, "sfc"):                 "sfc_coal",
    }
    col_map = {k: v for k, v in col_map.items() if k is not None}
    df = df.rename(columns=col_map)

    # Pastikan kolom standar ada meski kosong
    for col in ["tanggal","unit","coal_rcv","coal_con","coal_stok_awal","coal_stok_akhir",
                "gcv","coal_kal","hsd_rcv","hsd_con","hsd_stok_awal","hsd_stok_akhir",
                "bio_rcv","bio_con","bio_stok_awal","bio_stok_akhir",
                "produksi","beban","heat_rate","sfc_coal"]:
        if col not in df.columns:
            df[col] = np.nan

    # Parse types
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce", dayfirst=True)
    df["unit"]    = df["unit"].apply(_safe).astype(int)
    num_cols = [c for c in df.columns if c not in ["tanggal","unit"]]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Hitung stok akhir kalau masih kosong (fallback)
    for fuel, rcv, con, sa, se in [
        ("coal","coal_rcv","coal_con","coal_stok_awal","coal_stok_akhir"),
        ("hsd", "hsd_rcv", "hsd_con", "hsd_stok_awal", "hsd_stok_akhir"),
        ("bio", "bio_rcv", "bio_con", "bio_stok_awal", "bio_stok_akhir"),
    ]:
        mask = df[se].isna() & df[sa].notna()
        df.loc[mask, se] = df.loc[mask, sa] + df.loc[mask, rcv].fillna(0) - df.loc[mask, con].fillna(0)

    return df.reset_index(drop=True)


@st.cache_data(ttl=300)
def load_mingguan(src=None) -> pd.DataFrame:
    path = src or DATA_PATH
    df = pd.read_excel(path, sheet_name="2_Rekap_Mingguan", header=2)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(subset=[df.columns[0]])
    df = df[~df[df.columns[0]].astype(str).str.startswith("⬆")]
    for c in df.columns[2:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.reset_index(drop=True)


@st.cache_data(ttl=300)
def load_target(src=None) -> pd.DataFrame:
    path = src or DATA_PATH
    df = pd.read_excel(path, sheet_name="3_Target_vs_Realisasi", header=2)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(subset=[df.columns[0]])
    df = df[~df[df.columns[0]].astype(str).str.startswith("⬆")]
    return df.reset_index(drop=True)


# ════════════════════════════════════════════════════════════════════════════
# TREN HARIAN
# ════════════════════════════════════════════════════════════════════════════
def tren_harian(df: pd.DataFrame, unit_filter="Semua") -> pd.DataFrame:
    """
    Agregasi per hari (gabungan unit atau per unit).
    Return kolom: tanggal, coal_con, hsd_con, bio_con,
                  coal_stok_akhir, hsd_stok_akhir, bio_stok_akhir,
                  produksi, heat_rate, sfc_coal, rasio_co
    """
    d = df.copy()
    if unit_filter != "Semua":
        u = int(str(unit_filter).replace("Unit","").strip())
        d = d[d["unit"] == u]

    grp = d.groupby("tanggal").agg(
        coal_con    =("coal_con",    "sum"),
        hsd_con     =("hsd_con",     "sum"),
        bio_con     =("bio_con",     "sum"),
        coal_rcv    =("coal_rcv",    "sum"),
        hsd_rcv     =("hsd_rcv",     "sum"),
        bio_rcv     =("bio_rcv",     "sum"),
        coal_stok_akhir=("coal_stok_akhir","mean"),
        hsd_stok_akhir =("hsd_stok_akhir", "mean"),
        bio_stok_akhir =("bio_stok_akhir",  "mean"),
        produksi    =("produksi",    "sum"),
        heat_rate   =("heat_rate",   "mean"),
        sfc_coal    =("sfc_coal",    "mean"),
        gcv         =("gcv",         "mean"),
    ).reset_index()

    # Rasio co-firing harian
    total_fuel = grp["coal_con"] + grp["bio_con"]
    grp["rasio_co"] = np.where(total_fuel > 0, grp["bio_con"] / total_fuel * 100, 0)

    # Moving average 7 hari untuk smoothing
    for col in ["coal_con","hsd_con","bio_con","heat_rate","sfc_coal"]:
        grp[f"{col}_ma7"] = grp[col].rolling(7, min_periods=1).mean()

    return grp.sort_values("tanggal").reset_index(drop=True)


# ════════════════════════════════════════════════════════════════════════════
# PROGNOSA (Proyeksi akhir bulan)
# ════════════════════════════════════════════════════════════════════════════
def prognosa(df: pd.DataFrame, unit_filter="Semua") -> dict:
    """
    Hitung proyeksi konsumsi & stok akhir bulan berdasarkan:
    - Rerata konsumsi harian (7 hari terakhir)
    - Sisa hari dalam bulan berjalan
    Return dict berisi proyeksi per bahan bakar.
    """
    tr = tren_harian(df, unit_filter)
    if tr.empty:
        return {}

    today = tr["tanggal"].max()
    if pd.isnull(today):
        return {}

    # Sisa hari bulan ini
    if isinstance(today, pd.Timestamp):
        today = today.date()
    last_day = date(today.year, today.month + 1 if today.month < 12 else 1,
                    1) - timedelta(days=1)
    if today.month == 12:
        last_day = date(today.year, 12, 31)
    sisa_hari = (last_day - today).days

    # Rerata 7 hari terakhir
    last7 = tr.tail(7)
    avg = {
        "coal": last7["coal_con"].mean(),
        "hsd":  last7["hsd_con"].mean(),
        "bio":  last7["bio_con"].mean(),
        "prod": last7["produksi"].mean(),
        "hr":   last7["heat_rate"].mean(),
    }

    # Stok akhir terakhir
    last_row = tr.iloc[-1]
    stok_now = {
        "coal": _safe(last_row["coal_stok_akhir"]),
        "hsd":  _safe(last_row["hsd_stok_akhir"]),
        "bio":  _safe(last_row["bio_stok_akhir"]),
    }

    # Proyeksi
    proj_con = {k: avg[k] * sisa_hari for k in ["coal","hsd","bio"]}
    proj_stok_akhir = {k: stok_now[k] - proj_con[k] for k in ["coal","hsd","bio"]}
    proj_prod = avg["prod"] * sisa_hari
    proj_hr   = avg["hr"]

    # Total bulan (realisasi + proyeksi)
    hari_terdata = len(tr)
    real_con = {
        "coal": tr["coal_con"].sum(),
        "hsd":  tr["hsd_con"].sum(),
        "bio":  tr["bio_con"].sum(),
    }

    return {
        "today":        today,
        "last_day":     last_day,
        "sisa_hari":    sisa_hari,
        "hari_terdata": hari_terdata,
        "avg_harian":   avg,
        "stok_sekarang":stok_now,
        "proj_con_sisa":proj_con,
        "proj_stok_akhir": proj_stok_akhir,
        "proj_prod_sisa":  proj_prod,
        "proj_hr":         proj_hr,
        "real_con_ytm":    real_con,
        "proj_total_bulan":{
            "coal": real_con["coal"] + proj_con["coal"],
            "hsd":  real_con["hsd"]  + proj_con["hsd"],
            "bio":  real_con["bio"]  + proj_con["bio"],
        },
    }


# ════════════════════════════════════════════════════════════════════════════
# SUMMARY STOK (Stok Awal, Penerimaan, Konsumsi, Stok Akhir)
# ════════════════════════════════════════════════════════════════════════════
def summary_stok(df: pd.DataFrame, unit_filter="Semua") -> dict:
    """
    Rekap stok periode data:
      stok_awal    = stok awal baris pertama
      total_rcv    = total penerimaan
      total_con    = total konsumsi
      stok_akhir   = stok akhir baris terakhir
      hari_pakai   = proyeksi sisa hari berdasarkan avg konsumsi 7 hari
    """
    d = df.copy()
    if unit_filter != "Semua":
        u = int(str(unit_filter).replace("Unit","").strip())
        d = d[d["unit"] == u]

    if d.empty:
        return {}

    def _stok_summary(rcv_col, con_col, sa_col, se_col, unit_label):
        stok_awal  = _safe(d[sa_col].dropna().iloc[0]) if d[sa_col].dropna().any() else 0
        total_rcv  = d[rcv_col].apply(_safe).sum()
        total_con  = d[con_col].apply(_safe).sum()
        stok_akhir = _safe(d[se_col].dropna().iloc[-1]) if d[se_col].dropna().any() else (stok_awal + total_rcv - total_con)
        avg7       = d[con_col].apply(_safe).tail(7).mean()
        hari_pakai = round(stok_akhir / avg7, 1) if avg7 > 0 else 0

        return {
            "stok_awal":  stok_awal,
            "total_rcv":  total_rcv,
            "total_con":  total_con,
            "stok_akhir": stok_akhir,
            "avg_harian": round(avg7, 2),
            "hari_pakai": hari_pakai,
        }

    return {
        "coal": _stok_summary("coal_rcv","coal_con","coal_stok_awal","coal_stok_akhir","ton"),
        "hsd":  _stok_summary("hsd_rcv", "hsd_con", "hsd_stok_awal", "hsd_stok_akhir","kL"),
        "bio":  _stok_summary("bio_rcv",  "bio_con", "bio_stok_awal", "bio_stok_akhir","ton"),
    }


# ════════════════════════════════════════════════════════════════════════════
# HELPER: KPI OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
def kpi_overview(df: pd.DataFrame, unit_filter="Semua") -> dict:
    d = df.copy()
    if unit_filter != "Semua":
        u = int(str(unit_filter).replace("Unit","").strip())
        d = d[d["unit"] == u]

    total_prod = d["produksi"].apply(_safe).sum()
    avg_hr     = d["heat_rate"].apply(_safe).replace(0, np.nan).mean()
    avg_sfc    = d["sfc_coal"].apply(_safe).replace(0, np.nan).mean()
    total_coal = d["coal_con"].apply(_safe).sum()
    total_hsd  = d["hsd_con"].apply(_safe).sum()
    total_bio  = d["bio_con"].apply(_safe).sum()
    total_fuel = total_coal + total_bio
    rasio_co   = total_bio / total_fuel * 100 if total_fuel > 0 else 0

    return {
        "total_prod": round(total_prod, 1),
        "avg_hr":     round(_safe(avg_hr), 0),
        "avg_sfc":    round(_safe(avg_sfc), 3),
        "total_coal": round(total_coal, 1),
        "total_hsd":  round(total_hsd, 2),
        "total_bio":  round(total_bio, 1),
        "rasio_co":   round(rasio_co, 2),
    }
