set -e

GITHUB_USERNAME=$1
REPO_NAME=$2
WEBPAGE_INDEX=$3
BACKTEST_PERF_DATA=$4
BACKTEST_COMP_DATA=$5
OUTPUT_PATH=$6

WEBPAGE_DIR=$(dirname $WEBPAGE_INDEX)
BACKTEST_DIR=$(dirname $BACKTEST_PERF_DATA)
GH_PAGES_URL="https://$GITHUB_USERNAME.github.io/$REPO_NAME"

# remove the directory if it exists and start from scratch
rm -rf ./dist
mkdir dist
mkdir dist/data

# copy everything to new repo
cp -r $WEBPAGE_DIR/* dist -u
cp -r $BACKTEST_DIR/*.csv dist/data -u
cd dist

# but for this to work, the relative paths in the html need to change because dist is root
sed -i 's|../../data/portfolios/|data/|g' js/index.js

# publish new github repo
git init
git remote add origin ..
git checkout -b gh-pages
git add .
git commit -m "Add dist directory content for GitHub Pages"
git push origin gh-pages

# go back and delete everything
# (this is optional, you can also keep your folder locally)
# (in you do so )
cd ..
rm -rf ./dist 

# create a timestamped textfile telling us when the latest publication happened
date +"%m/%d/%Y %H:%M:%S $HOSTNAME" > "$OUTPUT_PATH"

# open webpage
python -m webbrowser $GH_PAGES_URL

echo "The page may not display! Go to https://github.com/$GITHUB_USERNAME/$REPO_NAME/settings/pages and select gh-pages branch. Wait for webpage to build and then reload."