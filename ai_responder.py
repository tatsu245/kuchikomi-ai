"""Claude API を使って口コミへの返信文を生成する"""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Streamlit Cloud では st.secrets から、ローカルでは .env から取得
try:
    import streamlit as st
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
except Exception:
    api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)

SYSTEM_PROMPT = """あなたは温泉旅館の支配人です。
お客様の口コミに対して、丁寧・誠実・温かみのある返信文を作成してください。

【返信のルール】
- 冒頭はお客様へのお礼から始める
- 口コミの内容（良い点・改善点）に具体的に言及する
- 悪い口コミにはお詫びと改善の意志を示す
- 良い口コミには喜びと次回来館への期待を伝える
- 締めは「またのご来館をお待ちしております」系で締める
- 文体：丁寧語、300〜400文字程度
- 署名：末尾に「○○ 支配人 [支配人名]」は入れない（別途設定）
- 出力は返信文のみ。見出し・マークダウン・前置き不要
"""


def generate_response(review_text: str, facility_name: str = "悠の湯 風の季") -> str:
    """口コミに対する返信文を生成する"""
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"施設名：{facility_name}\n\n口コミ内容：\n{review_text}\n\n返信文を作成してください。",
                }
            ],
        )
        return message.content[0].text
    except Exception as e:
        print(f"  ⚠️  API呼び出し失敗: {e}")
        return _mock_response(review_text)


def _mock_response(review_text: str) -> str:
    """APIキー未設定時のデモ用モック返信"""
    if any(w in review_text for w in ["残念", "悪かった", "時間がかかり", "事務的"]):
        return (
            "この度はご宿泊いただき、誠にありがとうございました。"
            "またご滞在中にご不便をおかけしてしまい、大変申し訳ございませんでした。"
            "いただいたご意見を真摯に受け止め、スタッフ一同サービス向上に努めてまいります。"
            "次回お越しの際は、より一層快適にお過ごしいただけるよう精進いたします。"
            "またのご来館を心よりお待ちしております。"
        )
    else:
        return (
            "この度は悠の湯 風の季にお越しいただき、また温かいお言葉を頂戴し、"
            "スタッフ一同大変嬉しく拝読いたしました。"
            "花巻の豊かな自然とともに、ゆったりとした時間をお過ごしいただけたとのこと、"
            "これ以上の喜びはございません。"
            "またぜひいつでもお越しくださいませ。"
            "皆様のご来館を心よりお待ちしております。"
        )


if __name__ == "__main__":
    sample_review = "温泉が最高でした！お湯がとろとろで肌がすべすべになりました。スタッフの方も親切で、夕食の和食も絶品。ただ、部屋のエアコンの調子が少し悪かったのが残念でした。次回また来たいと思います。"
    print("【口コミ】")
    print(sample_review)
    print("\n【AI生成返信文】")
    print(generate_response(sample_review))
