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

Run this script from the root directory of the project. To run this script, you will
likely need to change the user_agent and firefox_driver variables. 

Dependences:
    - tqdm
        - https://tqdm.github.io/
        - pip install tqdm
    - yfinance
        - https://pypi.org/project/yfinance/
        - pip install yfinance --upgrade --no-cache-dir
    - pandas_datareader
        - https://pandas-datareader.readthedocs.io/en/latest/
        - pip install pandas-datareader
    - selenium
        - https://selenium-python.readthedocs.io/installation.html
        - Installation can be cumbersome. I used the geckodriver for firefox. I do not have
          more advice to give you. My the odds be ever in your favor. 
    - bs4
        - https://pypi.org/project/bs4/
        - pip install bs4

"""
# ##############################################################################
# Set up workspace
# ##############################################################################

import os
import re
import yaml

from time import time
from tqdm import tqdm

import yfinance as yf
from pandas_datareader import data as pdr

import pandas as pd

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options

from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup

yf.pdr_override()

# ##############################################################################
# Scrape data for capitoal hill insider trading long-short portfolio
# ##############################################################################

ROOT = os.getcwd()
PATH_DATA = os.path.join(ROOT, 'data')
PATH_DATA_PRICES = os.path.join(PATH_DATA, 'yfinance_prices')

try:
    os.makedirs(PATH_DATA_PRICES)
except OSError:
    pass

# Selenium set up
user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0'
firefox_driver = '/home/lpupp/Documents/drivers/geckodriver'
firefox_service = Service(firefox_driver)
firefox_options = Options()
firefox_options.add_argument('--headless')
firefox_options.set_preference('general.useragent.override', user_agent)

# ------------------------------------------------------------------------------
# Start browser
# ------------------------------------------------------------------------------

browser = webdriver.Firefox(service=firefox_service, options=firefox_options)


# ------------------------------------------------------------------------------
# Scrape capitoltrades.com trade data
# ------------------------------------------------------------------------------
def flatten_list(l):
    return [item for row in l for item in row]


def extract_text(child):
    """Extract text from Politician and Traded Issuer cells."""
    try:
        main_text = child.find('h3').text
        sub_text = child.find('span').text
        return main_text, sub_text
    except AttributeError:
        return [child.text]


def get_table_from_url(browser, extension, delay=5):
    browser.get(base_url + extension)

    try:
        element_present = EC.presence_of_element_located((By.TAG_NAME, 'table'))
        WebDriverWait(browser, delay).until(element_present)
    except TimeoutException:
        print("Timed out waiting for page to load")

    content = browser.page_source
    soup = BeautifulSoup(content)
    table_html = soup.find('table').find('tbody')

    children = [x for x in table_html.children]
    table = [flatten_list([extract_text(x) for x in child][:-1]) for child in children] 

    return pd.DataFrame(table, columns=col_nms)

print('\n', '#' * 80)
print('Scraping capitoltrades.com')

base_url = 'https://www.capitoltrades.com/trades?per_page=96&page='
col_nms = ['politician', 'party', 'trade_issuer', 'ticker', 'published', 'traded', 'filed_after', 'owner', 'type', 'size', 'price']
n_pages = 419

df = pd.DataFrame()
failed = []

t0 = time()
for page_num in tqdm(range(n_pages)):

    table = get_table_from_url(browser, str(page_num+1))

    if table.empty:
        failed.append(page_num)
    else:
        df = df.append(table)

t_total = time() - t0

df.to_csv(os.path.join(PATH_DATA, 'CapitolTrades_raw.csv'), index=False)

print(f'time to scrape {df.shape[0]} trades: {t_total}')
print('\nFailed pages:')
print(failed)


# ------------------------------------------------------------------------------
# Scrape committee membership from ballotpedia.org
# ------------------------------------------------------------------------------
print('\n', '#' * 80)
print('Scraping ballotpedia.com')

base_url = 'https://ballotpedia.org/'

committee_membership = {}
failed = []

t0 = time()
for i, politician in enumerate(tqdm(df.politician.unique())):
    # This section is a bit shitty. Ballotpedia.org is very unstructured so I need to parse
    # it in order (as a list) to get the information.
    # HTML structure:
    # - Header: "Committee assignments"
    # - Header: Date range
    # - Paragraph: "<NAME> served on the following ... committees:"
    # - Unordered list: Committees

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
    except NoSuchElementException:
        failed.append(politician)

t_total = time() - t0

with open(os.path.join(PATH_DATA, 'ballotpedia.yml'), 'w') as f_nm:
    yaml.dump(committee_membership, f_nm, default_flow_style=False)

print(f'time to scrape {len(committee_membership)} politician committee memberships: {t_total}')
print('\nFailed politicians:')
print(failed)


# ------------------------------------------------------------------------------
# Close browser
# ------------------------------------------------------------------------------
browser.close()


# ------------------------------------------------------------------------------
# Scrape yahoo finance data for traded companies
# ------------------------------------------------------------------------------
print('\n', '#' * 80)
print('Scraping finance.yahoo.com')

tickers = [x.split(':')[0] for x in df.ticker.dropna().unique()]

df_industry = pd.DataFrame()
failed_sector, failed_data = [], []

t0 = time()
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
        failed_sector.append(ticker)

    df = pdr.get_data_yahoo(ticker, start='2020-09-01', end='2023-08-31')
    if df.empty:
        failed_sector.append(ticker)
    else:
        df.to_csv(os.path.join(PATH_DATA_PRICES, f'{ticker}.csv'), index=False)

t_total = time() - t0

print(f'time to download {df_industry.shape[0]} company industries: {t_total}')
print('\nFailed companies:')
print(failed_data)

print(f'time to download {len(tickers)} company price datasets: {t_total}')
print('\nFailed companies:')
print(failed_sector)
