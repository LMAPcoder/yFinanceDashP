import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import requests
import random
from fp.fp import FreeProxy  # Import FreeProxy
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.colors as pc

# Import functions from functions.py
from functions import get_proxy_dict, fetch_info, fetch_history, fetch_balance, \
    fetch_income, fetch_cash, fetch_splits, fetch_table, format_value, \
    remove_duplicates, top_table, info_table, plot_gauge, plot_candles_stick_bar, \
    plot_candles_stick, plot_line_multiple, plot_balance, plot_assets, \
    plot_liabilities, plot_equity, plot_income

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="NIFTY 200 Dashboard",
    page_icon=":material/stacked_line_chart:",
    layout="wide",
)

# --- LOGO ---
st.logo("imgs/logo_friendly.png", size="large")  # Use the friendly logo

# --- NIFTY 200 Page Content ---
st.title("NIFTY 200 Dashboard")

def get_nifty_200_tickers():
    """
    Fetches the list of NIFTY 200 stocks from the NSE website.
    Handles potential errors and retries.
    """
    url = "https://www.nseindia.com/products-services/indices-equity-indices-broad-market-indices-nifty-200-list"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    for attempt in range(3):  # Retry up to 3 times
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            df = pd.read_html(response.text)
            if df:
                return df[0]['Symbol'].tolist()  # Extract ticker symbols
            else:
                st.error(f"Failed to retrieve NIFTY 200 data: No table found. Attempt {attempt + 1}")
                return []
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching NIFTY 200 data: {e}. Attempt {attempt + 1}")
            # Optionally add a delay before retrying
            if attempt < 2:
                time.sleep(5)
    return []  # Return an empty list if all attempts fail

def get_top_gainers_losers():
    """
    Fetches the top 5 gainers and losers for the day from NSE.
    Handles errors, retries, and empty data.
    """
    try:
        gainer_url = "https://www.nseindia.com/live_market/dynaContent/live_analysis/nifty_top_gainers.json"
        loser_url = "https://www.nseindia.com/live_market/dynaContent/live_analysis/nifty_top_losers.json"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        gainers_response = requests.get(gainer_url, headers=headers, timeout=10)
        losers_response = requests.get(loser_url, headers=headers, timeout=10)

        gainers_response.raise_for_status()
        losers_response.raise_for_status()

        gainers_data = gainers_response.json().get('data', [])
        losers_data = losers_response.json().get('data', [])

        gainers_df = pd.DataFrame(gainers_data)
        losers_df = pd.DataFrame(losers_data)

        if gainers_df.empty or len(gainers_df) == 0:
            st.warning("No top gainers data available.")
            return pd.DataFrame(), pd.DataFrame()  # Return empty DataFrames
        if losers_df.empty or len(losers_df) == 0:
            st.warning("No top losers data available.")
            return pd.DataFrame(), pd.DataFrame()

        return gainers_df, losers_df

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching top gainers/losers: {e}")
        return pd.DataFrame(), pd.DataFrame()  # Return empty DataFrames
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON: {e}")
        return pd.DataFrame(), pd.DataFrame()

def display_indices():
    """Displays the performance of key Indian indices."""
    indices = ["^NSEI", "^CNX200", "^BSESN", "^CNX500"]  # Add NIFTY 200 and SENSEX
    indices_names = ["NIFTY 50", "NIFTY 200", "SENSEX", "NIFTY 500"]
    try:
        indices_data = yf.download(indices, period="1d")
        if not indices_data.empty:
            st.subheader("Key Indian Indices")
            latest_prices = indices_data['Close'].iloc[-1]
            previous_closes = indices_data['Close'].iloc[-2]
            changes = latest_prices - previous_closes
            percent_changes = (changes / previous_closes) * 100
            index_data = []
            for i, index in enumerate(indices):
                index_data.append({
                    "Index": indices_names[i],
                    "Last Traded Price": latest_prices[index],
                    "Change": changes[index],
                    "Change %": percent_changes[index],
                })
            df = pd.DataFrame(index_data)
            df = df.set_index("Index")
            st.dataframe(df.style.format({
                "Last Traded Price": "{:.2f}",
                "Change": "{:.2f}",
                "Change %": "{:.2f}%",
            }), use_container_width=True)
        else:
            st.warning("Could not retrieve index data.")
    except Exception as e:
        st.error(f"Error fetching index data: {e}")

def display_top_movers():
    """Displays the top 5 gainers and losers."""
    gainers_df, losers_df = get_top_gainers_losers()
    if not gainers_df.empty:
        st.subheader("Top 5 Gainers")
        gainers_df = gainers_df[['symbol', 'ltp', 'change', 'pChange']]  # Select relevant columns
        gainers_df.columns = ['Symbol', 'Last Traded Price', 'Change', 'Change %']
        st.dataframe(gainers_df.style.format({
            'Last Traded Price': '{:.2f}',
            'Change': '{:.2f}',
            'Change %': '{:.2f}%'
        }), use_container_width=True)

    if not losers_df.empty:
        st.subheader("Top 5 Losers")
        losers_df = losers_df[['symbol', 'ltp', 'change', 'pChange']]  # Select relevant columns
        losers_df.columns = ['Symbol', 'Last Traded Price', 'Change', 'Change %']
        st.dataframe(losers_df.style.format({
            'Last Traded Price': '{:.2f}',
            'Change': '{:.2f}',
            'Change %': '{:.2f}%'
        }), use_container_width=True)

def display_nifty_200_overview():
    """Displays an overview of the NIFTY 200 index."""
    nifty_200_info = yf.Ticker("^CNX200").info
    if nifty_200_info:
        st.subheader("NIFTY 200 Overview")
        nifty_200_df = pd.DataFrame({
            "Name": nifty_200_info.get("shortName", "-"),
            "Market": nifty_200_info.get("market", "-"),
            "Open": nifty_200_info.get("open", "-"),
            "Previous Close": nifty_200_info.get("previousClose", "-"),
            "Volume": nifty_200_info.get("volume", "-"),
        }, index=[0]).T  # Transpose for better layout
        st.dataframe(nifty_200_df, use_container_width=True)

        # Fetch and display a chart for NIFTY 200
        nifty_200_history = yf.download("^CNX200", period="1y")  # Example: 1-year history
        if not nifty_200_history.empty:
            fig = plot_candles_stick_bar(nifty_200_history, title="NIFTY 200 - 1 Year", currency="INR")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Could not retrieve NIFTY 200 historical data for the chart.")
    else:
        st.warning("Could not retrieve NIFTY 200 overview data.")

def display_selected_stock(selected_stock):
    """Displays detailed information and a chart for a selected stock."""
    if selected_stock:
        st.subheader(f"Security: {selected_stock}")
        try:
            stock_info = yf.Ticker(selected_stock).info
            if stock_info:
                stock_info_df = info_table(stock_info)
                st.dataframe(stock_info_df, use_container_width=True)

                stock_history = yf.download(selected_stock, period="1y")  # 1-year history
                if not stock_history.empty:
                    fig = plot_candles_stick_bar(stock_history, title=f"{selected_stock} - 1 Year", currency="INR")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"Could not retrieve historical data for {selected_stock} for the chart.")
            else:
                st.error(f"Could not retrieve information for ticker: {selected_stock}")
        except Exception as e:
            st.error(f"Error fetching data for {selected_stock}: {e}")

def main():
    """Main function to run the Streamlit application."""
    display_indices()
    display_top_movers()
    display_nifty_200_overview()

    # Allow the user to select a stock from NIFTY 200
    nifty_200_tickers = get_nifty_200_tickers()
    if nifty_200_tickers:
        selected_stock = st.selectbox("Select a stock from NIFTY 200 to view details", nifty_200_tickers)
        display_selected_stock(selected_stock)
    else:
        st.warning("Could not retrieve NIFTY 200 stock list.  Unable to select a stock.")

if __name__ == "__main__":
    main()
