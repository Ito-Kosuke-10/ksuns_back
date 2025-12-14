"""AI Client service for Azure OpenAI integration."""
from typing import AsyncGenerator, Optional

from openai import AsyncAzureOpenAI

from app.core.config import get_settings

settings = get_settings()

# Initialize Azure OpenAI client
client = AsyncAzureOpenAI(
    api_key=settings.azure_openai_api_key,
    api_version=settings.azure_openai_api_version,
    azure_endpoint=settings.azure_openai_endpoint,
)

MODEL_NAME = settings.azure_openai_deployment


async def _chat_completion(
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> Optional[str]:
    """Send a chat completion request to Azure OpenAI."""
    if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
        return None

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content
    except Exception:
        return None


async def _chat_completion_stream(
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """Send a streaming chat completion request to Azure OpenAI."""
    if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
        yield ""
        return

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"[エラー: {str(e)}]"


async def answer_question(context: dict, question: str) -> Optional[str]:
    """Answer a user question using AI."""
    axis_code = context.get("axis_code", "")

    system_prompt = """あなたは飲食店開業支援のAIアシスタントです。
ユーザーの質問に対して、親切かつ専門的にアドバイスしてください。
回答は日本語で、具体的で実用的な内容を心がけてください。"""

    if axis_code:
        system_prompt += f"\n現在、ユーザーは「{axis_code}」に関する質問をしています。"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    return await _chat_completion(messages)


async def generate_deep_dive_summary(
    axis_code: str,
    questions_and_answers: list[dict],
) -> Optional[str]:
    """Generate a summary for deep dive questions."""
    system_prompt = f"""あなたは飲食店開業支援のAIアシスタントです。
ユーザーが「{axis_code}」軸について回答した内容を要約してください。
要約は日本語で、簡潔にまとめてください。"""

    qa_text = "\n".join(
        f"Q: {qa.get('question', '')}\nA: {qa.get('answer', '')}"
        for qa in questions_and_answers
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"以下の質問と回答を要約してください:\n\n{qa_text}"},
    ]

    return await _chat_completion(messages, max_tokens=512)


async def generate_summary(
    summary_type: str,
    user_data: dict,
) -> Optional[str]:
    """Generate a summary for different audiences."""
    audience_map = {
        "family": "家族",
        "staff": "スタッフ",
        "bank": "銀行",
        "public": "一般公開",
    }
    audience = audience_map.get(summary_type, "関係者")

    system_prompt = f"""あなたは飲食店開業支援のAIアシスタントです。
ユーザーの開業計画を「{audience}」向けに要約してください。
要約は日本語で、対象者に適した表現を使用してください。"""

    user_content = f"以下の情報をもとに、{audience}向けの要約を作成してください:\n\n"
    for key, value in user_data.items():
        user_content += f"- {key}: {value}\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    return await _chat_completion(messages, max_tokens=1024)

# --- compatibility wrapper: legacy name expected by other modules ---
async def send_chat_completion(
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> str:
    """
    simulation.py 等が import している send_chat_completion の互換関数。
    既存の _chat_completion を呼び出すだけ。
    """
    result = await _chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return result or ""
