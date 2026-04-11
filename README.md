# arXiv Heavy-Ion Newsfeed

Minimal arXiv scraper that:
1. Searches arXiv using keyword filters from a JSON config.
2. Exports an RSS feed XML file.
3. Exports an OPML file that points to the RSS URL (for Zotero and other feed readers).

## Installation

```bash
git clone https://github.com/LucasConstantin/zotero_heavyIon_newsfeed.git
cd zotero_heavyIon_newsfeed
python -m pip install -r requirements.txt
```

Optional virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configuration

The scraper reads a config JSON in the repository root.

Default config name:
- `Heavy-Ion.json`

Config fields used:
- `source`: data source, either `arxiv` or `biorxiv` (default `arxiv`)
- `biorxiv_search_engine`: `rxivist` (recommended default) or `biorxiv`
- `list_categories`: arXiv categories to query (for example `nucl-th`)
- `list_keywords_include`: OR-of-groups include filter
- `list_keywords_exclude`: exclude filter

Notes:
- When `source` is `arxiv`, `list_categories` is used.
- When `source` is `biorxiv`, keyword groups are converted into text queries via `biorxiv_retriever`.

## Usage

Run search and export:

```bash
python create_arxiv_feed.py --search -c Heavy-Ion --lookback_days 10
```

Daily one-command workflow (generate feeds, then start local server):

```bash
./refresh_zotero_feed.sh
```

By default, this script refreshes all existing feed targets already present in `feeds/`
(matching `*_Xd_feed.xml`).

Optional overrides:

```bash
CONFIG=Heavy-Ion LOOKBACK_DAYS=30 MAX_RESULTS=400 PORT=8000 ./refresh_zotero_feed.sh
```

Override behavior note:
- If no matching feed files are found in `feeds/`, it falls back to `CONFIG` + `LOOKBACK_DAYS`.

Useful options:
- `--search`: run scraping/export flow
- `-c, --config`: config name without `.json`
- `--lookback_days`: date window size in days
- `--max_results`: max arXiv candidates per category before keyword filtering
- `--base_feed_url`: base URL used inside OPML `xmlUrl`

Example:

```bash
python create_arxiv_feed.py --search -c Heavy-Ion --lookback_days 30 --base_feed_url http://127.0.0.1:8000/feeds
```

## Output Files

Files are written to `feeds/` and include lookback days in their names:
- `feeds/<config>_<lookback>d_feed.xml`
- `feeds/<config>_<lookback>d_feed.opml`

For example:
- `feeds/Heavy-Ion_10d_feed.xml`
- `feeds/Heavy-Ion_10d_feed.opml`

## Zotero Setup

Zotero rejects `file://` feed URLs, so serve the feed over localhost HTTP.

1. Start a local server from the repository root:

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

2. Generate feeds with:

```bash
python create_arxiv_feed.py --search -c Heavy-Ion --lookback_days 10 --base_feed_url http://127.0.0.1:8000/feeds

```

3. In Zotero, import the generated OPML from `feeds/`.

4. Keep the local server running when refreshing feeds.
