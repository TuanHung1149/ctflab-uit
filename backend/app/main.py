from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, boxes, instances, submissions

app = FastAPI(title="CTFLab UIT", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(boxes.router, prefix="/api/boxes", tags=["boxes"])
app.include_router(instances.router, prefix="/api/instances", tags=["instances"])
app.include_router(submissions.router, prefix="/api/submissions", tags=["submissions"])


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
