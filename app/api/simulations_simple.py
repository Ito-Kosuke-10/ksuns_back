from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, get_current_user_optional
from app.core.db import get_session
from app.schemas.auth import UserInfo
from app.schemas.simulation import (
    AttachUserRequest,
    SimulationResultResponse,
    SubmitSimulationRequest,
)
from app.services.simulation import (
    attach_session_to_user,
    process_simulation_submission,
)

router = APIRouter(prefix="/simulations/simple", tags=["simulations"])


@router.post("/result", response_model=SimulationResultResponse)
async def submit_simple_simulation(
    payload: SubmitSimulationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[UserInfo] = Depends(get_current_user_optional),
) -> SimulationResultResponse:
    return await process_simulation_submission(
        db=session,
        payload=payload,
        user_id=current_user.id if current_user else None,
    )


@router.post("/attach-user", response_model=SimulationResultResponse)
async def attach_user_to_session(
    payload: AttachUserRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> SimulationResultResponse:
    result = await attach_session_to_user(
        db=session,
        session_id=payload.session_id,
        user_id=current_user.id,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Simulation session not found"
        )
    return result
