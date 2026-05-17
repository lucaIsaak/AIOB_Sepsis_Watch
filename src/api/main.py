from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routers import patients, narrative, feedback, stats

app = FastAPI(title="Sepsis Watch Demo", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router, prefix="/api")
app.include_router(narrative.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _dist.exists():
    # Serve static assets (JS, CSS, images) from the dist folder
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    # Catch-all: serve index.html for any non-API path (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(str(_dist / "index.html"))
