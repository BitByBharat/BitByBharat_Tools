import os
import requests
import pandas as pd
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from keywords_config import TARGET_KEYWORDS
from notion_sync import add_question_to_notion
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_path = os.path.join(LOG_DIR, "quora_scraper.log")
summary_path = os.path.join(LOG_DIR, "notion_summary.json")

logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s - %(message)s")

def calculate_visibility_score(position, keyword, title):
    keyword = keyword.lower()
    title = title.lower()
    if position <= 3 and keyword in title:
        return 5
    elif position <= 5:
        return 4
    elif position <= 10:
        return 3
    else:
        return 2

def search_quora_questions(keyword):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": f"site:quora.com {keyword}",
        "api_key": SERPAPI_KEY,
        "num": 20,
        "hl": "en"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        logging.error(f"❌ SERPAPI error for {keyword} — {response.status_code}")
        return []

    data = response.json()
    results = []
    for idx, result in enumerate(data.get("organic_results", []), start=1):
        link = result.get("link", "")
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        if "quora.com" in link and "/profile/" not in link:
            score = calculate_visibility_score(idx, keyword, title)
            results.append({
                "keyword": keyword,
                "title": title,
                "url": link,
                "snippet": snippet,
                "visibility_score": score
            })
    return results

def write_summary(summary_dict):
    summary = {}
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            summary = json.load(f)
    summary.update(summary_dict)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

def main():
    all_results = []
    notion_push_count = {}
    all_added_questions = []
    total_skipped = 0

    for keyword in TARGET_KEYWORDS:
        logging.info(f"🔍 Searching Quora for: {keyword}")
        results = search_quora_questions(keyword)
        all_results.extend(results)

        logging.info(f"Found {len(results)} results for '{keyword}'")
        with ThreadPoolExecutor(max_workers=4) as executor:
            results_chunked = list(tqdm(executor.map(add_question_to_notion, results), total=len(results)))

        # Track how many were actually added
        added_questions = [
            {"title": row["title"], "url": row["url"]}
            for row, added in zip(results, results_chunked) if added
        ]
        skipped = len(results) - len(added_questions)

        all_added_questions.extend(added_questions)
        total_skipped += skipped

        logging.info(f"✅ Pushed {len(added_questions)} questions for '{keyword}'")
        notion_push_count[keyword] = {
            "questions_pushed": len(added_questions),
            "last_updated": str(datetime.now())
        }

    # Save CSV
    df = pd.DataFrame(all_results)
    df.drop_duplicates(subset="url", inplace=True)
    os.makedirs("output", exist_ok=True)
    df.to_csv("output/trending_quora_questions.csv", index=False)
    logging.info("📁 Saved CSV to output/trending_quora_questions.csv")

    # Notion sync summary
    write_summary(notion_push_count)
    logging.info("✅ Notion summary updated.")

    # Save UI summary JSON
    result_ui = {
        "tool": "quora_scraper",
        "total_keywords": len(TARGET_KEYWORDS),
        "added": all_added_questions,
        "skipped": total_skipped
    }

    with open("logs/quora_ui_result.json", "w") as f:
        json.dump(result_ui, f, indent=2)
