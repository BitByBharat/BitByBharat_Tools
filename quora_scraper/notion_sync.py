import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DB_ID_QUORA_QUESTIONS")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def question_exists_in_notion(title):
    url = "https://api.notion.com/v1/databases/{}/query".format(NOTION_DATABASE_ID)
    payload = {
        "filter": {
            "property": "Question",
            "title": {
                "equals": title[:200]
            }
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        results = response.json().get("results", [])
        return len(results) > 0
    else:
        print(f"❌ Error checking for duplicate: {response.status_code}, {response.text}")
        return False

def add_question_to_notion(row):
    if question_exists_in_notion(row["title"]):
        return False  # Already exists

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Question": {"title": [{"text": {"content": row['title'][:200]}}]},
            "URL": {"url": row['url']},
            "Keyword": {"rich_text": [{"text": {"content": row['keyword']}}]},
            "Snippet": {"rich_text": [{"text": {"content": row['snippet'][:500]}}]},
            "Visibility Score": {"number": row['visibility_score']},
            "Answered": {"checkbox": False},
            "Date Added": {"date": {"start": datetime.today().isoformat()}}
        }
    }
    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
    if response.status_code == 200:
        return True
    else:
        print(f"❌ Error adding to Notion: {response.status_code}, {response.text}")
        return False
