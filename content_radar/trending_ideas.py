from trending_to_notion import fetch_and_push_articles
from keywords_config import CATEGORY_KEYWORDS
import json
import os

def main():
    print("🚀 Starting Content Idea Radar for all categories...\n")

    all_added = []
    total_skipped = 0

    for category in CATEGORY_KEYWORDS.keys():
        print(f"🔍 Running for category: {category}")
        try:
            result = fetch_and_push_articles(category)
            if result:
                added, skipped = result
                all_added.extend(added)
                total_skipped += skipped
        except Exception as e:
            print(f"❌ Error while processing '{category}': {e}")
        print("-" * 40)

    print("\n✅ All categories processed.")

    # Write combined result for UI
    ui_result = {
        "tool": "content_radar",
        "category": "All Categories",
        "added": all_added,
        "skipped": total_skipped
    }

    os.makedirs("logs", exist_ok=True)
    with open("logs/content_radar_ui_result.json", "w") as f:
        json.dump(ui_result, f, indent=2)

if __name__ == "__main__":
    main()
