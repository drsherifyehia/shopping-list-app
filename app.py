import streamlit as st
import pandas as pd
import datetime
import math

st.set_page_config(page_title="Clinic Inventory", layout="wide")

# --- DATA PERSISTENCE ---
# We store the main dataframe in session_state so edits stay saved
if 'master_df' not in st.session_state:
    st.session_state['master_df'] = None

st.title("🛒 Smart Shopping List")

tab1, tab2, tab3, tab4 = st.tabs(["1. Upload", "2. Consolidate", "3. Forecast", "4. Interactive Shopping List"])

# --- TAB 1 & 2: Same as before but saving to master_df ---
with tab1:
    col1, col2 = st.columns(2)
    file_amu = col1.file_uploader("Upload AMU Sheet (A,B,D,G)", type=["xlsx"])
    file_s2 = col2.file_uploader("Upload Sheet 2 (B,D,F,G)", type=["xlsx"])

    if file_amu and file_s2:
        df_amu = pd.read_excel(file_amu, usecols="A,B,D,G").rename(columns={"inventoryItem":"Item", "inventoryType":"Type", "price":"Price", "AMU":"AMU"})
        df_s2 = pd.read_excel(file_s2, usecols="B,D,F,G").rename(columns={"Name":"Item", "Type":"Type_S2", "branch amount":"Branch", "master amount":"Master"})
        
        # Merge and clean
        merged = pd.merge(df_amu, df_s2, on="Item", how="inner")
        merged['Item'] = merged['Item'].astype(str).str.strip()
        
        # Initial Forecast Calculation
        def calc_month(row):
            try:
                months = math.ceil(float(row['Master']) / float(row['AMU'])) if float(row['AMU']) > 0 else 0
                return (datetime.date.today() + pd.DateOffset(months=months)).replace(day=1)
            except: return datetime.date.today().replace(day=1)

        merged['TargetDate'] = merged.apply(calc_month, axis=1)
        st.session_state['master_df'] = merged
        st.success("Data Loaded!")

with tab2:
    if st.session_state['master_df'] is not None:
        st.dataframe(st.session_state['master_df'], use_container_width=True)

with tab3:
    st.info("Forecast is now live in Tab 4.")

# --- TAB 4: THE INTERACTIVE TRIPLE LIST ---
with tab4:
    if st.session_state['master_df'] is not None:
        df = st.session_state['master_df']

        # 1. Month Selection
        start_month = st.date_input("Select Starting Month", datetime.date.today().replace(day=1))
        month_list = [start_month + pd.DateOffset(months=i) for i in range(3)]
        
        # 2. Material Type Filter
        all_types = df['Type'].unique()
        selected_types = [t for t in all_types if st.checkbox(str(t), value=True, key=f"filter_{t}")]

        # We loop 3 times to create 3 vertical lists
        for i, current_month in enumerate(month_list):
            month_str = current_month.strftime("%B %Y")
            
            # Filter data for this specific list
            mask = (df['TargetDate'].dt.month == current_month.month) & \
                   (df['TargetDate'].dt.year == current_month.year) & \
                   (df['Type'].isin(selected_types))
            
            month_df = df[mask].copy()
            
            # UI Styling
            st.markdown(f"---")
            total_price = (month_df['Price'] * month_df['AMU']).sum()
            st.subheader(f"📅 {month_str}")
            st.metric("Total Estimated Cost", f"${total_price:,.2f}")

            # 3. EDITABLE TABLE (Add/Delete/Edit)
            # Users can tap cells to change Price, AMU, or Item names
            edited_df = st.data_editor(
                month_df,
                key=f"editor_{month_str}",
                num_rows="dynamic", # Allows adding/deleting rows
                use_container_width=True,
                column_config={
                    "TargetDate": st.column_config.DateColumn(disabled=True),
                    "Price": st.column_config.NumberColumn(format="$%.2f"),
                }
            )

            # 4. POSTPONE LOGIC
            if not month_df.empty:
                col_move1, col_move2 = st.columns([2, 1])
                item_to_move = col_move1.selectbox(f"Postpone an item from {month_str}:", month_df['Item'], key=f"select_{i}")
                
                if col_move2.button(f"Move to Next Month ➡️", key=f"btn_{i}"):
                    # Update the date in the main session state
                    idx = df[df['Item'] == item_to_move].index
                    df.loc[idx, 'TargetDate'] = current_month + pd.DateOffset(months=1)
                    st.session_state['master_df'] = df
                    st.rerun()

            # Save edits back to master_df
            if not edited_df.equals(month_df):
                df.update(edited_df)
                st.session_state['master_df'] = df

    else:
        st.warning("Please upload files in Tab 1 first.")
