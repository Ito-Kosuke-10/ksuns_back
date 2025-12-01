from typing import Any, Dict, List

import asyncio
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core.config import get_settings

settings = get_settings()

API_VERSION = "2025-04-01-preview"
MODEL_NAME = "gpt-5-mini"  # Azure 上のデプロイ名を想定


client = AzureOpenAI(
    api_version=API_VERSION,
    azure_endpoint=settings.target_uri,
    api_key=settings.ai_foundry_key,
)


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


async def generate_store_story(context: Dict[str, Any]) -> str:
    """簡易シミュレーション結果などから、店のストーリーテキストを生成する。"""
    prompt = (
        "あなたは飲食店開業のストーリーテラーです。"
        "ユーザーの回答をもとに、温かく具体的な店のイメージを、"
        "300〜500文字程度の日本語でまとめてください。"
        "否定的な表現は避け、前向きなトーンを保ってください。"
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"ユーザーの回答: {context}"},
    ]
    return await _chat_completion(messages, max_completion_tokens=512)


async def generate_summary(summary_type: str, context: Dict[str, Any]) -> str:
    """銀行向け・家族向けなどのサマリーテキストを生成する。"""
    prompt = (
        f"サマリー種別: {summary_type}。"
        "与えられた計画情報をもとに、対象読者に合わせた口調で、"
        "日本語のサマリーを 800〜1200 文字程度で作成してください。"
        "数値は入力に含まれるもののみを用い、新しい数字は作らないでください。"
        "リスクとその対策、今後のアクションにも触れてください。"
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"計画情報: {context}"},
    ]
    return await _chat_completion(messages, max_completion_tokens=1200)


async def answer_question(context: Dict[str, Any], question: str) -> str:
    """なんでも質問ボックスや深掘り質問で利用する回答生成。"""
    prompt = (
        "あなたは飲食店開業のコーチです。"
        "ユーザーの状況に沿って、親しみやすく現実的なアドバイスを日本語で返してください。"
        "可能であれば、今すぐ実行できる具体的な一歩も 1 つ示してください。"
    )
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"状況: {context}\n質問: {question}"},
    ]
    return await _chat_completion(messages, max_completion_tokens=800)

