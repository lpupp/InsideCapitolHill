"""Utils to be accessed from other scripts."""

import re
import string

import numpy as np
import pandas as pd
import argparse

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options


ranks = [
    'ranking member',
    'vice',
    'covice',
    'chair',
    'ex officio',
    'woman',
    'man',
]

hand_filter = [
    'AN ACT to amend 1961 PA 236',
    'Ballotpedia monitors legislation that',
    'Key votes',
    'MI HB4184 - Courts: district',
    'See also: Key votes',
    "The following table lists bills this",
]

word_list = [
    'united states house of representatives select committee on the',
    'joint committee on',
    'joint',
    'senate committee on',
    'senate committee',
    'senate',
    'house committee on',
    'house committee',
    'us house',
    'house ',
    'subcommittee for',
    'subcommittee on',
    'committee on',
    'subcommittee',
    'committee',
    'new york state assembly',
    'oregon state legislature',
    'oklahoma state'
]


def flatten_list(l):
    """
    Flattens a nested list (one level deep) into a single list.

    Parameters:
    - l (list of lists): A nested list to be flattened.

    Returns:
    - list: A flattened list containing all the items from the nested list.

    Example:
    >>> flatten_list([[1, 2], [3, 4], [5]])
    [1, 2, 3, 4, 5]
    """
    return [item for row in l for item in row]



def date_parser(string_list):
    """
    Parses a list of date strings in the format "Day MonthName Year"
    (e.g., "16 Jan 2021") and returns them in the format "Year Month Day"
    (e.g., "2018 01 16").

    Parameters:
    - string_list (list of str): List of date strings to be parsed.

    Returns:
    - list of str: A list of parsed date strings in the format "Year Month Day".

    Example:
    >>> date_parser(["16 Jan 2021"])
    ['2021 01 16']
    """
    date_today = pd.datetime.today()
    date_yesterday = date_today - pd.Timedelta(days=1)
    month_name = dict((k, v+1) for v, k in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']))
    month_ix = dict((k+1, v) for k, v in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']))

    def catch_today_yesterday(x):
        """
        x: date_string in the format 'Year Day MonthName.'
        """
        if 'today' in x.lower():
            return '  {0} {1} {2}'.format(date_today.year, date_today.day, month_ix[int(date_today.month)])
        elif 'yesterday' in x.lower():
            return '  {0} {1} {2}'.format(date_yesterday.year, date_yesterday.day, month_ix[int(date_yesterday.month)])
        else:
            return x

    def YYYYDDMM_to_YYYYMMDD(x):
        """
        x: date_string in the format 'Year Day MonthName.'
        """
        return f"{x.split(' ')[2]} {int(month_name[x.split(' ')[4]]):02d} {int(x.split(' ')[3]):02d}"

    return [YYYYDDMM_to_YYYYMMDD(catch_today_yesterday(x)) for x in string_list]


def compute_average_from_range(value):
    """
    Computes the average of a range given in string format. The function can also handle
    ranges with 'K' (indicating thousands) and 'M' (indicating millions).

    Parameters:
    - value (str): A string representation of a range (e.g., "10K–15K" or "1M–2M").

    Returns:
    - float: The average of the range.

    Example:
    >>> compute_average_from_range("10K–15K")
    12500.0
    >>> compute_average_from_range("1M–2M")
    1500000.0
    """
    series = [int(y) for y in value.strip().replace('K', '000').replace('M', '000000').split('–')]
    return np.mean(np.array(series))


def check_float_in_range(lb=0.0, ub=0.5):
    """
    Returns a function to be used as a type for argparse to check if a float value
    lies within a specified range (lb, ub].

    Parameters:
    - lb (float, optional): The lower bound of the range (exclusive). Defaults to 0.0.
    - ub (float, optional): The upper bound of the range (inclusive). Defaults to 0.5.

    Returns:
    - function: A function that takes a value as an argument and checks if it's a float
                within the specified range. Raises argparse.ArgumentTypeError if
                the value is not a float or is outside the range.

    Example:
    parser = argparse.ArgumentParser()
    parser.add_argument("--value", type=check_float_in_range(0.0, 1.0))
    """
    def _check_float_in_range(value):
        try:
            fl_value = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f'{value} is invalid float value')

        if (fl_value > ub) | (fl_value <= lb):
            raise argparse.ArgumentTypeError(f'{fl_value} is outside of range ({lb}, {ub}]')

        return fl_value
    return _check_float_in_range


def safe_get_user_agent(path_to_geckodriver):
    try:
        firefox_service = Service(path_to_geckodriver)
        firefox_options = Options()
        firefox_options.add_argument('--headless')
        browser = webdriver.Firefox(service=firefox_service, options=firefox_options)
        browser.get("https://www.seleniumhq.org/download/")
        user_agent = browser.execute_script("return navigator.userAgent")
        browser.close()
        return user_agent
    except:
        return None
            

def clean_committees(committees):
    """
    Cleans and preprocesses a list of committee names.

    This function performs several cleaning operations:
    - Removes any committee names that contain words from a predefined filter (`hand_filter`).
    - Removes any content within brackets.
    - Converts names to lowercase and removes punctuation.
    - Removes or replaces certain ranks and words based on predefined lists (`ranks` and `word_list`).
    - Applies several specific string replacements for common errors or patterns.
    - Strips any leading or trailing white spaces from each committee name.
    - Filters out names that are shorter than 2 characters.
    - Returns a set of unique committee names.

    Parameters:
    - committees (list of str): A list containing committee names to be cleaned.

    Returns:
    - list of str: A list of cleaned and unique committee names.

    Note:
    - This function relies on several predefined global variables (e.g., `hand_filter`, `ranks`, and `word_list`)
      which should be available in the function's scope.
    - Ensure all necessary global variables are initialized and updated as required.
    """
    for flt in hand_filter:
        committees = [x for x in committees if flt not in x]

    committees = [re.sub("[\(\[].*?[\)\]]", '',  x).lower().translate(str.maketrans('', '', string.punctuation)) for x in committees]

    for rank in ranks:
        committees = [x.replace(rank, '') for x in committees]

    for wrd in word_list:
        committees = [x.replace(wrd, '') for x in committees]

    #   Fixes
    committees = [x.replace('hu ', 'human') for x in committees]
    committees = [x.replace(' agement', ' management') for x in committees]
    committees = [x.replace(' ufacturing', ' manufacturing') for x in committees]
    committees = [x.replace(' sers', ' services') for x in committees]
    committees = [x.replace(' humansers', ' humanservices') for x in committees]
    committees = [x.replace('  ', ' ') for x in committees]

    committees = [x.strip() for x in committees]
    committees = [x for x in committees if len(x) > 1]
    try:
        committees.remove('')
    except ValueError:
        pass

    return list(set(committees))


def get_committee_list(df, committee_membership):
    """
    Retrieves a list of committees associated with each politician for a specific trade year.

    Parameters:
    - df (pandas.DataFrame): A DataFrame containing 'politician' and 'trade_year' columns.
    - committee_membership (dict): A dictionary where keys are politician names and values are dictionaries
                                  mapping years/periods to a list of associated committees.

    Returns:
    - pandas.DataFrame: The input DataFrame augmented with a 'committees' column containing lists of committees
                        associated with each politician for the given trade year. If no committee data is available
                        for a given year, the value is set as NaN.

    Notes:
    - The function uses an auxiliary function `clean_committees` which should preprocess/clean the committee names.
    """
    df_tmp = df[['politician', 'trade_year']].drop_duplicates().copy()
    membership = []
    for politician, trade_year in df_tmp.values:
        politician_committees = committee_membership.get(politician, {})
        if politician_committees == {}:
            membership.append(np.nan)
            continue

        relevant_key = [k for k in politician_committees.keys() if str(trade_year) in k]
        if len(relevant_key) == 0:
            membership.append(np.nan)
            continue

        membership.append(clean_committees(politician_committees[relevant_key[0]]))

    df_tmp['committees'] = membership
    return df_tmp


def encode_committees(df, model):
    """
    Encodes the 'committees' column values of a DataFrame using a given model.

    Parameters:
    - df (pandas.DataFrame): A DataFrame containing a 'committees' column with lists of committee names to be encoded.
    - model: A pretrained model capable of encoding text (e.g., sentence transformer model).

    Returns:
    - pandas.DataFrame: The input DataFrame augmented with a new 'encoded_committees' column containing the encoded values.
    """
    encoded_committees = []
    for committee in df['committees'].values:
        encoded_committees.append([model.encode(x) for x in committee])

    df['encoded_committees'] = encoded_committees
    return df
