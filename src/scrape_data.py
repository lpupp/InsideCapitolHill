"""Scrape data for InsideCapitolHill project for the Programming Practices
for Research in Economics course.

Author: Luca Gaegauf (lpupp) 09.2023

This script scrapes the following data:
    - Trades made by US congress members from capitoltrades.com,
    - Congress members' committee memberships from ballotpedia.org.

Furthermore, using the yahoo finance API, it downloads the following data:
    - Firm-industry pairs for firms traded by congress members from finance.yahoo.com,
    - Historical price data for firms traded by congress members from finance.yahoo.com.

Notes/confessions: #TODO
    - This script was not optimized for speed. It was written to be run once. However,
      it could be that the webdriver disconnects while scraping ballotpedia.org, in which
      case, the user would need to adjust the script accordingly as to not re-scrape data.
    - The ballotpedia.org scraping script is very hacky. The website is very unstructured
      and I had to parse it in order (as a list) to get the information.

Run this script from the root directory of the project. To run this script, you will
likely need to change the user_agent and firefox_driver variables.

Dependences:
    - tqdm==4.65.0
        - https://tqdm.github.io/
    - yfinance
        - https://pypi.org/project/yfinance/
        - pip install yfinance --upgrade --no-cache-dir
    - pandas_datareader==0.10.0
        - https://pandas-datareader.readthedocs.io/en/latest/
    - requests==2.31.0
        -
        -
    - bs4==4.12.2
        - https://pypi.org/project/bs4/
"""
# ##############################################################################
# Set up workspace
# ##############################################################################

import os
import re
import yaml
import argparse

from time import time
from tqdm import tqdm

import yfinance as yf
from pandas_datareader import data as pdr

import numpy as np
import pandas as pd

import requests
from bs4 import BeautifulSoup

from utils import flatten_list, date_parser


yf.pdr_override()


def get_html(url):
    """Use website URL to get html using beautiful soup."""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup


def extract_text(child):
    """Extract text from Politician and Traded Issuer cells."""
    try:
        main_text = child.find('h3').text
        sub_text = child.find('span').text
        return main_text, sub_text
    except AttributeError:
        return [child.text]


def get_table_from_url(url, col_nms):
    """
    Extracts a table from a given URL and returns it as a pandas DataFrame.

    Parameters:
    - url (str): The URL from which the table is to be extracted.
    - col_nms (list of str): List of column names to be assigned to the DataFrame.

    Returns:
    - pd.DataFrame: DataFrame representation of the extracted table, with provided column names.

    Notes:
    - Assumes the first table on the page is the target table and the table is well-structured with a 'tbody' tag.
    """
    soup = get_html(url)
    table_html = soup.find('table').find('tbody')

    children = [x for x in table_html.children]
    table = [flatten_list([extract_text(x) for x in child][:-1]) for child in children]

    return pd.DataFrame(table, columns=col_nms)


def safe_load_capitoltrades(path, default=None):
    try:
        df = pd.read_csv(
            path,
            parse_dates=[
                'traded',
                'published'
                ],
            date_parser=date_parser,
            usecols=[
                'politician',
                'trade_issuer',
                'published',
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
        return df
    except FileNotFoundError as err:
        return default
        # print(f"Couldn't load {capitoltrades_fl} from output_path. Possibly misspecified output_path. Otherwise, if it doesn't exist, add 0 to steps.")
        # raise err


def scrape_capitoltrades(last_date_scraped=None):
    """
    Scrapes trade data from Capitol Trades for all available pages and returns the data as a pandas DataFrame.

    Returns:
    - pd.DataFrame: DataFrame with columns corresponding to the trade data from Capitol Trades.
    - list of int: List of page numbers for which scraping failed.

    Notes:
    - The base URL, column names, and the number of pages to scrape are hardcoded within the function.
    - If a table cannot be fetched or is empty for a particular page, the page number is appended to the 'failed' list.
    """
    base_url = 'https://www.capitoltrades.com/trades?per_page=96&page='
    col_nms = ['politician', 'party', 'trade_issuer', 'ticker', 'published', 'traded', 'filed_after', 'owner', 'type', 'size', 'price']
    n_pages = 419 # TODO dynamic

    df = pd.DataFrame()
    failed = []

    for page_num in tqdm(range(n_pages)):

        table = get_table_from_url(base_url + str(page_num+1), col_nms)

        if table.empty:
            failed.append(page_num)
        else:
            df = df.append(table)

        if last_date_scraped is not None:
            if np.any(df.published <= last_date_scraped):
                df = df[df.published > last_date_scraped]
                break

    return df, failed


def scrape_ballotpedia(politicians):
    """
    Scrapes committee membership data from Ballotpedia for all available politicians and returns the data as a dict.

    Returns:
    - dict: Dict with columns corresponding to the committee membership data from Ballotpedia.
    - list of string: List of politicians for which scraping failed.

    Notes:
    This section is a bit shitty. Ballotpedia.org is very unstructured so I need to parse it in order (as a list)
    to get the information.
    HTML structure:
    - Header: "Committee assignments"
    - Header: Date range
    - Paragraph: "<NAME> served on the following ... committees:"
    - Unordered list: Committees
    """
    base_url = 'https://ballotpedia.org/'

    committee_membership = {}
    failed = []

    for i, politician in enumerate(tqdm(politicians)):
        skip_line, check_next_line, committee_section = True, False, False
        key = None
        person_committee_membership = {}

        browser.get(base_url + politician.replace(' ', '_'))
        try:
            for line in browser.find_element(By.CLASS_NAME, 'mw-parser-output').text.splitlines():
                # Skip lines until we find "Committee assignments" header
                if line == 'Committee assignments':
                    skip_line = False

                if skip_line:
                    continue

                # Once we passed "Committee assignments" header we check headers for dates or date ranges.
                # Every time there is a new date header, we store the previously collected information to a dict.
                # We only have trading data for 2020, so we can omit earlier years.
                dates_in_line = re.match(r'.*(202[0-4])', line)
                if dates_in_line is not None:
                    check_next_line = True

                    if committee_section:
                        if len(values) == 0:
                            failed.append(politician)
                        else:
                            person_committee_membership[key] = values
                        committee_section = False

                    key = line
                    values = []
                    continue

                # If we found a date, the next line should introduce committee membership
                if check_next_line:
                    if 'committee' in line:
                        committee_section = True

                    check_next_line = False
                    continue

                # If the next line introduced committee membership, we should now be in the committee membership section
                if committee_section:
                    if (re.match(r'.*(20\d\d)', line) is not None) or (line == ''):
                        person_committee_membership[key] = values
                        break
                    values.append(line)

            committee_membership[politician] = person_committee_membership
        except NoSuchElementException: #TODO
            failed.append(politician)

    return committee_membership, failed


def collect_ticker_meta(tickers):
    """
    Collects meta information (sector and industry) for a list of tickers using Yahoo Finance.

    Parameters:
    - tickers (list of str): List of ticker symbols for which meta information is to be collected.

    Returns:
    - pd.DataFrame: DataFrame containing columns ['ticker', 'sector', 'industry'] with the fetched meta information.
    - list of str: List of ticker symbols for which meta information collection failed.

    Notes:
    - The function relies on Yahoo Finance's `Ticker` API.
    - If meta information cannot be fetched or is absent for a particular ticker, the ticker symbol is appended to the 'failed' list.
    """
    df_industry = pd.DataFrame()
    failed = []

    for ticker in tickers:
        tick = yf.Ticker(ticker)

        try:
            df_industry = df_industry.append(
                pd.DataFrame(
                    data=[[ticker, tick.info['sector'], tick.info['industry']]],
                    columns=['ticker', 'sector', 'industry']
                )
            )
        except: # TODO HTTPError:
            failed.append(ticker)

    return df_industry, failed


def collect_ticker_prices(tickers, data_path, start_date='2020-09-01', end_date='2023-08-31'):
    """
    Collects historical price data for a list of tickers using Yahoo Finance and saves them as CSV files.

    Parameters:
    - tickers (list of str): List of ticker symbols for which historical price data is to be collected.
    - data_path (str): Path to the directory where the CSV price data files are stored or will be saved.
    - start_date (str, optional): Start date in the format 'YYYY-MM-DD' from which to fetch data in case no CSV file exists. Defaults to '2020-09-01'.
    - end_date (str, optional): End date in the format 'YYYY-MM-DD' until which to fetch data. Defaults to '2023-08-31'.


    Returns:
    - list of str: List of ticker symbols for which price data collection succeeded.
    - list of str: List of ticker symbols for which price data collection failed.

    Notes:
    - If price data cannot be fetched or is empty for a particular ticker, the ticker symbol is appended to the 'failed_prices' list.
    - Data for each ticker is saved in a separate CSV file, named by the ticker symbol, within the specified directory.
    """
    success, failed = [], []

    for ticker in tickers:
        df = pdr.get_data_yahoo(ticker, start=start_date, end=end_date)
        if df.empty:
            failed.append(ticker)
        else:
            df.to_csv(os.path.join(data_path, f'{ticker}.csv'))
            success.append(ticker)

    return success, failed


def collect_and_append_ticker_prices(tickers, data_path, start_date='2020-09-01', end_date='2023-08-31'):
    """
    Collects historical price data for a list of tickers and appends new data to existing CSV files, or creates new CSV files if they don't exist.

    Parameters:
    - tickers (list of str): List of ticker symbols for which historical price data is to be collected.
    - data_path (str): Path to the directory where the CSV price data files are stored or will be saved.
    - start_date (str, optional): Start date in the format 'YYYY-MM-DD' from which to fetch data in case no CSV file exists. Defaults to '2020-09-01'.
    - end_date (str, optional): End date in the format 'YYYY-MM-DD' until which to fetch data. Defaults to '2023-08-31'.
    """
    for ticker in tickers:
        try:
            df = pd.read_csv(os.path.join(data_path, f'{ticker}.csv')) #TODO better date parse read
            df_new = pdr.get_data_yahoo(ticker, start=df.Date.max() + timedelta(days=1), end=end_date)
            df.append(df_new).to_csv(os.path.join(data_path, f'{ticker}.csv'))
        except FileNotFoundError:
            df_new = pdr.get_data_yahoo(ticker, start=start_date, end=end_date)
            if not df_new.empty:
                df_new.to_csv(os.path.join(data_path, f'{ticker}.csv'))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output_path",
        help="The path to the output file. Default: data",
        type=str,
        default="data"
        )

    parser.add_argument('--capitoltrades', action='store_true')
    parser.add_argument('--no-capitoltrades', dest='capitoltrades', action='store_false')
    parser.set_defaults(capitoltrades=True)

    parser.add_argument('--ballotpedia', action='store_true')
    parser.add_argument('--no-ballotpedia', dest='ballotpedia', action='store_false')
    parser.set_defaults(ballotpedia=True)

    parser.add_argument('--yahoofinance_meta', action='store_true')
    parser.add_argument('--no-yahoofinance_meta', dest='yahoofinance_meta', action='store_false')
    parser.set_defaults(yahoofinance_meta=True)

    parser.add_argument('--yahoofinance_price', action='store_true')
    parser.add_argument('--no-yahoofinance_price', dest='yahoofinance_price', action='store_false')
    parser.set_defaults(yahoofinance_price=True)

    parser.add_argument('--savefailed', action='store_true')
    parser.add_argument('--no-savefailed', dest='savefailed', action='store_false')
    parser.set_defaults(savefailed=False)

    parser.add_argument('--only_scrape_new', action='store_true')
    parser.add_argument('--no-only_scrape_new', dest='only_scrape_new', action='store_false')
    parser.set_defaults(only_scrape_new=False)

    args = parser.parse_args()

    ROOT = os.getcwd()
    PATH_DATA = os.path.join(ROOT, args.output_path.strip('./'))
    PATH_DATA_PRICES = os.path.join(PATH_DATA, 'yfinance_prices')

    try:
        os.makedirs(PATH_DATA_PRICES)
    except OSError:
        pass

    steps_count = args.capitoltrades + args.ballotpedia + args.yahoofinance_meta + args.yahoofinance_price

    assert steps_count != 0, 'Nothing to scrape, all scraping flags (capitoltrades, ballotpedia, yahoofinance_meta, yahoofinance_price) are False!'

    #browser = webdriver.Firefox(service=firefox_service, options=firefox_options)

    # -------------------------------------------------------------------------
    # Scrape capitoltrades.com trade data
    # -------------------------------------------------------------------------
    capitoltrades_fl = os.path.join(PATH_DATA, 'CapitolTrades_raw.csv')
    df = safe_load_capitoltrades(pd.DateFrame())
    last_date_scraped = None

    print('\n', '#' * 80)
    if args.capitoltrades:
        print('Scraping capitoltrades.com')

        if args.only_scrape_new:
            if not df.empty:
                last_date_scraped = df.published.max()
            else:
                print(f'{capitoltrades_fl} not found. Scraping all capitol trades.')

        t0 = time()
        df_new, failed = scrape_capitoltrades(last_date_scraped)
        t_total = time() - t0

        df.append(df_new).to_csv(capitoltrades_fl, index=False)

        print(f'time to scrape {df.shape[0]} trades: {t_total}')
        print(f'saved to {capitoltrades_fl}')
        print('\nFailed pages:')
        print(failed)
    else:
        print('loading CapitolTrades dataframe')
        if df.empty:
            print(f"Couldn't load {capitoltrades_fl} from output_path. Possibly misspecified output_path. Otherwise, if it doesn't exist, add 0 to steps.")
            raise FileNotFoundError

    # TODO
    start_date = earliest_capitol_trade
    end_date = today
    # -------------------------------------------------------------------------
    # Scrape committee membership from ballotpedia.org
    # -------------------------------------------------------------------------
    print('\n', '#' * 80)
    if args.ballotpedia and not args.only_scrape_new:
        print('Scraping ballotpedia.com')

        t0 = time()
        committee_membership, failed = scrape_ballotpedia(df.politician.unique())
        t_total = time() - t0

        with open(os.path.join(PATH_DATA, 'ballotpedia.yml'), 'w') as f_nm:
            yaml.dump(committee_membership, f_nm, default_flow_style=False)

        print(f'time to scrape {len(committee_membership)} politician committee memberships: {t_total}')
        print('\nFailed politicians:')
        print(failed)
    else:
        print('ballotpedia.com scraping skipped')

    # browser.close()
    # -------------------------------------------------------------------------
    # Scrape yahoo finance data for traded companies
    # -------------------------------------------------------------------------
    print('\n', '#' * 80)
    tickers = [x.split(':')[0] for x in df.ticker.dropna().unique()]
    if args.yahoofinance_meta and not args.only_scrape_new:
        print('Collecting meta data from finance.yahoo.com')
        t0 = time()
        df_industry, failed_companies = collect_ticker_meta(tickers)
        t_total = time() - t0

        industry_fl = os.path.join(PATH_DATA, 'xxx.csv') #TODO
        df_industry.to_csv(industry_fl)

        print(f'time to download {len(tickers)} company industries: {t_total}')
        print('\nFailed companies:')
        print(failed_companies)
    else:
        print('finance.yahoo.com meta data scraping skipped')

    if args.yahoofinance_price:
        print('Collecting price data from finance.yahoo.com')

        t0 = time()
        if args.only_scrape_new:
            collect_and_append_ticker_prices(tickers, PATH_DATA_PRICES, start_date, end_date)
        else:
            success_prices, failed_prices = collect_ticker_prices(tickers, PATH_DATA_PRICES, start_date, end_date)
            t_total = time() - t0

            #TODO save success_prices as snakemake output

            print(f'time to download {len(tickers)} company price datasets: {t_total}')
            print('\nFailed companies:')
            print(failed_prices)
    else:
        print('finance.yahoo.com price data scraping skipped')


if __name__ == "__main__":
    main()
