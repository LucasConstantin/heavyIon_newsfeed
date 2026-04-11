
## ###############################################################
## LOAD MODULES
## ###############################################################
import argparse
import datetime
import json
from pathlib import Path
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

import arxiv
import rfeed


## ###############################################################
## RSS FEED GENERATOR FUNCTIONS
## ###############################################################
def cast_date_to_string(input_date):
  if isinstance(input_date, datetime.datetime):
    return input_date.strftime("%Y-%m-%d")
  return str(input_date)


def createRSSFeed(list_article_dicts, config_name="ArxivSearch", lookback_days=None):
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
    abs_url = f"https://arxiv.org/abs/{dict_article['arxiv_id']}"

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
      guid        = rfeed.Guid(dict_article["arxiv_id"], isPermaLink=False)
    )
    items.append(item)
  
  lookback_suffix = f" ({lookback_days}d)" if lookback_days is not None else ""

  feed = rfeed.Feed(
    title       = f"arXiv Search Results - {config_name}{lookback_suffix}",
    link        = "https://arxiv.org",
    description = f"arXiv papers from search configuration: {config_name}{lookback_suffix}",
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


def createOPMLFile(config_name, rss_file_url, output_filepath, lookback_days=None):
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
  SubElement(head, 'title').text = f"arXiv Search - {config_name}{lookback_suffix}"
  SubElement(head, 'dateCreated').text = datetime.datetime.now().isoformat()
  SubElement(head, 'ownerName').text = "arXiv Scraper"
  
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
    return json.load(f)


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
        "arxiv_id": result.get_short_id(),
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


def export_feed_files(list_article_dicts, config_name, base_feed_url, lookback_days):
  feed = createRSSFeed(list_article_dicts, config_name, lookback_days=lookback_days)
  root_dir = Path(__file__).resolve().parent
  feeds_dir = root_dir / "feeds"
  feeds_dir.mkdir(parents=True, exist_ok=True)

  rss_filename = f"{config_name}_{lookback_days}d_feed.xml"
  rss_filepath = feeds_dir / rss_filename
  saveRSSFeed(feed, str(rss_filepath))

  opml_filename = f"{config_name}_{lookback_days}d_feed.opml"
  opml_filepath = feeds_dir / opml_filename
  rss_http_url = f"{base_feed_url.rstrip('/')}/{rss_filename}"
  createOPMLFile(config_name, rss_http_url, str(opml_filepath), lookback_days=lookback_days)

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
  list_article_dicts = search_arxiv(config, args.lookback_days, args.max_results)
  export_feed_files(list_article_dicts, args.config_name, args.base_feed_url, args.lookback_days)

  elapsed = datetime.datetime.now() - time_start
  print(f"Elapsed time: {elapsed.total_seconds():.2f} seconds.")


## ###############################################################
## PROGRAM ENTRY POINT
## ###############################################################
if __name__ == "__main__":
  main()