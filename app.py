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
            # AMU Sheet: A=Item, B=Type, D=Price, G=AMU
            df_amu = pd.read_excel(file_amu, usecols="A,B,D,G")
            df_amu.columns = ["Item", "Type", "Price", "AMU"]
            
            # Sheet 2: B=Item, D=Type_S2, F=Branch, G=Master
            df_s2 = pd.read_excel(file_s2, usecols="B,D,F,G")
            df_s2.columns = ["Item", "Type_S2", "Branch", "Master"]
            
            # Match cleaning
            df_amu['MatchKey'] = df_amu['Item'].astype(str).str.strip().str.lower()
            df_s2['MatchKey'] = df_s2['Item'].astype(str).str.strip().str.lower()

            merged = pd.merge(df_amu, df_s2.drop(columns=['Item']), on="MatchKey", how="inner")
            
            def calc_month(row):
                try:
                    m = float(row['Master']) if not pd.isna(row['Master']) else 0
                    a = float(row['AMU']) if not pd.isna(row['AMU']) else 0
                    months = math.ceil(m / a) if a > 0 else 0
                    return (datetime.date.today() + pd.DateOffset(months=months)).replace(day=1)
                except: return datetime.date.today().replace(day=1)

            merged['TargetDate'] = pd.to_datetime(merged.apply(calc_month, axis=1))
            st.session_state['master_df'] = merged
            st.success(f"Linked {len(merged)} items successfully!")
        except Exception as e:
            st.error(f"Error: {e}")

# --- TAB 2: CONSOLIDATE ---
with tab2:
    if st.session_state['master_df'] is not None:
        st.dataframe(st.session_state['master_df'][['Item', 'Type', 'Price', 'AMU', 'Branch', 'Master']], use_container_width=True)

# --- TAB 3: FORECAST ---
with tab3:
    if st.session_state['master_df'] is not None:
        forecast = st.session_state['master_df'][['Item', 'Master', 'AMU', 'TargetDate']].copy()
        forecast['TargetDate'] = forecast['TargetDate'].dt.strftime('%B %Y')
        st.dataframe(forecast, use_container_width=True)

# --- TAB 4: INTERACTIVE LIST ---
with tab4:
    if st.session_state['master_df'] is not None:
        df = st.session_state['master_df']
        start_month = st.date_input("Start Month", datetime.date.today().replace(day=1))
        month_list = [pd.Timestamp(start_month) + pd.DateOffset(months=i) for i in range(3)]

        def style_rows(row):
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
                st.metric("Total Cost", f"${total:,.2f}")

                # Using data_editor for active editing/deleting
                st.data_editor(
                    month_df[['Item', 'Type', 'Price', 'AMU', 'Branch', 'Master']].style.apply(style_rows, axis=1),
                    key=f"edit_{i}",
                    use_container_width=True,
                    num_rows="dynamic"
                )
                
                # Simple Postpone Button
                col1, col2 = st.columns([3, 1])
                it_move = col1.selectbox("Postpone Item:", month_df['Item'], key=f"s_{i}")
                if col2.button("Move ➡️", key=f"b_{i}"):
                    idx = df[df['Item'] == it_move].index
                    df.loc[idx, 'TargetDate'] = current_month + pd.DateOffset(months=1)
                    st.session_state['master_df'] = df
                    st.rerun()
            else:
                st.write("No items scheduled.")
            st.divider()
