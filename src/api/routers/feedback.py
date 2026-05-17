from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

router = APIRouter()

_clinical: dict[int, dict] = {}
_narrative: list[dict] = []


class ClinicalFeedbackRequest(BaseModel):
    stay_id: int
    feedback_type: str
    risk_score: float

    @field_validator("feedback_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in {"confirmed_sepsis", "flagged_wrong"}:
            raise ValueError("feedback_type must be 'confirmed_sepsis' or 'flagged_wrong'")
        return v


class NarrativeFeedbackRequest(BaseModel):
    stay_id: int
    rating: int
    correction_note: Optional[str] = None
    narrative_text: Optional[str] = None
    model_used: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("rating must be between 1 and 5")
        return v


@router.post("/feedback/clinical")
def save_clinical_feedback(body: ClinicalFeedbackRequest):
    _clinical[body.stay_id] = {"feedback_type": body.feedback_type, "risk_score": body.risk_score}
    return {"status": "saved"}


@router.get("/feedback/clinical/{stay_id}")
def get_clinical_feedback(stay_id: int):
    return _clinical.get(stay_id)


@router.post("/feedback/narrative")
def save_narrative_feedback(body: NarrativeFeedbackRequest):
    _narrative.append(body.model_dump())
    return {"status": "saved"}


@router.get("/feedback/whisper-status")
def get_whisper_status():
    return {"available": False, "message": "Transcription is disabled in demo mode."}


@router.post("/feedback/transcribe")
def transcribe_audio():
    raise HTTPException(status_code=503, detail="Transcription is disabled in demo mode.")
