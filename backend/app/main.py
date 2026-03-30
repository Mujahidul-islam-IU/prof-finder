"""
ProfFinder — FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.routes import router
from app.api.auth import router as auth_router


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ProfFinder API",
        description="Multi-agent AI system for finding graduate school professors",
        version="1.0.0",
    )

    # ── CORS ─────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ───────────────────────────────────────────
    app.include_router(router)
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

    @app.on_event("startup")
    async def startup():
        import os
        os.makedirs(settings.upload_dir, exist_ok=True)
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        print("[ProfFinder] API started")
        print(f"   Upload dir: {settings.upload_dir}")
        print(f"   ChromaDB dir: {settings.chroma_persist_dir}")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
