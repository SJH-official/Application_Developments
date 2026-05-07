import httpx
from bs4 import BeautifulSoup
from database import create_quote, get_all_quotes

BASE_URL = "https://quotes.toscrape.com"

CATEGORIES = [
    "love", "life", "inspirational", "humor",
    "books", "reading", "friendship", "truth",
    "simile", "change",
]


def _existing_texts() -> set[str]:
    return {q["text"] for q in get_all_quotes(limit=10000)}


def scrape_by_tag(tag: str, max_quotes: int = 20) -> list[dict]:
    collected = []
    page = 1

    while len(collected) < max_quotes:
        url = f"{BASE_URL}/tag/{tag}/page/{page}/"
        try:
            resp = httpx.get(url, timeout=15, follow_redirects=True)
            if resp.status_code != 200:
                break
        except httpx.RequestError:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        quote_divs = soup.select("div.quote")
        if not quote_divs:
            break

        for div in quote_divs:
            if len(collected) >= max_quotes:
                break
            text   = div.select_one("span.text").get_text(strip=True).strip("\u201c\u201d")
            author = div.select_one("small.author").get_text(strip=True)
            tags   = ",".join(t.get_text(strip=True) for t in div.select("a.tag"))
            collected.append({"text": text, "author": author, "tags": tags})

        if not soup.select_one("li.next"):
            break
        page += 1

    return collected


def run_scraper(categories: list[str] = CATEGORIES, max_per_cat: int = 20) -> dict:
    existing = _existing_texts()
    saved, skipped = 0, 0

    for cat in categories:
        quotes = scrape_by_tag(cat, max_per_cat)
        for q in quotes:
            if q["text"] in existing:
                skipped += 1
                continue
            create_quote(
                text=q["text"],
                author=q["author"],
                tags=q["tags"],
                source=f"quotes.toscrape.com/tag/{cat}",
            )
            existing.add(q["text"])
            saved += 1

    return {"saved": saved, "skipped_duplicates": skipped, "categories": categories}


if __name__ == "__main__":
    from database import init_db
    init_db()
    result = run_scraper()
    print(result)