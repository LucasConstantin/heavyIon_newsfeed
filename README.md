# arXivScraper

**arXivScraper** is a lightweight paper management tool designed to help you find, filter, and rank new arXiv papers based on your research interests. It offers flexible search and ranking criteria, as well as seamless integration with Obsidian.

![Logo](./logo.jpg)

---

## Installation

Clone the repository and install the dependencies.

```
git clone https://github.com/yourusername/arXivScraper.git
cd arXivScraper
OPTIONAL: Create virtual environment first
pip install -r requirements.txt
```

## Usage

1. Scrape arXiv for papers and create an .xml file with main command: ```python create_arxiv_feed.py <options>```
2. Specify options to create different feeds: ```-c <JSON filename> --lookback_days <number of days>```
3. Link the feed to Zotero (or any other newsfeed reader). For Zotero go to: ```File -> New Bibliography -> New Feed -> From OPML...``` and select the .OPML file
4. Update the feed: Zotero needs an https server. 
    - Zotero needs an https server: Host your own using ```python3 -m http.server 8000 --bind 127.0.0.1```
    - Refresh feed inside Zotero

## Configuration files

Program runtime settings: Customise runtime settings in `./configs/settings.yaml`
JSON Profile Configurations: Define search criteria in JSON files located in `./configs/*.json`
User Profile for AI-ranking: Define a ranking profile in `./configs/user_profile.txt`
For detailed configuration instructions, see: `./docs/json-profiles.pdf`
Local LLM Support: see details in `./docs/bla.pdf`


