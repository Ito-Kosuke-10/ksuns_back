from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Tuple

from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core.config import get_settings

settings = get_settings()

API_VERSION = "2025-04-01-preview"
MODEL_NAME = "gpt-5-mini"  # Azure 上でのデプロイ名を想定
client = AzureOpenAI(
    api_version=API_VERSION,
    azure_endpoint=settings.target_uri,
    api_key=settings.ai_foundry_key,
)

# =========================================================
#  日本語変換用の辞書定義
# =========================================================
TRANSLATION_MAP = {
    # main_genre
    "japanese": "和食",
    "western": "洋食",
    "chinese": "中華",
    "asian": "アジア・エスニック",
    "cafe": "カフェ・スイーツ",
    "bar": "バー・酒場",
    "ramen": "ラーメン・麺",
    "yakiniku": "焼肉・焼き鳥・肉",
    "fastfood": "ファストフード・軽食",
    "bakery": "ベーカリー・惣菜",
    "kitchencar": "キッチンカー",
    "other": "その他",
    
    # sub_genre (ramen)
    "ramen_shoyu": "醤油ラーメン",
    "ramen_tonkotsu": "豚骨ラーメン",
    "ramen_miso": "味噌ラーメン",
    "ramen_tsukemen": "つけ麺",
    "ramen_aburasoba": "油そば",
    
    # location
    "station_area": "駅前・駅チカ",
    "shopping_district": "商店街",
    "office_area": "オフィス街",
    "residential_area": "住宅街",
    "mall": "ショッピングモール内",
    "roadside": "ロードサイド",
    "tourist_spot": "観光地",
    
    # business_hours
    "lunch": "ランチ",
    "dinner": "ディナー",
    "late_night": "深夜",
    "all_day": "終日",
}

# simple_simulation の質問メタデータ
QUESTION_METADATA: dict[str, dict[str, str]] = {
    "main_genre": {
        "label": "メインジャンル",
        "question": "どんなジャンルのお店としてスタートしたいですか？一番近いものを1つ選んでください。",
        "type": "single",
    },
    "sub_genre": {
        "label": "サブジャンル（メインジャンルの深掘り）",
        "question": "さきほど選んだジャンルについて、どのスタイルが一番近いですか？イメージに近いものを1つ選んでください。",
        "type": "single",
    },
    "seats": {
        "label": "座席数",
        "question": "カウンター・テーブル席を合わせた合計で、だいたい何席くらいを想定していますか？",
        "type": "slider",
    },
    "price_range": {
        "label": "想定客単価のレンジ",
        "question": "1人あたり（ドリンク込み）の想定客単価レンジで、イメージに一番近いものを1つ選んでください。",
        "type": "single",
    },
    "price_point": {
        "label": "想定客単価の具体的な金額（円）",
        "question": "1人あたりの想定客単価を、より具体的な金額（円）で教えてください。",
        "type": "slider",
    },
    "business_hours": {
        "label": "営業時間帯",
        "question": "メインの営業時間帯として、どの時間帯のイメージが近いですか？",
        "type": "single",
    },
    "location": {
        "label": "立地のイメージ",
        "question": "出店したい場所のイメージとして、一番近いものを1つ選んでください。",
        "type": "single",
    },
}

def _translate(value: Any) -> Any:
    """辞書にあるものは日本語に変換、なければそのまま返す"""
    if isinstance(value, str):
        return TRANSLATION_MAP.get(value, value)
    return value

def _calculate_kpi(store_profile: Dict[str, Any]) -> str:
    """KPI（想定月商など）を計算して説明文を返す"""
    try:
        seats = float(store_profile.get("seats", 0))
        price = float(store_profile.get("price_point", 0))
        
        # 簡易ロジック: ランチ1.5回転 + ディナー0.8回転 = 2.3回転/日 と仮定
        turns = 2.3
        # 営業日数: 25日と仮定
        days = 25
        
        monthly_sales = seats * price * turns * days
        
        return (
            f"【試算条件】席数:{int(seats)}席 / 客単価:{int(price)}円 / 想定回転数:{turns}回 / 営業日数:{days}日\n"
            f"【想定月商】約 {int(monthly_sales):,} 円"
        )
    except Exception:
        return "KPI算出不可（数値不足）"


def _format_store_profile_for_prompt(store_profile: Dict[str, Any]) -> str:
    """store_profile を人間可読な形（かつ日本語）に展開する。"""
    lines: list[str] = []
    
    # KPI計算結果を追加
    kpi_info = _calculate_kpi(store_profile)
    lines.append(f"--- 自動試算データ ---\n{kpi_info}\n-------------------")

    for key, meta in QUESTION_METADATA.items():
        raw_value = store_profile.get(key, "")
        # ここで日本語に変換！
        value = _translate(raw_value)
        
        label = meta.get("label", key)
        question = meta.get("question", "")
        qtype = meta.get("type", "")
        lines.append(f"- {label}: {value}")
    return "\n".join(lines)


async def _chat_completion(
    messages: List[ChatCompletionMessageParam],
    max_completion_tokens: int = 2000,
) -> str:
    """Azure OpenAI の chat.completions を呼び出し、最初のメッセージ内容を返す。"""

    def _call() -> str:
        response = client.chat.completions.create(
            messages=messages,
            max_completion_tokens=max_completion_tokens,
            model=MODEL_NAME,
        )
        
        # デバッグログ
        # print(f"🤖AIレスポンス詳細: {response.choices[0]}")

        if not response.choices:
            return ""
        content = response.choices[0].message.content
        return content or ""

    try:
        return await asyncio.to_thread(_call)
    except Exception as e:
        print(f"🔥🔥AIエラー発生: {e}")
        return ""


async def generate_store_story(store_profile: Dict[str, Any]) -> str:
    """簡易シミュレーション回答から、店のストーリーを生成する。"""
    prompt = (
        "あなたは飲食店開業を支援するストーリーライターです。"
        "ユーザーの回答をもとに、その店が実際に営業している情景が浮かぶようなストーリーを、"
        "300〜500文字程度の日本語でまとめてください。"
        "【重要】"
        "・回答にある「メインジャンル」「サブジャンル」を厳守してください。"
        "・回答にないジャンル（例：ラーメン屋なのにカフェ、居酒屋なのにパン屋など）を勝手に混ぜないでください。"
        "・「立地」や「客単価」から、具体的なターゲット（例：会社員、学生、ファミリー）を論理的に想定してください。"
        "・否定的な表現は避け、前向きなトーンを保ってください。"
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"{_format_store_profile_for_prompt(store_profile)}",
        },
    ]
    story = await _chat_completion(messages, max_completion_tokens=3000)
    if story:
        return story

    # フォールバック
    main = _translate(store_profile.get("main_genre")) or "お店"
    sub = _translate(store_profile.get("sub_genre")) or ""
    location = _translate(store_profile.get("location")) or "街"
    hours = _translate(store_profile.get("business_hours")) or "営業時間未設定"
    return (
        f"{location}にある{main}（{sub}）として、{hours}帯を中心にお客さまを迎える計画です。"
        "こじんまりとしつつも温かい雰囲気で、日常を少し特別にする場所を目指します。"
    )


async def generate_concept_summary(store_profile: Dict[str, Any]) -> Tuple[str, str]:
    """仮コンセプト（タイトル＋短文）を生成する。"""
    prompt = (
        "あなたは飲食店開業のコンセプトメイカーです。"
        "与えられた情報をもとに、仮コンセプトのタイトル（30文字以内）と短文（120文字以内）を作ってください。"
        "【重要】"
        "・英語のID（例: office_area）は使わず、必ず日本語（例: オフィス街）で表現してください。"
        "・指定されたジャンル以外の要素（カフェ等）を勝手に付け足さないでください。"
        "・「誰に（ターゲット）」「どんな価値（体験）を」提供するかを具体的にイメージさせる内容にしてください。"
        'JSON のみで返してください: {"title": "...", "detail": "..."}'
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"{_format_store_profile_for_prompt(store_profile)}",
        },
    ]
    text = await _chat_completion(messages, max_completion_tokens=2000)
    title = ""
    detail = ""
    if text:
        try:
            cleaned_text = text.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_text)
            title = (data.get("title") or "").strip()
            detail = (data.get("detail") or "").strip()
        except json.JSONDecodeError:
            for line in text.splitlines():
                if line.strip().upper().startswith("TITLE:"):
                    title = line.split(":", 1)[1].strip()
                elif line.strip().upper().startswith("DETAIL:"):
                    detail = line.split(":", 1)[1].strip()
            if not title and text.strip():
                title = text.strip().splitlines()[0][:30]
            if not detail and text.strip():
                detail = text.strip()

    if not title or not detail:
        main = _translate(store_profile.get("main_genre")) or "お店"
        sub = _translate(store_profile.get("sub_genre")) or ""
        loc = _translate(store_profile.get("location")) or ""
        title = title or f"{loc}の{main}".strip()
        detail = detail or "回答に基づき仮コンセプトを提示しています。条件を見直して再生成もできます。"

    return (title[:30], detail[:200])


async def generate_funds_summary(store_profile: Dict[str, Any]) -> str:
    """簡易収支の示唆を生成する。KPIの計算結果も参照させる。"""
    prompt = (
        "あなたは飲食店開業のファイナンスアドバイザーです。"
        "与えられた情報（自動試算データを含む）をもとに、"
        "想定月商に対する家賃負担や、利益を出すためのポイントについて、"
        "100〜200文字で具体的なアドバイスを返してください。"
        "【重要】"
        "・「想定月商」の金額を引用し、それに基づいた家賃目安（月商の10%程度など）に言及してください。"
        "・前向きで現実的なトーンにしてください。"
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"{_format_store_profile_for_prompt(store_profile)}",
        },
    ]
    summary = await _chat_completion(messages, max_completion_tokens=2000)
    if summary:
        return summary

    seats = store_profile.get("seats", 0)
    price = store_profile.get("price_point", 0)
    location = _translate(store_profile.get("location")) or "未設定"
    return (
        f"席数{seats}席、客単価{price}円、立地[{location}]を前提に、"
        "家賃と人件費のバランス、回転数のシナリオを確認しましょう。"
    )


async def generate_summary(summary_type: str, context: Dict[str, Any]) -> str:
    """summary_type に応じたサマリーテキストを生成する。"""
    prompt = (
        f"サマリー種別: {summary_type}。"
        "与えられた計画情報をもとに、対象読者に合わせた口調で、"
        "日本語のサマリーを800〜1200 文字程度で作成してください。"
        "数値は入力に含まれるもののみを用い、新しい数値は作らないでください。"
        "リスクと対策、今後のアクションにも触れてください。"
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"計画情報: {context}"},
    ]
    return await _chat_completion(messages, max_completion_tokens=5000)


async def answer_question(context: Dict[str, Any], question: str) -> str:
    """なんでも質問ボックス／深掘り質問で利用する回答生成。"""
    prompt = (
        "あなたは飲食店開業のコーチです。"
        "ユーザーの状況に沿って、親しみやすく現実的なアドバイスを日本語で返してください。"
        "理解があいまいな場合は、推測しすぎず、次の一手をシンプルに提案してください。"
        "長すぎない文章で、重要なポイントを1つ以上含めてください。"
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"前提: {context}\n質問: {question}"},
    ]
    return await _chat_completion(messages, max_completion_tokens=3000)