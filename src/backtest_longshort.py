"""
Portfolio Backtester and Visualizer Script

This script performs the following tasks:

1. Loads Capitol trades data.
2. Cleans the Capitol trades data using the `clean_capitol_trades_data` function.
3. Determines the date range for backtesting. If start and end dates are not provided as arguments, 
   it uses the earliest and latest dates available in the data.
4. Loads price data.
5. Backtests a portfolio based on the trades and price data using the `backtest_portfolio` function.
6. Saves the composition of the portfolio holdings to a CSV file.
7. Appends S&P 500 data to the portfolio wealth data for comparison purposes.
8. Saves the portfolio's performance data to a CSV file.
9. Plots the portfolio's performance.
10. Visualizes the long and short portfolio composition for each unique date.

Usage:
Simply run the script to execute the backtest and visualization processes. Ensure that all required arguments 
and data paths are set appropriately. See README for more details.
"""

import os
import pathlib
from datetime import timedelta

import numpy as np
import pandas as pd

import argparse

import matplotlib.pyplot as plt

from utils import compute_average_from_range, check_float_in_range

import yfinance as yf
from pandas_datareader import data as pdr

yf.pdr_override()


def clean_capitol_trades_data(df, path_to_prices):
    """
    Cleans the Capitol Trades data to format tickers, filter trades, and prepare the data for analysis.

    Parameters:
    - df (pd.DataFrame): DataFrame containing the Capitol Trades data with columns such as 'ticker', 'size', 'owner', 'type', and 'traded'.
    - path_to_prices (str): Path to the directory containing the CSV price files.

    Returns:
    - pd.DataFrame: A cleaned DataFrame containing the formatted and processed Capitol Trades data.
    """
    # Format tickers to correspond with pricing data
    df.dropna(subset=['ticker'], inplace=True)
    df['ticker'] = df['ticker'].apply(lambda x: x.strip(':US'))
    df['ticker'] = df['ticker'].astype('category')

    # Check which firms have price data
    firms = [x.strip('.csv') for x in os.listdir(path_to_prices)]

    # Drop trades the don't have pricing data
    df = df[df.ticker.isin(firms)]

    # Drop small trades
    df = df[df['size'] != ' < 1K']

    # Drop trades by children
    df = df[df['owner'] != ' Child']
    df['owner'] = df['owner'].cat.remove_unused_categories()

    # Convert upperbound of size bucket to log scale score (to make linear)
    df['size_score'] = df['size'].apply(lambda x: np.log(float(x.split('–')[-1].replace('K', '000').replace('M', '000000'))))

    # Assume position is average of bucket's upper and lower bound
    df['average_size'] = df['size'].apply(compute_average_from_range)

    df.drop(columns=['size'], inplace=True)

    # Drop exchanges and recieves (because I don't know what they are)
    df = df[df['type'].isin([' buy', ' sell'])]
    df['type'] = df['type'].cat.remove_unused_categories()

    # Convert buy/sell to 1/-1
    df['type_bool'] = (df['type'] == ' buy').astype(int) * 2 - 1
    df.drop(columns=['type'], inplace=True)

    # Convert size_score to contain buy/sell information
    df['size_score'] *= df['type_bool']
    df['average_size'] *= df['type_bool']

    # Round date to nearest friday (to get week closing price)
    df['week_date'] = pd.to_datetime(df.traded.dt.to_period('W').dt.end_time.dt.date - timedelta(days=2))

    return df


def load_prices(tickers, path_to_price_files):
    """
    Loads prices for a list of tickers.

    Parameters:
    - tickers (list of str): List of ticker symbols for which price data is to be loaded.
    - path_to_price_files (str): Path to the directory containing the CSV price files. Each file should be named as '<ticker>.csv'.

    Returns:
    - pd.DataFrame: A DataFrame containing columns 'Ticker', 'Date', 'Close', and 'Close_lag'.
                    'Close_lag' is the next week's closing price.

    Notes:
    - Only the closing prices for Friday are selected and returned.
    """
    df_prices = pd.DataFrame()
    for ticker in tickers:
        df_ticker_price = pd.read_csv(os.path.join(path_to_price_files, f'{ticker}.csv'))
        df_ticker_price['Ticker'] = ticker
        df_prices = df_prices.append(df_ticker_price.loc[:, ['Ticker', 'Date', 'Close']])

    df_prices['Date'] = pd.to_datetime(df_prices['Date'])
    df_prices = df_prices[df_prices['Date'].dt.day_of_week == 4]

    df_prices['Ticker'] = df_prices['Ticker'].astype('category')
    df_prices['Close_lag'] = df_prices.groupby('Ticker')['Close'].shift(-1)

    return df_prices


def load_spx(start, end):
    """
    Fetches the S&P 500 index closing prices for Fridays within the specified date range from Yahoo Finance.

    Parameters:
    - start (str): The start date in the format 'YYYY-MM-DD' from which to fetch the S&P 500 data.
    - end (str): The end date in the format 'YYYY-MM-DD' until which to fetch the S&P 500 data.

    Returns:
    - pd.DataFrame: A DataFrame containing columns 'Ticker' (always 'SPX') and 'Close', representing the
                    S&P 500's closing prices for Thursdays within the specified date range.
    """
    spx = pdr.get_data_yahoo('^spx', start=start, end=end)
    spx['Ticker'] = 'SPX'
    spx = spx.loc[spx.index.day_of_week == 4, ['Ticker', 'Close']]
    return spx


def select_date_and_merge_with_prices(df_trades_to_copy, df_historical_prices, date):
    """
    For a given date, selects trades from a provided DataFrame and merges with historical prices.

    Parameters:
    - df_trades_to_copy (pd.DataFrame): DataFrame containing the trade data. It should have columns 'week_date',
                                        'ticker', 'average_size', and 'size_score'.
    - df_historical_prices (pd.DataFrame): DataFrame containing historical price data for various assets.
                                           It should have columns 'Date', 'Ticker', 'Close', and 'Close_lag'.
    - date (datetime.date): The date for which the trades are to be selected and merged with historical prices.

    Returns:
    - pd.DataFrame: A DataFrame representing the portfolio for the given date, merged with historical price data.
                    It includes computed average sizes and size scores, along with close prices and lagged close prices.
    """
    portfolio = df_trades_to_copy.loc[(df_trades_to_copy.week_date == date), :].copy()
    portfolio['ticker'] = portfolio['ticker'].cat.remove_unused_categories()
    portfolio['date'] = date

    average_size = portfolio.groupby('ticker')['average_size'].sum().to_frame().reset_index()
    portfolio = portfolio.groupby('ticker')['size_score'].sum().sort_values().to_frame().reset_index()

    portfolio = portfolio.merge(average_size, how='left', on='ticker')
    portfolio = portfolio.merge(df_historical_prices.loc[df_historical_prices.Date == date, :], how='left', left_on='ticker', right_on='Ticker').drop(columns=['Ticker'])
    portfolio.dropna(subset=['Close', 'Close_lag'], inplace=True)

    return portfolio


def compute_holdings(df, wealth, scale):
    """
    Computes the holdings and returns for each asset in the portfolio based on their relative sizes and the total wealth.

    Parameters:
    - df (pd.DataFrame): DataFrame containing the portfolio's asset data. It should have columns 'average_size' and 'Close'.
    - wealth (float): The current wealth value.
    - scale (float): Scaling factor to adjust the leverage in the assets.

    Returns:
    - pd.DataFrame: Updated DataFrame with additional columns: 'weights', 'holding_value', 'holding_size',
                    'holding_value_next', and 'week_return_on_position', representing the computed values for the holdings.
    - float: The new computed wealth value after the returns.
    """
    df['weights'] = np.abs(df['average_size']) / np.abs(df['average_size']).sum()

    df['holding_value'] = df['weights'] * wealth * scale

    df['holding_size'] = df['holding_value'] / df['Close']

    df['holding_value_next'] = df['holding_size'] * df['Close_lag']

    df['week_return_on_position'] = df['holding_value_next'] - df['holding_value']

    wealth_new = df['holding_value_next'].sum()

    return df, wealth_new


def backtest_portfolio(df_trades_to_copy, df_historical_prices, initial_wealth, dates, portfolio_sample=1/3):
    """
    Backtests a portfolio based on a given set of trade data, historical prices, and date range.

    Parameters:
    - df_trades_to_copy (pd.DataFrame): DataFrame containing the trade data to be copied/backtested.
    - df_historical_prices (pd.DataFrame): DataFrame containing historical price data for various assets.
    - dates (iteratable): datetime.date iteratable representing the dates (of Fridays) for which the portfolio is backtested.
    - portfolio_sample (float, optional): Fraction of the portfolio to be sampled for short and long positions.
                                          Defaults to 1/3.

    Returns:
    - pd.DataFrame: DataFrame containing 'date' and 'wealth' columns, representing the portfolio's performance over the given dates.
    - pd.DataFrame: DataFrame containing the portfolio holdings over the backtested period.

    Notes:
    - Backtesting is done by dividing the portfolio into 'short' and 'long' positions based on the `portfolio_sample` value.
    - Wealth is computed based on the performance of these positions.
    """
    ws = [initial_wealth]

    df_pf = pd.DataFrame()
    for i, date in enumerate(dates[1:]):
        wealth = ws[-1]

        portfolio = select_date_and_merge_with_prices(df_trades_to_copy, df_historical_prices, date)

        cutoff = int(portfolio.shape[0] * portfolio_sample)

        if portfolio.shape[0] > 0:

            short = portfolio[:cutoff].copy()
            long = portfolio[-cutoff:].copy()

            scale = 0.3 if short.shape[0] > 0 else 0.0

            long, wealth_long_new = compute_holdings(long, wealth, 1+scale)
            short, wealth_short_new = compute_holdings(short, wealth, -scale)

            long['position'] = 'long'
            short['position'] = 'short'

            df_pf = df_pf.append(pd.concat([long, short]))

            wealth_new = wealth_long_new + wealth_short_new

        ws.append(wealth_new)

    return pd.DataFrame({'date': dates, 'wealth': ws}), df_pf


def plot_portfolio_performance(portfolio_wealth, save_path=None):
    """
    Plots the performance of a portfolio in comparison to the S&P 500 index over a given time range.

    Parameters:
    - portfolio_wealth (pd.DataFrame): DataFrame containing the investor's wealth at each point in time.
                                       It should have columns 'date' and 'wealth'.
    - start_date (datetime.datetime): Start date of the performance period.
    - end_date (datetime.datetime): End date of the performance period.
    - save_path (str, optional): Path to save the plot as an image file. If not provided, the plot is displayed instead.
    """
    initial_wealth = portfolio_wealth.wealth[0]
    plt.figure(figsize=(25, 7))
    plt.plot(portfolio_wealth.date, portfolio_wealth.wealth / initial_wealth, label='Long short portfolio')
    plt.plot(portfolio_wealth.date, portfolio_wealth.wealth_spx / initial_wealth, label='S&P500')
    plt.legend()
    if save_path is None:
        plt.show()
    else:
        plt.savefig(save_path)
    plt.close()


def long_short_portfolio_composition(portfolio, date, save_path):
    """
    Visualize the composition of a long-short portfolio on a given date.

    This function generates two pie charts: one for the long positions and one for the short positions 
    in the portfolio. Non-zero weighted assets are displayed in the charts.

    Parameters:
    - portfolio (DataFrame): A pandas DataFrame containing portfolio data with columns 'Date', 'position', 'weights', and 'ticker'.
    - date (str or datetime-like): The date for which the portfolio composition is to be visualized.
    - save_path (str, optional): If provided, the path (with optional string formatting for date) where the resulting plot 
      should be saved. If not provided, the plot will be shown interactively.
    """
    long = portfolio[(portfolio.Date == date) & (portfolio.position == 'long')]
    short = portfolio[(portfolio.Date == date) & (portfolio.position == 'short')]

    _, axes= plt.subplots(1, 2, figsize=(13, 7))

    axes[0].pie(long.loc[long.weights != 0.0, 'weights'],
            labels=long.loc[long.weights != 0.0, 'ticker'],
            radius=1.0, autopct="%.1f%%", pctdistance=0.8)
    axes[0].set_title('Long')
    axes[1].pie(short.loc[short.weights != 0.0, 'weights'],
            labels=short.loc[short.weights != 0.0, 'ticker'],
            radius=0.5, autopct="%.1f%%", pctdistance=0.8)
    axes[1].set_title('Short')
    if save_path is None:
        plt.show()
    else:
        plt.savefig(save_path.format(pd.to_datetime(date).strftime('%Y%m%d')))
    plt.close()


def compute_spx_portfolio(start_date, end_date):
    """
    Compute the relative wealth of the S&P 500 index over a specified date range.

    This function loads the S&P 500 index data for the given date range and computes the relative 
    wealth based on the closing prices, normalized to the first date's closing price.

    Parameters:
    - start_date (datetime.date or similar datetime-like object): Start date of the desired data range.
    - end_date (datetime.date or similar datetime-like object): End date of the desired data range.
    """
    spx = load_spx(start_date.strftime('%Y-%m-%d'), (end_date+timedelta(days=1)).strftime('%Y-%m-%d'))
    return (spx['Close'] / spx['Close'].iloc[0]).rename('wealth_spx').to_frame()


def main():

    class Args():
        def __init__(self):
            self.data_path = 'data'
            self.capitoltrades_filename = "CapitolTrades_raw"
            self.prices_dirname="yfinance_prices"
            self.wealth_initial=10000.0
            self.portfolio_sample=0.33333333
            self.start_date=None
            self.end_date=None
            self.save_dir="portfolios"
            self.performance_filename="wealth"
            self.composition_filename="composition"
            self.plot_performance_filename="wealth_plot"
            self.plot_composition_filename="composition_plot"
    args = Args()


    
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data_path",
        help="The path to the output file. Default: data",
        type=str,
        default="data"
        )

    parser.add_argument(
        "--capitoltrades_filename",
        help="Capitol Trades file name. Default: CapitolTrades_raw",
        type=str,
        default="CapitolTrades_raw"
        )

    parser.add_argument(
        "--prices_dirname",
        help="Directory name where stock prices data is stored. Default: yfinance_prices",
        type=str,
        default="yfinance_prices"
        )
    
    parser.add_argument(
        "--wealth_initial",
        help="Initial starting wealth of investor. Default: 10_000.0",
        type=float,
        default=10000.0
        )

    parser.add_argument(
        "--portfolio_sample",
        help="Fraction of total available stocks to include in the portfolio sample. Should be between 0.0 and 0.5. Default: 0.33333333",
        type=check_float_in_range(lb=0.0, ub=0.5),
        default=0.33333333
        )

    parser.add_argument(
        "--start_date",
        help="Start date for the analysis in the format 'YYYY-MM-DD'.",
        type=str
        )

    parser.add_argument(
        "--end_date",
        help="End date for the analysis in the format 'YYYY-MM-DD'.",
        type=str
        )

    parser.add_argument(
        "--save_dir",
        help="Directory where the analysis results and portfolios will be saved. Default: portfolios",
        type=str,
        default="portfolios"
        )

    parser.add_argument(
        "--performance_filename",
        help="File name to save the wealth performance of the portfolios. Default: wealth",
        type=str,
        default="wealth"
        )
    
    parser.add_argument(
        "--composition_filename",
        help="File name to save the composition of the portfolios. Default: composition",
        type=str,
        default="composition"
        )
    
    parser.add_argument(
        "--plot_performance_filename",
        help="File name for saving the plotted performance of the portfolios.",
        type=str,
        )
    
    parser.add_argument(
        "--plot_composition_filename",
        help="File name for saving the plotted composition of the portfolios.",
        type=str,
        )

    args = parser.parse_args()

    ROOT = os.getcwd()
    if pathlib.PurePath(ROOT).name == 'src':
        raise Exception('Please run the script from the root directory.')

    PATH_DATA = os.path.join(ROOT, args.data_path)
    PATH_DATA_PRICES = os.path.join(PATH_DATA, args.prices_dirname)
    PATH_DATA_PORTFOLIOS = os.path.join(PATH_DATA, args.save_dir)

    capitoltrades_fl = os.path.join(PATH_DATA, f'{args.capitoltrades_filename}.csv')
    composition_fl = os.path.join(PATH_DATA_PORTFOLIOS, f'{args.composition_filename}.csv')
    performance_fl = os.path.join(PATH_DATA_PORTFOLIOS, f'{args.performance_filename}.csv')

    if args.plot_composition_filename is None:
        composition_plot_fl = None
    else:
        composition_plot_fl = os.path.join(PATH_DATA_PORTFOLIOS, args.plot_composition_filename + '_{}.png')

    if args.plot_performance_filename is None:
        performance_plot_fl = None
    else:
        performance_plot_fl = os.path.join(PATH_DATA_PORTFOLIOS, f'{args.plot_performance_filename}.png')

    try:
        os.makedirs(PATH_DATA_PORTFOLIOS)
    except OSError:
        pass

    print('Loading data')
    df_trades = pd.read_csv(
            capitoltrades_fl,
            parse_dates=[
                'traded'
                ],
            usecols=[
                'politician',
                'trade_issuer',
                'ticker',
                'traded',
                'owner',
                'type',
                'size',
                'price'
                ],
            dtype={
                'owner': 'category',
                'politician': 'category',
                'type': 'category',
                },
        )
    
    print('Cleaning data')
    df_trades = clean_capitol_trades_data(df_trades, PATH_DATA_PRICES)

    earliest_date = df_trades.week_date.min()
    today = pd.to_datetime('today')
    if args.start_date is None:
        min_week = earliest_date
        max_week = today
    else:
        min_week = pd.to_datetime(args.start_date)
        max_week = pd.to_datetime(args.end_date)
        if min_week.date() < earliest_date.date():
            print('overriding start date to earliest available date: 2019-01-01')
            min_week = earliest_date
        if max_week.date() > today.date():
            print('overriding end date to today')
            max_week = today

    print('Loading prices')
    df_prices = load_prices(df_trades.ticker.dropna().unique(), PATH_DATA_PRICES)

    # Week freq rounds to Sunday. We want Friday closing prices, so we subtract 2 days.
    dates = pd.date_range(min_week-timedelta(days=7), max_week, freq='W') - timedelta(days=2)

    print('Backtesting portfolio')
    portfolio_wealth, portfolio_holdings = backtest_portfolio(df_trades, df_prices, args.wealth_initial, dates, args.portfolio_sample)

    print('Generating outputs')
    print('# Saving')
    portfolio_holdings.to_csv(composition_fl, index=False)

    # Append spx for comparison
    spx = compute_spx_portfolio(dates[0], dates[-1])
    portfolio_wealth = portfolio_wealth.merge(spx*args.wealth_initial, how='left', left_on='date', left_index=False, right_index=True)
    portfolio_wealth.fillna(method='ffill', inplace=True)

    portfolio_wealth.to_csv(performance_fl, index=False)

    print('# Plotting')
    plot_portfolio_performance(portfolio_wealth, performance_plot_fl)
    for date in portfolio_holdings.Date.unique():
        long_short_portfolio_composition(portfolio_holdings, date, composition_plot_fl)
        

if __name__ == '__main__':
    main()
