"""
Rewards & Gamification API Routes (Phase 15)

Authenticated endpoints for XP, streaks, badges, and reward history.
All access is restricted to the authenticated user.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.auth.session import get_current_user_id
from backend.services.reward_service import RewardService

router = APIRouter(prefix="/rewards", tags=["Rewards & Gamification"])


@router.get("")
async def get_rewards_summary(user_id: str = Depends(get_current_user_id)):
    """Fetch complete gamification summary for the authenticated user."""
    try:
        return RewardService.get_user_rewards(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rewards summary: {str(e)}"
        )


@router.get("/xp")
async def get_xp_summary(user_id: str = Depends(get_current_user_id)):
    """Fetch total XP and detailed transaction history."""
    try:
        return RewardService.get_user_xp(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch XP summary: {str(e)}"
        )


@router.get("/streak")
async def get_streak_summary(user_id: str = Depends(get_current_user_id)):
    """Fetch consecutive day streak metrics."""
    try:
        return RewardService.get_user_streak(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch streak summary: {str(e)}"
        )


@router.get("/badges")
async def get_badges_summary(user_id: str = Depends(get_current_user_id)):
    """Fetch earned badges and full badge progression catalog."""
    try:
        return RewardService.get_user_badges(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch badges: {str(e)}"
        )
