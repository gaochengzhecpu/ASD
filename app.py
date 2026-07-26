"""
EMA Approved ASD Drugs — Streamlit Dashboard
=============================================
Data: CMC properties extracted from EMA EPAR "Quality aspects" sections
      by Gemini (see PROJECT_SUMMARY.md), stored in gemini_epar_analysis.xlsx.

Run locally:   streamlit run app.py
"""
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# Page & style
# ============================================================
st.set_page_config(
    page_title="EMA Approved ASD Drugs",
    page_icon="💊",
    layout="wide",
)

DATA_LAST_UPDATED = "2026-07-25"
ACCENT = "#1D5FA8"    # primary pharma blue
ACCENT2 = "#D97706"   # amber highlight
BLUE_DARK = "#0F3D6E"

st.markdown("""
<style>
/* ---------- header band ---------- */
.header-band {
    background: linear-gradient(100deg, #0F3D6E 0%, #1D5FA8 60%, #3B83C4 100%);
    border-radius: 14px;
    padding: 30px 36px 26px 36px;
    margin-bottom: 20px;
    box-shadow: 0 4px 14px rgba(29, 95, 168, .22);
}
.header-band h1 { color: #FFFFFF; margin: 0; font-size: 2.1rem; font-weight: 800; letter-spacing: .3px; }
.header-band p  { color: #D3E4F5; margin: 8px 0 0 0; font-size: .95rem; }
.header-band .badge {
    display: inline-block; background: rgba(255,255,255,.16); color: #EAF2FA;
    border: 1px solid rgba(255,255,255,.35); border-radius: 999px;
    padding: 3px 12px; font-size: .78rem; margin-top: 12px; margin-right: 8px;
}

/* ---------- KPI cards ---------- */
.kpi-card {
    background: #FFFFFF; border: 1px solid #E2EAF2; border-radius: 14px;
    padding: 16px 20px 14px 20px; box-shadow: 0 2px 6px rgba(29, 95, 168, .07);
    border-top: 4px solid #1D5FA8; height: 118px;
}
.kpi-card.orange { border-top-color: #D97706; }
.kpi-label { font-size: .82rem; color: #5B7282; font-weight: 600; text-transform: uppercase; letter-spacing: .4px; }
.kpi-value { font-size: 2.1rem; font-weight: 800; color: #1D5FA8; line-height: 1.15; }
.kpi-card.orange .kpi-value { color: #D97706; }
.kpi-sub   { font-size: .76rem; color: #8AA3AD; margin-top: 2px; }

/* ---------- section titles ---------- */
.sec-title {
    color: #0F3D6E; font-weight: 700; font-size: 1.15rem;
    border-left: 5px solid #1D5FA8; padding-left: 10px; margin: 6px 0 12px 0;
}

/* ---------- tighten default padding ---------- */
.block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Data loading & cleaning
# ============================================================
def _find_data_file():
    candidates = [
        'excel/gemini_epar_analysis.xlsx',   # local dev (project folder)
        'gemini_epar_analysis.xlsx',          # repo root (Streamlit Cloud)
    ]
    return next((p for p in candidates if os.path.exists(p)), None)


@st.cache_data
def load_data(file_path, file_mtime):
    # file_mtime participates in the cache key: editing the xlsx invalidates cache
    df = pd.read_excel(file_path, sheet_name='All_Drugs')
    df['Approval Year'] = pd.to_numeric(df['Approval Year'], errors='coerce')

    # ---- Normalize polymer names ----
    def clean_polymer(p):
        pl = str(p).lower()
        if 'succinate' in pl or 'hpmcas' in pl or 'hpmc-as' in pl:
            return 'HPMCAS'
        if 'copovidone' in pl or 'vinyl acetate copolymer' in pl:
            return 'Copovidone'
        if ('hpmc' in pl or 'hypromellose' in pl) and 'phthalate' not in pl:
            return 'HPMC'
        if 'povidone' in pl and 'copovidone' not in pl:
            return 'Povidone (PVP)'
        if 'soluplus' in pl:
            return 'Soluplus'
        return str(p).strip()

    def polymer_list(s):
        if pd.isna(s) or str(s).strip() in ('', 'N/A', 'nan'):
            return []
        parts = str(s).replace(';', ',').split(',')
        return sorted({clean_polymer(p) for p in parts if p.strip() and p.strip().lower() != 'n/a'})

    df['Polymer List'] = df['ASD Polymer'].apply(polymer_list)
    df['ASD Polymer Clean'] = df['Polymer List'].apply(lambda l: ', '.join(l) if l else 'N/A')

    # ---- Normalize manufacturing methods ----
    def clean_method(m):
        ml = str(m).lower()
        if 'spray' in ml:
            return 'Spray Drying'
        if 'melt' in ml or 'hme' in ml or 'extrusion' in ml:
            return 'Hot-Melt Extrusion'
        if 'precipitation' in ml:
            return 'Co-precipitation'
        if pd.isna(m) or ml.strip() in ('', 'n/a', 'nan'):
            return 'N/A'
        return str(m).strip()

    df['ASD Method Clean'] = df['ASD Manufacturing Method'].apply(clean_method)

    # ---- Excipient functional classification ----
    categories = {
        'Filler': ['cellulose', 'lactose', 'mannitol', 'calcium hydrogen phosphate', 'isomalt', 'sucrose'],
        'Disintegrant': ['croscarmellose', 'crospovidone', 'sodium starch glycolate'],
        'Lubricant': ['magnesium stearate', 'sodium stearyl fumarate', 'stearic acid'],
        'Glidant': ['silica', 'talc'],
        'Coating/Polymer': ['hypromellose', 'copovidone', 'povidone', 'macrogol', 'polyvinyl alcohol',
                            'shellac', 'carnauba', 'methacrylic', 'triethyl citrate'],
        'Colorant': ['titanium dioxide', 'iron oxide', 'indigo carmine', 'brilliant blue'],
        'Surfactant': ['laurilsulfate', 'poloxamer', 'sorbitan', 'polysorbate', 'docusate'],
        'Plasticizer': ['triacetin', 'propylene glycol', 'glycerol'],
    }

    def classify_excipients(exc):
        out = {k: [] for k in list(categories) + ['Other']}
        if pd.isna(exc) or not str(exc).strip():
            return out
        for p in str(exc).replace(';', ',').split(','):
            p = p.strip()
            if not p:
                continue
            for cat, kws in categories.items():
                if any(kw in p.lower() for kw in kws):
                    out[cat].append(p.title())
                    break
            else:
                out['Other'].append(p.title())
        return out

    df['Excipient Categories'] = df['Excipients'].apply(classify_excipients)
    return df


_data_file = _find_data_file()
df = load_data(_data_file, os.path.getmtime(_data_file)) if _data_file else pd.DataFrame()
if df.empty:
    st.error("Data file not found. Expected `excel/gemini_epar_analysis.xlsx` (local) or `gemini_epar_analysis.xlsx` (repo root).")
    st.stop()

df_asd = df[df['Drug Solid Form'].astype(str).str.upper() == 'ASD'].copy()

PLOTLY_TEMPLATE = 'plotly_white'

# ============================================================
# Header band & KPI cards
# ============================================================
st.markdown(f"""
<div class="header-band">
  <h1>💊 EMA-Approved Oral ASD Drugs</h1>
  <p>Amorphous Solid Dispersion (ASD) drugs approved by the European Medicines Agency,
     extracted from EPAR <i>Quality aspects</i> sections with an LLM pipeline.</p>
  <span class="badge">Data updated {DATA_LAST_UPDATED}</span>
  <span class="badge">{len(df)} drugs analyzed</span>
  <span class="badge">{len(df_asd)} confirmed ASD</span>
</div>
""", unsafe_allow_html=True)

asd_years = df_asd['Approval Year'].dropna()
top_polymer = (pd.Series([p for l in df_asd['Polymer List'] for p in l])
               .value_counts().idxmax() if df_asd['Polymer List'].map(len).sum() else 'N/A')
method_counts_all = df_asd.loc[df_asd['ASD Method Clean'] != 'N/A', 'ASD Method Clean'].value_counts()
top_method = method_counts_all.idxmax() if len(method_counts_all) else 'N/A'
df_asd_2026 = df_asd[df_asd['Approval Year'] == 2026]
new26_names = ' · '.join(df_asd_2026['Drug Name']) if len(df_asd_2026) else ''


def kpi_card(col, label, value, sub='', orange=False):
    with col:
        st.markdown(f"""
        <div class="kpi-card{' orange' if orange else ''}">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)


k1, k2, k3, k4, k5 = st.columns(5)
kpi_card(k1, "Confirmed ASD Drugs", len(df_asd), f"of {len(df)} oral drugs analyzed")
kpi_card(k2, "Latest ASD Approvals", int(asd_years.max()) if not asd_years.empty else 'N/A',
         new26_names, orange=True)
kpi_card(k3, "New ASD in 2026", len(df_asd_2026), new26_names)
kpi_card(k4, "Top Polymer", top_polymer, "most used ASD carrier")
kpi_card(k5, "Top ASD Method", top_method, "most used technology")

st.markdown("<div style='height: 14px'></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🔍 Drug Database", "🧪 Formulation Insights", "ℹ️ About"])

# ============================================================
# Tab 1 — Overview
# ============================================================
with tab1:
    t1, t2 = st.columns(2)

    with t1:
        if not asd_years.empty:
            yr = asd_years.astype(int).value_counts().sort_index()
            fig = px.bar(x=yr.index, y=yr.values, text=yr.values,
                         title="ASD approvals per year",
                         color_discrete_sequence=[ACCENT])
            fig.update_traces(textposition='outside', textfont_size=13,
                              textfont_color=BLUE_DARK)
            fig.update_layout(template=PLOTLY_TEMPLATE, height=400, showlegend=False,
                              margin=dict(t=50, b=20),
                              xaxis=dict(tickmode='linear', dtick=1, title=None,
                                         range=[yr.index.min() - 0.6, yr.index.max() + 0.6]),
                              yaxis=dict(title='Approvals', tickmode='linear', dtick=1,
                                         range=[0, max(yr.values) + 1.2]))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No approval-year data.")

    with t2:
        if not asd_years.empty:
            cum = yr.cumsum()
            total_cum = int(cum.iloc[-1])
            figc = go.Figure()
            figc.add_scatter(x=cum.index, y=cum.values, mode='lines+markers+text',
                             line=dict(color=ACCENT2, width=3), marker=dict(size=6),
                             fill='tozeroy', fillcolor='rgba(217, 119, 6, .10)',
                             text=[''] * (len(cum) - 1) + [str(total_cum)],
                             textposition='top left',
                             textfont=dict(size=16, color=ACCENT2),
                             cliponaxis=False)
            figc.update_layout(template=PLOTLY_TEMPLATE, height=400, showlegend=False,
                               title=f"Cumulative ASD approvals — {total_cum} total",
                               margin=dict(t=50, b=20, r=50),
                               xaxis=dict(tickmode='linear', dtick=1, title=None,
                                          range=[cum.index.min() - 0.6, cum.index.max() + 1.2]),
                               yaxis=dict(title='Cumulative',
                                          range=[0, total_cum * 1.15]))
            st.plotly_chart(figc, width='stretch')

    m1, m2 = st.columns(2)

    with m1:
        # Solid form among oral drugs only; N/A (liquids etc.) excluded from the pie
        df_oral = df[df['Oral Administration'].astype(str).str.lower().eq('yes')]
        solid_raw = df_oral['Drug Solid Form'].fillna('N/A').replace('', 'N/A')
        n_na = int((solid_raw == 'N/A').sum())
        solid = solid_raw[solid_raw != 'N/A'].value_counts().reset_index()
        solid.columns = ['Solid Form', 'Count']
        fig2 = px.pie(solid, values='Count', names='Solid Form', hole=0.45,
                      title=f"Solid form of {len(df_oral)} oral drugs",
                      color='Solid Form',
                      color_discrete_map={'ASD': ACCENT2, 'Crystalline': ACCENT,
                                          'Pure Amorphous': '#7FA8D9'})
        fig2.update_layout(template=PLOTLY_TEMPLATE, height=420)
        st.plotly_chart(fig2, width='stretch')
        st.caption(f"Excludes {len(df) - len(df_oral)} non-oral products and "
                   f"{n_na} liquid/non-solid formulations (N/A).")

    with m2:
        poly_series = pd.Series([p for l in df_asd['Polymer List'] for p in l])
        if len(poly_series):
            pc = poly_series.value_counts().head(10).reset_index()
            pc.columns = ['Polymer', 'Drugs']
            figp = px.bar(pc, x='Drugs', y='Polymer', orientation='h',
                          title="Top ASD polymers",
                          color_discrete_sequence=[ACCENT])
            figp.update_layout(template=PLOTLY_TEMPLATE, height=420,
                               yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(figp, width='stretch')
        else:
            st.info("No polymer data.")

    # Polymer × method heatmap (full width)
    rows = []
    for _, r in df_asd.iterrows():
        for p in r['Polymer List']:
            rows.append({'Polymer': p, 'Method': r['ASD Method Clean']})
    if rows:
        pm = pd.DataFrame(rows)
        pm = pm[pm['Method'] != 'N/A']
        ct = pd.crosstab(pm['Polymer'], pm['Method'])
        ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False).index]
        fig4 = px.imshow(ct, text_auto=True, aspect='auto',
                         title="Polymer × Manufacturing Method (drug count)",
                         color_continuous_scale='Blues')
        fig4.update_layout(template=PLOTLY_TEMPLATE, height=460)
        st.plotly_chart(fig4, width='stretch')
    else:
        st.info("No polymer/method data.")

# ============================================================
# Tab 2 — Drug Database
# ============================================================
with tab2:
    st.markdown('<div class="sec-title">Search & Filter</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        search = st.text_input("Search drug name / active substance / company")
    with f2:
        solid_opts = sorted(df['Drug Solid Form'].dropna().unique())
        solid_sel = st.multiselect("Solid form", solid_opts,
                                   default=['ASD'] if 'ASD' in solid_opts else solid_opts)
    with f3:
        years_all = df['Approval Year']
        y_min, y_max = int(years_all.min()), int(years_all.max())
        year_sel = st.slider("Approval year range", y_min, y_max, (y_min, y_max))

    f4, f5, f6 = st.columns([2, 2, 2])
    with f4:
        poly_opts = sorted({p for l in df['Polymer List'] for p in l})
        poly_sel = st.multiselect("ASD polymer", poly_opts)
    with f5:
        method_opts = sorted(m for m in df['ASD Method Clean'].unique() if m != 'N/A')
        method_sel = st.multiselect("ASD method", method_opts)
    with f6:
        oral_only = st.checkbox("Oral drugs only", value=True)

    mask = pd.Series(True, index=df.index)
    if search:
        s = search.lower()
        mask &= (df['Drug Name'].str.lower().str.contains(s, na=False)
                 | df['Active Substance'].astype(str).str.lower().str.contains(s, na=False)
                 | df['Company'].astype(str).str.lower().str.contains(s, na=False))
    if solid_sel:
        mask &= df['Drug Solid Form'].isin(solid_sel)
    mask &= (df['Approval Year'].isna()
             | ((df['Approval Year'] >= year_sel[0]) & (df['Approval Year'] <= year_sel[1])))
    if poly_sel:
        mask &= df['Polymer List'].apply(lambda l: any(p in l for p in poly_sel))
    if method_sel:
        mask &= df['ASD Method Clean'].isin(method_sel)
    if oral_only:
        mask &= df['Oral Administration'].astype(str).str.lower().eq('yes')

    filtered = df[mask].copy()
    st.markdown(f"**{len(filtered)}** drugs match (of {len(df)} total)")

    show_cols = ['Drug Name', 'Active Substance', 'Company', 'Drug Solid Form', 'Dosage Form',
                 'Approval Year', 'ASD Polymer Clean', 'ASD Method Clean', 'Therapeutic Category']
    display = filtered[[c for c in show_cols if c in filtered.columns]].rename(
        columns={'ASD Polymer Clean': 'ASD Polymer', 'ASD Method Clean': 'ASD Method'})
    st.dataframe(display, width='stretch', hide_index=True)

    st.download_button(
        "⬇️ Download filtered data (CSV)",
        display.to_csv(index=False).encode('utf-8-sig'),
        file_name="ema_asd_drugs_filtered.csv",
        mime="text/csv",
    )

    st.markdown('<div class="sec-title">Drug Detail</div>', unsafe_allow_html=True)
    if len(filtered):
        pick = st.selectbox("Select a drug", sorted(filtered['Drug Name'].unique()))
        if pick:
            r = filtered[filtered['Drug Name'] == pick].iloc[0]
            is_asd = str(r['Drug Solid Form']).upper() == 'ASD'
            if is_asd:
                st.success(f"**{pick}** — confirmed ASD")
            else:
                st.info(f"**{pick}** — solid form: {r['Drug Solid Form']}")
            d1, d2 = st.columns(2)
            with d1:
                st.markdown("**General**")
                st.write(f"- Active substance: {r['Active Substance']}")
                st.write(f"- Company: {r.get('Company', 'N/A')}")
                st.write(f"- Approval year: {int(r['Approval Year']) if pd.notna(r['Approval Year']) else 'N/A'}")
                st.write(f"- Therapeutic category: {r.get('Therapeutic Category', 'N/A')}")
                st.write(f"- Dosage form: {r.get('Dosage Form', 'N/A')}")
                st.write(f"- Strengths: {r.get('Dose Strengths', 'N/A')}")
            with d2:
                st.markdown("**Formulation (CMC)**")
                st.write(f"- Solid form: {r['Drug Solid Form']}")
                st.write(f"- ASD polymer: {r['ASD Polymer Clean']}")
                st.write(f"- ASD method: {r['ASD Method Clean']}")
                st.write(f"- Drug loading: {r.get('Drug Loading', 'N/A')}")
                st.write(f"- Process: {r.get('Manufacturing Process', 'N/A')}")
            st.markdown("**Formulation summary**")
            st.write(r.get('Formulation Summary', 'N/A'))
            with st.expander("All excipients"):
                st.write(r.get('Excipients', 'N/A'))
    else:
        st.warning("No drugs match the current filters.")

# ============================================================
# Tab 3 — Formulation Insights
# ============================================================
with tab3:
    st.markdown('<div class="sec-title">Excipient Functional Roles in ASD Formulations</div>',
                unsafe_allow_html=True)

    cat_totals = {}
    exc_counter = {}
    for cats in df_asd['Excipient Categories']:
        for cat, items in cats.items():
            cat_totals[cat] = cat_totals.get(cat, 0) + len(items)
            for it in items:
                exc_counter[it] = exc_counter.get(it, 0) + 1

    i1, i2 = st.columns(2)
    with i1:
        if cat_totals:
            ct = pd.DataFrame(sorted(cat_totals.items(), key=lambda x: x[1]),
                              columns=['Category', 'Occurrences'])
            fig5 = px.bar(ct, x='Occurrences', y='Category', orientation='h',
                          title="Excipient Categories Across ASD Drugs",
                          color_discrete_sequence=[ACCENT])
            fig5.update_layout(template=PLOTLY_TEMPLATE, height=400)
            st.plotly_chart(fig5, width='stretch')

    with i2:
        if exc_counter:
            top_exc = pd.DataFrame(sorted(exc_counter.items(), key=lambda x: -x[1])[:15],
                                   columns=['Excipient', 'Drugs'])
            fig6 = px.bar(top_exc, x='Drugs', y='Excipient', orientation='h',
                          title="Top 15 Individual Excipients",
                          color_discrete_sequence=[ACCENT2])
            fig6.update_layout(template=PLOTLY_TEMPLATE, height=400,
                               yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig6, width='stretch')

    # Superdisintegrant choice by ASD method
    st.markdown('<div class="sec-title">Superdisintegrant Choice by ASD Method</div>',
                unsafe_allow_html=True)
    rows = []
    for _, r in df_asd.iterrows():
        m = r['ASD Method Clean']
        if m == 'N/A':
            continue
        exc = str(r.get('Excipients', '')).lower()
        rows.append({'Method': m, 'Disintegrant': 'Croscarmellose Sodium',
                     'Used': 'croscarmellose' in exc})
        rows.append({'Method': m, 'Disintegrant': 'Crospovidone',
                     'Used': 'crospovidone' in exc})
    sd = pd.DataFrame(rows)
    if len(sd):
        sd = sd[sd['Used']].groupby(['Method', 'Disintegrant']).size().reset_index(name='Drugs')
        fig7 = px.bar(sd, x='Method', y='Drugs', color='Disintegrant', barmode='group',
                      title="Croscarmellose vs Crospovidone Usage by ASD Method",
                      color_discrete_sequence=[ACCENT, ACCENT2])
        fig7.update_layout(template=PLOTLY_TEMPLATE, height=380)
        st.plotly_chart(fig7, width='stretch')

    st.markdown('<div class="sec-title">💡 Insights from the Data</div>', unsafe_allow_html=True)
    total_asd = len(df_asd)
    ccs_n = df_asd['Excipients'].str.contains('croscarmellose', case=False, na=False).sum()
    csp_n = df_asd['Excipients'].str.contains('crospovidone', case=False, na=False).sum()
    mgs_n = df_asd['Excipients'].str.contains('magnesium stearate', case=False, na=False).sum()

    fcol1, fcol2 = st.columns(2)
    with fcol1:
        st.info(f"**Magnesium Stearate rules them all.** It appears in **{mgs_n}/{total_asd}** ASD "
                f"oral drugs — the undisputed king of downstream tableting lubricants.")
        st.info(f"**The Superdisintegrant gap.** Croscarmellose Sodium (**{ccs_n}** drugs) crushes "
                f"Crospovidone (**{csp_n}** drugs). Its extreme swelling and fibrous structure tear apart "
                f"dense, glassy polymeric matrices from spray drying or HME.")
    with fcol2:
        st.info("**HPMCAS & Copovidone dominate** the ASD polymer space, repeatedly stabilizing "
                "these difficult, poorly soluble APIs.")
        st.info("**Oncology is the biggest benefactor.** Over half of these insoluble ASD APIs are "
                "targeted cancer therapies (mostly kinase inhibitors). Salt-based dissolution modulators "
                "(e.g., NaCl in Zepatier, Aquipta, Tukysa) appear as a niche but clever trick.")

# ============================================================
# Tab 4 — About
# ============================================================
with tab4:
    st.markdown('<div class="sec-title">How this dataset was built</div>', unsafe_allow_html=True)
    st.markdown(f"""
1. **Source**: EMA centrally authorised medicines report — all innovative human medicines approved since 2010
   (generics and biosimilars excluded).
2. **Screening**: oral route determined via the EMA Article 57 database; **{len(df)}** oral drug products analyzed.
3. **Document analysis**: the *Quality aspects* section of each EPAR (public assessment report) was extracted
   and read by **Google Gemini** with an enforced JSON schema, pulling out 17 CMC fields per drug —
   solid form (ASD / amorphous / crystalline), excipients, ASD polymer & manufacturing method, process flow, etc.
4. **Verification**: ASD assignments were cross-checked against the formulation descriptions.
5. **Last update**: {DATA_LAST_UPDATED} — covers EMA approvals through July 2026.
""")

    st.markdown('<div class="sec-title">Caveats</div>', unsafe_allow_html=True)
    st.markdown("""
- Fields are **AI-extracted** from public assessment reports; always confirm critical values against the
  original EPAR before citing.
- `Drug loading` is often not disclosed in EPARs and may be `N/A`.
- Non-oral products flagged during review are kept in the database with `Oral Administration = No`.
""")

    st.markdown('<div class="sec-title">🙏 Acknowledgements</div>', unsafe_allow_html=True)
    st.info("Thank you my wife Xiuli Li for the support. Thank my friend Tianyi Li, Yongjian Wang, Fan Meng, "
            "and Zoe Wen for brainstorming. Thank my manager Fady Ibrahim for the encouragement. Thank my PhD "
            "advisor Kevin J. Edgar, my postdoc advisor Lynne Taylor, and my mentor Tze Ning Hiew for me to "
            "start work on amorphous solid dispersion.")

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #8AA3AD'>Built with Streamlit & Gemini · Data: EMA EPAR</div>",
                unsafe_allow_html=True)
