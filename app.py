import streamlit as st
from datetime import datetime
import pandas as pd
import calendar
from io import BytesIO
import uuid
import json
from pathlib import Path

# File to store trade data
DATA_FILE = Path("trade_data.json")

# Function to load data from JSON file
def load_data():
    try:
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
            trade_history = pd.DataFrame(data.get('trade_history', []))
            if not trade_history.empty:
                trade_history['Date'] = pd.to_datetime(trade_history['Date'])
            trading_pairs = data.get('trading_pairs', ['USDJPY', 'EURUSD'])
            st.write("Debug: Loaded data from file.")
            return trade_history, trading_pairs
        st.write("Debug: No data file found, initializing defaults.")
        return pd.DataFrame(columns=['ID', 'Date', 'Pair', 'Type', 'Ratio', 'Points', 'P/L']), ['USDJPY', 'EURUSD']
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(columns=['ID', 'Date', 'Pair', 'Type', 'Ratio', 'Points', 'P/L']), ['USDJPY', 'EURUSD']

# Function to save data to JSON file
def save_data(trade_history, trading_pairs):
    try:
        data = {
            'trade_history': trade_history.to_dict('records'),
            'trading_pairs': trading_pairs
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, default=str)
        st.write("Debug: Data saved to file.")
    except Exception as e:
        st.error(f"Error saving data: {e}")

# Function to clear data
def clear_data():
    try:
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        st.session_state.trade_history = pd.DataFrame(columns=['ID', 'Date', 'Pair', 'Type', 'Ratio', 'Points', 'P/L'])
        st.session_state.trading_pairs = ['USDJPY', 'EURUSD']
        save_data(st.session_state.trade_history, st.session_state.trading_pairs)
        st.success("All data cleared.")
        st.rerun()
    except Exception as e:
        st.error(f"Error clearing data: {e}")

# Initialize session state
if 'trade_history' not in st.session_state or 'trading_pairs' not in st.session_state:
    st.session_state.trade_history, st.session_state.trading_pairs = load_data()
    st.write(f"Debug: Initialized trading pairs: {st.session_state.trading_pairs}")

# Function to add a new trading pair
def add_trading_pair(new_pair):
    new_pair = new_pair.upper().strip()
    if new_pair and new_pair not in st.session_state.trading_pairs:
        st.session_state.trading_pairs.append(new_pair)
        save_data(st.session_state.trade_history, st.session_state.trading_pairs)
        st.success(f"Added new trading pair: {new_pair}")
    elif new_pair in st.session_state.trading_pairs:
        st.warning(f"Pair {new_pair} already exists.")
    else:
        st.error("Please enter a valid pair name.")

# Function to add a trade
def add_trade(date, pair, trade_type, ratio):
    if ratio == '1:1':
        points = 1 if trade_type == 'TP' else -1
    else:  # 1:2
        points = 2 if trade_type == 'TP' else -1
    p_l = 'Profit' if trade_type == 'TP' else 'Loss'
    
    new_trade = pd.DataFrame({
        'ID': [str(uuid.uuid4())],
        'Date': [date],
        'Pair': [pair],
        'Type': [trade_type],
        'Ratio': [ratio],
        'Points': [points],
        'P/L': [p_l]
    })
    
    st.session_state.trade_history = pd.concat([st.session_state.trade_history, new_trade], ignore_index=True)
    st.session_state.trade_history['Date'] = pd.to_datetime(st.session_state.trade_history['Date'])
    st.session_state.trade_history = st.session_state.trade_history.sort_values('Date')
    save_data(st.session_state.trade_history, st.session_state.trading_pairs)

# Function to edit a trade
def edit_trade(trade_id, new_date, new_pair, new_type, new_ratio):
    index = st.session_state.trade_history[st.session_state.trade_history['ID'] == trade_id].index[0]
    if new_ratio == '1:1':
        points = 1 if new_type == 'TP' else -1
    else:  # 1:2
        points = 2 if new_type == 'TP' else -1
    p_l = 'Profit' if new_type == 'TP' else 'Loss'
    
    st.session_state.trade_history.at[index, 'Date'] = new_date
    st.session_state.trade_history.at[index, 'Pair'] = new_pair
    st.session_state.trade_history.at[index, 'Type'] = new_type
    st.session_state.trade_history.at[index, 'Ratio'] = new_ratio
    st.session_state.trade_history.at[index, 'Points'] = points
    st.session_state.trade_history.at[index, 'P/L'] = p_l
    st.session_state.trade_history['Date'] = pd.to_datetime(st.session_state.trade_history['Date'])
    st.session_state.trade_history = st.session_state.trade_history.sort_values('Date')
    save_data(st.session_state.trade_history, st.session_state.trading_pairs)

# Function to delete a trade
def delete_trade(trade_id):
    st.session_state.trade_history = st.session_state.trade_history[st.session_state.trade_history['ID'] != trade_id]
    save_data(st.session_state.trade_history, st.session_state.trading_pairs)

# Function to calculate advanced metrics
def calculate_advanced_metrics(df):
    if df.empty:
        return {
            'consecutive_losses': 0,
            'max_drawdown': 0,
            'total_win_rate': '0.00%'
        }
    
    max_consecutive_losses = 0
    current_consecutive_losses = 0
    for pl in df['P/L']:
        if pl == 'Loss':
            current_consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
        else:
            current_consecutive_losses = 0
    
    cumulative_points = df['Points'].cumsum()
    peak = cumulative_points.cummax()
    drawdown = peak - cumulative_points
    max_drawdown = drawdown.max() if len(drawdown) > 0 else 0
    
    total_win_rate = (df['P/L'] == 'Profit').mean() if not df.empty else 0
    total_win_rate = f"{total_win_rate:.2%}"
    
    return {
        'consecutive_losses': max_consecutive_losses,
        'max_drawdown': max_drawdown,
        'total_win_rate': total_win_rate
    }

# Function to generate analysis
def generate_analysis(df):
    if df.empty:
        return None
    
    analysis = {}
    
    monthly = df.copy()
    monthly['Month'] = monthly['Date'].dt.month
    monthly['Month_Name'] = monthly['Date'].dt.month_name()
    monthly['Year'] = monthly['Date'].dt.year
    monthly_agg = monthly.groupby(['Year', 'Month', 'Month_Name', 'Pair']).agg(
        Total_Trades=('Points', 'count'),
        TP=('Type', lambda x: (x == 'TP').sum()),
        SL=('Type', lambda x: (x == 'SL').sum()),
        Total_Points=('Points', 'sum'),
        Win_Rate=('P/L', lambda x: (x == 'Profit').mean())
    ).reset_index()
    monthly_agg['Win_Rate'] = monthly_agg['Win_Rate'].apply(lambda x: f"{x:.2%}")
    
    weekly = df.copy()
    weekly['Week'] = weekly['Date'].dt.isocalendar().week
    weekly['Year'] = weekly['Date'].dt.isocalendar().year
    weekly_agg = weekly.groupby(['Year', 'Week', 'Pair']).agg(
        Total_Trades=('Points', 'count'),
        TP=('Type', lambda x: (x == 'TP').sum()),
        SL=('Type', lambda x: (x == 'SL').sum()),
        Total_Points=('Points', 'sum'),
        Win_Rate=('P/L', lambda x: (x == 'Profit').mean())
    ).reset_index()
    weekly_agg['Win_Rate'] = weekly_agg['Win_Rate'].apply(lambda x: f"{x:.2%}")
    
    yearly = df.copy()
    yearly['Year'] = yearly['Date'].dt.year
    yearly_agg = yearly.groupby(['Year', 'Pair']).agg(
        Total_Trades=('Points', 'count'),
        TP=('Type', lambda x: (x == 'TP').sum()),
        SL=('Type', lambda x: (x == 'SL').sum()),
        Total_Points=('Points', 'sum'),
        Win_Rate=('P/L', lambda x: (x == 'Profit').mean())
    ).reset_index()
    yearly_agg['Win_Rate'] = yearly_agg['Win_Rate'].apply(lambda x: f"{x:.2%}")
    
    advanced = calculate_advanced_metrics(df)
    
    analysis['monthly'] = monthly_agg
    analysis['weekly'] = weekly_agg
    analysis['yearly'] = yearly_agg
    analysis['advanced'] = advanced
    
    return analysis

# Function to create downloadable Excel
def create_excel_download(df):
    if df.empty:
        return None
    
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    
    for (year, month), group in df.groupby(['Year', 'Month']):
        month_name = calendar.month_name[month]
        sheet_name = f"{month_name}_{year}"
        group.drop(['Year', 'Month'], axis=1).to_excel(writer, sheet_name=sheet_name[:31], index=False)
    
    summary = df.groupby(['Year', 'Month', 'Pair']).agg(
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

# Clear data button
st.subheader('Clear All Data')
if st.button('Clear Data'):
    clear_data()

# Add new trading pair
st.subheader('Manage Trading Pairs')
new_pair = st.text_input('Enter New Trading Pair (e.g., GBPUSD)')
if st.button('Add Pair'):
    add_trading_pair(new_pair)

# Date selection and trade entry
st.subheader('Add New Trade')
selected_date = st.date_input('Select Trading Date', datetime.today())
col1, col2, col3 = st.columns(3)
with col1:
    trade_type = st.radio('Trade Type', ['TP', 'SL'])
with col2:
    ratio = st.radio('Risk:Reward Ratio', ['1:1', '1:2'])
with col3:
    pair = st.selectbox('Trading Pair', options=st.session_state.trading_pairs, key='pair_select')

if st.button('Add Trade'):
    add_trade(selected_date, pair, trade_type, ratio)
    st.success(f"Added {trade_type} trade with {ratio} ratio for {pair} on {selected_date}")

# Display trade history
st.subheader('Trade History')
if not st.session_state.trade_history.empty:
    st.dataframe(st.session_state.trade_history)
else:
    st.info("No trades recorded yet.")

# Edit/Delete functionality
if not st.session_state.trade_history.empty:
    st.subheader('Manage Trades')
    edit_mode = st.checkbox('Enable Edit/Delete Mode')
    
    if edit_mode:
        trade_id = st.selectbox(
            'Select Trade to Edit/Delete',
            st.session_state.trade_history['ID'],
            format_func=lambda x: f"Trade {x[:8]}... ({st.session_state.trade_history[st.session_state.trade_history['ID'] == x]['Date'].iloc[0].date()}, {st.session_state.trade_history[st.session_state.trade_history['ID'] == x]['Pair'].iloc[0]}, {st.session_state.trade_history[st.session_state.trade_history['ID'] == x]['Type'].iloc[0]}, {st.session_state.trade_history[st.session_state.trade_history['ID'] == x]['Ratio'].iloc[0]})"
        )
        
        col_edit, col_delete = st.columns(2)
        with col_edit:
            st.write("Edit Trade")
            new_date = st.date_input(
                'New Date',
                st.session_state.trade_history[st.session_state.trade_history['ID'] == trade_id]['Date'].iloc[0].date(),
                key='edit_date'
            )
            new_pair = st.selectbox(
                'New Pair',
                st.session_state.trading_pairs,
                index=st.session_state.trading_pairs.index(st.session_state.trade_history[st.session_state.trade_history['ID'] == trade_id]['Pair'].iloc[0]),
                key='edit_pair'
            )
            new_type = st.radio(
                'New Type',
                ['TP', 'SL'],
                index=0 if st.session_state.trade_history[st.session_state.trade_history['ID'] == trade_id]['Type'].iloc[0] == 'TP' else 1,
                key='edit_type'
            )
            new_ratio = st.radio(
                'New Ratio',
                ['1:1', '1:2'],
                index=0 if st.session_state.trade_history[st.session_state.trade_history['ID'] == trade_id]['Ratio'].iloc[0] == '1:1' else 1,
                key='edit_ratio'
            )
            if st.button('Update Trade'):
                edit_trade(trade_id, new_date, new_pair, new_type, new_ratio)
                st.success(f"Updated trade {trade_id[:8]}...")
        
        with col_delete:
            if st.button('Delete Trade'):
                delete_trade(trade_id)
                st.success(f"Deleted trade {trade_id[:8]}...")
                st.rerun()

# Analysis dashboard
if not st.session_state.trade_history.empty:
    st.subheader('Performance Analysis')
    analysis = generate_analysis(st.session_state.trade_history)
    
    tab1, tab2, tab3, tab4 = st.tabs(["Monthly", "Weekly", "Yearly", "Advanced Metrics"])
    
    with tab1:
        st.write("Monthly Performance")
        st.dataframe(analysis['monthly'])
        
    with tab2:
        st.write("Weekly Performance")
        st.dataframe(analysis['weekly'])
        
    with tab3:
        st.write("Yearly Performance")
        st.dataframe(analysis['yearly'])
        
    with tab4:
        st.write("Advanced Metrics")
        st.write(f"**Maximum Consecutive Losses**: {analysis['advanced']['consecutive_losses']}")
        st.write(f"**Maximum Drawdown**: {analysis['advanced']['max_drawdown']} points")
        st.write(f"**Total Win Rate**: {analysis['advanced']['total_win_rate']}")
    
    st.subheader('Download Trade History')
    excel_file = create_excel_download(st.session_state.trade_history)
    st.download_button(
        label="Download as Excel (Monthly Sheets)",
        data=excel_file,
        file_name=f"trade_history_{datetime.now().date()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
