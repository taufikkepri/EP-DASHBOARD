"""
app.py — Dashboard Monitoring Energi Primer PLTU
Jalankan: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

st.set_page_config(
    page_title="Energi Primer PLTU",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif}
[data-testid="stSidebar"]{background:#1F4E79;color:white}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,
[data-testid="stSidebar"] .stMarkdown{color:#CADDF2!important}
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#fff!important}
.kpi{background:white;border-radius:10px;padding:14px 18px;border-left:4px solid #1F4E79;box-shadow:0 1px 4px rgba(0,0,0,.07)}
.kpi-label{font-size:10px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:#6B7280;margin-bottom:4px}
.kpi-val{font-size:26px;font-weight:600;line-height:1}
.kpi-sub{font-size:11px;color:#9CA3AF;margin-top:3px}
.sec{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:#6B7280;border-bottom:1px solid #E5E7EB;padding-bottom:5px;margin-bottom:10px}
.topbar{background:linear-gradient(135deg,#1F4E79,#2E6DA4);border-radius:12px;padding:18px 26px;margin-bottom:18px;color:white}
.topbar h1{font-size:20px;font-weight:600;margin:0;color:white}
.topbar p{font-size:12px;color:#CADDF2;margin:3px 0 0}
.fuel-coal{color:#2C2C2C;font-weight:600}
.fuel-hsd{color:#B8860B;font-weight:600}
.fuel-gas{color:#1565C0;font-weight:600}
.fuel-bio{color:#2E7D32;font-weight:600}
.status-ok{background:#E8F5E9;color:#2E7D32;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
.status-dev{background:#FFF8E1;color:#F57F17;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
</style>
""", unsafe_allow_html=True)

FUEL_COLORS = {
    "Coal": "#2C2C2C", "HSD": "#B8860B", "Biomassa": "#2E7D32"
}

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data(src):
    sheets = pd.read_excel(src, sheet_name=None)
    df_h = sheets.get("1_Input_Harian", pd.DataFrame())
    df_w = sheets.get("2_Rekap_Mingguan", pd.DataFrame())
    df_t = sheets.get("3_Target_vs_Realisasi", pd.DataFrame())

    if not df_h.empty:
        df_h.columns = df_h.iloc[1]; df_h = df_h.iloc[2:].reset_index(drop=True)
        df_h.columns = [str(c).strip() for c in df_h.columns]
        df_h = df_h.dropna(subset=[df_h.columns[0]])

    if not df_w.empty:
        df_w.columns = df_w.iloc[1]; df_w = df_w.iloc[2:].reset_index(drop=True)
        df_w.columns = [str(c).strip() for c in df_w.columns]
        df_w = df_w.dropna(subset=[df_w.columns[0]])

    if not df_t.empty:
        df_t.columns = df_t.iloc[1]; df_t = df_t.iloc[2:].reset_index(drop=True)
        df_t.columns = [str(c).strip() for c in df_t.columns]
        df_t = df_t.dropna(subset=[df_t.columns[0]])
    return df_h, df_w, df_t


def safe_num(val, default=0):
    try: return float(val)
    except: return default


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ Energi Primer\n### Monitoring Dashboard")
    st.markdown("---")
    uploaded = st.file_uploader("📂 Upload Excel (.xlsx)", type=["xlsx"])
    st.markdown("---")
    st.markdown("### Filter")
    sel_unit = st.selectbox("Unit PLTU", ["Semua", "Unit 1", "Unit 2"])
    page = st.radio("Halaman", [
        "📊 Overview",
        "🪨 Coal",
        "⛽ HSD",
        "🌿 Biomassa",
        "📈 Target vs Realisasi",
        "📉 Tren & Analisis",
    ])
    st.markdown("---")
    st.caption("Energi Primer Dashboard v1.0\nPLTU Unit 1 & 2")

DATA_PATH = Path("data/energi_data.xlsx")
src = uploaded if uploaded else (DATA_PATH if DATA_PATH.exists() else None)

if src is None:
    st.warning("Upload file Excel template Energi Primer untuk memulai.")
    st.stop()

df_h, df_w, df_t = load_data(src)

# ── Helper: quick KPI card ─────────────────────────────────────────────────────
def kpi_card(col, label, val, unit, sub, color="#1F4E79"):
    with col:
        st.markdown(f"""
        <div class="kpi" style="border-left-color:{color}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-val" style="color:{color}">{val} <span style="font-size:13px;color:#9CA3AF">{unit}</span></div>
            <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
if page == "📊 Overview":
    st.markdown("""
    <div class="topbar">
        <h1>⚡ Dashboard Monitoring Energi Primer</h1>
        <p>PLTU Unit 1 & 2 · Coal · HSD · Biomassa</p>
    </div>""", unsafe_allow_html=True)

    # KPI row — ambil dari rekap mingguan terakhir (semua unit)
    if not df_w.empty:
        last = df_w.iloc[-2:]  # 2 baris terakhir = 2 unit minggu terakhir
        def sum_col(df, kw):
            for c in df.columns:
                if kw.lower() in str(c).lower():
                    return df[c].apply(safe_num).sum()
            return 0

        total_coal  = sum_col(last, "coal")
        total_hsd   = sum_col(last, "hsd")
        total_bio   = sum_col(last, "biomassa")
        total_prod  = sum_col(last, "netto")
        avg_hr      = last[[c for c in last.columns if "heat" in str(c).lower()]].apply(
                          lambda x: x.apply(safe_num)).mean().mean()

        c1,c2,c3,c4,c5 = st.columns(5)
        kpi_card(c1,"Produksi Netto",f"{total_prod:,.0f}","MWh","Minggu berjalan","#1F4E79")
        kpi_card(c2,"Konsumsi Coal", f"{total_coal:,.0f}","ton","Minggu berjalan","#2C2C2C")
        kpi_card(c3,"Konsumsi HSD",  f"{total_hsd:,.1f}","kL","Minggu berjalan","#B8860B")
        kpi_card(c4,"Konsumsi Biomassa",f"{total_bio:,.0f}","ton","Minggu berjalan","#2E7D32")
        kpi_card(c5,"Heat Rate",f"{avg_hr:,.0f}","kCal/kWh","Rerata minggu ini","#7B3F00")

    st.markdown("<br>", unsafe_allow_html=True)

    # Chart: konsumsi energi per minggu (stacked bar)
    if not df_w.empty:
        col_l, col_r = st.columns([3,2])
        with col_l:
            st.markdown('<div class="sec">Konsumsi Energi Primer per Minggu (Gabungan Unit 1 & 2)</div>',
                        unsafe_allow_html=True)
            wk_col = df_w.columns[0]
            coal_col = next((c for c in df_w.columns if "coal" in str(c).lower() and "stok" not in str(c).lower()), None)
            bio_col  = next((c for c in df_w.columns if "biomassa" in str(c).lower() and "stok" not in str(c).lower()), None)
            if coal_col:
                df_agg = df_w.groupby(wk_col).apply(
                    lambda x: pd.Series({
                        "Coal (ton)": x[coal_col].apply(safe_num).sum(),
                        "Biomassa (ton)": x[bio_col].apply(safe_num).sum() if bio_col else 0,
                    })
                ).reset_index()
                fig = go.Figure()
                fig.add_bar(x=df_agg[wk_col], y=df_agg["Coal (ton)"], name="Coal",
                            marker_color="#2C2C2C")
                fig.add_bar(x=df_agg[wk_col], y=df_agg["Biomassa (ton)"], name="Biomassa",
                            marker_color="#2E7D32")
                fig.update_layout(barmode="stack", height=280,
                                  margin=dict(t=10,b=10,l=10,r=10),
                                  paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)",
                                  legend=dict(orientation="h",y=1.1))
                st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.markdown('<div class="sec">Proporsi Energi Primer (Total)</div>',
                        unsafe_allow_html=True)
            if not df_w.empty:
                hsd_col = next((c for c in df_w.columns if "hsd" in str(c).lower()), None)
                tots = {
                    "Coal": df_w[coal_col].apply(safe_num).sum() if coal_col else 0,
                    "HSD":  df_w[hsd_col].apply(safe_num).sum()*8.6 if hsd_col else 0,
                    "Biomassa": df_w[bio_col].apply(safe_num).sum()*3.5/1000 if bio_col else 0,
                }
                fig2 = px.pie(
                    names=list(tots.keys()), values=list(tots.values()),
                    color=list(tots.keys()),
                    color_discrete_map=FUEL_COLORS, hole=0.5
                )
                fig2.update_traces(textposition="outside", textinfo="percent+label")
                fig2.update_layout(showlegend=False, height=280,
                                   margin=dict(t=10,b=10,l=10,r=10),
                                   paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

    # Heat Rate tren
    if not df_w.empty:
        st.markdown('<div class="sec">Tren Heat Rate & Produksi per Minggu</div>',
                    unsafe_allow_html=True)
        wk_col = df_w.columns[0]
        hr_col   = next((c for c in df_w.columns if "heat" in str(c).lower()), None)
        prod_col = next((c for c in df_w.columns if "netto" in str(c).lower()), None)
        if hr_col and prod_col:
            df_hr = df_w.groupby(wk_col).apply(
                lambda x: pd.Series({
                    "Heat Rate (kCal/kWh)": x[hr_col].apply(safe_num).mean(),
                    "Produksi (MWh)": x[prod_col].apply(safe_num).sum(),
                })
            ).reset_index()
            fig3 = make_subplots(specs=[[{"secondary_y": True}]])
            fig3.add_trace(go.Bar(x=df_hr[wk_col], y=df_hr["Produksi (MWh)"],
                                  name="Produksi (MWh)", marker_color="#185FA5",
                                  opacity=0.7), secondary_y=False)
            fig3.add_trace(go.Scatter(x=df_hr[wk_col], y=df_hr["Heat Rate (kCal/kWh)"],
                                      name="Heat Rate (kCal/kWh)", mode="lines+markers",
                                      line=dict(color="#C62828", width=2),
                                      marker=dict(size=6)), secondary_y=True)
            fig3.add_hline(y=2450, line_dash="dot", line_color="#2E7D32",
                           annotation_text="Target HR 2450", secondary_y=True)
            fig3.update_layout(height=280, margin=dict(t=10,b=10,l=10,r=10),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               legend=dict(orientation="h", y=1.1))
            fig3.update_yaxes(title_text="Produksi (MWh)", secondary_y=False)
            fig3.update_yaxes(title_text="Heat Rate (kCal/kWh)", secondary_y=True)
            st.plotly_chart(fig3, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: COAL
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🪨 Coal":
    st.markdown('<div class="topbar"><h1>🪨 Monitoring Batubara (Coal)</h1><p>Penerimaan · Konsumsi · Stok · GCV</p></div>',
                unsafe_allow_html=True)
    if df_h.empty:
        st.info("Upload file Excel untuk melihat data.")
    else:
        tgl_col  = df_h.columns[0]
        rcv_col  = next((c for c in df_h.columns if "penerimaan" in str(c).lower() and "coal" in str(c).lower()), None)
        con_col  = next((c for c in df_h.columns if "konsumsi" in str(c).lower() and "coal" in str(c).lower()), None)
        stk_col  = next((c for c in df_h.columns if "stok" in str(c).lower() and "coal" in str(c).lower()), None)
        gcv_col  = next((c for c in df_h.columns if "gcv" in str(c).lower()), None)

        if con_col:
            total_rcv = df_h[rcv_col].apply(safe_num).sum() if rcv_col else 0
            total_con = df_h[con_col].apply(safe_num).sum()
            last_stk  = df_h[stk_col].apply(safe_num).iloc[-1] if stk_col else 0
            avg_gcv   = df_h[gcv_col].apply(safe_num).mean() if gcv_col else 0

            c1,c2,c3,c4 = st.columns(4)
            kpi_card(c1,"Total Penerimaan",f"{total_rcv:,.0f}","ton","Periode data","#2C2C2C")
            kpi_card(c2,"Total Konsumsi",  f"{total_con:,.0f}","ton","Periode data","#2C2C2C")
            kpi_card(c3,"Stok Akhir",      f"{last_stk:,.0f}","ton","Terakhir input","#B8860B")
            kpi_card(c4,"Avg GCV",         f"{avg_gcv:,.0f}","kCal/kg","Rata-rata periode","#1565C0")
            st.markdown("<br>", unsafe_allow_html=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown('<div class="sec">Konsumsi & Penerimaan Coal Harian</div>', unsafe_allow_html=True)
                fig = go.Figure()
                if rcv_col:
                    fig.add_bar(x=df_h[tgl_col], y=df_h[rcv_col].apply(safe_num),
                                name="Penerimaan", marker_color="#639922", opacity=0.7)
                fig.add_bar(x=df_h[tgl_col], y=df_h[con_col].apply(safe_num),
                            name="Konsumsi", marker_color="#2C2C2C", opacity=0.85)
                fig.update_layout(barmode="overlay", height=280,
                                  margin=dict(t=5,b=5,l=5,r=5),
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  legend=dict(orientation="h",y=1.1))
                st.plotly_chart(fig, use_container_width=True)

            with col_b:
                st.markdown('<div class="sec">Tren Stok Coal</div>', unsafe_allow_html=True)
                if stk_col:
                    fig2 = go.Figure()
                    stk_vals = df_h[stk_col].apply(safe_num)
                    fig2.add_trace(go.Scatter(x=df_h[tgl_col], y=stk_vals,
                                             fill="tozeroy", mode="lines",
                                             line=dict(color="#2C2C2C", width=2),
                                             fillcolor="rgba(44,44,44,0.15)"))
                    fig2.add_hline(y=5000, line_dash="dot", line_color="#C62828",
                                   annotation_text="Stok Minimum (5.000 ton)")
                    fig2.update_layout(height=280, margin=dict(t=5,b=5,l=5,r=5),
                                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig2, use_container_width=True)

        # Tabel
        st.markdown('<div class="sec">Data Harian Coal</div>', unsafe_allow_html=True)
        show = [c for c in [tgl_col, rcv_col, con_col, stk_col, gcv_col] if c]
        st.dataframe(df_h[show].tail(30), use_container_width=True,
                     height=300, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: HSD & GAS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "⛽ HSD":
    st.markdown('<div class="topbar"><h1>⛽ Monitoring HSD (Solar)</h1><p>Penerimaan · Konsumsi · Stok</p></div>',
                unsafe_allow_html=True)
    if df_h.empty:
        st.info("Upload file Excel untuk melihat data.")
    else:
        tgl_col = df_h.columns[0]
        hsd_con = next((c for c in df_h.columns if "konsumsi" in str(c).lower() and "hsd" in str(c).lower()), None)
        hsd_stk = next((c for c in df_h.columns if "stok" in str(c).lower() and "hsd" in str(c).lower()), None)

        c1,c2,c3 = st.columns(3)
        kpi_card(c1,"Total Konsumsi HSD",
                 f"{df_h[hsd_con].apply(safe_num).sum():,.1f}" if hsd_con else "—","kL","Periode data","#B8860B")
        kpi_card(c2,"Stok HSD Akhir",
                 f"{df_h[hsd_stk].apply(safe_num).iloc[-1]:,.1f}" if hsd_stk else "—","kL","Terakhir","#B8860B")
        kpi_card(c3,"Avg Konsumsi Harian HSD",
                 f"{df_h[hsd_con].apply(safe_num).mean():,.2f}" if hsd_con else "—","kL/hari","Rata-rata","#B8860B")
        st.markdown("<br>", unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<div class="sec">Konsumsi HSD Harian</div>', unsafe_allow_html=True)
            if hsd_con:
                fig = px.bar(df_h, x=tgl_col, y=df_h[hsd_con].apply(safe_num),
                             color_discrete_sequence=["#B8860B"])
                fig.update_layout(height=250, margin=dict(t=5,b=5,l=5,r=5),
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
        with col_b:
            st.markdown('<div class="sec">Tren Stok HSD</div>', unsafe_allow_html=True)
            if hsd_stk:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=df_h[tgl_col], y=df_h[hsd_stk].apply(safe_num),
                                          fill="tozeroy", mode="lines",
                                          line=dict(color="#B8860B", width=2),
                                          fillcolor="rgba(184,134,11,0.15)"))
                fig2.add_hline(y=10, line_dash="dot", line_color="#C62828",
                               annotation_text="Stok Minimum (10 kL)")
                fig2.update_layout(height=250, margin=dict(t=5,b=5,l=5,r=5),
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: BIOMASSA
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🌿 Biomassa":
    st.markdown('<div class="topbar"><h1>🌿 Monitoring Biomassa (Co-firing)</h1><p>Penerimaan · Konsumsi · Stok · Rasio Co-firing</p></div>',
                unsafe_allow_html=True)
    if df_h.empty:
        st.info("Upload file Excel untuk melihat data.")
    else:
        tgl_col = df_h.columns[0]
        bio_con = next((c for c in df_h.columns if "konsumsi" in str(c).lower() and "bio" in str(c).lower()), None)
        bio_stk = next((c for c in df_h.columns if "stok" in str(c).lower() and "bio" in str(c).lower()), None)
        bio_rcv = next((c for c in df_h.columns if "penerimaan" in str(c).lower() and "bio" in str(c).lower()), None)
        coal_con= next((c for c in df_h.columns if "konsumsi" in str(c).lower() and "coal" in str(c).lower()), None)

        total_bio = df_h[bio_con].apply(safe_num).sum() if bio_con else 0
        total_coal= df_h[coal_con].apply(safe_num).sum() if coal_con else 1
        rasio_co  = total_bio / (total_bio + total_coal) * 100 if (total_bio+total_coal) > 0 else 0

        c1,c2,c3,c4 = st.columns(4)
        kpi_card(c1,"Total Konsumsi Biomassa",f"{total_bio:,.0f}","ton","Periode data","#2E7D32")
        kpi_card(c2,"Total Penerimaan",
                 f"{df_h[bio_rcv].apply(safe_num).sum():,.0f}" if bio_rcv else "—","ton","Periode data","#2E7D32")
        kpi_card(c3,"Stok Akhir",
                 f"{df_h[bio_stk].apply(safe_num).iloc[-1]:,.0f}" if bio_stk else "—","ton","Terakhir","#639922")
        kpi_card(c4,"Rasio Co-firing",f"{rasio_co:.1f}","%","Biomassa/(Bio+Coal)","#185FA5")
        st.markdown("<br>", unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<div class="sec">Konsumsi Biomassa Harian</div>', unsafe_allow_html=True)
            if bio_con:
                fig = go.Figure()
                fig.add_bar(x=df_h[tgl_col], y=df_h[bio_con].apply(safe_num),
                            name="Biomassa", marker_color="#2E7D32")
                if bio_rcv:
                    fig.add_bar(x=df_h[tgl_col], y=df_h[bio_rcv].apply(safe_num),
                                name="Penerimaan", marker_color="#A5D6A7", opacity=0.7)
                fig.update_layout(barmode="overlay", height=260,
                                  margin=dict(t=5,b=5,l=5,r=5),
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  legend=dict(orientation="h",y=1.1))
                st.plotly_chart(fig, use_container_width=True)
        with col_b:
            st.markdown('<div class="sec">Tren Rasio Co-firing Harian</div>', unsafe_allow_html=True)
            if bio_con and coal_con:
                df_h["rasio_co"] = df_h[bio_con].apply(safe_num) / (
                    df_h[bio_con].apply(safe_num) + df_h[coal_con].apply(safe_num)
                ) * 100
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=df_h[tgl_col], y=df_h["rasio_co"],
                                          fill="tozeroy", mode="lines",
                                          line=dict(color="#2E7D32", width=2),
                                          fillcolor="rgba(46,125,50,0.15)"))
                fig2.add_hline(y=3.5, line_dash="dot", line_color="#1565C0",
                               annotation_text="Target Co-firing 3.5%")
                fig2.update_layout(height=260, margin=dict(t=5,b=5,l=5,r=5),
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: TARGET vs REALISASI
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📈 Target vs Realisasi":
    st.markdown('<div class="topbar"><h1>📈 Target vs Realisasi</h1><p>KPI Energi Primer Bulan Berjalan & YTD</p></div>',
                unsafe_allow_html=True)
    if df_t.empty:
        st.info("Data target belum tersedia di file Excel.")
    else:
        kpi_col  = df_t.columns[0]
        sat_col  = df_t.columns[1] if len(df_t.columns) > 1 else None
        tgt_col  = df_t.columns[2] if len(df_t.columns) > 2 else None
        real_col = df_t.columns[3] if len(df_t.columns) > 3 else None
        dev_col  = df_t.columns[4] if len(df_t.columns) > 4 else None
        devp_col = df_t.columns[5] if len(df_t.columns) > 5 else None
        stat_col = df_t.columns[6] if len(df_t.columns) > 6 else None

        # Gauge chart untuk KPI utama
        kpi_rows = df_t.head(8)
        col_g1, col_g2 = st.columns(2)
        for i, (_, row) in enumerate(kpi_rows.iterrows()):
            col = col_g1 if i % 2 == 0 else col_g2
            tgt  = safe_num(row.get(tgt_col, 0))
            real = safe_num(row.get(real_col, 0))
            nama = str(row.get(kpi_col, ""))
            sat  = str(row.get(sat_col, ""))
            pct  = real/tgt*100 if tgt else 0
            # Untuk HR & SFC: lebih kecil = lebih baik
            inv  = "Heat Rate" in nama or "SFC" in nama
            color= "#2E7D32" if (pct<=100 if inv else pct>=95) else "#F57F17"
            with col:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=real,
                    delta={"reference": tgt, "valueformat": ".1f",
                           "increasing": {"color":"#C62828"} if inv else {"color":"#2E7D32"},
                           "decreasing": {"color":"#2E7D32"} if inv else {"color":"#C62828"}},
                    number={"suffix": f" {sat}", "font": {"size": 22}},
                    title={"text": f"<b>{nama}</b><br><span style='font-size:11px'>Target: {tgt:,.1f} {sat}</span>"},
                    gauge={
                        "axis": {"range": [0, tgt*1.3]},
                        "bar": {"color": color, "thickness": 0.25},
                        "steps": [
                            {"range":[0, tgt*0.8], "color":"#FFEBEE"},
                            {"range":[tgt*0.8, tgt], "color":"#FFF8E1"},
                            {"range":[tgt, tgt*1.3], "color":"#E8F5E9"},
                        ],
                        "threshold":{"line":{"color":"#1F4E79","width":3},"value":tgt,"thickness":0.85}
                    }
                ))
                fig.update_layout(height=200, margin=dict(t=60,b=0,l=20,r=20),
                                  paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

        # Tabel lengkap
        st.markdown('<div class="sec">Tabel Target vs Realisasi</div>', unsafe_allow_html=True)
        show_cols = [c for c in df_t.columns[:8] if c]

        def style_status(val):
            if "BAIK" in str(val): return "background-color:#E8F5E9;color:#2E7D32;font-weight:600"
            if "DEVIASI" in str(val): return "background-color:#FFF8E1;color:#F57F17;font-weight:600"
            return ""

        styled = df_t[show_cols].style.map(style_status, subset=[stat_col] if stat_col else [])
        st.dataframe(styled, use_container_width=True, height=320, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: TREN & ANALISIS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📉 Tren & Analisis":
    st.markdown('<div class="topbar"><h1>📉 Tren & Analisis</h1><p>Heat Rate · SFC · Efisiensi Mingguan</p></div>',
                unsafe_allow_html=True)
    if df_w.empty:
        st.info("Data rekap mingguan belum tersedia.")
    else:
        wk_col   = df_w.columns[0]
        hr_col   = next((c for c in df_w.columns if "heat" in str(c).lower()), None)
        sfc_col  = next((c for c in df_w.columns if "sfc" in str(c).lower()), None)
        af_col   = next((c for c in df_w.columns if "avail" in str(c).lower()), None)
        prod_col = next((c for c in df_w.columns if "netto" in str(c).lower()), None)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<div class="sec">Tren Heat Rate per Minggu (per Unit)</div>',
                        unsafe_allow_html=True)
            if hr_col:
                unit_col = df_w.columns[2] if len(df_w.columns)>2 else None
                fig = px.line(df_w, x=wk_col, y=df_w[hr_col].apply(safe_num),
                              color=df_w[unit_col].astype(str) if unit_col else None,
                              markers=True,
                              color_discrete_sequence=["#1F4E79","#C62828"],
                              labels={hr_col:"Heat Rate (kCal/kWh)","color":"Unit"})
                fig.add_hline(y=2450, line_dash="dot", line_color="#2E7D32",
                              annotation_text="Target 2450")
                fig.update_layout(height=270, margin=dict(t=5,b=5,l=5,r=5),
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown('<div class="sec">Tren SFC Coal per Minggu</div>',
                        unsafe_allow_html=True)
            if sfc_col:
                unit_col = df_w.columns[2] if len(df_w.columns)>2 else None
                fig2 = px.line(df_w, x=wk_col, y=df_w[sfc_col].apply(safe_num),
                               color=df_w[unit_col].astype(str) if unit_col else None,
                               markers=True,
                               color_discrete_sequence=["#1F4E79","#C62828"],
                               labels={sfc_col:"SFC Coal (kg/kWh)","color":"Unit"})
                fig2.add_hline(y=5.8, line_dash="dot", line_color="#2E7D32",
                               annotation_text="Target 5.80 kg/kWh")
                fig2.update_layout(height=270, margin=dict(t=5,b=5,l=5,r=5),
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

        # Availability Factor
        if af_col:
            st.markdown('<div class="sec">Availability Factor per Minggu</div>',
                        unsafe_allow_html=True)
            unit_col = df_w.columns[2] if len(df_w.columns)>2 else None
            fig3 = px.bar(df_w, x=wk_col, y=df_w[af_col].apply(safe_num),
                          color=df_w[unit_col].astype(str) if unit_col else None,
                          barmode="group",
                          color_discrete_sequence=["#1F4E79","#185FA5"],
                          labels={af_col:"Availability Factor (%)","color":"Unit"})
            fig3.add_hline(y=92, line_dash="dot", line_color="#C62828",
                           annotation_text="Target 92%")
            fig3.update_layout(height=260, margin=dict(t=5,b=5,l=5,r=5),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)

        # Download data mingguan
        csv = df_w.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Rekap Mingguan (CSV)",
                           csv, "rekap_mingguan.csv", "text/csv")
