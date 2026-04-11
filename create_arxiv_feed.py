
## ###############################################################
## LOAD MODULES
## ###############################################################
import argparse
import datetime
import json
import re
from pathlib import Path
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

import arxiv
import rfeed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

## ###############################################################
## RSS FEED GENERATOR FUNCTIONS
## ###############################################################
def cast_date_to_string(input_date):
  if isinstance(input_date, datetime.datetime):
    return input_date.strftime("%Y-%m-%d")
  return str(input_date)


def createRSSFeed(list_article_dicts, config_name="ArxivSearch", lookback_days=None, source="arxiv"):
  """
  Create an RSS feed from a list of article dictionaries.
  
  Args:
    list_article_dicts: List of article dictionaries with keys: title, arxiv_id, 
                        url_pdf, date_updated, authors, abstract
    config_name: Name of the configuration/channel (default: "ArxivSearch")
  
  Returns:
    rfeed.Feed object
  """
  items = []
  
  for dict_article in list_article_dicts:
    abs_url = dict_article["url_abs"]

    # Create author string
    authors_str = ", ".join(dict_article.get("authors", []))
    
    # Convert date to datetime if needed
    pub_date = dict_article["date_updated"]
    if isinstance(pub_date, datetime.date) and not isinstance(pub_date, datetime.datetime):
      pub_date = datetime.datetime.combine(pub_date, datetime.time())
    
    # Create item description with abstract
    description = f"<p><strong>Authors:</strong> {authors_str}</p>"
    description += f"<p><strong>Updated:</strong> {cast_date_to_string(dict_article['date_updated'])}</p>"
    description += f"<p><strong>Category:</strong> {dict_article.get('category_primary', 'N/A')}</p>"
    description += f"<p><strong>Abstract:</strong></p><p>{dict_article.get('abstract', '')}</p>"
    
    item = rfeed.Item(
      title       = dict_article["title"],
      link        = abs_url,
      description = description,
      pubDate     = pub_date,
      guid        = rfeed.Guid(dict_article["paper_id"], isPermaLink=False)
    )
    items.append(item)
  
  lookback_suffix = f" ({lookback_days}d)" if lookback_days is not None else ""
  source_label = "bioRxiv" if source == "biorxiv" else "arXiv"
  source_link = "https://www.biorxiv.org" if source == "biorxiv" else "https://arxiv.org"

  feed = rfeed.Feed(
    title       = f"{source_label} Search Results - {config_name}{lookback_suffix}",
    link        = source_link,
    description = f"{source_label} papers from search configuration: {config_name}{lookback_suffix}",
    language    = "en-us",
    lastBuildDate = datetime.datetime.now(),
    items       = items
  )
  
  return feed


def saveRSSFeed(feed, output_filepath):
  """
  Save an RSS feed to an XML file.
  
  Args:
    feed: rfeed.Feed object
    output_filepath: Path where the RSS XML file should be saved
  """
  rss_str = feed.rss()
  with open(output_filepath, 'w', encoding='utf-8') as f:
    f.write(rss_str)
  print(f"RSS feed saved to: {output_filepath}")


def createOPMLFile(config_name, rss_file_url, output_filepath, lookback_days=None, source="arxiv"):
  """
  Create an OPML file that references an RSS feed.
  
  Args:
    config_name: Name of the configuration
    rss_file_url: URL or path to the RSS feed file
    output_filepath: Path where the OPML XML file should be saved
  """
  opml = Element('opml')
  opml.set('version', '2.0')
  
  head = SubElement(opml, 'head')
  lookback_suffix = f" ({lookback_days}d)" if lookback_days is not None else ""
  source_label = "bioRxiv" if source == "biorxiv" else "arXiv"
  SubElement(head, 'title').text = f"{source_label} Search - {config_name}{lookback_suffix}"
  SubElement(head, 'dateCreated').text = datetime.datetime.now().isoformat()
  SubElement(head, 'ownerName').text = f"{source_label} Scraper"
  
  body = SubElement(opml, 'body')
  feed_outline = SubElement(body, 'outline')
  feed_outline.set('type', 'rss')
  feed_outline.set('text', f"{config_name}{lookback_suffix} Feed")
  feed_outline.set('title', f"{config_name}{lookback_suffix} Feed")

  feed_outline.set('xmlUrl', rss_file_url)
  
  # Pretty print
  xml_str = minidom.parseString(tostring(opml)).toprettyxml(indent="  ")
  
  with open(output_filepath, 'w', encoding='utf-8') as f:
    f.write(xml_str)
  print(f"OPML file saved to: {output_filepath}")


## ###############################################################
def parse_arguments():
  parser = argparse.ArgumentParser(description="Search arXiv and export RSS/OPML for Zotero.")
  parser.add_argument("--search", default=True, action="store_true", help="Search arXiv and export feed files.")
  parser.add_argument("-c", "--config", dest="config_name", default="Heavy-Ion", help="Config name without .json")
  parser.add_argument("--lookback_days", type=int, default=10, help="Number of days to look back")
  parser.add_argument("--max_results", type=int, default=200, help="Max candidate arXiv results")
  parser.add_argument(
    "--base_feed_url",
    default="http://127.0.0.1:8000/feeds",
    help="Base URL used in OPML xmlUrl (e.g. http://127.0.0.1:8000/feeds)",
  )
  return parser.parse_args()


def load_config(config_name):
  config_path = Path(__file__).resolve().parent / f"{config_name}.json"
  if not config_path.exists():
    raise FileNotFoundError(f"Config not found: {config_path}")
  with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

  source = str(config.get("source", "arxiv")).strip().lower()
  if source not in {"arxiv", "biorxiv"}:
    raise ValueError("Config field 'source' must be either 'arxiv' or 'biorxiv'.")
  config["source"] = source

  biorxiv_engine = str(config.get("biorxiv_search_engine", "rxivist")).strip().lower()
  if biorxiv_engine not in {"biorxiv", "rxivist"}:
    raise ValueError("Config field 'biorxiv_search_engine' must be either 'biorxiv' or 'rxivist'.")
  config["biorxiv_search_engine"] = biorxiv_engine
  return config


def get_date_range(lookback_days):
  date_to = datetime.date.today()
  date_from = date_to - datetime.timedelta(days=lookback_days)
  return date_from, date_to


def build_arxiv_query(category, date_from, date_to):
  start = date_from.strftime("%Y%m%d") + "0000"
  end = date_to.strftime("%Y%m%d") + "2359"
  return f"cat:{category} AND submittedDate:[{start} TO {end}]"


def text_matches_keywords(text, include_groups, exclude_terms):
  text_low = text.lower()

  if include_groups:
    include_ok = False
    for group in include_groups:
      if isinstance(group, list):
        if all(term.lower() in text_low for term in group):
          include_ok = True
          break
      elif isinstance(group, str) and group.lower() in text_low:
        include_ok = True
        break
    if not include_ok:
      return False

  for term in exclude_terms:
    if isinstance(term, list):
      if all(t.lower() in text_low for t in term):
        return False
    elif isinstance(term, str) and term.lower() in text_low:
      return False

  return True


def parse_biorxiv_posted_date(posted):
  if not posted:
    return None

  text = str(posted).strip()
  text = text.removeprefix("Posted:").strip().rstrip(".")
  month_date_match = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4})", text)
  if month_date_match:
    text = month_date_match.group(1)

  for fmt in ("%B %d, %Y", "%b %d, %Y"):
    try:
      return datetime.datetime.strptime(text, fmt)
    except ValueError:
      continue
  return None


def search_arxiv(config, lookback_days, max_results):
  categories = config.get("list_categories", [])
  include_groups = config.get("list_keywords_include", [])
  exclude_terms = config.get("list_keywords_exclude", [])

  date_from, date_to = get_date_range(lookback_days)
  print("Searching for articles:")
  print(f"> from: {date_from}")
  print(f"> to:   {date_to}")
  print()

  client = arxiv.Client()
  article_by_id = {}

  for category in categories:
    query = build_arxiv_query(category, date_from, date_to)
    print(f"Searching category: {category}")
    search = arxiv.Search(
      query=query,
      max_results=max_results,
      sort_by=arxiv.SortCriterion.SubmittedDate,
      sort_order=arxiv.SortOrder.Descending,
    )

    for result in client.results(search):
      joined_text = f"{result.title}\n{result.summary}"
      if not text_matches_keywords(joined_text, include_groups, exclude_terms):
        continue

      article_by_id[result.get_short_id()] = {
        "title": result.title,
        "paper_id": result.get_short_id(),
        "url_abs": result.entry_id,
        "url_pdf": result.pdf_url,
        "date_updated": result.updated,
        "authors": [author.name for author in result.authors],
        "abstract": result.summary,
        "category_primary": result.primary_category,
      }

  list_article_dicts = sorted(
    article_by_id.values(),
    key=lambda d: d["date_updated"],
    reverse=True,
  )
  print(f"Found {len(list_article_dicts)} matching articles.")
  return list_article_dicts


def build_biorxiv_queries(include_groups):
  queries = []
  for group in include_groups:
    if isinstance(group, list):
      terms = [str(term).strip() for term in group if str(term).strip()]
      if terms:
        queries.append(" ".join(terms))
    elif isinstance(group, str) and group.strip():
      queries.append(group.strip())

  # Fallback broad query when no include groups are configured.
  return queries or ["physics"]


def build_requests_session():
  session = requests.Session()
  retry = Retry(
    total=5,
    connect=5,
    read=5,
    backoff_factor=1.0,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("GET",),
    raise_on_status=False,
  )
  adapter = HTTPAdapter(max_retries=retry)
  session.mount("https://", adapter)
  session.mount("http://", adapter)
  session.headers.update(
    {
      "User-Agent": "HeavyIonFeed/1.0 (constantin@itp.uni-frankfurt.de; research use)",
      "Accept": "application/json",
    }
  )
  return session


def fetch_biorxiv_collection(date_from, date_to, max_records=2000):
  session = build_requests_session()
  cursor = 0
  all_items = []

  while len(all_items) < max_records:
    url = f"https://api.biorxiv.org/details/biorxiv/{date_from}/{date_to}/{cursor}"
    try:
      response = session.get(url, timeout=(10, 45))
      response.raise_for_status()
      data = response.json()
    except requests.RequestException as err:
      print(f"bioRxiv API request failed at cursor={cursor}: {err}")
      break
    except ValueError as err:
      print(f"bioRxiv API returned invalid JSON at cursor={cursor}: {err}")
      break

    items = data.get("collection", [])
    if not items:
      break

    all_items.extend(items)
    total = int(data.get("messages", [{}])[0].get("total", len(all_items)))
    cursor += len(items)
    print(f"Fetched {min(len(all_items), max_records)}/{min(total, max_records)} bioRxiv records")

    if cursor >= total:
      break

  return all_items[:max_records]


def search_biorxiv(config, lookback_days, max_results):
  include_groups = config.get("list_keywords_include", [])
  exclude_terms = config.get("list_keywords_exclude", [])

  date_from, date_to = get_date_range(lookback_days)
  date_from_dt = datetime.datetime.combine(date_from, datetime.time.min)
  date_to_dt = datetime.datetime.combine(date_to, datetime.time.max)

  print("Searching for bioRxiv articles:")
  print(f"> from: {date_from}")
  print(f"> to:   {date_to}")
  print()

  api_fetch_cap = max(max_results * 20, 500)
  api_items = fetch_biorxiv_collection(date_from.isoformat(), date_to.isoformat(), max_records=api_fetch_cap)
  article_by_id = {}

  for paper in api_items:
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    try:
      posted_dt = datetime.datetime.strptime(str(paper.get("date", "")), "%Y-%m-%d")
    except ValueError:
      continue
    if posted_dt < date_from_dt or posted_dt > date_to_dt:
      continue

    joined_text = f"{title}\n{abstract}"
    if not text_matches_keywords(joined_text, include_groups, exclude_terms):
      continue

    doi = str(paper.get("doi", "")).strip()
    if not doi:
      continue
    paper_id = doi
    url_abs = f"https://www.biorxiv.org/content/{doi}v{paper.get('version', '1')}"

    article_by_id[paper_id] = {
      "title": title,
      "paper_id": paper_id,
      "url_abs": url_abs,
      "url_pdf": "",
      "date_updated": posted_dt,
      "authors": [a.strip() for a in str(paper.get("authors", "")).split(";") if a.strip()],
      "abstract": abstract,
      "category_primary": paper.get("category", "bioRxiv"),
    }

    if len(article_by_id) >= max_results:
      break

  list_article_dicts = sorted(
    article_by_id.values(),
    key=lambda d: d["date_updated"],
    reverse=True,
  )
  print(f"Found {len(list_article_dicts)} matching articles.")
  return list_article_dicts


def export_feed_files(list_article_dicts, config_name, base_feed_url, lookback_days, source):
  feed = createRSSFeed(list_article_dicts, config_name, lookback_days=lookback_days, source=source)
  root_dir = Path(__file__).resolve().parent
  feeds_dir = root_dir / "feeds"
  feeds_dir.mkdir(parents=True, exist_ok=True)

  rss_filename = f"{config_name}_{lookback_days}d_feed.xml"
  rss_filepath = feeds_dir / rss_filename
  saveRSSFeed(feed, str(rss_filepath))

  opml_filename = f"{config_name}_{lookback_days}d_feed.opml"
  opml_filepath = feeds_dir / opml_filename
  rss_http_url = f"{base_feed_url.rstrip('/')}/{rss_filename}"
  createOPMLFile(
    config_name,
    rss_http_url,
    str(opml_filepath),
    lookback_days=lookback_days,
    source=source,
  )

  print(f"Exported {len(list_article_dicts)} articles to RSS/OPML.")


## ###############################################################
## MAIN PROGRAM
## ###############################################################
def main():
  args = parse_arguments()
  if not args.search:
    raise SystemExit("Use --search to run arXiv scraping and feed export.")

  time_start = datetime.datetime.now()
  print(f"Program started at {time_start.strftime('%H:%M:%S')}")

  config = load_config(args.config_name)
  source = config.get("source", "arxiv")
  print(f"Selected source: {source}")
  if source == "biorxiv":
    list_article_dicts = search_biorxiv(config, args.lookback_days, args.max_results)
  else:
    list_article_dicts = search_arxiv(config, args.lookback_days, args.max_results)

  export_feed_files(
    list_article_dicts,
    args.config_name,
    args.base_feed_url,
    args.lookback_days,
    source,
  )

  elapsed = datetime.datetime.now() - time_start
  print(f"Elapsed time: {elapsed.total_seconds():.2f} seconds.")


## ###############################################################
## PROGRAM ENTRY POINT
## ###############################################################
if __name__ == "__main__":
  main()