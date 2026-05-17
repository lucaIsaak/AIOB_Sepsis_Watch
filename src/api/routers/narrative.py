import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.mock_data import CLINICAL_NARRATIVE, PATIENTS

router = APIRouter()


class StreamRequest(BaseModel):
    stay_id: int
    model_name: str = "demo-model"


@router.get("/narrative/models")
def list_models():
    return ["demo-model"]


@router.post("/narrative/stream")
async def stream_narrative(body: StreamRequest):
    patient = next((p for p in PATIENTS if p["stay_id"] == body.stay_id), None)
    score = patient["risk_score"] if patient else 0.5
    label = patient["risk_label"] if patient else "MODERATE"

    text = CLINICAL_NARRATIVE.format(stay_id=body.stay_id, score=score, label=label)

    async def _generate():
        chunk_size = 8
        for i in range(0, len(text), chunk_size):
            yield text[i: i + chunk_size]
            await asyncio.sleep(0.02)

    return StreamingResponse(
        _generate(),
        media_type="text/plain",
        headers={"X-Accel-Buffering": "no"},
    )
