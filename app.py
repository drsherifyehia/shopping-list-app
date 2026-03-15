import streamlit as st
import pandas as pd
import datetime
import math

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
            df_amu = pd.read_excel(file_amu, usecols="A,B,D,G").rename(columns={"inventoryItem":"Item", "inventoryType":"Type", "price":"Price", "AMU":"AMU"})
            df_s2 = pd.read_excel(file_s2, usecols="B,D,F,G").rename(columns={"Name":"Item", "Type":"Type_S2", "branch amount":"Branch", "master amount":"Master"})
            
            merged = pd.merge(df_amu, df_s2, on="Item", how="inner")
            merged['Item'] = merged['Item'].astype(str).str.strip()
            
            def calc_month(row):
                try:
                    m_val = float(row['Master']) if not pd.isna(row['Master']) else 0
                    a_val = float(row['AMU']) if not pd.isna(row['AMU']) else 0
                    months = math.ceil(m_val / a_val) if a_val > 0 else 0
                    return (datetime.date.today() + pd.DateOffset(months=months)).replace(day=1)
                except: return datetime.date.today().replace(day=1)

            merged['TargetDate'] = merged.apply(calc_month, axis=1)
            # FIX: Force TargetDate to be a datetime type
            merged['TargetDate'] = pd.to_datetime(merged['TargetDate'])
            
            st.session_state['master_df'] = merged
            st.success("Data Loaded Successfully!")
        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    if st.session_state['master_df'] is not None:
        st.dataframe(st.session_state['master_df'], use_container_width=True)

with tab4:
    if st.session_state['master_df'] is not None:
        df = st.session_state['master_df']

        # 1. Selection & Filters
        start_month = st.date_input("Select Starting Month", datetime.date.today().replace(day=1))
        # Ensure start_month is a Timestamp for comparison
        start_ts = pd.Timestamp(start_month)
        month_list = [start_ts + pd.DateOffset(months=i) for i in range(3)]
        
        st.write("**Filter by Material Type:**")
        all_types = sorted(df['Type'].unique().astype(str))
        cols = st.columns(3)
        selected_types = []
        for i, t in enumerate(all_types):
            if cols[i % 3].checkbox(t, value=True, key=f"filter_{t}"):
                selected_types.append(t)

        # Highlight Function
        def style_rows(row):
            # Since these items are in the shopping list, Master is assumed near 0
            branch = float(row['Branch']) if not pd.isna(row['Branch']) else 0
            if branch <= 0:
                return ['background-color: #ff4b4b; color: white'] * len(row) # Red
            return ['background-color: #fffd80; color: black'] * len(row) # Yellow

        # 2. Loop through 3 months
        for i, current_month in enumerate(month_list):
            month_str = current_month.strftime("%B %Y")
            
            mask = (df['TargetDate'].dt.month == current_month.month) & \
                   (df['TargetDate'].dt.year == current_month.year) & \
                   (df['Type'].isin(selected_types))
            
            month_df = df[mask].copy()
            
            st.markdown(f"### 📅 {month_str}")
            total_price = (month_df['Price'] * month_df['AMU']).sum()
            st.metric(f"Total for {month_str}", f"${total_price:,.2f}")

            if not month_df.empty:
                # 3. Editable Table with Highlighting
                edited_df = st.data_editor(
                    month_df.style.apply(style_rows, axis=1),
                    key=f"editor_{i}",
                    num_rows="dynamic",
                    use_container_width=True
                )

                # 4. Postpone Logic
                col_move1, col_move2 = st.columns([3, 1])
                item_to_move = col_move1.selectbox(f"Move item from {month_str}:", month_df['Item'], key=f"sel_{i}")
                
                if col_move2.button(f"Postpone ➡️", key=f"btn_{i}"):
                    idx = df[df['Item'] == item_to_move].index
                    df.loc[idx, 'TargetDate'] = current_month + pd.DateOffset(months=1)
                    st.session_state['master_df'] = df
                    st.rerun()
            else:
                st.write("No items for this month.")
            st.markdown("---")
    else:
        st.info("Upload files in Tab 1 to begin.")
