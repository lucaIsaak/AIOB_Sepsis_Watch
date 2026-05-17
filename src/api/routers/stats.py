from fastapi import APIRouter
from src.api.mock_data import STATS, MODEL_INFO, DRIFT_STATUS, FEEDBACK_AGENT_STATUS

router = APIRouter()


@router.get("/stats")
def get_stats():
    return STATS


@router.get("/model/info")
def get_model_info():
    return MODEL_INFO


@router.get("/drift/status")
def get_drift_status():
    return DRIFT_STATUS


@router.get("/feedback-agent/status")
def get_feedback_agent_status():
    return FEEDBACK_AGENT_STATUS


@router.get("/audit")
def get_audit_log(n: int = 50):
    return []


@router.post("/retrain")
def trigger_retrain():
    return {"status": "unavailable", "message": "Retraining is disabled in demo mode."}


@router.get("/retrain/status")
def get_retrain_status():
    return {"status": "idle", "log": "", "started_at": None, "finished_at": None, "exit_code": None}
