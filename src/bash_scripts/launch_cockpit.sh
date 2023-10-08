set -e

WEBPAGE_INDEX=$1
OUTPUT_PATH=$2

# open webpage
python -m webbrowser "./src/doc/index.html"

date +"%m/%d/%Y %H:%M:%S $HOSTNAME" > "$OUTPUT_PATH"

echo "cockpit currently out-of-order due to CORS restriction. Tried building a desktop app, but it didn't work. Push ./src/doc to github and run pages from respective repo for visualization... Sorry!"