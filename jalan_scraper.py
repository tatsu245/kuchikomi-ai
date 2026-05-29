"""
じゃらん施設管理画面（宿ぷらざ）から口コミを取得・返信するPlaywrightスクリプト

【使い方】
1. .env に JALAN_ID / JALAN_PASSWORD を設定
2. python jalan_scraper.py --mode=scrape   # 口コミ取得のみ
3. python jalan_scraper.py --mode=auto     # 取得 + AI返信 + 送信
4. python jalan_scraper.py --mode=demo     # 画面キャプチャ付きデモ
"""

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright

from ai_responder import generate_response

load_dotenv()

# =====================
# じゃらん管理画面の設定
# =====================
JALAN_LOGIN_URL = "https://innkeeper.jalan.net/"
SELECTORS = {
    # ログイン画面（5/29 MTGでスクショ確認後に更新）
    "login_id": "input[name='userId']",
    "login_password": "input[name='password']",
    "login_button": "button[type='submit']",
    # 口コミ一覧（TODO: 吉田様画面共有後に確認）
    "review_menu": "a:has-text('口コミ')",
    "review_list": ".review-list-item",
    "review_text": ".review-comment",
    "reviewer_name": ".reviewer-name",
    "review_date": ".review-date",
    "reply_button": "button:has-text('返信する')",
    "reply_textarea": "textarea.reply-input",
    "reply_submit": "button:has-text('送信')",
}


@dataclass
class Review:
    id: str
    reviewer: str
    date: str
    text: str
    rating: float
    replied: bool = False


def login(page: Page) -> bool:
    """じゃらん施設管理画面にログイン"""
    jalan_id = os.getenv("JALAN_ID")
    jalan_password = os.getenv("JALAN_PASSWORD")

    if not jalan_id or not jalan_password:
        print("⚠️  .env に JALAN_ID / JALAN_PASSWORD が未設定です")
        return False

    page.goto(JALAN_LOGIN_URL)
    page.wait_for_load_state("networkidle")

    page.fill(SELECTORS["login_id"], jalan_id)
    page.fill(SELECTORS["login_password"], jalan_password)
    page.click(SELECTORS["login_button"])
    page.wait_for_load_state("networkidle")

    print("✅ ログイン完了")
    return True


def scrape_reviews(page: Page) -> list[Review]:
    """未返信の口コミ一覧を取得"""
    page.click(SELECTORS["review_menu"])
    page.wait_for_load_state("networkidle")
    page.screenshot(path="screenshots/review_list.png")

    reviews = []
    items = page.query_selector_all(SELECTORS["review_list"])
    for i, item in enumerate(items):
        text_el = item.query_selector(SELECTORS["review_text"])
        name_el = item.query_selector(SELECTORS["reviewer_name"])
        date_el = item.query_selector(SELECTORS["review_date"])

        if text_el:
            review = Review(
                id=f"review_{i}",
                reviewer=name_el.inner_text() if name_el else "匿名",
                date=date_el.inner_text() if date_el else "",
                text=text_el.inner_text(),
                rating=5.0,
            )
            reviews.append(review)

    print(f"✅ {len(reviews)}件の未返信口コミを取得")
    return reviews


def post_reply(page: Page, review_item, reply_text: str) -> bool:
    """口コミに返信を投稿"""
    reply_btn = review_item.query_selector(SELECTORS["reply_button"])
    if not reply_btn:
        return False

    reply_btn.click()
    page.wait_for_timeout(1000)

    textarea = page.query_selector(SELECTORS["reply_textarea"])
    if not textarea:
        return False

    textarea.fill(reply_text)
    page.screenshot(path="screenshots/before_submit.png")

    page.click(SELECTORS["reply_submit"])
    page.wait_for_load_state("networkidle")
    page.screenshot(path="screenshots/after_submit.png")
    return True


def run_demo_mode():
    """デモ用：モックデータで AI 返信生成フローを実演"""
    mock_reviews = [
        Review(
            id="r001",
            reviewer="山田太郎様",
            date="2026-05-10",
            text="温泉が最高でした！お湯がとろとろで肌がすべすべになりました。スタッフの方も親切で、夕食の和食も絶品。ただ、部屋のエアコンの調子が少し悪かったのが残念でした。次回また来たいと思います。",
            rating=4.0,
        ),
        Review(
            id="r002",
            reviewer="佐藤花子様",
            date="2026-05-12",
            text="チェックインが思ったより時間がかかりました。部屋は清潔で広く、温泉も良かったのですが、フロントの対応が少し事務的に感じました。料理はとても美味しかったです。",
            rating=3.5,
        ),
        Review(
            id="r003",
            reviewer="鈴木一郎様",
            date="2026-05-15",
            text="記念日の旅行で利用しました。サプライズのデザートを用意していただき、スタッフの皆様のお心遣いに感動しました。温泉も最高で、一生の思い出になりました。ありがとうございました。",
            rating=5.0,
        ),
    ]

    results = []
    print("=" * 60)
    print("🤖 口コミ返信AI デモ（悠の湯 風の季）")
    print("=" * 60)

    for review in mock_reviews:
        print(f"\n📝 【口コミ #{review.id}】 {review.reviewer} ★{review.rating}")
        print(f"   {review.text[:80]}{'...' if len(review.text) > 80 else ''}")
        print("\n⏳ AI返信生成中...")

        reply = generate_response(review.text, facility_name="悠の湯 風の季")
        print(f"\n✅ 【AI生成返信文】")
        print(reply)
        print("-" * 60)

        results.append({"review": review.text, "ai_reply": reply})
        time.sleep(0.5)

    # 結果をJSONに保存
    Path("output").mkdir(exist_ok=True)
    with open("output/demo_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 結果を output/demo_results.json に保存しました")
    return results


def run_auto_mode():
    """本番用：じゃらん管理画面にログインして自動返信"""
    Path("screenshots").mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        if not login(page):
            browser.close()
            return

        reviews = scrape_reviews(page)
        items = page.query_selector_all(SELECTORS["review_list"])

        for i, review in enumerate(reviews):
            print(f"\n処理中: {review.reviewer} の口コミ")
            reply = generate_response(review.text)
            print(f"返信案: {reply[:100]}...")

            if i < len(items):
                success = post_reply(page, items[i], reply)
                print("✅ 送信完了" if success else "⚠️ 送信失敗")

            time.sleep(2)

        browser.close()
        print("\n✅ 全件処理完了")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["demo", "scrape", "auto"], default="demo")
    args = parser.parse_args()

    if args.mode == "demo":
        run_demo_mode()
    elif args.mode in ("scrape", "auto"):
        run_auto_mode()
