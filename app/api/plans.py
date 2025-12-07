# プラン関連のAPI　からちゃん
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.db import get_session
from app.models.plan import PlanningPlan
from app.schemas.auth import UserInfo
from app.schemas.plan import PlanCreateRequest, PlanListResponse, PlanResponse

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=PlanListResponse)
async def list_my_plans(
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> PlanListResponse:
    """
    ログインユーザーが持っているプラン一覧を返す。
    （STEP2ではまだ単純に created_at 昇順で返すだけ）
    """
    result = await session.execute(
        select(PlanningPlan)
        .where(PlanningPlan.user_id == current_user.id)
        .order_by(PlanningPlan.created_at.asc())
    )
    plans = result.scalars().all()
    return PlanListResponse(plans=plans)


@router.post(
    "",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_plan(
    payload: PlanCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> PlanResponse:
    """
    新しいプランを1つ作成する。
    name が指定されていなければ「新しいプラン」を仮名として付与する。
    （後で簡易シミュ結果からいい感じの名前に更新してもOK）
    """
    name = payload.name or "新しいプラン"

    plan = PlanningPlan(user_id=current_user.id, name=name)
    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    return plan
