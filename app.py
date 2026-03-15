import streamlit as st
import pandas as pd
import datetime
import math
from io import BytesIO

st.set_page_config(page_title="Clinic Inventory", layout="wide")

# Persistent State
if 'master_df' not in st.session_state:
    st.session_state['master_df'] = None
if 'unmatched_amu' not in st.session_state:
    st.session_state['unmatched_amu'] = None
if 'unmatched_sheet2' not in st.session_state:
    st.session_state['unmatched_sheet2'] = None

st.title("🛒 Smart Shopping List")

# --- CALLBACK FOR POSTPONE ---
def postpone_item(item_name, current_target_date):
    df = st.session_state['master_df']
    idx = df[df['Item'] == item_name].index
    new_date = current_target_date + pd.DateOffset(months=1)
    df.loc[idx, 'TargetDate'] = new_date
    st.session_state['master_df'] = df

tabs = st.tabs(["1. Upload", "2. Consolidate", "3. Unmatched Items", "4. Interactive List"])

# --- TAB 1: UPLOAD ---
with tabs[0]:
    col1, col2 = st.columns(2)
    file_amu = col1.file_uploader("Upload AMU Sheet", type=["xlsx"])
    file_s2 = col2.file_uploader("Upload Sheet 2", type=["xlsx"])

    if file_amu and file_s2:
        try:
            df_amu = pd.read_excel(file_amu, usecols="A,B,D,G")
            df_amu.columns = ["Item", "Type", "Price", "AMU"]
            
            df_s2 = pd.read_excel(file_s2, usecols="B,D,F,G")
            df_s2.columns = ["Item", "Type_S2", "Branch", "Master"]
            
            # Cleaning Keys
            df_amu['MatchKey'] = df_amu['Item'].astype(str).str.strip().str.lower()
            df_s2['MatchKey'] = df_s2['Item'].astype(str).str.strip().str.lower()

            # 1. Successful Consolidate (Inner)
            merged = pd.merge(df_amu, df_s2.drop(columns=['Item']), on="MatchKey", how="inner")
            
            # 2. Unmatched in AMU (Items we have usage for but no stock data)
            st.session_state['unmatched_amu'] = df_amu[~df_amu['MatchKey'].isin(df_s2['MatchKey'])].drop(columns=['MatchKey'])
            
            # 3. Unmatched in Sheet 2 (Items in stock but no usage data)
            st.session_state['unmatched_sheet2'] = df_s2[~df_s2['MatchKey'].isin(df_amu['MatchKey'])].drop(columns=['MatchKey'])

            # Calculate Dates
            def calc_month(row):
                try:
                    m = float(row['Master']) if not pd.isna(row['Master']) else 0
                    a = float(row['AMU']) if not pd.isna(row['AMU']) else 0
                    months = math.ceil(m / a) if a > 0 else 0
                    return (datetime.date.today() + pd.DateOffset(months=months)).replace(day=1)
                except: return datetime.date.today().replace(day=1)

            merged['TargetDate'] = pd.to_datetime(merged.apply(calc_month, axis=1))
            st.session_state['master_df'] = merged
            st.success("Analysis Complete!")
        except Exception as e:
            st.error(f"Error: {e}")

# --- TAB 3: UNMATCHED ---
with tabs[2]:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("⚠️ Missing from Sheet 2")
        st.caption("Items in AMU list that don't exist in Inventory.")
        if st.session_state['unmatched_amu'] is not None:
            st.dataframe(st.session_state['unmatched_amu'], use_container_width=True)

    with col_right:
        st.subheader("🔍 Missing from AMU")
        st.caption("Inventory items that have no usage (AMU) data.")
        if st.session_state['unmatched_sheet2'] is not None:
            st.dataframe(st.session_state['unmatched_sheet2'], use_container_width=True)

# --- TAB 4: INTERACTIVE LIST ---
with tabs[3]:
    if st.session_state['master_df'] is not None:
        df = st.session_state['master_df']
        start_month = st.date_input("Select Start Month", datetime.date.today().replace(day=1))
        month_list = [pd.Timestamp(start_month) + pd.DateOffset(months=i) for i in range(3)]

        def style_logic(row):
            # Red: Branch is 0. Yellow: Branch > 0.
            branch = float(row['Branch']) if not pd.isna(row['Branch']) else 0
            if branch <= 0:
                return ['background-color: #ff4b4b; color: white'] * len(row)
            return ['background-color: #fffd80; color: black'] * len(row)

        for i, current_month in enumerate(month_list):
            m_str = current_month.strftime("%B %Y")
            mask = (df['TargetDate'].dt.month == current_month.month) & \
                   (df['TargetDate'].dt.year == current_month.year)
            
            month_df = df[mask].copy()
            st.markdown(f"### 📅 {m_str}")
            
            if not month_df.empty:
                total = (month_df['Price'] * month_df['AMU']).sum()
                st.metric(f"Total for {m_str}", f"${total:,.2f}")
                
                # Table with highlight
                display_cols = ['Item', 'Type', 'Price', 'AMU', 'Branch', 'Master']
                st.dataframe(month_df[display_cols].style.apply(style_logic, axis=1), use_container_width=True)

                # Postpone Control
                with st.expander(f"Move items from {m_str}"):
                    it_to_move = st.selectbox("Choose Item:", month_df['Item'], key=f"sel_{i}")
                    st.button("Postpone to Next Month ➡️", key=f"btn_{i}", 
                              on_click=postpone_item, args=(it_to_move, current_month))
            else:
                st.write("No items forecast for this month.")
            st.divider()
    else:
        st.info("Upload files in Tab 1.")
