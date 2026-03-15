import streamlit as st
import pandas as pd
import datetime
import math
from io import BytesIO

st.set_page_config(page_title="Clinic Inventory", layout="wide")

if 'master_df' not in st.session_state:
    st.session_state['master_df'] = None

st.title("🛒 Smart Shopping List")

tab1, tab2, tab3, tab4 = st.tabs(["1. Upload", "2. Consolidate", "3. Forecast", "4. Interactive Shopping List"])

# --- TAB 1: UPLOAD & MATCHING ---
with tab1:
    col1, col2 = st.columns(2)
    file_amu = col1.file_uploader("Upload AMU Sheet (A,B,D,G)", type=["xlsx"])
    file_s2 = col2.file_uploader("Upload Sheet 2 (B,D,F,G)", type=["xlsx"])

    if file_amu and file_s2:
        try:
            # Load AMU Sheet (A, B, D, G)
            df_amu = pd.read_excel(file_amu, usecols="A,B,D,G")
            df_amu.columns = ["Item", "Type", "Price", "AMU"]
            
            # Load Sheet 2 (B, D, F, G)
            df_s2 = pd.read_excel(file_s2, usecols="B,D,F,G")
            df_s2.columns = ["Item", "Type_S2", "Branch", "Master"]
            
            # CRITICAL: Clean names for matching
            df_amu['MatchKey'] = df_amu['Item'].astype(str).str.strip().str.lower()
            df_s2['MatchKey'] = df_s2['Item'].astype(str).str.strip().str.lower()

            # Merge
            merged = pd.merge(df_amu, df_s2.drop(columns=['Item']), on="MatchKey", how="inner")
            
            def calc_month(row):
                try:
                    m_val = float(row['Master']) if not pd.isna(row['Master']) else 0
                    a_val = float(row['AMU']) if not pd.isna(row['AMU']) else 0
                    months = math.ceil(m_val / a_val) if a_val > 0 else 0
                    # Return first day of target month
                    target = (datetime.date.today() + pd.DateOffset(months=months)).replace(day=1)
                    return target
                except: return datetime.date.today().replace(day=1)

            # Ensure proper datetime format for filtering
            merged['TargetDate'] = pd.to_datetime(merged.apply(calc_month, axis=1))
            st.session_state['master_df'] = merged
            st.success(f"🔗 Successfully matched {len(merged)} items!")
            
        except Exception as e:
            st.error(f"Error: {e}")

# --- TAB 2: CONSOLIDATE ---
with tab2:
    st.header("Consolidated List")
    if st.session_state['master_df'] is not None:
        st.dataframe(st.session_state['master_df'][['Item', 'Type', 'Price', 'AMU', 'Branch', 'Master']], use_container_width=True)

# --- TAB 3: FORECAST ---
with tab3:
    st.header("Depletion Forecast")
    if st.session_state['master_df'] is not None:
        forecast_df = st.session_state['master_df'][['Item', 'Master', 'AMU', 'TargetDate']].copy()
        forecast_df['TargetDate'] = forecast_df['TargetDate'].dt.strftime('%B %Y')
        st.dataframe(forecast_df, use_container_width=True)

# --- TAB 4: INTERACTIVE LIST ---
with tab4:
    if st.session_state['master_df'] is not None:
        df = st.session_state['master_df']

        # Filters
        start_month = st.date_input("Start Month", datetime.date.today().replace(day=1))
        start_ts = pd.Timestamp(start_month)
        month_list = [start_ts + pd.DateOffset(months=i) for i in range(3)]
        
        st.write("**Filter Material Type:**")
        all_types = sorted(df['Type'].unique().astype(str))
        cols = st.columns(3)
        selected_types = [t for i, t in enumerate(all_types) if cols[i % 3].checkbox(t, value=True, key=f"check_{t}")]

        def style_rows(row):
            try:
                branch_val = float(row.get('Branch', 0))
            except:
                branch_val = 0
            # Red if Branch is 0, Yellow if Branch > 0
            if branch_val <= 0:
                return ['background-color: #ff4b4b; color: white'] * len(row)
            return ['background-color: #fffd80; color: black'] * len(row)

        for i, current_month in enumerate(month_list):
            m_str = current_month.strftime("%B %Y")
            mask = (df['TargetDate'].dt.month == current_month.month) & \
                   (df['TargetDate'].dt.year == current_month.year) & \
                   (df['Type'].isin(selected_types))
            
            month_df = df[mask].copy()
            st.markdown(f"### 📅 {m_str}")
            
            if not month_df.empty:
                total = (month_df['Price'] * month_df['AMU']).sum()
                st.metric("Estimated Cost", f"${total:,.2f}")

                st.data_editor(
                    month_df[['Item', 'Type', 'Price', 'AMU', 'Branch', 'Master']].style.apply(style_rows, axis=1),
                    key=f"editor_{i}",
                    use_container_width=True,
                    num_rows="dynamic"
                )

                # Move/Postpone Logic
                c1, c2 = st.columns([3, 1])
                it = c1.selectbox("Select Item to Postpone:", month_df['Item'], key=f"sel_{i}")
                if c2.button("Postpone ➡️", key=f"btn_{i}"):
                    # Update date in the main session state
                    idx = df[df['Item'] == it].index
                    # Increment existing TargetDate by one month
                    df.loc[idx, 'TargetDate'] = df.loc[idx, 'TargetDate'] + pd.DateOffset(months=1)
                    st.session_state['master_df'] = df
                    st.rerun()
            else:
                st.write("No items for this month.")
            st.divider()
    else:
        st.info("Please upload files in Tab 1.")
