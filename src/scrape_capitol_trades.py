"""Scrape data for InsideCapitolHill project for the Programming Practices
for Research in Economics course.

This script scrapes the following data:
    - Trades made by US congress members from capitoltrades.com,
    - Congress members' committee memberships from ballotpedia.org,
    - Firm-industry pairs for firms traded by congress members from finance.yahoo.com,
    - Historical price data for firms traded by congress members from finance.yahoo.com.

Notes/confessions:
    - This script was not optimized for speed. It was written to be run once.
    - The ballotpedia.org scraping script is very hacky. The website is very unstructured
      and I had to parse it in order (as a list) to get the information.
    - I downloaded the historical price data by automating pushing the "download" button
      on finance.yahoo.com. I'm sure there is an API I could have used, but since I was
      already working with selenium, I thought its quicker than learning the API syntax.
"""
# ##############################################################################
# Set up workspace
# ##############################################################################

import os
import re
import yaml

from time import time
from tqdm import tqdm

import pandas as pd

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options

from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup


# ##############################################################################
# Scrape data for capitoal hill insider trading long-short portfolio
# ##############################################################################

ROOT = '/home/lpupp/Documents/GitHub/InsideCapitolHill'
ROOT_DATA = os.path.join(ROOT, 'data')

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
    try:
        main_text = child.find('h3').text
        sub_text = child.find('span').text
        return main_text, sub_text
    except AttributeError:
        return [child.text]


def get_table_from_url(browser, extension, delay=5):
    browser.get(base_url + extension)
    # sleep(delay) # Bit hacky but WebDriverWait doesn't work:
    # WebDriverWait doesn't work because the page is "successfully loaded" before the
    # content of the table is loaded. That is, the table body is loaded, but content
    # isn't. If we wait for the table body, it will continue prematurely. I don't
    # know how to wait for the content...

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

df.to_csv(os.path.join(ROOT_DATA, 'CapitolTrades_raw.csv'), index=False)

print(f'time to scrape {df.shape[0]} trades: {t_total}')
print('\nFailed pages:')
print(failed)
# df = pd.read_csv(os.path.join(ROOT_DATA, 'CapitolTrades_raw.csv'))


# ------------------------------------------------------------------------------
# Scrape committee membership from ballotpedia.org
# ------------------------------------------------------------------------------
print('\n', '#' * 80)
print('Scraping ballotpedia.com')

base_url = 'https://ballotpedia.org/'

committee_membership = {}
failed = []

t0 = time()
for politician in tqdm(df.politician.unique()):
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

t_total = time() - t0

with open(os.path.join(ROOT_DATA, 'ballotpedia.yml'), 'w') as f_nm:
    yaml.dump(committee_membership, f_nm, default_flow_style=False)

print(f'time to scrape {len(committee_membership)} politician committee memberships: {t_total}')
print('\nFailed politicians:')
print(failed)


# ------------------------------------------------------------------------------
# Scrape yahoo finance data for traded companies
# ------------------------------------------------------------------------------
print('\n', '#' * 80)
print('Scraping finance.yahoo.com')

base_url = 'https://finance.yahoo.com/quote/{}/profile'
base_url_historical_data = 'https://finance.yahoo.com/quote/{}/history?period1=1598918400&period2=1693785600&interval=1d&filter=history&frequency=1d&includeAdjustedClose=false'

tickers = [x.split(':')[0] for x in df.ticker.dropna().unique()]
df_industry = pd.DataFrame()
failed_sector, failed_data = [], []

t0 = time()
for ticker in tqdm(tickers):
    browser.get(base_url.format(ticker))

    try:
        df_industry = df_industry.append(
            pd.DataFrame(
                data=[[ticker] + [x.split(': ')[-1] for x in browser.find_element(By.CSS_SELECTOR, "p[class='D(ib) Va(t)']").text.splitlines() if ('sector' in x.lower()) or  ('industry' in x.lower())]],
                columns=['ticker', 'sector', 'industry']
            )
        )
    except NoSuchElementException:
        failed_sector.append(ticker)

t_total = time() - t0

df_industry.to_csv(os.path.join(ROOT_DATA, 'YahooFinance_industry.csv'), index=False)

print(f'time to scrape {df_industry.shape[0]} company industries: {t_total}')
print('\nFailed companies:')
print(failed_sector)


t0 = time()
for ticker in tqdm(tickers):
    browser.get(base_url_historical_data.format(ticker))
    
    try:
        download_btn = browser.find_element(By.CSS_SELECTOR, "a[class='Fl(end) Mt(3px) Cur(p)']")
        download_btn.click()
    except NoSuchElementException:
        failed_data.append(ticker)

t_total = time() - t0

print(f'time to download {tickers.shape[0]} company price datasets: {t_total}')
print('\nFailed companies:')
print(failed_data)

# ------------------------------------------------------------------------------
# Close browser
# ------------------------------------------------------------------------------
browser.close()

