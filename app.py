import streamlit as st
import pandas as pd
import datetime
import math

st.set_page_config(page_title="Inventory Planner", layout="wide")

st.title("📦 Clinic Inventory & Shopping List")

# Define tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "1. Upload Sheets", 
    "2. Consolidate", 
    "3. Depletion Forecast", 
    "4. Monthly Shopping List"
])

# --- TAB 1: UPLOAD ---
with tab1:
    st.header("Upload Excel Files")
    col1, col2 = st.columns(2)
    
    with col1:
        file_amu = st.file_uploader("Upload AMU Sheet (Cols A, B, D, G)", type=["xlsx", "xls"])
    with col2:
        file_sheet2 = st.file_uploader("Upload Sheet 2 (Cols B, D, F, G)", type=["xlsx", "xls"])

    if file_amu and file_sheet2:
        try:
            # AMU Sheet: A=inventoryItem, B=inventoryType, D=price, G=AMU
            df_amu = pd.read_excel(file_amu, usecols="A,B,D,G")
            df_amu.columns = ["inventoryItem", "inventoryType", "price", "AMU"]
            
            # Sheet 2: B=Name, D=Type, F=branch amount, G=master amount
            df_s2 = pd.read_excel(file_sheet2, usecols="B,D,F,G")
            df_s2.columns = ["Name", "Type", "branch amount", "master amount"]
            
            # Clean strings for matching
            for df, col in [(df_amu, 'inventoryItem'), (df_s2, 'Name')]:
                df[col] = df[col].astype(str).str.strip()

            st.session_state['df_amu'] = df_amu
            st.session_state['df_s2'] = df_s2
            st.success("Sheets mapped successfully! Proceed to Tab 2.")
        except Exception as e:
            st.error(f"Mapping Error: {e}. Please ensure columns match the specified letters.")

# --- TAB 2: CONSOLIDATE ---
with tab2:
    st.header("Consolidated Data")
    if 'df_amu' in st.session_state and 'df_s2' in st.session_state:
        # Merge on Item Name
        merged_df = pd.merge(
            st.session_state['df_amu'], 
            st.session_state['df_s2'], 
            left_on="inventoryItem", 
            right_on="Name", 
            how="inner"
        )
        st.session_state['merged_df'] = merged_df
        st.dataframe(merged_df, use_container_width=True)
    else:
        st.info("Waiting for file uploads...")

# --- TAB 3: DEPLETION DATE ---
with tab3:
    st.header("Master Stock Depletion Forecast")
    if 'merged_df' in st.session_state:
        calc_df = st.session_state['merged_df'].copy()
        
        def get_depletion_month(row):
            try:
                master = float(row['master amount'])
                amu = float(row['AMU'])
                if amu <= 0: return "N/A (No Usage)"
                
                months_until_zero = math.ceil(master / amu)
                target_date = datetime.date.today() + pd.DateOffset(months=months_until_zero)
                return target_date.strftime("%B %Y")
            except:
                return "Data Error"

        calc_df['Finish Month'] = calc_df.apply(get_depletion_month, axis=1)
        st.session_state['calc_df'] = calc_df
        st.dataframe(calc_df[['inventoryItem', 'master amount', 'AMU', 'Finish Month']], use_container_width=True)
    else:
        st.info("Consolidate data in Tab 2 first.")

# --- TAB 4: SHOPPING LIST & FILTERS ---
with tab4:
    st.header("Shopping List Generator")
    if 'calc_df' in st.session_state:
        df = st.session_state['calc_df']
        
        # Filters
        all_months = sorted([m for m in df['Finish Month'].unique() if " " in m], 
                            key=lambda x: datetime.datetime.strptime(x, "%B %Y"))
        
        col_a, col_b = st.columns([1, 2])
        with col_a:
            selected_month = st.selectbox("Select Target Month:", all_months)
        with col_b:
            st.write("**Filter by Material Type:**")
            types = df['inventoryType'].unique()
            selected_types = [t for t in types if st.checkbox(str(t), value=True)]

        # Apply Filters
        final_list = df[(df['Finish Month'] == selected_month) & (df['inventoryType'].isin(selected_types))]

        def apply_highlights(row):
            # Red: Both Master and Branch are 0
            # Yellow: Master is 0 (all items in this list have Master reaching 0)
            master = float(row['master amount'])
            branch = float(row['branch amount'])
            
            if branch <= 0:
                return ['background-color: #ff4b4b; color: white'] * len(row) # Red
            else:
                return ['background-color: #fffd80; color: black'] * len(row) # Yellow

        if not final_list.empty:
            st.subheader(f"Items reaching zero stock in {selected_month}")
            st.dataframe(final_list.style.apply(apply_highlights, axis=1), use_container_width=True)
        else:
            st.write("No items found for this selection.")
    else:
        st.info("Complete Tabs 1-3 to see the shopping list.")
