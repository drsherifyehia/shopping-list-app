import streamlit as st
import pandas as pd
import datetime
import math

st.set_page_config(page_title="Clinic Inventory", layout="wide")

# Initialize master data in session state
if 'master_df' not in st.session_state:
    st.session_state['master_df'] = None

st.title("🛒 Smart Shopping List")

tabs = st.tabs(["1. Upload", "2. Consolidate", "3. Forecast", "4. Interactive Shopping List"])

# --- TAB 1: UPLOAD & POSITION-BASED MAPPING ---
with tabs[0]:
    col1, col2 = st.columns(2)
    file_amu = col1.file_uploader("Upload AMU Sheet (A,B,D,G)", type=["xlsx"])
    file_s2 = col2.file_uploader("Upload Sheet 2 (B,D,F,G)", type=["xlsx"])

    if file_amu and file_s2:
        try:
            # Load AMU by position: A=Item, B=Type, D=Price, G=AMU
            df_amu = pd.read_excel(file_amu, usecols="A,B,D,G")
            df_amu.columns = ["Item", "Type", "Price", "AMU"]
            
            # Load Sheet 2 by position: B=Item, D=Type_S2, F=Branch, G=Master
            df_s2 = pd.read_excel(file_s2, usecols="B,D,F,G")
            df_s2.columns = ["Item", "Type_S2", "Branch", "Master"]
            
            # Clean for matching
            df_amu['MatchKey'] = df_amu['Item'].astype(str).str.strip().str.lower()
            df_s2['MatchKey'] = df_s2['Item'].astype(str).str.strip().str.lower()

            # Merge and calculate forecast
            merged = pd.merge(df_amu, df_s2.drop(columns=['Item']), on="MatchKey", how="inner")
            
            def calc_target(row):
                try:
                    m = float(row['Master']) if not pd.isna(row['Master']) else 0
                    a = float(row['AMU']) if not pd.isna(row['AMU']) else 0
                    months = math.ceil(m / a) if a > 0 else 0
                    return (datetime.date.today() + pd.DateOffset(months=months)).replace(day=1)
                except: return datetime.date.today().replace(day=1)

            # Ensure TargetDate is a proper datetime object
            merged['TargetDate'] = pd.to_datetime(merged.apply(calc_target, axis=1))
            st.session_state['master_df'] = merged
            st.success(f"Successfully linked {len(merged)} items!")
        except Exception as e:
            st.error(f"Error processing files: {e}")

# --- TAB 4: THE INTERACTIVE LISTS ---
with tabs[3]:
    if st.session_state['master_df'] is not None:
        df = st.session_state['master_df']
        
        # Select base month
        start_date = st.date_input("Select Starting Month", datetime.date.today().replace(day=1))
        month_list = [pd.Timestamp(start_date) + pd.DateOffset(months=i) for i in range(3)]

        # Highlight logic: Red if Branch is 0, Yellow if Branch > 0
        def highlight_logic(row):
            b_val = float(row['Branch']) if not pd.isna(row['Branch']) else 0
            color = '#ff4b4b' if b_val <= 0 else '#fffd80' # Red vs Yellow
            text_color = 'white' if b_val <= 0 else 'black'
            return [f'background-color: {color}; color: {text_color}'] * len(row)

        for i, current_month in enumerate(month_list):
            m_str = current_month.strftime("%B %Y")
            
            # Filter for this specific month
            mask = (df['TargetDate'].dt.month == current_month.month) & \
                   (df['TargetDate'].dt.year == current_month.year)
            
            month_df = df[mask].copy()
            st.markdown(f"### 📅 {m_str}")
            
            if not month_df.empty:
                # Show Total Price
                total = (month_df['Price'] * month_df['AMU']).sum()
                st.metric(f"Total for {m_str}", f"${total:,.2f}")

                # Display list with color coding
                st.dataframe(
                    month_df[['Item', 'Type', 'Price', 'AMU', 'Branch', 'Master']].style.apply(highlight_logic, axis=1),
                    use_container_width=True
                )
                
                # Postpone logic
                col_sel, col_btn = st.columns([3, 1])
                it_to_move = col_sel.selectbox(f"Select Item to Move:", month_df['Item'], key=f"sel_{i}")
                
                if col_btn.button("Postpone ➡️", key=f"btn_{i}"):
                    # Update master_df in session state
                    idx = df[df['Item'] == it_to_move].index
                    df.loc[idx, 'TargetDate'] = current_month + pd.DateOffset(months=1)
                    st.session_state['master_df'] = df
                    st.rerun()
            else:
                st.write("No items scheduled for this month.")
            st.divider()
    else:
        st.info("Upload your Excel files in Tab 1 to see your shopping lists.")
