"""
口コミ返信AI - 管理画面デモ
悠の湯 風の季 × GREE X
"""
import streamlit as st
from ai_responder import generate_response
from jalan_public_scraper import Review, scrape_jalan_reviews

st.set_page_config(
    page_title="口コミ返信AI | 悠の湯 風の季",
    page_icon="♨️",
    layout="wide",
)

st.markdown("""
<style>
.review-card {
    background: #f8f9fa;
    border-left: 4px solid #e74c3c;
    padding: 16px 20px;
    border-radius: 4px;
    margin-bottom: 8px;
}
.platform-badge {
    display: inline-block;
    background: #ff6600;
    color: white;
    font-size: 12px;
    padding: 2px 10px;
    border-radius: 12px;
    font-weight: bold;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


# ========== データ取得 ==========
@st.cache_data(ttl=300, show_spinner="じゃらんから最新口コミを取得中...")
def load_reviews() -> list[dict]:
    reviews = scrape_jalan_reviews(max_pages=1)
    return [
        {
            "id": r.id,
            "platform": r.platform,
            "reviewer": r.reviewer,
            "date": r.date,
            "rating": r.rating,
            "text": r.text,
            "replied": r.replied,
        }
        for r in reviews
    ]


# セッションステート初期化
if "reviews" not in st.session_state:
    st.session_state.reviews = load_reviews()
if "generated" not in st.session_state:
    st.session_state.generated = {}
if "sent" not in st.session_state:
    st.session_state.sent = set()
if "sent_replies" not in st.session_state:
    st.session_state.sent_replies = {}  # rid -> 実際に送信した返信文


# ========== ヘッダー ==========
col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.title("♨️ 口コミ返信AI")
    st.caption("悠の湯 風の季 — じゃらん口コミ管理")
with col_refresh:
    st.write("")
    if st.button("🔄 最新取得", use_container_width=True):
        st.cache_data.clear()
        st.session_state.reviews = load_reviews()
        st.session_state.generated = {}
        st.session_state.sent = set()
        st.rerun()

# ========== KPI ==========
reviews = st.session_state.reviews
total = len(reviews)
unreplied_list = [r for r in reviews if not r["replied"] and r["id"] not in st.session_state.sent]
replied_count = total - len(unreplied_list)
avg_rating = sum(r["rating"] for r in reviews) / total if total else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("未返信", f"{len(unreplied_list)}件", delta=f"-{len(unreplied_list)}件 要対応", delta_color="inverse")
c2.metric("返信済み", f"{replied_count}件")
c3.metric("平均評価", f"★ {avg_rating:.1f}")
c4.metric("総口コミ数", f"{total}件")

st.divider()

# ========== 一括生成 ==========
col_btn, _ = st.columns([3, 5])
with col_btn:
    if st.button("⚡ 未返信を一括AI生成", type="primary", use_container_width=True):
        targets = [r for r in reviews if not r["replied"] and r["id"] not in st.session_state.sent and r["id"] not in st.session_state.generated]
        if targets:
            with st.spinner(f"{len(targets)}件の返信案を生成中..."):
                for r in targets:
                    st.session_state.generated[r["id"]] = generate_response(r["text"])
            st.success(f"✅ {len(targets)}件の返信案を生成しました")
        else:
            st.info("生成済みか返信済みです")

st.divider()

# ========== 絞り込みタブ ==========
tab1, tab2, tab3 = st.tabs([f"未返信 ({len(unreplied_list)}件)", f"返信済み ({replied_count}件)", f"全件 ({total}件)"])

def render_reviews(review_list, tab_prefix: str = ""):
    if not review_list:
        st.info("該当する口コミはありません")
        return

    for review in review_list:
        rid = review["id"]
        key = f"{tab_prefix}_{rid}"  # タブごとにユニークなキー
        is_done = review["replied"] or rid in st.session_state.sent
        stars = "★" * int(review["rating"]) + ("☆" * (5 - int(review["rating"])))

        with st.expander(
            f"{'✅' if is_done else '📝'} {review['platform']} | {review['reviewer']} | {stars} {review['rating']} | {review['date']}",
            expanded=(not is_done),
        ):
            st.markdown(f"""
            <div class="review-card">
                <span class="platform-badge">{review['platform']}</span>
                <p style="margin-top:8px; line-height:1.8; color:#333;">{review['text']}</p>
            </div>
            """, unsafe_allow_html=True)

            if is_done:
                if rid in st.session_state.sent_replies:
                    st.success("✅ 返信済み（このセッションで送信）")
                    with st.expander("送信した返信文を確認"):
                        st.write(st.session_state.sent_replies[rid])
                else:
                    st.success("✅ 返信済み")
                continue

            col_gen, _ = st.columns([2, 6])
            with col_gen:
                if st.button("🤖 AI返信を生成", key=f"gen_{key}", use_container_width=True):
                    with st.spinner("生成中..."):
                        st.session_state.generated[rid] = generate_response(review["text"])

            if rid in st.session_state.generated:
                st.markdown("**AI生成返信案（自由に編集できます）：**")
                edit_key = f"edit_{key}"
                # 初回はAI生成文、以降は編集内容を保持
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = st.session_state.generated[rid]
                edited = st.text_area(
                    "↓ 自由に編集してください",
                    value=st.session_state[edit_key],
                    height=180,
                    key=edit_key,
                )
                char_count = len(edited)
                st.caption(f"文字数: {char_count}文字")

                col_send, col_reset, col_skip, _ = st.columns([2, 2, 2, 2])
                with col_send:
                    if st.button("📤 承認して送信", key=f"send_{key}", type="primary", use_container_width=True):
                        final_text = st.session_state.get(edit_key, st.session_state.generated[rid])
                        st.session_state.sent.add(rid)
                        st.session_state.sent_replies[rid] = final_text
                        del st.session_state.generated[rid]
                        st.success("✅ 送信しました")
                        st.rerun()
                with col_reset:
                    if st.button("↩ AI文に戻す", key=f"reset_{key}", use_container_width=True):
                        st.session_state[edit_key] = st.session_state.generated[rid]
                        st.rerun()
                with col_skip:
                    if st.button("⏭ スキップ", key=f"skip_{key}", use_container_width=True):
                        del st.session_state.generated[rid]
                        st.rerun()

with tab1:
    render_reviews(unreplied_list, tab_prefix="t1")

with tab2:
    replied_list = [r for r in reviews if r["replied"] or r["id"] in st.session_state.sent]
    render_reviews(replied_list, tab_prefix="t2")

with tab3:
    render_reviews(reviews, tab_prefix="t3")

st.divider()
st.caption("Powered by Claude AI × GREE X | 口コミ返信AI v0.2 | データソース: じゃらんnet")
