"""
add --scrape_only_new args
debug long_short.py
have some portfolio output document
"""

import os
import yaml
from datetime import timedelta

import numpy as np
import pandas as pd

import argparse

import matplotlib.pyplot as plt

from utils import compute_average_from_range, date_parser, check_float_in_range

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


def backtest_portfolio(df_trades_to_copy, df_historical_prices, dates, portfolio_sample=1/3):
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
    ws = [1]

    df_pf = pd.DataFrame()
    for i, date in enumerate(dates):
        wealth = ws[-1]

        portfolio = select_date_and_merge_with_prices(df_trades_to_copy, df_historical_prices, date)

        cutoff = int(portfolio.shape[0] * portfolio_sample)

        if portfolio.shape[0] > 0:

            short = portfolio[:cutoff].copy()
            long = portfolio[-cutoff:].copy()

            scale = 0.3 if short.shape[0] > 0 else 0.0

            long, wealth_long_new = compute_holdings(long, wealth, 1+scale)
            short, wealth_short_new = compute_holdings(short, wealth, -scale)

            df_pf = df_pf.append(pd.concat(long, short))

            wealth_new = wealth_long_new + wealth_short_new

        ws.append(wealth_new)

    # TODO append 1 week earlier to beginning of date
    return pd.DataFrame({'date': dates, 'wealth': ws}), df_pf


def plot_portfolio_performance(portfolio_wealth, start_date, end_date, save_path=None):
    """
    Plots the performance of a portfolio in comparison to the S&P 500 index over a given time range.

    Parameters:
    - portfolio_wealth (pd.DataFrame): DataFrame containing the investor's wealth at each point in time.
                                       It should have columns 'date' and 'wealth'.
    - start_date (datetime.datetime): Start date of the performance period.
    - end_date (datetime.datetime): End date of the performance period.
    - save_path (str, optional): Path to save the plot as an image file. If not provided, the plot is displayed instead.
    """
    spx = load_spx(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    n_spx_shares = 1 / spx['Close'].iloc[0]

    plt.figure(figsize=(25, 7))
    plt.plot(portfolio_wealth.date, [w for w in portfolio_wealth.wealth], label='Long short portfolio')
    plt.plot(spx.index, (spx['Close'] * n_spx_shares), label='S&P500')
    plt.legend()
    if save_path is None:
        plt.show()
    else:
        plt.savefig(save_path)
    plt.close()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data_path",
        help="The path to the output file. Default: data",
        type=str,
        default="data"
        )

    parser.add_argument(
        "--capitoltrades_data",
        help="Capitol Trades file name. Default: CapitolTrades_raw.csv",
        type=str,
        default="CapitolTrades_raw.csv"
        )

    parser.add_argument(
        "--wealth_initial",
        help="Initial starting wealth of investor.",
        type=float,
        default=100000.0
        )

    parser.add_argument(
        "--portfolio_sample",
        help="TODO.",
        type=check_float_in_range(lb=0.0, ub=0.5),
        default=0.33333333
        )

    parser.add_argument(
        "--start_date",
        help="TODO",
        type=str,
        default='2020-09-03'
        )

    parser.add_argument(
        "--end_date",
        help="TODO",
        type=str,
        default='2023-08-15'
        )

    parser.add_argument(
        "--save_path",
        help="TODO",
        type=str,
        default="TODO"
        )

    # parser.add_argument('--savefailed', action='store_true')
    # parser.add_argument('--no-savefailed', dest='savefailed', action='store_false')
    # parser.set_defaults(savefailed=False)

    args = parser.parse_args()

    ROOT = os.path.dirname(os.getcwd())
    PATH_DATA = os.path.join(ROOT, args.data_path)
    PATH_DATA_PRICES = os.path.join(PATH_DATA, 'yfinance_prices')
    PATH_DATA_PORTFOLIOS = os.path.join(ROOT, 'portfolios')

    try:
        os.makedirs(PATH_DATA_PORTFOLIOS)
    except OSError:
        pass

    min_week = pd.to_datetime(args.start_date)
    max_week = pd.to_datetime(args.end_date)

    # TODO if the start or end dates are outside of the df_trades date range: terminate!!!

    df_trades = pd.read_csv(
            os.path.join(args.data_path, args.capitoltrades_data),
            parse_dates=[
                'traded'
                ],
            date_parser=date_parser,
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

    df_trades = clean_capitol_trades_data(df_trades, PATH_DATA_PRICES)
    df_prices = load_prices(df_trades.ticker.dropna().unique(), PATH_DATA_PRICES)

    # Week freq rounds to Sunday. We want Friday closing prices, so we subtract 2 days.
    dates = pd.date_range(min_week, max_week, freq='W') - timedelta(days=2)

    portfolio_wealth, portfolio_holdings = backtest_portfolio(df_trades, df_prices, dates, args.portfolio_sample)

    portfolio_fn = os.path.join(PATH_DATA, 'portfolios', f'portfolio_holdings_{args.start_date}-{args.end_date}.yml')
    portfolio_holdings.to_csv(portfolio_fn)

    wealth_fn = os.path.join(PATH_DATA, 'portfolios', f'wealth_{args.start_date}-{args.end_date}.yml')
    portfolio_wealth.to_csv(wealth_fn)

    plot_portfolio_performance(portfolio_wealth, min_week, max_week, args.save_path)


if __name__ == '__main__':
    main()
