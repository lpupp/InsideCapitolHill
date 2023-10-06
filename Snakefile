rule outputs_all:
    input:
        data_path = "data",
        backtest_dir = "portfolios",
        backtest_performance = "wealth",
        backtest_composition = "composition",
        webpage_timestamp = "src/doc/gh_publication_date_ddmmyy.txt"

rule install_geckodriver:
    output:
        driver_path = '../../drivers/geckodriver'
    shell:
        'sh src/bash_scripts/install_geckodriver.sh {output.driver_path}'

rule install_firefox:
    output:
        firefox_installed = 'True'
    shell:
        'sh src/bash_scripts/install_firefox.sh'

rule scrape_data:
    conda: "envs/env_pp4rs.yaml"
    input:
        driver_path = '../../drivers/geckodriver',
        firefox_installed = 'True'
    output:
        data_path = "data",
        capitoltrades_filename = "CapitolTrades_raw",
        prices_dirname = "yfinance_prices"
    shell:
        '''
        python src/scrape_data.py \
        --output_data_path {output.data_path} \
        --capitoltrades_filename {output.capitoltrades_filename} \
        --prices_dirname {output.prices_dirname} \
        --path_to_geckodriver {input.driver_path} \
        --no-ballotpedia \
        --no-yahoofinance_meta \
        --only_scrape_new
        '''

rule backtest_portfolio:
    conda: "envs/env_pp4rs.yaml"
    input:
        data_path = "data",
        capitoltrades_filename = "CapitolTrades_raw",
        prices_dirname = "yfinance_prices",
    output:
        backtest_dir = "portfolios",
        backtest_performance = "wealth",
        backtest_composition = "composition",
        backtest_plot_performance = "wealth_plot",
        backtest_plot_composition = "composition_plot"
    shell:
        '''
        python src/backtest_strategy.py \
        --data_path {input.data_path} \
        --capitoltrades_filename {input.capitoltrades_filename} \
        --prices_dirname {input.prices_dirname} \
        --save_dir {output.backtest_dir} \
        --performance_filename {output.backtest_performance} \
        --composition_filename {output.backtest_composition} \
        --plot_performance_filename {output.backtest_plot_performance} \
        --plot_composition_filename {output.backtest_plot_composition}
        '''

rule publish_gh_page:
    input: 
        data_path = "data",
        backtest_dir = "portfolios",
        backtest_performance = "wealth",
        backtest_composition = "composition"
    output:
        webpage_directory = "src/doc",
        webpage_index = "index.html",
        github_username = 'github_username_placeholder',
        repo_fork_name = 'repo_placeholder',
        webpage_timestamp = "src/doc/gh_publication_date_ddmmyy.txt"
    shell:
        '''
        sh src/bash_scripts/publish-to-gh-pages.sh \
        {output.github_username} \
        {output.repo_fork_name} \
        {output.webpage_directory} \
        {input.data_path} \
        {input.backtest_dir} \
        {input.backtest_performance} \
        {input.backtest_composition} \
        {output.webpage_timestamp}
        '''
