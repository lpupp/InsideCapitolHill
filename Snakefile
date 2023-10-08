rule outputs_all:
    input:
        backtest_performance = "./data/portfolios/wealth.csv",
        backtest_composition = "./data/portfolios/composition.csv",
        webpage_timestamp = "./src/doc/gh_publication_date_ddmmyy.txt"

rule install_geckodriver:
    output:
        driver_path = '../../drivers/geckodriver'
    shell:
        'sh src/bash_scripts/install_geckodriver.sh {output.driver_path}'

rule scrape_data:
    conda: "envs/env_pp4rs.yaml"
    input:
        driver_path = '../../drivers/geckodriver',
    output:
        capitoltrades_filename = "./data/CapitolTrades_raw.csv",
    shell:
        '''
        python src/scrape_data.py \
        --capitoltrades_filename {output.capitoltrades_filename} \
        --prices_dirname ./data/yfinance_prices \
        --path_to_geckodriver {input.driver_path} \
        --no-ballotpedia \
        --no-yahoofinance_meta \
        --only_scrape_new
        '''

rule backtest_portfolio:
    conda: "envs/env_pp4rs.yaml"
    input:
        capitoltrades_filename = "./data/CapitolTrades_raw.csv",
    output:
        backtest_performance = "./data/portfolios/wealth.csv",
        backtest_composition = "./data/portfolios/composition.csv",
    shell:
        '''
        python src/backtest_longshort.py \
        --capitoltrades_filename {input.capitoltrades_filename} \
        --prices_dirname ./data/yfinance_prices \
        --performance_filename {output.backtest_performance} \
        --composition_filename {output.backtest_composition}
        '''

rule launch_cockpit:
    input: 
        backtest_performance = "./data/portfolios/wealth.csv",
        backtest_composition = "./data/portfolios/composition.csv",
        webpage_index = "./src/doc/index.html",
    output:
        webpage_timestamp = "./src/doc/gh_publication_date_ddmmyy.txt"
    shell:
        '''
        sh src/bash_scripts/launch_cockpit.sh \
        {output.webpage_index} \
        {output.webpage_timestamp}
        '''
