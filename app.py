"""
app.py — Dashboard Monitoring Energi Primer PLTU v2
"""
import streamlit as st
import pandas as pd, pandas as pd, numpy as np
import plotly.express as px, plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import datetime

from utils.loader_energi import (
    load_harian, load_mingguan, load_target,
    tren_harian, prognosa, summary_stok, kpi_overview
)

st.set_page_config(page_title="Energi Primer PLTU",page_icon="⚡",layout="wide",initial_sidebar_state="expanded")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif}
[data-testid="stSidebar"]{background:#1F4E79}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,[data-testid="stSidebar"] .stMarkdown{color:#CADDF2!important}
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#fff!important}
.kpi{background:white;border-radius:10px;padding:14px 18px;border-left:4px solid #1F4E79;box-shadow:0 1px 4px rgba(0,0,0,.07);margin-bottom:4px}
.kpi-lbl{font-size:10px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:#6B7280;margin-bottom:4px}
.kpi-val{font-size:24px;font-weight:600;line-height:1}
.kpi-sub{font-size:11px;color:#9CA3AF;margin-top:3px}
.sec{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:#6B7280;border-bottom:1px solid #E5E7EB;padding-bottom:5px;margin-bottom:10px}
.topbar{background:linear-gradient(135deg,#1F4E79,#2E6DA4);border-radius:12px;padding:16px 24px;margin-bottom:16px;color:white}
.topbar h1{font-size:20px;font-weight:600;margin:0;color:white}
.topbar p{font-size:12px;color:#CADDF2;margin:3px 0 0}
.sc{background:white;border-radius:10px;padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,.07);margin-bottom:10px}
.sr{display:flex;justify-content:space-between;font-size:12px;padding:4px 0;border-bottom:.5px solid #F3F4F6}
.sr:last-child{border:none;font-weight:600}
.bok{background:#E8F5E9;color:#2E7D32;padding:1px 8px;border-radius:12px;font-size:10px;font-weight:600}
.bwrn{background:#FFF8E1;color:#F57F17;padding:1px 8px;border-radius:12px;font-size:10px;font-weight:600}
.bcrt{background:#FFEBEE;color:#C62828;padding:1px 8px;border-radius:12px;font-size:10px;font-weight:600}
.pb{background:#F3F4F6;border-radius:6px;height:8px;margin-top:4px}
.pbf{height:8px;border-radius:6px}
</style>""",unsafe_allow_html=True)

COLORS={"Coal":"#2C2C2C","HSD":"#B8860B","Biomassa":"#2E7D32","Produksi":"#1565C0","HR":"#C62828"}

def kpi_card(col,label,val,unit,sub,color="#1F4E79"):
    with col:
        st.markdown(f'<div class="kpi" style="border-left-color:{color}"><div class="kpi-lbl">{label}</div>'
                    f'<div class="kpi-val" style="color:{color}">{val}<span style="font-size:12px;color:#9CA3AF;font-weight:400"> {unit}</span></div>'
                    f'<div class="kpi-sub">{sub}</div></div>',unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## ⚡ Energi Primer\n### Monitoring Dashboard")
    st.markdown("---")
    uploaded=st.file_uploader("📂 Upload Excel (.xlsx)",type=["xlsx"])
    st.markdown("---")
    st.markdown("### Filter")
    sel_unit=st.selectbox("Unit PLTU",["Semua","Unit 1","Unit 2"])
    page=st.radio("Halaman",[
        "📊 Overview","📅 Tren Harian","🔮 Prognosa","📦 Stok",
        "🪨 Coal","⛽ HSD","🌿 Biomassa","📈 Target vs Realisasi"])
    st.markdown("---")
    st.caption("Energi Primer Dashboard v2.0\nPLTU Unit 1 & 2")

DATA_PATH=Path("data/energi_data.xlsx")
src=uploaded if uploaded else (DATA_PATH if DATA_PATH.exists() else None)
if src is None:
    st.warning("⬆️ Upload file Excel Energi Primer untuk memulai.")
    st.stop()

df_h=load_harian(src); df_w=load_mingguan(src); df_t=load_target(src)
df_tr=tren_harian(df_h,sel_unit); prog=prognosa(df_h,sel_unit)
stok=summary_stok(df_h,sel_unit); kpi_ov=kpi_overview(df_h,sel_unit)

BGMAP={"2C2C2C":(44,44,44),"B8860B":(184,134,11),"2E7D32":(46,125,50)}

def area_chart(x,y,color_hex,min_line=None,min_label="",title="",h=250):
    rgb=BGMAP.get(color_hex.upper().lstrip("#"),(100,100,100))
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=x,y=y,fill="tozeroy",mode="lines+markers",
                              line=dict(color=f"#{color_hex}",width=2),
                              fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.12)",
                              marker=dict(size=3)))
    if min_line:
        fig.add_hline(y=min_line,line_dash="dot",line_color="#C62828",annotation_text=min_label)
    fig.update_layout(height=h,margin=dict(t=5,b=5,l=5,r=5),
                       paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",showlegend=False)
    return fig

# ══════════════════════════════════════════════════════════════════════
if page=="📊 Overview":
    st.markdown('<div class="topbar"><h1>⚡ Dashboard Monitoring Energi Primer</h1><p>PLTU Unit 1 & 2 · Coal · HSD · Biomassa</p></div>',unsafe_allow_html=True)
    c1,c2,c3,c4,c5=st.columns(5)
    kpi_card(c1,"Produksi Netto",f"{kpi_ov['total_prod']:,.0f}","MWh","Total periode","#1565C0")
    kpi_card(c2,"Konsumsi Coal",f"{kpi_ov['total_coal']:,.0f}","ton","Total periode","#2C2C2C")
    kpi_card(c3,"Konsumsi HSD",f"{kpi_ov['total_hsd']:,.1f}","kL","Total periode","#B8860B")
    kpi_card(c4,"Konsumsi Biomassa",f"{kpi_ov['total_bio']:,.0f}","ton","Total periode","#2E7D32")
    kpi_card(c5,"Heat Rate Rerata",f"{kpi_ov['avg_hr']:,.0f}","kCal/kWh","Rata-rata","#C62828")
    st.markdown("<br>",unsafe_allow_html=True)

    # ── Tren konsumsi harian — pisah Unit 1 & 2 ───────────────────────────
    st.markdown('<div class="sec">Konsumsi Coal & Biomassa Harian — Unit 1 vs Unit 2</div>',unsafe_allow_html=True)
    df_u1=tren_harian(df_h, unit_filter="Unit 1"); df_u2=tren_harian(df_h, unit_filter="Unit 2")
    fig_con=make_subplots(rows=1,cols=2,
                          subplot_titles=("Unit 1","Unit 2"),
                          shared_yaxes=True)
    for col_i,(dfu,unit_label) in enumerate([(df_u1,"Unit 1"),(df_u2,"Unit 2")],start=1):
        if not dfu.empty:
            fig_con.add_trace(go.Bar(x=dfu["tanggal"],y=dfu["coal_con"],
                                     name=f"Coal {unit_label}",marker_color="#2C2C2C",
                                     opacity=0.85,showlegend=(col_i==1)),row=1,col=col_i)
            fig_con.add_trace(go.Bar(x=dfu["tanggal"],y=dfu["bio_con"],
                                     name=f"Biomassa {unit_label}",marker_color="#2E7D32",
                                     opacity=0.85,showlegend=(col_i==1)),row=1,col=col_i)
            fig_con.add_trace(go.Scatter(x=dfu["tanggal"],y=dfu["coal_con_ma7"],
                                         name="MA7 Coal" if col_i==1 else "",
                                         mode="lines",line=dict(color="#F9A825",width=2,dash="dot"),
                                         showlegend=(col_i==1)),row=1,col=col_i)
    fig_con.update_layout(barmode="stack",height=300,
                          margin=dict(t=30,b=5,l=5,r=5),
                          paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                          legend=dict(orientation="h",y=1.15))
    fig_con.update_yaxes(title_text="Konsumsi (ton)",col=1)
    st.plotly_chart(fig_con,use_container_width=True)

    # ── Proporsi energi ───────────────────────────────────────────────────
    cl,cr=st.columns([1,2])
    with cl:
        st.markdown('<div class="sec">Proporsi Energi (GCal)</div>',unsafe_allow_html=True)
        coal_k=kpi_ov["total_coal"]*5000/1e6; hsd_k=kpi_ov["total_hsd"]*8.6; bio_k=kpi_ov["total_bio"]*3.5/1000
        fig2=px.pie(names=["Coal","HSD","Biomassa"],values=[coal_k,hsd_k,bio_k],
                    color=["Coal","HSD","Biomassa"],color_discrete_map=COLORS,hole=0.52)
        fig2.update_traces(textposition="outside",textinfo="percent+label")
        fig2.update_layout(showlegend=False,height=270,
                           margin=dict(t=10,b=10,l=10,r=10),
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2,use_container_width=True)

    with cr:
        st.markdown('<div class="sec">Konsumsi HSD Harian — Unit 1 vs Unit 2</div>',unsafe_allow_html=True)
        fig_hsd=make_subplots(rows=1,cols=2,
                              subplot_titles=("Unit 1","Unit 2"),
                              shared_yaxes=True)
        for col_i,(dfu,ul) in enumerate([(df_u1,"Unit 1"),(df_u2,"Unit 2")],start=1):
            if not dfu.empty:
                fig_hsd.add_trace(go.Bar(x=dfu["tanggal"],y=dfu["hsd_con"],
                                         name=f"HSD {ul}",marker_color="#B8860B",
                                         opacity=0.85,showlegend=False),row=1,col=col_i)
                fig_hsd.add_trace(go.Scatter(x=dfu["tanggal"],y=dfu["hsd_con_ma7"],
                                             name="MA7" if col_i==1 else "",
                                             mode="lines",line=dict(color="#C62828",width=2,dash="dot"),
                                             showlegend=False),row=1,col=col_i)
        fig_hsd.update_layout(height=270,margin=dict(t=30,b=5,l=5,r=5),
                              paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        fig_hsd.update_yaxes(title_text="Konsumsi (kL)",col=1)
        st.plotly_chart(fig_hsd,use_container_width=True)

    # ── Heat Rate harian — pisah Unit 1 & 2 ──────────────────────────────
    st.markdown('<div class="sec">Heat Rate Harian — Unit 1 vs Unit 2</div>',unsafe_allow_html=True)
    fig_hr=make_subplots(rows=1,cols=2,
                         subplot_titles=("Unit 1","Unit 2"),
                         shared_yaxes=True)
    for col_i,(dfu,ul) in enumerate([(df_u1,"Unit 1"),(df_u2,"Unit 2")],start=1):
        if not dfu.empty:
            fig_hr.add_trace(go.Scatter(x=dfu["tanggal"],y=dfu["heat_rate"],
                                        name=f"Heat Rate {ul}",
                                        mode="lines+markers",
                                        marker=dict(size=4),
                                        line=dict(color="#C62828" if col_i==1 else "#1565C0",width=2),
                                        showlegend=True),row=1,col=col_i)
            fig_hr.add_trace(go.Scatter(x=dfu["tanggal"],y=dfu["heat_rate_ma7"],
                                        name=f"MA7 {ul}",
                                        mode="lines",
                                        line=dict(color="#F9A825",width=1.5,dash="dot"),
                                        showlegend=(col_i==1)),row=1,col=col_i)
            # Target line per subplot
            fig_hr.add_hline(y=2450,line_dash="dot",line_color="#2E7D32",
                             annotation_text="Target 2450" if col_i==1 else "",
                             row=1,col=col_i)
    fig_hr.update_layout(height=300,margin=dict(t=30,b=5,l=5,r=5),
                         paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                         legend=dict(orientation="h",y=1.15))
    fig_hr.update_yaxes(title_text="Heat Rate (kCal/kWh)",col=1)
    st.plotly_chart(fig_hr,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════
elif page=="📅 Tren Harian":
    st.markdown('<div class="topbar"><h1>📅 Tren Harian Energi Primer</h1><p>MA7 = Moving Average 7 hari · Klik tab bahan bakar di bawah</p></div>',unsafe_allow_html=True)
    tab1,tab2,tab3,tab4=st.tabs(["🪨 Coal","⛽ HSD","🌿 Biomassa","📊 Efisiensi"])

    with tab1:
        ca,cb=st.columns(2)
        with ca:
            st.markdown('<div class="sec">Konsumsi Coal Harian + MA7</div>',unsafe_allow_html=True)
            fig=go.Figure()
            fig.add_bar(x=df_tr["tanggal"],y=df_tr["coal_con"],name="Konsumsi",marker_color="#2C2C2C",opacity=0.75)
            fig.add_scatter(x=df_tr["tanggal"],y=df_tr["coal_con_ma7"],name="MA7",mode="lines",line=dict(color="#F9A825",width=2))
            fig.update_layout(height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.12))
            st.plotly_chart(fig,use_container_width=True)
        with cb:
            st.markdown('<div class="sec">Penerimaan vs Konsumsi Coal</div>',unsafe_allow_html=True)
            fig2=go.Figure()
            fig2.add_bar(x=df_tr["tanggal"],y=df_tr["coal_rcv"],name="Penerimaan",marker_color="#639922",opacity=0.8)
            fig2.add_bar(x=df_tr["tanggal"],y=df_tr["coal_con"],name="Konsumsi",marker_color="#2C2C2C",opacity=0.8)
            fig2.update_layout(barmode="group",height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.12))
            st.plotly_chart(fig2,use_container_width=True)
        st.markdown('<div class="sec">Tren Stok Akhir Coal</div>',unsafe_allow_html=True)
        st.plotly_chart(area_chart(df_tr["tanggal"],df_tr["coal_stok_akhir"],"2C2C2C",5000,"Min 5.000 ton",h=200),use_container_width=True)

    with tab2:
        ca,cb=st.columns(2)
        with ca:
            st.markdown('<div class="sec">Konsumsi HSD Harian + MA7</div>',unsafe_allow_html=True)
            fig=go.Figure()
            fig.add_bar(x=df_tr["tanggal"],y=df_tr["hsd_con"],name="Konsumsi",marker_color="#B8860B",opacity=0.8)
            fig.add_scatter(x=df_tr["tanggal"],y=df_tr["hsd_con_ma7"],name="MA7",mode="lines",line=dict(color="#C62828",width=2))
            fig.update_layout(height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.12))
            st.plotly_chart(fig,use_container_width=True)
        with cb:
            st.markdown('<div class="sec">Tren Stok HSD</div>',unsafe_allow_html=True)
            st.plotly_chart(area_chart(df_tr["tanggal"],df_tr["hsd_stok_akhir"],"B8860B",10,"Min 10 kL",h=260),use_container_width=True)

    with tab3:
        ca,cb=st.columns(2)
        with ca:
            st.markdown('<div class="sec">Konsumsi Biomassa + MA7</div>',unsafe_allow_html=True)
            fig=go.Figure()
            fig.add_bar(x=df_tr["tanggal"],y=df_tr["bio_con"],name="Konsumsi",marker_color="#2E7D32",opacity=0.8)
            fig.add_scatter(x=df_tr["tanggal"],y=df_tr["bio_con_ma7"],name="MA7",mode="lines",line=dict(color="#F9A825",width=2))
            fig.update_layout(height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.12))
            st.plotly_chart(fig,use_container_width=True)
        with cb:
            st.markdown('<div class="sec">Tren Rasio Co-firing Harian</div>',unsafe_allow_html=True)
            fig2=go.Figure()
            fig2.add_trace(go.Scatter(x=df_tr["tanggal"],y=df_tr["rasio_co"],fill="tozeroy",mode="lines",line=dict(color="#2E7D32",width=2),fillcolor="rgba(46,125,50,0.15)"))
            fig2.add_hline(y=3.5,line_dash="dot",line_color="#1565C0",annotation_text="Target 3.5%")
            fig2.update_layout(height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2,use_container_width=True)

    with tab4:
        ca,cb=st.columns(2)
        with ca:
            st.markdown('<div class="sec">Heat Rate Harian + MA7</div>',unsafe_allow_html=True)
            fig=go.Figure()
            fig.add_scatter(x=df_tr["tanggal"],y=df_tr["heat_rate"],mode="lines",name="Heat Rate",line=dict(color="#C62828",width=1.5))
            fig.add_scatter(x=df_tr["tanggal"],y=df_tr["heat_rate_ma7"],mode="lines",name="MA7",line=dict(color="#F9A825",width=2,dash="dot"))
            fig.add_hline(y=2450,line_dash="dot",line_color="#2E7D32",annotation_text="Target 2450")
            fig.update_layout(height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.12))
            st.plotly_chart(fig,use_container_width=True)
        with cb:
            st.markdown('<div class="sec">SFC Coal Harian + MA7</div>',unsafe_allow_html=True)
            fig2=go.Figure()
            fig2.add_scatter(x=df_tr["tanggal"],y=df_tr["sfc_coal"],mode="lines",name="SFC Coal",line=dict(color="#7B3F00",width=1.5))
            fig2.add_scatter(x=df_tr["tanggal"],y=df_tr["sfc_coal_ma7"],mode="lines",name="MA7",line=dict(color="#F9A825",width=2,dash="dot"))
            fig2.add_hline(y=5.8,line_dash="dot",line_color="#2E7D32",annotation_text="Target 5.80")
            fig2.update_layout(height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.12))
            st.plotly_chart(fig2,use_container_width=True)
        with st.expander("📋 Tabel data harian"):
            cols=["tanggal","coal_con","hsd_con","bio_con","produksi","heat_rate","sfc_coal","rasio_co"]
            cols=[c for c in cols if c in df_tr.columns]
            ren={"tanggal":"Tanggal","coal_con":"Coal (ton)","hsd_con":"HSD (kL)","bio_con":"Biomassa (ton)",
                 "produksi":"Produksi (MWh)","heat_rate":"Heat Rate","sfc_coal":"SFC Coal","rasio_co":"Co-firing (%)"}
            st.dataframe(df_tr[cols].rename(columns=ren),use_container_width=True,height=280,hide_index=True)
            st.download_button("⬇️ Download CSV",df_tr[cols].to_csv(index=False).encode(),"tren_harian.csv","text/csv")

# ══════════════════════════════════════════════════════════════════════
elif page=="🔮 Prognosa":
    st.markdown('<div class="topbar"><h1>🔮 Prognosa Akhir Bulan</h1><p>Proyeksi berdasarkan rata-rata konsumsi 7 hari terakhir</p></div>',unsafe_allow_html=True)
    if not prog:
        st.info("Data belum cukup untuk prognosa.")
        st.stop()
    c1,c2,c3=st.columns(3)
    kpi_card(c1,"Data Terakhir",str(prog["today"]),"","Tanggal input terakhir","#1F4E79")
    kpi_card(c2,"Akhir Bulan",str(prog["last_day"]),"","Target proyeksi","#1F4E79")
    kpi_card(c3,"Sisa Hari",prog["sisa_hari"],"hari","Dalam bulan berjalan","#7B3F00")
    st.markdown("<br>",unsafe_allow_html=True)

    for fk,fname,funit,fcolor,ficon in [
        ("coal","Coal","ton","#2C2C2C","🪨"),
        ("hsd","HSD","kL","#B8860B","⛽"),
        ("bio","Biomassa","ton","#2E7D32","🌿"),
    ]:
        avg_h=prog["avg_harian"].get(fk,0)
        stok_n=prog["stok_sekarang"].get(fk,0)
        proj_c=prog["proj_con_sisa"].get(fk,0)
        proj_s=prog["proj_stok_akhir"].get(fk,0)
        real_c=prog["real_con_ytm"].get(fk,0)
        total_b=prog["proj_total_bulan"].get(fk,0)
        pct=min(max((stok_n-proj_s)/stok_n*100 if stok_n>0 else 0,0),100)
        sc="bok" if proj_s>stok_n*0.2 else ("bwrn" if proj_s>0 else "bcrt")
        sl="Aman" if proj_s>stok_n*0.2 else ("Perlu perhatian" if proj_s>0 else "⚠️ HABIS")
        st.markdown(f"""<div class="sc">
          <div style="font-size:13px;font-weight:600;color:{fcolor};margin-bottom:8px">{ficon} {fname}</div>
          <div style="display:flex;gap:16px;flex-wrap:wrap">
            <div style="flex:1;min-width:180px">
              <div class="sr"><span>Avg konsumsi 7 hari terakhir</span><span><b>{avg_h:,.2f} {funit}/hari</b></span></div>
              <div class="sr"><span>Realisasi s.d. hari ini</span><span>{real_c:,.1f} {funit}</span></div>
              <div class="sr"><span>Proyeksi konsumsi sisa {prog["sisa_hari"]} hari</span><span>{proj_c:,.1f} {funit}</span></div>
              <div class="sr"><span>Proyeksi total bulan</span><span><b>{total_b:,.1f} {funit}</b></span></div>
            </div>
            <div style="flex:1;min-width:180px">
              <div class="sr"><span>Stok sekarang</span><span><b>{stok_n:,.1f} {funit}</b></span></div>
              <div class="sr"><span>Proyeksi stok akhir bulan</span><span><span class="{sc}">{proj_s:,.1f} {funit} — {sl}</span></span></div>
              <div style="margin-top:8px"><div style="font-size:10px;color:#9CA3AF;margin-bottom:2px">Stok terpakai: {pct:.0f}%</div>
              <div class="pb"><div class="pbf" style="width:{pct:.0f}%;background:{fcolor}"></div></div></div>
            </div>
          </div></div>""",unsafe_allow_html=True)

    # Chart proyeksi stok coal
    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown('<div class="sec">Grafik Proyeksi Stok Coal hingga Akhir Bulan</div>',unsafe_allow_html=True)
    sisa=prog["sisa_hari"]; today=prog["today"]; avg_c=prog["avg_harian"]["coal"]; stok_c=prog["stok_sekarang"]["coal"]
    pdates=[today+datetime.timedelta(days=i) for i in range(sisa+1)]
    pstoks=[stok_c-avg_c*i for i in range(sisa+1)]
    fp=go.Figure()
    fp.add_trace(go.Scatter(x=df_tr["tanggal"],y=df_tr["coal_stok_akhir"],mode="lines",name="Realisasi",line=dict(color="#2C2C2C",width=2)))
    fp.add_trace(go.Scatter(x=pdates,y=pstoks,mode="lines+markers",name="Proyeksi",line=dict(color="#F9A825",width=2,dash="dash"),marker=dict(size=5,symbol="circle-open")))
    fp.add_hline(y=5000,line_dash="dot",line_color="#C62828",annotation_text="Min 5.000 ton")
    # add_vline di plotly baru butuh timestamp dalam milidetik untuk axis datetime
    today_ts = int(pd.Timestamp(today).timestamp() * 1000)
    fp.add_vline(x=today_ts,line_dash="dash",line_color="#9CA3AF",annotation_text="Hari ini")
    fp.update_layout(height=280,margin=dict(t=10,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.12))
    st.plotly_chart(fp,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════
elif page=="📦 Stok":
    st.markdown('<div class="topbar"><h1>📦 Monitoring Stok Bahan Bakar</h1><p>Stok Awal · Penerimaan · Konsumsi · Stok Akhir · Estimasi Hari Pakai</p></div>',unsafe_allow_html=True)
    for fk,fname,funit,fcolor,stok_col,smin in [
        ("coal","🪨 Coal","ton","2C2C2C","coal_stok_akhir",5000),
        ("hsd","⛽ HSD","kL","B8860B","hsd_stok_akhir",10),
        ("bio","🌿 Biomassa","ton","2E7D32","bio_stok_akhir",50),
    ]:
        s=stok.get(fk,{})
        if not s: continue
        hp=s["hari_pakai"]; hc="bok" if hp>14 else ("bwrn" if hp>7 else "bcrt")
        ci,cc=st.columns([1,2])
        with ci:
            st.markdown(f"""<div class="sc">
              <div style="font-size:13px;font-weight:600;color:#{fcolor};margin-bottom:8px">{fname}</div>
              <div class="sr"><span>Stok Awal</span><span><b>{s['stok_awal']:,.1f} {funit}</b></span></div>
              <div class="sr"><span>Total Penerimaan</span><span>{s['total_rcv']:,.1f} {funit}</span></div>
              <div class="sr"><span>Total Konsumsi</span><span>{s['total_con']:,.1f} {funit}</span></div>
              <div class="sr"><span>Stok Akhir</span><span><b>{s['stok_akhir']:,.1f} {funit}</b></span></div>
              <div class="sr"><span>Avg konsumsi/hari</span><span>{s['avg_con_hari']:,.2f} {funit}</span></div>
              <div class="sr"><span>Estimasi hari pakai</span><span><span class="{hc}">{hp:.0f} hari</span></span></div>
            </div>""",unsafe_allow_html=True)
        with cc:
            st.markdown(f'<div class="sec">Tren Stok {fname}</div>',unsafe_allow_html=True)
            if stok_col in df_tr.columns:
                st.plotly_chart(area_chart(df_tr["tanggal"],df_tr[stok_col],fcolor.lstrip("#"),smin,f"Min {smin:,} {funit}",h=180),use_container_width=True)
        st.markdown("")

# ══════════════════════════════════════════════════════════════════════
elif page=="🪨 Coal":
    st.markdown('<div class="topbar"><h1>🪨 Monitoring Coal</h1><p>Penerimaan · Konsumsi · Stok · GCV</p></div>',unsafe_allow_html=True)
    s=stok.get("coal",{})
    c1,c2,c3,c4=st.columns(4)
    kpi_card(c1,"Stok Awal",f"{s.get('stok_awal',0):,.0f}","ton","Awal periode","#1F4E79")
    kpi_card(c2,"Total Konsumsi",f"{s.get('total_con',0):,.0f}","ton","Total periode","#2C2C2C")
    kpi_card(c3,"Stok Akhir",f"{s.get('stok_akhir',0):,.0f}","ton","Terakhir","#B8860B")
    kpi_card(c4,"Avg GCV",f"{df_h['gcv'].mean():,.0f}","kCal/kg","Rata-rata","#1565C0")
    st.markdown("<br>",unsafe_allow_html=True)
    ca,cb=st.columns(2)
    with ca:
        st.markdown('<div class="sec">Konsumsi + MA7</div>',unsafe_allow_html=True)
        fig=go.Figure()
        fig.add_bar(x=df_tr["tanggal"],y=df_tr["coal_con"],name="Konsumsi",marker_color="#2C2C2C",opacity=0.75)
        fig.add_scatter(x=df_tr["tanggal"],y=df_tr["coal_con_ma7"],name="MA7",mode="lines",line=dict(color="#F9A825",width=2))
        fig.update_layout(height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.12))
        st.plotly_chart(fig,use_container_width=True)
    with cb:
        st.markdown('<div class="sec">Tren Stok Coal</div>',unsafe_allow_html=True)
        st.plotly_chart(area_chart(df_tr["tanggal"],df_tr["coal_stok_akhir"],"2C2C2C",5000,"Min 5.000 ton",h=260),use_container_width=True)

elif page=="⛽ HSD":
    st.markdown('<div class="topbar"><h1>⛽ Monitoring HSD</h1><p>Penerimaan · Konsumsi · Stok</p></div>',unsafe_allow_html=True)
    s=stok.get("hsd",{})
    c1,c2,c3=st.columns(3)
    kpi_card(c1,"Stok Awal",f"{s.get('stok_awal',0):,.1f}","kL","Awal periode","#1F4E79")
    kpi_card(c2,"Total Konsumsi",f"{s.get('total_con',0):,.1f}","kL","Total periode","#B8860B")
    kpi_card(c3,"Stok Akhir",f"{s.get('stok_akhir',0):,.1f}","kL","Terakhir","#B8860B")
    st.markdown("<br>",unsafe_allow_html=True)
    ca,cb=st.columns(2)
    with ca:
        st.markdown('<div class="sec">Konsumsi HSD + MA7</div>',unsafe_allow_html=True)
        fig=go.Figure()
        fig.add_bar(x=df_tr["tanggal"],y=df_tr["hsd_con"],name="Konsumsi",marker_color="#B8860B",opacity=0.8)
        fig.add_scatter(x=df_tr["tanggal"],y=df_tr["hsd_con_ma7"],name="MA7",mode="lines",line=dict(color="#C62828",width=2))
        fig.update_layout(height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.12))
        st.plotly_chart(fig,use_container_width=True)
    with cb:
        st.markdown('<div class="sec">Tren Stok HSD</div>',unsafe_allow_html=True)
        st.plotly_chart(area_chart(df_tr["tanggal"],df_tr["hsd_stok_akhir"],"B8860B",10,"Min 10 kL",h=260),use_container_width=True)

elif page=="🌿 Biomassa":
    st.markdown('<div class="topbar"><h1>🌿 Monitoring Biomassa</h1><p>Co-firing · Konsumsi · Stok · Rasio</p></div>',unsafe_allow_html=True)
    s=stok.get("bio",{})
    total_f=s.get("total_con",0)+stok.get("coal",{}).get("total_con",1)
    rasio=s.get("total_con",0)/total_f*100 if total_f else 0
    c1,c2,c3,c4=st.columns(4)
    kpi_card(c1,"Stok Awal",f"{s.get('stok_awal',0):,.0f}","ton","Awal periode","#1F4E79")
    kpi_card(c2,"Total Konsumsi",f"{s.get('total_con',0):,.0f}","ton","Total periode","#2E7D32")
    kpi_card(c3,"Stok Akhir",f"{s.get('stok_akhir',0):,.0f}","ton","Terakhir","#639922")
    kpi_card(c4,"Rasio Co-firing",f"{rasio:.2f}","%","Biomassa/(Bio+Coal)","#185FA5")
    st.markdown("<br>",unsafe_allow_html=True)
    ca,cb=st.columns(2)
    with ca:
        st.markdown('<div class="sec">Konsumsi Biomassa + MA7</div>',unsafe_allow_html=True)
        fig=go.Figure()
        fig.add_bar(x=df_tr["tanggal"],y=df_tr["bio_con"],name="Konsumsi",marker_color="#2E7D32",opacity=0.8)
        fig.add_scatter(x=df_tr["tanggal"],y=df_tr["bio_con_ma7"],name="MA7",mode="lines",line=dict(color="#F9A825",width=2))
        fig.update_layout(height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.12))
        st.plotly_chart(fig,use_container_width=True)
    with cb:
        st.markdown('<div class="sec">Tren Rasio Co-firing</div>',unsafe_allow_html=True)
        fig2=go.Figure()
        fig2.add_trace(go.Scatter(x=df_tr["tanggal"],y=df_tr["rasio_co"],fill="tozeroy",mode="lines",line=dict(color="#2E7D32",width=2),fillcolor="rgba(46,125,50,0.15)"))
        fig2.add_hline(y=3.5,line_dash="dot",line_color="#1565C0",annotation_text="Target 3.5%")
        fig2.update_layout(height=260,margin=dict(t=5,b=5,l=5,r=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2,use_container_width=True)

elif page=="📈 Target vs Realisasi":
    st.markdown('<div class="topbar"><h1>📈 Target vs Realisasi</h1><p>KPI Energi Primer Bulanan & YTD</p></div>',unsafe_allow_html=True)
    if df_t.empty:
        st.info("Data target belum tersedia.")
    else:
        kc=df_t.columns[0]; tc=df_t.columns[2] if len(df_t.columns)>2 else None
        rc=df_t.columns[3] if len(df_t.columns)>3 else None; sc_=df_t.columns[1] if len(df_t.columns)>1 else None
        stc=df_t.columns[6] if len(df_t.columns)>6 else None
        if tc and rc:
            g1,g2=st.columns(2)
            for i,(_,row) in enumerate(df_t.head(8).iterrows()):
                col=g1 if i%2==0 else g2
                tgt=float(str(row.get(tc,0)).replace(",",".")); real=float(str(row.get(rc,0)).replace(",","."))
                nama=str(row.get(kc,"")); sat=str(row.get(sc_,""))
                inv=any(x in nama for x in ["Heat Rate","SFC"])
                color="#2E7D32" if (real<=tgt if inv else real>=tgt*0.95) else "#F57F17"
                with col:
                    fig=go.Figure(go.Indicator(
                        mode="gauge+number+delta",value=real,
                        delta={"reference":tgt,"valueformat":".1f",
                               "increasing":{"color":"#C62828" if inv else "#2E7D32"},
                               "decreasing":{"color":"#2E7D32" if inv else "#C62828"}},
                        number={"suffix":f" {sat}","font":{"size":20}},
                        title={"text":f"<b>{nama}</b><br><span style='font-size:10px'>Target: {tgt:,.1f} {sat}</span>"},
                        gauge={"axis":{"range":[0,tgt*1.3]},"bar":{"color":color,"thickness":0.25},
                               "steps":[{"range":[0,tgt*0.8],"color":"#FFEBEE"},{"range":[tgt*0.8,tgt],"color":"#FFF8E1"},{"range":[tgt,tgt*1.3],"color":"#E8F5E9"}],
                               "threshold":{"line":{"color":"#1F4E79","width":3},"value":tgt,"thickness":0.85}}))
                    fig.update_layout(height=195,margin=dict(t=55,b=0,l=20,r=20),paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig,use_container_width=True)
        st.markdown('<div class="sec">Tabel Lengkap</div>',unsafe_allow_html=True)
        def ss(v):
            if "BAIK" in str(v): return "background-color:#E8F5E9;color:#2E7D32;font-weight:600"
            if "DEVIASI" in str(v): return "background-color:#FFF8E1;color:#F57F17;font-weight:600"
            return ""
        styled=df_t[df_t.columns[:8]].style.map(ss,subset=[stc] if stc else [])
        st.dataframe(styled,use_container_width=True,height=300,hide_index=True)
