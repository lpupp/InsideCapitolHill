# Capitol Hill's Trading Performance: An Investigation

US members of Congress, under the Stop Trading on Congressional Knowledge (STOCK) Act, are required to declare their trades, shedding light on their financial activities. Some studies, like [Karadas (2017)](https://link.springer.com/article/10.1007/s12197-017-9384-z), show significant returns from congressional trades. This project probes whether politicians potentially exploit insider information for above-market returns.

## Key Features:

1. **Trade-Committee Matching**: Links a Congress member's committee membership with the industry of a traded firm.
2. **Advanced Matching**: Uses a pretrained language model to connect committees and industries, ensuring a more comprehensive match than straightforward approaches.

## Datasets:

1. **Congress Trades**: 
   - Source: [CapitolTrades.com](https://www.capitoltrades.com/trades)
   - Extraction: Used [`selenium`](https://selenium-python.readthedocs.io/installation.html) to scrape.

2. **Congress Committee Membership**: 
   - Source: [ballotpedia.org](ballotpedia.org)
   - Extraction: Data scraped for each politician using `selenium`.

3. **Firm's Industry and Sector Info**: 
   - Source: [finance.yahoo.com](finance.yahoo.com) 
   - Note: Data encompasses all firms from the capitol-trades dataset.

4. **Historical Price Data**:
   - Source: [finance.yahoo.com](finance.yahoo.com)
   - Purpose: Essential for portfolio construction and evaluation. 

Further details in [the scraping script](src/scrape_data.py).

## Dependencies and Setup

Before running the project, ensure you have the following dependencies installed:

1. **tqdm**
    - Version: 4.62.1
    - [https://tqdm.github.io/](https://tqdm.github.io/)
    ```bash
    pip install tqdm
    ```

2. **yfinance**
    - Version: 0.2.28
    - [https://pypi.org/project/yfinance/](https://pypi.org/project/yfinance/)
    ```bash
    pip install yfinance --upgrade --no-cache-dir
    ```

3. **pandas_datareader**
    - Version: 0.10.0
    - [https://pandas-datareader.readthedocs.io/en/latest/](https://pandas-datareader.readthedocs.io/en/latest/)
    ```bash
    pip install pandas-datareader
    ```

4. **selenium**
    - Version: 4.7.0
    - [https://selenium-python.readthedocs.io/installation.html](https://selenium-python.readthedocs.io/installation.html)
    - *Note*: Installation might be tricky. I utilized geckodriver (v0.32.0) for Firefox. May the odds be ever in your favor with its setup!

5. **beautifulsoup4**
    - Version: 4.12.2
    - [https://pypi.org/project/bs4/](https://pypi.org/project/bs4/)
    ```bash
    pip install bs4
    ```

6. **sentence_transformers**
    - Version: 2.2.2
    - [https://www.sbert.net/](https://www.sbert.net/)
    ```bash
    pip install sentence-transformers
    ```

7. **scikit-learn**
    - Version: 1.0.2
    - [https://scikit-learn.org/stable/](https://scikit-learn.org/stable/)
    ```bash
    pip install scikit-learn
    ```

Dependencies included in requirements.txt (`selenium` not included).
```bash
pip install -r requirements.txt
```

## Data Extraction

To scrape the necessary data, run the following command:

```bash
python src/scrape_data.py
```

However, given the complexities in setting up selenium, the scraped data has been provided in the `data` directory. *Note: This pre-scraped data will be removed in approx. 2 weeks.*

### Data Directory Structure:

- `CapitolTrades_raw.csv`: Trades executed by Congress members.
- `ballotpedia.yml`: Dictionary capturing politicians' committee membership.
- `yfinance_prices`: Folder with historical price data, each named '`<ticker>.csv`' for individual firms.
- `YahooFinance_industry.csv`: Industry and sector meta data for the firms.

## Analysis

Find main exploration and findings in [the notebook](src/capitol_hill_portfolio.ipynb) or through [nbviewer](https://nbviewer.org/github/lpupp/InsideCapitolHill/blob/main/src/capitol_hill_portfolio.ipynb).
