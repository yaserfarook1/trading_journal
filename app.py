import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import calendar
from io import BytesIO

# Initialize session state for trade history if it doesn't exist
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = pd.DataFrame(columns=['Date', 'Type', 'Points', 'P/L'])

# Function to add a trade
def add_trade(date, trade_type):
    if trade_type == 'TP':
        points = 2
        p_l = 'Profit'
    else:
        points = -1
        p_l = 'Loss'
    
    new_trade = pd.DataFrame({
        'Date': [date],
        'Type': [trade_type],
        'Points': [points],
        'P/L': [p_l]
    })
    
    st.session_state.trade_history = pd.concat([st.session_state.trade_history, new_trade], ignore_index=True)
    st.session_state.trade_history['Date'] = pd.to_datetime(st.session_state.trade_history['Date'])
    st.session_state.trade_history = st.session_state.trade_history.sort_values('Date')

# Function to generate analysis
def generate_analysis(df):
    if df.empty:
        return None
    
    analysis = {}
    
    # Monthly analysis
    monthly = df.copy()
    monthly['Month'] = monthly['Date'].dt.month
    monthly['Month_Name'] = monthly['Date'].dt.month_name()
    monthly['Year'] = monthly['Date'].dt.year
    monthly_agg = monthly.groupby(['Year', 'Month', 'Month_Name']).agg(
        Total_Trades=('Points', 'count'),
        TP=('Type', lambda x: (x == 'TP').sum()),
        SL=('Type', lambda x: (x == 'SL').sum()),
        Total_Points=('Points', 'sum'),
        Win_Rate=('P/L', lambda x: (x == 'Profit').mean())
    ).reset_index()
    monthly_agg['Win_Rate'] = monthly_agg['Win_Rate'].apply(lambda x: f"{x:.2%}")
    
    # Weekly analysis
    weekly = df.copy()
    weekly['Week'] = weekly['Date'].dt.isocalendar().week
    weekly['Year'] = weekly['Date'].dt.isocalendar().year
    weekly_agg = weekly.groupby(['Year', 'Week']).agg(
        Total_Trades=('Points', 'count'),
        TP=('Type', lambda x: (x == 'TP').sum()),
        SL=('Type', lambda x: (x == 'SL').sum()),
        Total_Points=('Points', 'sum'),
        Win_Rate=('P/L', lambda x: (x == 'Profit').mean())
    ).reset_index()
    weekly_agg['Win_Rate'] = weekly_agg['Win_Rate'].apply(lambda x: f"{x:.2%}")
    
    # Yearly analysis
    yearly = df.copy()
    yearly['Year'] = yearly['Date'].dt.year
    yearly_agg = yearly.groupby('Year').agg(
        Total_Trades=('Points', 'count'),
        TP=('Type', lambda x: (x == 'TP').sum()),
        SL=('Type', lambda x: (x == 'SL').sum()),
        Total_Points=('Points', 'sum'),
        Win_Rate=('P/L', lambda x: (x == 'Profit').mean())
    ).reset_index()
    yearly_agg['Win_Rate'] = yearly_agg['Win_Rate'].apply(lambda x: f"{x:.2%}")
    
    analysis['monthly'] = monthly_agg
    analysis['weekly'] = weekly_agg
    analysis['yearly'] = yearly_agg
    
    return analysis

# Function to create downloadable Excel with monthly sheets
def create_excel_download(df):
    if df.empty:
        return None
    
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    # Create a sheet for each month-year combination
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    
    for (year, month), group in df.groupby(['Year', 'Month']):
        month_name = calendar.month_name[month]
        sheet_name = f"{month_name}_{year}"
        group.drop(['Year', 'Month'], axis=1).to_excel(writer, sheet_name=sheet_name[:31], index=False)
    
    # Create a summary sheet
    summary = df.groupby(['Year', 'Month']).agg(
        Total_Trades=('Points', 'count'),
        TP=('Type', lambda x: (x == 'TP').sum()),
        SL=('Type', lambda x: (x == 'SL').sum()),
        Total_Points=('Points', 'sum')
    ).reset_index()
    summary['Month'] = summary['Month'].apply(lambda x: calendar.month_name[x])
    summary.to_excel(writer, sheet_name='Summary', index=False)
    
    writer.close()
    output.seek(0)
    
    return output

# Streamlit UI
st.title('Trade Journal')

# Date selection
selected_date = st.date_input('Select Trading Date', datetime.today())

# Trade type buttons
col1, col2 = st.columns(2)
with col1:
    if st.button('TP (+2 points)'):
        add_trade(selected_date, 'TP')
        st.success(f"Added TP trade for {selected_date}")
with col2:
    if st.button('SL (-1 point)'):
        add_trade(selected_date, 'SL')
        st.success(f"Added SL trade for {selected_date}")

# Display trade history
st.subheader('Trade History')
if not st.session_state.trade_history.empty:
    st.dataframe(st.session_state.trade_history)
else:
    st.info("No trades recorded yet.")

# Analysis dashboard
if not st.session_state.trade_history.empty:
    st.subheader('Performance Analysis')
    analysis = generate_analysis(st.session_state.trade_history)
    
    tab1, tab2, tab3 = st.tabs(["Monthly", "Weekly", "Yearly"])
    
    with tab1:
        st.write("Monthly Performance")
        st.dataframe(analysis['monthly'])
        
    with tab2:
        st.write("Weekly Performance")
        st.dataframe(analysis['weekly'])
        
    with tab3:
        st.write("Yearly Performance")
        st.dataframe(analysis['yearly'])
    
    # Download button
    st.subheader('Download Trade History')
    excel_file = create_excel_download(st.session_state.trade_history)
    st.download_button(
        label="Download as Excel (Monthly Sheets)",
        data=excel_file,
        file_name=f"trade_history_{datetime.now().date()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )