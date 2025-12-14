"""
開業プラン出力API
全8軸のAIサマリーを結合し、AIに再構成させて事業計画書を生成する
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.db import get_session
from app.models.concept_answer import ConceptAnswer
from app.models.funding_plan_answer import FundingPlanAnswer
from app.models.interior_exterior_answer import InteriorExteriorAnswer
from app.models.location_answer import LocationAnswer
from app.models.marketing_answer import MarketingAnswer
from app.models.menu_answer import MenuAnswer
from app.models.operation_answer import OperationAnswer
from app.models.revenue_forecast_answer import RevenueForecastAnswer
from app.schemas.auth import UserInfo
from app.services.ai_client import _chat_completion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("")
async def get_report(
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> dict[str, str]:
    """
    全8軸のAIサマリーを結合してMarkdown形式で返す
    """
    # 各軸のサマリーを取得する関数
    async def get_axis_summary(AnswerModel, axis_name: str) -> str:
        try:
            # ユーザーのすべての回答を取得（summaryが存在するもののみ）
            result = await session.execute(
                select(AnswerModel)
                .where(AnswerModel.user_id == current_user.id)
                .where(AnswerModel.summary.isnot(None))
                .where(AnswerModel.summary != "")
                .order_by(AnswerModel.card_id, desc(AnswerModel.updated_at))
            )
            answers = result.scalars().all()
            
            if not answers:
                return "（未作成）"
            
            # すべてのサマリーを結合（改行で区切る）
            summaries = [answer.summary for answer in answers if answer.summary]
            if not summaries:
                return "（未作成）"
            
            return "\n\n".join(summaries)
        except Exception as e:
            # テーブルが存在しない場合など、エラーが発生した場合は「（未作成）」を返す
            return "（未作成）"
    
    # 各軸のサマリーを取得
    concept_summary = await get_axis_summary(ConceptAnswer, "コンセプト")
    location_summary = await get_axis_summary(LocationAnswer, "立地・物件")
    menu_summary = await get_axis_summary(MenuAnswer, "メニュー")
    marketing_summary = await get_axis_summary(MarketingAnswer, "販促")
    funding_plan_summary = await get_axis_summary(FundingPlanAnswer, "資金計画")
    revenue_forecast_summary = await get_axis_summary(RevenueForecastAnswer, "収支予測")
    operation_summary = await get_axis_summary(OperationAnswer, "オペレーション")
    interior_exterior_summary = await get_axis_summary(InteriorExteriorAnswer, "内装外装")
    
    # AIに事業計画書を生成させる
    system_prompt = """あなたはプロの経営コンサルタント兼コピーライターです。
投資家や金融機関に提出できるレベルの事業計画書（エグゼクティブ・サマリー）を作成してください。

【役割】
- ユーザーが考えた8つの事業軸のメモを統合し、一貫性のある魅力的な「事業計画書サマリー」を執筆する

【出力形式】
以下のMarkdown構造で出力してください：

1. **# 事業計画書：[店名またはコンセプト名]**
   - コンセプトから店名やコンセプト名を抽出して使用してください

2. **## エグゼクティブ・サマリー**
   - 全体の魅力を300文字程度で要約してください
   - 投資家や金融機関が「会って話を聞きたい」と思うような内容にしてください

3. **## 事業コンセプトと強み**
   - Concept（コンセプト）、Menu（メニュー）、Interior（内装外装）を統合して魅力的に記述してください
   - 事業の独自性と強みを明確に示してください

4. **## マーケットと戦略**
   - Location（立地）、Marketing（販促）を統合してください
   - ターゲット市場とマーケティング戦略を論理的に説明してください

5. **## オペレーションと実行計画**
   - Operation（オペレーション）の内容を基に、具体的な実行計画を記述してください

6. **## 財務計画**
   - Funding（資金計画）、Revenue（収支予測）を統合してください
   - 数字は強調（**太字**）してください
   - 投資対効果や収益性を明確に示してください

【トーン】
- 「〜です。〜ます。」調（デスマス体）で記述してください
- 自信に満ちた、かつ論理的なビジネス文書のトーンにしてください
- 冗長な表現を削ぎ落とし、読み手が「会って話を聞きたい」と思うような文章にしてください

【注意事項】
- 入力データに「（未作成）」や空の部分がある場合は、「検討中」として自然に文章に組み込んでください
- すべての情報を統合し、一貫性のある物語として構成してください
- 投資家や金融機関が評価できる具体的な数値や根拠を含めてください"""

    user_prompt = f"""以下の8つの事業軸のメモを基に、事業計画書を作成してください：

【コンセプト】
{concept_summary}

【立地・物件】
{location_summary}

【メニュー】
{menu_summary}

【販促】
{marketing_summary}

【資金計画】
{funding_plan_summary}

【収支予測】
{revenue_forecast_summary}

【オペレーション】
{operation_summary}

【内装外装】
{interior_exterior_summary}

上記の情報を統合し、投資家や金融機関に提出できるレベルの事業計画書を作成してください。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    # AIに事業計画書を生成させる
    try:
        ai_generated_content = await _chat_completion(
            messages=messages,
            max_tokens=4000,  # 事業計画書は長文になるため、トークン数を増やす
            temperature=0.7,
        )
        
        if not ai_generated_content:
            logger.error("AIによる事業計画書の生成に失敗しました")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="事業計画書の生成に失敗しました。時間をおいて再試行してください。"
            )
        
        return {"content": ai_generated_content}
    except Exception as e:
        logger.error(f"事業計画書生成エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"事業計画書の生成中にエラーが発生しました: {str(e)}"
        )

