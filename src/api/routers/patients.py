from fastapi import APIRouter, HTTPException
from src.api.mock_data import PATIENTS, PATIENT_DETAILS

router = APIRouter()


@router.get("/patients")
def list_patients():
    return sorted(PATIENTS, key=lambda p: p["risk_score"], reverse=True)


@router.get("/patients/{stay_id}")
def get_patient(stay_id: int):
    detail = PATIENT_DETAILS.get(stay_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Patient {stay_id} not found")
    return detail
