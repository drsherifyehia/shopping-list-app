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

# --- TAB 1: UPLOAD ---
with tab1:
    col1, col2 = st.columns(2)
    file_amu = col1.file_uploader("Upload AMU Sheet (A,B,D,G)", type=["xlsx"])
    file_s2 = col2.file_uploader("Upload Sheet 2 (B,D,F,G)", type=["xlsx"])

    if file_amu and file_s2:
        try:
            # Load by position to avoid KeyError
            df_amu = pd.read_excel(file_amu, usecols="A,B,D,G")
            df_amu.columns = ["Item", "Type", "Price", "AMU"]
            
            df_s2 = pd.read_excel(file_s2, usecols="B,D,F,G")
            df_s2.columns = ["Item", "Type_S2", "Branch", "Master"]
            
            # Clean item names for matching
            df_amu['Item'] = df_amu['Item'].astype(str).str.strip()
            df_s2['Item'] = df_s2['Item'].astype(str).str.strip()

            merged = pd.merge(df_amu, df_s2, on="Item", how="inner")
            
            def calc_month(row):
                try:
                    m_val = float(row['Master']) if not pd.isna(row['Master']) else 0
                    a_val = float(row['AMU']) if not pd.isna(row['AMU']) else 0
                    months = math.ceil(m_val / a_val) if a_val > 0 else 0
                    return (datetime.date.today() + pd.DateOffset(months=months)).replace(day=1)
                except: return datetime.date.today().replace(day=1)

            merged['TargetDate'] = pd.to_datetime(merged.apply(calc_month, axis=1))
            st.session_state['master_df'] = merged
            st.success("Data Loaded! Columns mapped by position.")
        except Exception as e:
            st.error(f"Error loading files: {e}")

with tab4:
    if st.session_state['master_df'] is not None:
        df = st.session_state['master_df']

        # 1. Selection & Filters
        start_month = st.date_input("Select Starting Month", datetime.date.today().replace(day=1))
        start_ts = pd.Timestamp(start_month)
        month_list = [start_ts + pd.DateOffset(months=i) for i in range(3)]
        
        st.write("**Filter by Material Type:**")
        all_types = sorted(df['Type'].unique().astype(str))
        selected_types = [t for t in all_types if st.checkbox(t, value=True, key=f"f_{t}")]

        # Highlight Function - Safe check for column existence
        def style_rows(row):
            b_val = float(row['Branch']) if 'Branch' in row and not pd.isna(row['Branch']) else 0
            if b_val <= 0:
                return ['background-color: #ff4b4b; color: white'] * len(row)
            return ['background-color: #fffd80; color: black'] * len(row)

        # 2. Loop through 3 months
        for i, current_month in enumerate(month_list):
            month_str = current_month.strftime("%B %Y")
            mask = (df['TargetDate'].dt.month == current_month.month) & \
                   (df['TargetDate'].dt.year == current_month.year) & \
                   (df['Type'].isin(selected_types))
            
            month_df = df[mask].copy()
            
            st.markdown(f"### 📅 {month_str}")
            total_price = (month_df['Price'] * month_df['AMU']).sum()
            st.metric(f"Total Price", f"${total_price:,.2f}")

            if not month_df.empty:
                # Editable Table
                edited_df = st.data_editor(
                    month_df.style.apply(style_rows, axis=1),
                    key=f"editor_{i}",
                    num_rows="dynamic",
                    use_container_width=True
                )

                # Postpone Logic
                col_m1, col_m2 = st.columns([3, 1])
                item_to_move = col_m1.selectbox(f"Select Item:", month_df['Item'], key=f"s_{i}")
                if col_m2.button(f"Postpone ➡️", key=f"b_{i}"):
                    idx = df[df['Item'] == item_to_move].index
                    df.loc[idx, 'TargetDate'] = current_month + pd.DateOffset(months=1)
                    st.session_state['master_df'] = df
                    st.rerun()
            else:
                st.write("List is empty for this month.")
            st.markdown("---")
            
        # Download Button
        if st.button("Generate Excel Report"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Master_Shopping_List')
            st.download_button(
                label="📥 Download Full List",
                data=output.getvalue(),
                file_name=f"shopping_list_{datetime.date.today()}.xlsx",
                mime="application/vnd.ms-excel"
            )
    else:
        st.info("Please upload files in Tab 1.")
