import streamlit as st
import pandas as pd
import datetime
import math

st.set_page_config(page_title="Shopping List App", layout="wide")

st.title("🛒 Shopping List Inventory Manager")

# Define our 4 tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "1. Upload", 
    "2. Consolidate", 
    "3. Master Depletion Date", 
    "4. Monthly Shopping List"
])

# --- TAB 1: UPLOAD ---
with tab1:
    st.header("Upload Excel Sheets")
    col1, col2 = st.columns(2)
    
    with col1:
        file1 = st.file_uploader("Upload Sheet 1 (items, type, price, amu)", type=["xlsx", "xls"])
    with col2:
        file2 = st.file_uploader("Upload Sheet 2 (Name, Type, Branch Amount, Master Amount)", type=["xlsx", "xls"])

    if file1 and file2:
        try:
            # Read Sheet 1 normally
            df1 = pd.read_excel(file1)
            
            # Read Sheet 2 extracting only specific columns. 
            # In Pandas (0-indexed): B=1, D=3, F=5, G=6 
            df2 = pd.read_excel(
                file2, 
                usecols="B,D,F,G", 
                names=["Name", "Type_Sheet2", "Branch Amount", "Master Amount"]
            )
            
            # Save dataframes to session state to share across tabs
            st.session_state['df1'] = df1
            st.session_state['df2'] = df2
            st.success("Files successfully uploaded and read! Proceed to the next tab.")
        except Exception as e:
            st.error(f"Error reading files: {e}")

# --- TAB 2: CONSOLIDATE ---
with tab2:
    st.header("Consolidated Inventory List")
    if 'df1' in st.session_state and 'df2' in st.session_state:
        df1 = st.session_state['df1']
        df2 = st.session_state['df2']
        
        # Consolidate according to Item Name
        merged_df = pd.merge(df1, df2, left_on="items", right_on="Name", how="outer")
        
        st.session_state['merged_df'] = merged_df
        st.dataframe(merged_df, use_container_width=True)
    else:
        st.info("Please upload your sheets in the 'Upload' tab first.")

# --- TAB 3: CALCULATE ---
with tab3:
    st.header("Master Stock Depletion Calculation")
    if 'merged_df' in st.session_state:
        calc_df = st.session_state['merged_df'].copy()
        
        def calculate_finish_month(row):
            try:
                master_amt = float(row.get('Master Amount', 0))
                amu = float(row.get('amu', 0))
                
                # Handle edge cases where data is missing or AMU is 0
                if pd.isna(master_amt) or pd.isna(amu) or amu <= 0:
                    return "Unknown"
                    
                # Calculate how many months until master stock hits 0
                months_left = math.ceil(master_amt / amu)
                
                # Add the months left to today's date
                finish_date = datetime.date.today() + pd.DateOffset(months=int(months_left))
                return finish_date.strftime("%B %Y")
            except:
                return "Error"

        # Apply calculation row-by-row
        calc_df['Finish Month'] = calc_df.apply(calculate_finish_month, axis=1)
        st.session_state['calc_df'] = calc_df
        st.dataframe(calc_df, use_container_width=True)
    else:
        st.info("Consolidated data is not available yet.")

# --- TAB 4: FILTER & DISPLAY ---
with tab4:
    st.header("Monthly Shopping List")
    if 'calc_df' in st.session_state:
        df = st.session_state['calc_df']
        
        # 1. Dropdown List for Months
        valid_months = [m for m in df['Finish Month'].dropna().unique() if m not in ["Unknown", "Error"]]
        # Sort months chronologically so the dropdown looks clean
        valid_months.sort(key=lambda d: datetime.datetime.strptime(d, "%B %Y"))
        
        selected_month = st.selectbox("Select the month the master stock finishes:", options=valid_months)
        
        # 2. Checkbox Filters for Material Type
        st.write("**Filter by Material Type:**")
        # Default to Sheet 1's type column, fallback to Sheet 2's if missing
        type_col = 'type' if 'type' in df.columns else 'Type_Sheet2'
        unique_types = df[type_col].dropna().unique()
        
        selected_types = []
        # Create a dynamic grid of checkboxes
        cols = st.columns(min(len(unique_types), 4) if len(unique_types) > 0 else 1)
        for i, material_type in enumerate(unique_types):
            with cols[i % len(cols)]:
                # Checkboxes default to True
                if st.checkbox(str(material_type), value=True):
                    selected_types.append(material_type)
        
        # 3. Apply Filters and Formatting
        if selected_month and selected_types:
            filtered_df = df[(df['Finish Month'] == selected_month) & (df[type_col].isin(selected_types))]
            
            def highlight_stock(row):
                try:
                    branch_amt = float(row.get('Branch Amount', 0))
                except:
                    branch_amt = 0
                    
                # If an item appears here, its Master stock is 0 for this month.
                # If Branch is also 0, red. If Branch has stock, yellow.
                if pd.isna(branch_amt) or branch_amt <= 0:
                    return ['background-color: #ffcccc; color: #900000'] * len(row) # Red
                else:
                    return ['background-color: #ffffcc; color: #808000'] * len(row) # Yellow
            
            if not filtered_df.empty:
                st.dataframe(filtered_df.style.apply(highlight_stock, axis=1), use_container_width=True)
            else:
                st.warning("No materials match the selected month and type filters.")
    else:
        st.info("Data processing incomplete. Please upload and consolidate first.")

