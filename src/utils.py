"""Utils to be accessed from other scripts."""

"""TODO docstrings"""

import re
import string

import numpy as np

def flatten_list(l):
    return [item for row in l for item in row]


def compute_average_from_range(value):
    series = [int(y) for y in value.strip().replace('K', '000').replace('M', '000000').split('–')]
    return np.mean(np.array(series))


def get_committee_list(df, committee_membership):
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
    encoded_committees = []
    for committee in df['committees'].values:
        encoded_committees.append([model.encode(x) for x in committee])

    df['encoded_committees'] = encoded_committees
    return df


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

def clean_committees(committees):
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