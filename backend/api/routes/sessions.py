from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from backend.auth.session import get_current_user_id
from backend.schemas.contracts import LearningSession, SessionInputs, SessionInputsResponse, CALAResult, Roadmap
from backend.services.session_service import SessionService
from backend.services.cala_service import CALAService
from backend.services.roadmap_service import RoadmapService

router = APIRouter(tags=["sessions"])

@router.post("/sessions", response_model=LearningSession, status_code=status.HTTP_201_CREATED)
async def create_session(user_id: str = Depends(get_current_user_id)):
    """Create a new learning session."""
    return SessionService.create_session(user_id)

@router.get("/sessions", response_model=List[LearningSession])
async def list_current_user_sessions(current_user_id: str = Depends(get_current_user_id)) -> List[LearningSession]:
    """List sessions for the currently authenticated user."""
    return SessionService.list_user_sessions(current_user_id)

@router.get("/users/{user_id}/sessions", response_model=List[LearningSession])
async def list_user_sessions(user_id: str, current_user_id: str = Depends(get_current_user_id)) -> List[LearningSession]:
    """List sessions for a specific user ID."""
    if user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other user's sessions.")
    return SessionService.list_user_sessions(user_id)

@router.post("/sessions/{session_id}/inputs", response_model=SessionInputsResponse)
async def save_inputs(session_id: str, inputs: SessionInputs, user_id: str = Depends(get_current_user_id)):
    """Save the four mandatory inputs for a session."""
    try:
        return SessionService.save_inputs(session_id, user_id, inputs)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/sessions/{session_id}/inputs", response_model=SessionInputsResponse)
async def update_inputs(session_id: str, inputs: SessionInputs, user_id: str = Depends(get_current_user_id)):
    """Update existing inputs for a session."""
    try:
        return SessionService.save_inputs(session_id, user_id, inputs)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/sessions/{session_id}", response_model=LearningSession)
async def get_session(session_id: str, user_id: str = Depends(get_current_user_id)):
    """Get the current state of a learning session."""
    try:
        return SessionService.get_session(session_id, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.get("/sessions/{session_id}/inputs", response_model=SessionInputsResponse)
async def get_session_inputs(session_id: str, user_id: str = Depends(get_current_user_id)):
    """Retrieve the four saved inputs for a session."""
    try:
        return SessionService.get_session_inputs(session_id, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/sessions/{session_id}/analyze", response_model=CALAResult)
async def analyze_learner(session_id: str, user_id: str = Depends(get_current_user_id)):
    """Execute CALA analysis for the session."""
    try:
        session = SessionService.get_session(session_id, user_id)
        if session.status != 'READY_FOR_CALA':
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST,
                 detail=f"Session must be READY_FOR_CALA, currently {session.status}"
             )

        return CALAService.run_analysis(user_id, session_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/sessions/{session_id}/roadmap", response_model=Roadmap)
async def generate_roadmap(session_id: str, user_id: str = Depends(get_current_user_id)):
    """Generate a personalized roadmap based on CALA results."""
    try:
        # Verify session exists and is owned by user
        SessionService.get_session(session_id, user_id)

        return RoadmapService.generate_roadmap(user_id, session_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/sessions/{session_id}/finalize", response_model=LearningSession)
async def finalize_session(session_id: str, user_id: str = Depends(get_current_user_id)):
    """Confirm all inputs and mark session as READY_FOR_CALA."""
    try:
        return SessionService.finalize_session(session_id, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
