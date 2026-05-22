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
    """
    Cari kolom yang mengandung semua keyword (case-insensitive).
    Normalisasi newline dan bracket keterangan sebelum matching,
    supaya kolom seperti 'Stok Awal\nCoal (ton)\n[isi hari-1]' tetap terdeteksi.
    """
    import re as _re
    for c in df.columns:
        cs = _re.sub(r'\[.*?\]', ' ', str(c))
        cs = _re.sub(r'[\n\r]+', ' ', cs)
        cs = _re.sub(r'\s+', ' ', cs).strip().lower()
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

    # ── Deteksi format stok — 2 kemungkinan format Excel:
    # Format A (template ane): kolom "Stok Awal" dan "Stok Akhir" terpisah
    # Format B (format user):  hanya kolom "Stok Coal/HSD/Bio" (= stok akhir, awal dihitung)
    def _stok(fuel, mode):
        if mode == "awal":
            # Cari kolom yang ada kata "stok" + "awal" + nama fuel
            return _find_col(df, "stok", "awal", fuel)
        else:
            # Cari kolom stok akhir:
            # Format A: "Stok Akhir Coal" → keyword "stok","akhir","fuel"
            # Format B: "Stok Coal [otomatis]" → keyword "stok","fuel" exclude "awal"
            col = _find_col(df, "stok", "akhir", fuel)
            if col:
                return col
            # Format B: pakai exclude awal supaya tidak keambil kolom stok awal
            return _find_col(df, "stok", fuel, exclude=["awal"])

    # Deteksi satuan HSD — bisa kL atau L (liter)
    hsd_stk_col = _stok("hsd", "akhir")
    hsd_con_col = _find_col(df, "konsumsi", "hsd")
    hsd_rcv_col = _find_col(df, "penerimaan", "hsd")
    _hsd_is_liter = False
    for _c in [hsd_stk_col, hsd_con_col, hsd_rcv_col]:
        if _c and "(l)" in str(_c).lower() and "kl" not in str(_c).lower():
            _hsd_is_liter = True
            break

    # Deteksi satuan Produksi — MWh atau kWh
    prod_col = _find_col(df, "produksi", "netto") or _find_col(df, "produksi")
    _prod_is_kwh = bool(prod_col and "kwh" in str(prod_col).lower()
                        and "mwh" not in str(prod_col).lower())

    # Rename kolom ke key standar
    col_map = {
        _find_col(df, "tanggal"):             "tanggal",
        _find_col(df, "unit"):                "unit",
        # Coal
        _find_col(df, "penerimaan", "coal"):  "coal_rcv",
        _find_col(df, "konsumsi", "coal"):    "coal_con",
        _stok("coal", "awal"):                "coal_stok_awal",
        _stok("coal", "akhir"):               "coal_stok_akhir",
        _find_col(df, "gcv"):                 "gcv",
        _find_col(df, "nilai", "kalor", "coal"): "coal_kal",
        # HSD
        hsd_rcv_col:                          "hsd_rcv",
        hsd_con_col:                          "hsd_con",
        _stok("hsd", "awal"):                 "hsd_stok_awal",
        hsd_stk_col:                          "hsd_stok_akhir",
        # Biomassa
        _find_col(df, "penerimaan", "bio"):   "bio_rcv",
        _find_col(df, "konsumsi", "bio"):     "bio_con",
        _stok("bio", "awal"):                 "bio_stok_awal",
        _stok("bio", "akhir"):                "bio_stok_akhir",
        # Produksi
        prod_col:                             "produksi",
        _find_col(df, "beban", "rerata"):     "beban",
        _find_col(df, "heat", "rate"):        "heat_rate",
        _find_col(df, "sfc"):                 "sfc_coal",
    }
    col_map = {k: v for k, v in col_map.items() if k is not None}
    df = df.rename(columns=col_map)

    # ── Konversi satuan otomatis ────────────────────────────────────────────
    # Produksi: kWh → MWh (÷1000)
    if _prod_is_kwh and "produksi" in df.columns:
        df["produksi"] = pd.to_numeric(df["produksi"], errors="coerce").fillna(0) / 1000.0

    # HSD: Liter → kL (÷1000) jika kolom header pakai satuan (L)
    # Contoh: 10.760 L = 10.76 kL, konsumsi 2.890 L = 2.89 kL
    if _hsd_is_liter:
        for col in ["hsd_rcv", "hsd_con", "hsd_stok_awal", "hsd_stok_akhir"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0) / 1000.0

    # ── Hitung Stok Akhir jika kolom formula belum terhitung (None/NaN) ─────
    # Terjadi saat Excel dibaca tanpa Excel engine yang bisa eval formula
    # Rumus: Stok Akhir = Stok Awal + Penerimaan - Konsumsi
    for fuel, sa, se, rcv, con in [
        ("coal", "coal_stok_awal", "coal_stok_akhir", "coal_rcv", "coal_con"),
        ("hsd",  "hsd_stok_awal",  "hsd_stok_akhir",  "hsd_rcv",  "hsd_con"),
        ("bio",  "bio_stok_awal",  "bio_stok_akhir",  "bio_rcv",  "bio_con"),
    ]:
        if se not in df.columns:
            df[se] = 0.0
        # Cek apakah stok akhir semua kosong/NaN
        if df[se].apply(_safe).sum() == 0 and sa in df.columns:
            # Hitung rolling stok akhir per unit
            unit_col_name = "unit" if "unit" in df.columns else None
            units = df[unit_col_name].dropna().unique() if unit_col_name else [None]
            for uid in units:
                mask = (df[unit_col_name] == uid) if unit_col_name else pd.Series([True]*len(df), index=df.index)
                idx_list = df[mask].index.tolist()
                if not idx_list: continue
                stk = _safe(df.loc[idx_list[0], sa])  # stok awal baris pertama
                for i, row_idx in enumerate(idx_list):
                    rcv_val = _safe(df.loc[row_idx, rcv]) if rcv in df.columns else 0
                    con_val = _safe(df.loc[row_idx, con]) if con in df.columns else 0
                    stk_awal_row = _safe(df.loc[row_idx, sa]) if i == 0 else stk
                    stk = stk_awal_row + rcv_val - con_val
                    df.loc[row_idx, se] = round(stk, 3)
                    if i < len(idx_list) - 1:
                        # Update stok awal baris berikutnya
                        next_idx = idx_list[i+1]
                        df.loc[next_idx, sa] = round(stk, 3)

    # Stok awal Format B: hitung dari stok akhir + konsumsi - penerimaan
    # Dijalankan setelah rename & numeric conversion selesai
    for fuel in ["coal", "hsd", "bio"]:
        sa = f"{fuel}_stok_awal"
        se = f"{fuel}_stok_akhir"
        con = f"{fuel}_con"
        rcv = f"{fuel}_rcv"
        # Hanya proses jika stok_awal belum ada atau semua 0
        if se in df.columns and (sa not in df.columns or df[sa].fillna(0).sum() == 0):
            if sa not in df.columns:
                df[sa] = 0.0
            # Hitung per unit
            unit_col_name = "unit" if "unit" in df.columns else None
            units = df[unit_col_name].dropna().unique() if unit_col_name else [None]
            for uid in units:
                if uid is None:
                    mask = pd.Series([True] * len(df), index=df.index)
                else:
                    mask = df[unit_col_name] == uid
                idx = df[mask].index.tolist()
                if not idx: continue
                stk  = df.loc[idx, se].apply(_safe).values
                kon_ = df.loc[idx, con].apply(_safe).values if con in df.columns else np.zeros(len(idx))
                rcv_ = df.loc[idx, rcv].apply(_safe).values if rcv in df.columns else np.zeros(len(idx))
                # Stok awal hari-1 = stok_akhir[0] + konsumsi[0] - penerimaan[0]
                # Stok awal hari-n = stok_akhir[n-1]
                awal = np.concatenate([[stk[0] + kon_[0] - rcv_[0]], stk[:-1]])
                df.loc[idx, sa] = awal

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

    if "tanggal" not in d.columns or d.empty:
        return pd.DataFrame()
    # Pastikan kolom numerik ada semua
    for _col in ["coal_con","hsd_con","bio_con","coal_rcv","hsd_rcv","bio_rcv",
                 "coal_stok_akhir","hsd_stok_akhir","bio_stok_akhir",
                 "produksi","heat_rate","sfc_coal","gcv"]:
        if _col not in d.columns:
            d[_col] = 0.0
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
    Rekap stok per bahan bakar:
      stok_awal    = total stok awal hari pertama (Unit 1 + Unit 2)
      total_rcv    = total penerimaan periode
      total_con    = total konsumsi periode
      stok_akhir   = total stok akhir hari terakhir
      avg_con_hari = rata-rata konsumsi per hari
      hari_pakai   = estimasi hari bertahan (stok_akhir / avg_con_hari)
      status       = 🟢 AMAN / 🟡 WASPADA / 🔴 KRITIS
    """
    d = df.copy()
    if unit_filter != "Semua":
        u = int(str(unit_filter).replace("Unit","").strip())
        d = d[d["unit"] == u]

    if d.empty:
        return {}

    hasil = {}
    tren = tren_harian(d, unit_filter="Semua")

    for fuel, sa, se, rcv, con, min_stok, satuan in [
        ("coal", "coal_stok_awal", "coal_stok_akhir", "coal_rcv", "coal_con", 5000, "MT"),
        ("hsd",  "hsd_stok_awal",  "hsd_stok_akhir",  "hsd_rcv",  "hsd_con",   10, "kL"),
        ("bio",  "bio_stok_awal",  "bio_stok_akhir",  "bio_rcv",  "bio_con",    50, "ton"),
    ]:
        # Stok awal = jumlah stok awal baris pertama per unit
        if sa in d.columns and d[sa].apply(_safe).sum() > 0:
            if "unit" in d.columns and unit_filter == "Semua":
                stok_awal = sum(
                    _safe(d[d["unit"]==u][sa].dropna().iloc[0])
                    for u in d["unit"].dropna().unique()
                    if not d[d["unit"]==u][sa].dropna().empty
                )
            else:
                stok_awal = _safe(d[sa].dropna().iloc[0])
        else:
            stok_awal = 0.0

        # Total penerimaan & konsumsi
        total_rcv = d[rcv].apply(_safe).sum() if rcv in d.columns else 0
        total_con = d[con].apply(_safe).sum() if con in d.columns else 0

        # Stok akhir = jumlah stok akhir baris terakhir per unit
        if se in d.columns and d[se].apply(_safe).sum() != 0:
            if "unit" in d.columns and unit_filter == "Semua":
                stok_akhir = sum(
                    _safe(d[d["unit"]==u][se].dropna().iloc[-1])
                    for u in d["unit"].dropna().unique()
                    if not d[d["unit"]==u][se].dropna().empty
                )
            else:
                stok_akhir = _safe(d[se].dropna().iloc[-1])
        else:
            # Hitung dari stok awal + rcv - con
            stok_akhir = stok_awal + total_rcv - total_con

        # Avg konsumsi per hari (dari tren)
        avg_con = float(tren[con].mean()) if con in tren.columns and tren[con].mean() > 0 else (
                  total_con / max(len(tren), 1))

        # Estimasi hari bertahan
        hari_pakai = round(stok_akhir / avg_con, 1) if avg_con > 0 else 0

        # Status
        if stok_akhir <= 0:
            status = "🔴 KRITIS"
        elif stok_akhir < min_stok:
            status = "🟡 WASPADA"
        elif stok_akhir < min_stok * 1.5:
            status = "🟡 MENDEKATI MINIMUM"
        else:
            status = "🟢 AMAN"

        hasil[fuel] = {
            "stok_awal":   round(stok_awal, 2),
            "total_rcv":   round(total_rcv, 2),
            "total_con":   round(total_con, 2),
            "stok_akhir":  round(stok_akhir, 2),
            "avg_con_hari":round(avg_con, 2),
            "hari_pakai":  hari_pakai,
            "status":      status,
            "satuan":      satuan,
            "min_stok":    min_stok,
        }

    return hasil


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
