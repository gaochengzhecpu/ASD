import streamlit as st
import pandas as pd
import plotly.express as px

# Set page layout
st.set_page_config(page_title="EMA ASD Drugs Dashboard", page_icon="💊", layout="wide")

st.title("EMA Approved Oral ASD Drugs Dashboard (2010 - 2025)")
st.markdown("Interactive dashboard exploring the Amorphous Solid Dispersion (ASD) drugs approved by the European Medicines Agency.")

@st.cache_data
def load_data():
    import os
    file_path = 'c:/Users/CHENGZHE GAO/Desktop/coding/ASD/excel/gemini_epar_analysis.xlsx'
    # Fallback to local relative path for Streamlit Cloud deployment
    if not os.path.exists(file_path):
        file_path = 'gemini_epar_analysis.xlsx'
        
    try:
        # Read the main sheet and filter for ASD
        df = pd.read_excel(file_path, sheet_name='All_Drugs')
        df = df[df['Drug Solid Form'].astype(str).str.contains('ASD', na=False, case=False)].copy()
        
        # Clean up Polymer names
        if 'ASD Polymer' in df.columns:
            df['ASD Polymer'] = df['ASD Polymer'].fillna('Unknown').astype(str)
            def clean_polymer(p_str):
                p_lower = p_str.lower()
                if 'succinate' in p_lower or 'hpmcas' in p_lower or 'hpmc-as' in p_lower:
                    return 'Hypromellose acetate succinate (HPMCAS)'
                if 'copovidone' in p_lower or 'vinyl acetate copolymer' in p_lower:
                    return 'Copovidone'
                if ('hpmc' in p_lower or 'hypromellose' in p_lower) and 'phthalate' not in p_lower and 'succinate' not in p_lower:
                    return 'Hypromellose (HPMC)'
                if 'povidone' in p_lower and 'copovidone' not in p_lower:
                    return 'Povidone (PVP)'
                return p_str.strip()
            
            # Since some might be comma-separated, split, clean, and re-join
            def process_polymer_list(p_str):
                if p_str == 'Unknown': return p_str
                parts = p_str.replace(';', ',').split(',')
                cleaned = [clean_polymer(p.strip()) for p in parts if p.strip()]
                return ', '.join(sorted(list(set(cleaned))))
                
            df['ASD Polymer'] = df['ASD Polymer'].apply(process_polymer_list)

        # Clean up Manufacturing Methods
        if 'ASD Manufacturing Method' in df.columns:
            df['ASD Manufacturing Method'] = df['ASD Manufacturing Method'].fillna('Unknown').astype(str)
            def clean_method(m_str):
                m_lower = m_str.lower()
                if 'spray dry' in m_lower or 'spray drying' in m_lower: return 'Spray Drying'
                if 'melt' in m_lower or 'hme' in m_lower: return 'Hot Melt Technologies (HME)'
                if 'precipitation' in m_lower: return 'Co-precipitation'
                return m_str.strip().capitalize()
            df['ASD Manufacturing Method'] = df['ASD Manufacturing Method'].apply(clean_method)
                
        if 'Approval Year' in df.columns:
            # Handle possible float/string NaNs
            df['Approval Year'] = pd.to_numeric(df['Approval Year'], errors='coerce')
        # Classify Excipients
        def classify_excipients(exc_str):
            if pd.isna(exc_str) or not exc_str: return {}
            parts = [p.strip().lower() for p in str(exc_str).replace(';', ',').split(',')]
            
            categories = {
                'Filler': ['cellulose', 'lactose', 'mannitol', 'calcium hydrogen phosphate'],
                'Disintegrant': ['croscarmellose', 'crospovidone', 'sodium starch glycolate'],
                'Lubricant': ['magnesium stearate', 'sodium stearyl fumarate'],
                'Glidant': ['silica', 'talc'],
                'Coating/Polymer': ['hypromellose', 'copovidone', 'povidone', 'macrogol', 'polyvinyl alcohol', 'shellac', 'carnauba', 'methacrylic'],
                'Colorant': ['titanium dioxide', 'iron oxide', 'indigo carmine', 'brilliant blue'],
                'Surfactant': ['laurilsulfate', 'poloxamer', 'sorbitan', 'polysorbate'],
                'Plasticizer': ['triacetin', 'propylene glycol', 'glycerol']
            }
            
            classified = {k: [] for k in categories.keys()}
            classified['Other'] = []
            
            for p in parts:
                if not p: continue
                matched = False
                for cat, keywords in categories.items():
                    if any(kw in p for kw in keywords):
                        classified[cat].append(p.title())
                        matched = True
                        break
                if not matched:
                    classified['Other'].append(p.title())
                    
            return classified
            
        df['Excipient Categories'] = df['Excipients'].apply(classify_excipients)
        
        # Unpack some common ones into their own helper columns
        df['Fillers'] = df['Excipient Categories'].apply(lambda d: ', '.join(d.get('Filler', [])) if isinstance(d, dict) else '')
        df['Disintegrants'] = df['Excipient Categories'].apply(lambda d: ', '.join(d.get('Disintegrant', [])) if isinstance(d, dict) else '')
        df['Lubricants'] = df['Excipient Categories'].apply(lambda d: ', '.join(d.get('Lubricant', [])) if isinstance(d, dict) else '')

        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No data found or failed to load. Please ensure the Excel file exists.")
    st.stop()

# Key Metrics
st.markdown("### Top-Level Metrics")
col1, col2 = st.columns(2)

total_drugs = len(df)
years = df['Approval Year'].dropna().astype(int)
latest_year = years.max() if not years.empty else "N/A"

with col1:
    st.metric(label="Total Confirmed ASDs", value=total_drugs)
with col2:
    st.metric(label="Latest Approval", value=latest_year)

st.divider()

# Charts row 1
st.markdown("### 📈 Approval Trends & Therapeutic Areas")
c1, c2 = st.columns(2)

with c1:
    if 'Approval Year' in df.columns and not df['Approval Year'].dropna().empty:
        year_counts = df['Approval Year'].dropna().astype(int).value_counts().sort_index().reset_index()
        year_counts.columns = ['Year', 'Count']
        fig1 = px.bar(year_counts, x='Year', y='Count', title="Approvals per Year", text='Count', color_discrete_sequence=['#1f77b4'])
        fig1.update_traces(textposition='outside')
        fig1.update_layout(xaxis=dict(tickmode='linear', tick0=2010, dtick=1))
        st.plotly_chart(fig1, width='stretch')

with c2:
    if 'Therapeutic Category' in df.columns:
        cat_counts = df['Therapeutic Category'].value_counts().reset_index().head(8)
        cat_counts.columns = ['Category', 'Count']
        fig2 = px.pie(cat_counts, values='Count', names='Category', title="Top Therapeutic Categories (Top 8)", hole=0.4)
        st.plotly_chart(fig2, width='stretch')

# Charts row 2
st.markdown("### 🔬 Formulation Deep-Dive")
c3, c4 = st.columns(2)

with c3:
    if 'ASD Polymer' in df.columns:
        # Simplify polymer names for visualization (often they are comma separated)
        poly_series = df['ASD Polymer'].dropna().str.split(',', expand=True).stack().str.strip()
        poly_counts = poly_series.value_counts().reset_index().head(10)
        poly_counts.columns = ['Polymer', 'Count']
        poly_counts = poly_counts[poly_counts['Polymer'].str.lower() != 'unknown']
        poly_counts = poly_counts[poly_counts['Polymer'] != '']
        
        fig3 = px.bar(poly_counts, x='Count', y='Polymer', orientation='h', title="Most Used Polymers in Formulations", color='Count', color_continuous_scale='Viridis')
        fig3.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig3, width='stretch')

with c4:
    if 'ASD Manufacturing Method' in df.columns:
        method_counts = df['ASD Manufacturing Method'].fillna('Unknown').value_counts().reset_index()
        method_counts.columns = ['Method', 'Count']
        method_counts = method_counts[method_counts['Method'].str.lower() != 'unknown']
        
        fig4 = px.pie(method_counts, values='Count', names='Method', title="Manufacturing Methods")
        st.plotly_chart(fig4, width='stretch')

st.divider()

# Data Grid
st.markdown("### 📊 Raw Data Explorer")
# Allow filtering by company or polymer
def filter_dataframe(df):
    st.write("Search and Filter Options:")
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        text_search = st.text_input("Search by Drug Name or Active Substance")
    with f_col2:
        if 'ASD Polymer' in df.columns:
            poly_options = ['All'] + sorted(list(set(df['ASD Polymer'].dropna().unique())))
            poly_filter = st.selectbox("Filter by Polymer", poly_options)
        else:
            poly_filter = 'All'

    # Apply filters
    filtered_df = df.copy()
    if text_search:
        mask = filtered_df['Drug Name'].str.contains(text_search, case=False, na=False) | \
               filtered_df['Active Substance'].str.contains(text_search, case=False, na=False)
        filtered_df = filtered_df[mask]
    
    if poly_filter != 'All':
        filtered_df = filtered_df[filtered_df['ASD Polymer'].str.contains(poly_filter, regex=False, na=False)]

    # Reset index starting from 1 for clean presentation
    display_df = filtered_df.drop(columns=['Excipient Categories'], errors='ignore').copy()
    display_df.index = range(1, len(display_df) + 1)
    
    # Present the table
    st.dataframe(display_df, width='stretch')
    
    # Excipient Deep Dive
    st.markdown("### 💊 Excipient Classification Deep Dive")
    st.caption("Select a drug to view how its excipients are classified by their functional roles.")
    
    drug_to_view = st.selectbox("Select Drug", filtered_df['Drug Name'].sort_values().unique())
    if drug_to_view:
        drug_data = df[df['Drug Name'] == drug_to_view].iloc[0]
        st.write(f"**{drug_to_view}** ({drug_data.get('Company', 'Unknown')}) - {drug_data.get('Dosage Form', '')}")
        
        cats = drug_data.get('Excipient Categories', {})
        if not cats:
            st.info("No excipient data available.")
        else:
            cols = st.columns(4)
            idx = 0
            for cat, items in cats.items():
                if items:
                    with cols[idx % 4]:
                        st.markdown(f"**{cat}**")
                        for item in items:
                            st.markdown(f"- {item}")
                    idx += 1

filter_dataframe(df)

st.divider()

st.markdown("### 💡 Fun Facts from the Data")

# Dynamically calculate disintegrant counts for the fun facts
total_asd = len(df)
croscarmellose_count = df['Excipients'].str.contains('croscarmellose', case=False, na=False).sum()
crospovidone_count = df['Excipients'].str.contains('crospovidone', case=False, na=False).sum()

st.info(f"""
1. **Magnesium Stearate rules them all!** It appears as a lubricant in a massive majority of ASD oral drugs, making it the undeniable king of downstream tableting.
2. **The rise of HPMCAS & Copovidone.** Hypromellose acetate succinate (HPMCAS) and Copovidone absolutely dominate the ASD polymer space, appearing repeatedly to stabilize these difficult APIs.
3. **The Superdisintegrant Gap.** **Croscarmellose Sodium** (used in **{croscarmellose_count}** ASD drugs) absolutely crushes **Crospovidone** (only **{crospovidone_count}** drugs). This is likely because Croscarmellose Sodium's extreme swelling capacity and fibrous structure are uniquely suited for forcefully tearing apart dense, glassy polymeric beads created by spray drying or HME!
4. **Salt in the wound... literally?** A surprising few ASD formulations (Zepatier, Aquipta, Tukysa) specifically include **Sodium Chloride (NaCl)** in their tableting/matrix to modulate dissolution, solubility, or osmotic gradients!
5. **Oncology is the biggest benefactor.** Over half of these tricky, insoluble ASD APIs are intended for Targeted Cancer Therapies (mostly Kinase Inhibitors).
""")

st.markdown("---")
st.markdown("### 🙏 Acknowledgements")
st.info("Thank you my wife Xiuli Li for the support. Thank my friend Tianyi Li, Yongjian Wang, Fan Meng, and Zoe Wen for brainstorming. Thank my manager Fady Ibrahim for the encouragement. Thank my PhD advisor Kevin J. Edgar, my postdoc advisor Lynne Taylor, and my mentor Tze Ning Hiew for me to start work on amorphous solid dispersion.")
st.markdown("<div style='text-align: center'>Built with Streamlit & Gemini 3.1 Pro </div>", unsafe_allow_html=True)
