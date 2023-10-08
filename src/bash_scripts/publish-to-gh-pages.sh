set -e

GITHUB_USERNAME=$1
REPO_NAME=$2
WEBPAGE_DIR=$3
BACKTEST_DIR="$4/$5"
BACKTEST_PERF_DATA=$6
BACKTEST_COMP_DATA=$7
GH_PAGES_URL="https://$GITHUB_USERNAME.github.io/$REPO_NAME"
OUTPUT_PATH=$8

# remove the directory if it exists and start from scratch
rm -rf ./dist
mkdir dist
mkdir dist/data

# copy everything to new repo
BACKTEST_DIR='data/portfolios'
cp -r $WEBPAGE_DIR/* dist -u
cp -r $BACKTEST_DIR/*.csv dist/data -u
cd dist

# copy index.html
# but for this to work, the relative paths in the html need to change because dist is root
sed -i 's|../../data/portfolios/|data/|g' js/index.js

# publish new github repo
git init --initial-branch=main
git add -A
git commit -m 'Deploy to GH pages'

git push -f git@github.com:$GITHUB_USERNAME/$REPO_NAME.git main:gh-pages

# go back and delete everything
# (this is optional, you can also keep your folder locally)
# (in you do so )
cd ..
rm -rf ./dist 

# create a timestamped textfile telling us when the latest publication happened
date +"%m/%d/%Y %H:%M:%S $HOSTNAME" > "./src/doc/gh_publication_date_ddmmyy.txt"

# open webpage
python -m webbrowser $GH_PAGES_URL
