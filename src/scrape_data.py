"""Scrape data for InsideCapitolHill project for the Programming Practices
for Research in Economics course.

Author: Luca Gaegauf (lpupp) 09.2023

This script scrapes the following data:
    - Trades made by US congress members from capitoltrades.com,
    - Congress members' committee memberships from ballotpedia.org.

Furthermore, using the yahoo finance API, it downloads the following data:
    - Firm-industry pairs for firms traded by congress members from finance.yahoo.com,
    - Historical price data for firms traded by congress members from finance.yahoo.com.

Notes/confessions:
    - This script was not optimized for speed. It was written to be run once. However,
      it could be that the webdriver disconnects while scraping ballotpedia.org, in which
      case, the user would need to adjust the script accordingly as to not re-scrape data.
    - The ballotpedia.org scraping script is very hacky. The website is very unstructured
      and I had to parse it in order (as a list) to get the information.
    - Currently a lot of data scraping fails. We drop any trades with missing prices and
      any politicians with missing committees from our final analysis.

Run this script from the root directory of the project. To run this script, you will
likely need to change the user_agent and firefox_driver variables.

Using the --only_scrape_new, you can update already scraped CapitolTrades.com data and
price data with new data.

For reliable use, run the script with only one component activated at a time. I.e., set
the remaining flags:
    --no-capitoltrades
    --no-ballotpedia
    --no-yahoofinance_meta
    --no-yahoofinance_price

Dependences:
    - tqdm==4.65.0
        - https://tqdm.github.io/
    - yfinance
        - https://pypi.org/project/yfinance/
        - pip install yfinance --upgrade --no-cache-dir
    - pandas_datareader==0.10.0
        - https://pandas-datareader.readthedocs.io/en/latest/
    - selenium
        - https://selenium-python.readthedocs.io/installation.html
        - Installation can be cumbersome. I used the geckodriver for firefox. I do not have
          more advice to give you. My the odds be ever in your favor. 
    - bs4==4.12.2
        - https://pypi.org/project/bs4/

The script depends on Selenium to scrape data from CapitolTrades.com as the data table is
loaded dynamically. This package can be cumbersome to install. A bash script is included
to help with installation (bash_scripts/install_geckodriver.sh) but is not guaranteed to
work. If successful, pass the path to the geckodriver to the script using the
--path_to_geckodriver flag. Only firefox is supported, but Chrome should be easy to
implement for those with a Chrome webdriver.
"""
# ##############################################################################
# Set up workspace
# ##############################################################################

import os
import pathlib
import re
import yaml
import argparse

from time import time
from tqdm import tqdm

import yfinance as yf
from pandas_datareader import data as pdr

import numpy as np
import pandas as pd

from bs4 import BeautifulSoup
from datetime import timedelta

from utils import flatten_list, date_parser
# from utils import safe_get_user_agent

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options

from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# from webdriver_manager.chrome import ChromeDriverManager
# from webdriver_manager.firefox import GeckoDriverManager

yf.pdr_override()


def get_html(browser, url, delay=5):
    """Use website URL to get html using beautiful soup."""
    browser.get(url)

    try:
        element_present = EC.presence_of_element_located((By.TAG_NAME, 'table'))
        WebDriverWait(browser, delay).until(element_present)
    except TimeoutException:
        print("Timed out waiting for page to load")
        if 'no trades found' in BeautifulSoup(browser.page_source).text.lower():
            print('Terminating. Reached end of trades.')
            return None
        else:
            raise Exception('Scraping failed. Make sure you have reliable internet connection and try again.')

    content = browser.page_source
    soup = BeautifulSoup(content)
    return soup


def extract_text(child):
    """Extract text from Politician and Traded Issuer cells."""
    try:
        main_text = child.find('h3').text
        sub_text = child.find('span').text
        return main_text, sub_text
    except AttributeError:
        return [child.text]


def get_table_from_url(browser, url, col_nms, delay=5):
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
    soup = get_html(browser, url, delay)
    if soup is None:
        return None
    table_html = soup.find('table').find('tbody')

    children = [x for x in table_html.children]
    table = [flatten_list([extract_text(x) for x in child][:-1]) for child in children]

    return pd.DataFrame(table, columns=col_nms)


def safe_load_capitoltrades(path, default=None):
    """
    Safely load capitol trades data from a CSV file at the specified path.

    Parameters:
    - path (str): Path to the CSV file containing capitol trades data.
    - default (optional): Default value to return if a FileNotFoundError occurs. Default is None.

    Behavior:
    - Tries to load a CSV file using pandas' read_csv method with specific columns and datatypes.
    - Columns to be parsed as dates: 'traded' and 'published'.
    - Specific columns to be used are 'politician', 'trade_issuer', 'published', 'ticker', 'traded', 'owner', 'type', 'size', and 'price'.
    - Datatype specifications: 'owner', 'politician', and 'type' are set as category dtype.

    Returns:
    - DataFrame: A pandas DataFrame containing the loaded data if successful.
    - default: Specified default value or None if a FileNotFoundError occurs.
    """
    try:
        df = pd.read_csv(
            path,
            parse_dates=[
                'traded',
                'published'
                ],
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


def scrape_capitoltrades(browser, last_date_scraped=None):
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

    df = pd.DataFrame()
    failed = []

    pages_remaining = True
    page_num = 1
    while pages_remaining:
        if page_num % 10 == 0:
            print(page_num)

        table = get_table_from_url(browser, base_url + str(page_num), col_nms)
        if table is None:
            pages_remaining = False
            continue

        table.published = pd.to_datetime(date_parser(table.published))
        table.traded = pd.to_datetime(date_parser(table.traded))

        if table.empty:
            failed.append(page_num)
        else:
            df = df.append(table)

        if last_date_scraped is not None:
            if np.any(table.published <= last_date_scraped):
                df = df[df.published > last_date_scraped]
                break

        page_num += 1

    return df, failed


def scrape_ballotpedia(browser, politicians):
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



def safe_get_data_yahoo(ticker, start_date, end_date):
    """
    Fetch stock data from Yahoo Finance for a specific ticker and date range.

    Parameters:
    - ticker (str): Stock ticker symbol (e.g., "AAPL" for Apple Inc.)
    - start_date (str or datetime-like): Start date for the data fetch in the format "YYYY-MM-DD" or as a datetime object.
    - end_date (str or datetime-like): End date for the data fetch in the format "YYYY-MM-DD" or as a datetime object.

    Returns:
    - DataFrame: A pandas DataFrame containing the fetched stock data, or None if there's a KeyError.
    """
    try:
        df = pdr.get_data_yahoo(ticker, start=start_date, end=end_date)
        return df
    except KeyError:
        return None


def collect_ticker_prices(tickers, data_path, start_date='2020-09-01', end_date='2023-08-31', light=False):
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
    failed = []

    list_of_files = os.listdir(data_path)
    for ticker in tickers:
        if f'{ticker}.csv' in list_of_files:
            continue

        df = safe_get_data_yahoo(ticker, start_date, end_date)
        if df.empty:
            failed.append(ticker)
        else:
            if light:
                df = df[pd.to_datetime(df['Date']).dt.day_of_week == 4]
            df.to_csv(os.path.join(data_path, f'{ticker}.csv'))

    return failed


def collect_and_append_ticker_prices(tickers, data_path, start_date='2020-09-01', end_date='2023-08-31', light=False):
    """
    Collect stock data for a list of tickers and append or create .csv files at the specified path.

    Parameters:
    - tickers (list): List of stock ticker symbols (e.g., ["AAPL", "GOOG"]).
    - data_path (str): Path to the directory where the .csv files are located or will be saved.
    - start_date (str or datetime-like, optional): Start date for fetching data. Default is '2020-09-01'.
    - end_date (str or datetime-like, optional): End date for fetching data. Default is '2023-08-31'.
    - light (bool, optional): If set to True, only the data for the days of the week corresponding to Friday (day=4) will be fetched. Default is False.

    Behavior:
    - For each ticker:
      1. If a .csv file exists, it will read the file and append new data after the latest date in the file.
      2. If no .csv file exists for a ticker, it will fetch the data for the specified date range and create a new .csv file.
    """
    list_of_files = os.listdir(data_path)
    for ticker in tickers:
        if f'{ticker}.csv' in list_of_files:
            df = pd.read_csv(os.path.join(data_path, f'{ticker}.csv'))

            if 'Date' not in df.columns:
                continue
            else:
                df['Date'] = pd.to_datetime(df.Date)
                df.set_index('Date', inplace=True)

                _start_date = df.index.max() + timedelta(days=1)
                if _start_date.date() != end_date:
                    df_new = safe_get_data_yahoo(ticker, _start_date, end_date)
                    if df_new is None:
                        continue
                    elif not df_new.empty:
                        if light:
                            df_new = df_new[pd.to_datetime(df_new['Date']).dt.day_of_week == 4]
                        pd.concat([df, df_new]).to_csv(os.path.join(data_path, f'{ticker}.csv'))
        else:
            df_new = safe_get_data_yahoo(ticker, start_date, end_date)
            if df_new is None:
                continue
            elif not df_new.empty:
                if light:
                    df_new = df_new[pd.to_datetime(df_new['Date']).dt.day_of_week == 4]
                df_new.to_csv(os.path.join(data_path, f'{ticker}.csv'))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output_data_path",
        help="The path to the output file. Default: data",
        type=str,
        default="data"
        )

    parser.add_argument(
        "--capitoltrades_filename",
        help="The path to the output file. Default: data",
        type=str,
        default="CapitolTrades_raw"
        )

    parser.add_argument(
        "--ballotpedia_filename",
        help="The path to the output file. Default: data",
        type=str,
        default="ballotpedia"
        )
    
    parser.add_argument(
        "--company_metadata_filename",
        help="The path to the output file. Default: data",
        type=str,
        default="YahooFinance_industry"
        )

    parser.add_argument(
        "--prices_dirname",
        help="The path to the output file. Default: data",
        type=str,
        default="yfinance_prices"
        )

    parser.add_argument(
        "--path_to_geckodriver",
        help="The path to the output file. Default: data",
        type=str,
        default='/home/lpupp/Documents/drivers/geckodriver'
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

    # Paths
    ROOT = os.getcwd()
    if pathlib.PurePath(ROOT).name == 'src':
        raise Exception('Please run the script from the root directory.')

    PATH_DATA = os.path.join(ROOT, args.output_data_path.strip('./'))
    PATH_DATA_PRICES = os.path.join(PATH_DATA, args.prices_dirname)

    # File names
    capitoltrades_fl = os.path.join(PATH_DATA, f'{args.capitoltrades_filename}.csv')
    ballotpredia_fl = os.path.join(PATH_DATA, f'{args.ballotpedia_filename}.yaml')
    company_metadata_fl = os.path.join(PATH_DATA, f'{args.company_metadata_filename}.csv')

    try:
        os.makedirs(PATH_DATA_PRICES)
    except OSError:
        pass

    steps_count = args.capitoltrades + args.ballotpedia + args.yahoofinance_meta + args.yahoofinance_price

    assert steps_count != 0, 'Nothing to scrape, all scraping flags (capitoltrades, ballotpedia, yahoofinance_meta, yahoofinance_price) are False!'
    assert not args.savefailed, 'savefailed is not implemented yet!'

    # Selenium set up
    # user_agent = safe_get_user_agent(args.path_to_geckodriver)
            
    firefox_service = Service(args.path_to_geckodriver)
    firefox_options = Options()
    firefox_options.add_argument('--headless')
    # firefox_options.set_preference('general.useragent.override', args.user_agent)

    browser = webdriver.Firefox(service=firefox_service, options=firefox_options)

    # -------------------------------------------------------------------------
    # Scrape capitoltrades.com trade data
    # -------------------------------------------------------------------------
    df = safe_load_capitoltrades(capitoltrades_fl, pd.DataFrame())
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
        df_new, failed_pages = scrape_capitoltrades(browser, last_date_scraped)
        t_total = time() - t0

        df = df.append(df_new)
        df.to_csv(capitoltrades_fl, index=False)

        # TODO save failed_pages if args.savefailed
        print(f'time to scrape {df_new.shape[0]} trades: {t_total}')
        print(f'saved to {capitoltrades_fl}')
        print('\nFailed pages:')
        print(failed_pages)
    else:
        print('loading CapitolTrades dataframe')
        if df.empty:
            print(f"Couldn't load {capitoltrades_fl} from output_path. Possibly misspecified output_path. Otherwise, if it doesn't exist, add 0 to steps.")
            raise FileNotFoundError

    start_date = df.traded.min().date()
    end_date = pd.Timestamp.today().date()

    # -------------------------------------------------------------------------
    # Scrape committee membership from ballotpedia.org
    # -------------------------------------------------------------------------
    print('\n', '#' * 80)
    if args.ballotpedia and not args.only_scrape_new:
        print('Scraping ballotpedia.com')

        t0 = time()
        committee_membership, failed_politicians = scrape_ballotpedia(df.politician.unique())
        t_total = time() - t0

        with open(ballotpredia_fl, 'w') as f_nm:
            yaml.dump(committee_membership, f_nm, default_flow_style=False)

        # TODO save failed_politicians if args.savefailed
        print(f'time to scrape {len(committee_membership)} politician committee memberships: {t_total}')
        print('\nFailed politicians:')
        print(failed_politicians)
    else:
        print('ballotpedia.com scraping skipped')

    browser.close()

    # -------------------------------------------------------------------------
    # Scrape yahoo finance data for traded companies
    # -------------------------------------------------------------------------
    print('\n', '#' * 80)
    tickers = [x.split(':')[0].strip('$') for x in df.ticker.dropna().unique()]
    if args.yahoofinance_meta and not args.only_scrape_new:
        print('Collecting meta data from finance.yahoo.com')
        t0 = time()
        df_industry, failed_companies = collect_ticker_meta(tickers)
        t_total = time() - t0

        df_industry.to_csv(company_metadata_fl)

        # TODO save failed_companies if args.savefailed
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
            failed_prices = collect_ticker_prices(tickers, PATH_DATA_PRICES, start_date, end_date)
            t_total = time() - t0

            # TODO save failed_prices if args.savefailed
            print(f'time to download {len(tickers)} company price datasets: {t_total}')
            print('\nFailed companies:')
            print(failed_prices)
    else:
        print('finance.yahoo.com price data scraping skipped')


if __name__ == "__main__":
    main()
