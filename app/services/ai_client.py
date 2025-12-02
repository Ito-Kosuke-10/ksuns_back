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


def _format_store_profile_for_prompt(store_profile: Dict[str, Any]) -> str:
    """store_profile を人間可読な形に展開する。"""
    lines: list[str] = []
    for key, meta in QUESTION_METADATA.items():
        value = store_profile.get(key, "")
        label = meta.get("label", key)
        question = meta.get("question", "")
        qtype = meta.get("type", "")
        lines.append(f"- {label} ({key}, {qtype}): {value} // {question}")
    return "\n".join(lines)


async def _chat_completion(
    messages: List[ChatCompletionMessageParam],
    max_completion_tokens: int = 800,
) -> str:
    """Azure OpenAI の chat.completions を呼び出し、最初のメッセージ内容を返す。"""

    def _call() -> str:
        response = client.chat.completions.create(
            messages=messages,
            max_completion_tokens=max_completion_tokens,
            model=MODEL_NAME,
        )
        if not response.choices:
            return ""
        content = response.choices[0].message.content
        return content or ""

    try:
        return await asyncio.to_thread(_call)
    except Exception:
        return ""


async def generate_store_story(store_profile: Dict[str, Any]) -> str:
    """簡易シミュレーション回答から、店のストーリーを生成する。"""
    prompt = (
        "あなたは飲食店開業を支援するストーリーライターです。"
        "ユーザーの回答をもとに、温かく具体的な店のイメージを、"
        "300〜500文字程度の日本語でまとめてください。"
        "否定的な表現は避け、前向きなトーンを保ってください。"
        "新しい数値を作らず、入力に含まれる情報だけを使ってください。"
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"store_profile(JSON): {store_profile}\nstore_profile(detail):\n{_format_store_profile_for_prompt(store_profile)}",
        },
    ]
    story = await _chat_completion(messages, max_completion_tokens=512)
    if story:
        return story

    # フォールバック: store_profile をもとに簡易生成
    main = store_profile.get("main_genre") or "お店"
    sub = store_profile.get("sub_genre") or ""
    location = store_profile.get("location") or "街"
    hours = store_profile.get("business_hours") or "営業時間未設定"
    return (
        f"{location}にある{main}（{sub}）として、{hours}帯を中心にお客さまを迎える計画です。"
        "こじんまりとしつつも温かい雰囲気で、日常を少し特別にする場所を目指します。"
    )


async def generate_concept_summary(store_profile: Dict[str, Any]) -> Tuple[str, str]:
    """仮コンセプト（タイトル＋短文）を生成する。"""
    prompt = (
        "あなたは飲食店開業のコンセプトメイカーです。"
        "与えられた store_profile をもとに、仮コンセプトのタイトル（30文字以内）と短文（120文字以内）を作ってください。"
        "前向きで具体的な表現にし、数字は入力にあるもののみを使い、新規の数値は作らないでください。"
        'JSON のみで返してください: {"title": "...", "detail": "..."}'
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"store_profile(JSON): {store_profile}\nstore_profile(detail):\n{_format_store_profile_for_prompt(store_profile)}",
        },
    ]
    text = await _chat_completion(messages, max_completion_tokens=256)
    title = ""
    detail = ""
    if text:
        try:
            data = json.loads(text)
            title = (data.get("title") or "").strip()
            detail = (data.get("detail") or "").strip()
        except json.JSONDecodeError:
            # シンプルなテキスト fallback: "TITLE: ..." 形式などを拾う
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
        main = store_profile.get("main_genre") or "お店"
        sub = store_profile.get("sub_genre") or ""
        loc = store_profile.get("location") or ""
        title = title or f"{loc}の{main}".strip()
        detail = detail or "回答に基づき仮コンセプトを提示しています。条件を見直して再生成もできます。"

    return (title[:30], detail[:200])


async def generate_funds_summary(store_profile: Dict[str, Any]) -> str:
    """簡易収支の示唆を生成する。新規の具体的な数値は作らない。"""
    prompt = (
        "あなたは飲食店開業のファイナンスアドバイザーです。"
        "与えられた回答をもとに、簡易な収支の示唆・注意点を100〜200文字で返してください。"
        "新しい数値は作らず、入力にある数値・条件のみを参照してください。"
        "前向きで現実的なトーンにしてください。"
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"store_profile(JSON): {store_profile}\nstore_profile(detail):\n{_format_store_profile_for_prompt(store_profile)}",
        },
    ]
    summary = await _chat_completion(messages, max_completion_tokens=256)
    if summary:
        return summary

    seats = store_profile.get("seats", 0)
    price_range = store_profile.get("price_range", "未設定")
    location = store_profile.get("location", "未設定")
    return (
        f"席数{seats}席、客単価レンジ[{price_range}]、立地[{location}]を前提に、"
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
    return await _chat_completion(messages, max_completion_tokens=1200)


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
    return await _chat_completion(messages, max_completion_tokens=800)

