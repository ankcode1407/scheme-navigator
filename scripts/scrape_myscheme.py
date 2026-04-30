import requests
import json
import time
import os
from datetime import date

BASE_SEARCH = "https://api.myscheme.gov.in/search/v6/schemes"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "origin": "https://www.myscheme.gov.in",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
    "x-api-key": "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc",
}

CATEGORIES = [
    "Agriculture,Rural & Environment",
    "Social welfare & Empowerment",
    "Skills & Employment",
    "Business & Entrepreneurship",
    "Women and Child",
    "Housing & Shelter",
    "Health & Wellness",
    "Education & Learning",
    "Banking,Financial Services and Insurance",
    "Sports & Culture",
    "Science, IT & Communications",
    "Transport & Infrastructure",
    "Utility & Sanitation",
]

def fetch_page(category: str, from_: int, size: int = 100) -> dict:
    params = {
        "lang": "en",
        "q": json.dumps([{
            "identifier": "schemeCategory",
            "value": category
        }]),
        "keyword": "",
        "sort": "",
        "from": from_,
        "size": size,
    }
    try:
        r = requests.get(BASE_SEARCH, params=params,
                         headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"    Error: {e}")
        return {}

def scrape_all():
    all_schemes = []
    seen_ids = set()

    for category in CATEGORIES:
        print(f"\n[{category}]")
        from_ = 0

        while True:
            data = fetch_page(category, from_)
            if not data:
                break

            hits = data.get("data", {}).get("hits", {})
            items = hits.get("items", [])
            page_info = hits.get("page", {})
            total = page_info.get("total", 0)

            if not items:
                break

            added = 0
            for item in items:
                sid = item.get("id")
                if sid in seen_ids:
                    continue
                seen_ids.add(sid)
                fields = item.get("fields", {})

                all_schemes.append({
                    "id": sid,
                    "slug": fields.get("slug", ""),
                    "name": fields.get("schemeName", ""),
                    "short_title": fields.get("schemeShortTitle", ""),
                    "brief_description": fields.get("briefDescription", ""),
                    "tags": fields.get("tags", []),
                    "state": fields.get("beneficiaryState", []),
                    "level": fields.get("level", ""),
                    "category": fields.get("schemeCategory", []),
                    "scheme_for": fields.get("schemeFor", ""),
                    "close_date": fields.get("schemeCloseDate"),
                    "source_url": f"https://www.myscheme.gov.in/schemes/{fields.get('slug', '')}",
                    "scraped_date": str(date.today()),
                })
                added += 1

            from_ += len(items)
            print(f"  {from_}/{total} fetched | total unique: {len(all_schemes)}")

            if from_ >= total:
                break

            time.sleep(0.4)

    return all_schemes

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    print("Scraping MyScheme API...")
    schemes = scrape_all()
    print(f"\nTotal unique schemes: {len(schemes)}")

    with open("data/myscheme_raw.json", "w", encoding="utf-8") as f:
        json.dump(schemes, f, ensure_ascii=False, indent=2)

    print("Saved: data/myscheme_raw.json")
    print(f"\nSample scheme:")
    print(json.dumps(schemes[0], indent=2, ensure_ascii=False))