"""
開業プラン出力API
全8軸のAIサマリーを結合して返す
"""
from fastapi import APIRouter, Depends
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
    
    # Markdown形式で結合
    markdown_content = f"""# 開業計画書

## 1. コンセプト

{concept_summary}

## 2. 立地・物件

{location_summary}

## 3. メニュー

{menu_summary}

## 4. 販促

{marketing_summary}

## 5. 資金計画

{funding_plan_summary}

## 6. 収支予測

{revenue_forecast_summary}

## 7. オペレーション

{operation_summary}

## 8. 内装外装

{interior_exterior_summary}
"""
    
    return {"content": markdown_content}

