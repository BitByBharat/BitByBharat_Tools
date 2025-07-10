import os
import json
import requests
from dotenv import load_dotenv
from notion_client import Client
from datetime import datetime
import logging
from keywords_config import CATEGORY_KEYWORDS
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

load_dotenv()

# Setup logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_path = os.path.join(LOG_DIR, "content_radar.log")
summary_path = os.path.join(LOG_DIR, "notion_summary.json")

logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s - %(message)s")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID_CONTENT_IDEAS")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

notion = Client(auth=NOTION_TOKEN)

def deduplicate_articles(articles):
    seen_titles = set()
    unique_articles = []
    for article in articles:
        title = article["title"]
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_articles.append(article)
    return unique_articles

def article_exists_in_notion(title):
    try:
        response = notion.databases.query(
            **{
                "database_id": NOTION_DB_ID,
                "filter": {
                    "property": "Content Topic Idea",
                    "title": {"equals": title}
                }
            }
        )
        return len(response.get("results", [])) > 0
    except Exception as e:
        logging.error(f"Error checking for duplicate in Notion: {e}")
        return False

def fetch_articles(category_keywords, max_articles=5, region=None):
    all_articles = []
    headers = {"Authorization": NEWS_API_KEY}

    for keyword in category_keywords:
        url = f"https://newsapi.org/v2/everything?q={keyword}&sortBy=publishedAt&pageSize={max_articles}&language=en&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            logging.info(f"✅ NewsAPI success for keyword: {keyword}")
            articles = response.json().get("articles", [])
            for art in articles:
                all_articles.append({
                    "title": art.get("title"),
                    "url": art.get("url"),
                    "publishedAt": art.get("publishedAt"),
                    "source": art.get("source", {}).get("name")
                })
        elif response.status_code == 429:
            logging.warning("⏳ Too Many Requests from NewsAPI")
        else:
            logging.error(f"❌ NewsAPI failed ({response.status_code}) for keyword: {keyword}")

    return deduplicate_articles(all_articles)

def push_to_notion(article, category):
    try:
        date_obj = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")).date()
        notion.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties={
                "Content Topic Idea": {"title": [{"text": {"content": article["title"]}}]},
                "Content Category": {"select": {"name": category}},
                "Angle": {"multi_select": [{"name": "Industry Trend"}]},
                "Status": {"status": {"name": "Idea"}},
                "Date": {"date": {"start": str(date_obj)}},
                "Remarks": {"rich_text": [{"text": {"content": article["url"]}}]}
            }
        )
        logging.info(f"✅ Pushed to Notion: {article['title']}")
        return True
    except Exception as e:
        logging.error(f"❌ Failed to push: {article['title']} | Error: {e}")
        return False

def write_summary(category, count):
    summary = {}
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            summary = json.load(f)

    summary[category] = {
        "articles_pushed": count,
        "last_updated": str(datetime.now())
    }

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

def fetch_and_push_articles(category, region=None):
    keywords = CATEGORY_KEYWORDS.get(category)
    if not keywords:
        logging.error(f"❌ Invalid category: {category}")
        return

    logging.info(f"\n📍 Starting fetch for: {category} | Region: {region or 'Global'}")
    articles = fetch_articles(keywords, max_articles=5, region=region)

    new_articles = [a for a in articles if not article_exists_in_notion(a["title"])]

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(tqdm(executor.map(lambda a: push_to_notion(a, category), new_articles), total=len(new_articles)))

    count = sum(results)
    write_summary(category, count)
    logging.info(f"📦 Done: {count} new articles added for category '{category}'\n")

    # ✅ Save result for Streamlit UI
    ui_output = [
        {"title": article["title"], "url": article["url"]}
        for article, success in zip(new_articles, results) if success
    ]
    
    ui_result = {
        "tool": "content_radar",
        "category": category,
        "added": ui_output,
        "skipped": len(new_articles) - len(ui_output)
    }

    with open("logs/content_radar_ui_result.json", "w") as f:
        json.dump(ui_result, f, indent=2)

    return ui_output, len(new_articles) - len(ui_output)