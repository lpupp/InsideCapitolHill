# Capitol Hill's Trading Performance: An Investigation

US members of Congress, under the Stop Trading on Congressional Knowledge (STOCK) Act, are required to declare their trades, shedding light on their financial activities. Some studies, like [Karadas (2017)](https://link.springer.com/article/10.1007/s12197-017-9384-z), show significant returns from congressional trades. This project probes whether politicians potentially exploit insider information for above-market returns.

## Key features:

1. **Trade-Committee Matching**: Links a Congress member's committee membership with the industry of a traded firm.
2. **Advanced Matching**: Uses a pretrained language model to connect committees and industries, ensuring a more comprehensive match than straightforward approaches.

## Datasets:

1. **Congress Trades**: 
   - Source: [CapitolTrades.com](https://www.capitoltrades.com/trades)
   - Tool: Used [`selenium`](https://selenium-python.readthedocs.io/installation.html) to scrape.

2. **Congress Committee Membership**: 
   - Source: [ballotpedia.org](ballotpedia.org)
   - Tool: Data scraped for each politician using `selenium`. (Note: `requests` package would suffice as alternative.)

3. **Firm's Industry and Sector Info**: 
   - Source: [finance.yahoo.com](finance.yahoo.com) 
   - Note: Data encompasses all firms from the capitol-trades dataset.

4. **Historical Price Data**:
   - Source: [finance.yahoo.com](finance.yahoo.com)
   - Purpose: Essential for portfolio construction and evaluation. 

Further details in the [scraping script](src/scrape_data.py).

## Dependencies and setup

Before running the project, ensure you have installed the dependencies by either cloning the environment ([found here](envs/env_pp4rs.yaml)) or installing them manually. To clone environment, run:
```bash
conda env create -f envs/env_pp4rs.yaml
```

Note however, the [scraping script](src/scrape_data.py) will not run without installing a webdriver. See next section for advice.

Should you with to run the notebook, make environment available for notebook by running:
```bash
conda activate env_pp4rs
conda install -c anaconda ipykernel
python -m ipykernel install --user --name=env_pp4rs
```

Otherwise, install the following dependencies manually:

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
    - *Note*: Installation might be tricky. I utilized geckodriver (v0.32.0) for Firefox. See [this bash script](src/setup/install_geckodriver.sh) that hopefully helps with installation. May the odds be ever in your favor!

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

### Installing geckodriver

`selenium` is needed to scrape the [CapitolTrades.com](https://www.capitoltrades.com/trades) as the standard `requests` package fails with the dynamic tables. 

There are bash scripts to install a geckodriver to run `selenium` with Firefox.
```bash
sh src/install_geckodriver.sh /path/to/geckodriver
```

To install Firefox (for Mac (with homebrew installed) and Linux OS):
```bash
sh src/install_firefox.sh
```

If this does not work. Please follow standard online `geckodriver` installation resources. Alternatively, a Chrome driver can be installed, however, small changes to [src/scrape_data.py](src/scrape_data.py) would have to be made.

## Data scraping

To scrape the necessary data, run the following command:

```bash
conda activate env_pp4rs
python src/scrape_data.py --path_to_geckodriver '/path/to/geckodriver'
```

### Data output directory structure:

- `CapitolTrades_raw.csv`: Trades executed by Congress members.
- `ballotpedia.yml`: Dictionary capturing politicians' committee membership.
- `yfinance_prices`: Folder with historical price data, each named '`<ticker>.csv`' for individual firms.
- `YahooFinance_industry.csv`: Industry and sector meta data for the firms.

## Analysis

Find main exploration and findings in [the notebook](src/analysis/capitol_hill_portfolio.ipynb) or through [nbviewer](https://nbviewer.org/github/lpupp/InsideCapitolHill/blob/main/src/analysis/capitol_hill_portfolio.ipynb).

## Real-time backtesting

To keep this project relevant, I've integrated the ability to fetch fresh data directly from [CapitolTrades.com](https://www.capitoltrades.com/trades) and [finance.yahoo.com](finance.yahoo.com) to ensures you're always copying the most recent Congressional trades. The performance of your long-short strategy can be evaluated in a web-cockpit (on GithHub Pages).

### Dependencies

We use the workflow manager `snakemake`, which handles the installation of the required dependencies into a local virtual environment. With this method, the only external dependencies are:

1. Install [anaconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) based on your operating system
2. Install [snakemake](https://snakemake.github.io/), ideally in its own separate conda virtual environment:
   ```bash
   conda create -c conda-forge -c bioconda -n snakemake snakemake
   ```
3. Install [Firefox](https://www.mozilla.org/en-US/firefox/new/) if not already installed. Try:
   ```bash
   sh src/bash_scripts/install_firefox.sh
   ```
   or follow online tutorials.

### Deployment

If you have the geckodriver pre-installed, replace `path/to/geckodriver` below. If not, kindly remove the relevant line.

```bash
cd /path/to/InsideCapitolHill
sed -i 's|../../drivers/geckodriver|path/to/geckodriver|g' Snakefile
conda activate snakemake
snakemake --cores 1 --use-conda --conda-frontend conda
```

### Output 

A cockpit to evaluate the current performance of your long-short portfolio built on the most recent data should load locally after completion. If not, run:
```bash
firefox .src/doc/index.html
```

There is a small unsolved bug that you are likely to encounter. Namely, since politicians have a 45-day grace period to report trades and since there may be weeks without new trades, it is likely that not every week has any open position. If there is not at least 1 long and 1 short position in the final week, the portfolio composition in the cockpit will not be displayed. This bug was not yet fixed. To see the output for a week where this bug is not encountered see [GitHub pages](https://lpupp.github.io/InsideCapitolHill) or run:
```bash
firefox https://lpupp.github.io/InsideCapitolHill
```