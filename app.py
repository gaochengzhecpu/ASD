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
# Page & theme
# ============================================================
st.set_page_config(
    page_title="EMA Approved ASD Drugs",
    page_icon="💊",
    layout="wide",
)

DATA_LAST_UPDATED = "2026-07-25"

# ============================================================
# Data loading & cleaning
# ============================================================
@st.cache_data
def load_data():
    candidates = [
        'excel/gemini_epar_analysis.xlsx',   # local dev (project folder)
        'gemini_epar_analysis.xlsx',          # repo root (Streamlit Cloud)
    ]
    file_path = next((p for p in candidates if os.path.exists(p)), None)
    if file_path is None:
        return pd.DataFrame()

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


df = load_data()
if df.empty:
    st.error("Data file not found. Expected `excel/gemini_epar_analysis.xlsx` (local) or `gemini_epar_analysis.xlsx` (repo root).")
    st.stop()

df_asd = df[df['Drug Solid Form'].astype(str).str.upper() == 'ASD'].copy()

PLOTLY_TEMPLATE = 'plotly_white'
ACCENT = '#0E7C7B'

# ============================================================
# Header & KPIs
# ============================================================
st.title("💊 EMA-Approved Oral ASD Drugs")
st.caption(
    f"Amorphous Solid Dispersion (ASD) drugs approved by the European Medicines Agency, "
    f"extracted from EPAR Quality Aspects via LLM · Data updated {DATA_LAST_UPDATED}"
)

asd_years = df_asd['Approval Year'].dropna()
top_polymer = (pd.Series([p for l in df_asd['Polymer List'] for p in l])
               .value_counts().idxmax() if df_asd['Polymer List'].map(len).sum() else 'N/A')
method_counts_all = df_asd.loc[df_asd['ASD Method Clean'] != 'N/A', 'ASD Method Clean'].value_counts()
top_method = method_counts_all.idxmax() if len(method_counts_all) else 'N/A'
asd_2026 = int((df_asd['Approval Year'] == 2026).sum())

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Confirmed ASD Drugs", len(df_asd))
k2.metric("Drugs Analyzed", len(df))
k3.metric("New ASD in 2026", asd_2026)
k4.metric("Top Polymer", top_polymer)
k5.metric("Top ASD Method", top_method)

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🔍 Drug Database", "🧪 Formulation Insights", "ℹ️ About"])

# ============================================================
# Tab 1 — Overview
# ============================================================
with tab1:
    c1, c2 = st.columns(2)

    with c1:
        if not asd_years.empty:
            yr = asd_years.astype(int).value_counts().sort_index()
            fig = go.Figure()
            fig.add_bar(x=yr.index, y=yr.values, name='Per year',
                        marker_color=ACCENT, text=yr.values, textposition='outside')
            fig.add_scatter(x=yr.index, y=yr.cumsum(), name='Cumulative',
                            yaxis='y2', mode='lines+markers', line=dict(color='#E76F51'))
            fig.update_layout(
                title="ASD Approvals per Year (cumulative overlay)",
                template=PLOTLY_TEMPLATE, height=380,
                yaxis=dict(title='Approvals', tickmode='linear', dtick=1),
                yaxis2=dict(title='Cumulative', overlaying='y', side='right', showgrid=False),
                xaxis=dict(tickmode='linear', dtick=1),
                legend=dict(orientation='h', y=1.12),
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No approval-year data.")

    with c2:
        solid = df['Drug Solid Form'].fillna('N/A').replace('', 'N/A').value_counts().reset_index()
        solid.columns = ['Solid Form', 'Count']
        fig2 = px.pie(solid, values='Count', names='Solid Form', hole=0.45,
                      title=f"Solid Form Across All {len(df)} Analyzed Drugs",
                      color_discrete_sequence=px.colors.sequential.Teal)
        fig2.update_layout(template=PLOTLY_TEMPLATE, height=380)
        st.plotly_chart(fig2, width='stretch')

    c3, c4 = st.columns(2)

    with c3:
        tc = df_asd['Therapeutic Category'].dropna().str.strip()
        tc = tc[tc.ne('') & tc.ne('N/A')]
        tc_counts = tc.value_counts().head(10).reset_index()
        tc_counts.columns = ['Therapeutic Category', 'Count']
        fig3 = px.bar(tc_counts, x='Count', y='Therapeutic Category', orientation='h',
                      title="ASD Drugs by Therapeutic Category (Top 10)",
                      color_discrete_sequence=[ACCENT])
        fig3.update_layout(template=PLOTLY_TEMPLATE, height=420,
                           yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig3, width='stretch')

    with c4:
        # Polymer × method heatmap
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
                             color_continuous_scale='Teal')
            fig4.update_layout(template=PLOTLY_TEMPLATE, height=420)
            st.plotly_chart(fig4, width='stretch')
        else:
            st.info("No polymer/method data.")

# ============================================================
# Tab 2 — Drug Database
# ============================================================
with tab2:
    st.markdown("#### Search & Filter")

    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        search = st.text_input("Search drug name / active substance / company")
    with f2:
        solid_opts = sorted(df['Drug Solid Form'].dropna().unique())
        solid_sel = st.multiselect("Solid form", solid_opts, default=solid_opts)
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

    st.markdown("#### Drug Detail")
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
    st.markdown("#### Excipient Functional Roles in ASD Formulations")

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
                          color_discrete_sequence=['#E76F51'])
            fig6.update_layout(template=PLOTLY_TEMPLATE, height=400,
                               yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig6, width='stretch')

    # Superdisintegrant choice by ASD method
    st.markdown("#### Superdisintegrant Choice by ASD Method")
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
                      color_discrete_sequence=[ACCENT, '#E76F51'])
        fig7.update_layout(template=PLOTLY_TEMPLATE, height=380)
        st.plotly_chart(fig7, width='stretch')

    st.markdown("#### 💡 Insights from the Data")
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
        st.info(f"**HPMCAS & Copovidone dominate** the ASD polymer space, repeatedly stabilizing "
                f"these difficult, poorly soluble APIs.")
        st.info("**Oncology is the biggest benefactor.** Over half of these insoluble ASD APIs are "
                "targeted cancer therapies (mostly kinase inhibitors). Salt-based dissolution modulators "
                "(e.g., NaCl in Zepatier, Aquipta, Tukysa) appear as a niche but clever trick.")

# ============================================================
# Tab 4 — About
# ============================================================
with tab4:
    st.markdown("#### How this dataset was built")
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

    st.markdown("#### Caveats")
    st.markdown("""
- Fields are **AI-extracted** from public assessment reports; always confirm critical values against the
  original EPAR before citing.
- `Drug loading` is often not disclosed in EPARs and may be `N/A`.
- Non-oral products flagged during review are kept in the database with `Oral Administration = No`.
""")

    st.markdown("#### 🙏 Acknowledgements")
    st.info("Thank you my wife Xiuli Li for the support. Thank my friend Tianyi Li, Yongjian Wang, Fan Meng, "
            "and Zoe Wen for brainstorming. Thank my manager Fady Ibrahim for the encouragement. Thank my PhD "
            "advisor Kevin J. Edgar, my postdoc advisor Lynne Taylor, and my mentor Tze Ning Hiew for me to "
            "start work on amorphous solid dispersion.")

    st.markdown("---")
    st.markdown("<div style='text-align: center'>Built with Streamlit & Gemini · Data: EMA EPAR</div>",
                unsafe_allow_html=True)
