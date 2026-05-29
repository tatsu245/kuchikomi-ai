"""
じゃらん公開口コミページからレビューを取得する
管理画面ログイン不要 — デモ・動作確認用
"""
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

JALAN_KUCHIKOMI_URL = "https://www.jalan.net/yad314822/kuchikomi/"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(JALAN_KUCHIKOMI_URL, timeout=20000)
        page.wait_for_load_state("networkidle", timeout=10000)

        for page_num in range(max_pages):
            items = page.query_selector_all(".jlnpc-kuchikomiCassette")

            for i, item in enumerate(items):
                name_el = item.query_selector(".jlnpc-kuchikomiCassette__userName")
                date_el = item.query_selector(".jlnpc-kuchikomiCassette__postDate")
                rate_el = item.query_selector(".jlnpc-kuchikomiCassette__totalRate")
                body_el = item.query_selector(".jlnpc-kuchikomiCassette__postBody")
                reply_el = item.query_selector(".jlnpc-kuchikomiCassette__reply")

                if not body_el:
                    continue

                reviewer = name_el.inner_text().strip() if name_el else "匿名"
                date_raw = date_el.inner_text().strip() if date_el else ""
                date = date_raw.replace("投稿日：", "").strip()
                rating_raw = rate_el.inner_text().strip() if rate_el else "0"
                try:
                    rating = float(rating_raw)
                except ValueError:
                    rating = 0.0
                text = body_el.inner_text().strip()
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

            # 次ページがあれば遷移（max_pages > 1 の場合）
            if page_num + 1 < max_pages:
                next_btn = page.query_selector("a.c-pagination__next")
                if next_btn:
                    next_btn.click()
                    page.wait_for_load_state("networkidle", timeout=10000)
                else:
                    break

        browser.close()

    return reviews


def save_reviews(reviews: list[Review], path: str = "output/jalan_reviews.json"):
    Path(path).parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in reviews], f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("じゃらん口コミを取得中...")
    reviews = scrape_jalan_reviews(max_pages=1)
    unreplied = [r for r in reviews if not r.replied]

    print(f"\n取得件数: {len(reviews)}件")
    print(f"未返信: {len(unreplied)}件")
    print(f"返信済み: {len(reviews) - len(unreplied)}件\n")

    for r in unreplied[:3]:
        print(f"★{r.rating} {r.reviewer} ({r.date})")
        print(f"  {r.text[:80]}...")
        print()

    save_reviews(reviews)
    print(f"保存: output/jalan_reviews.json")
