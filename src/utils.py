"""Utils to be accessed from other scripts."""

import re
import string

import numpy as np

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
