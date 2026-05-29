"""
じゃらん公開口コミページからレビューを取得する
requests + BeautifulSoup 版（Streamlit Cloud対応）
"""
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

JALAN_KUCHIKOMI_URL = "https://www.jalan.net/yad314822/kuchikomi/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


@dataclass
class Review:
    id: str
    platform: str
    reviewer: str
    date: str
    rating: float
    text: str
    replied: bool


def scrape_jalan_reviews(max_pages: int = 1) -> list[Review]:
    """じゃらん公開口コミページから口コミ一覧を取得"""
    reviews = []

    for page_num in range(max_pages):
        url = JALAN_KUCHIKOMI_URL if page_num == 0 else f"{JALAN_KUCHIKOMI_URL}?page={page_num + 1}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        items = soup.select(".jlnpc-kuchikomiCassette")
        if not items:
            break

        for i, item in enumerate(items):
            name_el = item.select_one(".jlnpc-kuchikomiCassette__userName")
            date_el = item.select_one(".jlnpc-kuchikomiCassette__postDate")
            rate_el = item.select_one(".jlnpc-kuchikomiCassette__totalRate")
            body_el = item.select_one(".jlnpc-kuchikomiCassette__postBody")
            reply_el = item.select_one(".jlnpc-kuchikomiCassette__reply")

            if not body_el:
                continue

            reviewer = name_el.get_text(strip=True) if name_el else "匿名"
            date = (date_el.get_text(strip=True) if date_el else "").replace("投稿日：", "")
            try:
                rating = float(rate_el.get_text(strip=True)) if rate_el else 0.0
            except ValueError:
                rating = 0.0
            text = body_el.get_text(strip=True)
            replied = reply_el is not None

            reviews.append(Review(
                id=f"jalan_{page_num}_{i}",
                platform="じゃらん",
                reviewer=reviewer,
                date=date,
                rating=rating,
                text=text,
                replied=replied,
            ))

    return reviews


def save_reviews(reviews: list[Review], path: str = "output/jalan_reviews.json"):
    Path(path).parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in reviews], f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("じゃらん口コミを取得中...")
    reviews = scrape_jalan_reviews()
    unreplied = [r for r in reviews if not r.replied]
    print(f"取得: {len(reviews)}件 / 未返信: {len(unreplied)}件")
    for r in unreplied[:3]:
        print(f"★{r.rating} {r.reviewer} ({r.date})\n  {r.text[:80]}...")
    save_reviews(reviews)
